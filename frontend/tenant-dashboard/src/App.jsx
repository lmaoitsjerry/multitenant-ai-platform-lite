import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Suspense, lazy, useEffect, useMemo } from 'react';
import { AppProvider } from './context/AppContext';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/layout/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { warmCache, prefetchForRoute } from './services/api';

// Skeleton loaders for instant visual feedback
function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Welcome card skeleton */}
      <div className="h-24 bg-purple-100 rounded-xl"></div>
      {/* Stats grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-white rounded-xl p-6 border border-gray-200">
            <div className="flex justify-between">
              <div className="space-y-2">
                <div className="h-4 w-20 bg-gray-200 rounded"></div>
                <div className="h-8 w-16 bg-gray-200 rounded"></div>
              </div>
              <div className="h-12 w-12 bg-gray-200 rounded-lg"></div>
            </div>
          </div>
        ))}
      </div>
      {/* Content skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-200 h-64"></div>
        <div className="bg-white rounded-xl p-6 border border-gray-200 h-64 lg:col-span-2"></div>
      </div>
    </div>
  );
}

function ListPageSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="h-8 w-32 bg-gray-200 rounded"></div>
        <div className="h-10 w-28 bg-gray-200 rounded-lg"></div>
      </div>
      {/* Filters */}
      <div className="flex gap-3">
        <div className="h-10 w-64 bg-gray-200 rounded-lg"></div>
        <div className="h-10 w-32 bg-gray-200 rounded-lg"></div>
      </div>
      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="h-12 bg-gray-50 border-b"></div>
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-16 border-b border-gray-100 px-4 flex items-center gap-4">
            <div className="h-4 w-32 bg-gray-200 rounded"></div>
            <div className="h-4 w-24 bg-gray-200 rounded"></div>
            <div className="h-4 w-20 bg-gray-200 rounded flex-1"></div>
            <div className="h-6 w-16 bg-gray-200 rounded-full"></div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PipelineSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="flex justify-between items-center">
        <div className="h-8 w-40 bg-gray-200 rounded"></div>
        <div className="flex gap-2">
          <div className="h-10 w-10 bg-gray-200 rounded-lg"></div>
          <div className="h-10 w-10 bg-gray-200 rounded-lg"></div>
        </div>
      </div>
      <div className="grid grid-cols-6 gap-4">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="bg-gray-100 rounded-xl p-4 min-h-96">
            <div className="h-6 w-20 bg-gray-200 rounded mb-4"></div>
            <div className="space-y-3">
              {[1, 2, 3].map(j => (
                <div key={j} className="h-24 bg-white rounded-lg border"></div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SettingsSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-24 bg-gray-200 rounded"></div>
      <div className="flex gap-2 border-b pb-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-10 w-24 bg-gray-200 rounded-lg"></div>
        ))}
      </div>
      <div className="bg-white rounded-xl p-6 border border-gray-200 space-y-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="space-y-2">
            <div className="h-4 w-24 bg-gray-200 rounded"></div>
            <div className="h-10 w-full bg-gray-200 rounded-lg"></div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Generic loading fallback
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  );
}

// Route-aware skeleton loader
function RouteSkeleton() {
  const location = useLocation();
  const path = location.pathname;

  const skeleton = useMemo(() => {
    if (path === '/' || path === '/dashboard') return <DashboardSkeleton />;
    if (path === '/crm/pipeline') return <PipelineSkeleton />;
    if (path === '/settings') return <SettingsSkeleton />;
    if (path.includes('/quotes') || path.includes('/invoices') || path.includes('/clients') || path.includes('/pricing')) {
      return <ListPageSkeleton />;
    }
    return <PageLoader />;
  }, [path]);

  return skeleton;
}

// Cache warmer - runs once when user is authenticated
function CacheWarmer() {
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      // Warm cache in background
      warmCache();
    }
  }, [user]);

  return null;
}

// Route prefetcher - prefetches data for upcoming navigation
function RoutePrefetcher() {
  const location = useLocation();

  useEffect(() => {
    // Prefetch data for the current route
    prefetchForRoute(location.pathname);
  }, [location.pathname]);

  return null;
}

