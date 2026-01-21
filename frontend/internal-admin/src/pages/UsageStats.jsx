import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowPathIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';
import { analyticsApi } from '../services/api';

export default function UsageStats() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [topTenants, setTopTenants] = useState([]);

  useEffect(() => {
    loadUsage();
  }, []);

  const loadUsage = async () => {
    try {
      setLoading(true);
      const [overviewRes, topTenantsRes] = await Promise.all([
        analyticsApi.getOverview(),
        analyticsApi.getTopTenants('revenue', 20),
      ]);
      setOverview(overviewRes.data?.data || overviewRes.data);
      setTopTenants(topTenantsRes.data?.data || []);
    } catch (error) {
      console.error('Failed to load usage:', error);
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
          <h1 className="text-2xl font-bold text-gray-900">Usage Statistics</h1>
          <p className="text-gray-500 mt-1">Platform usage across all tenants (this month)</p>
        </div>
        <button onClick={loadUsage} className="btn-secondary flex items-center gap-2">
          <ArrowPathIcon className="w-5 h-5" />
          Refresh
        </button>
      </div>

      {/* Totals */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-20 bg-gray-100 rounded"></div>
            </div>
          ))}
        </div>
      ) : overview && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <TotalCard
            title="Revenue (This Month)"
            value={formatCurrency(overview.revenue_this_month)}
            subtitle={`${overview.invoices_paid_this_month || 0} paid invoices`}
            icon={CurrencyDollarIcon}
            color="green"
          />
          <TotalCard
            title="Quotes Generated"
            value={overview.quotes_this_month || 0}
            subtitle={`${overview.total_tenants || 0} active tenants`}
            icon={DocumentTextIcon}
            color="blue"
          />
          <TotalCard
            title="Total Invoices"
            value={overview.total_invoices || 0}
            subtitle={`${overview.invoices_paid_this_month || 0} paid this month`}
            icon={ChartBarIcon}
            color="purple"
          />
          <TotalCard
            title="Total Users"
            value={overview.total_users || 0}
            subtitle={`${overview.total_crm_clients || 0} CRM clients`}
            icon={UsersIcon}
            color="orange"
          />
        </div>
      )}

      {/* Usage by Tenant Table */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Top Tenants by Revenue
        </h3>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
            ))}
          </div>
        ) : topTenants?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Tenant</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Quotes</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Invoices</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Paid</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Revenue</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Users</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Clients</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {topTenants.map((tenant) => (
                    <tr key={tenant.tenant_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <Link
                          to={`/tenants/${tenant.tenant_id}`}
                          className="font-medium text-zorah-600 hover:text-zorah-700"
                        >
                          {tenant.company_name || tenant.tenant_id}
                        </Link>
                        <p className="text-xs text-gray-400">{tenant.tenant_id}</p>
                      </td>
                      <td className="px-4 py-3 text-right">{tenant.quotes_count || 0}</td>
                      <td className="px-4 py-3 text-right">{tenant.invoices_count || 0}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-green-600 font-medium">{tenant.invoices_paid || 0}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-bold text-green-600">
                          {formatCurrency(tenant.total_revenue)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">{tenant.users_count || 0}</td>
                      <td className="px-4 py-3 text-right">{tenant.clients_count || 0}</td>
                    </tr>
                  ))}
              </tbody>
              {overview && (
                <tfoot className="bg-gray-50 border-t-2 border-gray-200">
                  <tr>
                    <td className="px-4 py-3 font-bold">Platform Total</td>
                    <td className="px-4 py-3 text-right font-bold">{overview.quotes_this_month || 0}</td>
                    <td className="px-4 py-3 text-right font-bold">{overview.total_invoices || 0}</td>
                    <td className="px-4 py-3 text-right font-bold text-green-600">
                      {overview.invoices_paid_this_month || 0}
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-green-600">
                      {formatCurrency(overview.revenue_this_month)}
                    </td>
                    <td className="px-4 py-3 text-right font-bold">{overview.total_users || 0}</td>
                    <td className="px-4 py-3 text-right font-bold">{overview.total_crm_clients || 0}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No usage data available</p>
        )}
      </div>

      {/* Revenue Comparison */}
      {topTenants?.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Revenue Comparison</h3>
          <div className="space-y-4">
            {topTenants.map((tenant) => {
                const maxRevenue = Math.max(...topTenants.map(t => t.total_revenue || 0));
                const percentage = maxRevenue > 0 ? ((tenant.total_revenue || 0) / maxRevenue) * 100 : 0;

                return (
                  <div key={tenant.tenant_id}>
                    <div className="flex items-center justify-between mb-1">
                      <Link
                        to={`/tenants/${tenant.tenant_id}`}
                        className="font-medium text-gray-900 hover:text-zorah-600"
                      >
                        {tenant.company_name || tenant.tenant_id}
                      </Link>
                      <span className="font-bold text-green-600">
                        {formatCurrency(tenant.total_revenue)}
                      </span>
                    </div>
                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-zorah-500 to-zorah-600 rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}

function TotalCard({ title, value, subtitle, icon: Icon, color }) {
  const colorClasses = {
    green: 'bg-green-100 text-green-600',
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className={`text-2xl font-bold mt-1 ${color === 'green' ? 'text-green-600' : 'text-gray-900'}`}>
            {value}
          </p>
          {subtitle && <p className="text-sm text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
