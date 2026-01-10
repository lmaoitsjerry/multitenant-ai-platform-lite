import { useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../services/api';
import { useTheme } from '../context/ThemeContext';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const { branding } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;

    setSubmitting(true);
    setError('');

    try {
      await authApi.requestPasswordReset(email);
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send reset email. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const primaryColor = branding?.colors?.primary || '#3B82F6';
  const companyName = branding?.company_name || 'Travel Platform';
  const logoUrl = branding?.logos?.primary;

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          <div className="text-center mb-8">
            {logoUrl ? (
              <img src={logoUrl} alt={companyName} className="h-16 mx-auto mb-4" />
            ) : (
              <div
                className="w-16 h-16 rounded-xl mx-auto mb-4 flex items-center justify-center text-white text-2xl font-bold"
                style={{ backgroundColor: primaryColor }}
              >
                {companyName.charAt(0)}
              </div>
            )}
            <h2 className="text-2xl font-bold text-gray-900">{companyName}</h2>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Check your email</h3>
              <p className="text-gray-600 mb-6">
                If an account exists for <span className="font-medium">{email}</span>, we've sent a password reset link.
              </p>
              <p className="text-sm text-gray-500 mb-6">
                Didn't receive the email? Check your spam folder or try again.
              </p>
              <div className="space-y-3">
                <button
                  onClick={() => {
                    setSubmitted(false);
                    setEmail('');
                  }}
                  className="w-full py-3 px-4 rounded-lg text-white font-medium transition-all hover:opacity-90"
                  style={{ backgroundColor: primaryColor }}
                >
                  Try another email
                </button>
                <Link
                  to="/login"
                  className="block w-full py-3 px-4 rounded-lg border border-gray-300 text-gray-700 font-medium transition-all hover:bg-gray-50 text-center"
                >
                  Back to login
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          {logoUrl ? (
            <img src={logoUrl} alt={companyName} className="h-16 mx-auto mb-4" />
          ) : (
            <div
              className="w-16 h-16 rounded-xl mx-auto mb-4 flex items-center justify-center text-white text-2xl font-bold"
              style={{ backgroundColor: primaryColor }}
            >
              {companyName.charAt(0)}
            </div>
          )}
          <h2 className="text-2xl font-bold text-gray-900">{companyName}</h2>
          <p className="mt-2 text-gray-600">Reset your password</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <p className="text-sm text-gray-600 text-center mb-4">
              Enter your email address and we'll send you a link to reset your password.
            </p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
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
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none"
                placeholder="you@company.com"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !email}
              className="w-full py-3 px-4 rounded-lg text-white font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
              style={{ backgroundColor: primaryColor }}
            >
              {submitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Sending...
                </span>
              ) : (
                'Send reset link'
              )}
            </button>

            <div className="text-center">
              <Link
                to="/login"
                className="text-sm hover:underline"
                style={{ color: primaryColor }}
              >
                Back to login
              </Link>
            </div>
          </form>
        </div>

        <p className="mt-8 text-center text-sm text-gray-500">
          Need help? Contact your administrator.
        </p>
      </div>
    </div>
  );
}
