import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import {
  DocumentTextIcon,
  UsersIcon,
  BuildingOffice2Icon,
  MapPinIcon,
  ArrowTrendingUpIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import { dashboardApi, quotesApi } from '../services/api';

function StatCard({ title, value, icon: Icon, href, loading }) {
  return (
    <Link to={href} className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          {loading ? (
            <div className="h-8 w-16 bg-gray-200 rounded animate-pulse mt-1"></div>
          ) : (
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          )}
        </div>
        <div className="p-3 bg-purple-100 rounded-lg">
          <Icon className="w-6 h-6 text-purple-600" />
        </div>
      </div>
    </Link>
  );
}

function QuickAction({ title, description, href, icon: Icon }) {
  return (
    <Link
      to={href}
      className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
    >
      <div className="p-2 bg-white rounded-lg shadow-sm">
        <Icon className="w-5 h-5 text-purple-600" />
      </div>
      <div>
        <p className="font-medium text-gray-900">{title}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
    </Link>
  );
}

export default function Dashboard() {
  const { clientInfo } = useApp();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  // Single API call for ALL dashboard data
  const loadDashboard = async () => {
    try {
      const response = await dashboardApi.getAll();
      if (response.data?.success) {
        setDashboardData(response.data.data);
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const stats = dashboardData?.stats || { total_quotes: 0, active_clients: 0, total_hotels: 0, total_destinations: 0 };
  const recentQuotes = dashboardData?.recent_quotes || [];
  const usage = dashboardData?.usage || {};

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return `R ${Number(amount).toLocaleString()}`;
  };

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="card gradient-purple text-white">
        <h2 className="text-2xl font-bold">Welcome back!</h2>
        <p className="text-purple-100 mt-1">
          Here's what's happening with {clientInfo?.client_name || 'your business'} today.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Quotes"
          value={stats.total_quotes}
          icon={DocumentTextIcon}
          href="/quotes"
          loading={loading}
        />
        <StatCard
          title="Active Clients"
          value={stats.active_clients}
          icon={UsersIcon}
          href="/crm/clients"
          loading={loading}
        />
        <StatCard
          title="Hotels"
          value={stats.total_hotels}
          icon={BuildingOffice2Icon}
          href="/pricing/hotels"
          loading={loading}
        />
        <StatCard
          title="Destinations"
          value={stats.total_destinations}
          icon={MapPinIcon}
          href="/pricing/rates"
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction
              title="Generate Quote"
              description="Create a new travel quote"
              href="/quotes/new"
              icon={PlusIcon}
            />
            <QuickAction
              title="Start Chat"
              description="Handle customer inquiry"
              href="/chat"
              icon={UsersIcon}
            />
            <QuickAction
              title="View Pipeline"
              description="Check CRM pipeline"
              href="/crm/pipeline"
              icon={ArrowTrendingUpIcon}
            />
          </div>
        </div>

        {/* Recent Quotes */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Recent Quotes</h3>
            <Link to="/quotes" className="text-sm text-purple-600 hover:text-purple-700">
              View all →
            </Link>
          </div>
          <div className="space-y-2">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
                ))}
              </div>
            ) : recentQuotes.length > 0 ? (
              recentQuotes.map((quote) => (
                <Link
                  key={quote.quote_id}
                  to={`/quotes/${quote.quote_id}`}
                  onMouseEnter={() => quotesApi.prefetch(quote.quote_id)}
                  className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                >
                  <div>
                    <p className="font-medium text-gray-900">{quote.customer_name}</p>
                    <p className="text-sm text-gray-500">{quote.destination}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-gray-900">
                      {formatCurrency(quote.total_price)}
                    </p>
                    <p className="text-xs text-gray-500">{quote.quote_id?.slice(0, 8)}</p>
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-gray-500 text-center py-8">No quotes yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Usage Stats */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage Today</h3>
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-100 rounded animate-pulse"></div>
            ))}
          </div>
        ) : usage && Object.keys(usage).length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(usage).map(([key, data]) => (
              <div key={key} className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 capitalize">{key.replace('_', ' ')}</p>
                <p className="text-xl font-bold text-gray-900">
                  {data.current} / {data.limit}
                </p>
                <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-600 rounded-full"
                    style={{ width: `${Math.min((data.current / data.limit) * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">No usage data available</p>
        )}
      </div>
    </div>
  );
}
