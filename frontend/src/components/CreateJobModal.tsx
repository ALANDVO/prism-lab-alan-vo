import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useJobs } from '../hooks/useJobs';
import { Plus, Loader2, AlertCircle } from 'lucide-react';
const createJobSchema = z.object({
  filename: z.string().min(1, 'Filename is required'),
  input_path: z.string().min(1, 'Input path is required'),
  preset: z.string().optional(),
  enable_ltx: z.boolean().default(false),
  enable_mosaic_removal: z.boolean().default(false),
  mosaic_mode: z.string().optional(),
});

type CreateJobForm = z.infer<typeof createJobSchema>;

interface CreateJobModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateJobModal({ isOpen, onClose }: CreateJobModalProps) {
  const { createJob } = useJobs();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateJobForm>({
    resolver: zodResolver(createJobSchema),
    defaultValues: {
      enable_ltx: false,
      enable_mosaic_removal: false,
    },
  });

  const onSubmit = async (data: CreateJobForm) => {
    setSubmitting(true);
    setError(null);
    try {
      await createJob(data);
      reset();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create job');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="card-header">
          <h2 id="modal-title" className="text-lg font-semibold text-gray-900">Create New Job</h2>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="card-body space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div>
            <label htmlFor="filename" className="label">Filename</label>
            <input
              id="filename"
              type="text"
              className={`input ${errors.filename ? 'input-error' : ''}`}
              placeholder="video.mp4"
              {...register('filename')}
            />
            {errors.filename && <p className="error-text">{errors.filename.message}</p>}
          </div>

          <div>
            <label htmlFor="input_path" className="label">Input Path</label>
            <input
              id="input_path"
              type="text"
              className={`input ${errors.input_path ? 'input-error' : ''}`}
              placeholder="/path/to/video.mp4"
              {...register('input_path')}
            />
            {errors.input_path && <p className="error-text">{errors.input_path.message}</p>}
          </div>

          <div>
            <label htmlFor="preset" className="label">Preset (optional)</label>
            <select
              id="preset"
              className="input"
              {...register('preset')}
            >
              <option value="">None</option>
              <option value="fast">Fast</option>
              <option value="balanced">Balanced</option>
              <option value="quality">Quality</option>
            </select>
          </div>

          <div className="space-y-3 border-t pt-4">
            <h3 className="text-sm font-medium text-gray-900">Processing Options</h3>
            <div className="flex items-center gap-3">
              <input
                id="enable_ltx"
                type="checkbox"
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                {...register('enable_ltx')}
              />
              <label htmlFor="enable_ltx" className="text-sm text-gray-700 cursor-pointer">
                Enable LTX Restoration
              </label>
            </div>
            <div className="flex items-center gap-3">
              <input
                id="enable_mosaic_removal"
                type="checkbox"
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                {...register('enable_mosaic_removal')}
              />
              <label htmlFor="enable_mosaic_removal" className="text-sm text-gray-700 cursor-pointer">
                Enable Mosaic Removal
              </label>
            </div>
            <div>
              <label htmlFor="mosaic_mode" className="label">Mosaic Mode</label>
              <select
                id="mosaic_mode"
                className="input"
                {...register('mosaic_mode')}
              >
                <option value="">Auto</option>
                <option value="sbs_fisheye">SBS + Fisheye</option>
                <option value="sbs_per_eye">SBS - Per Eye</option>
              </select>
            </div>
          </div>
        </form>
        <div className="card-footer">
          <button
            type="button"
            onClick={onClose}
            className="btn btn-outline"
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            form="create-job-form"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 loading-spinner" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                Create Job
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}