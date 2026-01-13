import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BuildingOfficeIcon,
  EnvelopeIcon,
  RocketLaunchIcon,
  CheckCircleIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  ArrowPathIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { onboardingApi } from '../../services/api';

const STORAGE_KEY = 'tenant_onboarding_progress_lite';

// Lite version: 3 steps only
const STEPS = [
  { id: 1, name: 'Company Profile', icon: BuildingOfficeIcon },
  { id: 2, name: 'Email Settings', icon: EnvelopeIcon },
  { id: 3, name: 'Review & Launch', icon: RocketLaunchIcon },
];

// Default form data (Lite version - no AI agent, no KB)
const getDefaultData = () => ({
  company: {
    company_name: '',
    support_email: '',
    support_phone: '',
    website_url: '',
    timezone: 'Africa/Johannesburg',
    currency: 'ZAR',
    brand_theme: {
      theme_id: 'royal-purple',
      primary: '#7C3AED',
      secondary: '#6D28D9',
      accent: '#A78BFA',
    },
  },
  email: {
    from_name: '',
    from_email: '',
    email_signature: '',
    auto_send_quotes: true,
    quote_validity_days: 14,
    sendgrid_api_key: '',
  },
  admin_email: '',
  admin_password: '',
  admin_name: '',
});

// Fallback themes
const DEFAULT_THEMES = [
  { id: 'ocean-blue', name: 'Ocean Blue', description: 'Professional and trustworthy', primary: '#0EA5E9', secondary: '#0284C7', accent: '#38BDF8' },
  { id: 'safari-gold', name: 'Safari Gold', description: 'Warm and adventurous', primary: '#D97706', secondary: '#B45309', accent: '#FBBF24' },
  { id: 'sunset-orange', name: 'Sunset Orange', description: 'Energetic and vibrant', primary: '#EA580C', secondary: '#C2410C', accent: '#FB923C' },
  { id: 'forest-green', name: 'Forest Green', description: 'Natural and eco-friendly', primary: '#059669', secondary: '#047857', accent: '#34D399' },
  { id: 'royal-purple', name: 'Royal Purple', description: 'Luxurious and premium', primary: '#7C3AED', secondary: '#6D28D9', accent: '#A78BFA' },
  { id: 'teal-modern', name: 'Teal Modern', description: 'Fresh and contemporary', primary: '#0D9488', secondary: '#0F766E', accent: '#2DD4BF' },
];

