"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models import JobStatus, UserRole


class UserBase(BaseModel):
    email: str
    name: str


class UserCreate(UserBase):
    sub: str
    role: UserRole = UserRole.VIEWER


class UserResponse(UserBase):
    id: int
    sub: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VideoJobBase(BaseModel):
    filename: str
    input_path: str
    preset: Optional[str] = None
    enable_ltx: bool = False
    enable_mosaic_removal: bool = False
    mosaic_mode: Optional[str] = None


class VideoJobCreate(VideoJobBase):
    pass


class VideoJobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    progress: Optional[int] = None
    current_frame: Optional[int] = None
    total_frames: Optional[int] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    color_primaries: Optional[str] = None
    color_transfer: Optional[str] = None
    color_matrix: Optional[str] = None
    color_range: Optional[str] = None
    chroma_location: Optional[str] = None
    pix_fmt: Optional[str] = None


class VideoJobResponse(VideoJobBase):
    id: int
    owner_id: int
    status: JobStatus
    progress: int
    current_frame: int
    total_frames: int
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    color_primaries: Optional[str] = None
    color_transfer: Optional[str] = None
    color_matrix: Optional[str] = None
    color_range: Optional[str] = None
    chroma_location: Optional[str] = None
    pix_fmt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VideoJobListResponse(BaseModel):
    jobs: List[VideoJobResponse]
    total: int
    page: int
    page_size: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthCallbackRequest(BaseModel):
    code: str
    state: str


class HealthResponse(BaseModel):
    status: str
    version: str
    oidc_enabled: bool


class ErrorResponse(BaseModel):
    detail: str


class PaginatedResponse(BaseModel):
    items: List[VideoJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int