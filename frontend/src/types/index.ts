export interface User {
  id: number;
  sub: string;
  email: string;
  name: string;
  role: UserRole;
  created_at: string;
  last_login: string | null;
}

export type UserRole = 'viewer' | 'operator' | 'admin';

export type JobStatus =
  | 'pending'
  | 'queued'
  | 'processing'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface VideoJob {
  id: number;
  owner_id: number;
  filename: string;
  input_path: string;
  output_path: string | null;
  status: JobStatus;
  progress: number;
  current_frame: number;
  total_frames: number;
  error_message: string | null;
  color_primaries: string | null;
  color_transfer: string | null;
  color_matrix: string | null;
  color_range: string | null;
  chroma_location: string | null;
  pix_fmt: string | null;
  preset: string | null;
  enable_ltx: boolean;
  enable_mosaic_removal: boolean;
  mosaic_mode: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface VideoJobCreate {
  filename: string;
  input_path: string;
  preset?: string;
  enable_ltx: boolean;
  enable_mosaic_removal: boolean;
  mosaic_mode?: string;
}

export interface VideoJobUpdate {
  status?: JobStatus;
  progress?: number;
  current_frame?: number;
  total_frames?: number;
  output_path?: string;
  error_message?: string;
  color_primaries?: string;
  color_transfer?: string;
  color_matrix?: string;
  color_range?: string;
  chroma_location?: string;
  pix_fmt?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  oidc_enabled: boolean;
}