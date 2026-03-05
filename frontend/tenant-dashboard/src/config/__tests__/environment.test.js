/**
 * Tests for the central environment configuration module.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// We need to mock import.meta.env before importing the module,
// so we use vi.hoisted + dynamic imports per test.

describe('environment config', () => {
  describe('pdfUrl', () => {
    it('builds quote PDF URL with absolute base', async () => {
      const { pdfUrl } = await import('../environment.js');
      const url = pdfUrl('quotes', 'QT-123');
      expect(url).toContain('/api/v1/public/quotes/QT-123/pdf');
      // Should be absolute (starts with http)
      expect(url).toMatch(/^https?:\/\//);
    });

    it('builds invoice PDF URL with absolute base', async () => {
      const { pdfUrl } = await import('../environment.js');
      const url = pdfUrl('invoices', 'INV-456');
      expect(url).toContain('/api/v1/public/invoices/INV-456/pdf');
      expect(url).toMatch(/^https?:\/\//);
    });
  });

  describe('publicLink', () => {
    it('returns same URL as pdfUrl', async () => {
      const { pdfUrl, publicLink } = await import('../environment.js');
      expect(publicLink('invoices', 'INV-1')).toBe(pdfUrl('invoices', 'INV-1'));
    });
  });

  describe('apiUrl', () => {
    it('prepends API_BASE_URL to path', async () => {
      const { apiUrl } = await import('../environment.js');
      const url = apiUrl('/api/v1/test');
      expect(url).toContain('/api/v1/test');
    });

    it('returns empty string for empty path when in dev (proxy)', async () => {
      const { apiUrl, API_BASE_URL } = await import('../environment.js');
      // In dev mode API_BASE_URL is '', so apiUrl('') should be ''
      if (API_BASE_URL === '') {
        expect(apiUrl('')).toBe('');
      }
    });
  });

  describe('websiteBuilderUrl', () => {
    it('builds website builder path', async () => {
      const { websiteBuilderUrl } = await import('../environment.js');
      const url = websiteBuilderUrl('/api/analytics/summary');
      expect(url).toContain('/api/analytics/summary');
    });
  });

  describe('constants', () => {
    it('exports DEFAULT_TENANT_ID as example', async () => {
      const { DEFAULT_TENANT_ID } = await import('../environment.js');
      expect(DEFAULT_TENANT_ID).toBe('example');
    });

    it('exports API_ABSOLUTE_URL as a string', async () => {
      const { API_ABSOLUTE_URL } = await import('../environment.js');
      expect(typeof API_ABSOLUTE_URL).toBe('string');
      expect(API_ABSOLUTE_URL.length).toBeGreaterThan(0);
    });

    it('exports WEBSITE_BUILDER_URL as a string', async () => {
      const { WEBSITE_BUILDER_URL } = await import('../environment.js');
      expect(typeof WEBSITE_BUILDER_URL).toBe('string');
    });
  });
});
