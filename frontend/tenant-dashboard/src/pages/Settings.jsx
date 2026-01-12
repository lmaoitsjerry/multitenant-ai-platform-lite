import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { usersApi, clientApi, templatesApi, authApi, tenantSettingsApi } from '../services/api';
import TeamSettings from './settings/TeamSettings';
import TemplateBuilder from './settings/TemplateBuilder';
import PrivacySettings from './settings/PrivacySettings';
import LogoCropModal from '../components/ui/LogoCropModal';
import Toggle from '../components/ui/Toggle';
import {
  UserIcon,
  BuildingOfficeIcon,
  BellIcon,
  KeyIcon,
  EnvelopeIcon,
  GlobeAltIcon,
  PaintBrushIcon,
  ShieldCheckIcon,
  CreditCardIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  SwatchIcon,
  PhotoIcon,
  SunIcon,
  MoonIcon,
  ArrowUpTrayIcon,
  XMarkIcon,
  EyeIcon,
  UsersIcon,
  DocumentTextIcon,
  WrenchScrewdriverIcon,
  BanknotesIcon,
  ChevronDownIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';

// Confirmation Modal Component
function ConfirmModal({ isOpen, title, message, onConfirm, onCancel }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="btn-secondary flex-1">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}

const tabs = [
  { id: 'profile', label: 'Profile', icon: UserIcon },
  { id: 'company', label: 'Company', icon: BuildingOfficeIcon },
  { id: 'team', label: 'Team', icon: UsersIcon, adminOnly: true },
  { id: 'branding', label: 'Branding', icon: PaintBrushIcon },
  { id: 'notifications', label: 'Notifications', icon: BellIcon },
  { id: 'privacy', label: 'Privacy', icon: ShieldCheckIcon },
  { id: 'integrations', label: 'Integrations', icon: KeyIcon },
  { id: 'billing', label: 'Billing', icon: CreditCardIcon, adminOnly: true },
];

// Branding sub-tabs
const brandingTabs = [
  { id: 'presets', label: 'Theme Presets', icon: SwatchIcon },
  { id: 'colors', label: 'Colors', icon: PaintBrushIcon },
  { id: 'logos', label: 'Logos', icon: PhotoIcon },
  { id: 'fonts', label: 'Typography', icon: 'Aa' },
  { id: 'templates', label: 'Templates', icon: DocumentTextIcon },
];

// Color picker component
function ColorPicker({ label, value, onChange, description }) {
  const [localValue, setLocalValue] = useState(value || '#7C3AED');

  useEffect(() => {
    if (value) setLocalValue(value);
  }, [value]);

  const handleChange = (newValue) => {
    setLocalValue(newValue);
    onChange(newValue);
  };

  return (
    <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
      <div>
        <p className="font-medium text-gray-900">{label}</p>
        {description && <p className="text-sm text-gray-500">{description}</p>}
      </div>
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={localValue}
          onChange={(e) => handleChange(e.target.value)}
          className="w-24 px-2 py-1 text-sm font-mono border border-gray-200 rounded"
        />
        <input
          type="color"
          value={localValue}
          onChange={(e) => handleChange(e.target.value)}
          className="w-10 h-10 rounded-lg border-2 border-gray-200 cursor-pointer"
        />
      </div>
    </div>
  );
}

// Font Selector component - shows each font in its actual typeface
function FontSelector({ value, onChange, fonts, label }) {
  const [isOpen, setIsOpen] = useState(false);
  const [loadedFonts, setLoadedFonts] = useState(new Set());
  const dropdownRef = useRef(null);

  // Load font when it needs to be displayed
  const loadFont = useCallback((fontFamily) => {
    if (!fontFamily || loadedFonts.has(fontFamily)) return;

    const fontName = fontFamily.split(',')[0].trim().replace(/['"]/g, '');
    if (fontName === 'system-ui' || fontName === 'sans-serif' || fontName === 'serif') return;

    // Check if font link already exists
    if (document.querySelector(`link[data-font="${fontName}"]`)) {
      setLoadedFonts(prev => new Set([...prev, fontFamily]));
      return;
    }

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = `https://fonts.googleapis.com/css2?family=${fontName.replace(/\s+/g, '+')}:wght@400;500;600;700&display=swap`;
    link.setAttribute('data-font', fontName);
    document.head.appendChild(link);
    setLoadedFonts(prev => new Set([...prev, fontFamily]));
  }, [loadedFonts]);

  // Load visible fonts when dropdown opens
  useEffect(() => {
    if (isOpen) {
      fonts.forEach(font => loadFont(font.value));
    }
  }, [isOpen, fonts, loadFont]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedFont = fonts.find(f => f.value === value) || fonts[0];

  return (
    <div className="relative" ref={dropdownRef}>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
      >
        <span style={{ fontFamily: value }} className="text-base">
          {selectedFont?.name || 'Select font'}
        </span>
        <ChevronDownIcon className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          {fonts.map((font) => (
            <button
              key={font.name}
              type="button"
              onClick={() => {
                onChange(font.value);
                setIsOpen(false);
              }}
              className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 ${
                value === font.value ? 'bg-primary-50' : ''
              }`}
              style={{ fontFamily: font.value }}
            >
              <span className="text-base">{font.name}</span>
              <span className="text-xs text-gray-400">{font.category}</span>
              {value === font.value && <CheckIcon className="w-4 h-4 text-primary-600 ml-2" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Logo upload component with crop modal
function LogoUpload({ label, currentUrl, onUpload, description, accept = "image/*", cropShape = "round" }) {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(currentUrl);
  const [uploading, setUploading] = useState(false);
  const [showCropModal, setShowCropModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);

  useEffect(() => {
    setPreview(currentUrl);
  }, [currentUrl]);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Read file and open crop modal
    const reader = new FileReader();
    reader.onload = (e) => {
      setSelectedImage(e.target.result);
      setShowCropModal(true);
    };
    reader.readAsDataURL(file);

    // Reset input so same file can be selected again
    e.target.value = '';
  };

  const handleCropComplete = async (croppedBlob) => {
    // Create a File object from the blob for upload
    const file = new File([croppedBlob], 'logo.png', { type: 'image/png' });

    // Show preview immediately
    const previewUrl = URL.createObjectURL(croppedBlob);
    setPreview(previewUrl);

    // Upload
    setUploading(true);
    await onUpload(file);
    setUploading(false);

    // Cleanup
    setSelectedImage(null);
  };

  const handleRemove = () => {
    setPreview(null);
    onUpload(null);
  };

  return (
    <div className="p-4 border border-theme rounded-lg bg-theme-surface">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="font-medium text-theme">{label}</p>
          {description && <p className="text-sm text-theme-muted">{description}</p>}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className={`w-24 h-24 border-2 border-dashed border-theme flex items-center justify-center bg-theme-surface-elevated overflow-hidden ${
          cropShape === 'round' ? 'rounded-full' : 'rounded-lg'
        }`}>
          {preview ? (
            <img src={preview} alt={label} className="w-full h-full object-cover" />
          ) : (
            <PhotoIcon className="w-8 h-8 text-theme-muted" />
          )}
        </div>

        <div className="flex flex-col gap-2">
          <button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="btn-secondary text-sm flex items-center gap-2"
          >
            <ArrowUpTrayIcon className="w-4 h-4" />
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
          {preview && (
            <button
              onClick={handleRemove}
              className="text-sm text-red-600 hover:text-red-700"
            >
              Remove
            </button>
          )}
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Crop Modal */}
      <LogoCropModal
        isOpen={showCropModal}
        onClose={() => {
          setShowCropModal(false);
          setSelectedImage(null);
        }}
        imageSrc={selectedImage}
        onCropComplete={handleCropComplete}
        cropShape={cropShape}
        aspectRatio={1}
        title={`Crop ${label}`}
      />
    </div>
  );
}

export default function Settings() {
  const { clientInfo, refreshClientInfo, updateClientInfo } = useApp();
  const { user, isAdmin, updateUser } = useAuth();
  const {
    branding,
    presets,
    fonts,
    darkMode,
    loading: themeLoading,
    updateBranding,
    applyPreset,
    uploadLogo,
    resetBranding,
    setPreview,
    clearPreview,
    toggleDarkMode,
  } = useTheme();

  // Filter tabs based on user role
  const visibleTabs = tabs.filter(tab => !tab.adminOnly || isAdmin);

  const [activeTab, setActiveTab] = useState('profile');
  const [brandingTab, setBrandingTab] = useState('presets');
  const [activeTemplateType, setActiveTemplateType] = useState('quote');
  const [editingTemplate, setEditingTemplate] = useState(null); // 'quote' or 'invoice' when editing
  const [templateView, setTemplateView] = useState('quote'); // 'quote' or 'invoice' for single view
  const [saving, setSaving] = useState(false);
  const [selectingPreset, setSelectingPreset] = useState(null);
  const [toast, setToast] = useState(null);
  const [pendingColors, setPendingColors] = useState({});
  const [pendingFonts, setPendingFonts] = useState({});
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null });

  // Track dirty state for unified save button
  const [dirtyFields, setDirtyFields] = useState({
    company: false,
    email: false,
    banking: false,
  });

  // Wrapper functions that mark fields as dirty when changed
  const updateCompany = (updates) => {
    setCompany(prev => ({ ...prev, ...updates }));
    setDirtyFields(prev => ({ ...prev, company: true }));
  };

  const updateEmailSettings = (updates) => {
    setEmailSettings(prev => ({ ...prev, ...updates }));
    setDirtyFields(prev => ({ ...prev, email: true }));
  };

  const updateBanking = (updates) => {
    setBanking(prev => ({ ...prev, ...updates }));
    setDirtyFields(prev => ({ ...prev, banking: true }));
  };

  // Template settings state
  const [templateSettings, setTemplateSettings] = useState({
    quote: {
      pdf_layout: 'standard',
      default_terms: '',
      default_notes: '',
      validity_days: 14,
      show_price_breakdown: true,
      show_transfers: true,
      show_company_address: true,
      show_website: true,
    },
    invoice: {
      pdf_layout: 'standard',
      default_terms: '',
      default_payment_instructions: '',
      default_notes: '',
      due_days: 14,
      show_banking_details: true,
      show_vat: true,
      show_traveler_details: true,
      show_company_address: true,
    },
  });
  const [templatesLoading, setTemplatesLoading] = useState(false);

  const [profile, setProfile] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: '',
    role: user?.role || 'consultant',
  });

  // Initialize profile from user context
  useEffect(() => {
    if (user) {
      setProfile({
        name: user.name || '',
        email: user.email || '',
        phone: '',
        role: user.role || 'consultant',
      });
    }
  }, [user]);

  const [company, setCompany] = useState({
    name: '',
    email: '',
    phone: '',
    website: '',
    address: '',
    currency: 'ZAR',
    timezone: 'Africa/Johannesburg',
  });

  const [banking, setBanking] = useState({
    bank_name: '',
    account_name: '',
    account_number: '',
    branch_code: '',
    swift_code: '',
    reference_prefix: '',
  });

  const [emailSettings, setEmailSettings] = useState({
    from_name: '',
    from_email: '',
    reply_to: '',
    quotes_email: '',
  });

  const [notifications, setNotifications] = useState({
    emailNewQuote: true,
    emailQuoteAccepted: true,
    emailNewInquiry: true,
    pushEnabled: false,
    dailyDigest: true,
  });

  useEffect(() => {
    if (clientInfo) {
      setCompany({
        name: clientInfo.client_name || '',
        email: clientInfo.support_email || '',
        phone: clientInfo.support_phone || '',
        website: clientInfo.website || '',
        address: '',
        currency: clientInfo.currency || 'ZAR',
        timezone: clientInfo.timezone || 'Africa/Johannesburg',
      });

      // Set banking details
      if (clientInfo.banking) {
        setBanking({
          bank_name: clientInfo.banking.bank_name || '',
          account_name: clientInfo.banking.account_name || '',
          account_number: clientInfo.banking.account_number || '',
          branch_code: clientInfo.banking.branch_code || '',
          swift_code: clientInfo.banking.swift_code || '',
          reference_prefix: clientInfo.banking.reference_prefix || '',
        });
      }

      // Set email settings
      if (clientInfo.email_settings) {
        setEmailSettings({
          from_name: clientInfo.email_settings.from_name || '',
          from_email: clientInfo.email_settings.from_email || '',
          reply_to: clientInfo.email_settings.reply_to || '',
          quotes_email: clientInfo.quotes_email || '',
        });
      }
    }
  }, [clientInfo]);

  // Initialize pending colors from branding
  useEffect(() => {
    if (branding?.colors) {
      setPendingColors(branding.colors);
    }
    if (branding?.fonts) {
      setPendingFonts(branding.fonts);
    }
  }, [branding]);

  // Load template settings when templates tab is active
  useEffect(() => {
    if (activeTab === 'branding' && brandingTab === 'templates') {
      loadTemplateSettings();
    }
  }, [activeTab, brandingTab]);

  const loadTemplateSettings = async () => {
    try {
      setTemplatesLoading(true);
      const response = await templatesApi.get();
      if (response.data?.success) {
        setTemplateSettings(response.data.data);
      }
    } catch (error) {
      console.error('Failed to load template settings:', error);
    } finally {
      setTemplatesLoading(false);
    }
  };

  const handleSaveTemplates = async () => {
    try {
      setSaving(true);
      const response = await templatesApi.update(templateSettings);
      if (response.data?.success) {
        setToast({ message: 'Template settings saved successfully!', type: 'success' });
      } else {
        setToast({ message: 'Failed to save template settings', type: 'error' });
      }
    } catch (error) {
      console.error('Failed to save template settings:', error);
      setToast({ message: 'Failed to save template settings', type: 'error' });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  const handleQuoteTemplateChange = (field, value) => {
    setTemplateSettings(prev => ({
      ...prev,
      quote: { ...prev.quote, [field]: value }
    }));
  };

  const handleInvoiceTemplateChange = (field, value) => {
    setTemplateSettings(prev => ({
      ...prev,
      invoice: { ...prev.invoice, [field]: value }
    }));
  };

  // Save profile settings
  const handleSaveProfile = async () => {
    if (!user?.id) {
      setToast({ message: 'User session not found. Please refresh.', type: 'error' });
      setTimeout(() => setToast(null), 3000);
      return;
    }

    setSaving(true);
    try {
      const updateData = { name: profile.name };
      if (profile.phone) {
        updateData.phone = profile.phone;
      }
      const response = await authApi.updateProfile(updateData);
      // Use the returned user data if available, otherwise construct from current user
      const updatedUser = response.data?.user || { ...user, name: profile.name };
      updateUser(updatedUser);
      setToast({ message: 'Profile saved successfully!', type: 'success' });
    } catch (err) {
      console.error('Failed to save profile:', err);
      setToast({ message: err.response?.data?.detail || 'Failed to save profile', type: 'error' });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  // Save company settings (persists to database)
  const handleSaveCompany = async () => {
    setSaving(true);
    try {
      // Persist to backend
      await tenantSettingsApi.updateCompany({
        company_name: company.name,
        support_email: company.email || null,
        support_phone: company.phone || null,
        website: company.website || null,
        currency: company.currency,
        timezone: company.timezone,
      });

      // Update the API cache so subsequent page loads use updated data
      const updates = {
        client_name: company.name,
        support_email: company.email,
        support_phone: company.phone,
        website: company.website,
        currency: company.currency,
        timezone: company.timezone,
      };
      clientApi.updateInfoCache(updates);

      // Update React context state for immediate UI updates
      updateClientInfo(updates);

      // Refresh client info to ensure consistency
      await refreshClientInfo();

      setToast({ message: 'Company settings saved!', type: 'success' });
    } catch (err) {
      setToast({ message: err.response?.data?.detail || 'Failed to save company settings', type: 'error' });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  // Save email settings
  const handleSaveEmailSettings = async () => {
    setSaving(true);
    try {
      await tenantSettingsApi.updateEmail({
        from_name: emailSettings.from_name || null,
        from_email: emailSettings.from_email || null,
        reply_to: emailSettings.reply_to || null,
        quotes_email: emailSettings.quotes_email || null,
      });
      setToast({ message: 'Email settings saved!', type: 'success' });
    } catch (err) {
      setToast({ message: err.response?.data?.detail || 'Failed to save email settings', type: 'error' });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  // Save banking settings
  const handleSaveBankingSettings = async () => {
    setSaving(true);
    try {
      await tenantSettingsApi.updateBanking({
        bank_name: banking.bank_name || null,
        account_name: banking.account_name || null,
        account_number: banking.account_number || null,
        branch_code: banking.branch_code || null,
        swift_code: banking.swift_code || null,
        reference_prefix: banking.reference_prefix || null,
      });
      setToast({ message: 'Banking details saved!', type: 'success' });
    } catch (err) {
      setToast({ message: err.response?.data?.detail || 'Failed to save banking details', type: 'error' });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  // Generic save for other settings
  const handleSave = async () => {
    setSaving(true);
    await new Promise(resolve => setTimeout(resolve, 500));
    setSaving(false);
    setToast({ message: 'Settings saved successfully!', type: 'success' });
    setTimeout(() => setToast(null), 3000);
  };

  // Unified save handler for all dirty fields
  const handleSaveAll = async () => {
    setSaving(true);
    const errors = [];

    try {
      // Save company settings if dirty
      if (dirtyFields.company) {
        try {
          await tenantSettingsApi.updateCompany({
            company_name: company.name,
            support_email: company.email || null,
            support_phone: company.phone || null,
            website: company.website || null,
            currency: company.currency,
            timezone: company.timezone,
          });
          setDirtyFields(prev => ({ ...prev, company: false }));
        } catch (err) {
          errors.push('Company settings');
        }
      }

      // Save email settings if dirty
      if (dirtyFields.email) {
        try {
          await tenantSettingsApi.updateEmail({
            from_name: emailSettings.from_name || null,
            from_email: emailSettings.from_email || null,
            reply_to: emailSettings.reply_to || null,
            quotes_email: emailSettings.quotes_email || null,
          });
          setDirtyFields(prev => ({ ...prev, email: false }));
        } catch (err) {
          errors.push('Email settings');
        }
      }

      // Save banking settings if dirty
      if (dirtyFields.banking) {
        try {
          await tenantSettingsApi.updateBanking({
            bank_name: banking.bank_name || null,
            account_name: banking.account_name || null,
            account_number: banking.account_number || null,
            branch_code: banking.branch_code || null,
            swift_code: banking.swift_code || null,
            reference_prefix: banking.reference_prefix || null,
          });
          setDirtyFields(prev => ({ ...prev, banking: false }));
        } catch (err) {
          errors.push('Banking details');
        }
      }

      // Clear cache and refresh after saves
      clientApi.clearInfoCache();
      await refreshClientInfo();

      if (errors.length > 0) {
        setToast({ message: `Failed to save: ${errors.join(', ')}`, type: 'error' });
      } else {
        setToast({ message: 'All settings saved successfully!', type: 'success' });
      }
    } catch (err) {
      setToast({ message: 'Failed to save settings', type: 'error' });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  // Check if any fields are dirty
  const hasUnsavedChanges = Object.values(dirtyFields).some(Boolean);

  // Branding handlers
  const handleApplyPreset = async (presetId) => {
    setSelectingPreset(presetId);
    setSaving(true);
    const result = await applyPreset(presetId);
    setSaving(false);
    setSelectingPreset(null);
    if (result.success) {
      const presetName = presets.find(p => p.id === presetId)?.name || presetId;
      setToast({ message: `Theme "${presetName}" applied!`, type: 'success' });
    } else {
      setToast({ message: result.error, type: 'error' });
    }
    setTimeout(() => setToast(null), 3000);
  };

  const handleColorChange = useCallback((colorKey, value) => {
    setPendingColors(prev => ({ ...prev, [colorKey]: value }));
  }, []);

  const handleFontChange = useCallback((fontKey, value) => {
    setPendingFonts(prev => ({ ...prev, [fontKey]: value }));
  }, []);

  const handleSaveColors = async () => {
    setSaving(true);
    const result = await updateBranding({ colors: pendingColors });
    setSaving(false);
    if (result.success) {
      setToast({ message: 'Colors saved successfully!', type: 'success' });
    } else {
      setToast({ message: result.error, type: 'error' });
    }
    setTimeout(() => setToast(null), 3000);
  };

  const handleSaveFonts = async () => {
    setSaving(true);
    const result = await updateBranding({ fonts: pendingFonts });
    setSaving(false);
    if (result.success) {
      setToast({ message: 'Fonts saved successfully!', type: 'success' });
    } else {
      setToast({ message: result.error, type: 'error' });
    }
    setTimeout(() => setToast(null), 3000);
  };

  const handleLogoUpload = async (file, logoType) => {
    if (!file) {
      // Remove logo
      await updateBranding({ [`logo_${logoType}_url`]: null });
      return;
    }
    const result = await uploadLogo(file, logoType);
    if (result.success) {
      setToast({ message: 'Logo uploaded successfully!', type: 'success' });
    } else {
      setToast({ message: result.error, type: 'error' });
    }
    setTimeout(() => setToast(null), 3000);
  };

  const handleResetBranding = () => {
    setConfirmModal({
      isOpen: true,
      title: 'Reset Branding',
      message: 'Are you sure you want to reset all branding to defaults? This cannot be undone.',
      onConfirm: async () => {
        setConfirmModal({ ...confirmModal, isOpen: false });
        setSaving(true);
        const result = await resetBranding();
        setSaving(false);
        if (result.success) {
          setToast({ message: 'Branding reset to defaults!', type: 'success' });
        } else {
          setToast({ message: result.error, type: 'error' });
        }
        setTimeout(() => setToast(null), 3000);
      }
    });
  };

  const togglePreviewMode = () => {
    if (isPreviewMode) {
      clearPreview();
      setIsPreviewMode(false);
    } else {
      setPreview({
        colors: pendingColors,
        fonts: pendingFonts,
      });
      setIsPreviewMode(true);
    }
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-theme">Settings</h1>
        <p className="text-theme-muted mt-1">Manage your account and preferences</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            {visibleTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span className="font-medium">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {/* Profile Settings */}
          {activeTab === 'profile' && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Profile Settings</h2>
              <div className="space-y-4 max-w-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    className="input"
                    placeholder="Your name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={profile.email}
                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    className="input"
                    placeholder="your@email.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={profile.phone}
                    onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                    className="input"
                    placeholder="+27 82 123 4567"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                  <input
                    type="text"
                    value={profile.role}
                    disabled
                    className="input bg-gray-50"
                  />
                </div>
                <button onClick={handleSaveProfile} disabled={saving} className="btn-primary">
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          )}

          {/* Company Settings */}
          {activeTab === 'company' && (
            <div className="space-y-6">
              {/* Basic Company Info */}
              <div className="card">
                <h2 className="text-lg font-semibold text-gray-900 mb-6">Company Information</h2>
                <div className="space-y-4 max-w-lg">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
                    <input
                      type="text"
                      value={company.name}
                      onChange={(e) => updateCompany({ name: e.target.value })}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Support Email</label>
                    <input
                      type="email"
                      value={company.email}
                      onChange={(e) => updateCompany({ email: e.target.value })}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Support Phone</label>
                    <input
                      type="tel"
                      value={company.phone}
                      onChange={(e) => updateCompany({ phone: e.target.value })}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
                    <input
                      type="url"
                      value={company.website}
                      onChange={(e) => updateCompany({ website: e.target.value })}
                      className="input"
                      placeholder="https://example.com"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
                      <select
                        value={company.currency}
                        onChange={(e) => updateCompany({ currency: e.target.value })}
                        className="input"
                      >
                        <option value="ZAR">ZAR (R)</option>
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                      <select
                        value={company.timezone}
                        onChange={(e) => updateCompany({ timezone: e.target.value })}
                        className="input"
                      >
                        <option value="Africa/Johannesburg">Africa/Johannesburg</option>
                        <option value="UTC">UTC</option>
                        <option value="Europe/London">Europe/London</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              {/* Email Settings */}
              <div className="card">
                <div className="flex items-center gap-2 mb-6">
                  <EnvelopeIcon className="w-5 h-5 text-primary-600" />
                  <h2 className="text-lg font-semibold text-gray-900">Email Settings</h2>
                </div>
                <p className="text-sm text-gray-500 mb-4">
                  These email addresses are used for sending quotes, invoices, and customer communications.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">From Name</label>
                    <input
                      type="text"
                      value={emailSettings.from_name}
                      onChange={(e) => updateEmailSettings({ from_name: e.target.value })}
                      className="input"
                      placeholder="Company Name"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">From Email</label>
                    <input
                      type="email"
                      value={emailSettings.from_email}
                      onChange={(e) => updateEmailSettings({ from_email: e.target.value })}
                      className="input"
                      placeholder="info@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Quotes Email</label>
                    <input
                      type="email"
                      value={emailSettings.quotes_email}
                      onChange={(e) => updateEmailSettings({ quotes_email: e.target.value })}
                      className="input"
                      placeholder="quotes@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Reply-To Address</label>
                    <input
                      type="email"
                      value={emailSettings.reply_to}
                      onChange={(e) => updateEmailSettings({ reply_to: e.target.value })}
                      className="input"
                      placeholder="reply@company.com"
                    />
                  </div>
                </div>
              </div>

              {/* Banking Details */}
              <div className="card">
                <div className="flex items-center gap-2 mb-6">
                  <BanknotesIcon className="w-5 h-5 text-primary-600" />
                  <h2 className="text-lg font-semibold text-gray-900">Banking Details</h2>
                </div>
                <p className="text-sm text-gray-500 mb-4">
                  These banking details appear on invoices and quotes for customer payments.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Bank Name</label>
                    <input
                      type="text"
                      value={banking.bank_name}
                      onChange={(e) => updateBanking({ bank_name: e.target.value })}
                      className="input"
                      placeholder="First National Bank"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Account Name</label>
                    <input
                      type="text"
                      value={banking.account_name}
                      onChange={(e) => updateBanking({ account_name: e.target.value })}
                      className="input"
                      placeholder="Company Name (Pty) Ltd"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Account Number</label>
                    <input
                      type="text"
                      value={banking.account_number}
                      onChange={(e) => updateBanking({ account_number: e.target.value })}
                      className="input"
                      placeholder="1234567890"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Branch Code</label>
                    <input
                      type="text"
                      value={banking.branch_code}
                      onChange={(e) => updateBanking({ branch_code: e.target.value })}
                      className="input"
                      placeholder="250655"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SWIFT Code</label>
                    <input
                      type="text"
                      value={banking.swift_code}
                      onChange={(e) => updateBanking({ swift_code: e.target.value })}
                      className="input"
                      placeholder="FIRNZAJJ"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Reference Prefix</label>
                    <input
                      type="text"
                      value={banking.reference_prefix}
                      onChange={(e) => updateBanking({ reference_prefix: e.target.value })}
                      className="input"
                      placeholder="INV-"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Team Settings (Admin only) */}
          {activeTab === 'team' && isAdmin && (
            <TeamSettings />
          )}

          {/* Branding Settings */}
          {activeTab === 'branding' && (
            <div className="space-y-6">
              {/* Branding Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Branding & Appearance</h2>
                  <p className="text-sm text-gray-500">Customize your platform's look and feel</p>
                </div>
                <div className="flex items-center gap-3">
                  {/* Dark Mode Toggle */}
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-theme bg-theme-surface">
                    {darkMode ? (
                      <MoonIcon className="w-5 h-5 text-indigo-600" />
                    ) : (
                      <SunIcon className="w-5 h-5 text-amber-500" />
                    )}
                    <span className="text-sm text-theme-secondary">{darkMode ? 'Dark' : 'Light'}</span>
                    <Toggle
                      checked={darkMode}
                      onChange={toggleDarkMode}
                      size="sm"
                    />
                  </div>

                  {/* Reset Button */}
                  <button
                    onClick={handleResetBranding}
                    disabled={saving}
                    className="btn-secondary text-sm flex items-center gap-2"
                  >
                    <ArrowPathIcon className="w-4 h-4" />
                    Reset
                  </button>
                </div>
              </div>

              {/* Branding Sub-tabs */}
              <div className="border-b border-gray-200">
                <nav className="flex gap-4">
                  {brandingTabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setBrandingTab(tab.id)}
                      className={`flex items-center gap-2 px-1 py-3 border-b-2 transition-colors ${
                        brandingTab === tab.id
                          ? 'border-primary-600 text-primary-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {typeof tab.icon === 'string' ? (
                        <span className="text-sm font-bold">{tab.icon}</span>
                      ) : (
                        <tab.icon className="w-4 h-4" />
                      )}
                      <span className="font-medium text-sm">{tab.label}</span>
                    </button>
                  ))}
                </nav>
              </div>

              {/* Theme Presets */}
              {brandingTab === 'presets' && (
                <div className="card">
                  <h3 className="font-semibold text-gray-900 mb-4">Choose a Theme Preset</h3>
                  <p className="text-sm text-gray-500 mb-6">
                    Select a pre-designed theme to quickly apply a complete look, or customize individual settings below.
                  </p>

                  {themeLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {presets.map((preset) => {
                        const isSelected = branding?.preset_theme === preset.id;
                        const isSelecting = selectingPreset === preset.id;
                        const isHighlighted = isSelected || isSelecting;

                        return (
                          <button
                            key={preset.id}
                            onClick={() => handleApplyPreset(preset.id)}
                            disabled={saving}
                            className={`text-left p-4 border-2 rounded-xl transition-all hover:shadow-md relative ${
                              isHighlighted
                                ? 'border-primary-600 bg-primary-50 ring-2 ring-primary-200'
                                : 'border-gray-200 hover:border-gray-300'
                            } ${isSelecting ? 'opacity-75' : ''}`}
                          >
                            {/* Loading overlay */}
                            {isSelecting && (
                              <div className="absolute inset-0 bg-white/50 rounded-xl flex items-center justify-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                              </div>
                            )}

                            {/* Preview Gradient */}
                            <div
                              className="h-16 rounded-lg mb-3"
                              style={{ background: preset.preview_gradient }}
                            />

                            {/* Theme Info */}
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-semibold text-gray-900">{preset.name}</h4>
                              {isSelected && !isSelecting && (
                                <CheckCircleIcon className="w-5 h-5 text-primary-600" />
                              )}
                              {isSelecting && (
                                <span className="text-xs text-primary-600 font-medium">Applying...</span>
                              )}
                            </div>
                            <p className="text-sm text-gray-500">{preset.description}</p>

                            {/* Color Swatches */}
                            <div className="flex gap-1 mt-3">
                              {Object.entries(preset.colors).slice(0, 5).map(([key, color]) => (
                                <div
                                  key={key}
                                  className="w-6 h-6 rounded-full border border-white shadow-sm"
                                  style={{ backgroundColor: color }}
                                  title={key}
                                />
                              ))}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Colors */}
              {brandingTab === 'colors' && (
                <div className="card">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="font-semibold text-gray-900">Custom Colors</h3>
                      <p className="text-sm text-gray-500">Fine-tune individual colors to match your brand</p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={togglePreviewMode}
                        className={`btn-secondary text-sm flex items-center gap-2 ${isPreviewMode ? 'bg-primary-100 text-primary-700' : ''}`}
                      >
                        <EyeIcon className="w-4 h-4" />
                        {isPreviewMode ? 'Exit Preview' : 'Preview'}
                      </button>
                      <button
                        onClick={handleSaveColors}
                        disabled={saving}
                        className="btn-primary text-sm"
                      >
                        {saving ? 'Saving...' : 'Save Colors'}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-3">Primary Colors</h4>
                      <div className="space-y-3">
                        <ColorPicker
                          label="Primary"
                          description="Main brand color"
                          value={pendingColors.primary}
                          onChange={(v) => handleColorChange('primary', v)}
                        />
                        <ColorPicker
                          label="Primary Light"
                          description="Lighter variant for hover states"
                          value={pendingColors.primary_light}
                          onChange={(v) => handleColorChange('primary_light', v)}
                        />
                        <ColorPicker
                          label="Primary Dark"
                          description="Darker variant for active states"
                          value={pendingColors.primary_dark}
                          onChange={(v) => handleColorChange('primary_dark', v)}
                        />
                      </div>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-3">Secondary Colors</h4>
                      <div className="space-y-3">
                        <ColorPicker
                          label="Secondary"
                          description="Secondary accent color"
                          value={pendingColors.secondary}
                          onChange={(v) => handleColorChange('secondary', v)}
                        />
                        <ColorPicker
                          label="Accent"
                          description="Highlight and call-to-action color"
                          value={pendingColors.accent}
                          onChange={(v) => handleColorChange('accent', v)}
                        />
                      </div>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-3">Status Colors</h4>
                      <div className="space-y-3">
                        <ColorPicker
                          label="Success"
                          description="Positive actions and states"
                          value={pendingColors.success}
                          onChange={(v) => handleColorChange('success', v)}
                        />
                        <ColorPicker
                          label="Warning"
                          description="Warning messages"
                          value={pendingColors.warning}
                          onChange={(v) => handleColorChange('warning', v)}
                        />
                        <ColorPicker
                          label="Error"
                          description="Error states and messages"
                          value={pendingColors.error}
                          onChange={(v) => handleColorChange('error', v)}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Logos */}
              {brandingTab === 'logos' && (
                <div className="card">
                  <h3 className="font-semibold text-gray-900 mb-2">Logo & Branding Assets</h3>
                  <p className="text-sm text-gray-500 mb-6">
                    Upload your logos for different contexts. Recommended formats: PNG, SVG. Max size: 2MB.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <LogoUpload
                      label="Primary Logo"
                      description="Used in header and light backgrounds"
                      currentUrl={branding?.logos?.primary}
                      onUpload={(file) => handleLogoUpload(file, 'primary')}
                      cropShape="round"
                    />
                    <LogoUpload
                      label="Dark Mode Logo"
                      description="Used on dark backgrounds (optional)"
                      currentUrl={branding?.logos?.dark}
                      onUpload={(file) => handleLogoUpload(file, 'dark')}
                      cropShape="round"
                    />
                    <LogoUpload
                      label="Favicon"
                      description="Browser tab icon (32x32 recommended)"
                      currentUrl={branding?.logos?.favicon}
                      onUpload={(file) => handleLogoUpload(file, 'favicon')}
                      accept="image/png,image/x-icon,image/svg+xml"
                      cropShape="rect"
                    />
                    <LogoUpload
                      label="Email Logo"
                      description="Used in email templates"
                      currentUrl={branding?.logos?.email}
                      onUpload={(file) => handleLogoUpload(file, 'email')}
                      cropShape="rect"
                    />
                  </div>
                </div>
              )}

              {/* Typography */}
              {brandingTab === 'fonts' && (
                <div className="card">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="font-semibold text-gray-900">Typography</h3>
                      <p className="text-sm text-gray-500">Choose fonts for headings and body text</p>
                    </div>
                    <button
                      onClick={handleSaveFonts}
                      disabled={saving}
                      className="btn-primary text-sm"
                    >
                      {saving ? 'Saving...' : 'Save Fonts'}
                    </button>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <FontSelector
                        label="Heading Font"
                        value={pendingFonts.heading || 'Inter, system-ui, sans-serif'}
                        onChange={(value) => handleFontChange('heading', value)}
                        fonts={fonts}
                      />
                      <div
                        className="mt-3 p-4 bg-gray-50 rounded-lg"
                        style={{ fontFamily: pendingFonts.heading || 'Inter, system-ui, sans-serif' }}
                      >
                        <p className="text-2xl font-bold">The quick brown fox</p>
                        <p className="text-lg font-semibold">jumps over the lazy dog</p>
                      </div>
                    </div>

                    <div>
                      <FontSelector
                        label="Body Font"
                        value={pendingFonts.body || 'Inter, system-ui, sans-serif'}
                        onChange={(value) => handleFontChange('body', value)}
                        fonts={fonts}
                      />
                      <div
                        className="mt-3 p-4 bg-gray-50 rounded-lg"
                        style={{ fontFamily: pendingFonts.body || 'Inter, system-ui, sans-serif' }}
                      >
                        <p className="text-base">
                          Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
                          tempor incididunt ut labore et dolore magna aliqua.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Templates */}
              {brandingTab === 'templates' && !editingTemplate && (
                <div className="space-y-6">
                  {/* Header with Toggle */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-1">Document Templates</h3>
                      <p className="text-sm text-gray-500">
                        Customize how your documents look
                      </p>
                    </div>

                    {/* Toggle between Quote and Invoice */}
                    <div className="flex bg-gray-100 rounded-lg p-1">
                      <button
                        onClick={() => setTemplateView('quote')}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                          templateView === 'quote'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-600 hover:text-gray-900'
                        }`}
                      >
                        Quote Template
                      </button>
                      <button
                        onClick={() => setTemplateView('invoice')}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                          templateView === 'invoice'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-600 hover:text-gray-900'
                        }`}
                      >
                        Invoice Template
                      </button>
                    </div>
                  </div>

                  {/* Single Template Preview - Large */}
                  <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                    {/* Large Document Preview Area */}
                    <div className="bg-gradient-to-b from-gray-50 to-gray-100 p-8 flex items-center justify-center min-h-[500px]">
                      <div className="w-full max-w-md bg-white rounded-lg shadow-lg p-8 space-y-4">
                        {/* Header */}
                        <div className="flex justify-between items-start border-b pb-4">
                          <div>
                            <div className="h-8 w-20 bg-primary-200 rounded mb-2"></div>
                            <div className="text-xs text-gray-400">Company Name</div>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold text-primary-600">
                              {templateView === 'quote' ? 'QUOTATION' : 'TAX INVOICE'}
                            </div>
                            <div className="text-sm text-gray-500">#{templateView === 'quote' ? 'Q-2024-001' : 'INV-2024-001'}</div>
                            <div className="text-xs text-gray-400 mt-1">Date: {new Date().toLocaleDateString()}</div>
                          </div>
                        </div>

                        {/* Customer Info */}
                        <div className="grid grid-cols-2 gap-4 py-3">
                          <div>
                            <div className="text-xs font-medium text-gray-500 mb-1">Bill To:</div>
                            <div className="h-3 bg-gray-200 rounded w-24 mb-1"></div>
                            <div className="h-2 bg-gray-100 rounded w-32"></div>
                            <div className="h-2 bg-gray-100 rounded w-28 mt-1"></div>
                          </div>
                          {templateView === 'quote' && (
                            <div>
                              <div className="text-xs font-medium text-gray-500 mb-1">Travel Details:</div>
                              <div className="h-2 bg-gray-100 rounded w-28 mb-1"></div>
                              <div className="h-2 bg-gray-100 rounded w-24"></div>
                            </div>
                          )}
                        </div>

                        {/* Line Items Table */}
                        <div className="border rounded-lg overflow-hidden">
                          <div className="bg-gray-50 px-3 py-2 flex text-xs font-medium text-gray-600">
                            <span className="flex-1">Description</span>
                            <span className="w-16 text-right">Qty</span>
                            <span className="w-20 text-right">Price</span>
                            <span className="w-20 text-right">Total</span>
                          </div>
                          <div className="divide-y divide-gray-100">
                            <div className="px-3 py-2 flex items-center text-sm">
                              <div className="flex-1">
                                <div className="h-2 bg-gray-200 rounded w-32"></div>
                              </div>
                              <div className="w-16 text-right text-gray-500">2</div>
                              <div className="w-20 text-right text-gray-500">R 1,500</div>
                              <div className="w-20 text-right font-medium">R 3,000</div>
                            </div>
                            <div className="px-3 py-2 flex items-center text-sm">
                              <div className="flex-1">
                                <div className="h-2 bg-gray-200 rounded w-28"></div>
                              </div>
                              <div className="w-16 text-right text-gray-500">1</div>
                              <div className="w-20 text-right text-gray-500">R 2,500</div>
                              <div className="w-20 text-right font-medium">R 2,500</div>
                            </div>
                          </div>
                        </div>

                        {/* Totals */}
                        <div className="flex justify-end">
                          <div className="w-48 space-y-1">
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-500">Subtotal:</span>
                              <span>R 5,500</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-500">VAT (15%):</span>
                              <span>R 825</span>
                            </div>
                            <div className="flex justify-between text-sm font-bold border-t pt-1 mt-1">
                              <span>Total:</span>
                              <span className="text-primary-600">R 6,325</span>
                            </div>
                          </div>
                        </div>

                        {/* Footer */}
                        {templateView === 'invoice' && (
                          <div className="border-t pt-4 mt-4">
                            <div className="text-xs font-medium text-gray-500 mb-1">Banking Details:</div>
                            <div className="text-xs text-gray-400 space-y-0.5">
                              <div className="h-2 bg-gray-100 rounded w-40"></div>
                              <div className="h-2 bg-gray-100 rounded w-32"></div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Footer with Edit Button */}
                    <div className="p-6 border-t border-gray-100 bg-white">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-gray-900">
                            {templateView === 'quote' ? 'Quote Template' : 'Invoice Template'}
                          </h4>
                          <p className="text-sm text-gray-500">
                            Drag sections to reorder, toggle visibility, and configure options
                          </p>
                        </div>
                        <button
                          onClick={() => setEditingTemplate(templateView)}
                          className="btn-primary"
                        >
                          <WrenchScrewdriverIcon className="w-4 h-4 mr-2" />
                          Edit Template
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Template Editor Modal */}
              {brandingTab === 'templates' && editingTemplate && (
                <div className="fixed inset-0 z-50 bg-white flex flex-col">
                  {/* Editor Header */}
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
                    <button
                      onClick={() => setEditingTemplate(null)}
                      className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                      Back to Templates
                    </button>
                    <h2 className="font-semibold text-gray-900">
                      {editingTemplate === 'quote' ? 'Quote Template' : 'Invoice Template'}
                    </h2>
                    <div className="w-32"></div>
                  </div>
                  {/* Template Builder */}
                  <div className="flex-1 overflow-hidden">
                    <TemplateBuilder
                      key={editingTemplate}
                      templateType={editingTemplate}
                      onClose={() => setEditingTemplate(null)}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Notification Settings */}
          {activeTab === 'notifications' && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Notification Settings</h2>
              <div className="space-y-4 max-w-lg">
                <div className="flex items-center justify-between py-3 border-b border-gray-100">
                  <div>
                    <p className="font-medium text-gray-900">New quote requests</p>
                    <p className="text-sm text-gray-500">Get notified when a new quote is requested</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifications.emailNewQuote}
                      onChange={(e) => setNotifications({ ...notifications, emailNewQuote: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-500 rounded-full peer peer-checked:bg-primary-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-gray-100">
                  <div>
                    <p className="font-medium text-gray-900">Quote accepted</p>
                    <p className="text-sm text-gray-500">Get notified when a customer accepts a quote</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifications.emailQuoteAccepted}
                      onChange={(e) => setNotifications({ ...notifications, emailQuoteAccepted: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-500 rounded-full peer peer-checked:bg-primary-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-gray-100">
                  <div>
                    <p className="font-medium text-gray-900">New customer inquiries</p>
                    <p className="text-sm text-gray-500">Get notified for new email inquiries</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifications.emailNewInquiry}
                      onChange={(e) => setNotifications({ ...notifications, emailNewInquiry: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-500 rounded-full peer peer-checked:bg-primary-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium text-gray-900">Daily digest</p>
                    <p className="text-sm text-gray-500">Receive a daily summary email</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifications.dailyDigest}
                      onChange={(e) => setNotifications({ ...notifications, dailyDigest: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-500 rounded-full peer peer-checked:bg-primary-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                  </label>
                </div>
                <button onClick={handleSave} disabled={saving} className="btn-primary mt-4">
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          )}

          {/* Privacy & Data Rights (GDPR/POPIA) */}
          {activeTab === 'privacy' && (
            <PrivacySettings />
          )}

          {/* Integrations */}
          {activeTab === 'integrations' && (
            <div className="space-y-6">
              <div className="card">
                <h2 className="text-lg font-semibold text-gray-900 mb-6">Integrations</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <EnvelopeIcon className="w-6 h-6 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">SendGrid</p>
                        <p className="text-sm text-gray-500">Email delivery service</p>
                      </div>
                    </div>
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <CheckCircleIcon className="w-5 h-5" />
                      Connected
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                        <GlobeAltIcon className="w-6 h-6 text-primary-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">Google Cloud</p>
                        <p className="text-sm text-gray-500">AI and data services</p>
                      </div>
                    </div>
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <CheckCircleIcon className="w-5 h-5" />
                      Connected
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                        <ShieldCheckIcon className="w-6 h-6 text-orange-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">Supabase</p>
                        <p className="text-sm text-gray-500">Database and authentication</p>
                      </div>
                    </div>
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <CheckCircleIcon className="w-5 h-5" />
                      Connected
                    </span>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* Billing */}
          {activeTab === 'billing' && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Billing & Subscription</h2>
              <div className="space-y-6">
                <div className="p-4 bg-primary-50 border border-primary-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-primary-900">Professional Plan</p>
                      <p className="text-sm text-primary-700">Unlimited quotes, 3 AI agents, priority support</p>
                    </div>
                    <span className="text-2xl font-bold text-primary-900">R 2,999/mo</span>
                  </div>
                </div>

                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Usage This Month</h3>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Quotes Generated</span>
                        <span className="font-medium">45 / Unlimited</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full">
                        <div className="h-full bg-primary-600 rounded-full" style={{ width: '45%' }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">AI Chat Messages</span>
                        <span className="font-medium">234 / 1000</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full">
                        <div className="h-full bg-primary-600 rounded-full" style={{ width: '23%' }} />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-4">
                  <button className="btn-secondary">Manage Subscription</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Floating Save Button */}
      <div className="fixed bottom-6 right-6 z-40">
        <button
          type="button"
          onClick={handleSaveAll}
          disabled={saving || !hasUnsavedChanges}
          className={`btn-primary px-6 py-3 text-base font-medium shadow-lg transition-all ${
            !hasUnsavedChanges
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:shadow-xl hover:-translate-y-0.5'
          }`}
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, isOpen: false })}
      />

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-20 right-6 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          <CheckCircleIcon className="w-5 h-5" />
          {toast.message}
        </div>
      )}
    </div>
  );
}
