import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import {
  DocumentTextIcon,
  UsersIcon,
  BuildingOffice2Icon,
  MapPinIcon,
  ArrowTrendingUpIcon,
  PlusIcon,
  ArrowPathIcon,
  SparklesIcon,
  RocketLaunchIcon,
  SunIcon,
  MoonIcon,
} from '@heroicons/react/24/outline';
import { dashboardApi, quotesApi, pricingApi } from '../services/api';

// Dynamic welcome messages
const WELCOME_MESSAGES = [
  { greeting: "Let's make today great!", icon: SparklesIcon, subtext: "Your next booking is waiting" },
  { greeting: "Ready to close some deals?", icon: RocketLaunchIcon, subtext: "Check your pipeline for hot leads" },
  { greeting: "Great things ahead!", icon: SparklesIcon, subtext: "Time to create amazing travel experiences" },
  { greeting: "Let's get productive!", icon: RocketLaunchIcon, subtext: "Your dashboard is ready" },
  { greeting: "Another day, another adventure!", icon: SparklesIcon, subtext: "Help your clients explore the world" },
  { greeting: "Time to shine!", icon: SparklesIcon, subtext: "Your customers are counting on you" },
  { greeting: "Let's make it happen!", icon: RocketLaunchIcon, subtext: "Today's quotes could be tomorrow's bookings" },
];

// Get time-based greeting
const getTimeGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return { text: "Good morning", icon: SunIcon };
  if (hour < 17) return { text: "Good afternoon", icon: SunIcon };
  if (hour < 21) return { text: "Good evening", icon: MoonIcon };
  return { text: "Working late?", icon: MoonIcon };
};

// Cache configuration
const CACHE_KEY = 'dashboard_data_cache';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes - show cached data immediately
const STALE_TTL = 30 * 60 * 1000; // 30 minutes - data is still usable but refresh in background

function StatCard({ title, value, icon: Icon, href, loading, notice, isStale }) {
  return (
    <Link to={href} className="card card-hover relative">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-theme-muted">{title}</p>
          {loading ? (
            <div className="h-8 w-16 bg-theme-surface-elevated rounded animate-pulse mt-1"></div>
          ) : (
            <p className="text-2xl font-bold text-theme mt-1">{value}</p>
          )}
          {notice && (
            <p className="text-xs text-theme-muted mt-1">{notice}</p>
          )}
        </div>
        <div className="p-3 bg-theme-primary/10 rounded-lg">
          <Icon className="w-6 h-6 text-theme-primary" />
        </div>
      </div>
      {isStale && (
        <div className="absolute top-2 right-2">
          <ArrowPathIcon className="w-3 h-3 text-theme-muted animate-spin" />
        </div>
      )}
    </Link>
  );
}

function QuickAction({ title, description, href, icon: Icon }) {
  return (
    <Link
      to={href}
      className="flex items-center gap-4 p-4 bg-theme-surface-elevated rounded-lg hover:bg-theme-border-light transition-colors"
    >
      <div className="p-2 bg-theme-surface rounded-lg shadow-sm">
        <Icon className="w-5 h-5 text-theme-primary" />
      </div>
      <div>
        <p className="font-medium text-theme">{title}</p>
        <p className="text-sm text-theme-muted">{description}</p>
      </div>
    </Link>
  );
}

