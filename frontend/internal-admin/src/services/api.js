import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN || 'zorah-internal-admin-2024';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-Admin-Token': ADMIN_TOKEN,
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ==================== Caching Layer ====================

const CACHE_TTL = {
  SHORT: 30 * 1000,   // 30 seconds for frequently changing data
  MEDIUM: 60 * 1000,  // 1 minute for dashboard stats
  LONG: 5 * 60 * 1000 // 5 minutes for rarely changing data
};

// In-memory cache
const memoryCache = new Map();

// Get from cache (memory first, then localStorage)
function getCached(key) {
  // Check memory cache
  const memEntry = memoryCache.get(key);
  if (memEntry && Date.now() < memEntry.expires) {
    return memEntry.data;
  }

  // Check localStorage for persistence across page refreshes
  try {
    const stored = localStorage.getItem(`admin_cache_${key}`);
    if (stored) {
      const { data, expires } = JSON.parse(stored);
      if (Date.now() < expires) {
        // Restore to memory cache
        memoryCache.set(key, { data, expires });
        return data;
      }
      localStorage.removeItem(`admin_cache_${key}`);
    }
  } catch (e) {
    // Ignore localStorage errors
  }

  return null;
}

// Set in cache (both memory and localStorage)
function setCached(key, data, ttl = CACHE_TTL.MEDIUM) {
  const expires = Date.now() + ttl;
  memoryCache.set(key, { data, expires });

  try {
    localStorage.setItem(`admin_cache_${key}`, JSON.stringify({ data, expires }));
  } catch (e) {
    // Ignore localStorage errors (quota exceeded, etc)
  }
}

// Fetch with cache (stale-while-revalidate pattern)
async function fetchWithCache(key, fetcher, ttl = CACHE_TTL.MEDIUM) {
  const cached = getCached(key);

  // If we have cached data, return it immediately and refresh in background
  if (cached) {
    // Background refresh (don't await)
    fetcher().then(response => {
      if (response?.data) {
        setCached(key, response.data, ttl);
      }
    }).catch(() => {});

    return { data: cached, fromCache: true };
  }

  // No cache, fetch fresh
  const response = await fetcher();
  if (response?.data) {
    setCached(key, response.data, ttl);
  }
  return { ...response, fromCache: false };
}

// Export cache utilities for components
export { getCached, setCached, fetchWithCache, CACHE_TTL };

// Tenants API
export const tenantsApi = {
  // List all tenants with summary
  listSummary: () => api.get('/api/v1/admin/tenants'),

  // List all tenants (detailed) with filters
  list: (params = {}) => api.get('/api/v1/admin/tenants', { params }),

  // Get tenant details
  get: (tenantId) => api.get(`/api/v1/admin/tenants/${tenantId}`),

  // Get tenant stats
  getStats: (tenantId) => api.get(`/api/v1/admin/tenants/${tenantId}/stats`),

  // Get tenant usage (alias for stats)
  getUsage: (tenantId) => api.get(`/api/v1/admin/tenants/${tenantId}/stats`),

  // Suspend tenant
  suspend: (tenantId, reason) =>
    api.post(`/api/v1/admin/tenants/${tenantId}/suspend`, { reason }),

  // Activate tenant
  activate: (tenantId) =>
    api.post(`/api/v1/admin/tenants/${tenantId}/activate`),

  // Delete tenant
  delete: (tenantId, confirm = false) =>
    api.delete(`/api/v1/admin/tenants/${tenantId}`, { params: { confirm } }),
};

// Analytics API
export const analyticsApi = {
  // Get platform overview
  getOverview: () => api.get('/api/v1/admin/analytics/overview'),

  // Get usage analytics over time
  getUsage: (period = '30d', metric = 'all') =>
    api.get('/api/v1/admin/analytics/usage', { params: { period, metric } }),

  // Get top tenants
  getTopTenants: (metric = 'quotes', limit = 10) =>
    api.get('/api/v1/admin/analytics/tenants/top', { params: { metric, limit } }),

  // Get growth metrics
  getGrowth: () => api.get('/api/v1/admin/analytics/growth'),
};

// Usage API (backwards compatibility)
export const usageApi = {
  // Get all tenants usage summary (maps to analytics overview)
  getSummary: () => analyticsApi.getOverview(),
};

// System API
export const systemApi = {
  // Get system health
  getHealth: () => api.get('/api/v1/admin/health'),
};

// SendGrid API
export const sendgridApi = {
  // List all subusers
  listSubusers: () => api.get('/api/v1/admin/sendgrid/subusers'),

  // Get subuser stats
  getSubuserStats: (username, days = 30) =>
    api.get(`/api/v1/admin/sendgrid/subusers/${username}/stats`, { params: { days } }),

  // Disable subuser
  disableSubuser: (username) =>
    api.post(`/api/v1/admin/sendgrid/subusers/${username}/disable`),

  // Enable subuser
  enableSubuser: (username) =>
    api.post(`/api/v1/admin/sendgrid/subusers/${username}/enable`),

  // Get global email stats
  getStats: (days = 30) =>
    api.get('/api/v1/admin/sendgrid/stats', { params: { days } }),
};

// Knowledge Base API
export const knowledgeApi = {
  // List all documents
  listDocuments: (params = {}) =>
    api.get('/api/v1/admin/knowledge/documents', { params }),

  // Get single document
  getDocument: (docId) =>
    api.get(`/api/v1/admin/knowledge/documents/${docId}`),

  // Create document
  createDocument: (data) =>
    api.post('/api/v1/admin/knowledge/documents', data),

  // Update document
  updateDocument: (docId, data) =>
    api.put(`/api/v1/admin/knowledge/documents/${docId}`, data),

  // Delete document
  deleteDocument: (docId) =>
    api.delete(`/api/v1/admin/knowledge/documents/${docId}`),

  // Rebuild FAISS index
  rebuildIndex: () =>
    api.post('/api/v1/admin/knowledge/rebuild-index'),

  // Get knowledge stats
  getStats: () =>
    api.get('/api/v1/admin/knowledge/stats'),
};

// Provisioning API
export const provisioningApi = {
  // Get VAPI status for tenant
  getVAPIStatus: (tenantId) => api.get(`/api/v1/admin/provision/vapi/${tenantId}`),

  // Provision VAPI for tenant
  provisionVAPI: (data) => api.post('/api/v1/admin/provision/vapi', data),

  // Search available phone numbers
  searchPhones: (data) => api.post('/api/v1/admin/provision/phone/search', data),
};

export default api;
