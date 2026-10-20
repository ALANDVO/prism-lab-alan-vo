import { useEffect, useState } from 'react';
import { useJobs } from '../hooks/useJobs';
import { JobTable } from '../components/JobTable';
import { CreateJobModal } from '../components/CreateJobModal';
import { ToastContainer } from '../components/Toast';
import { Plus, RefreshCw, AlertCircle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

export function Dashboard() {
  const {
    jobs,
    total,
    page,
    pageSize,
    loading,
    error,
    fetchJobs,
    pauseJob,
    resumeJob,
    cancelJob,
    deleteJob,
  } = useJobs();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const addToast = (message: string, type: ToastType) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
  };

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handlePause = async (id: number) => {
    await pauseJob(id);
    addToast('Job paused', 'info');
  };

  const handleResume = async (id: number) => {
    await resumeJob(id);
    addToast('Job resumed', 'success');
  };

  const handleCancel = async (id: number) => {
    await cancelJob(id);
    addToast('Job cancelled', 'warning');
  };

  const handleDelete = async (id: number) => {
    await deleteJob(id);
    addToast('Job deleted', 'info');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Manage your video restoration jobs</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary"
        >
          <Plus className="w-4 h-4" />
          New Job
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{error}</span>
          <button
            onClick={() => fetchJobs(page)}
            className="ml-auto btn btn-outline btn-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">Jobs ({total})</h2>
        </div>
        <div className="card-body p-0">
          <JobTable
            jobs={jobs}
            onPause={handlePause}
            onResume={handleResume}
            onCancel={handleCancel}
            onDelete={handleDelete}
            loading={loading}
          />
        </div>
        {total > pageSize && (
          <div className="card-footer border-t border-gray-200 justify-between">
            <div className="text-sm text-gray-500">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => fetchJobs(page - 1)}
                disabled={page === 1 || loading}
                className="btn btn-outline btn-sm"
              >
                Previous
              </button>
              <button
                onClick={() => fetchJobs(page + 1)}
                disabled={page * pageSize >= total || loading}
                className="btn btn-outline btn-sm"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      <CreateJobModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}