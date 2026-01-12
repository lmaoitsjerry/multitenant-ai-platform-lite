import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { privacyApi } from '../../services/api';
import { ToggleCard } from '../../components/ui/Toggle';
import {
  ShieldCheckIcon,
  DocumentArrowDownIcon,
  TrashIcon,
  EnvelopeIcon,
  PhoneIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

// Consent type descriptions
const consentDescriptions = {
  marketing_email: {
    label: 'Marketing Emails',
    description: 'Receive promotional emails about special offers and travel deals',
    icon: EnvelopeIcon,
    category: 'marketing'
  },
  marketing_sms: {
    label: 'Marketing SMS',
    description: 'Receive promotional text messages',
    icon: PhoneIcon,
    category: 'marketing'
  },
  marketing_phone: {
    label: 'Marketing Calls',
    description: 'Receive promotional phone calls',
    icon: PhoneIcon,
    category: 'marketing'
  },
  analytics: {
    label: 'Analytics',
    description: 'Allow us to analyze your usage to improve our services',
    icon: ChartBarIcon,
    category: 'functional'
  },
  third_party_sharing: {
    label: 'Third-Party Sharing',
    description: 'Share your data with trusted partners for better service',
    icon: ShieldCheckIcon,
    category: 'functional'
  },
};

function ConsentToggle({ type, config, granted, onToggle, disabled }) {
  return (
    <ToggleCard
      icon={config.icon}
      title={config.label}
      description={config.description}
      checked={granted}
      onChange={(checked) => onToggle(type, checked)}
      disabled={disabled}
    />
  );
}

function DSARRequestForm({ onSubmit, loading }) {
  const [requestType, setRequestType] = useState('access');
  const [details, setDetails] = useState('');

  const requestTypes = [
    { value: 'access', label: 'Access My Data', description: 'Get a copy of all data we hold about you' },
    { value: 'portability', label: 'Export My Data', description: 'Download your data in a portable format' },
    { value: 'rectification', label: 'Correct My Data', description: 'Request corrections to inaccurate data' },
    { value: 'erasure', label: 'Delete My Data', description: 'Request deletion of your personal data' },
    { value: 'objection', label: 'Object to Processing', description: 'Object to how we process your data' },
  ];

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(requestType, details); }} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-theme-secondary mb-2">Request Type</label>
        <div className="space-y-2">
          {requestTypes.map((type) => (
            <label
              key={type.value}
              className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                requestType === type.value
                  ? 'border-theme-primary bg-theme-primary/10'
                  : 'border-theme hover:bg-theme-border-light'
              }`}
            >
              <input
                type="radio"
                name="requestType"
                value={type.value}
                checked={requestType === type.value}
                onChange={(e) => setRequestType(e.target.value)}
                className="mt-1 accent-[var(--color-primary)]"
              />
              <div>
                <p className="font-medium text-theme">{type.label}</p>
                <p className="text-sm text-theme-muted">{type.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-theme-secondary mb-1">
          Additional Details (Optional)
        </label>
        <textarea
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          rows={3}
          className="input"
          placeholder="Provide any additional details about your request..."
        />
      </div>

      <button type="submit" disabled={loading} className="btn-primary w-full">
        {loading ? 'Submitting...' : 'Submit Request'}
      </button>
    </form>
  );
}

function DSARHistory({ requests }) {
  const statusStyles = {
    pending: { bg: 'rgba(var(--color-warning-rgb, 245, 158, 11), 0.15)', text: 'var(--color-warning)' },
    verified: { bg: 'rgba(var(--color-primary-rgb, 124, 58, 237), 0.15)', text: 'var(--color-primary)' },
    in_progress: { bg: 'rgba(var(--color-primary-rgb, 124, 58, 237), 0.15)', text: 'var(--color-primary)' },
    completed: { bg: 'rgba(var(--color-success-rgb, 34, 197, 94), 0.15)', text: 'var(--color-success)' },
    rejected: { bg: 'rgba(var(--color-error-rgb, 239, 68, 68), 0.15)', text: 'var(--color-error)' },
  };

  const statusIcons = {
    pending: ClockIcon,
    verified: CheckCircleIcon,
    in_progress: ClockIcon,
    completed: CheckCircleIcon,
    rejected: ExclamationTriangleIcon,
  };

  if (!requests || requests.length === 0) {
    return (
      <div className="text-center py-8 text-theme-muted">
        <ShieldCheckIcon className="w-12 h-12 mx-auto mb-2 text-theme-border" />
        <p>No previous requests</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {requests.map((req) => {
        const StatusIcon = statusIcons[req.status] || ClockIcon;
        const style = statusStyles[req.status] || { bg: 'var(--color-surface-elevated)', text: 'var(--color-text-secondary)' };
        return (
          <div key={req.id} className="flex items-center justify-between p-4 border border-theme rounded-lg">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-theme-surface-elevated rounded-lg flex items-center justify-center">
                <StatusIcon className="w-5 h-5 text-theme-secondary" />
              </div>
              <div>
                <p className="font-medium text-theme capitalize">{req.request_type.replace('_', ' ')} Request</p>
                <p className="text-sm text-theme-muted">
                  {new Date(req.created_at).toLocaleDateString()} - Due: {new Date(req.due_date).toLocaleDateString()}
                </p>
              </div>
            </div>
            <span
              className="px-3 py-1 rounded-full text-xs font-medium capitalize"
              style={{ backgroundColor: style.bg, color: style.text }}
            >
              {req.status.replace('_', ' ')}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function PrivacySettings() {
  const { user } = useAuth();
  const [consents, setConsents] = useState({});
  const [dsarRequests, setDsarRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  // Fetch consents and DSAR history
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [consentsRes, dsarRes] = await Promise.all([
        privacyApi.getConsents(),
        privacyApi.getDSARs()
      ]);

      if (consentsRes.data?.success) {
        setConsents(consentsRes.data.consents || {});
      }
      if (dsarRes.data?.success) {
        setDsarRequests(dsarRes.data.requests || []);
      }
    } catch (error) {
      console.error('Failed to fetch privacy data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleConsentToggle = async (type, granted) => {
    setSaving(true);
    try {
      await privacyApi.updateConsent({ consent_type: type, granted, source: 'web' });
      setConsents(prev => ({
        ...prev,
        [type]: { ...prev[type], granted }
      }));
      setMessage({ type: 'success', text: 'Preference saved' });
    } catch (error) {
      console.error('Failed to update consent:', error);
      setMessage({ type: 'error', text: 'Failed to save preference' });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const handleDSARSubmit = async (requestType, details) => {
    setSubmitting(true);
    try {
      const response = await privacyApi.submitDSAR({
        request_type: requestType,
        email: user?.email,
        name: user?.name,
        details
      });

      if (response.data?.success) {
        setMessage({
          type: 'success',
          text: `Request submitted. Reference: ${response.data.request_number}`
        });
        fetchData(); // Refresh DSAR list
      }
    } catch (error) {
      console.error('Failed to submit DSAR:', error);
      setMessage({ type: 'error', text: 'Failed to submit request' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportData = async () => {
    setSaving(true);
    try {
      const response = await privacyApi.requestExport({
        email: user?.email,
        include_quotes: true,
        include_invoices: true,
        include_communications: true,
        format: 'json'
      });

      if (response.data?.success) {
        setMessage({
          type: 'success',
          text: 'Export requested. You will receive an email when ready.'
        });
      }
    } catch (error) {
      console.error('Failed to request export:', error);
      setMessage({ type: 'error', text: 'Failed to request export' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-theme-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Info Banner */}
      <div
        className="rounded-lg p-4 flex items-start gap-3 border"
        style={{
          backgroundColor: 'rgba(var(--color-primary-rgb, 124, 58, 237), 0.1)',
          borderColor: 'rgba(var(--color-primary-rgb, 124, 58, 237), 0.3)',
        }}
      >
        <InformationCircleIcon className="w-5 h-5 text-theme-primary flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium text-theme">Your Privacy Rights</p>
          <p className="text-sm text-theme-secondary">
            Under GDPR and POPIA, you have the right to access, correct, delete, and export your personal data.
            We process your data in accordance with our privacy policy.
          </p>
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div
          className="p-4 rounded-lg flex items-center gap-2"
          style={{
            backgroundColor: message.type === 'success'
              ? 'rgba(var(--color-success-rgb, 34, 197, 94), 0.15)'
              : 'rgba(var(--color-error-rgb, 239, 68, 68), 0.15)',
            color: message.type === 'success' ? 'var(--color-success)' : 'var(--color-error)',
          }}
        >
          {message.type === 'success' ? (
            <CheckCircleIcon className="w-5 h-5" />
          ) : (
            <ExclamationTriangleIcon className="w-5 h-5" />
          )}
          {message.text}
        </div>
      )}

      {/* Consent Management */}
      <div className="card">
        <h2 className="text-lg font-semibold text-theme mb-4">Communication Preferences</h2>
        <p className="text-sm text-theme-muted mb-4">
          Manage how we contact you and what data we collect.
        </p>
        <div className="space-y-3">
          {Object.entries(consentDescriptions).map(([type, config]) => (
            <ConsentToggle
              key={type}
              type={type}
              config={config}
              granted={consents[type]?.granted || false}
              onToggle={handleConsentToggle}
              disabled={saving}
            />
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-lg font-semibold text-theme mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={handleExportData}
            disabled={saving}
            className="flex items-center gap-3 p-4 border border-theme rounded-lg hover:bg-theme-border-light text-left transition-colors"
          >
            <div className="w-10 h-10 bg-theme-primary/15 rounded-lg flex items-center justify-center">
              <DocumentArrowDownIcon className="w-5 h-5 text-theme-primary" />
            </div>
            <div>
              <p className="font-medium text-theme">Download My Data</p>
              <p className="text-sm text-theme-muted">Export all your personal data</p>
            </div>
          </button>

          <button
            onClick={() => handleDSARSubmit('erasure', 'Requesting account deletion')}
            disabled={submitting}
            className="flex items-center gap-3 p-4 border rounded-lg text-left transition-colors"
            style={{
              borderColor: 'rgba(var(--color-error-rgb, 239, 68, 68), 0.3)',
            }}
          >
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: 'rgba(var(--color-error-rgb, 239, 68, 68), 0.15)' }}
            >
              <TrashIcon className="w-5 h-5 text-error" />
            </div>
            <div>
              <p className="font-medium text-theme">Delete My Account</p>
              <p className="text-sm text-theme-muted">Request account and data deletion</p>
            </div>
          </button>
        </div>
      </div>

      {/* DSAR Form */}
      <div className="card">
        <h2 className="text-lg font-semibold text-theme mb-4">Submit Data Request</h2>
        <p className="text-sm text-theme-muted mb-4">
          Exercise your data rights. We will respond within 30 days as required by law.
        </p>
        <DSARRequestForm onSubmit={handleDSARSubmit} loading={submitting} />
      </div>

      {/* Request History */}
      <div className="card">
        <h2 className="text-lg font-semibold text-theme mb-4">Request History</h2>
        <DSARHistory requests={dsarRequests} />
      </div>
    </div>
  );
}
