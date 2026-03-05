import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { websiteBuilderApi } from '../../services/api';
import {
  ChartBarIcon,
  EyeIcon,
  UsersIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ComputerDesktopIcon,
  PencilSquareIcon,
  GlobeAltIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  SwatchIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';

function StatCard({ label, value, change, icon: Icon, invertChange = false }) {
  const isPositive = invertChange ? (change && change < 0) : (change && change > 0);
  const changeColor = isPositive ? 'text-green-600' : 'text-red-600';
  const ChangeIcon = isPositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 card-hover">
      <div className="flex items-center justify-between mb-4">
        <div className="p-2.5 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-lg">
          <Icon className="w-5 h-5 text-purple-600" />
        </div>
        {change !== undefined && change !== 0 && (
          <div className={`flex items-center gap-1 text-sm font-medium ${changeColor}`}>
            <ChangeIcon className="w-4 h-4" />
            {Math.abs(change)}%
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  );
}

function formatDuration(seconds) {
  if (!seconds) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

export default function WebsiteOverview() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [websiteConfig, setWebsiteConfig] = useState(null);
  const [builderAvailable, setBuilderAvailable] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);

    try {
      // Check if Website Builder is available
      const healthResponse = await websiteBuilderApi.health();
      setBuilderAvailable(healthResponse.data?.available || false);

      if (healthResponse.data?.available) {
        // Load analytics and config in parallel — log failures instead of swallowing
        const [analyticsRes, configRes] = await Promise.all([
          websiteBuilderApi.getAnalyticsSummary('30d').catch((err) => {
            console.warn('Failed to load website analytics:', err.message || err);
            return { data: null };
          }),
          websiteBuilderApi.getWebsiteConfig().catch((err) => {
            console.warn('Failed to load website config:', err.message || err);
            return { data: null };
          }),
        ]);

        // Analytics data is at the root level, not nested under 'summary'
        setAnalytics(analyticsRes.data?.success ? {
          totalVisitors: analyticsRes.data.visitors || 0,
          pageViews: analyticsRes.data.pageViews || 0,
          bounceRate: analyticsRes.data.bounceRate || 0,
          avgSessionDuration: 0,
          visitorsChange: analyticsRes.data.trend?.visitors || 0,
          pageViewsChange: analyticsRes.data.trend?.pageViews || 0,
        } : null);
        setWebsiteConfig(configRes.data || null);
      }
    } catch (err) {
      console.error('Failed to load website data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="grid grid-cols-4 gap-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Website Overview</h1>
          <p className="text-gray-500">Manage your travel website and track performance</p>
        </div>
        <a
          href={websiteBuilderApi.getEditorUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary flex items-center gap-2"
        >
          <PencilSquareIcon className="w-5 h-5" />
          Open Editor
        </a>
      </div>

      {/* Connection Status */}
      {!builderAvailable && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <ExclamationTriangleIcon className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-amber-800">Website Builder Not Connected</h3>
            <p className="text-sm text-amber-700 mt-1">
              The Website Builder service is not available. Please check your configuration or contact support.
            </p>
          </div>
        </div>
      )}

      {/* Website Status Card */}
      {websiteConfig && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl">
                <GlobeAltIcon className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Your Website</h2>
                <p className="text-sm text-gray-500">
                  Template: {websiteConfig.template || 'Not selected'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                websiteConfig.status === 'published'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {websiteConfig.status === 'published' ? (
                  <CheckCircleIcon className="w-4 h-4" />
                ) : (
                  <XCircleIcon className="w-4 h-4" />
                )}
                {websiteConfig.status === 'published' ? 'Published' : 'Draft'}
              </div>
              {websiteConfig.status === 'published' && (
                <a
                  href={websiteBuilderApi.getLiveSiteUrl()}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sm text-green-700 hover:text-green-800 font-medium transition-colors"
                >
                  <GlobeAltIcon className="w-4 h-4" />
                  View Live Site
                </a>
              )}
              <Link to="/website/preview" className="btn-secondary flex items-center gap-2">
                <EyeIcon className="w-4 h-4" />
                Preview
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Live URL Banner */}
      {websiteConfig?.status === 'published' && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <GlobeAltIcon className="w-5 h-5 text-green-600" />
            <div>
              <p className="text-sm font-medium text-green-800">Your website is live</p>
              <a
                href={websiteBuilderApi.getLiveSiteUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-green-600 hover:text-green-700 underline font-mono"
              >
                {websiteBuilderApi.getLiveSiteUrl()}
              </a>
            </div>
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(websiteBuilderApi.getLiveSiteUrl());
            }}
            className="px-3 py-1.5 text-sm text-green-700 hover:bg-green-100 rounded-lg transition-colors font-medium"
          >
            Copy Link
          </button>
        </div>
      )}

      {/* Analytics Stats */}
      {analytics ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            label="Total Visitors"
            value={analytics.totalVisitors?.toLocaleString() || '0'}
            change={analytics.visitorsChange}
            icon={UsersIcon}
          />
          <StatCard
            label="Page Views"
            value={analytics.pageViews?.toLocaleString() || '0'}
            change={analytics.pageViewsChange}
            icon={EyeIcon}
          />
          <StatCard
            label="Bounce Rate"
            value={`${analytics.bounceRate || 0}%`}
            change={analytics.bounceRateChange}
            icon={ChartBarIcon}
            invertChange
          />
          <StatCard
            label="Avg. Session"
            value={formatDuration(analytics.avgSessionDuration)}
            icon={ClockIcon}
          />
        </div>
      ) : builderAvailable ? (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
          <ChartBarIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Analytics Data Yet</h3>
          <p className="text-gray-500">
            Analytics will appear here once your website starts receiving visitors.
          </p>
        </div>
      ) : null}

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          to="/website/templates"
          className="bg-white rounded-xl border border-gray-200 p-6 hover:border-purple-300 transition-all group card-hover"
        >
          <div className="p-3 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-xl w-fit mb-4 group-hover:from-purple-200 group-hover:to-indigo-200 transition-colors">
            <ComputerDesktopIcon className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-1 group-hover:text-purple-700 transition-colors">Templates</h3>
          <p className="text-sm text-gray-500">Choose from beautiful, pre-designed website templates</p>
        </Link>

        <Link
          to="/website/branding"
          className="bg-white rounded-xl border border-gray-200 p-6 hover:border-pink-300 transition-all group card-hover"
        >
          <div className="p-3 bg-gradient-to-br from-pink-100 to-rose-100 rounded-xl w-fit mb-4 group-hover:from-pink-200 group-hover:to-rose-200 transition-colors">
            <SwatchIcon className="w-6 h-6 text-pink-600" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-1 group-hover:text-pink-700 transition-colors">Branding</h3>
          <p className="text-sm text-gray-500">Customize your logo, colors, and fonts</p>
        </Link>

        <Link
          to="/website/bookings"
          className="bg-white rounded-xl border border-gray-200 p-6 hover:border-blue-300 transition-all group card-hover"
        >
          <div className="p-3 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-xl w-fit mb-4 group-hover:from-blue-200 group-hover:to-cyan-200 transition-colors">
            <ClipboardDocumentListIcon className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-1 group-hover:text-blue-700 transition-colors">Bookings</h3>
          <p className="text-sm text-gray-500">View and manage customer booking requests</p>
        </Link>
      </div>
    </div>
  );
}
