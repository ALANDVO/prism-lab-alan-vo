import { VideoJob, JobStatus } from '../types';
import { Play, Pause, X, Trash2, FileVideo } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface JobTableProps {
  jobs: VideoJob[];
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onCancel: (id: number) => void;
  onDelete: (id: number) => void;
  loading?: boolean;
}

const statusLabels: Record<JobStatus, string> = {
  pending: 'Pending',
  queued: 'Queued',
  processing: 'Processing',
  paused: 'Paused',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

const statusBadges: Record<JobStatus, string> = {
  pending: 'badge-pending',
  queued: 'badge-queued',
  processing: 'badge-processing',
  paused: 'badge-paused',
  completed: 'badge-completed',
  failed: 'badge-failed',
  cancelled: 'badge-cancelled',
};

export function JobTable({
  jobs,
  onPause,
  onResume,
  onCancel,
  onDelete,
  loading,
}: JobTableProps) {
  if (loading) {
    return (
      <div className="table-container" data-testid="loading-skeleton">
        <table className="table">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Frames</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {[...Array(5)].map((_, i) => (
              <tr key={i}>
                <td><div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" /></td>
                <td><div className="h-4 bg-gray-200 rounded w-20 animate-pulse" /></td>
                <td><div className="h-2 bg-gray-200 rounded animate-pulse" /></td>
                <td><div className="h-4 bg-gray-200 rounded w-24 animate-pulse" /></td>
                <td><div className="h-4 bg-gray-200 rounded w-32 animate-pulse" /></td>
                <td><div className="h-4 bg-gray-200 rounded w-16 animate-pulse" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="empty-state">
        <FileVideo className="empty-state-icon" />
        <h3 className="text-lg font-medium text-gray-900 mb-1">No jobs yet</h3>
        <p className="text-gray-500">Create your first video restoration job to get started.</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="table" role="table">
        <thead>
          <tr>
            <th scope="col">File</th>
            <th scope="col">Status</th>
            <th scope="col">Progress</th>
            <th scope="col">Frames</th>
            <th scope="col">Created</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>
                <div className="max-w-xs truncate" title={job.filename}>
                  {job.filename}
                </div>
              </td>
              <td>
                <span className={`badge ${statusBadges[job.status]}`}>
                  {statusLabels[job.status]}
                </span>
              </td>
              <td className="w-48">
                <div className="progress-bar">
                  <div
                    className={`progress-bar-fill ${job.status}`}
                    style={{ width: `${job.progress}%` }}
                    role="progressbar"
                    aria-valuenow={job.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`${job.progress}% complete`}
                  />
                </div>
              </td>
              <td className="text-sm text-gray-600">
                {job.current_frame.toLocaleString()} / {job.total_frames.toLocaleString()}
              </td>
              <td className="text-sm text-gray-500">
                {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
              </td>
              <td>
                <div className="flex items-center gap-2">
                  {job.status === 'processing' && (
                    <button
                      onClick={() => onPause(job.id)}
                      className="btn btn-outline btn-sm"
                      aria-label={`Pause job ${job.filename}`}
                    >
                      <Pause className="w-4 h-4" />
                    </button>
                  )}
                  {job.status === 'paused' && (
                    <button
                      onClick={() => onResume(job.id)}
                      className="btn btn-primary btn-sm"
                      aria-label={`Resume job ${job.filename}`}
                    >
                      <Play className="w-4 h-4" />
                    </button>
                  )}
                  {(job.status === 'pending' || job.status === 'queued' || job.status === 'processing' || job.status === 'paused') && (
                    <button
                      onClick={() => onCancel(job.id)}
                      className="btn btn-outline btn-sm"
                      aria-label={`Cancel job ${job.filename}`}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                  {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                    <button
                      onClick={() => onDelete(job.id)}
                      className="btn btn-outline btn-sm text-red-600 hover:bg-red-50"
                      aria-label={`Delete job ${job.filename}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}