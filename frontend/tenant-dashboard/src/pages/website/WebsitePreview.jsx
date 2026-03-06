import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { websiteBuilderApi } from '../../services/api';
import { useTheme } from '../../context/ThemeContext';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import {
  EyeIcon,
  PencilSquareIcon,
  ArrowPathIcon,
  ComputerDesktopIcon,
  DevicePhoneMobileIcon,
  DeviceTabletIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  GlobeAltIcon,
  ExclamationTriangleIcon,
  SwatchIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

const DEVICE_MODES = [
  { id: 'desktop', icon: ComputerDesktopIcon, width: '100%', label: 'Desktop' },
  { id: 'tablet', icon: DeviceTabletIcon, width: '768px', label: 'Tablet' },
  { id: 'mobile', icon: DevicePhoneMobileIcon, width: '375px', label: 'Mobile' },
];

// Error types for different fallback UI
const ERROR_TYPES = {
  NONE: null,
  NO_WEBSITE: 'no_website',
  SERVICE_UNAVAILABLE: 'service_unavailable',
};

export default function WebsitePreview() {
  const { branding } = useTheme();
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [preview, setPreview] = useState(null);
  const [deviceMode, setDeviceMode] = useState('desktop');
  const [errorType, setErrorType] = useState(ERROR_TYPES.NONE);
  const [errorMessage, setErrorMessage] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);

  useEffect(() => {
    loadPreview();
  }, []);

  async function loadPreview() {
    setLoading(true);
    setErrorType(ERROR_TYPES.NONE);
    setErrorMessage(null);

    try {
      // First check if the Website Builder service is available
      const healthResponse = await websiteBuilderApi.health();

      if (!healthResponse.data?.available) {
        setErrorType(ERROR_TYPES.SERVICE_UNAVAILABLE);
        setErrorMessage('The Website Builder service is not available.');
        return;
      }

      // Get website config (same endpoint as Overview for consistent status)
      const response = await websiteBuilderApi.getWebsiteConfig();

      // Check if we got valid data
      if (!response.data || response.data.error) {
        // No website configured for this tenant
        setErrorType(ERROR_TYPES.NO_WEBSITE);
        return;
      }

      setPreview(response.data);
    } catch (err) {
      console.error('Failed to load preview:', err);

      // Determine error type based on the error
      const status = err.response?.status;
      const errorBody = err.response?.data?.error || err.response?.data?.message || '';

      if (status === 404 || status === 403 || errorBody.toLowerCase().includes('not found')) {
        // 403 from website builder means tenant not provisioned (it returns 403 instead of 404)
        setErrorType(ERROR_TYPES.NO_WEBSITE);
      } else {
        setErrorType(ERROR_TYPES.SERVICE_UNAVAILABLE);
        setErrorMessage(err.message || 'Failed to connect to Website Builder.');
      }
    } finally {
      setLoading(false);
    }
  }

  async function handlePublish() {
    setConfirmAction('publish');
  }

  async function handleUnpublish() {
    setConfirmAction('unpublish');
  }

  async function confirmPublishAction() {
    const action = confirmAction;
    setConfirmAction(null);
    setPublishing(true);
    setErrorMessage(null);
    try {
      if (action === 'publish') {
        await websiteBuilderApi.publishWebsite();
      } else {
        await websiteBuilderApi.unpublishWebsite();
      }
      await loadPreview();
    } catch (err) {
      console.error(`${action} failed:`, err);
      const detail = err.response?.data?.error || err.response?.data?.message || err.message;
      setErrorMessage(detail ? `Failed to ${action}: ${detail}` : `Failed to ${action} website`);
    } finally {
      setPublishing(false);
    }
  }

  const editorUrl = websiteBuilderApi.getEditorUrl('home', { theme: branding?.preset_theme });
  const embedPreviewUrl = websiteBuilderApi.getEmbedPreviewUrl();
  const selectedDevice = DEVICE_MODES.find(d => d.id === deviceMode);
  const isPublished = preview?.status === 'published';
  const hasWebsite = preview && !errorType;

  // Loading state
  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-[600px] bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Website Preview</h1>
          <p className="text-gray-500">
            {hasWebsite
              ? `Preview your website before publishing${preview?.template ? ` - Template: ${preview.template.name || preview.template}` : ''}`
              : 'Create and preview your travel website'
            }
          </p>
        </div>
        {hasWebsite && (
          <div className="flex items-center gap-3">
            <button onClick={loadPreview} className="btn-secondary flex items-center gap-2">
              <ArrowPathIcon className="w-4 h-4" />
              Refresh
            </button>
            <a
              href={editorUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary flex items-center gap-2"
            >
              <PencilSquareIcon className="w-4 h-4" />
              Open Editor
            </a>
            {isPublished ? (
              <button
                onClick={handleUnpublish}
                disabled={publishing}
                className="btn-secondary text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                {publishing ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <ExclamationTriangleIcon className="w-4 h-4" />}
                Unpublish
              </button>
            ) : (
              <button
                onClick={handlePublish}
                disabled={publishing}
                className="btn-primary flex items-center gap-2"
              >
                {publishing ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <CloudArrowUpIcon className="w-4 h-4" />}
                Publish Website
              </button>
            )}
          </div>
        )}
      </div>

      {/* Temporary error message */}
      {errorMessage && errorType !== ERROR_TYPES.SERVICE_UNAVAILABLE && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {errorMessage}
        </div>
      )}

      {/* No Website CTA */}
      {errorType === ERROR_TYPES.NO_WEBSITE && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <GlobeAltIcon className="w-10 h-10 text-purple-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Build Your First Website
          </h2>
          <p className="text-gray-500 max-w-md mx-auto mb-8">
            Create a stunning travel website in minutes. Choose a template, customize your branding, and start attracting customers.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/website/templates"
              className="btn-primary flex items-center gap-2"
            >
              <SwatchIcon className="w-5 h-5" />
              Choose Template
            </Link>
            <a
              href={editorUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary flex items-center gap-2"
            >
              <PencilSquareIcon className="w-5 h-5" />
              Open Editor
            </a>
          </div>
        </div>
      )}

      {/* Service Unavailable Error */}
      {errorType === ERROR_TYPES.SERVICE_UNAVAILABLE && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="w-20 h-20 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <ExclamationCircleIcon className="w-10 h-10 text-amber-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-3">
            Preview Temporarily Unavailable
          </h2>
          <p className="text-gray-500 max-w-md mx-auto mb-8">
            The Website Builder service may be restarting or experiencing issues. Please try again in a moment.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={loadPreview}
              className="btn-primary flex items-center gap-2"
            >
              <ArrowPathIcon className="w-5 h-5" />
              Retry
            </button>
            <a
              href={editorUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary flex items-center gap-2"
            >
              <PencilSquareIcon className="w-5 h-5" />
              Open Editor
            </a>
          </div>
        </div>
      )}

      {/* Device Mode Selector - Always visible but disabled when no website */}
      <div className={`flex items-center justify-center gap-2 bg-gray-100 rounded-lg p-1 w-fit mx-auto ${!hasWebsite ? 'opacity-50' : ''}`}>
        {DEVICE_MODES.map(mode => (
          <button
            key={mode.id}
            onClick={() => hasWebsite && setDeviceMode(mode.id)}
            disabled={!hasWebsite}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              deviceMode === mode.id
                ? 'bg-white text-purple-700 shadow'
                : 'text-gray-600 hover:text-gray-900'
            } ${!hasWebsite ? 'cursor-not-allowed' : ''}`}
          >
            <mode.icon className="w-4 h-4" />
            {mode.label}
          </button>
        ))}
      </div>

      {/* Website exists - show full preview UI */}
      {hasWebsite && (
        <>
          {/* Status Banner */}
          <div className={`rounded-xl p-4 flex items-center justify-between ${
            isPublished ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'
          }`}>
            <div className="flex items-center gap-3">
              {isPublished ? (
                <>
                  <CheckCircleIcon className="w-6 h-6 text-green-600" />
                  <div>
                    <p className="font-medium text-green-800">Website is Live</p>
                    <p className="text-sm text-green-600">Your website is published and accessible to visitors</p>
                  </div>
                </>
              ) : (
                <>
                  <EyeIcon className="w-6 h-6 text-yellow-600" />
                  <div>
                    <p className="font-medium text-yellow-800">Draft Mode</p>
                    <p className="text-sm text-yellow-600">Your website is not yet published</p>
                  </div>
                </>
              )}
            </div>
            {isPublished && preview?.url && (
              <a
                href={preview.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-green-700 hover:text-green-800 font-medium"
              >
                <GlobeAltIcon className="w-5 h-5" />
                View Live Site
              </a>
            )}
          </div>

          {/* Preview Frame */}
          <div className="bg-gray-100 rounded-xl p-6 flex justify-center">
            <div
              className="bg-white rounded-lg shadow-xl overflow-hidden transition-all duration-300"
              style={{
                width: selectedDevice.width,
                maxWidth: '100%',
              }}
            >
              {/* Embed standalone Website Builder preview in iframe */}
              <div className="relative" style={{ height: 'calc(100vh - 350px)', minHeight: '500px' }}>
                <iframe
                  src={embedPreviewUrl}
                  className="w-full h-full border-0"
                  title="Website Preview"
                  sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                />
                {/* Overlay for non-published sites */}
                {!isPublished && (
                  <div className="absolute bottom-0 left-0 right-0 bg-gray-800/90 text-white text-xs py-2 px-4 text-center">
                    Preview Mode - Click "Publish Website" to make your site live
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Last Updated */}
          {preview?.updatedAt && (
            <p className="text-center text-sm text-gray-500">
              Last updated: {new Date(preview.updatedAt).toLocaleString()}
            </p>
          )}
        </>
      )}

      <ConfirmDialog
        open={!!confirmAction}
        title={confirmAction === 'publish' ? 'Publish Website' : 'Unpublish Website'}
        message={confirmAction === 'publish'
          ? 'Publish your website? This will make it live to the public.'
          : 'Unpublish your website? It will no longer be accessible to visitors.'}
        confirmLabel={confirmAction === 'publish' ? 'Publish' : 'Unpublish'}
        confirmVariant={confirmAction === 'publish' ? 'primary' : 'warning'}
        onConfirm={confirmPublishAction}
        onCancel={() => setConfirmAction(null)}
        loading={publishing}
      />
    </div>
  );
}
