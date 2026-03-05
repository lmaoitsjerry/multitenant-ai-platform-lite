import { useState } from 'react';

/**
 * Reusable hook for destructive actions with confirmation state.
 *
 * Usage:
 *   const { showConfirm, setShowConfirm, loading, handleAction } = useDeleteAction({
 *     actionFn: () => crmApi.deleteClient(clientId),
 *     onSuccess: () => { showToast('Deleted'); navigate('/clients'); },
 *     onError: (err) => showToast(err.response?.data?.detail || 'Failed', 'error'),
 *   });
 */
export function useDeleteAction({ actionFn, onSuccess, onError }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleAction = async () => {
    try {
      setLoading(true);
      await actionFn();
      setShowConfirm(false);
      onSuccess?.();
    } catch (error) {
      onError?.(error);
    } finally {
      setLoading(false);
    }
  };

  return { showConfirm, setShowConfirm, loading, handleAction };
}
