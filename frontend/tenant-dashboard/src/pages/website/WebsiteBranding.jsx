import { useState, useEffect, useCallback } from 'react';
import { websiteBuilderApi, brandingApi } from '../../services/api';
import {
  PhotoIcon,
  CheckIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

const GOOGLE_FONTS = [
  'Inter', 'Outfit', 'Playfair Display', 'Lato', 'Nunito',
  'Roboto', 'Open Sans', 'Montserrat', 'Poppins', 'Raleway'
];

export default function WebsiteBranding() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [branding, setBranding] = useState({
    logo_url: '',
    primary_color: '#0891b2',
    secondary_color: '#06b6d4',
    accent_color: '#f97316',
    font_heading: 'Outfit',
    font_body: 'Nunito',
    tagline: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const response = await websiteBuilderApi.getWebsiteConfig();
      if (response.data?.branding) {
        setBranding(prev => ({ ...prev, ...response.data.branding }));
      }
    } catch (err) {
      console.error('Failed to load branding:', err);
      setError('Failed to load branding settings');
    } finally {
      setLoading(false);
    }
  }

  const handleChange = useCallback((field, value) => {
    setBranding(prev => ({ ...prev, [field]: value }));
    setSaved(false);
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await websiteBuilderApi.updateBranding(branding);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save branding:', err);
      setError('Failed to save branding settings');
    } finally {
      setSaving(false);
    }
  }

  async function handleLogoUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError('Invalid file type. Please upload PNG, JPG, SVG, or WebP.');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('File too large. Maximum size is 5MB.');
      return;
    }

    setError(null);
    setSaving(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('logo_type', 'primary');

      const response = await brandingApi.uploadLogo(formData);
      if (response.data?.success && response.data?.data?.url) {
        handleChange('logo_url', response.data.data.url);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        setError(response.data?.detail || 'Failed to upload logo');
      }
    } catch (err) {
      console.error('Failed to upload logo:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to upload logo';
      setError(errorMsg);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-96 bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Branding</h1>
          <p className="text-gray-500">Customize your website's look and feel</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center gap-2"
        >
          {saving ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <CheckIcon className="w-4 h-4" />
          ) : null}
          {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Logo Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Logo</h2>

          <div className="space-y-4">
            {branding.logo_url ? (
              <div className="flex items-center gap-4">
                <img
                  src={branding.logo_url}
                  alt="Logo"
                  className="h-16 w-auto object-contain bg-gray-50 rounded-lg p-2"
                />
                <button
                  onClick={() => handleChange('logo_url', '')}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  Remove
                </button>
              </div>
            ) : (
              <label className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg transition-colors ${
                saving ? 'border-purple-400 bg-purple-50' : 'border-gray-300 hover:border-purple-400 cursor-pointer'
              }`}>
                {saving ? (
                  <>
                    <ArrowPathIcon className="w-8 h-8 text-purple-500 mb-2 animate-spin" />
                    <span className="text-sm text-purple-600">Uploading...</span>
                  </>
                ) : (
                  <>
                    <PhotoIcon className="w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-500">Click to upload logo</span>
                    <span className="text-xs text-gray-400 mt-1">PNG, JPG, SVG, WebP • Max 5MB</span>
                  </>
                )}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/svg+xml,image/webp"
                  onChange={handleLogoUpload}
                  className="hidden"
                  disabled={saving}
                />
              </label>
            )}
          </div>
        </div>

        {/* Tagline */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Tagline</h2>
          <input
            type="text"
            value={branding.tagline || ''}
            onChange={(e) => handleChange('tagline', e.target.value)}
            placeholder="Your travel adventure starts here..."
            className="input"
          />
          <p className="text-sm text-gray-500 mt-2">
            A short phrase that appears on your website header
          </p>
        </div>

        {/* Colors Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Colors</h2>

          <div className="space-y-4">
            {[
              { key: 'primary_color', label: 'Primary Color', desc: 'Main brand color' },
              { key: 'secondary_color', label: 'Secondary Color', desc: 'Supporting color' },
              { key: 'accent_color', label: 'Accent Color', desc: 'Highlights and CTAs' },
            ].map(({ key, label, desc }) => (
              <div key={key} className="flex items-center gap-4">
                <input
                  type="color"
                  value={branding[key] || '#000000'}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-12 h-12 rounded-lg border border-gray-200 cursor-pointer"
                />
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-700">{label}</label>
                  <p className="text-xs text-gray-500">{desc}</p>
                </div>
                <input
                  type="text"
                  value={branding[key] || ''}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-24 px-2 py-1 text-sm border border-gray-200 rounded font-mono"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Fonts Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Typography</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Font Selectors */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Heading Font
                </label>
                <select
                  value={branding.font_heading || 'Outfit'}
                  onChange={(e) => handleChange('font_heading', e.target.value)}
                  className="input"
                  style={{ fontFamily: `"${branding.font_heading}", sans-serif` }}
                >
                  {GOOGLE_FONTS.map(font => (
                    <option key={font} value={font} style={{ fontFamily: `"${font}", sans-serif` }}>
                      {font}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Body Font
                </label>
                <select
                  value={branding.font_body || 'Nunito'}
                  onChange={(e) => handleChange('font_body', e.target.value)}
                  className="input"
                  style={{ fontFamily: `"${branding.font_body}", sans-serif` }}
                >
                  {GOOGLE_FONTS.map(font => (
                    <option key={font} value={font} style={{ fontFamily: `"${font}", sans-serif` }}>
                      {font}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Preview - Side by side on desktop */}
            <div className="p-4 bg-gray-50 rounded-lg flex flex-col justify-center">
              <p className="text-xs text-gray-500 mb-2">Live Preview:</p>
              <h3
                className="text-xl font-bold text-gray-900"
                style={{ fontFamily: `"${branding.font_heading}", serif` }}
              >
                Welcome to Paradise
              </h3>
              <p
                className="text-gray-600 mt-2"
                style={{ fontFamily: `"${branding.font_body}", sans-serif` }}
              >
                Discover breathtaking destinations and create unforgettable memories with our expertly curated travel experiences.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
