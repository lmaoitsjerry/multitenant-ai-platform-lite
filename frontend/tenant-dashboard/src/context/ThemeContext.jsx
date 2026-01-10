import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { brandingApi } from '../services/api';

const ThemeContext = createContext(null);

// CSS Variable name mapping
const CSS_VAR_MAP = {
  primary: '--color-primary',
  primary_light: '--color-primary-light',
  primary_dark: '--color-primary-dark',
  secondary: '--color-secondary',
  secondary_light: '--color-secondary-light',
  secondary_dark: '--color-secondary-dark',
  accent: '--color-accent',
  success: '--color-success',
  warning: '--color-warning',
  error: '--color-error',
  background: '--color-background',
  surface: '--color-surface',
  surface_elevated: '--color-surface-elevated',
  text_primary: '--color-text-primary',
  text_secondary: '--color-text-secondary',
  text_muted: '--color-text-muted',
  border: '--color-border',
  border_light: '--color-border-light',
};

const FONT_VAR_MAP = {
  heading: '--font-family-heading',
  body: '--font-family-body',
};

// Default theme presets fallback if API fails
const DEFAULT_PRESETS = [
  {
    id: 'professional_blue',
    name: 'Professional Blue',
    description: 'Clean, corporate aesthetic with blue tones',
    colors: {
      primary: '#2563EB',
      primary_light: '#3B82F6',
      primary_dark: '#1D4ED8',
      secondary: '#64748B',
    },
    fonts: { heading: 'Inter, system-ui, sans-serif', body: 'Inter, system-ui, sans-serif' },
    preview_gradient: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
  },
  {
    id: 'vibrant_orange',
    name: 'Vibrant Orange',
    description: 'Energetic and warm with orange accents',
    colors: { primary: '#EA580C', primary_light: '#F97316', primary_dark: '#C2410C', secondary: '#78716C' },
    fonts: { heading: 'Poppins, system-ui, sans-serif', body: 'Inter, system-ui, sans-serif' },
    preview_gradient: 'linear-gradient(135deg, #EA580C 0%, #C2410C 100%)',
  },
  {
    id: 'elegant_purple',
    name: 'Elegant Purple',
    description: 'Sophisticated and creative with purple shades',
    colors: { primary: '#7C3AED', primary_light: '#8B5CF6', primary_dark: '#6D28D9', secondary: '#6B7280' },
    fonts: { heading: 'Playfair Display, serif', body: 'Open Sans, system-ui, sans-serif' },
    preview_gradient: 'linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%)',
  },
  {
    id: 'nature_green',
    name: 'Nature Green',
    description: 'Fresh and organic with green hues',
    colors: { primary: '#059669', primary_light: '#10B981', primary_dark: '#047857', secondary: '#4B5563' },
    fonts: { heading: 'Montserrat, system-ui, sans-serif', body: 'Open Sans, system-ui, sans-serif' },
    preview_gradient: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
  },
  {
    id: 'ocean_teal',
    name: 'Ocean Teal',
    description: 'Calm and refreshing with teal tones',
    colors: { primary: '#0D9488', primary_light: '#14B8A6', primary_dark: '#0F766E', secondary: '#475569' },
    fonts: { heading: 'Quicksand, system-ui, sans-serif', body: 'Roboto, system-ui, sans-serif' },
    preview_gradient: 'linear-gradient(135deg, #0D9488 0%, #0F766E 100%)',
  },
];

// Default fonts fallback if API fails
const DEFAULT_FONTS = [
  { name: 'Inter', value: 'Inter, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Poppins', value: 'Poppins, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Montserrat', value: 'Montserrat, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Open Sans', value: 'Open Sans, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Roboto', value: 'Roboto, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Lato', value: 'Lato, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Nunito', value: 'Nunito, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Quicksand', value: 'Quicksand, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Source Sans Pro', value: 'Source Sans Pro, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Raleway', value: 'Raleway, system-ui, sans-serif', category: 'sans-serif' },
  { name: 'Playfair Display', value: 'Playfair Display, serif', category: 'serif' },
  { name: 'Merriweather', value: 'Merriweather, serif', category: 'serif' },
  { name: 'Libre Baskerville', value: 'Libre Baskerville, serif', category: 'serif' },
];

