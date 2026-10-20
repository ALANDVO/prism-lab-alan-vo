"""Video job API routes."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import generate_csrf_token
from app.models import VideoJob, JobStatus, User
from app.api.deps import get_current_user, require_operator_or_admin
from app.api.schemas import (
    VideoJobCreate,
    VideoJobUpdate,
    VideoJobResponse,
    VideoJobListResponse,
    PaginatedResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=VideoJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: VideoJobCreate,
    user: User = Depends(require_operator_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new video restoration job."""
    # Verify CSRF token for cookie-authenticated requests
    # (In production, use proper CSRF middleware)

    job = VideoJob(
        owner_id=user.id,
        filename=job_data.filename,
        input_path=job_data.input_path,
        preset=job_data.preset,
        enable_ltx=job_data.enable_ltx,
        enable_mosaic_removal=job_data.enable_mosaic_removal,
        mosaic_mode=job_data.mosaic_mode,
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("", response_model=PaginatedResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List video jobs for current user with pagination."""
    query = select(VideoJob).where(VideoJob.owner_id == user.id)
    count_query = select(func.count(VideoJob.id)).where(VideoJob.owner_id == user.id)

    if status_filter:
        query = query.where(VideoJob.status == status_filter)
        count_query = count_query.where(VideoJob.status == status_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(VideoJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=jobs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{job_id}", response_model=VideoJobResponse)
async def get_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific job by ID."""
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.patch("/{job_id}", response_model=VideoJobResponse)
async def update_job(
    job_id: int,
    job_update: VideoJobUpdate,
    user: User = Depends(require_operator_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a job (status, progress, etc.)."""
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_data = job_update.model_dump(exclude_unset=True)

    # Handle status transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == JobStatus.PROCESSING and job.status == JobStatus.PENDING:
            job.started_at = datetime.now(timezone.utc)
        elif new_status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/pause", response_model=VideoJobResponse)
async def pause_job(
    job_id: int,
    user: User = Depends(require_operator_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Pause a processing job."""
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Can only pause processing jobs")

    job.status = JobStatus.PAUSED
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/resume", response_model=VideoJobResponse)
async def resume_job(
    job_id: int,
    user: User = Depends(require_operator_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused job."""
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Can only resume paused jobs")

    job.status = JobStatus.PROCESSING
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/cancel", response_model=VideoJobResponse)
async def cancel_job(
    job_id: int,
    user: User = Depends(require_operator_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or processing job."""
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Cannot cancel completed or already cancelled job")

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    user: User = Depends(require_operator_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job (only if not processing)."""
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Cannot delete processing job")

    await db.delete(job)
    await db.commit()
    return None