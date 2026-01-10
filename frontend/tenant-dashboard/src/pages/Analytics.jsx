import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { dashboardApi, analyticsApi } from '../services/api';
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CurrencyDollarIcon,
  UsersIcon,
  DocumentTextIcon,
  PhoneIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  BanknotesIcon,
} from '@heroicons/react/24/outline';

// Stat card with trend indicator
function StatCard({ title, value, change, changeType, icon: Icon, prefix = '', suffix = '', color = 'purple' }) {
  const isPositive = changeType === 'positive';
  const isNeutral = changeType === 'neutral';
  const TrendIcon = isPositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon;

  const colorClasses = {
    purple: 'bg-purple-100 text-purple-600',
    green: 'bg-green-100 text-green-600',
    blue: 'bg-blue-100 text-blue-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    red: 'bg-red-100 text-red-600',
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {prefix}{value}{suffix}
          </p>
          {change !== undefined && change !== null && !isNeutral && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              <TrendIcon className="w-4 h-4" />
              <span>{change}% vs last period</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

// Simple bar chart component
function BarChart({ data, valueKey = 'value', labelKey = 'label', color = 'purple' }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400 text-center py-8">No data available</p>;
  }

  const maxValue = Math.max(...data.map(d => d[valueKey] || 0), 1);

  const colorClass = {
    purple: 'bg-purple-600',
    blue: 'bg-blue-600',
    green: 'bg-green-600',
  }[color] || 'bg-purple-600';

  return (
    <div className="space-y-3">
      {data.map((item, idx) => (
        <div key={idx} className="flex items-center gap-3">
          <span className="text-sm text-gray-600 w-28 text-right truncate" title={item[labelKey]}>
            {item[labelKey]}
          </span>
          <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
            <div
              className={`h-full ${colorClass} rounded-full transition-all duration-500`}
              style={{ width: `${(item[valueKey] / maxValue) * 100}%` }}
            />
          </div>
          <span className="text-sm font-medium text-gray-900 w-16 text-right">
            {typeof item[valueKey] === 'number' ? item[valueKey].toLocaleString() : item[valueKey]}
          </span>
        </div>
      ))}
    </div>
  );
}

// Trend chart (vertical bars)
function TrendChart({ data, valueKey = 'count', labelKey = 'date' }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400 text-center py-8">No trend data available</p>;
  }

  const maxValue = Math.max(...data.map(d => d[valueKey] || 0), 1);
  const height = 120;

  return (
    <div className="relative h-40">
      <div className="absolute inset-0 flex items-end justify-between gap-1 pt-4">
        {data.slice(-12).map((item, idx) => (
          <div key={idx} className="flex-1 flex flex-col items-center min-w-0">
            <div
              className="w-full bg-purple-500 rounded-t transition-all duration-500 hover:bg-purple-600 min-h-[4px]"
              style={{ height: `${Math.max((item[valueKey] / maxValue) * height, 4)}px` }}
              title={`${item[valueKey]}`}
            />
            <span className="text-xs text-gray-500 mt-2 truncate w-full text-center">
              {item[labelKey]?.split('-').slice(-1)[0] || item[labelKey]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Pipeline funnel visualization
function PipelineFunnel({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400 text-center py-8">No pipeline data</p>;
  }

  const stageColors = {
    QUOTED: 'bg-blue-500',
    NEGOTIATING: 'bg-yellow-500',
    BOOKED: 'bg-purple-500',
    PAID: 'bg-green-500',
    TRAVELLED: 'bg-teal-500',
    LOST: 'bg-red-400',
  };

  const maxCount = Math.max(...data.map(d => d.count), 1);

  return (
    <div className="space-y-3">
      {data.filter(d => d.stage !== 'LOST').map((stage, idx) => (
        <div key={idx} className="flex items-center gap-3">
          <span className="text-sm text-gray-600 w-24">{stage.stage}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-8 overflow-hidden">
            <div
              className={`h-full ${stageColors[stage.stage] || 'bg-gray-500'} rounded-full transition-all duration-500 flex items-center justify-end pr-2`}
              style={{ width: `${Math.max((stage.count / maxCount) * 100, 10)}%` }}
            >
              <span className="text-white text-xs font-medium">{stage.count}</span>
            </div>
          </div>
          <span className="text-sm text-gray-500 w-16 text-right">
            {stage.conversion_rate}%
          </span>
        </div>
      ))}
    </div>
  );
}

// Invoice aging component
function AgingChart({ aging, currency }) {
  const formatCurrency = (amount) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(0)}K`;
    return amount.toLocaleString();
  };

  const segments = [
    { label: 'Current', value: aging?.current || 0, color: 'bg-green-500' },
    { label: '1-30 days', value: aging?.['30_days'] || 0, color: 'bg-yellow-500' },
    { label: '31-60 days', value: aging?.['60_days'] || 0, color: 'bg-orange-500' },
    { label: '60+ days', value: aging?.['90_plus_days'] || 0, color: 'bg-red-500' },
  ];

  const total = segments.reduce((sum, s) => sum + s.value, 0);

  return (
    <div className="space-y-4">
      {/* Stacked bar */}
      <div className="h-8 flex rounded-full overflow-hidden bg-gray-100">
        {segments.map((seg, idx) => (
          seg.value > 0 && (
            <div
              key={idx}
              className={`${seg.color} transition-all duration-500`}
              style={{ width: `${(seg.value / Math.max(total, 1)) * 100}%` }}
              title={`${seg.label}: ${currency} ${formatCurrency(seg.value)}`}
            />
          )
        ))}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-2">
        {segments.map((seg, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${seg.color}`} />
            <span className="text-sm text-gray-600">{seg.label}</span>
            <span className="text-sm font-medium text-gray-900 ml-auto">
              {currency} {formatCurrency(seg.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Analytics() {
  const { clientInfo } = useApp();
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('30d');

  // Data states
  const [dashboardStats, setDashboardStats] = useState(null);
  const [quoteAnalytics, setQuoteAnalytics] = useState(null);
  const [invoiceAnalytics, setInvoiceAnalytics] = useState(null);
  const [callAnalytics, setCallAnalytics] = useState(null);
  const [pipelineAnalytics, setPipelineAnalytics] = useState(null);

  const currency = clientInfo?.currency || 'USD';

  useEffect(() => {
    loadAnalytics();
  }, [period]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const [dashRes, quoteRes, invoiceRes, callRes, pipelineRes] = await Promise.all([
        dashboardApi.getStats(period).catch(() => ({ data: { data: null } })),
        analyticsApi.getQuoteAnalytics(period).catch(() => ({ data: { data: null } })),
        analyticsApi.getInvoiceAnalytics(period).catch(() => ({ data: { data: null } })),
        analyticsApi.getCallAnalytics(period).catch(() => ({ data: { data: null } })),
        analyticsApi.getPipelineAnalytics().catch(() => ({ data: { data: null } })),
      ]);

      setDashboardStats(dashRes.data?.data || null);
      setQuoteAnalytics(quoteRes.data?.data || null);
      setInvoiceAnalytics(invoiceRes.data?.data || null);
      setCallAnalytics(callRes.data?.data || null);
      setPipelineAnalytics(pipelineRes.data?.data || null);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount) return `${currency} 0`;
    if (amount >= 1000000) return `${currency} ${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${currency} ${(amount / 1000).toFixed(0)}K`;
    return `${currency} ${amount.toLocaleString()}`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">Track your business performance</p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="input w-40"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="year">This year</option>
        </select>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Quotes"
          value={dashboardStats?.quotes?.total || 0}
          icon={DocumentTextIcon}
          color="blue"
        />
        <StatCard
          title="Conversion Rate"
          value={dashboardStats?.quotes?.conversion_rate || 0}
          suffix="%"
          icon={ArrowTrendingUpIcon}
          color="green"
        />
        <StatCard
          title="Revenue Collected"
          value={formatCurrency(dashboardStats?.revenue?.collected || 0)}
          icon={BanknotesIcon}
          color="green"
        />
        <StatCard
          title="Outstanding"
          value={formatCurrency(dashboardStats?.revenue?.outstanding || 0)}
          icon={ClockIcon}
          color={dashboardStats?.revenue?.overdue > 0 ? 'red' : 'yellow'}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Clients"
          value={dashboardStats?.clients?.active || 0}
          icon={UsersIcon}
          color="purple"
        />
        <StatCard
          title="New Clients"
          value={dashboardStats?.clients?.new || 0}
          icon={UsersIcon}
          color="blue"
        />
        <StatCard
          title="Calls Completed"
          value={callAnalytics?.summary?.completed || 0}
          icon={PhoneIcon}
          color="green"
        />
        <StatCard
          title="Pending Calls"
          value={(callAnalytics?.queue?.pending || 0) + (callAnalytics?.queue?.scheduled || 0)}
          icon={PhoneIcon}
          color="yellow"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quote Trend */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quotes Over Time</h3>
          <TrendChart
            data={quoteAnalytics?.trend || []}
            valueKey="count"
            labelKey="date"
          />
        </div>

        {/* Quotes by Destination */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quotes by Destination</h3>
          <BarChart
            data={(quoteAnalytics?.by_destination || []).map(d => ({
              label: d.destination,
              value: d.count
            }))}
            color="purple"
          />
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quote Status */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quotes by Status</h3>
          <BarChart
            data={Object.entries(quoteAnalytics?.by_status || {}).map(([status, data]) => ({
              label: status.charAt(0).toUpperCase() + status.slice(1),
              value: data.count
            }))}
            color="blue"
          />
        </div>

        {/* Pipeline Funnel */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sales Pipeline</h3>
          <PipelineFunnel data={pipelineAnalytics?.funnel || []} />
        </div>
      </div>

      {/* Invoice Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Invoice Summary */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Invoice Summary</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Invoiced</p>
              <p className="text-xl font-bold text-gray-900">
                {formatCurrency(invoiceAnalytics?.summary?.total_value || 0)}
              </p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-green-600">Paid</p>
              <p className="text-xl font-bold text-green-700">
                {formatCurrency(invoiceAnalytics?.summary?.paid_value || 0)}
              </p>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg">
              <p className="text-sm text-yellow-600">Outstanding</p>
              <p className="text-xl font-bold text-yellow-700">
                {formatCurrency(invoiceAnalytics?.summary?.outstanding_value || 0)}
              </p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg">
              <p className="text-sm text-red-600">Overdue</p>
              <p className="text-xl font-bold text-red-700">
                {formatCurrency(invoiceAnalytics?.summary?.overdue_value || 0)}
              </p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Payment Rate</span>
              <span className="text-lg font-semibold text-gray-900">
                {invoiceAnalytics?.summary?.payment_rate || 0}%
              </span>
            </div>
          </div>
        </div>

        {/* Invoice Aging */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Accounts Receivable Aging</h3>
          <AgingChart aging={invoiceAnalytics?.aging} currency={currency} />
        </div>
      </div>

      {/* Call Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Call Summary */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Call Performance</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-600">Total Calls</p>
              <p className="text-xl font-bold text-blue-700">
                {callAnalytics?.summary?.total_calls || 0}
              </p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-green-600">Completed</p>
              <p className="text-xl font-bold text-green-700">
                {callAnalytics?.summary?.completed || 0}
              </p>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <p className="text-sm text-purple-600">Success Rate</p>
              <p className="text-xl font-bold text-purple-700">
                {callAnalytics?.summary?.success_rate || 0}%
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Avg Duration</p>
              <p className="text-xl font-bold text-gray-700">
                {formatDuration(callAnalytics?.summary?.avg_duration_seconds || 0)}
              </p>
            </div>
          </div>
        </div>

        {/* Top Hotels */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Hotels by Quotes</h3>
          <BarChart
            data={(quoteAnalytics?.by_hotel || []).slice(0, 5).map(h => ({
              label: h.hotel,
              value: h.count
            }))}
            color="green"
          />
        </div>
      </div>

      {/* Pipeline Value Summary */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Value by Stage</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {(pipelineAnalytics?.funnel || []).map((stage, idx) => {
            const stageColors = {
              QUOTED: { bg: 'bg-blue-50', text: 'text-blue-600', value: 'text-blue-700' },
              NEGOTIATING: { bg: 'bg-yellow-50', text: 'text-yellow-600', value: 'text-yellow-700' },
              BOOKED: { bg: 'bg-purple-50', text: 'text-purple-600', value: 'text-purple-700' },
              PAID: { bg: 'bg-green-50', text: 'text-green-600', value: 'text-green-700' },
              TRAVELLED: { bg: 'bg-teal-50', text: 'text-teal-600', value: 'text-teal-700' },
              LOST: { bg: 'bg-red-50', text: 'text-red-600', value: 'text-red-700' },
            };
            const colors = stageColors[stage.stage] || stageColors.QUOTED;

            return (
              <div key={idx} className={`p-4 rounded-lg ${colors.bg}`}>
                <p className={`text-sm ${colors.text}`}>{stage.stage}</p>
                <p className={`text-lg font-bold ${colors.value}`}>
                  {formatCurrency(stage.value || 0)}
                </p>
                <p className="text-xs text-gray-500 mt-1">{stage.count} clients</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