export default function Dashboard() {
  const { clientInfo } = useApp();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isStale, setIsStale] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Select random welcome message on mount (stable for session)
  const welcomeMessage = useMemo(() => {
    return WELCOME_MESSAGES[Math.floor(Math.random() * WELCOME_MESSAGES.length)];
  }, []);

  // Get time-based greeting
  const timeGreeting = useMemo(() => getTimeGreeting(), []);

  // Load cached data on mount, then fetch fresh data
  useEffect(() => {
    const cached = getCachedData();
    if (cached) {
      setDashboardData(cached.data);
      setLoading(false);

      // If cache is fresh enough, don't refetch immediately
      const age = Date.now() - cached.timestamp;
      if (age < CACHE_TTL) {
        return; // Cache is fresh, no need to refetch
      }

      // Cache is stale but usable - show indicator and refresh in background
      if (age < STALE_TTL) {
        setIsStale(true);
        loadDashboard(true); // Background refresh
        return;
      }
    }

    // No cache or cache too old - fetch with loading state
    loadDashboard(false);
  }, []);

  // Get cached data from localStorage
  const getCachedData = () => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        return JSON.parse(cached);
      }
    } catch (e) {
      // Ignore localStorage errors
    }
    return null;
  };

  // Save data to localStorage cache
  const setCachedData = (data) => {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        data,
        timestamp: Date.now()
      }));
    } catch (e) {
      // Ignore localStorage errors
    }
  };

  // Fetch pricing stats as fallback when dashboard returns 0
  const fetchPricingStats = async () => {
    try {
      const [hotelsRes, destinationsRes] = await Promise.all([
        pricingApi.listHotels(),
        pricingApi.listDestinations()
      ]);

      return {
        hotels: hotelsRes.data?.count || hotelsRes.data?.data?.length || 0,
        destinations: destinationsRes.data?.count || destinationsRes.data?.data?.length || 0
      };
    } catch {
      return { hotels: 0, destinations: 0 };
    }
  };

  // Fetch dashboard data from API
  const loadDashboard = useCallback(async (isBackgroundRefresh = false) => {
    if (!isBackgroundRefresh) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const response = await dashboardApi.getAll();
      if (response.data?.success && response.data?.data) {
        let data = response.data.data;

        // Fallback: If hotels/destinations are 0, try fetching from pricing API directly
        if (data.stats?.total_hotels === 0 || data.stats?.total_destinations === 0) {
          const pricingStats = await fetchPricingStats();
          if (pricingStats.hotels > 0 || pricingStats.destinations > 0) {
            data = {
              ...data,
              stats: {
                ...data.stats,
                total_hotels: pricingStats.hotels || data.stats.total_hotels,
                total_destinations: pricingStats.destinations || data.stats.total_destinations
              }
            };
          }
        }

        setDashboardData(data);
        setCachedData(data);
        setIsStale(false);
      } else if (!dashboardData) {
        // Only set defaults if we don't already have data
        setDashboardData({
          stats: { total_quotes: 0, active_clients: 0, total_hotels: 0, total_destinations: 0 },
          recent_quotes: [],
          usage: {}
        });
      }
    } catch (error) {
      // On error, only set defaults if we don't have any data
      if (!dashboardData) {
        setDashboardData({
          stats: { total_quotes: 0, active_clients: 0, total_hotels: 0, total_destinations: 0 },
          recent_quotes: [],
          usage: {}
        });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
      setIsStale(false);
    }
  }, [dashboardData]);

  // Manual refresh handler
  const handleRefresh = () => {
    if (!refreshing) {
      loadDashboard(true);
    }
  };

  // Stats from API response (defaults set in loadDashboard if API fails)
  const stats = dashboardData?.stats;
  const recentQuotes = dashboardData?.recent_quotes || [];
  const usage = dashboardData?.usage || {};

  // Currency formatting with symbol based on configured currency
  const currencySymbols = { ZAR: 'R', USD: '$', EUR: '€', GBP: '£' };
  const currencyCode = clientInfo?.currency || 'ZAR';
  const currencySymbol = currencySymbols[currencyCode] || currencyCode;

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return `${currencySymbol} ${Number(amount).toLocaleString()}`;
  };

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="card gradient-purple text-white">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white/10 rounded-xl hidden sm:block">
              <timeGreeting.icon className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold">{timeGreeting.text}!</h2>
              </div>
              <p className="text-purple-100 mt-1 text-lg flex items-center gap-2">
                <welcomeMessage.icon className="w-5 h-5 inline" />
                {welcomeMessage.greeting}
              </p>
              <p className="text-purple-200 text-sm mt-2">
                {welcomeMessage.subtext} {clientInfo?.client_name ? `at ${clientInfo.client_name}` : ''}
              </p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors disabled:opacity-50"
            title="Refresh dashboard"
          >
            <ArrowPathIcon className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Quotes"
          value={stats?.total_quotes ?? 0}
          icon={DocumentTextIcon}
          href="/quotes"
          loading={loading}
          isStale={isStale || refreshing}
        />
        <StatCard
          title="Active Clients"
          value={stats?.active_clients ?? 0}
          icon={UsersIcon}
          href="/crm/clients"
          loading={loading}
          isStale={isStale || refreshing}
        />
        <StatCard
          title="Hotels"
          value={stats?.total_hotels ?? 0}
          icon={BuildingOffice2Icon}
          href="/pricing/hotels"
          loading={loading}
          isStale={isStale || refreshing}
          notice={!loading && stats?.total_hotels === 0 ? "View pricing guide →" : null}
        />
        <StatCard
          title="Destinations"
          value={stats?.total_destinations ?? 0}
          icon={MapPinIcon}
          href="/pricing/rates"
          loading={loading}
          isStale={isStale || refreshing}
          notice={!loading && stats?.total_destinations === 0 ? "View pricing guide →" : null}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="card">
          <h3 className="text-lg font-semibold text-theme mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction
              title="Generate Quote"
              description="Create a new travel quote"
              href="/quotes/new"
              icon={PlusIcon}
            />
            <QuickAction
              title="Add Client"
              description="Add a new client to CRM"
              href="/crm/clients"
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
            <h3 className="text-lg font-semibold text-theme">Recent Quotes</h3>
            <Link to="/quotes" className="text-sm text-theme-primary hover:text-theme-primary-dark">
              View all →
            </Link>
          </div>
          <div className="space-y-2">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-16 bg-theme-surface-elevated rounded animate-pulse"></div>
                ))}
              </div>
            ) : recentQuotes.length > 0 ? (
              recentQuotes.map((quote) => (
                <Link
                  key={quote.quote_id}
                  to={`/quotes/${quote.quote_id}`}
                  onMouseEnter={() => quotesApi.prefetch(quote.quote_id)}
                  className="flex items-center justify-between p-3 hover:bg-theme-surface-elevated rounded-lg transition-colors"
                >
                  <div>
                    <p className="font-medium text-theme">{quote.customer_name}</p>
                    <p className="text-sm text-theme-muted">{quote.destination}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-theme">
                      {formatCurrency(quote.total_price)}
                    </p>
                    <p className="text-xs text-theme-muted">{quote.quote_id?.slice(0, 8)}</p>
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-theme-muted text-center py-8">No quotes yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Usage Stats */}
      <div className="card">
        <h3 className="text-lg font-semibold text-theme mb-4">Usage Today</h3>
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-theme-surface-elevated rounded animate-pulse"></div>
            ))}
          </div>
        ) : usage && Object.keys(usage).length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(usage).map(([key, data]) => (
              <div key={key} className="p-4 bg-theme-surface-elevated rounded-lg">
                <p className="text-sm text-theme-muted capitalize">{key.replace('_', ' ')}</p>
                <p className="text-xl font-bold text-theme">
                  {data.current} / {data.limit}
                </p>
                <div className="mt-2 h-2 bg-theme-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-theme-primary rounded-full"
                    style={{ width: `${Math.min((data.current / data.limit) * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-theme-muted text-center py-4">No usage data available</p>
        )}
      </div>
    </div>
  );
}
