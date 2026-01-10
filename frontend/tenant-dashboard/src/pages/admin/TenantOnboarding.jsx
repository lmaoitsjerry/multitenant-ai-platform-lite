import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BuildingOfficeIcon,
  CpuChipIcon,
  EnvelopeIcon,
  BookOpenIcon,
  RocketLaunchIcon,
  CheckCircleIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  SparklesIcon,
  ArrowPathIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { onboardingApi } from '../../services/api';

// Confirmation Modal Component
function ConfirmModal({ isOpen, title, message, confirmText, cancelText, onConfirm, onCancel, danger }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${danger ? 'bg-red-100' : 'bg-amber-100'}`}>
            <ExclamationTriangleIcon className={`w-6 h-6 ${danger ? 'text-red-600' : 'text-amber-600'}`} />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 rounded-lg font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
          >
            {cancelText || 'Cancel'}
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              danger
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-amber-600 text-white hover:bg-amber-700'
            }`}
          >
            {confirmText || 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}

const STORAGE_KEY = 'tenant_onboarding_progress';

// Step definitions (Lite version - no voice/outbound features)
const STEPS = [
  { id: 1, name: 'Company Profile', icon: BuildingOfficeIcon },
  { id: 2, name: 'AI Agent', icon: CpuChipIcon },
  { id: 3, name: 'Email Settings', icon: EnvelopeIcon },
  { id: 4, name: 'Knowledge Base', icon: BookOpenIcon },
  { id: 5, name: 'Review & Launch', icon: RocketLaunchIcon },
];

// Default form data
const getDefaultData = () => ({
  company: {
    company_name: '',
    support_email: '',
    support_phone: '',
    website_url: '',
    timezone: 'Africa/Johannesburg',
    currency: 'ZAR',
    brand_theme: {
      theme_id: 'ocean-blue',
      primary: '#0EA5E9',
      secondary: '#0284C7',
      accent: '#38BDF8',
    },
    logo_url: '',
  },
  agents: {
    inbound_description: '',
    inbound_prompt: '',
    inbound_agent_name: 'AI Assistant',
  },
  email: {
    from_name: '',
    email_signature: '',
    auto_send_quotes: true,
    quote_validity_days: 14,
    follow_up_days: 3,
    sendgrid_api_key: '',
    from_email: '',
  },
  knowledge_base: {
    categories: ['Destinations', 'Hotels', 'Visa Info', 'FAQs', 'Company Policies'],
    skip_initial_setup: true,
  },
  // Admin user credentials for first login
  admin_email: '',
  admin_password: '',
  admin_name: '',
});

