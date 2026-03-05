import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Reusable hook for async operations with loading, error, and success states.
 * Prevents state updates on unmounted components.
 *
 * Usage:
 *   const { execute, loading, error, clearError } = useAsyncOperation();
 *
 *   const handleSave = () => execute(
 *     async () => { await api.save(data); },
 *     { errorMessage: 'Failed to save' }
 *   );
 */
export function useAsyncOperation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const execute = useCallback(async (operation, options = {}) => {
    const {
      errorMessage = 'An error occurred',
      onSuccess,
      onError,
      rethrow = false,
    } = options;

    setLoading(true);
    setError(null);

    try {
      const result = await operation();
      if (mountedRef.current) {
        setLoading(false);
        onSuccess?.(result);
      }
      return result;
    } catch (err) {
      if (mountedRef.current) {
        const message = extractErrorMessage(err, errorMessage);
        setError(message);
        setLoading(false);
        onError?.(err, message);
      }
      if (rethrow) throw err;
      return null;
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { execute, loading, error, clearError };
}

/**
 * Extract a user-friendly error message from various error formats.
 * Handles: axios errors, ServiceError responses, plain strings, generic errors.
 */
export function extractErrorMessage(error, fallback = 'An error occurred') {
  if (!error) return fallback;

  // Axios error with API response
  if (error.response?.data) {
    const data = error.response.data;
    // ServiceError format from backend: { detail: { error: "...", service: "..." } }
    if (data.detail?.error) return data.detail.error;
    // Simple detail string
    if (typeof data.detail === 'string') return data.detail;
    // Message field
    if (data.message) return data.message;
    // Error field
    if (data.error) return data.error;
  }

  // Axios network error
  if (error.code === 'ERR_NETWORK') {
    return 'Unable to connect to the server. Please check your connection.';
  }

  // Axios timeout
  if (error.code === 'ECONNABORTED') {
    return 'The request timed out. Please try again.';
  }

  // Standard error
  if (error.message) return error.message;

  // String error
  if (typeof error === 'string') return error;

  return fallback;
}
