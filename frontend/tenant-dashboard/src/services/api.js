import axios from 'axios';
import axiosRetry from 'axios-retry';

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const TENANT_ID_KEY = 'tenant_id';

// Get tenant ID - priority: localStorage (from onboarding) > env var > default
export const getTenantId = () => {
  return localStorage.getItem(TENANT_ID_KEY) || import.meta.env.VITE_CLIENT_ID || 'example';
};

// Set tenant ID (called after onboarding)
export const setTenantId = (tenantId) => {
  if (tenantId) {
    localStorage.setItem(TENANT_ID_KEY, tenantId);
  }
};

// Clear tenant ID (for switching tenants or logout)
export const clearTenantId = () => {
  localStorage.removeItem(TENANT_ID_KEY);
};

// Create axios instance with default config
// NOTE: Do NOT set default Content-Type here - let axios auto-detect for FormData uploads
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000, // 10 second timeout - prevents infinite hangs
});

// Automatic retry for transient failures
axiosRetry(api, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (error) => {
    // Retry on network errors (no response at all)
    if (!error.response) return true;
    // Retry GET requests on 5xx
    if (error.config?.method === 'get' && error.response.status >= 500) return true;
    // Never retry 4xx
    return false;
  },
});

// Add client ID and auth headers to all requests
api.interceptors.request.use((config) => {
  // TENANT-AGNOSTIC LOGIN: Don't send X-Client-ID for login requests
  // This allows the backend to auto-detect the user's tenant from their email
  // After login, the tenant_id is stored and used for all subsequent requests
  const isLoginRequest = config.url?.includes('/auth/login');

  if (!isLoginRequest) {
    // Add client ID for all non-login requests
    const clientId = getTenantId();
    if (clientId && clientId !== 'example') {
      config.headers['X-Client-ID'] = clientId;
    }
  }

  // Add auth token if available
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }

  // Set Content-Type to JSON only for non-FormData requests
  // FormData needs axios to auto-set Content-Type with multipart boundary
  if (!(config.data instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
  }

  return config;
});

