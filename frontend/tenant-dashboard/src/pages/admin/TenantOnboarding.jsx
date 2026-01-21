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
  EyeIcon,
  EyeSlashIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { onboardingApi, setTenantId } from '../../services/api';

// Password strength calculator
const getPasswordStrength = (password) => {
  if (!password) return null;

  let strength = 0;
  if (password.length >= 8) strength++;
  if (password.length >= 12) strength++;
  if (/[a-z]/.test(password)) strength++;
  if (/[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[^a-zA-Z0-9]/.test(password)) strength++;

  if (strength <= 2) return { level: 'weak', color: 'bg-red-500', width: '25%', label: 'Weak' };
  if (strength <= 3) return { level: 'fair', color: 'bg-orange-500', width: '50%', label: 'Fair' };
  if (strength <= 4) return { level: 'good', color: 'bg-yellow-500', width: '75%', label: 'Good' };
  return { level: 'strong', color: 'bg-green-500', width: '100%', label: 'Strong' };
};

// Generate a strong random password
const generateStrongPassword = () => {
  const length = 16;
  const lowercase = 'abcdefghijklmnopqrstuvwxyz';
  const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const numbers = '0123456789';
  const symbols = '!@#$%^&*';
  const allChars = lowercase + uppercase + numbers + symbols;

  // Ensure at least one of each type
  let password = '';
  password += uppercase[Math.floor(Math.random() * uppercase.length)];
  password += lowercase[Math.floor(Math.random() * lowercase.length)];
  password += numbers[Math.floor(Math.random() * numbers.length)];
  password += symbols[Math.floor(Math.random() * symbols.length)];

  // Fill the rest randomly
  for (let i = password.length; i < length; i++) {
    password += allChars[Math.floor(Math.random() * allChars.length)];
  }

  // Shuffle the password
  return password.split('').sort(() => Math.random() - 0.5).join('');
};

// Password field component with show/hide, strength indicator, and generator
function PasswordField({ value, onChange, error }) {
  const [showPassword, setShowPassword] = useState(false);
  const strength = getPasswordStrength(value);

  const handleGenerate = () => {
    const newPassword = generateStrongPassword();
    onChange(newPassword);
    setShowPassword(true); // Show the generated password so user can see/copy it
  };

  return (
    <div className="space-y-2">
      {/* Password input with toggle */}
      <div className="relative">
        <input
          type={showPassword ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="At least 8 characters"
          className={`w-full px-3 py-2 pr-20 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 ${
            error ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600"
          title={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            <EyeSlashIcon className="w-5 h-5" />
          ) : (
            <EyeIcon className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Strength indicator */}
      {value && strength && (
        <div className="space-y-1">
          <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${strength.color} transition-all duration-300`}
              style={{ width: strength.width }}
            />
          </div>
          <p className={`text-xs ${
            strength.level === 'weak' ? 'text-red-600' :
            strength.level === 'fair' ? 'text-orange-600' :
            strength.level === 'good' ? 'text-yellow-600' :
            'text-green-600'
          }`}>
            Password strength: {strength.label}
          </p>
        </div>
      )}

      {/* Generate button */}
      <button
        type="button"
        onClick={handleGenerate}
        className="flex items-center gap-1.5 text-sm text-purple-600 hover:text-purple-700 font-medium"
      >
        <SparklesIcon className="w-4 h-4" />
        Generate strong password
      </button>

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}

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
    quote_validity_days: 7,
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
        // Store tenant ID for future API calls
        const tenantId = response.data.tenant_id;
        if (tenantId) {
          setTenantId(tenantId);
        }

        // Check for critical errors (e.g., admin user creation failed)
        const criticalErrors = response.data.errors?.filter(e =>
          e.includes('Email already registered') ||
          e.includes('Admin user')
        ) || [];

        // Check if auto-login tokens were provided
        const { access_token, refresh_token, user } = response.data;
        if (access_token && refresh_token && user) {
          // Store tokens and user for auto-login
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
          localStorage.setItem('user', JSON.stringify(user));  // Store user for session
          localStorage.removeItem(STORAGE_KEY);

          // Redirect to dashboard - user is now logged in
          setProvisioningStatus({ step: 'redirecting', message: 'Logging you in...' });
          setTimeout(() => {
            navigate('/');
          }, 1000);
        } else if (criticalErrors.length > 0) {
          // Admin user creation failed - show error with helpful message
          const isEmailExists = criticalErrors.some(e => e.includes('Email already registered'));
          setProvisioningStatus({
            step: 'error',
            message: isEmailExists
              ? 'This email is already registered with a different password.'
              : 'Could not create your admin account.',
            errors: [
              ...criticalErrors,
              isEmailExists
                ? 'Please use your existing password to login, or use a different email address.'
                : 'Please try again or contact support.'
            ],
          });
        } else {
          // No tokens but no critical errors - show success screen with login button
          setProvisioningStatus({
            step: 'complete',
            message: 'Setup complete!',
            resources: response.data.resources || { tenant_id: tenantId },
            tenant_id: tenantId,
          });
          localStorage.removeItem(STORAGE_KEY);
        }
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
              onBack={handleBack}
              loading={loading}
            />
          )}
        </div>

        {/* Navigation - hide on step 3 (Review has its own launch button) */}
        {currentStep < 3 && (
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

            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
            >
              Next
              <ArrowRightIcon className="w-5 h-5" />
            </button>
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
              className={`relative p-4 rounded-xl border-2 transition-all text-left bg-white ${
                formData.company.brand_theme?.theme_id === theme.id
                  ? 'border-purple-500 ring-2 ring-purple-200'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              {formData.company.brand_theme?.theme_id === theme.id && (
                <div className="absolute top-2 right-2">
                  <CheckCircleIcon className="w-5 h-5 text-purple-600" />
                </div>
              )}
              <div className="flex gap-1.5 mb-3">
                <div className="w-7 h-7 rounded-full border border-gray-200" style={{ backgroundColor: theme.primary }} />
                <div className="w-7 h-7 rounded-full border border-gray-200" style={{ backgroundColor: theme.secondary }} />
                <div className="w-7 h-7 rounded-full border border-gray-200" style={{ backgroundColor: theme.accent }} />
              </div>
              <p className="font-semibold text-gray-900 text-sm">{theme.name}</p>
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
            <PasswordField
              value={formData.admin_password}
              onChange={(value) => updateTopLevel('admin_password', value)}
              error={errors['admin_password']}
            />
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
            className="px-3 py-1.5 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm appearance-none cursor-pointer"
            style={{ backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`, backgroundPosition: 'right 0.5rem center', backgroundRepeat: 'no-repeat', backgroundSize: '1.5em 1.5em', paddingRight: '2.5rem' }}
          >
            <option value={1}>1 day</option>
            <option value={2}>2 days</option>
            <option value={3}>3 days</option>
            <option value={4}>4 days</option>
            <option value={5}>5 days</option>
            <option value={6}>6 days</option>
            <option value={7}>7 days</option>
          </select>
        </div>
      </div>

      {/* Email Info Note */}
      <div className="border-t border-gray-200 pt-6">
        <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg">
          <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-sm font-medium text-blue-900">Email Setup</p>
            <p className="text-sm text-blue-700 mt-1">
              We'll automatically configure email sending for your platform. Quotes and invoices will be sent from your company name.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== Step 3: Review & Launch ====================
function Step3Review({ formData, provisioningStatus, onLaunch, onBack, loading }) {
  // Redirecting state (auto-login in progress)
  if (provisioningStatus?.step === 'redirecting') {
    return (
      <div className="text-center py-12">
        <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <ArrowPathIcon className="w-10 h-10 text-purple-600 animate-spin" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome!</h2>
        <p className="text-gray-500">Setting up your dashboard...</p>
      </div>
    );
  }

  // Success state (fallback - no auto-login)
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
          </dl>
          <p className="text-xs text-gray-400 mt-4">Use the password you created during setup to log in.</p>
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
    const isEmailExists = provisioningStatus.message?.includes('already registered');

    return (
      <div className="text-center py-8">
        <div className={`w-20 h-20 ${isEmailExists ? 'bg-yellow-100' : 'bg-red-100'} rounded-full flex items-center justify-center mx-auto mb-6`}>
          <ExclamationTriangleIcon className={`w-12 h-12 ${isEmailExists ? 'text-yellow-600' : 'text-red-600'}`} />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {isEmailExists ? 'Account Already Exists' : 'Setup Failed'}
        </h2>
        <p className="text-gray-500 mb-4">{provisioningStatus.message}</p>

        {provisioningStatus.errors?.length > 0 && (
          <div className={`${isEmailExists ? 'bg-yellow-50' : 'bg-red-50'} rounded-lg p-4 text-left max-w-md mx-auto mb-6`}>
            <ul className={`list-disc list-inside text-sm ${isEmailExists ? 'text-yellow-700' : 'text-red-700'} space-y-1`}>
              {provisioningStatus.errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-center justify-center gap-4">
          {isEmailExists && (
            <a
              href="/login"
              className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
            >
              Go to Login
            </a>
          )}
          <button
            onClick={onLaunch}
            className={`px-6 py-3 rounded-lg font-medium ${
              isEmailExists
                ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                : 'bg-purple-600 text-white hover:bg-purple-700'
            }`}
          >
            {isEmailExists ? 'Try Different Email' : 'Try Again'}
          </button>
        </div>
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
              <dt className="text-gray-500">Email Service</dt>
              <dd className="font-medium text-green-600">Auto-configured</dd>
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

      {/* Actions */}
      <div className="flex items-center justify-between pt-6">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium"
        >
          <ArrowLeftIcon className="w-5 h-5" />
          Back
        </button>
        <button
          onClick={onLaunch}
          disabled={loading}
          className="inline-flex items-center gap-2 px-8 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium disabled:opacity-50"
        >
          <RocketLaunchIcon className="w-6 h-6" />
          Launch My Platform
        </button>
      </div>
      <p className="text-sm text-gray-500 text-center mt-3">
        This will create your account and configure your platform
      </p>
    </div>
  );
}
