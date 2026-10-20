import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { VideoJob, VideoJobCreate, VideoJobUpdate, JobStatus } from '../types';
import { jobsApi } from '../api/client';

interface JobsContextType {
  jobs: VideoJob[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  error: string | null;
  fetchJobs: (page?: number, status?: JobStatus) => Promise<void>;
  createJob: (data: VideoJobCreate) => Promise<VideoJob | null>;
  updateJob: (id: number, data: VideoJobUpdate) => Promise<VideoJob | null>;
  pauseJob: (id: number) => Promise<VideoJob | null>;
  resumeJob: (id: number) => Promise<VideoJob | null>;
  cancelJob: (id: number) => Promise<VideoJob | null>;
  deleteJob: (id: number) => Promise<boolean>;
  refetch: () => Promise<void>;
}

const JobsContext = createContext<JobsContextType | undefined>(undefined);

export function JobProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async (newPage = 1, status?: JobStatus) => {
    setLoading(true);
    setError(null);
    try {
      const response = await jobsApi.list({ page: newPage, page_size: pageSize, status });
      setJobs(response.data.items);
      setTotal(response.data.total);
      setPage(response.data.page);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch jobs');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  const createJob = useCallback(async (data: VideoJobCreate) => {
    try {
      const response = await jobsApi.create(data);
      await fetchJobs(page);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create job');
      return null;
    }
  }, [fetchJobs, page]);

  const updateJob = useCallback(async (id: number, data: VideoJobUpdate) => {
    try {
      const response = await jobsApi.update(id, data);
      setJobs(jobs.map(j => j.id === id ? response.data : j));
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update job');
      return null;
    }
  }, [jobs]);

  const pauseJob = useCallback(async (id: number) => {
    try {
      const response = await jobsApi.pause(id);
      setJobs(jobs.map(j => j.id === id ? response.data : j));
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to pause job');
      return null;
    }
  }, [jobs]);

  const resumeJob = useCallback(async (id: number) => {
    try {
      const response = await jobsApi.resume(id);
      setJobs(jobs.map(j => j.id === id ? response.data : j));
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resume job');
      return null;
    }
  }, [jobs]);

  const cancelJob = useCallback(async (id: number) => {
    try {
      const response = await jobsApi.cancel(id);
      setJobs(jobs.map(j => j.id === id ? response.data : j));
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to cancel job');
      return null;
    }
  }, [jobs]);

  const deleteJob = useCallback(async (id: number) => {
    try {
      await jobsApi.delete(id);
      setJobs(jobs.filter(j => j.id !== id));
      setTotal(total - 1);
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete job');
      return false;
    }
  }, [jobs, total]);

  const refetch = useCallback(() => fetchJobs(page), [fetchJobs, page]);

  return (
    <JobsContext.Provider value={{
      jobs, total, page, pageSize, loading, error,
      fetchJobs, createJob, updateJob, pauseJob, resumeJob, cancelJob, deleteJob, refetch
    }}>
      {children}
    </JobsContext.Provider>
  );
}

export function useJobs() {
  const context = useContext(JobsContext);
  if (!context) {
    throw new Error('useJobs must be used within JobProvider');
  }
  return context;
}