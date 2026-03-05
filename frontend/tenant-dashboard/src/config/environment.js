/**
 * Central environment configuration module.
 *
 * All URL construction and environment variable access is consolidated here
 * so that no component needs to hardcode localhost, port numbers, or tenant IDs.
 *
 * Usage:
 *   import { apiUrl, pdfUrl, publicLink, websiteBuilderUrl } from '../config/environment';
 */

// ── Raw env values ──────────────────────────────────────────────────────────
const isDev = import.meta.env.DEV;

/**
 * Base API URL.
 * - In development: empty string (requests go through Vite proxy, avoiding CORS)
 * - In production: VITE_API_URL env var
 */
export const API_BASE_URL = isDev ? '' : (import.meta.env.VITE_API_URL || '');

/**
 * Absolute API URL — always includes the host, even in dev.
 * Used for URLs that must be absolute (PDF iframes, clipboard links, <a> targets).
 */
export const API_ABSOLUTE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Website Builder direct URL — the real service URL for browser navigation.
 * Used for iframes, new-tab links, and editor embeds (getEditorUrl, getEmbedPreviewUrl, etc.)
 * These are NOT subject to CORS because they load in separate browsing contexts.
 */
export const WEBSITE_BUILDER_URL = import.meta.env.VITE_WEBSITE_BUILDER_URL || 'http://localhost:3000';

/**
 * Website Builder API proxy base — for axios API calls (avoids CORS).
 * - In development: '/wb' prefix, Vite proxy strips it and forwards to service
 * - In production: '/api/v1/wb' prefix, FastAPI proxy forwards to service
 */
export const WEBSITE_BUILDER_API_BASE = isDev ? '/wb' : `${API_BASE_URL}/api/v1/wb`;

/**
 * Public-facing app URL (used for generating shareable links).
 */
export const PUBLIC_APP_URL = import.meta.env.VITE_APP_URL || '';

/**
 * Default tenant/client ID when none is set in localStorage or env.
 * The value 'example' is intentionally used as a sentinel — the request interceptor
 * in api.js skips the X-Client-ID header when the tenant is 'example',
 * which allows the login flow to work without a pre-selected tenant.
 */
export const DEFAULT_TENANT_ID = 'example';

// ── URL helpers ─────────────────────────────────────────────────────────────

/**
 * Build an API path relative to the base URL (proxied in dev, absolute in prod).
 * Use for axios requests that go through the `api` instance.
 *
 * @param {string} path - e.g. '/api/v1/invoices'
 * @returns {string}
 */
export function apiUrl(path = '') {
  return `${API_BASE_URL}${path}`;
}

/**
 * Build an absolute URL for a public PDF endpoint.
 * Always absolute because PDFs are loaded in iframes / new tabs.
 *
 * @param {'quotes'|'invoices'} entity
 * @param {string} id - quote_id or invoice_id
 * @returns {string}
 */
export function pdfUrl(entity, id) {
  return `${API_ABSOLUTE_URL}/api/v1/public/${entity}/${id}/pdf`;
}

/**
 * Build a shareable public link (e.g. invoice PDF link for clipboard).
 *
 * @param {'quotes'|'invoices'} entity
 * @param {string} id
 * @returns {string}
 */
export function publicLink(entity, id) {
  return pdfUrl(entity, id);
}

/**
 * Build a Website Builder API path.
 *
 * @param {string} path - e.g. '/api/analytics/summary'
 * @returns {string}
 */
export function websiteBuilderUrl(path = '') {
  return `${WEBSITE_BUILDER_URL}${path}`;
}
