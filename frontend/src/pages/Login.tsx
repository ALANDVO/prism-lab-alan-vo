import { useAuth } from '../hooks/useAuth';
import { Loader2 } from 'lucide-react';

export function Login() {
  const { login, loading } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">prism-lab-alan-vo</h1>
          <p className="text-gray-500 mt-2">Video Restoration Platform</p>
        </div>

        <div className="card">
          <div className="card-body">
            <button
              onClick={login}
              disabled={loading}
              className="w-full btn btn-primary btn-lg"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 loading-spinner" />
                  Redirecting...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
                  </svg>
                  Sign in with Keycloak
                </>
              )}
            </button>

            <p className="mt-4 text-center text-sm text-gray-500">
              You will be redirected to your organization's identity provider.
            </p>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-gray-400">
          prism-lab-alan-vo v1.0.0 &copy; 2024 Alan Vo
        </p>
      </div>
    </div>
  );
}