export function ThemeProvider({ children }) {
  const [branding, setBranding] = useState(null);
  const [previewBranding, setPreviewBranding] = useState(null);
  const [presets, setPresets] = useState(DEFAULT_PRESETS);
  const [fonts, setFonts] = useState(DEFAULT_FONTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [darkMode, setDarkMode] = useState(false);

  // Load branding on mount
  useEffect(() => {
    loadBranding();
    loadPresets();
    loadFonts();
  }, []);

  // Apply CSS variables when branding changes
  useEffect(() => {
    const activeTheme = previewBranding || branding;
    if (activeTheme) {
      applyCSSVariables(activeTheme);
    }
  }, [branding, previewBranding]);

  // Apply dark mode attribute
  useEffect(() => {
    if (darkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }, [darkMode]);

  const loadBranding = async () => {
    try {
      setLoading(true);
      const response = await brandingApi.get();
      if (response.data?.success) {
        setBranding(response.data.data);
        setDarkMode(response.data.data.dark_mode_enabled || false);
      }
    } catch (err) {
      console.error('Failed to load branding:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadPresets = async () => {
    try {
      const response = await brandingApi.getPresets();
      if (response.data?.success && response.data.data?.length > 0) {
        setPresets(response.data.data);
      }
      // Keep DEFAULT_PRESETS if API fails or returns empty
    } catch (err) {
      console.error('Failed to load presets from API, using defaults:', err);
      // Presets already initialized with DEFAULT_PRESETS
    }
  };

  const loadFonts = async () => {
    try {
      const response = await brandingApi.getFonts();
      if (response.data?.success && response.data.data?.length > 0) {
        setFonts(response.data.data);
      } else {
        // Use default fonts if API returns empty or fails
        setFonts(DEFAULT_FONTS);
      }
    } catch (err) {
      console.error('Failed to load fonts from API, using defaults:', err);
      setFonts(DEFAULT_FONTS);
    }
  };

  const applyCSSVariables = useCallback((theme) => {
    const root = document.documentElement;

    // Apply colors
    if (theme.colors) {
      Object.entries(theme.colors).forEach(([key, value]) => {
        const cssVar = CSS_VAR_MAP[key];
        if (cssVar && value) {
          root.style.setProperty(cssVar, value);
        }
      });
    }

    // Apply fonts
    if (theme.fonts) {
      Object.entries(theme.fonts).forEach(([key, value]) => {
        const cssVar = FONT_VAR_MAP[key];
        if (cssVar && value) {
          root.style.setProperty(cssVar, value);
          // Also load Google Font if needed
          loadGoogleFont(value);
        }
      });
    }

    // Apply custom CSS
    if (theme.custom_css) {
      let styleEl = document.getElementById('tenant-custom-css');
      if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = 'tenant-custom-css';
        document.head.appendChild(styleEl);
      }
      styleEl.textContent = theme.custom_css;
    } else {
      // Remove custom CSS if not present
      const existingStyle = document.getElementById('tenant-custom-css');
      if (existingStyle) {
        existingStyle.remove();
      }
    }

    // Update favicon if provided
    if (theme.logos?.favicon) {
      updateFavicon(theme.logos.favicon);
    }
  }, []);

  const loadGoogleFont = (fontFamily) => {
    // Extract font name from font family string
    const fontName = fontFamily.split(',')[0].trim().replace(/['"]/g, '');

    // Skip system fonts
    if (fontName === 'system-ui' || fontName === 'sans-serif' || fontName === 'serif') {
      return;
    }

    // Check if font is already loaded
    const existingLink = document.querySelector(`link[data-font="${fontName}"]`);
    if (existingLink) return;

    // Load from Google Fonts
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = `https://fonts.googleapis.com/css2?family=${fontName.replace(/\s+/g, '+')}:wght@400;500;600;700&display=swap`;
    link.setAttribute('data-font', fontName);
    document.head.appendChild(link);
  };

  const updateFavicon = (faviconUrl) => {
    let link = document.querySelector("link[rel*='icon']");
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = faviconUrl;
  };

  const updateBranding = async (updates) => {
    try {
      const response = await brandingApi.update(updates);
      if (response.data?.success) {
        setBranding(response.data.data);
        if (updates.dark_mode_enabled !== undefined) {
          setDarkMode(updates.dark_mode_enabled);
        }
        return { success: true, data: response.data.data };
      }
      return { success: false, error: 'Failed to update branding' };
    } catch (err) {
      console.error('Failed to update branding:', err);
      return { success: false, error: err.message };
    }
  };

  const applyPreset = async (presetName) => {
    // Find the preset to apply immediately
    const preset = presets.find(p => p.id === presetName);

    // Optimistic update: Apply preset colors instantly
    if (preset) {
      const optimisticBranding = {
        ...branding,
        colors: preset.colors,
        preset_theme: preset.id,
      };
      setPreviewBranding(optimisticBranding);
    }

    try {
      // Save to backend in background
      const response = await brandingApi.applyPreset(presetName);
      if (response.data?.success) {
        setBranding(response.data.data);
        setPreviewBranding(null); // Clear preview, use actual data
        return { success: true, data: response.data.data };
      }
      // Revert on failure
      setPreviewBranding(null);
      return { success: false, error: 'Failed to apply preset' };
    } catch (err) {
      console.error('Failed to apply preset:', err);
      // Revert on error
      setPreviewBranding(null);
      return { success: false, error: err.message };
    }
  };

  const uploadLogo = async (file, logoType = 'primary') => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('logo_type', logoType);

      const response = await brandingApi.uploadLogo(formData);
      if (response.data?.success) {
        // Reload branding to get updated logo URL
        await loadBranding();
        return { success: true, data: response.data.data };
      }
      return { success: false, error: 'Failed to upload logo' };
    } catch (err) {
      console.error('Failed to upload logo:', err);
      return { success: false, error: err.message };
    }
  };

  const resetBranding = async () => {
    try {
      const response = await brandingApi.reset();
      if (response.data?.success) {
        setBranding(response.data.data);
        setDarkMode(false);
        return { success: true };
      }
      return { success: false, error: 'Failed to reset branding' };
    } catch (err) {
      console.error('Failed to reset branding:', err);
      return { success: false, error: err.message };
    }
  };

  const setPreview = (previewData) => {
    setPreviewBranding(previewData);
  };

  const clearPreview = () => {
    setPreviewBranding(null);
    // Reapply actual branding
    if (branding) {
      applyCSSVariables(branding);
    }
  };

  const toggleDarkMode = async () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);

    // Save to server
    await updateBranding({ dark_mode_enabled: newDarkMode });
  };

  const value = useMemo(() => ({
    branding,
    previewBranding,
    presets,
    fonts,
    loading,
    error,
    darkMode,
    updateBranding,
    applyPreset,
    uploadLogo,
    resetBranding,
    setPreview,
    clearPreview,
    toggleDarkMode,
    refreshBranding: loadBranding,
  }), [branding, previewBranding, presets, fonts, loading, error, darkMode]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

export default ThemeContext;
