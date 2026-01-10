import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { privacyApi } from '../../services/api';
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
  const Icon = config.icon;

  return (
    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
          <Icon className="w-5 h-5 text-gray-600" />
        </div>
        <div>
          <p className="font-medium text-gray-900">{config.label}</p>
          <p className="text-sm text-gray-500">{config.description}</p>
        </div>
      </div>
      <label className="relative inline-flex cursor-pointer">
        <input
          type="checkbox"
          checked={granted}
          onChange={() => onToggle(type, !granted)}
          disabled={disabled}
          className="sr-only peer"
        />
        <div className={`w-11 h-6 rounded-full peer ${
          disabled ? 'bg-gray-300' : 'bg-gray-200 peer-checked:bg-primary-600'
        } after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full`}></div>
      </label>
    </div>
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
        <label className="block text-sm font-medium text-gray-700 mb-2">Request Type</label>
        <div className="space-y-2">
          {requestTypes.map((type) => (
            <label
              key={type.value}
              className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer ${
                requestType === type.value ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'
              }`}
            >
              <input
                type="radio"
                name="requestType"
                value={type.value}
                checked={requestType === type.value}
                onChange={(e) => setRequestType(e.target.value)}
                className="mt-1"
              />
              <div>
                <p className="font-medium text-gray-900">{type.label}</p>
                <p className="text-sm text-gray-500">{type.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
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
  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    verified: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
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
      <div className="text-center py-8 text-gray-500">
        <ShieldCheckIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
        <p>No previous requests</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {requests.map((req) => {
        const StatusIcon = statusIcons[req.status] || ClockIcon;
        return (
          <div key={req.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                <StatusIcon className="w-5 h-5 text-gray-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900 capitalize">{req.request_type.replace('_', ' ')} Request</p>
                <p className="text-sm text-gray-500">
                  {new Date(req.created_at).toLocaleDateString()} - Due: {new Date(req.due_date).toLocaleDateString()}
                </p>
              </div>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${statusColors[req.status] || 'bg-gray-100 text-gray-800'}`}>
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
        <InformationCircleIcon className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium text-blue-900">Your Privacy Rights</p>
          <p className="text-sm text-blue-700">
            Under GDPR and POPIA, you have the right to access, correct, delete, and export your personal data.
            We process your data in accordance with our privacy policy.
          </p>
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-2 ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
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
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Communication Preferences</h2>
        <p className="text-sm text-gray-500 mb-4">
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
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={handleExportData}
            disabled={saving}
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 text-left"
          >
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <DocumentArrowDownIcon className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Download My Data</p>
              <p className="text-sm text-gray-500">Export all your personal data</p>
            </div>
          </button>

          <button
            onClick={() => handleDSARSubmit('erasure', 'Requesting account deletion')}
            disabled={submitting}
            className="flex items-center gap-3 p-4 border border-red-200 rounded-lg hover:bg-red-50 text-left"
          >
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <TrashIcon className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Delete My Account</p>
              <p className="text-sm text-gray-500">Request account and data deletion</p>
            </div>
          </button>
        </div>
      </div>

      {/* DSAR Form */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Submit Data Request</h2>
        <p className="text-sm text-gray-500 mb-4">
          Exercise your data rights. We will respond within 30 days as required by law.
        </p>
        <DSARRequestForm onSubmit={handleDSARSubmit} loading={submitting} />
      </div>

      {/* Request History */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Request History</h2>
        <DSARHistory requests={dsarRequests} />
      </div>
    </div>
  );
}