export default function TenantOnboarding() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState(getDefaultData());
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generatingPrompt, setGeneratingPrompt] = useState(null);
  const [errors, setErrors] = useState({});
  const [provisioningStatus, setProvisioningStatus] = useState(null);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null });

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
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      formData,
      currentStep,
    }));
  }, [formData, currentStep]);

  const loadThemes = async () => {
    try {
      const response = await onboardingApi.getThemes();
      setThemes(response.data?.themes || []);
    } catch (error) {
      console.error('Failed to load themes:', error);
      // Provide fallback themes if API fails
      setThemes([
        { id: 'ocean-blue', name: 'Ocean Blue', description: 'Professional and trustworthy', primary: '#0EA5E9', secondary: '#0284C7', accent: '#38BDF8' },
        { id: 'safari-gold', name: 'Safari Gold', description: 'Warm and adventurous', primary: '#D97706', secondary: '#B45309', accent: '#FBBF24' },
        { id: 'sunset-orange', name: 'Sunset Orange', description: 'Energetic and vibrant', primary: '#EA580C', secondary: '#C2410C', accent: '#FB923C' },
        { id: 'forest-green', name: 'Forest Green', description: 'Natural and eco-friendly', primary: '#059669', secondary: '#047857', accent: '#34D399' },
        { id: 'royal-purple', name: 'Royal Purple', description: 'Luxurious and premium', primary: '#7C3AED', secondary: '#6D28D9', accent: '#A78BFA' },
        { id: 'classic-black', name: 'Classic Black', description: 'Elegant and sophisticated', primary: '#1F2937', secondary: '#111827', accent: '#6B7280' },
        { id: 'rose-pink', name: 'Rose Pink', description: 'Modern and stylish', primary: '#DB2777', secondary: '#BE185D', accent: '#F472B6' },
        { id: 'teal-modern', name: 'Teal Modern', description: 'Fresh and contemporary', primary: '#0D9488', secondary: '#0F766E', accent: '#2DD4BF' },
      ]);
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
    // Clear error for this field
    setErrors(prev => ({ ...prev, [`${section}.${field}`]: null }));
  };

  const updateTopLevel = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const validateStep = (step) => {
    const newErrors = {};

    if (step === 1) {
      if (!formData.company.company_name) newErrors['company.company_name'] = 'Company name is required';
      if (!formData.company.support_email) newErrors['company.support_email'] = 'Support email is required';
      if (!formData.company.brand_theme?.theme_id) newErrors['company.brand_theme'] = 'Please select a brand theme';
      // Validate admin credentials
      if (!formData.admin_email) newErrors['admin_email'] = 'Admin email is required';
      if (!formData.admin_password) {
        newErrors['admin_password'] = 'Admin password is required';
      } else if (formData.admin_password.length < 8) {
        newErrors['admin_password'] = 'Password must be at least 8 characters';
      }
    }

    if (step === 2) {
      if (!formData.agents.inbound_description) {
        newErrors['agents.inbound_description'] = 'Please describe your AI agent';
      }
      if (!formData.agents.inbound_prompt) {
        newErrors['agents.inbound_prompt'] = 'Please generate a system prompt first';
      }
    }

    if (step === 4) {
      if (!formData.email.from_name) newErrors['email.from_name'] = 'From name is required';
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

  const generatePrompt = async (agentType) => {
    const description = formData.agents.inbound_description;

    if (!description || description.length < 20) {
      setErrors(prev => ({
        ...prev,
        [`agents.${agentType}_description`]: 'Please provide a longer description (at least 20 characters)',
      }));
      return;
    }

    setGeneratingPrompt(agentType);

    try {
      const response = await onboardingApi.generatePrompt({
        description,
        agent_type: 'inbound',
        company_name: formData.company.company_name,
        agent_name: formData.agents.inbound_agent_name,
      });

      if (response.data) {
        const { system_prompt, agent_name } = response.data;
        updateField('agents', `${agentType}_prompt`, system_prompt);
        if (agent_name && !formData.agents[`${agentType}_agent_name`]) {
          updateField('agents', `${agentType}_agent_name`, agent_name);
        }
      }
    } catch (error) {
      console.error('Failed to generate prompt:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to generate prompt. Please try again.';
      setErrors(prev => ({
        ...prev,
        [`agents.${agentType}_prompt`]: errorMessage,
      }));
    } finally {
      setGeneratingPrompt(null);
    }
  };

  const handleLaunch = async () => {
    if (!validateStep(currentStep)) return;

    setLoading(true);
    setProvisioningStatus({ step: 'starting', message: 'Starting onboarding...' });

    try {
      // Prepare the request (Lite version - no voice features)
      const request = {
        company: formData.company,
        agents: formData.agents,
        email: formData.email,
        knowledge_base: formData.knowledge_base,
        // Admin user credentials
        admin_email: formData.admin_email,
        admin_password: formData.admin_password,
        admin_name: formData.admin_name || undefined,
      };

      setProvisioningStatus({ step: 'config', message: 'Creating tenant configuration...' });

      const response = await onboardingApi.complete(request);

      if (response.data?.success) {
        setProvisioningStatus({
          step: 'complete',
          message: 'Onboarding complete!',
          resources: response.data.resources,
        });

        // Clear saved progress
        localStorage.removeItem(STORAGE_KEY);
      } else {
        setProvisioningStatus({
          step: 'error',
          message: response.data?.message || 'Onboarding failed',
          errors: response.data?.errors || [],
        });
      }
    } catch (error) {
      console.error('Onboarding failed:', error);
      setProvisioningStatus({
        step: 'error',
        message: error.response?.data?.detail || 'Failed to complete onboarding',
        errors: [error.message],
      });
    } finally {
      setLoading(false);
    }
  };

  const resetOnboarding = () => {
    setConfirmModal({
      isOpen: true,
      title: 'Start Over?',
      message: 'Are you sure you want to start over? All progress will be lost.',
      onConfirm: () => {
        setConfirmModal({ ...confirmModal, isOpen: false });
        localStorage.removeItem(STORAGE_KEY);
        setFormData(getDefaultData());
        setCurrentStep(1);
        setErrors({});
        setProvisioningStatus(null);
      }
    });
  };

  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return <Step1CompanyProfile formData={formData} updateField={updateField} updateTopLevel={updateTopLevel} errors={errors} themes={themes} />;
      case 2:
        return (
          <Step2AgentConfig
            formData={formData}
            updateField={updateField}
            errors={errors}
            generatePrompt={generatePrompt}
            generatingPrompt={generatingPrompt}
          />
        );
      case 3:
        return <Step3EmailSettings formData={formData} updateField={updateField} errors={errors} />;
      case 4:
        return <Step4KnowledgeBase formData={formData} updateField={updateField} />;
      case 5:
        return (
          <Step5Review
            formData={formData}
            provisioningStatus={provisioningStatus}
            onLaunch={handleLaunch}
            loading={loading}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Tenant Onboarding</h1>
              <p className="text-gray-500 mt-1">Configure your AI travel platform</p>
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
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {STEPS.map((step, idx) => (
              <div key={step.id} className="flex items-center">
                <button
                  onClick={() => currentStep > step.id && setCurrentStep(step.id)}
                  disabled={currentStep < step.id}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                    currentStep === step.id
                      ? 'bg-purple-100 text-purple-700'
                      : currentStep > step.id
                      ? 'text-green-600 hover:bg-green-50 cursor-pointer'
                      : 'text-gray-400 cursor-not-allowed'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
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
                      <span className="text-sm font-medium">{step.id}</span>
                    )}
                  </div>
                  <span className="hidden md:block text-sm font-medium">{step.name}</span>
                </button>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`w-8 h-0.5 mx-1 ${
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
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
          {renderStepContent()}
        </div>

        {/* Navigation */}
        {currentStep < 6 && (
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={handleBack}
              disabled={currentStep === 1}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
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
              className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            >
              Next
              <ArrowRightIcon className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText="Start Over"
        danger={true}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, isOpen: false })}
      />
    </div>
  );
}

// ==================== Step Components ====================

function Step1CompanyProfile({ formData, updateField, updateTopLevel, errors, themes }) {
  const timezones = [
    { value: 'Africa/Johannesburg', label: 'South Africa (SAST)' },
    { value: 'Africa/Lagos', label: 'Nigeria (WAT)' },
    { value: 'Africa/Nairobi', label: 'Kenya (EAT)' },
    { value: 'Europe/London', label: 'UK (GMT/BST)' },
    { value: 'America/New_York', label: 'US Eastern (EST/EDT)' },
    { value: 'Australia/Sydney', label: 'Australia (AEST/AEDT)' },
  ];

  const currencies = [
    { value: 'ZAR', label: 'South African Rand (ZAR)' },
    { value: 'USD', label: 'US Dollar (USD)' },
    { value: 'EUR', label: 'Euro (EUR)' },
    { value: 'GBP', label: 'British Pound (GBP)' },
    { value: 'KES', label: 'Kenyan Shilling (KES)' },
    { value: 'NGN', label: 'Nigerian Naira (NGN)' },
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
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Company Profile</h2>
        <p className="text-gray-500 mt-1">Basic information about your travel agency</p>
      </div>

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
            className={`input w-full ${errors['company.company_name'] ? 'border-red-500' : ''}`}
          />
          {errors['company.company_name'] && (
            <p className="text-sm text-red-500 mt-1">{errors['company.company_name']}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">A unique tenant ID will be auto-generated from your company name</p>
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
            className={`input w-full ${errors['company.support_email'] ? 'border-red-500' : ''}`}
          />
          {errors['company.support_email'] && (
            <p className="text-sm text-red-500 mt-1">{errors['company.support_email']}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
          <input
            type="tel"
            value={formData.company.support_phone}
            onChange={(e) => updateField('company', 'support_phone', e.target.value)}
            placeholder="+27 12 345 6789"
            className="input w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
          <input
            type="url"
            value={formData.company.website_url}
            onChange={(e) => updateField('company', 'website_url', e.target.value)}
            placeholder="https://www.yourcompany.com"
            className="input w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
          <select
            value={formData.company.timezone}
            onChange={(e) => updateField('company', 'timezone', e.target.value)}
            className="input w-full"
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
            className="input w-full"
          >
            {currencies.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Brand Theme Selection */}
      <div className="mt-8">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Brand Theme <span className="text-red-500">*</span>
        </label>
        <p className="text-sm text-gray-500 mb-4">Select a color theme for your platform's dashboard and emails</p>
        {errors['company.brand_theme'] && (
          <p className="text-sm text-red-500 mb-3">{errors['company.brand_theme']}</p>
        )}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {themes.map((theme) => (
            <button
              key={theme.id}
              type="button"
              onClick={() => selectTheme(theme)}
              className={`relative p-4 rounded-xl border-2 transition-all text-left ${
                formData.company.brand_theme?.theme_id === theme.id
                  ? 'border-purple-500 ring-2 ring-purple-200'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              {formData.company.brand_theme?.theme_id === theme.id && (
                <div className="absolute top-2 right-2">
                  <CheckCircleIcon className="w-5 h-5 text-purple-600" />
                </div>
              )}
              <div className="flex gap-1 mb-3">
                <div
                  className="w-8 h-8 rounded-full"
                  style={{ backgroundColor: theme.primary }}
                />
                <div
                  className="w-8 h-8 rounded-full"
                  style={{ backgroundColor: theme.secondary }}
                />
                <div
                  className="w-8 h-8 rounded-full"
                  style={{ backgroundColor: theme.accent }}
                />
              </div>
              <p className="font-medium text-gray-900 text-sm">{theme.name}</p>
              <p className="text-xs text-gray-500">{theme.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Admin Account Section */}
      <div className="mt-8 pt-8 border-t border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Admin Account</h3>
        <p className="text-sm text-gray-500 mb-4">Create your first admin account to access the dashboard after setup</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admin Name
            </label>
            <input
              type="text"
              value={formData.admin_name}
              onChange={(e) => updateTopLevel('admin_name', e.target.value)}
              placeholder="John Doe"
              className="input w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admin Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={formData.admin_email}
              onChange={(e) => updateTopLevel('admin_email', e.target.value)}
              placeholder="admin@yourcompany.com"
              className={`input w-full ${errors['admin_email'] ? 'border-red-500' : ''}`}
            />
            {errors['admin_email'] && (
              <p className="text-sm text-red-500 mt-1">{errors['admin_email']}</p>
            )}
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admin Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              value={formData.admin_password}
              onChange={(e) => updateTopLevel('admin_password', e.target.value)}
              placeholder="Create a strong password (min 8 characters)"
              className={`input w-full ${errors['admin_password'] ? 'border-red-500' : ''}`}
            />
            {errors['admin_password'] && (
              <p className="text-sm text-red-500 mt-1">{errors['admin_password']}</p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              Password must be at least 8 characters with uppercase, lowercase, and number
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Step2AgentConfig({ formData, updateField, errors, generatePrompt, generatingPrompt }) {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">AI Agent Configuration</h2>
        <p className="text-gray-500 mt-1">Configure the AI agent that handles email inquiries and generates quotes</p>
      </div>

      {/* Agent Configuration */}
      <div className="border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Email Quote Agent</h3>
        <p className="text-sm text-gray-500 mb-4">This agent processes incoming email inquiries and generates personalized travel quotes</p>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Agent Name</label>
          <input
            type="text"
            value={formData.agents.inbound_agent_name}
            onChange={(e) => updateField('agents', 'inbound_agent_name', e.target.value)}
            placeholder="AI Assistant"
            className="input w-full max-w-xs"
          />
          <p className="text-xs text-gray-500 mt-1">Used in email signatures and quote documents</p>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Describe Your Agent <span className="text-red-500">*</span>
          </label>
          <textarea
            value={formData.agents.inbound_description}
            onChange={(e) => updateField('agents', 'inbound_description', e.target.value)}
            rows={4}
            placeholder="Example: I want a friendly, professional agent named Sarah who specializes in African safaris and beach holidays. She should be warm but not too casual, always mention our 24/7 support, and try to upsell premium packages when appropriate."
            className={`input w-full ${errors['agents.inbound_description'] ? 'border-red-500' : ''}`}
          />
          {errors['agents.inbound_description'] && (
            <p className="text-sm text-red-500 mt-1">{errors['agents.inbound_description']}</p>
          )}
        </div>

        <button
          onClick={() => generatePrompt('inbound')}
          disabled={generatingPrompt === 'inbound'}
          className="flex items-center gap-2 px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 disabled:opacity-50"
        >
          {generatingPrompt === 'inbound' ? (
            <ArrowPathIcon className="w-5 h-5 animate-spin" />
          ) : (
            <SparklesIcon className="w-5 h-5" />
          )}
          {generatingPrompt === 'inbound' ? 'Generating...' : 'Generate System Prompt'}
        </button>

        {formData.agents.inbound_prompt && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Generated System Prompt
            </label>
            <textarea
              value={formData.agents.inbound_prompt}
              onChange={(e) => updateField('agents', 'inbound_prompt', e.target.value)}
              rows={8}
              className="input w-full font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">You can edit this prompt to fine-tune your agent's behavior</p>
          </div>
        )}
        {errors['agents.inbound_prompt'] && (
          <p className="text-sm text-red-500 mt-2">{errors['agents.inbound_prompt']}</p>
        )}
      </div>

    </div>
  );
}

function Step3EmailSettings({ formData, updateField, errors }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Email & Communication</h2>
        <p className="text-gray-500 mt-1">Configure email settings for quotes and invoices</p>
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
            className={`input w-full ${errors['email.from_name'] ? 'border-red-500' : ''}`}
          />
          {errors['email.from_name'] && (
            <p className="text-sm text-red-500 mt-1">{errors['email.from_name']}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">From Email</label>
          <input
            type="email"
            value={formData.email.from_email}
            onChange={(e) => updateField('email', 'from_email', e.target.value)}
            placeholder="quotes@yourcompany.com"
            className="input w-full"
          />
          <p className="text-xs text-gray-500 mt-1">Leave blank to use support email</p>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email Signature</label>
        <textarea
          value={formData.email.email_signature}
          onChange={(e) => updateField('email', 'email_signature', e.target.value)}
          rows={4}
          placeholder="Best regards,&#10;The Safari Adventures Team&#10;+27 12 345 6789 | www.safari-adventures.com"
          className="input w-full"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
          <input
            type="checkbox"
            id="auto_send"
            checked={formData.email.auto_send_quotes}
            onChange={(e) => updateField('email', 'auto_send_quotes', e.target.checked)}
            className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
          />
          <label htmlFor="auto_send" className="text-sm text-gray-700">
            Auto-send quotes to customers
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Quote Validity</label>
          <select
            value={formData.email.quote_validity_days}
            onChange={(e) => updateField('email', 'quote_validity_days', parseInt(e.target.value))}
            className="input w-full"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Follow-up After</label>
          <select
            value={formData.email.follow_up_days}
            onChange={(e) => updateField('email', 'follow_up_days', parseInt(e.target.value))}
            className="input w-full"
          >
            <option value={2}>2 days</option>
            <option value={3}>3 days</option>
            <option value={5}>5 days</option>
            <option value={7}>7 days</option>
          </select>
        </div>
      </div>

      {/* SendGrid API Key */}
      <div className="border-t border-gray-200 pt-6">
        <h3 className="font-medium text-gray-900 mb-2">SendGrid Configuration (Optional)</h3>
        <p className="text-sm text-gray-500 mb-4">Enter your SendGrid API key for email delivery, or leave blank to use the platform default.</p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">SendGrid API Key</label>
          <input
            type="password"
            value={formData.email.sendgrid_api_key}
            onChange={(e) => updateField('email', 'sendgrid_api_key', e.target.value)}
            placeholder="SG.xxxxxxxxxxxxxxxx"
            className="input w-full"
          />
        </div>
      </div>
    </div>
  );
}

function Step4KnowledgeBase({ formData, updateField }) {
  const defaultCategories = ['Destinations', 'Hotels', 'Visa Info', 'FAQs', 'Company Policies', 'Terms & Conditions'];

  const toggleCategory = (category) => {
    const current = formData.knowledge_base.categories || [];
    if (current.includes(category)) {
      updateField('knowledge_base', 'categories', current.filter(c => c !== category));
    } else {
      updateField('knowledge_base', 'categories', [...current, category]);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Knowledge Base Setup</h2>
        <p className="text-gray-500 mt-1">Configure your AI's knowledge base categories</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Knowledge Categories
        </label>
        <p className="text-sm text-gray-500 mb-4">
          Select categories to organize your knowledge base. You can upload documents to these categories after setup.
        </p>
        <div className="flex flex-wrap gap-2">
          {defaultCategories.map((category) => (
            <button
              key={category}
              onClick={() => toggleCategory(category)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                formData.knowledge_base.categories?.includes(category)
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <div className="text-center">
          <BookOpenIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="font-medium text-gray-900 mb-2">Document Upload</h3>
          <p className="text-sm text-gray-500 mb-4">
            You can upload destination guides, hotel information, FAQ documents, and more after completing setup.
          </p>
          <div className="flex items-center justify-center gap-2">
            <input
              type="checkbox"
              id="skip_kb"
              checked={formData.knowledge_base.skip_initial_setup}
              onChange={(e) => updateField('knowledge_base', 'skip_initial_setup', e.target.checked)}
              className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
            />
            <label htmlFor="skip_kb" className="text-sm text-gray-700">
              Skip document upload for now (recommended)
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

function Step5Review({ formData, provisioningStatus, onLaunch, loading }) {
  if (provisioningStatus?.step === 'complete') {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircleIcon className="w-10 h-10 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Onboarding Complete!</h2>
        <p className="text-gray-500 mb-8">Your AI travel platform is ready to go.</p>

        <div className="bg-gray-50 rounded-lg p-6 text-left max-w-md mx-auto mb-8">
          <h3 className="font-medium text-gray-900 mb-4">Your Resources</h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-gray-500">Tenant ID:</dt>
              <dd className="font-medium font-mono">{provisioningStatus.resources?.tenant_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Status:</dt>
              <dd className="font-medium text-green-600">Ready</dd>
            </div>
          </dl>
        </div>

        <a
          href={`/?client=${provisioningStatus.resources?.tenant_id}`}
          className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
        >
          Go to Dashboard
          <ArrowRightIcon className="w-5 h-5" />
        </a>
      </div>
    );
  }

  if (provisioningStatus?.step === 'error') {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-3xl">!</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Onboarding Failed</h2>
        <p className="text-gray-500 mb-4">{provisioningStatus.message}</p>
        {provisioningStatus.errors?.length > 0 && (
          <div className="bg-red-50 rounded-lg p-4 text-left max-w-md mx-auto mb-8">
            <ul className="list-disc list-inside text-sm text-red-700">
              {provisioningStatus.errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          </div>
        )}
        <button
          onClick={onLaunch}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <ArrowPathIcon className="w-12 h-12 text-purple-600 mx-auto mb-6 animate-spin" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Setting Up Your Platform</h2>
        <p className="text-gray-500">{provisioningStatus?.message || 'Please wait...'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Review & Launch</h2>
        <p className="text-gray-500 mt-1">Review your configuration before launching</p>
      </div>

      {/* Summary Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SummaryCard title="Company" icon={BuildingOfficeIcon}>
          <SummaryItem label="Name" value={formData.company.company_name} />
          <SummaryItem label="Email" value={formData.company.support_email} />
          <SummaryItem label="Currency" value={formData.company.currency} />
          <SummaryItem label="Theme" value={formData.company.brand_theme?.theme_id?.replace(/-/g, ' ')} />
        </SummaryCard>

        <SummaryCard title="AI Agent" icon={CpuChipIcon}>
          <SummaryItem label="Agent Name" value={formData.agents.inbound_agent_name} />
          <SummaryItem
            label="System Prompt"
            value={formData.agents.inbound_prompt ? 'Configured' : 'Not set'}
            status={!!formData.agents.inbound_prompt}
          />
        </SummaryCard>

        <SummaryCard title="Email" icon={EnvelopeIcon}>
          <SummaryItem label="From Name" value={formData.email.from_name} />
          <SummaryItem
            label="Auto-send Quotes"
            value={formData.email.auto_send_quotes ? 'Yes' : 'No'}
            status={formData.email.auto_send_quotes}
          />
          <SummaryItem label="Quote Validity" value={`${formData.email.quote_validity_days} days`} />
          <SummaryItem
            label="SendGrid"
            value={formData.email.sendgrid_api_key ? 'Custom' : 'Platform default'}
          />
        </SummaryCard>
      </div>

      <div className="text-center pt-6">
        <button
          onClick={onLaunch}
          disabled={loading}
          className="inline-flex items-center gap-2 px-8 py-4 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-lg font-medium disabled:opacity-50"
        >
          <RocketLaunchIcon className="w-6 h-6" />
          Launch My Platform
        </button>
        <p className="text-sm text-gray-500 mt-3">
          This will create your tenant configuration and set up your platform
        </p>
      </div>
    </div>
  );
}

function SummaryCard({ title, icon: Icon, children }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-5 h-5 text-purple-600" />
        <h3 className="font-medium text-gray-900">{title}</h3>
      </div>
      <dl className="space-y-2">{children}</dl>
    </div>
  );
}

function SummaryItem({ label, value, status }) {
  return (
    <div className="flex justify-between text-sm">
      <dt className="text-gray-500">{label}</dt>
      <dd className={`font-medium ${status === false ? 'text-gray-400' : status === true ? 'text-green-600' : ''}`}>
        {value || '-'}
      </dd>
    </div>
  );
}
