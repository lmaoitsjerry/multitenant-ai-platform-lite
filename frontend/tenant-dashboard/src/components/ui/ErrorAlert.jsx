import { ExclamationTriangleIcon, XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

/**
 * Inline error alert component.
 * Shows error messages within the page context with optional retry and dismiss.
 *
 * Usage:
 *   {error && <ErrorAlert message={error} onDismiss={clearError} onRetry={refetch} />}
 */
export default function ErrorAlert({ message, onDismiss, onRetry, className = '' }) {
  return (
    <div className={`rounded-lg border border-red-200 bg-red-50 p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <ExclamationTriangleIcon className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-red-800">{message}</p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {onRetry && (
            <button
              onClick={onRetry}
              className="p-1 text-red-500 hover:text-red-700 transition-colors"
              title="Retry"
            >
              <ArrowPathIcon className="w-4 h-4" />
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 text-red-400 hover:text-red-600 transition-colors"
              title="Dismiss"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
