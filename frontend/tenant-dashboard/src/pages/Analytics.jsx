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
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  BanknotesIcon,
  UserPlusIcon,
} from '@heroicons/react/24/outline';

// Icon style configurations - using theme colors with subtle backgrounds
const iconStyles = {
  primary: 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]',
  secondary: 'bg-[var(--color-secondary)]/10 text-[var(--color-secondary)]',
  success: 'bg-[var(--color-success)]/10 text-[var(--color-success)]',
  warning: 'bg-[var(--color-warning)]/10 text-[var(--color-warning)]',
  error: 'bg-[var(--color-error)]/10 text-[var(--color-error)]',
  accent: 'bg-[var(--color-accent)]/10 text-[var(--color-accent)]',
  info: 'bg-[var(--color-info)]/10 text-[var(--color-info)]',
};

// Stat card with theme-aware styling
function StatCard({ title, value, change, changeType, icon: Icon, prefix = '', suffix = '', variant = 'primary' }) {
  const isPositive = changeType === 'positive';
  const isNeutral = changeType === 'neutral';
  const TrendIcon = isPositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon;

  return (
    <div className="bg-theme-surface border border-theme rounded-xl p-5 transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-theme-muted font-medium">{title}</p>
          <p className="text-2xl font-bold text-theme mt-1">
            {prefix}{value}{suffix}
          </p>
          {change !== undefined && change !== null && !isNeutral && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${isPositive ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
              <TrendIcon className="w-4 h-4" />
              <span>{change}% vs last period</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-xl ${iconStyles[variant]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

// Simple bar chart component with theme colors and tooltips
function BarChart({ data, valueKey = 'value', labelKey = 'label', variant = 'primary' }) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  if (!data || data.length === 0) {
    return <p className="text-theme-muted text-center py-8">No data available</p>;
  }

  const maxValue = Math.max(...data.map(d => d[valueKey] || 0), 1);

  // Map variant to CSS variable
  const colorVar = {
    primary: 'var(--color-primary)',
    secondary: 'var(--color-secondary)',
    accent: 'var(--color-accent)',
    success: 'var(--color-success)',
  }[variant] || 'var(--color-primary)';

  return (
    <div className="space-y-3">
      {data.map((item, idx) => (
        <div
          key={idx}
          className="flex items-center gap-3 relative group"
          onMouseEnter={() => setHoveredIndex(idx)}
          onMouseLeave={() => setHoveredIndex(null)}
        >
          <span className="text-sm text-theme-secondary w-28 text-right truncate" title={item[labelKey]}>
            {item[labelKey]}
          </span>
          <div className="flex-1 bg-theme-border-light rounded-full h-6 overflow-hidden relative">
            <div
              className="h-full rounded-full transition-all duration-500 hover:opacity-80 cursor-pointer"
              style={{
                width: `${(item[valueKey] / maxValue) * 100}%`,
                backgroundColor: colorVar
              }}
            />
            {/* Tooltip */}
            {hoveredIndex === idx && (
              <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-10 bg-theme-surface-elevated text-theme text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg border border-theme">
                <div className="font-semibold">{item[labelKey]}</div>
                <div className="text-theme-muted">Value: {typeof item[valueKey] === 'number' ? item[valueKey].toLocaleString() : item[valueKey]}</div>
              </div>
            )}
          </div>
          <span className="text-sm font-medium text-theme w-16 text-right">
            {typeof item[valueKey] === 'number' ? item[valueKey].toLocaleString() : item[valueKey]}
          </span>
        </div>
      ))}
    </div>
  );
}

// Format date for display (e.g., "Jan 08" or "08")
function formatChartDate(dateStr, showMonth = true) {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      // If not a valid date, try to extract day
      const parts = dateStr.split('-');
      return parts[parts.length - 1];
    }
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const day = date.getDate().toString().padStart(2, '0');
    if (showMonth) {
      return `${months[date.getMonth()]} ${day}`;
    }
    return day;
  } catch {
    return dateStr?.split('-').slice(-1)[0] || '';
  }
}

// Trend chart (vertical bars) with theme colors, tooltips, and Y-axis
function TrendChart({ data, valueKey = 'count', labelKey = 'date', variant = 'primary', title = 'quotes' }) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  if (!data || data.length === 0) {
    return <p className="text-theme-muted text-center py-8">No trend data available</p>;
  }

  const maxValue = Math.max(...data.map(d => d[valueKey] || 0), 1);
  const totalValue = data.reduce((sum, d) => sum + (d[valueKey] || 0), 0);
  const height = 100;
  const displayData = data.slice(-14); // Show last 14 days

  const colorVar = {
    primary: 'var(--color-primary)',
    secondary: 'var(--color-secondary)',
    accent: 'var(--color-accent)',
  }[variant] || 'var(--color-primary)';

  // Calculate Y-axis labels (0, mid, max)
  const yAxisLabels = [maxValue, Math.round(maxValue / 2), 0];

  return (
    <div className="space-y-2">
      {/* Summary */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-theme-muted">Last {displayData.length} days</span>
        <span className="text-theme font-medium">Total: {totalValue.toLocaleString()}</span>
      </div>

      <div className="relative h-40 flex">
        {/* Y-axis labels */}
        <div className="flex flex-col justify-between py-1 pr-2 text-xs text-theme-muted w-8 shrink-0">
          {yAxisLabels.map((val, i) => (
            <span key={i} className="text-right">{val}</span>
          ))}
        </div>

        {/* Chart area */}
        <div className="flex-1 relative border-l border-b border-theme-border">
          {/* Horizontal grid lines */}
          <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
            {[0, 1, 2].map(i => (
              <div key={i} className="w-full border-t border-theme-border/30" />
            ))}
          </div>

          {/* Bars */}
          <div className="absolute inset-0 flex items-end justify-between gap-0.5 px-1 pt-2 pb-6">
            {displayData.map((item, idx) => (
              <div
                key={idx}
                className="flex-1 flex flex-col items-center min-w-0 relative group"
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                {/* Tooltip */}
                {hoveredIndex === idx && (
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-20 bg-theme-surface-elevated text-theme text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg border border-theme">
                    <div className="font-semibold">{item[valueKey]?.toLocaleString() || 0} {title}</div>
                    <div className="text-theme-muted">{formatChartDate(item[labelKey], true)}</div>
                  </div>
                )}
                <div
                  className="w-full rounded-t transition-all duration-300 hover:opacity-80 min-h-[2px] cursor-pointer"
                  style={{
                    height: `${Math.max((item[valueKey] / maxValue) * height, 2)}px`,
                    backgroundColor: colorVar
                  }}
                />
              </div>
            ))}
          </div>

          {/* X-axis labels */}
          <div className="absolute bottom-0 left-0 right-0 flex justify-between px-1 h-5">
            {displayData.map((item, idx) => (
              <span
                key={idx}
                className="flex-1 text-[10px] text-theme-muted text-center truncate"
              >
                {/* Show month only on first, middle, and last item */}
                {formatChartDate(item[labelKey], idx === 0 || idx === Math.floor(displayData.length / 2) || idx === displayData.length - 1)}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Pipeline pie chart visualization (full circle)
function PipelineDonut({ data, currency = 'USD' }) {
  const [hoveredStage, setHoveredStage] = useState(null);

  if (!data || data.length === 0) {
    return <p className="text-theme-muted text-center py-8">No pipeline data</p>;
  }

  const stageConfig = {
    QUOTED: { color: 'var(--color-primary)', label: 'Quoted' },
    NEGOTIATING: { color: 'var(--color-warning)', label: 'Negotiating' },
    BOOKED: { color: 'var(--color-accent)', label: 'Booked' },
    PAID: { color: 'var(--color-success)', label: 'Paid' },
    TRAVELLED: { color: 'var(--color-info)', label: 'Travelled' },
    LOST: { color: 'var(--color-error)', label: 'Lost' },
  };

  const filteredData = data.filter(d => d.stage !== 'LOST');
  const total = filteredData.reduce((sum, d) => sum + (d.count || 0), 0);

  // Calculate pie segments
  let currentAngle = -90; // Start from top
  const segments = filteredData.map(stage => {
    const percentage = total > 0 ? (stage.count / total) * 100 : 0;
    const angle = (percentage / 100) * 360;
    const segment = {
      ...stage,
      startAngle: currentAngle,
      endAngle: currentAngle + angle,
      percentage,
      config: stageConfig[stage.stage] || stageConfig.QUOTED,
    };
    currentAngle += angle;
    return segment;
  });

  // SVG pie chart helper - create arc path
  const createArcPath = (startAngle, endAngle, radius, cx, cy) => {
    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const x1 = cx + radius * Math.cos(startRad);
    const y1 = cy + radius * Math.sin(startRad);
    const x2 = cx + radius * Math.cos(endRad);
    const y2 = cy + radius * Math.sin(endRad);
    const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;

    return `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
  };

  const size = 200;
  const radius = size / 2 - 10;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <div className="flex items-center gap-6">
      {/* Pie Chart */}
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size}>
          {segments.map((segment, idx) => {
            // Handle 100% case (full circle)
            if (segment.percentage >= 99.9) {
              return (
                <circle
                  key={idx}
                  cx={cx}
                  cy={cy}
                  r={radius}
                  fill={segment.config.color}
                  className="transition-all duration-300 cursor-pointer"
                  style={{ opacity: hoveredStage === null || hoveredStage === segment.stage ? 1 : 0.6 }}
                  onMouseEnter={() => setHoveredStage(segment.stage)}
                  onMouseLeave={() => setHoveredStage(null)}
                />
              );
            }

            if (segment.percentage === 0) return null;

            return (
              <path
                key={idx}
                d={createArcPath(segment.startAngle, segment.endAngle, radius, cx, cy)}
                fill={segment.config.color}
                className="transition-all duration-300 cursor-pointer"
                style={{
                  opacity: hoveredStage === null || hoveredStage === segment.stage ? 1 : 0.6,
                  transform: hoveredStage === segment.stage ? 'scale(1.02)' : 'scale(1)',
                  transformOrigin: `${cx}px ${cy}px`
                }}
                onMouseEnter={() => setHoveredStage(segment.stage)}
                onMouseLeave={() => setHoveredStage(null)}
              />
            );
          })}
          {/* Small center circle for visual polish */}
          <circle cx={cx} cy={cy} r={radius * 0.35} fill="var(--color-surface)" />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-bold text-theme">{total}</span>
          <span className="text-xs text-theme-muted">Total</span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex-1 space-y-2">
        {segments.map((segment, idx) => (
          <div
            key={idx}
            className={`flex items-center justify-between p-2 rounded-lg transition-colors cursor-pointer ${
              hoveredStage === segment.stage ? 'bg-theme-surface-elevated' : ''
            }`}
            onMouseEnter={() => setHoveredStage(segment.stage)}
            onMouseLeave={() => setHoveredStage(null)}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: segment.config.color }}
              />
              <span className="text-sm text-theme-secondary">{segment.config.label}</span>
            </div>
            <div className="text-right">
              <span className="text-sm font-medium text-theme">{segment.count}</span>
              <span className="text-xs text-theme-muted ml-2">({segment.percentage.toFixed(0)}%)</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Invoice aging component with theme colors
function AgingChart({ aging, currency }) {
  const formatCurrency = (amount) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(0)}K`;
    return amount.toLocaleString();
  };

  const segments = [
    { label: 'Current', value: aging?.current || 0, color: 'var(--color-success)' },
    { label: '1-30 days', value: aging?.['30_days'] || 0, color: 'var(--color-warning)' },
    { label: '31-60 days', value: aging?.['60_days'] || 0, color: 'var(--color-accent)' },
    { label: '60+ days', value: aging?.['90_plus_days'] || 0, color: 'var(--color-error)' },
  ];

  const total = segments.reduce((sum, s) => sum + s.value, 0);

  return (
    <div className="space-y-4">
      {/* Stacked bar */}
      <div className="h-8 flex rounded-full overflow-hidden bg-theme-border-light">
        {segments.map((seg, idx) => (
          seg.value > 0 && (
            <div
              key={idx}
              className="transition-all duration-500"
              style={{
                width: `${(seg.value / Math.max(total, 1)) * 100}%`,
                backgroundColor: seg.color
              }}
              title={`${seg.label}: ${currency} ${formatCurrency(seg.value)}`}
            />
          )
        ))}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-3">
        {segments.map((seg, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: seg.color }}
            />
            <span className="text-sm text-theme-secondary">{seg.label}</span>
            <span className="text-sm font-medium text-theme ml-auto">
              {currency} {formatCurrency(seg.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Summary card for invoices and calls - professional styling
function SummaryCard({ label, value, variant = 'default' }) {
  const variants = {
    default: 'border-theme-border',
    success: 'border-l-4 border-l-[var(--color-success)]',
    warning: 'border-l-4 border-l-[var(--color-warning)]',
    error: 'border-l-4 border-l-[var(--color-error)]',
    info: 'border-l-4 border-l-[var(--color-info)]',
    primary: 'border-l-4 border-l-[var(--color-primary)]',
  };

  const textColors = {
    default: 'text-theme',
    success: 'text-[var(--color-success)]',
    warning: 'text-[var(--color-warning)]',
    error: 'text-[var(--color-error)]',
    info: 'text-[var(--color-info)]',
    primary: 'text-[var(--color-primary)]',
  };

  return (
    <div className={`bg-theme-surface rounded-lg p-4 border border-theme ${variants[variant]}`}>
      <p className="text-sm text-theme-muted">{label}</p>
      <p className={`text-xl font-bold mt-1 ${textColors[variant]}`}>{value}</p>
    </div>
  );
}

// Pipeline stage card with left border accent
function PipelineStageCard({ stage, value, count, currency }) {
  const stageConfig = {
    QUOTED: { color: 'var(--color-primary)', label: 'Quoted' },
    NEGOTIATING: { color: 'var(--color-warning)', label: 'Negotiating' },
    BOOKED: { color: 'var(--color-accent)', label: 'Booked' },
    PAID: { color: 'var(--color-success)', label: 'Paid' },
    TRAVELLED: { color: 'var(--color-info)', label: 'Travelled' },
    LOST: { color: 'var(--color-error)', label: 'Lost' },
  };

  const config = stageConfig[stage] || stageConfig.QUOTED;

  const formatCurrency = (amount) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(0)}K`;
    return amount.toLocaleString();
  };

  return (
    <div
      className="bg-theme-surface rounded-lg p-4 border-l-4 border border-theme"
      style={{ borderLeftColor: config.color }}
    >
      <p className="text-sm font-medium" style={{ color: config.color }}>{config.label}</p>
      <p className="text-xl font-bold text-theme mt-1">
        {currency} {formatCurrency(value || 0)}
      </p>
      <p className="text-xs text-theme-muted mt-1">{count} clients</p>
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
  const [pipelineAnalytics, setPipelineAnalytics] = useState(null);

  const currency = clientInfo?.currency || 'USD';

  useEffect(() => {
    loadAnalytics();
  }, [period]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const [dashRes, quoteRes, invoiceRes, pipelineRes] = await Promise.all([
        dashboardApi.getStats(period).catch(() => ({ data: { data: null } })),
        analyticsApi.getQuoteAnalytics(period).catch(() => ({ data: { data: null } })),
        analyticsApi.getInvoiceAnalytics(period).catch(() => ({ data: { data: null } })),
        analyticsApi.getPipelineAnalytics().catch(() => ({ data: { data: null } })),
      ]);

      setDashboardStats(dashRes.data?.data || null);
      setQuoteAnalytics(quoteRes.data?.data || null);
      setInvoiceAnalytics(invoiceRes.data?.data || null);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-theme-muted">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-theme">Analytics</h1>
          <p className="text-theme-muted mt-1">Track your business performance</p>
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
          variant="primary"
        />
        <StatCard
          title="Conversion Rate"
          value={dashboardStats?.quotes?.conversion_rate || 0}
          suffix="%"
          icon={ArrowTrendingUpIcon}
          variant="success"
        />
        <StatCard
          title="Revenue Collected"
          value={formatCurrency(dashboardStats?.revenue?.collected || 0)}
          icon={BanknotesIcon}
          variant="success"
        />
        <StatCard
          title="Outstanding"
          value={formatCurrency(dashboardStats?.revenue?.outstanding || 0)}
          icon={ClockIcon}
          variant={dashboardStats?.revenue?.overdue > 0 ? 'error' : 'warning'}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Clients"
          value={dashboardStats?.clients?.active || 0}
          icon={UsersIcon}
          variant="primary"
        />
        <StatCard
          title="New Clients"
          value={dashboardStats?.clients?.new || 0}
          icon={UserPlusIcon}
          variant="accent"
        />
        <StatCard
          title="Accepted Quotes"
          value={dashboardStats?.quotes?.accepted || 0}
          icon={CheckCircleIcon}
          variant="success"
        />
        <StatCard
          title="Pending Quotes"
          value={dashboardStats?.quotes?.pending || 0}
          icon={ClockIcon}
          variant="warning"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quote Trend */}
        <div className="bg-theme-surface border border-theme rounded-xl p-6">
          <h3 className="text-lg font-semibold text-theme mb-4">Quotes Over Time</h3>
          <TrendChart
            data={quoteAnalytics?.trend || []}
            valueKey="count"
            labelKey="date"
            variant="primary"
          />
        </div>

        {/* Quotes by Destination */}
        <div className="bg-theme-surface border border-theme rounded-xl p-6">
          <h3 className="text-lg font-semibold text-theme mb-4">Quotes by Destination</h3>
          <BarChart
            data={(quoteAnalytics?.by_destination || []).map(d => ({
              label: d.destination,
              value: d.count
            }))}
            variant="secondary"
          />
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quote Status */}
        <div className="bg-theme-surface border border-theme rounded-xl p-6">
          <h3 className="text-lg font-semibold text-theme mb-4">Quotes by Status</h3>
          <BarChart
            data={Object.entries(quoteAnalytics?.by_status || {}).map(([status, data]) => ({
              label: status.charAt(0).toUpperCase() + status.slice(1),
              value: data.count
            }))}
            variant="accent"
          />
        </div>

        {/* Pipeline Donut */}
        <div className="bg-theme-surface border border-theme rounded-xl p-6">
          <h3 className="text-lg font-semibold text-theme mb-4">Sales Pipeline</h3>
          <PipelineDonut data={pipelineAnalytics?.funnel || []} currency={currency} />
        </div>
      </div>

      {/* Invoice Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Invoice Summary */}
        <div className="bg-theme-surface border border-theme rounded-xl p-6">
          <h3 className="text-lg font-semibold text-theme mb-4">Invoice Summary</h3>
          <div className="grid grid-cols-2 gap-4">
            <SummaryCard
              label="Total Invoiced"
              value={formatCurrency(invoiceAnalytics?.summary?.total_value || 0)}
              variant="primary"
            />
            <SummaryCard
              label="Paid"
              value={formatCurrency(invoiceAnalytics?.summary?.paid_value || 0)}
              variant="success"
            />
            <SummaryCard
              label="Outstanding"
              value={formatCurrency(invoiceAnalytics?.summary?.outstanding_value || 0)}
              variant="warning"
            />
            <SummaryCard
              label="Overdue"
              value={formatCurrency(invoiceAnalytics?.summary?.overdue_value || 0)}
              variant="error"
            />
          </div>
          <div className="mt-4 pt-4 border-t border-theme">
            <div className="flex justify-between items-center">
              <span className="text-sm text-theme-muted">Payment Rate</span>
              <span className="text-lg font-semibold text-theme">
                {invoiceAnalytics?.summary?.payment_rate || 0}%
              </span>
            </div>
          </div>
        </div>

        {/* Invoice Aging */}
        <div className="bg-theme-surface border border-theme rounded-xl p-6">
          <h3 className="text-lg font-semibold text-theme mb-4">Accounts Receivable Aging</h3>
          <AgingChart aging={invoiceAnalytics?.aging} currency={currency} />
        </div>
      </div>

      {/* Top Hotels */}
      <div className="bg-theme-surface border border-theme rounded-xl p-6">
        <h3 className="text-lg font-semibold text-theme mb-4">Top Hotels by Quotes</h3>
        <BarChart
          data={(quoteAnalytics?.by_hotel || []).slice(0, 5).map(h => ({
            label: h.hotel,
            value: h.count
          }))}
          variant="success"
        />
      </div>

      {/* Pipeline Value Summary */}
      <div className="bg-theme-surface border border-theme rounded-xl p-6">
        <h3 className="text-lg font-semibold text-theme mb-4">Pipeline Value by Stage</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {(pipelineAnalytics?.funnel || []).map((stage, idx) => (
            <PipelineStageCard
              key={idx}
              stage={stage.stage}
              value={stage.value}
              count={stage.count}
              currency={currency}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
