import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8082';
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN || 'zorah-internal-admin-2024';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-Admin-Token': ADMIN_TOKEN,
  },
});

// Tenants API
export const tenantsApi = {
  // List all tenants with summary
  listSummary: () => api.get('/api/v1/admin/tenants/summary'),

  // List all tenants (detailed)
  list: () => api.get('/api/v1/admin/tenants'),

  // Get tenant details
  get: (tenantId) => api.get(`/api/v1/admin/tenants/${tenantId}`),

  // Get tenant usage
  getUsage: (tenantId, period = 'month') =>
    api.get(`/api/v1/admin/tenants/${tenantId}/usage`, { params: { period } }),

  // Toggle tenant status
  toggle: (tenantId, enabled) =>
    api.post(`/api/v1/admin/tenants/${tenantId}/toggle`, { enabled }),
};

// Usage API
export const usageApi = {
  // Get all tenants usage summary
  getSummary: (period = 'month') =>
    api.get('/api/v1/admin/usage/summary', { params: { period } }),
};

// System API
export const systemApi = {
  // Get system health
  getHealth: () => api.get('/api/v1/admin/health'),
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
