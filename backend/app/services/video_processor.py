"""Video processing service with job checkpointing."""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models import VideoJob, JobStatus
from app.services.color_engine import ColorMetadataExtractor, ColorCorrectionEngine, ColorMetadata


@dataclass
class JobCheckpoint:
    """Checkpoint data for job resume capability."""
    job_id: int
    current_frame: int
    total_frames: int
    processed_files: List[str]
    color_metadata: Optional[Dict[str, Any]] = None
    created_at: str = ""


class VideoProcessor:
    """Video processing with pause/resume and checkpoint support."""

    def __init__(self, checkpoint_dir: str = "./data/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.color_extractor = ColorMetadataExtractor()
        self.color_engine = ColorCorrectionEngine(self.color_extractor)
        self._running_jobs: Dict[int, asyncio.Task] = {}

    def _checkpoint_path(self, job_id: int) -> Path:
        return self.checkpoint_dir / f"job_{job_id}.json"

    def save_checkpoint(self, checkpoint: JobCheckpoint) -> None:
        """Save job checkpoint to disk."""
        checkpoint.created_at = datetime.now(timezone.utc).isoformat()
        path = self._checkpoint_path(checkpoint.job_id)
        path.write_text(json.dumps(asdict(checkpoint)))

    def load_checkpoint(self, job_id: int) -> Optional[JobCheckpoint]:
        """Load job checkpoint from disk."""
        path = self._checkpoint_path(job_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return JobCheckpoint(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def clear_checkpoint(self, job_id: int) -> None:
        """Clear job checkpoint after completion."""
        path = self._checkpoint_path(job_id)
        if path.exists():
            path.unlink()

    async def process_job(self, job_id: int, db: AsyncSession) -> None:
        """Process a video job with checkpointing."""
        result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        # Load existing checkpoint if resuming
        checkpoint = self.load_checkpoint(job_id)
        start_frame = checkpoint.current_frame if checkpoint else 0
        processed_files = checkpoint.processed_files if checkpoint else []

        # Update job status
        job.status = JobStatus.PROCESSING
        job.current_frame = start_frame
        if not job.started_at:
            job.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # Extract color metadata from source
            color_metadata = self.color_extractor.extract(job.input_path)
            job.color_primaries = color_metadata.color_primaries
            job.color_transfer = color_metadata.color_transfer
            job.color_matrix = color_metadata.color_space
            job.color_range = color_metadata.color_range
            job.chroma_location = color_metadata.chroma_location
            job.pix_fmt = color_metadata.pix_fmt
            await db.commit()

            # Simulate frame processing (replace with actual processing)
            total_frames = job.total_frames or 1000
            job.total_frames = total_frames

            for frame in range(start_frame, total_frames):
                # Check if job was paused/cancelled
                await db.refresh(job)
                if job.status == JobStatus.PAUSED:
                    # Save checkpoint and exit
                    checkpoint = JobCheckpoint(
                        job_id=job_id,
                        current_frame=frame,
                        total_frames=total_frames,
                        processed_files=processed_files,
                        color_metadata=asdict(color_metadata) if color_metadata else None,
                    )
                    self.save_checkpoint(checkpoint)
                    return
                elif job.status == JobStatus.CANCELLED:
                    return

                # Simulate work
                await asyncio.sleep(0.01)

                # Update progress every 10 frames
                if frame % 10 == 0:
                    job.current_frame = frame
                    job.progress = int((frame / total_frames) * 100)
                    await db.commit()

            # Complete job
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.current_frame = total_frames
            job.completed_at = datetime.now(timezone.utc)
            job.output_path = f"{Path(job.input_path).stem}_restored.mp4"
            await db.commit()

            # Clear checkpoint
            self.clear_checkpoint(job_id)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise

    async def get_next_unprocessed_job(self, user_id: int, db: AsyncSession) -> Optional[VideoJob]:
        """Get next unprocessed job for user, skipping completed ones."""
        # This would check output file existence in real implementation
        result = await db.execute(
            select(VideoJob)
            .where(VideoJob.owner_id == user_id)
            .where(VideoJob.status.in_([JobStatus.PENDING, JobStatus.QUEUED]))
            .order_by(VideoJob.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()


video_processor = VideoProcessor()