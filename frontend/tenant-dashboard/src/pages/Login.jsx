import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const { login, error, clearError, isAuthenticated } = useAuth();
  const { branding } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // Clear error on unmount
  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;

    setSubmitting(true);
    clearError();

    const result = await login(email, password);

    setSubmitting(false);

    if (result.success) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  };

  // Get branding colors and background
  const primaryColor = branding?.colors?.primary || '#3B82F6';
  const companyName = branding?.company_name || 'Travel Platform';
  const logoUrl = branding?.logos?.primary;
  const loginBgImage = branding?.login_background_url;
  const loginBgGradient = branding?.login_background_gradient;

  // Background style - supports image, gradient, or default
  const backgroundStyle = loginBgImage
    ? { backgroundImage: `url(${loginBgImage})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : loginBgGradient
    ? { background: loginBgGradient }
    : {};

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-theme-background py-12 px-4 sm:px-6 lg:px-8"
      style={backgroundStyle}
    >
      {/* Overlay for background images */}
      {loginBgImage && (
        <div className="absolute inset-0 bg-black/40" />
      )}

      <div className="max-w-md w-full relative z-10">
        {/* Logo/Company Name */}
        <div className="text-center mb-8">
          {logoUrl ? (
            <img
              src={logoUrl}
              alt={companyName}
              className="h-16 mx-auto mb-4"
            />
          ) : (
            <div
              className="w-16 h-16 rounded-xl mx-auto mb-4 flex items-center justify-center text-white text-2xl font-bold bg-theme-primary"
            >
              {companyName.charAt(0)}
            </div>
          )}
          <h2 className={`text-2xl font-bold ${loginBgImage ? 'text-white' : 'text-theme'}`}>{companyName}</h2>
          <p className={`mt-2 ${loginBgImage ? 'text-white/80' : 'text-theme-secondary'}`}>Sign in to your account</p>
        </div>

        {/* Login Card */}
        <div className="bg-theme-surface rounded-2xl shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-error px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-theme-secondary mb-1">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@company.com"
              />
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-theme-secondary mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pr-12"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-theme-muted hover:text-theme-secondary"
                >
                  {showPassword ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting || !email || !password}
              className="btn-primary w-full py-3"
            >
              {submitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Signing in...
                </span>
              ) : (
                'Sign in'
              )}
            </button>

            {/* Forgot Password Link */}
            <div className="text-center">
              <Link
                to="/forgot-password"
                className="text-sm text-theme-primary hover:underline"
              >
                Forgot your password?
              </Link>
            </div>
          </form>
        </div>

        {/* Footer */}
        <p className={`mt-8 text-center text-sm ${loginBgImage ? 'text-white/70' : 'text-theme-muted'}`}>
          Need help? Contact your administrator.
        </p>
      </div>
    </div>
  );
}
