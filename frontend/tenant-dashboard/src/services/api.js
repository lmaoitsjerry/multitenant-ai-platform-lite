import axios from 'axios';

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// Create axios instance with default config
// NOTE: Do NOT set default Content-Type here - let axios auto-detect for FormData uploads
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000, // 10 second timeout - prevents infinite hangs
});

// Add client ID and auth headers to all requests
api.interceptors.request.use((config) => {
  // Add client ID
  const clientId = import.meta.env.VITE_CLIENT_ID || 'africastay';
  config.headers['X-Client-ID'] = clientId;

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
        // Clear auth and redirect to login
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(
          `${api.defaults.baseURL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken },
          {
            headers: { 'X-Client-ID': import.meta.env.VITE_CLIENT_ID || 'africastay' },
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

        // Clear auth and redirect to login
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem('user');
        window.location.href = '/login';

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

// Warm cache on app start - preload commonly used data
export const warmCache = async () => {
  const warmPromises = [];

  // Only warm cache if user is authenticated
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    // Prefetch dashboard data (includes stats, recent quotes, usage)
    warmPromises.push(
      prefetch('dashboard-all', () => api.get('/api/v1/dashboard/all'), STATS_CACHE_TTL)
    );

    // Prefetch pricing destinations (static - rarely changes)
    warmPromises.push(
      prefetch('destinations', () => api.get('/api/v1/pricing/destinations'), STATIC_CACHE_TTL)
    );

    // Prefetch hotels (static - rarely changes)
    warmPromises.push(
      prefetch('hotels', () => api.get('/api/v1/pricing/hotels'), STATIC_CACHE_TTL)
    );

    // Prefetch client info (tenant-specific, rarely changes)
    warmPromises.push(
      prefetch('client-info', () => api.get('/api/v1/client/info'), STATIC_CACHE_TTL)
    );

    // Prefetch branding presets (static)
    warmPromises.push(
      prefetch('branding-presets', () => api.get('/api/v1/branding/presets'), STATIC_CACHE_TTL)
    );

    // Prefetch recent quotes (commonly accessed)
    warmPromises.push(
      prefetch('quotes-list-{}', () => api.get('/api/v1/quotes', { params: { limit: 20 } }), LIST_CACHE_TTL)
    );

    // Prefetch pipeline (commonly accessed)
    warmPromises.push(
      prefetch('pipeline', () => api.get('/api/v1/crm/pipeline'), STATS_CACHE_TTL)
    );

    await Promise.allSettled(warmPromises);
    console.debug('Cache warmed successfully');
  } catch (e) {
    console.debug('Cache warming failed:', e);
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
  list: async (params = {}) => {
    const cacheKey = `quotes-list-${JSON.stringify(params)}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/quotes', { params });
    setCached(cacheKey, response.data, LIST_CACHE_TTL);
    return response;
  },
  get: async (id) => {
    const cacheKey = `quote-${id}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get(`/api/v1/quotes/${id}`);
    setCached(cacheKey, response.data, DETAIL_CACHE_TTL);
    return response;
  },
  generate: (data) => api.post('/api/v1/quotes/generate', data),
  resend: (id) => api.post(`/api/v1/quotes/${id}/resend`),
  update: (id, data) => api.patch(`/api/v1/quotes/${id}`, data),
  delete: (id) => api.delete(`/api/v1/quotes/${id}`),

  // Prefetch quote detail on hover
  prefetch: (id) => prefetch(`quote-${id}`, () => api.get(`/api/v1/quotes/${id}`)),
};

// ==================== Pricing API ====================
export const pricingApi = {
  listRates: async (params = {}) => {
    const cacheKey = `rates-${JSON.stringify(params)}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    // BigQuery can be slow on cold start - use 30s timeout
    const response = await api.get('/api/v1/pricing/rates', { params, timeout: 30000 });
    // Only cache successful responses with data
    if (response.data?.success && response.data?.data?.length > 0) {
      setCached(cacheKey, response.data, CACHE_TTL);
    }
    return response;
  },
  
  getRate: (id) => api.get(`/api/v1/pricing/rates/${id}`),
  createRate: (data) => api.post('/api/v1/pricing/rates', data),
  updateRate: (id, data) => api.put(`/api/v1/pricing/rates/${id}`, data),
  deleteRate: (id) => api.delete(`/api/v1/pricing/rates/${id}`),
  
  listHotels: async (params = {}) => {
    const cacheKey = `hotels-${JSON.stringify(params)}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    // BigQuery can be slow on cold start - use 30s timeout
    const response = await api.get('/api/v1/pricing/hotels', { params, timeout: 30000 });
    // Only cache successful responses with data
    if (response.data?.success && response.data?.data?.length > 0) {
      setCached(cacheKey, response.data, CACHE_TTL);
    }
    return response;
  },

  getHotel: async (hotelName) => {
    const cacheKey = `hotel-${hotelName}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get(`/api/v1/pricing/hotels/${encodeURIComponent(hotelName)}`);
    setCached(cacheKey, response.data, CACHE_TTL);
    return response;
  },

  getHotelRates: async (hotelName) => {
    const cacheKey = `hotel-rates-${hotelName}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get(`/api/v1/pricing/hotels/${encodeURIComponent(hotelName)}/rates`);
    setCached(cacheKey, response.data, CACHE_TTL);
    return response;
  },
  
  listDestinations: async () => {
    const cacheKey = 'destinations';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    // BigQuery can be slow on cold start - use 30s timeout
    const response = await api.get('/api/v1/pricing/destinations', { timeout: 30000 });
    if (response.data?.success && response.data?.data?.length > 0) {
      setCached(cacheKey, response.data, CACHE_TTL);
    }
    return response;
  },

  getStats: async () => {
    const cacheKey = 'pricing-stats';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    // BigQuery can be slow on cold start - use 30s timeout
    const response = await api.get('/api/v1/pricing/stats', { timeout: 30000 });
    if (response.data?.success) {
      setCached(cacheKey, response.data, STATS_CACHE_TTL);
    }
    return response;
  },
};

// ==================== CRM API ====================
export const crmApi = {
  // Clients
  listClients: async (params = {}) => {
    const cacheKey = `crm-clients-${JSON.stringify(params)}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/crm/clients', { params });
    setCached(cacheKey, response.data, LIST_CACHE_TTL);
    return response;
  },
  getClient: async (id) => {
    const cacheKey = `client-${id}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get(`/api/v1/crm/clients/${id}`);
    setCached(cacheKey, response.data, DETAIL_CACHE_TTL);
    return response;
  },
  createClient: (data) => api.post('/api/v1/crm/clients', data),
  updateClient: (id, data) => api.patch(`/api/v1/crm/clients/${id}`, data),
  deleteClient: (id) => api.delete(`/api/v1/crm/clients/${id}`),

  // Pipeline
  getPipeline: async () => {
    const cacheKey = 'pipeline';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/crm/pipeline');
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  updateStage: (clientId, stage) => api.patch(`/api/v1/crm/clients/${clientId}/stage`, { stage }),

  // Activities
  getActivities: (clientId) => api.get(`/api/v1/crm/clients/${clientId}/activities`),
  addActivity: (clientId, data) => api.post(`/api/v1/crm/clients/${clientId}/activities`, data),

  // Stats
  getStats: async () => {
    const cacheKey = 'crm-stats';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/crm/stats');
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Prefetch client detail on hover
  prefetch: (id) => prefetch(`client-${id}`, () => api.get(`/api/v1/crm/clients/${id}`)),
};

// ==================== Invoices API ====================
export const invoicesApi = {
  list: async (params = {}) => {
    const cacheKey = `invoices-list-${JSON.stringify(params)}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/invoices', { params });
    setCached(cacheKey, response.data, LIST_CACHE_TTL);
    return response;
  },
  get: async (id) => {
    const cacheKey = `invoice-${id}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get(`/api/v1/invoices/${id}`);
    setCached(cacheKey, response.data, DETAIL_CACHE_TTL);
    return response;
  },
  // Create invoice from quote
  createFromQuote: (data) => api.post('/api/v1/invoices/convert-quote', data),
  // Create manual invoice (without quote)
  createManual: (data) => api.post('/api/v1/invoices/create', data),
  // Alias for backwards compatibility (creates from quote)
  create: (data) => api.post('/api/v1/invoices/convert-quote', data),
  update: (id, data) => api.patch(`/api/v1/invoices/${id}`, data),
  delete: (id) => api.delete(`/api/v1/invoices/${id}`),

  // Actions
  send: (id) => api.post(`/api/v1/invoices/${id}/send`),
  download: (id) => api.get(`/api/v1/invoices/${id}/pdf`, { responseType: 'blob' }),
  updateStatus: (id, status) => api.patch(`/api/v1/invoices/${id}/status`, { status }),
  recordPayment: (id, data) => api.post(`/api/v1/invoices/${id}/payments`, data),

  // Stats
  getStats: async () => {
    const cacheKey = 'invoice-stats';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/invoices/stats');
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Prefetch invoice detail on hover
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
  getLimits: async () => {
    const cacheKey = 'usage-limits';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/rate-limits/usage');
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },
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
  // Quote analytics
  getQuoteAnalytics: async (period = '30d') => {
    const cacheKey = `analytics-quotes-${period}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/analytics/quotes', { params: { period } });
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Invoice analytics
  getInvoiceAnalytics: async (period = '30d') => {
    const cacheKey = `analytics-invoices-${period}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/analytics/invoices', { params: { period } });
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Pipeline analytics
  getPipelineAnalytics: async () => {
    const cacheKey = 'analytics-pipeline';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/analytics/pipeline');
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Call analytics
  getCallAnalytics: async (period = '30d') => {
    const cacheKey = `analytics-calls-${period}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/analytics/calls', { params: { period } });
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },
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
  // Get current branding
  get: async () => {
    const response = await api.get('/api/v1/branding');
    return response;
  },

  // Update branding
  update: (data) => api.put('/api/v1/branding', data),

  // Get available presets
  getPresets: async () => {
    const cacheKey = 'branding-presets';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/branding/presets');
    setCached(cacheKey, response.data, CACHE_TTL * 10); // Cache for 10 minutes
    return response;
  },

  // Apply a preset
  applyPreset: (presetName) => api.post(`/api/v1/branding/apply-preset/${presetName}`),

  // Upload logo - let axios auto-set Content-Type with proper multipart boundary
  uploadLogo: (formData) => api.post('/api/v1/branding/upload/logo', formData),

  // Upload login background image
  uploadBackground: (formData) => api.post('/api/v1/branding/upload/background', formData),

  // Reset to defaults
  reset: () => api.post('/api/v1/branding/reset'),

  // Get available fonts
  getFonts: async () => {
    const cacheKey = 'branding-fonts';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/branding/fonts');
    setCached(cacheKey, response.data, CACHE_TTL * 10);
    return response;
  },

  // Preview branding changes
  preview: (data) => api.post('/api/v1/branding/preview', data),

  // Get CSS variables
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

  // Get available layouts
  getLayouts: async () => {
    const cacheKey = 'template-layouts';
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/templates/layouts');
    setCached(cacheKey, response.data, CACHE_TTL * 10);
    return response;
  },
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
  // Get consultant rankings
  getRankings: async (period = 'month', metric = 'conversions', limit = 50) => {
    const cacheKey = `leaderboard-rankings-${period}-${metric}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/leaderboard/rankings', {
      params: { period, metric, limit },
    });
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Get current user's performance
  getMyPerformance: async (period = 'month') => {
    const cacheKey = `leaderboard-me-${period}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/leaderboard/me', {
      params: { period },
    });
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Get organization performance summary
  getSummary: async (period = 'month') => {
    const cacheKey = `leaderboard-summary-${period}`;
    const cached = getCached(cacheKey);
    if (cached) return { data: cached };

    const response = await api.get('/api/v1/leaderboard/summary', {
      params: { period },
    });
    setCached(cacheKey, response.data, STATS_CACHE_TTL);
    return response;
  },

  // Get specific consultant's performance
  getConsultantPerformance: (consultantId, period = 'month') =>
    api.get(`/api/v1/leaderboard/consultant/${consultantId}`, {
      params: { period },
    }),
};

// ==================== Helpdesk API ====================
// Central Zorah helpdesk - uses centralized knowledge base (not tenant-specific)
export const helpdeskApi = {
  // Ask a question to the centralized helpdesk
  ask: async (question) => {
    try {
      const response = await api.post('/api/v1/helpdesk/ask', { question });
      return response;
    } catch (error) {
      // Fallback to null if endpoint not available
      return { data: { success: false, error: error.message } };
    }
  },

  // Get help topics/categories
  getTopics: async () => {
    try {
      const cacheKey = 'helpdesk-topics';
      const cached = getCached(cacheKey);
      if (cached) return { data: cached };

      const response = await api.get('/api/v1/helpdesk/topics');
      setCached(cacheKey, response.data, CACHE_TTL * 10); // Cache for 10 minutes
      return response;
    } catch (error) {
      return { data: { success: false, topics: [] } };
    }
  },

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

// Export the axios instance for custom calls
export default api;