// Response interceptor for handling 401 errors and token refresh
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't retry for login or refresh endpoints
      if (originalRequest.url.includes('/auth/login') ||
          originalRequest.url.includes('/auth/refresh')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue requests while refreshing
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers['Authorization'] = `Bearer ${token}`;
          return api(originalRequest);
        }).catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

      if (!refreshToken) {
        isRefreshing = false;
        // Clear auth and dispatch logout event (let React handle navigation)
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem('user');
        // Dispatch event for AuthContext to handle navigation properly
        window.dispatchEvent(new CustomEvent('auth:session-expired'));
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(
          `${api.defaults.baseURL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken },
          {
            headers: { 'X-Client-ID': getTenantId() },
            timeout: 10000, // 10 second timeout
          }
        );

        if (response.data.success) {
          const { access_token, refresh_token: newRefreshToken } = response.data;

          localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
          localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);

          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          originalRequest.headers['Authorization'] = `Bearer ${access_token}`;

          processQueue(null, access_token);
          isRefreshing = false;

          return api(originalRequest);
        }
      } catch (refreshError) {
        processQueue(refreshError, null);
        isRefreshing = false;

        // Clear auth and dispatch logout event (let React handle navigation)
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem('user');
        // Dispatch event for AuthContext to handle navigation properly
        window.dispatchEvent(new CustomEvent('auth:session-expired'));

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ==================== Enhanced Caching System ====================
const cache = new Map();
const CACHE_TTL = 600000; // 10 minutes for rates (static data)
const STATS_CACHE_TTL = 300000; // 5 minutes for stats (semi-dynamic)
const DETAIL_CACHE_TTL = 600000; // 10 minutes for detail pages (static)
const LIST_CACHE_TTL = 300000; // 5 minutes for list pages
const STATIC_CACHE_TTL = 1800000; // 30 minutes for truly static data (hotels, destinations)

// Try to restore cache from sessionStorage on load
try {
  const savedCache = sessionStorage.getItem('api_cache');
  if (savedCache) {
    const parsed = JSON.parse(savedCache);
    Object.entries(parsed).forEach(([key, value]) => {
      // Only restore if still fresh
      if (Date.now() - value.timestamp < value.ttl) {
        cache.set(key, value);
      }
    });
  }
} catch (e) {
  // Ignore parse errors
}

// Persist cache to sessionStorage periodically
const persistCache = () => {
  try {
    const cacheObj = {};
    cache.forEach((value, key) => {
      // Only persist fresh items
      if (Date.now() - value.timestamp < value.ttl) {
        cacheObj[key] = value;
      }
    });
    sessionStorage.setItem('api_cache', JSON.stringify(cacheObj));
  } catch (e) {
    // Ignore quota errors
  }
};

// Persist cache every 10 seconds
setInterval(persistCache, 10000);

const getCached = (key) => {
  const item = cache.get(key);
  if (item && Date.now() - item.timestamp < item.ttl) {
    return item.data;
  }
  cache.delete(key);
  return null;
};

// Get stale cache (even if expired) - useful for stale-while-revalidate
const getStaleCached = (key) => {
  const item = cache.get(key);
  if (item) {
    return {
      data: item.data,
      isStale: Date.now() - item.timestamp >= item.ttl
    };
  }
  return null;
};

const setCached = (key, data, ttl = CACHE_TTL) => {
  cache.set(key, { data, timestamp: Date.now(), ttl });
};

// Stale-while-revalidate: Return stale data immediately, fetch fresh in background
const fetchWithSWR = async (key, fetcher, ttl = CACHE_TTL) => {
  const stale = getStaleCached(key);

  // If we have fresh cached data, return it immediately
  const fresh = getCached(key);
  if (fresh) {
    return { data: fresh };
  }

  // If we have stale data, return it but refresh in background
  if (stale) {
    // Refresh in background (don't await)
    fetcher().then(response => {
      setCached(key, response.data, ttl);
    }).catch(() => {});

    return { data: stale.data };
  }

  // No cache at all - must fetch
  const response = await fetcher();
  setCached(key, response.data, ttl);
  return response;
};

// Clear specific cache entries
export const clearCache = (pattern) => {
  if (!pattern) {
    cache.clear();
    return;
  }
  cache.forEach((_, key) => {
    if (key.includes(pattern)) {
      cache.delete(key);
    }
  });
};

// Cached GET helper - eliminates repetitive cache-check-fetch-cache pattern
const cachedGet = async (key, url, { ttl = CACHE_TTL, params, timeout, cacheIf, fallback } = {}) => {
  const cached = getCached(key);
  if (cached) return { data: cached };

  try {
    const config = {};
    if (params) config.params = params;
    if (timeout) config.timeout = timeout;

    const response = await api.get(url, config);

    if (!cacheIf || cacheIf(response.data)) {
      setCached(key, response.data, ttl);
    }

    return response;
  } catch (error) {
    if (fallback) return { data: fallback };
    throw error;
  }
};

// Prefetch helper - fetches and caches data for later use
export const prefetch = async (key, fetcher, ttl = DETAIL_CACHE_TTL) => {
  // Don't prefetch if already cached and fresh
  if (getCached(key)) return;

  try {
    const response = await fetcher();
    setCached(key, response.data, ttl);
  } catch (e) {
    // Silently fail - prefetch is best effort
    console.debug('Prefetch failed:', key);
  }
};

// Warm cache on app start - preload essential data only
// Uses sequential fetching to avoid overloading backend with concurrent requests
export const warmCache = async () => {
  // Only warm cache if user is authenticated
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    // Essential: Dashboard data (includes stats, recent quotes, usage in one call)
    // This is the most important - covers the landing page entirely
    await prefetch('dashboard-all', () => api.get('/api/v1/dashboard/all', { timeout: 30000 }), STATS_CACHE_TTL);

    // Secondary: Client info (needed for header display)
    // Only if not already cached
    if (!getCached('client-info')) {
      await prefetch('client-info', () => api.get('/api/v1/client/info'), STATIC_CACHE_TTL);
    }

    console.debug('Cache warmed successfully');
  } catch (e) {
    // Silently fail - cache warming is best effort
    console.debug('Cache warming skipped:', e?.message);
  }
};

// Prefetch on route change helper
export const prefetchForRoute = (route) => {
  // Use requestIdleCallback if available for non-blocking prefetch
  const doPrefetch = () => {
    switch (route) {
      case '/':
      case '/dashboard':
        prefetch('dashboard-all', () => api.get('/api/v1/dashboard/all'), STATS_CACHE_TTL);
        break;
      case '/quotes':
        prefetch('quotes-list-{}', () => api.get('/api/v1/quotes', { params: { limit: 50 } }), LIST_CACHE_TTL);
        prefetch('destinations', () => api.get('/api/v1/pricing/destinations'), STATIC_CACHE_TTL);
        break;
      case '/invoices':
        prefetch('invoices-list-{}', () => api.get('/api/v1/invoices', { params: { limit: 50 } }), LIST_CACHE_TTL);
        break;
      case '/crm/clients':
        prefetch('crm-clients-{}', () => api.get('/api/v1/crm/clients', { params: { limit: 50 } }), LIST_CACHE_TTL);
        break;
      case '/crm/pipeline':
        prefetch('pipeline', () => api.get('/api/v1/crm/pipeline'), STATS_CACHE_TTL);
        break;
      case '/pricing/rates':
        prefetch('rates-{}', () => api.get('/api/v1/pricing/rates'), STATIC_CACHE_TTL);
        prefetch('destinations', () => api.get('/api/v1/pricing/destinations'), STATIC_CACHE_TTL);
        break;
      case '/pricing/hotels':
        prefetch('hotels', () => api.get('/api/v1/pricing/hotels'), STATIC_CACHE_TTL);
        break;
      case '/analytics':
        prefetch('analytics-quotes-30d', () => api.get('/api/v1/analytics/quotes', { params: { period: '30d' } }), STATS_CACHE_TTL);
        break;
      case '/settings':
        prefetch('branding', () => api.get('/api/v1/branding'), CACHE_TTL);
        prefetch('branding-presets', () => api.get('/api/v1/branding/presets'), STATIC_CACHE_TTL);
        break;
      case '/leaderboard':
        prefetch('leaderboard-rankings-month-conversions', () => api.get('/api/v1/leaderboard/rankings', { params: { period: 'month' } }), STATS_CACHE_TTL);
        break;
      default:
        break;
    }
  };

  // Use requestIdleCallback for non-blocking prefetch, fallback to setTimeout
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    window.requestIdleCallback(doPrefetch, { timeout: 2000 });
  } else {
    setTimeout(doPrefetch, 100);
  }
};

// ==================== Quotes API ====================
export const quotesApi = {
  list: async (params = {}, options = {}) => {
    const { skipCache = false } = options;
    const cacheKey = `quotes-list-${JSON.stringify(params)}`;

    // Skip cache if requested (useful for debugging tenant issues)
    if (!skipCache) {
      const cached = getCached(cacheKey);
      if (cached) return { data: cached };
    }

    const response = await api.get('/api/v1/quotes', { params });
    setCached(cacheKey, response.data, LIST_CACHE_TTL);
    return response;
  },
  get: (id) => cachedGet(`quote-${id}`, `/api/v1/quotes/${id}`, { ttl: DETAIL_CACHE_TTL }),
  generate: (data) => api.post('/api/v1/quotes/generate', data, { timeout: 30000 }), // 30s for quote generation
  resend: (id) => api.post(`/api/v1/quotes/${id}/resend`),
  update: (id, data) => api.patch(`/api/v1/quotes/${id}`, data),
  delete: (id) => api.delete(`/api/v1/quotes/${id}`),
  download: (id) => api.get(`/api/v1/quotes/${id}/pdf`, { responseType: 'blob' }),

  // Prefetch quote detail on hover
  prefetch: (id) => prefetch(`quote-${id}`, () => api.get(`/api/v1/quotes/${id}`)),
};

// ==================== Pricing API ====================
const hasSuccessData = (data) => data?.success && data?.data?.length > 0;

export const pricingApi = {
  listRates: (params = {}) =>
    cachedGet(`rates-${JSON.stringify(params)}`, '/api/v1/pricing/rates', { params, timeout: 30000, cacheIf: hasSuccessData }),
  getRate: (id) => api.get(`/api/v1/pricing/rates/${id}`),
  createRate: (data) => api.post('/api/v1/pricing/rates', data),
  updateRate: (id, data) => api.put(`/api/v1/pricing/rates/${id}`, data),
  deleteRate: (id) => api.delete(`/api/v1/pricing/rates/${id}`),
  listHotels: (params = {}) =>
    cachedGet(`hotels-${JSON.stringify(params)}`, '/api/v1/pricing/hotels', { params, timeout: 30000, cacheIf: hasSuccessData }),
  getHotel: (hotelName) =>
    cachedGet(`hotel-${hotelName}`, `/api/v1/pricing/hotels/${encodeURIComponent(hotelName)}`),
  getHotelRates: (hotelName) =>
    cachedGet(`hotel-rates-${hotelName}`, `/api/v1/pricing/hotels/${encodeURIComponent(hotelName)}/rates`),
  listDestinations: () =>
    cachedGet('destinations', '/api/v1/pricing/destinations', { timeout: 30000, cacheIf: hasSuccessData }),
  getStats: () =>
    cachedGet('pricing-stats', '/api/v1/pricing/stats', { ttl: STATS_CACHE_TTL, timeout: 30000, cacheIf: (d) => d?.success }),
};

// ==================== CRM API ====================
export const crmApi = {
  // Clients
  listClients: async (params = {}, forceRefresh = false) => {
    const cacheKey = `crm-clients-${JSON.stringify(params)}`;

    if (!forceRefresh) {
      const cached = getCached(cacheKey);
      if (cached) return { data: cached };
    }

    const response = await api.get('/api/v1/crm/clients', { params });
    setCached(cacheKey, response.data, LIST_CACHE_TTL);
    return response;
  },
  getClient: (id) => cachedGet(`client-${id}`, `/api/v1/crm/clients/${id}`, { ttl: DETAIL_CACHE_TTL }),
  createClient: async (data) => {
    const response = await api.post('/api/v1/crm/clients', data);
    // Clear CRM caches after successful creation so list refreshes
    if (response.data?.success) {
      clearCache('crm-');
      clearCache('pipeline');
      clearCache('dashboard');
    }
    return response;
  },
  updateClient: async (id, data) => {
    const response = await api.patch(`/api/v1/crm/clients/${id}`, data);
    clearCache('crm-');
    clearCache(`client-${id}`);
    return response;
  },
  deleteClient: async (id) => {
    const response = await api.delete(`/api/v1/crm/clients/${id}`);
    clearCache('crm-');
    return response;
  },

  // Pipeline
  getPipeline: () => cachedGet('pipeline', '/api/v1/crm/pipeline', { ttl: STATS_CACHE_TTL }),

  updateStage: (clientId, stage) => api.patch(`/api/v1/crm/clients/${clientId}/stage`, { stage }),

  // Activities
  getActivities: (clientId) => api.get(`/api/v1/crm/clients/${clientId}/activities`),
  addActivity: (clientId, data) => api.post(`/api/v1/crm/clients/${clientId}/activities`, data),

  getStats: () => cachedGet('crm-stats', '/api/v1/crm/stats', { ttl: STATS_CACHE_TTL }),
  prefetch: (id) => prefetch(`client-${id}`, () => api.get(`/api/v1/crm/clients/${id}`)),
};

// ==================== Invoices API ====================
export const invoicesApi = {
  // Clear all invoice list caches (called after create/update/delete)
  clearListCache: () => {
    // Clear all cached invoice lists by removing entries that start with 'invoices-list-'
    for (const key of cache.keys()) {
      if (key.startsWith('invoices-list-') || key === 'invoice-stats') {
        cache.delete(key);
      }
    }
    // Also clear dashboard cache since it shows invoice stats
    cache.delete('dashboard-all');
  },

  list: (params = {}) => cachedGet(`invoices-list-${JSON.stringify(params)}`, '/api/v1/invoices', { ttl: LIST_CACHE_TTL, params }),
  get: (id) => cachedGet(`invoice-${id}`, `/api/v1/invoices/${id}`, { ttl: DETAIL_CACHE_TTL }),
  // Create invoice from quote - clears cache after success
  createFromQuote: async (data) => {
    const response = await api.post('/api/v1/invoices/convert-quote', data);
    if (response.data?.success || response.data?.invoice_id) {
      invoicesApi.clearListCache();
    }
    return response;
  },
  // Create manual invoice (without quote) - clears cache after success
  createManual: async (data) => {
    const response = await api.post('/api/v1/invoices/create', data);
    if (response.data?.success || response.data?.invoice_id) {
      invoicesApi.clearListCache();
    }
    return response;
  },
  // Alias for backwards compatibility
  create: (...args) => invoicesApi.createFromQuote(...args),
  update: async (id, data) => {
    const response = await api.patch(`/api/v1/invoices/${id}`, data);
    invoicesApi.clearListCache();
    cache.delete(`invoice-${id}`);
    return response;
  },
  delete: async (id) => {
    const response = await api.delete(`/api/v1/invoices/${id}`);
    invoicesApi.clearListCache();
    cache.delete(`invoice-${id}`);
    return response;
  },

  // Actions
  send: (id) => api.post(`/api/v1/invoices/${id}/send`),
  download: (id) => api.get(`/api/v1/invoices/${id}/pdf`, { responseType: 'blob' }),
  updateStatus: async (id, status) => {
    const response = await api.patch(`/api/v1/invoices/${id}/status`, { status });
    invoicesApi.clearListCache();
    cache.delete(`invoice-${id}`);
    return response;
  },
  recordPayment: async (id, data) => {
    const response = await api.post(`/api/v1/invoices/${id}/payments`, data);
    invoicesApi.clearListCache();
    cache.delete(`invoice-${id}`);
    return response;
  },

  getStats: () => cachedGet('invoice-stats', '/api/v1/invoices/stats', { ttl: STATS_CACHE_TTL }),
  prefetch: (id) => prefetch(`invoice-${id}`, () => api.get(`/api/v1/invoices/${id}`)),
};

// ==================== Knowledge Base API ====================
export const knowledgeApi = {
  listDocuments: (params = {}) => api.get('/api/v1/knowledge/documents', { params }),
  getDocument: (id) => api.get(`/api/v1/knowledge/documents/${id}`),
  // Let axios auto-set Content-Type with proper multipart boundary
  uploadDocument: (formData) => api.post('/api/v1/knowledge/documents', formData),
  deleteDocument: (id) => api.delete(`/api/v1/knowledge/documents/${id}`),
  updateVisibility: (id, visibility) => api.patch(`/api/v1/knowledge/documents/${id}`, { visibility }),
  search: (query, params = {}) => api.post('/api/v1/knowledge/search', { query, ...params }),
  getStatus: () => api.get('/api/v1/knowledge/status'),
};

// ==================== Inbound Chat API ====================
export const inboundApi = {
  // Tickets
  listTickets: (params = {}) => api.get('/api/v1/inbound/tickets', { params }),
  getTicket: (id) => api.get(`/api/v1/inbound/tickets/${id}`),
  updateTicket: (id, data) => api.patch(`/api/v1/inbound/tickets/${id}`, data),
  
  // Chat with customer
  sendReply: (ticketId, message) => api.post(`/api/v1/inbound/tickets/${ticketId}/reply`, { message }),
};

// ==================== Usage/Rate Limits API ====================
export const usageApi = {
  getLimits: () => cachedGet('usage-limits', '/api/v1/rate-limits/usage', { ttl: STATS_CACHE_TTL }),
  getStats: () => api.get('/api/v1/rate-limits/stats'),
};

// ==================== Dashboard API ====================
export const dashboardApi = {
  // Aggregated endpoint - returns everything in ONE call (optimized)
  // Uses stale-while-revalidate for instant page loads
  // Extended timeout for BigQuery cold start (matches backend 15s + buffer)
  getAll: () => fetchWithSWR(
    'dashboard-all',
    () => api.get('/api/v1/dashboard/all', { timeout: 30000 }),
    STATS_CACHE_TTL
  ),

  getStats: (period = '30d') => fetchWithSWR(
    `dashboard-stats-${period}`,
    () => api.get('/api/v1/dashboard/stats', { params: { period } }),
    STATS_CACHE_TTL
  ),

  getRecentActivity: (limit = 20) => api.get('/api/v1/dashboard/activity', { params: { limit } }),
};

// ==================== Analytics API ====================
export const analyticsApi = {
  getQuoteAnalytics: (period = '30d') =>
    cachedGet(`analytics-quotes-${period}`, '/api/v1/analytics/quotes', { ttl: STATS_CACHE_TTL, params: { period } }),
  getInvoiceAnalytics: (period = '30d') =>
    cachedGet(`analytics-invoices-${period}`, '/api/v1/analytics/invoices', { ttl: STATS_CACHE_TTL, params: { period } }),
  getPipelineAnalytics: () =>
    cachedGet('analytics-pipeline', '/api/v1/analytics/pipeline', { ttl: STATS_CACHE_TTL }),
  getCallAnalytics: (period = '30d') =>
    cachedGet(`analytics-calls-${period}`, '/api/v1/analytics/calls', { ttl: STATS_CACHE_TTL, params: { period } }),
};

// ==================== Client Info API ====================
export const clientApi = {
  getInfo: async () => {
    const cacheKey = 'client-info';
    const cached = getCached(cacheKey);
    if (cached) return { data: { success: true, data: cached } };

    const response = await api.get('/api/v1/client/info');
    // Cache the actual data object, not the wrapper
    const actualData = response.data?.data;
    if (actualData) {
      setCached(cacheKey, actualData, STATIC_CACHE_TTL);
    }
    return response;
  },
  // Update local cache with new client info (for immediate UI updates)
  updateInfoCache: (updates) => {
    const cacheKey = 'client-info';
    const cached = getCached(cacheKey);
    if (cached) {
      const updated = { ...cached, ...updates };
      setCached(cacheKey, updated, STATIC_CACHE_TTL);
      return { data: { success: true, data: updated } };
    }
    return { data: { success: true, data: updates } };
  },
  // Clear client info cache (force refresh on next read)
  clearInfoCache: () => {
    cache.delete('client-info');
  },
};

// ==================== Tenant Settings API ====================
export const tenantSettingsApi = {
  // Get all settings
  get: () => api.get('/api/v1/settings'),

  // Update all settings (company, email and banking)
  update: (data) => api.put('/api/v1/settings', data),

  // Update company settings only
  updateCompany: (data) => api.put('/api/v1/settings/company', data),

  // Update email settings only
  updateEmail: (data) => api.put('/api/v1/settings/email', data),

  // Update banking settings only
  updateBanking: (data) => api.put('/api/v1/settings/banking', data),
};

// ==================== Branding API ====================
export const brandingApi = {
  get: () => api.get('/api/v1/branding'),
  update: (data) => api.put('/api/v1/branding', data),
  getPresets: () => cachedGet('branding-presets', '/api/v1/branding/presets', { ttl: STATIC_CACHE_TTL }),
  applyPreset: (presetName) => api.post(`/api/v1/branding/apply-preset/${presetName}`),
  uploadLogo: (formData) => api.post('/api/v1/branding/upload/logo', formData),
  uploadBackground: (formData) => api.post('/api/v1/branding/upload/background', formData),
  reset: () => api.post('/api/v1/branding/reset'),
  getFonts: () => cachedGet('branding-fonts', '/api/v1/branding/fonts', { ttl: STATIC_CACHE_TTL }),
  preview: (data) => api.post('/api/v1/branding/preview', data),
  getCSSVariables: () => api.get('/api/v1/branding/css-variables'),
};

// ==================== Templates API ====================
export const templatesApi = {
  // Get all template settings
  get: () => api.get('/api/v1/templates'),

  // Update template settings
  update: (data) => api.put('/api/v1/templates', data),

  // Get quote template settings
  getQuote: () => api.get('/api/v1/templates/quote'),

  // Get invoice template settings
  getInvoice: () => api.get('/api/v1/templates/invoice'),

  // Reset to defaults
  reset: () => api.post('/api/v1/templates/reset'),

  getLayouts: () => cachedGet('template-layouts', '/api/v1/templates/layouts', { ttl: STATIC_CACHE_TTL }),
};

// ==================== Authentication API ====================
export const authApi = {
  login: (email, password, tenantId = null) => api.post('/api/v1/auth/login', {
    email,
    password,
    tenant_id: tenantId,
  }),

  logout: () => api.post('/api/v1/auth/logout'),

  refresh: (refreshToken) => api.post('/api/v1/auth/refresh', {
    refresh_token: refreshToken,
  }),

  me: () => api.get('/api/v1/auth/me'),

  requestPasswordReset: (email) => api.post('/api/v1/auth/password/reset', { email }),

  changePassword: (newPassword) => api.post('/api/v1/auth/password/change', {
    new_password: newPassword,
  }),

  updateProfile: (data) => api.patch('/api/v1/auth/profile', data),

  acceptInvite: (token, password, name = null) => api.post('/api/v1/auth/invite/accept', {
    password,
    name,
  }, { params: { token } }),
};

// ==================== Users API (Admin only) ====================
export const usersApi = {
  // User management
  list: () => api.get('/api/v1/users'),
  get: (userId) => api.get(`/api/v1/users/${userId}`),
  update: (userId, data) => api.patch(`/api/v1/users/${userId}`, data),
  deactivate: (userId) => api.delete(`/api/v1/users/${userId}`),

  // Invitations
  invite: (email, name, role = 'consultant') => api.post('/api/v1/users/invite', {
    email,
    name,
    role,
  }),
  listInvitations: () => api.get('/api/v1/users/invitations'),
  cancelInvitation: (invitationId) => api.delete(`/api/v1/users/invitations/${invitationId}`),
  resendInvitation: (invitationId) => api.post(`/api/v1/users/invitations/${invitationId}/resend`),
};

// ==================== Onboarding API ====================
export const onboardingApi = {
  // Generate AI system prompt from description
  generatePrompt: (data) => api.post('/api/v1/admin/onboarding/generate-prompt', data),

  // Get available brand themes
  getThemes: () => api.get('/api/v1/admin/onboarding/themes'),

  // Complete full onboarding
  complete: (data) => api.post('/api/v1/admin/onboarding/complete', data),

  // Check onboarding status
  getStatus: (tenantId) => api.get(`/api/v1/admin/onboarding/status/${tenantId}`),
};

// ==================== Leaderboard API ====================
export const leaderboardApi = {
  getRankings: (period = 'month', metric = 'conversions', limit = 50) =>
    cachedGet(`leaderboard-rankings-${period}-${metric}`, '/api/v1/leaderboard/rankings', { ttl: STATS_CACHE_TTL, params: { period, metric, limit } }),
  getMyPerformance: (period = 'month') =>
    cachedGet(`leaderboard-me-${period}`, '/api/v1/leaderboard/me', { ttl: STATS_CACHE_TTL, params: { period } }),
  getSummary: (period = 'month') =>
    cachedGet(`leaderboard-summary-${period}`, '/api/v1/leaderboard/summary', { ttl: STATS_CACHE_TTL, params: { period } }),
  getConsultantPerformance: (consultantId, period = 'month') =>
    api.get(`/api/v1/leaderboard/consultant/${consultantId}`, { params: { period } }),
};

// ==================== Helpdesk API ====================
// Central Zorah helpdesk - uses centralized knowledge base (not tenant-specific)
export const helpdeskApi = {
  // Ask a question to the centralized helpdesk
  // Uses longer timeout (60s) because RAG can take 15-30s on cold start
  ask: async (question) => {
    try {
      const response = await api.post('/api/v1/helpdesk/ask', { question }, { timeout: 60000 });
      return response;
    } catch (error) {
      // Fallback to null if endpoint not available
      return { data: { success: false, error: error.message } };
    }
  },

  getTopics: () =>
    cachedGet('helpdesk-topics', '/api/v1/helpdesk/topics', { ttl: STATIC_CACHE_TTL, fallback: { success: false, topics: [] } }),

  // Search help articles
  search: async (query) => {
    try {
      const response = await api.get('/api/v1/helpdesk/search', { params: { q: query } });
      return response;
    } catch (error) {
      return { data: { success: false, results: [] } };
    }
  },
};

// ==================== Notifications API ====================
export const notificationsApi = {
  // List notifications for current user
  list: async (params = {}) => {
    try {
      const response = await api.get('/api/v1/notifications', { params });
      return response;
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
      return { data: { success: false, data: [] } };
    }
  },

  // Get unread notification count
  getUnreadCount: async () => {
    try {
      const response = await api.get('/api/v1/notifications/unread-count');
      return response;
    } catch (error) {
      return { data: { success: false, unread_count: 0 } };
    }
  },

  // Mark a single notification as read
  markRead: async (notificationId) => {
    try {
      const response = await api.patch(`/api/v1/notifications/${notificationId}/read`);
      return response;
    } catch (error) {
      console.error('Failed to mark notification read:', error);
      return { data: { success: false } };
    }
  },

  // Mark all notifications as read
  markAllRead: async () => {
    try {
      const response = await api.post('/api/v1/notifications/mark-all-read');
      return response;
    } catch (error) {
      console.error('Failed to mark all read:', error);
      return { data: { success: false } };
    }
  },

  // Get notification preferences
  getPreferences: async () => {
    try {
      const response = await api.get('/api/v1/notifications/preferences');
      return response;
    } catch (error) {
      return { data: { success: false, data: {} } };
    }
  },

  // Update notification preferences
  updatePreferences: async (preferences) => {
    try {
      const response = await api.put('/api/v1/notifications/preferences', preferences);
      return response;
    } catch (error) {
      console.error('Failed to update preferences:', error);
      return { data: { success: false } };
    }
  },
};

// ==================== Privacy API (GDPR/POPIA) ====================
export const privacyApi = {
  // Get user's consent preferences
  getConsents: async () => {
    try {
      const response = await api.get('/privacy/consent');
      return response;
    } catch (error) {
      console.error('Failed to fetch consents:', error);
      return { data: { success: false, consents: {} } };
    }
  },

  // Update a single consent preference
  updateConsent: async (consent) => {
    try {
      const response = await api.post('/privacy/consent', consent);
      return response;
    } catch (error) {
      console.error('Failed to update consent:', error);
      return { data: { success: false } };
    }
  },

  // Update multiple consent preferences
  updateConsentsBulk: async (consents) => {
    try {
      const response = await api.post('/privacy/consent/bulk', { consents });
      return response;
    } catch (error) {
      console.error('Failed to update consents:', error);
      return { data: { success: false } };
    }
  },

  // Submit a Data Subject Access Request (DSAR)
  submitDSAR: async (request) => {
    try {
      const response = await api.post('/privacy/dsar', request);
      return response;
    } catch (error) {
      console.error('Failed to submit DSAR:', error);
      throw error;
    }
  },

  // Get user's DSAR history
  getDSARs: async () => {
    try {
      const response = await api.get('/privacy/dsar');
      return response;
    } catch (error) {
      console.error('Failed to fetch DSARs:', error);
      return { data: { success: false, requests: [] } };
    }
  },

  // Get status of a specific DSAR
  getDSARStatus: async (requestId) => {
    try {
      const response = await api.get(`/privacy/dsar/${requestId}`);
      return response;
    } catch (error) {
      console.error('Failed to fetch DSAR status:', error);
      return { data: { success: false } };
    }
  },

  // Request data export (portability)
  requestExport: async (request) => {
    try {
      const response = await api.post('/privacy/export', request);
      return response;
    } catch (error) {
      console.error('Failed to request export:', error);
      throw error;
    }
  },

  // Request data erasure
  requestErasure: async (email) => {
    try {
      const response = await api.post('/privacy/erasure', { email });
      return response;
    } catch (error) {
      console.error('Failed to request erasure:', error);
      throw error;
    }
  },
};

// ==================== Travel Services API ====================

// Hotels API (Live rates via Juniper)
export const hotelsApi = {
  health: () =>
    cachedGet('rates-health', '/api/v1/rates/health', { fallback: { success: false, available: false } }),
  search: (params) =>
    api.post('/api/v1/rates/hotels/search', params, { timeout: 180000 }),
  destinations: () =>
    cachedGet('rates-destinations', '/api/v1/rates/destinations', { ttl: STATIC_CACHE_TTL, fallback: { success: false, destinations: [] } }),
};

// Flights API
export const flightsApi = {
  list: (params = {}) =>
    cachedGet(`flights-${JSON.stringify(params)}`, '/api/v1/travel/flights', { ttl: LIST_CACHE_TTL, params, fallback: { success: false, flights: [] } }),
  search: async (destination, departureDate = null) => {
    const params = { destination };
    if (departureDate) params.departure_date = departureDate;
    try {
      return await api.get('/api/v1/travel/flights/search', { params });
    } catch {
      return { data: { success: false, flights: [] } };
    }
  },
};

// Transfers API
export const transfersApi = {
  list: (params = {}) =>
    cachedGet(`transfers-${JSON.stringify(params)}`, '/api/v1/travel/transfers', { ttl: LIST_CACHE_TTL, params, fallback: { success: false, transfers: [] } }),
  search: async (destination, hotelName = null) => {
    const params = { destination };
    if (hotelName) params.hotel_name = hotelName;
    try {
      return await api.get('/api/v1/travel/transfers/search', { params });
    } catch {
      return { data: { success: false, transfers: [] } };
    }
  },
};

// Activities API
export const activitiesApi = {
  list: (params = {}) =>
    cachedGet(`activities-${JSON.stringify(params)}`, '/api/v1/travel/activities', { ttl: LIST_CACHE_TTL, params, fallback: { success: false, activities: [] } }),
  search: async (destination, category = null, query = null) => {
    const params = { destination };
    if (category) params.category = category;
    if (query) params.query = query;
    try {
      return await api.get('/api/v1/travel/activities/search', { params });
    } catch {
      return { data: { success: false, activities: [] } };
    }
  },
  categories: () =>
    cachedGet('activity-categories', '/api/v1/travel/activities/categories', { ttl: STATIC_CACHE_TTL, fallback: { success: false, categories: [] } }),
};

// Travel Destinations (combined)
export const travelApi = {
  destinations: () =>
    cachedGet('travel-destinations', '/api/v1/travel/destinations', { ttl: STATIC_CACHE_TTL, fallback: { success: false, destinations: [] } }),
};

// ==================== Travel Platform Global Knowledge Base ====================
// All requests proxied through our backend to handle CORS and auth

export const globalKnowledgeApi = {
  listDocuments: (params = {}) =>
    cachedGet(`global-kb-list-${JSON.stringify(params)}`, '/api/v1/knowledge/global', {
      ttl: STATIC_CACHE_TTL,
      params,
      timeout: 120000,
      cacheIf: (d) => d?.success,
      fallback: { success: false, data: [], total: 0 },
    }),

  // Get document content as text (proxied through backend)
  getDocumentContent: async (documentId) => {
    try {
      const response = await api.get(`/api/v1/knowledge/global/${documentId}/content`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch document content:', error);
      throw error;
    }
  },

  // View document content in new tab (proxied through backend)
  viewDocument: (documentId) => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    window.open(`${baseUrl}/api/v1/knowledge/global/${documentId}/content`, '_blank');
  },

  // Download document - uses original file URL if available, otherwise falls back to extracted text
  downloadDocument: async (documentId, filename, originalFileUrl) => {
    // If original file is available, download directly from Travel Platform (public endpoint)
    if (originalFileUrl) {
      window.open(`${originalFileUrl}?download=true`, '_blank');
      return;
    }

    // Fallback: download extracted text via backend proxy
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/knowledge/global/${documentId}/download`);

      if (!response.ok) throw new Error(`Download failed: ${response.status}`);

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      // Ensure .txt extension since content is extracted text
      const baseName = (filename || 'document').replace(/\.[^.]+$/, '');
      link.download = `${baseName}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download failed. Please try again.');
    }
  },
};

// Export the axios instance for custom calls
export default api;