import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../hooks/useAuth'
import { JobProvider } from '../hooks/useJobs'
import { Login } from '../pages/Login'
import { JobTable } from '../components/JobTable'
import { CreateJobModal } from '../components/CreateJobModal'
import { Toast, ToastContainer } from '../components/Toast'

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  authApi: {
    me: vi.fn(),
    logout: vi.fn(),
    getCsrf: vi.fn(),
  },
  jobsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    cancel: vi.fn(),
    delete: vi.fn(),
  },
  healthApi: {
    check: vi.fn(),
  },
}))

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <JobProvider>
          {component}
        </JobProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('Login Page', () => {
  it('renders login page with title', () => {
    renderWithProviders(<Login />)
    expect(screen.getByText('prism-lab-alan-vo')).toBeInTheDocument()
    expect(screen.getByText('Video Restoration Platform')).toBeInTheDocument()
  })

  it('shows disabled button when loading', () => {
    renderWithProviders(<Login />)
    const button = screen.getByRole('button', { name: /redirecting/i })
    expect(button).toBeInTheDocument()
    expect(button).toBeDisabled()
  })
})

describe('JobTable Component', () => {
  const mockJobs = [
    {
      id: 1,
      filename: 'video1.mp4',
      input_path: '/path/video1.mp4',
      output_path: null,
      status: 'processing' as const,
      progress: 50,
      current_frame: 500,
      total_frames: 1000,
      error_message: null,
      color_primaries: null,
      color_transfer: null,
      color_matrix: null,
      color_range: null,
      chroma_location: null,
      pix_fmt: null,
      preset: 'balanced',
      enable_ltx: false,
      enable_mosaic_removal: false,
      mosaic_mode: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      started_at: '2024-01-01T00:00:00Z',
      completed_at: null,
      owner_id: 1,
    },
    {
      id: 2,
      filename: 'video2.mp4',
      input_path: '/path/video2.mp4',
      output_path: '/path/video2_restored.mp4',
      status: 'completed' as const,
      progress: 100,
      current_frame: 1000,
      total_frames: 1000,
      error_message: null,
      color_primaries: 'bt709',
      color_transfer: 'bt709',
      color_matrix: 'bt709',
      color_range: 'tv',
      chroma_location: 'center',
      pix_fmt: 'yuv420p',
      preset: 'quality',
      enable_ltx: true,
      enable_mosaic_removal: true,
      mosaic_mode: 'sbs_fisheye',
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
      started_at: '2024-01-02T00:00:00Z',
      completed_at: '2024-01-02T01:00:00Z',
      owner_id: 1,
    },
  ]

  it('renders jobs table with data', () => {
    renderWithProviders(<JobTable jobs={mockJobs} onPause={vi.fn()} onResume={vi.fn()} onCancel={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText('video1.mp4')).toBeInTheDocument()
    expect(screen.getByText('video2.mp4')).toBeInTheDocument()
    expect(screen.getByText('Processing')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
  })

  it('shows empty state when no jobs', () => {
    renderWithProviders(<JobTable jobs={[]} onPause={vi.fn()} onResume={vi.fn()} onCancel={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText('No jobs yet')).toBeInTheDocument()
  })

  it('shows loading skeleton when loading', () => {
    renderWithProviders(<JobTable jobs={[]} onPause={vi.fn()} onResume={vi.fn()} onCancel={vi.fn()} onDelete={vi.fn()} loading={true} />)
    expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument()
  })
})

describe('CreateJobModal Component', () => {
  it('renders form fields when open', () => {
    renderWithProviders(<CreateJobModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByLabelText('Filename')).toBeInTheDocument()
    expect(screen.getByLabelText('Input Path')).toBeInTheDocument()
    expect(screen.getByLabelText('Preset (optional)')).toBeInTheDocument()
    expect(screen.getByLabelText('Enable LTX Restoration')).toBeInTheDocument()
    expect(screen.getByLabelText('Enable Mosaic Removal')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    renderWithProviders(<CreateJobModal isOpen={false} onClose={vi.fn()} />)
    expect(screen.queryByLabelText('Filename')).not.toBeInTheDocument()
  })

  it('shows form with submit button', () => {
    renderWithProviders(<CreateJobModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByRole('button', { name: /create job/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })
})

describe('Toast Component', () => {
  it('renders success toast', () => {
    renderWithProviders(<Toast message="Success!" type="success" onClose={vi.fn()} />)
    expect(screen.getByText('Success!')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('renders error toast', () => {
    renderWithProviders(<Toast message="Error!" type="error" onClose={vi.fn()} />)
    expect(screen.getByText('Error!')).toBeInTheDocument()
  })

  it('renders warning toast', () => {
    renderWithProviders(<Toast message="Warning!" type="warning" onClose={vi.fn()} />)
    expect(screen.getByText('Warning!')).toBeInTheDocument()
  })

  it('renders info toast', () => {
    renderWithProviders(<Toast message="Info!" type="info" onClose={vi.fn()} />)
    expect(screen.getByText('Info!')).toBeInTheDocument()
  })
})

describe('ToastContainer Component', () => {
  it('renders multiple toasts', () => {
    const toasts = [
      { id: 1, message: 'First', type: 'success' as const },
      { id: 2, message: 'Second', type: 'error' as const },
    ]
    renderWithProviders(<ToastContainer toasts={toasts} onRemove={vi.fn()} />)
    expect(screen.getByText('First')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()
  })

  it('removes toast on close', () => {
    const onRemove = vi.fn()
    const toasts = [{ id: 1, message: 'Test', type: 'info' as const }]
    renderWithProviders(<ToastContainer toasts={toasts} onRemove={onRemove} />)
    const closeButton = screen.getByLabelText('Dismiss')
    fireEvent.click(closeButton)
    expect(onRemove).toHaveBeenCalledWith(1)
  })
})