export default function TenantOnboarding() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState(getDefaultData());
  const [themes, setThemes] = useState(DEFAULT_THEMES);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [provisioningStatus, setProvisioningStatus] = useState(null);

  // Load saved progress on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setFormData(prev => ({ ...prev, ...parsed.formData }));
        setCurrentStep(parsed.currentStep || 1);
      } catch (e) {
        console.error('Failed to restore progress:', e);
      }
    }
    loadThemes();
  }, []);

  // Save progress on changes
  useEffect(() => {
    if (formData.company.company_name || formData.admin_email) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        formData,
        currentStep,
      }));
    }
  }, [formData, currentStep]);

  const loadThemes = async () => {
    try {
      const response = await onboardingApi.getThemes();
      if (response.data?.themes?.length > 0) {
        setThemes(response.data.themes);
      }
    } catch (error) {
      console.error('Failed to load themes, using defaults');
    }
  };

  const updateField = (section, field, value) => {
    setFormData(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));
    setErrors(prev => ({ ...prev, [`${section}.${field}`]: null }));
  };

  const updateTopLevel = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: null }));
  };

  const validateStep = (step) => {
    const newErrors = {};

    if (step === 1) {
      if (!formData.company.company_name?.trim()) {
        newErrors['company.company_name'] = 'Company name is required';
      }
      if (!formData.company.support_email?.trim()) {
        newErrors['company.support_email'] = 'Support email is required';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.company.support_email)) {
        newErrors['company.support_email'] = 'Please enter a valid email';
      }
      if (!formData.admin_email?.trim()) {
        newErrors['admin_email'] = 'Admin email is required';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.admin_email)) {
        newErrors['admin_email'] = 'Please enter a valid email';
      }
      if (!formData.admin_password) {
        newErrors['admin_password'] = 'Admin password is required';
      } else if (formData.admin_password.length < 8) {
        newErrors['admin_password'] = 'Password must be at least 8 characters';
      }
    }

    if (step === 2) {
      if (!formData.email.from_name?.trim()) {
        newErrors['email.from_name'] = 'From name is required';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, STEPS.length));
    }
  };

  const handleBack = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const handleLaunch = async () => {
    // Validate final step
    if (!validateStep(1) || !validateStep(2)) {
      setProvisioningStatus({
        step: 'error',
        message: 'Please complete all required fields',
        errors: Object.values(errors).filter(Boolean),
      });
      return;
    }

    setLoading(true);
    setProvisioningStatus({ step: 'starting', message: 'Starting setup...' });

    try {
      // Build the request for Lite version
      const request = {
        company: {
          ...formData.company,
          brand_theme: formData.company.brand_theme,
        },
        // Lite version: minimal agent config (required by backend)
        agents: {
          inbound_description: `Travel consultant for ${formData.company.company_name}`,
          inbound_prompt: `You are a helpful travel assistant for ${formData.company.company_name}. Help customers with travel inquiries and generate quotes.`,
          inbound_agent_name: 'Assistant',
        },
        email: formData.email,
        // Lite version: skip knowledge base
        knowledge_base: {
          categories: ['Destinations', 'Hotels', 'FAQs'],
          skip_initial_setup: true,
        },
        // No voice features in Lite
        provision_phone: false,
        // Outbound disabled in Lite
        outbound: {
          enabled: false,
          timing: 'next_business_day',
          call_window_start: '09:00',
          call_window_end: '17:00',
          call_days: ['mon', 'tue', 'wed', 'thu', 'fri'],
          max_attempts: 2,
          min_quote_value: 0,
        },
        // Admin credentials
        admin_email: formData.admin_email,
        admin_password: formData.admin_password,
        admin_name: formData.admin_name || formData.company.company_name + ' Admin',
      };

      setProvisioningStatus({ step: 'config', message: 'Creating your platform...' });

      const response = await onboardingApi.complete(request);

      if (response.data?.success || response.data?.tenant_id) {
        setProvisioningStatus({
          step: 'complete',
          message: 'Setup complete!',
          resources: response.data.resources || { tenant_id: response.data.tenant_id },
          tenant_id: response.data.tenant_id,
        });
        localStorage.removeItem(STORAGE_KEY);
      } else {
        throw new Error(response.data?.message || 'Setup failed');
      }
    } catch (error) {
      console.error('Onboarding failed:', error);
      setProvisioningStatus({
        step: 'error',
        message: error.response?.data?.detail || error.message || 'Failed to complete setup',
        errors: error.response?.data?.errors || [error.message],
      });
    } finally {
      setLoading(false);
    }
  };

  const resetOnboarding = () => {
    if (window.confirm('Are you sure you want to start over? All progress will be lost.')) {
      localStorage.removeItem(STORAGE_KEY);
      setFormData(getDefaultData());
      setCurrentStep(1);
      setErrors({});
      setProvisioningStatus(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Platform Setup</h1>
              <p className="text-gray-500 mt-1">Get your travel platform ready in minutes</p>
            </div>
            <button
              onClick={resetOnboarding}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Start Over
            </button>
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center justify-center gap-4">
            {STEPS.map((step, idx) => (
              <div key={step.id} className="flex items-center">
                <button
                  onClick={() => currentStep > step.id && setCurrentStep(step.id)}
                  disabled={currentStep < step.id}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                    currentStep === step.id
                      ? 'bg-purple-100 text-purple-700'
                      : currentStep > step.id
                      ? 'text-green-600 hover:bg-green-50 cursor-pointer'
                      : 'text-gray-400 cursor-not-allowed'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      currentStep === step.id
                        ? 'bg-purple-600 text-white'
                        : currentStep > step.id
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {currentStep > step.id ? (
                      <CheckCircleIcon className="w-5 h-5" />
                    ) : (
                      step.id
                    )}
                  </div>
                  <span className="hidden sm:block font-medium">{step.name}</span>
                </button>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`w-12 h-0.5 mx-2 ${
                      currentStep > step.id ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
          {currentStep === 1 && (
            <Step1CompanyProfile
              formData={formData}
              updateField={updateField}
              updateTopLevel={updateTopLevel}
              errors={errors}
              themes={themes}
            />
          )}
          {currentStep === 2 && (
            <Step2EmailSettings
              formData={formData}
              updateField={updateField}
              errors={errors}
            />
          )}
          {currentStep === 3 && (
            <Step3Review
              formData={formData}
              provisioningStatus={provisioningStatus}
              onLaunch={handleLaunch}
              loading={loading}
            />
          )}
        </div>

        {/* Navigation - hide on step 3 when showing results */}
        {!(currentStep === 3 && (provisioningStatus?.step === 'complete' || provisioningStatus?.step === 'error' || loading)) && (
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={handleBack}
              disabled={currentStep === 1}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium ${
                currentStep === 1
                  ? 'text-gray-300 cursor-not-allowed'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <ArrowLeftIcon className="w-5 h-5" />
              Back
            </button>

            {currentStep < 3 ? (
              <button
                onClick={handleNext}
                className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
              >
                Next
                <ArrowRightIcon className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handleLaunch}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium disabled:opacity-50"
              >
                <RocketLaunchIcon className="w-5 h-5" />
                Launch Platform
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ==================== Step 1: Company Profile ====================
function Step1CompanyProfile({ formData, updateField, updateTopLevel, errors, themes }) {
  const timezones = [
    { value: 'Africa/Johannesburg', label: 'South Africa (SAST)' },
    { value: 'Africa/Lagos', label: 'Nigeria (WAT)' },
    { value: 'Africa/Nairobi', label: 'Kenya (EAT)' },
    { value: 'Europe/London', label: 'UK (GMT/BST)' },
    { value: 'America/New_York', label: 'US Eastern' },
  ];

  const currencies = [
    { value: 'ZAR', label: 'South African Rand (R)' },
    { value: 'USD', label: 'US Dollar ($)' },
    { value: 'EUR', label: 'Euro (€)' },
    { value: 'GBP', label: 'British Pound (£)' },
  ];

  const selectTheme = (theme) => {
    updateField('company', 'brand_theme', {
      theme_id: theme.id,
      primary: theme.primary,
      secondary: theme.secondary,
      accent: theme.accent,
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Company Profile</h2>
        <p className="text-gray-500 mt-1">Tell us about your travel business</p>
      </div>

      {/* Company Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Company Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.company.company_name}
            onChange={(e) => updateField('company', 'company_name', e.target.value)}
            placeholder="e.g., Safari Adventures Travel"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${
              errors['company.company_name'] ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors['company.company_name'] && (
            <p className="text-sm text-red-500 mt-1">{errors['company.company_name']}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Support Email <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            value={formData.company.support_email}
            onChange={(e) => updateField('company', 'support_email', e.target.value)}
            placeholder="support@yourcompany.com"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${
              errors['company.support_email'] ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors['company.support_email'] && (
            <p className="text-sm text-red-500 mt-1">{errors['company.support_email']}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone (Optional)</label>
          <input
            type="tel"
            value={formData.company.support_phone}
            onChange={(e) => updateField('company', 'support_phone', e.target.value)}
            placeholder="+27 12 345 6789"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
          <select
            value={formData.company.timezone}
            onChange={(e) => updateField('company', 'timezone', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          >
            {timezones.map((tz) => (
              <option key={tz.value} value={tz.value}>{tz.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
          <select
            value={formData.company.currency}
            onChange={(e) => updateField('company', 'currency', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          >
            {currencies.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Brand Theme */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">Brand Theme</label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {themes.map((theme) => (
            <button
              key={theme.id}
              type="button"
              onClick={() => selectTheme(theme)}
              className={`relative p-4 rounded-xl border-2 transition-all text-left ${
                formData.company.brand_theme?.theme_id === theme.id
                  ? 'border-purple-500 ring-2 ring-purple-200 bg-purple-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex gap-1 mb-2">
                <div className="w-6 h-6 rounded-full" style={{ backgroundColor: theme.primary }} />
                <div className="w-6 h-6 rounded-full" style={{ backgroundColor: theme.secondary }} />
                <div className="w-6 h-6 rounded-full" style={{ backgroundColor: theme.accent }} />
              </div>
              <p className="font-medium text-gray-900 text-sm">{theme.name}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Admin Account */}
      <div className="border-t border-gray-200 pt-8">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Admin Account</h3>
        <p className="text-sm text-gray-500 mb-4">Create your login credentials</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your Name</label>
            <input
              type="text"
              value={formData.admin_name}
              onChange={(e) => updateTopLevel('admin_name', e.target.value)}
              placeholder="John Doe"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Login Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={formData.admin_email}
              onChange={(e) => updateTopLevel('admin_email', e.target.value)}
              placeholder="you@yourcompany.com"
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${
                errors['admin_email'] ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {errors['admin_email'] && (
              <p className="text-sm text-red-500 mt-1">{errors['admin_email']}</p>
            )}
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              value={formData.admin_password}
              onChange={(e) => updateTopLevel('admin_password', e.target.value)}
              placeholder="At least 8 characters"
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${
                errors['admin_password'] ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {errors['admin_password'] && (
              <p className="text-sm text-red-500 mt-1">{errors['admin_password']}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== Step 2: Email Settings ====================
function Step2EmailSettings({ formData, updateField, errors }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Email Settings</h2>
        <p className="text-gray-500 mt-1">Configure how your quotes and invoices are sent</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            From Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.email.from_name}
            onChange={(e) => updateField('email', 'from_name', e.target.value)}
            placeholder="e.g., Safari Adventures"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${
              errors['email.from_name'] ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors['email.from_name'] && (
            <p className="text-sm text-red-500 mt-1">{errors['email.from_name']}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">Appears as sender name in emails</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">From Email (Optional)</label>
          <input
            type="email"
            value={formData.email.from_email}
            onChange={(e) => updateField('email', 'from_email', e.target.value)}
            placeholder="quotes@yourcompany.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          />
          <p className="text-xs text-gray-500 mt-1">Leave blank to use support email</p>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email Signature (Optional)</label>
        <textarea
          value={formData.email.email_signature}
          onChange={(e) => updateField('email', 'email_signature', e.target.value)}
          rows={3}
          placeholder="Best regards,&#10;The Safari Adventures Team&#10;+27 12 345 6789"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
        />
      </div>

      <div className="flex items-center gap-6 py-4 px-4 bg-gray-50 rounded-lg">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.email.auto_send_quotes}
            onChange={(e) => updateField('email', 'auto_send_quotes', e.target.checked)}
            className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
          />
          <span className="text-sm text-gray-700">Auto-send quotes to customers</span>
        </label>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-700">Quote valid for</span>
          <select
            value={formData.email.quote_validity_days}
            onChange={(e) => updateField('email', 'quote_validity_days', parseInt(e.target.value))}
            className="px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </div>
      </div>

      {/* SendGrid (Optional) */}
      <div className="border-t border-gray-200 pt-6">
        <h3 className="font-medium text-gray-900 mb-2">SendGrid API Key (Optional)</h3>
        <p className="text-sm text-gray-500 mb-4">
          Enter your own SendGrid API key for email delivery, or leave blank to use the platform default.
        </p>
        <input
          type="password"
          value={formData.email.sendgrid_api_key}
          onChange={(e) => updateField('email', 'sendgrid_api_key', e.target.value)}
          placeholder="SG.xxxxxxxxxxxxxxxx"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
        />
      </div>
    </div>
  );
}

// ==================== Step 3: Review & Launch ====================
function Step3Review({ formData, provisioningStatus, onLaunch, loading }) {
  // Success state
  if (provisioningStatus?.step === 'complete') {
    return (
      <div className="text-center py-8">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircleIcon className="w-12 h-12 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">You're All Set!</h2>
        <p className="text-gray-500 mb-8">Your travel platform is ready to use.</p>

        <div className="bg-gray-50 rounded-lg p-6 text-left max-w-sm mx-auto mb-8">
          <h3 className="font-medium text-gray-900 mb-3">Your Login Details</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Email:</dt>
              <dd className="font-medium">{formData.admin_email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Tenant ID:</dt>
              <dd className="font-mono text-xs">{provisioningStatus.tenant_id || provisioningStatus.resources?.tenant_id}</dd>
            </div>
          </dl>
        </div>

        <a
          href="/login"
          className="inline-flex items-center gap-2 px-8 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
        >
          Go to Login
          <ArrowRightIcon className="w-5 h-5" />
        </a>
      </div>
    );
  }

  // Error state
  if (provisioningStatus?.step === 'error') {
    return (
      <div className="text-center py-8">
        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <ExclamationTriangleIcon className="w-12 h-12 text-red-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Setup Failed</h2>
        <p className="text-gray-500 mb-4">{provisioningStatus.message}</p>

        {provisioningStatus.errors?.length > 0 && (
          <div className="bg-red-50 rounded-lg p-4 text-left max-w-md mx-auto mb-6">
            <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
              {provisioningStatus.errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        <button
          onClick={onLaunch}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="text-center py-12">
        <ArrowPathIcon className="w-12 h-12 text-purple-600 mx-auto mb-6 animate-spin" />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Setting Up Your Platform</h2>
        <p className="text-gray-500">{provisioningStatus?.message || 'This may take a moment...'}</p>
      </div>
    );
  }

  // Review state
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Review & Launch</h2>
        <p className="text-gray-500 mt-1">Review your settings before launching</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <BuildingOfficeIcon className="w-5 h-5 text-purple-600" />
            <h3 className="font-medium text-gray-900">Company</h3>
          </div>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Name</dt>
              <dd className="font-medium text-gray-900">{formData.company.company_name || '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Email</dt>
              <dd className="font-medium text-gray-900">{formData.company.support_email || '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Currency</dt>
              <dd className="font-medium text-gray-900">{formData.company.currency}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Theme</dt>
              <dd className="flex items-center gap-1">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: formData.company.brand_theme?.primary }} />
                <span className="font-medium text-gray-900 capitalize">
                  {formData.company.brand_theme?.theme_id?.replace(/-/g, ' ')}
                </span>
              </dd>
            </div>
          </dl>
        </div>

        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <EnvelopeIcon className="w-5 h-5 text-purple-600" />
            <h3 className="font-medium text-gray-900">Email</h3>
          </div>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">From Name</dt>
              <dd className="font-medium text-gray-900">{formData.email.from_name || '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Auto-send Quotes</dt>
              <dd className={`font-medium ${formData.email.auto_send_quotes ? 'text-green-600' : 'text-gray-500'}`}>
                {formData.email.auto_send_quotes ? 'Yes' : 'No'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Quote Validity</dt>
              <dd className="font-medium text-gray-900">{formData.email.quote_validity_days} days</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">SendGrid</dt>
              <dd className="font-medium text-gray-900">
                {formData.email.sendgrid_api_key ? 'Custom Key' : 'Platform Default'}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <CheckCircleIcon className="w-5 h-5 text-purple-600" />
          <h3 className="font-medium text-gray-900">Admin Account</h3>
        </div>
        <dl className="text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Login Email</dt>
            <dd className="font-medium text-gray-900">{formData.admin_email || '-'}</dd>
          </div>
        </dl>
      </div>

      {/* Launch Button */}
      <div className="text-center pt-4">
        <button
          onClick={onLaunch}
          disabled={loading}
          className="inline-flex items-center gap-2 px-8 py-4 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-lg font-medium disabled:opacity-50"
        >
          <RocketLaunchIcon className="w-6 h-6" />
          Launch My Platform
        </button>
        <p className="text-sm text-gray-500 mt-3">
          This will create your account and configure your platform
        </p>
      </div>
    </div>
  );
}
