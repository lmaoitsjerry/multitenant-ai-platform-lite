import { useApp } from '../../context/AppContext';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout({ children }) {
  const { sidebarOpen, loading, error } = useApp();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-background">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-theme-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-theme-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-background">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-theme mb-2">Connection Error</h2>
          <p className="text-theme-secondary mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-theme-background">
      <Sidebar />
      <div
        className={`transition-all duration-300 ${
          sidebarOpen ? 'ml-64' : 'ml-16'
        }`}
      >
        <Header />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
