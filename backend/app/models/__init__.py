"""Database models."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Enum as SQLEnum, Index, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sub: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # Keycloak subject
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    jobs: Mapped[list["VideoJob"]] = relationship("VideoJob", back_populates="owner", cascade="all, delete-orphan")


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    input_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    output_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    current_frame: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_frames: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Color metadata preservation
    color_primaries: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    color_transfer: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    color_matrix: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    color_range: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    chroma_location: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pix_fmt: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Processing settings
    preset: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    enable_ltx: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_mosaic_removal: Mapped[bool] = mapped_column(Boolean, default=False)
    mosaic_mode: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="jobs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


Index("ix_video_jobs_owner_status", VideoJob.owner_id, VideoJob.status)
Index("ix_audit_logs_user_created", AuditLog.user_id, AuditLog.created_at)