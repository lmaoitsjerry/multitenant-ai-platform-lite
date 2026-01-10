import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowPathIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';
import { usageApi } from '../services/api';

export default function UsageStats() {
  const [loading, setLoading] = useState(true);
  const [usage, setUsage] = useState(null);
  const [period, setPeriod] = useState('month');

  useEffect(() => {
    loadUsage();
  }, [period]);

  const loadUsage = async () => {
    try {
      setLoading(true);
      const response = await usageApi.getSummary(period);
      setUsage(response.data);
    } catch (error) {
      console.error('Failed to load usage:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => `R ${Number(amount || 0).toLocaleString()}`;

  const periodLabels = {
    day: 'Today',
    week: 'This Week',
    month: 'This Month',
    quarter: 'This Quarter',
    year: 'This Year',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usage Statistics</h1>
          <p className="text-gray-500 mt-1">Platform usage across all tenants</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="input w-40"
          >
            <option value="day">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
          </select>
          <button onClick={loadUsage} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
        </div>
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
      ) : usage?.totals && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <TotalCard
            title="Total Revenue"
            value={formatCurrency(usage.totals.total_revenue)}
            subtitle={`${usage.totals.total_invoices_paid} paid invoices`}
            icon={CurrencyDollarIcon}
            color="green"
          />
          <TotalCard
            title="Quotes Generated"
            value={usage.totals.total_quotes}
            subtitle={`${usage.totals.tenant_count} active tenants`}
            icon={DocumentTextIcon}
            color="blue"
          />
          <TotalCard
            title="Invoices Created"
            value={usage.totals.total_invoices}
            subtitle={`${usage.totals.total_invoices_paid} paid`}
            icon={ChartBarIcon}
            color="purple"
          />
          <TotalCard
            title="Active Users"
            value={usage.totals.total_active_users}
            subtitle={`${usage.totals.total_crm_clients} CRM clients`}
            icon={UsersIcon}
            color="orange"
          />
        </div>
      )}

      {/* Usage by Tenant Table */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Usage by Tenant - {periodLabels[period]}
        </h3>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
            ))}
          </div>
        ) : usage?.by_tenant?.length > 0 ? (
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
                {usage.by_tenant
                  .sort((a, b) => b.total_revenue - a.total_revenue)
                  .map((tenantUsage) => (
                    <tr key={tenantUsage.client_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <Link
                          to={`/tenants/${tenantUsage.client_id}`}
                          className="font-medium text-zorah-600 hover:text-zorah-700"
                        >
                          {tenantUsage.client_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right">{tenantUsage.quotes_generated}</td>
                      <td className="px-4 py-3 text-right">{tenantUsage.invoices_created}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-green-600 font-medium">{tenantUsage.invoices_paid}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-bold text-green-600">
                          {formatCurrency(tenantUsage.total_revenue)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">{tenantUsage.active_users}</td>
                      <td className="px-4 py-3 text-right">{tenantUsage.total_clients}</td>
                    </tr>
                  ))}
              </tbody>
              <tfoot className="bg-gray-50 border-t-2 border-gray-200">
                <tr>
                  <td className="px-4 py-3 font-bold">Total</td>
                  <td className="px-4 py-3 text-right font-bold">{usage.totals.total_quotes}</td>
                  <td className="px-4 py-3 text-right font-bold">{usage.totals.total_invoices}</td>
                  <td className="px-4 py-3 text-right font-bold text-green-600">
                    {usage.totals.total_invoices_paid}
                  </td>
                  <td className="px-4 py-3 text-right font-bold text-green-600">
                    {formatCurrency(usage.totals.total_revenue)}
                  </td>
                  <td className="px-4 py-3 text-right font-bold">{usage.totals.total_active_users}</td>
                  <td className="px-4 py-3 text-right font-bold">{usage.totals.total_crm_clients}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No usage data available</p>
        )}
      </div>

      {/* Revenue Comparison */}
      {usage?.by_tenant?.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Revenue Comparison</h3>
          <div className="space-y-4">
            {usage.by_tenant
              .sort((a, b) => b.total_revenue - a.total_revenue)
              .map((tenantUsage) => {
                const maxRevenue = Math.max(...usage.by_tenant.map(t => t.total_revenue));
                const percentage = maxRevenue > 0 ? (tenantUsage.total_revenue / maxRevenue) * 100 : 0;

                return (
                  <div key={tenantUsage.client_id}>
                    <div className="flex items-center justify-between mb-1">
                      <Link
                        to={`/tenants/${tenantUsage.client_id}`}
                        className="font-medium text-gray-900 hover:text-zorah-600"
                      >
                        {tenantUsage.client_id}
                      </Link>
                      <span className="font-bold text-green-600">
                        {formatCurrency(tenantUsage.total_revenue)}
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
