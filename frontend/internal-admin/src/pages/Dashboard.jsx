import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BuildingOffice2Icon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  UsersIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline';
import { tenantsApi, analyticsApi, systemApi, getCached, setCached, CACHE_TTL } from '../services/api';

// Cache keys for dashboard data
const CACHE_KEYS = {
  OVERVIEW: 'dashboard_overview',
  TENANTS: 'dashboard_tenants',
  TOP_TENANTS: 'dashboard_top_tenants',
  HEALTH: 'dashboard_health'
};

// Get cached dashboard data for instant display
function getCachedDashboardData() {
  return {
    overview: getCached(CACHE_KEYS.OVERVIEW)?.data || getCached(CACHE_KEYS.OVERVIEW),
    tenants: getCached(CACHE_KEYS.TENANTS)?.data || getCached(CACHE_KEYS.TENANTS)?.tenants || [],
    topTenants: getCached(CACHE_KEYS.TOP_TENANTS)?.data || getCached(CACHE_KEYS.TOP_TENANTS) || [],
    health: getCached(CACHE_KEYS.HEALTH)
  };
}

function StatCard({ title, value, icon: Icon, href, loading, color = 'zorah' }) {
  const content = (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          {loading ? (
            <div className="h-8 w-20 bg-gray-200 rounded animate-pulse mt-1"></div>
          ) : (
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          )}
        </div>
        <div className={`p-3 bg-${color}-100 rounded-lg`}>
          <Icon className={`w-6 h-6 text-${color}-600`} />
        </div>
      </div>
    </div>
  );

  return href ? <Link to={href}>{content}</Link> : content;
}

function HealthIndicator({ status }) {
  const isHealthy = status === 'healthy';
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
      isHealthy ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
    }`}>
      {isHealthy ? (
        <CheckCircleIcon className="w-4 h-4" />
      ) : (
        <ExclamationTriangleIcon className="w-4 h-4" />
      )}
      <span className="text-sm font-medium">{isHealthy ? 'System Healthy' : 'Issues Detected'}</span>
    </div>
  );
}

export default function Dashboard() {
  // Initialize with cached data for instant display
  const cachedData = getCachedDashboardData();
  const [loading, setLoading] = useState(!cachedData.overview);
  const [health, setHealth] = useState(cachedData.health);
  const [tenants, setTenants] = useState(cachedData.tenants);
  const [overview, setOverview] = useState(cachedData.overview);
  const [topTenants, setTopTenants] = useState(cachedData.topTenants);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    // Only show loading if we don't have cached data
    if (!overview) {
      setLoading(true);
    }

    try {
      const [healthRes, tenantsRes, overviewRes, topTenantsRes] = await Promise.all([
        systemApi.getHealth(),
        tenantsApi.listSummary(),
        analyticsApi.getOverview(),
        analyticsApi.getTopTenants('revenue', 5),
      ]);

      // Update state
      const healthData = healthRes.data;
      const tenantsData = tenantsRes.data?.data || tenantsRes.data?.tenants || [];
      const overviewData = overviewRes.data?.data || overviewRes.data;
      const topTenantsData = topTenantsRes.data?.data || [];

      setHealth(healthData);
      setTenants(tenantsData);
      setOverview(overviewData);
      setTopTenants(topTenantsData);

      // Cache the data for next visit
      setCached(CACHE_KEYS.HEALTH, healthData, CACHE_TTL.SHORT);
      setCached(CACHE_KEYS.TENANTS, tenantsData, CACHE_TTL.MEDIUM);
      setCached(CACHE_KEYS.OVERVIEW, overviewData, CACHE_TTL.MEDIUM);
      setCached(CACHE_KEYS.TOP_TENANTS, topTenantsData, CACHE_TTL.MEDIUM);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => `R ${Number(amount || 0).toLocaleString()}`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Zorah AI Platform Overview</p>
        </div>
        <div className="flex items-center gap-4">
          {health && <HealthIndicator status={health.status} />}
          <a
            href="/admin/onboarding"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-zorah-600 text-white rounded-lg hover:bg-zorah-700 transition-colors"
          >
            <PlusCircleIcon className="w-5 h-5" />
            Onboard New Tenant
          </a>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Tenants"
          value={overview?.total_tenants || tenants.length}
          icon={BuildingOffice2Icon}
          href="/tenants"
          loading={loading}
        />
        <StatCard
          title="Revenue (This Month)"
          value={formatCurrency(overview?.revenue_this_month)}
          icon={CurrencyDollarIcon}
          href="/usage"
          loading={loading}
          color="green"
        />
        <StatCard
          title="Quotes (This Month)"
          value={overview?.quotes_this_month || 0}
          icon={DocumentTextIcon}
          loading={loading}
          color="blue"
        />
        <StatCard
          title="Total Users"
          value={overview?.total_users || 0}
          icon={UsersIcon}
          loading={loading}
          color="purple"
        />
      </div>

      {/* Tenants Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tenant List */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Tenants</h3>
            <Link to="/tenants" className="text-sm text-zorah-600 hover:text-zorah-700">
              View all →
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {tenants.slice(0, 5).map((tenant) => (
                <Link
                  key={tenant.tenant_id}
                  to={`/tenants/${tenant.tenant_id}`}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-zorah-100 rounded-lg flex items-center justify-center">
                      <span className="font-bold text-zorah-600">
                        {tenant.company_name?.charAt(0) || 'T'}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{tenant.company_name}</p>
                      <p className="text-sm text-gray-500">{tenant.tenant_id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">
                      {tenant.quote_count || 0} quotes
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Top Tenants by Revenue */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Top Tenants (This Month)</h3>
            <Link to="/usage" className="text-sm text-zorah-600 hover:text-zorah-700">
              Details →
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-gray-100 rounded animate-pulse"></div>
              ))}
            </div>
          ) : topTenants?.length > 0 ? (
            <div className="space-y-3">
              {topTenants.map((tenant) => (
                <Link
                  key={tenant.tenant_id}
                  to={`/tenants/${tenant.tenant_id}`}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div>
                    <p className="font-medium text-gray-900">{tenant.company_name || tenant.tenant_id}</p>
                    <p className="text-sm text-gray-500">
                      {tenant.quotes_count || 0} quotes • {tenant.invoices_paid || 0} paid
                    </p>
                  </div>
                  <p className="font-bold text-green-600">
                    {formatCurrency(tenant.total_revenue)}
                  </p>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No usage data available</p>
          )}
        </div>
      </div>

      {/* System Info */}
      {health && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Status</p>
              <p className={`font-bold ${health.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                {health.status}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Tenants</p>
              <p className="font-bold text-gray-900">{health.total_tenants}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Database</p>
              <p className={`font-bold ${health.database_status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                {health.database_status}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Last Check</p>
              <p className="font-bold text-gray-900 text-sm">
                {new Date(health.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
