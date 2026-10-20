import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import User, UserRole, VideoJob, JobStatus


# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestAsyncSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        sub="test-sub-123",
        email="test@example.com",
        name="Test User",
        role=UserRole.OPERATOR,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    user = User(
        sub="admin-sub-456",
        email="admin@example.com",
        name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(test_user: User):
    token = create_access_token({"sub": str(test_user.id), "email": test_user.email, "role": test_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user: User):
    token = create_access_token({"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role.value})
    return {"Authorization": f"Bearer {token}"}


class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAuth:
    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401

    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["role"] == test_user.role.value

    async def test_csrf_token(self, client: AsyncClient):
        response = await client.get("/auth/csrf")
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 0


class TestJobs:
    async def test_create_job_unauthenticated(self, client: AsyncClient):
        response = await client.post("/jobs", json={
            "filename": "test.mp4",
            "input_path": "/path/to/test.mp4",
            "enable_ltx": False,
            "enable_mosaic_removal": False,
        })
        assert response.status_code == 401

    async def test_create_job_viewer_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        viewer = User(sub="viewer-sub", email="viewer@test.com", name="Viewer", role=UserRole.VIEWER)
        db_session.add(viewer)
        await db_session.commit()
        token = create_access_token({"sub": str(viewer.id), "email": viewer.email, "role": viewer.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post("/jobs", json={
            "filename": "test.mp4",
            "input_path": "/path/to/test.mp4",
            "enable_ltx": False,
            "enable_mosaic_removal": False,
        }, headers=headers)
        assert response.status_code == 403

    async def test_create_job_operator(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/jobs", json={
            "filename": "test.mp4",
            "input_path": "/path/to/test.mp4",
            "preset": "balanced",
            "enable_ltx": True,
            "enable_mosaic_removal": False,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.mp4"
        assert data["status"] == "pending"
        assert data["preset"] == "balanced"
        assert data["enable_ltx"] is True

    async def test_list_jobs(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        # Create some jobs
        for i in range(3):
            job = VideoJob(
                owner_id=test_user.id,
                filename=f"video_{i}.mp4",
                input_path=f"/path/to/video_{i}.mp4",
                status=JobStatus.PENDING if i < 2 else JobStatus.COMPLETED,
            )
            db_session.add(job)
        await db_session.commit()

        response = await client.get("/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_jobs_with_status_filter(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job1 = VideoJob(owner_id=test_user.id, filename="pending.mp4", input_path="/p.mp4", status=JobStatus.PENDING)
        job2 = VideoJob(owner_id=test_user.id, filename="completed.mp4", input_path="/c.mp4", status=JobStatus.COMPLETED)
        db_session.add_all([job1, job2])
        await db_session.commit()

        response = await client.get("/jobs?status=pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "pending.mp4"

    async def test_get_job(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/path/test.mp4")
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.get(f"/jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job.id
        assert data["filename"] == "test.mp4"

    async def test_get_job_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/jobs/99999", headers=auth_headers)
        assert response.status_code == 404

    async def test_get_job_other_user(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, admin_user: User):
        job = VideoJob(owner_id=admin_user.id, filename="admin.mp4", input_path="/admin.mp4")
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.get(f"/jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_update_job(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/test.mp4", status=JobStatus.PENDING)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.patch(f"/jobs/{job.id}", json={
            "status": "processing",
            "progress": 50,
            "current_frame": 500,
            "total_frames": 1000,
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 50
        assert data["current_frame"] == 500

    async def test_pause_job(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/test.mp4", status=JobStatus.PROCESSING)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.post(f"/jobs/{job.id}/pause", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    async def test_pause_non_processing_job(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/test.mp4", status=JobStatus.PENDING)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.post(f"/jobs/{job.id}/pause", headers=auth_headers)
        assert response.status_code == 400

    async def test_resume_job(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/test.mp4", status=JobStatus.PAUSED)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.post(f"/jobs/{job.id}/resume", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"

    async def test_cancel_job(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/test.mp4", status=JobStatus.PROCESSING)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.post(f"/jobs/{job.id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    async def test_delete_job(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/test.mp4", status=JobStatus.COMPLETED)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.delete(f"/jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_delete_processing_job_fails(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User):
        job = VideoJob(owner_id=test_user.id, filename="test.mp4", input_path="/test.mp4", status=JobStatus.PROCESSING)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.delete(f"/jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 400


class TestColorEngine:
    def test_color_metadata_extraction(self):
        from app.services.color_engine import ColorMetadataExtractor
        extractor = ColorMetadataExtractor(ffprobe_path="ffprobe")
        # This will fail if ffprobe not available, but tests the code path
        metadata = extractor.extract("/nonexistent.mp4")
        assert metadata.pix_fmt is None
        assert metadata.color_space is None

    def test_color_correction_engine_unknown_source(self):
        from app.services.color_engine import ColorCorrectionEngine, ColorMetadataExtractor, ColorMetadata
        extractor = ColorMetadataExtractor()
        engine = ColorCorrectionEngine(extractor)

        # Source with unknown color metadata
        source = ColorMetadata(
            pix_fmt="yuv420p",
            color_range="tv",
            color_space="unknown",
            color_transfer="unknown",
            color_primaries="unknown",
            chroma_location="center",
        )

        corrected = engine.get_corrected_metadata(source)
        assert corrected.color_space is None  # Not forced to bt709
        assert corrected.chroma_location == "center"  # Preserved
        assert corrected.color_range == "tv"

    def test_color_correction_engine_explicit_source(self):
        from app.services.color_engine import ColorCorrectionEngine, ColorMetadataExtractor, ColorMetadata
        extractor = ColorMetadataExtractor()
        engine = ColorCorrectionEngine(extractor)

        # Source with explicit BT.601 metadata
        source = ColorMetadata(
            pix_fmt="yuv420p",
            color_range="tv",
            color_space="bt470bg",  # BT.601
            color_transfer="bt470bg",
            color_primaries="bt470bg",
            chroma_location="center",
        )

        corrected = engine.get_corrected_metadata(source)
        assert corrected.color_space == "bt470bg"  # Preserved
        assert corrected.color_primaries == "bt470bg"

    def test_green_tint_risk_detection(self):
        from app.services.color_engine import detect_green_tint_risk, ColorMetadata
        # Unknown metadata -> risk
        risky = ColorMetadata(
            pix_fmt="yuv420p",
            color_range="tv",
            color_space="unknown",
            color_transfer="unknown",
            color_primaries="unknown",
            chroma_location="center",
        )
        assert detect_green_tint_risk(risky) is True

        # Explicit metadata -> no risk
        safe = ColorMetadata(
            pix_fmt="yuv420p",
            color_range="tv",
            color_space="bt709",
            color_transfer="bt709",
            color_primaries="bt709",
            chroma_location="center",
        )
        assert detect_green_tint_risk(safe) is False


class TestVideoProcessor:
    @pytest.mark.asyncio
    async def test_checkpoint_save_load(self, tmp_path):
        from app.services.video_processor import VideoProcessor, JobCheckpoint
        processor = VideoProcessor(checkpoint_dir=str(tmp_path))

        checkpoint = JobCheckpoint(
            job_id=1,
            current_frame=100,
            total_frames=1000,
            processed_files=["file1.mp4"],
        )
        processor.save_checkpoint(checkpoint)

        loaded = processor.load_checkpoint(1)
        assert loaded is not None
        assert loaded.job_id == 1
        assert loaded.current_frame == 100
        assert loaded.total_frames == 1000
        assert loaded.processed_files == ["file1.mp4"]

    @pytest.mark.asyncio
    async def test_checkpoint_clear(self, tmp_path):
        from app.services.video_processor import VideoProcessor, JobCheckpoint
        processor = VideoProcessor(checkpoint_dir=str(tmp_path))

        checkpoint = JobCheckpoint(job_id=1, current_frame=100, total_frames=1000, processed_files=[])
        processor.save_checkpoint(checkpoint)
        processor.clear_checkpoint(1)

        loaded = processor.load_checkpoint(1)
        assert loaded is None