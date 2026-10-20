import { useAuth } from '../hooks/useAuth';
import { Shield, Key, Info } from 'lucide-react';

export function Settings() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Manage your account and preferences</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">Account</h2>
        </div>
        <div className="card-body space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
              <span className="text-2xl font-medium text-blue-700">
                {user.name?.charAt(0).toUpperCase() || 'U'}
              </span>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{user.name}</h3>
              <p className="text-gray-500">{user.email}</p>
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 mt-1">
                <Shield className="w-3 h-3" />
                {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
              </span>
            </div>
          </div>
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-gray-900 mb-2">User ID</h4>
            <p className="font-mono text-sm text-gray-500">{user.sub}</p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">Preferences</h2>
        </div>
        <div className="card-body space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Key className="w-5 h-5 text-gray-400" />
              <span className="text-gray-700">API Access</span>
            </div>
            <span className="badge badge-pending">Not Configured</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Info className="w-5 h-5 text-gray-400" />
              <span className="text-gray-700">Color Correction</span>
            </div>
            <span className="badge badge-completed">Enabled</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">About</h2>
        </div>
        <div className="card-body space-y-2 text-sm text-gray-500">
          <p>prism-lab-alan-vo v1.0.0</p>
          <p>Video restoration tool with AI/ML-powered quality enhancement</p>
          <p className="mt-2">
            Built by <a href="mailto:alanvo@gmail.com" className="text-blue-600 hover:underline">Alan Vo</a>
          </p>
        </div>
      </div>
    </div>
  );
}