// Auth pages (public)
const Login = lazy(() => import('./pages/Login'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const AcceptInvite = lazy(() => import('./pages/AcceptInvite'));

// Admin pages (public - uses admin token auth)
const TenantOnboarding = lazy(() => import('./pages/admin/TenantOnboarding'));

// Lazy load pages - only load when needed
const Dashboard = lazy(() => import('./pages/Dashboard'));

// Quotes
const QuotesList = lazy(() => import('./pages/quotes/QuotesList'));
const QuoteDetail = lazy(() => import('./pages/quotes/QuoteDetail'));
const GenerateQuote = lazy(() => import('./pages/quotes/GenerateQuote'));

// CRM
const Pipeline = lazy(() => import('./pages/crm/Pipeline'));
const ClientsList = lazy(() => import('./pages/crm/ClientsList'));
const ClientDetail = lazy(() => import('./pages/crm/ClientDetail'));

// Invoices
const InvoicesList = lazy(() => import('./pages/invoices/InvoicesList'));
const InvoiceDetail = lazy(() => import('./pages/invoices/InvoiceDetail'));

// Pricing
const PricingRates = lazy(() => import('./pages/pricing/PricingRates'));
const PricingHotels = lazy(() => import('./pages/pricing/PricingHotels'));
const HotelDetail = lazy(() => import('./pages/pricing/HotelDetail'));

// Helpdesk
const Helpdesk = lazy(() => import('./pages/Helpdesk'));

// Other
const Analytics = lazy(() => import('./pages/Analytics'));
const Settings = lazy(() => import('./pages/Settings'));

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppProvider>
          <Router>
            <CacheWarmer />
            <RoutePrefetcher />
            <Routes>
              {/* Public routes - no auth required */}
              <Route path="/login" element={
                <Suspense fallback={<PageLoader />}>
                  <Login />
                </Suspense>
              } />
              <Route path="/forgot-password" element={
                <Suspense fallback={<PageLoader />}>
                  <ForgotPassword />
                </Suspense>
              } />
              <Route path="/accept-invite" element={
                <Suspense fallback={<PageLoader />}>
                  <AcceptInvite />
                </Suspense>
              } />
              <Route path="/admin/onboarding" element={
                <Suspense fallback={<PageLoader />}>
                  <TenantOnboarding />
                </Suspense>
              } />
              <Route path="/onboard" element={
                <Suspense fallback={<PageLoader />}>
                  <TenantOnboarding />
                </Suspense>
              } />

              {/* Protected routes - require auth */}
              <Route path="/*" element={
                <ProtectedRoute>
                  <Layout>
                    <Suspense fallback={<RouteSkeleton />}>
                      <Routes>
                        {/* Dashboard */}
                        <Route path="/" element={<Dashboard />} />

                        {/* Quotes */}
                        <Route path="/quotes" element={<QuotesList />} />
                        <Route path="/quotes/new" element={<GenerateQuote />} />
                        <Route path="/quotes/:id" element={<QuoteDetail />} />

                        {/* CRM */}
                        <Route path="/crm/pipeline" element={<Pipeline />} />
                        <Route path="/crm/clients" element={<ClientsList />} />
                        <Route path="/crm/clients/:id" element={<ClientDetail />} />

                        {/* Invoices */}
                        <Route path="/invoices" element={<InvoicesList />} />
                        <Route path="/invoices/:id" element={<InvoiceDetail />} />

                        {/* Pricing */}
                        <Route path="/pricing/rates" element={<PricingRates />} />
                        <Route path="/pricing/hotels" element={<PricingHotels />} />
                        <Route path="/pricing/hotels/:hotelName" element={<HotelDetail />} />

                        {/* Helpdesk */}
                        <Route path="/helpdesk" element={<Helpdesk />} />

                        {/* Analytics */}
                        <Route path="/analytics" element={<Analytics />} />

                        {/* Settings */}
                        <Route path="/settings" element={<Settings />} />

                        {/* Fallback */}
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Routes>
                    </Suspense>
                  </Layout>
                </ProtectedRoute>
              } />
            </Routes>
          </Router>
        </AppProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;