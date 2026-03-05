import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

/**
 * Banner for degraded service notifications.
 * Renders when API response contains _service_status metadata from the backend
 * circuit breaker (CircuitBreakerState.response_metadata).
 *
 * Usage:
 *   {serviceStatus?.degraded && <DegradedServiceBanner status={serviceStatus} />}
 */
export default function DegradedServiceBanner({ status }) {
  if (!status?.degraded) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 mb-4">
      <div className="flex items-center gap-2">
        <ExclamationTriangleIcon className="w-4 h-4 text-amber-600 flex-shrink-0" />
        <p className="text-sm text-amber-800">
          {status.message || 'Some features are temporarily limited. Showing cached results.'}
        </p>
      </div>
    </div>
  );
}
