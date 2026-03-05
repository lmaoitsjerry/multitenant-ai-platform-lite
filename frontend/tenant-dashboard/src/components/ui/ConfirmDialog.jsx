import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  confirmVariant = 'danger',
  onConfirm,
  onCancel,
  loading = false,
}) {
  if (!open) return null;

  const variantClasses = {
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    warning: 'bg-amber-500 hover:bg-amber-600 text-white',
    primary: 'bg-purple-600 hover:bg-purple-700 text-white',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={loading ? undefined : onCancel}
      />
      <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start gap-4 mb-4">
          <div className={`p-2 rounded-full ${
            confirmVariant === 'danger' ? 'bg-red-100' :
            confirmVariant === 'warning' ? 'bg-amber-100' : 'bg-purple-100'
          }`}>
            <ExclamationTriangleIcon className={`w-6 h-6 ${
              confirmVariant === 'danger' ? 'text-red-600' :
              confirmVariant === 'warning' ? 'text-amber-600' : 'text-purple-600'
            }`} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <p className="text-gray-600 mt-1">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2 rounded-lg transition-colors ${variantClasses[confirmVariant]} ${
              loading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {loading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
