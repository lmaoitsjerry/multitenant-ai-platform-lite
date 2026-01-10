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
import { tenantsApi, usageApi, systemApi } from '../services/api';

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
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [healthRes, tenantsRes, usageRes] = await Promise.all([
        systemApi.getHealth(),
        tenantsApi.listSummary(),
        usageApi.getSummary('month'),
      ]);

      setHealth(healthRes.data);
      setTenants(tenantsRes.data?.tenants || []);
      setUsage(usageRes.data);
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
          value={tenants.length}
          icon={BuildingOffice2Icon}
          href="/tenants"
          loading={loading}
        />
        <StatCard
          title="Total Revenue (Month)"
          value={formatCurrency(usage?.totals?.total_revenue)}
          icon={CurrencyDollarIcon}
          href="/usage"
          loading={loading}
          color="green"
        />
        <StatCard
          title="Quotes Generated"
          value={usage?.totals?.total_quotes || 0}
          icon={DocumentTextIcon}
          loading={loading}
          color="blue"
        />
        <StatCard
          title="Active Users"
          value={usage?.totals?.total_active_users || 0}
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
                  key={tenant.client_id}
                  to={`/tenants/${tenant.client_id}`}
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
                      <p className="text-sm text-gray-500">{tenant.client_id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {tenant.vapi_configured && (
                      <span className="badge badge-success">VAPI</span>
                    )}
                    {tenant.sendgrid_configured && (
                      <span className="badge badge-info">Email</span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Usage by Tenant */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Usage by Tenant (This Month)</h3>
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
          ) : usage?.by_tenant?.length > 0 ? (
            <div className="space-y-3">
              {usage.by_tenant.map((tenantUsage) => (
                <div
                  key={tenantUsage.client_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-gray-900">{tenantUsage.client_id}</p>
                    <p className="text-sm text-gray-500">
                      {tenantUsage.quotes_generated} quotes • {tenantUsage.invoices_paid} paid
                    </p>
                  </div>
                  <p className="font-bold text-green-600">
                    {formatCurrency(tenantUsage.total_revenue)}
                  </p>
                </div>
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
