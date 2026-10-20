import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { VideoJob, VideoJobCreate, VideoJobUpdate, PaginatedResponse, HealthResponse, JobStatus } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for CSRF
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // Add CSRF token for mutating requests
  const csrfToken = sessionStorage.getItem('csrf_token');
  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method || '')) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail: string }>) => {
    if (error.response?.status === 401) {
      // Clear auth state
      sessionStorage.removeItem('csrf_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: () => { window.location.href = '/auth/login'; },
  logout: () => api.post('/auth/logout'),
  me: () => api.get<User>('/auth/me'),
  getCsrf: () => api.get<{ csrf_token: string }>('/auth/csrf'),
};

export const jobsApi = {
  list: (params?: { page?: number; page_size?: number; status?: JobStatus }) =>
    api.get<PaginatedResponse<VideoJob>>('/jobs', { params }),
  get: (id: number) => api.get<VideoJob>(`/jobs/${id}`),
  create: (data: VideoJobCreate) => api.post<VideoJob>('/jobs', data),
  update: (id: number, data: VideoJobUpdate) => api.patch<VideoJob>(`/jobs/${id}`, data),
  pause: (id: number) => api.post<VideoJob>(`/jobs/${id}/pause`),
  resume: (id: number) => api.post<VideoJob>(`/jobs/${id}/resume`),
  cancel: (id: number) => api.post<VideoJob>(`/jobs/${id}/cancel`),
  delete: (id: number) => api.delete(`/jobs/${id}`),
};

export const healthApi = {
  check: () => api.get<HealthResponse>('/health'),
};

// Re-export types for convenience
export type { VideoJob, VideoJobCreate, VideoJobUpdate, PaginatedResponse, HealthResponse, JobStatus };

interface User {
  id: number;
  sub: string;
  email: string;
  name: string;
  role: 'viewer' | 'operator' | 'admin';
  created_at: string;
  last_login: string | null;
}