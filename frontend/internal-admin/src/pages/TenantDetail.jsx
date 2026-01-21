import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  GlobeAltIcon,
  CurrencyDollarIcon,
  UserGroupIcon,
  PauseCircleIcon,
  PlayCircleIcon,
  TrashIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { tenantsApi } from '../services/api';

export default function TenantDetail() {
  const { tenantId } = useParams();
  const [tenant, setTenant] = useState(null);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showSuspendModal, setShowSuspendModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [suspendReason, setSuspendReason] = useState('');

  useEffect(() => {
    loadData();
  }, [tenantId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [tenantRes, usageRes] = await Promise.all([
        tenantsApi.get(tenantId),
        tenantsApi.getStats(tenantId),
      ]);

      setTenant(tenantRes.data?.data || tenantRes.data);
      setUsage(usageRes.data?.data || usageRes.data);
    } catch (error) {
      console.error('Failed to load tenant:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => `R ${Number(amount || 0).toLocaleString()}`;

  const handleSuspend = async () => {
    if (!suspendReason.trim() || suspendReason.length < 5) {
      alert('Please provide a reason (at least 5 characters)');
      return;
    }
    try {
      setActionLoading(true);
      await tenantsApi.suspend(tenantId, suspendReason);
      setShowSuspendModal(false);
      setSuspendReason('');
      loadData(); // Refresh tenant data
    } catch (error) {
      console.error('Failed to suspend tenant:', error);
      alert('Failed to suspend tenant: ' + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleActivate = async () => {
    try {
      setActionLoading(true);
      await tenantsApi.activate(tenantId);
      loadData(); // Refresh tenant data
    } catch (error) {
      console.error('Failed to activate tenant:', error);
      alert('Failed to activate tenant: ' + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setActionLoading(true);
      await tenantsApi.delete(tenantId, true);
      setShowDeleteModal(false);
      // Navigate back to tenants list
      window.location.href = '/tenants';
    } catch (error) {
      console.error('Failed to delete tenant:', error);
      alert('Failed to delete tenant: ' + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/3 animate-pulse"></div>
        <div className="card animate-pulse">
          <div className="h-40 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500">Tenant not found</p>
        <Link to="/tenants" className="btn-primary mt-4 inline-block">
          Back to Tenants
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/tenants" className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeftIcon className="w-5 h-5 text-gray-600" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {tenant.client?.company_name || tenant.company_name || tenantId}
            </h1>
            <div className="flex items-center gap-2">
              <p className="text-gray-500">{tenant.tenant_id || tenantId}</p>
              {tenant.status === 'suspended' && (
                <span className="badge badge-error">Suspended</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
          {tenant.status === 'suspended' ? (
            <button
              onClick={handleActivate}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              <PlayCircleIcon className="w-5 h-5" />
              {actionLoading ? 'Activating...' : 'Activate'}
            </button>
          ) : (
            <button
              onClick={() => setShowSuspendModal(true)}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors disabled:opacity-50"
            >
              <PauseCircleIcon className="w-5 h-5" />
              Suspend
            </button>
          )}
          <button
            onClick={() => setShowDeleteModal(true)}
            disabled={actionLoading}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            <TrashIcon className="w-5 h-5" />
            Delete
          </button>
        </div>
      </div>

      {/* Usage Stats */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage Statistics</h3>

        {usage && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatBox label="Total Quotes" value={usage.quotes_count || 0} subValue={`${usage.quotes_this_month || 0} this month`} icon={GlobeAltIcon} />
            <StatBox label="Invoices" value={usage.invoices_count || 0} subValue={`${usage.invoices_paid || 0} paid`} icon={CurrencyDollarIcon} />
            <StatBox label="Total Paid" value={formatCurrency(usage.total_paid)} color="green" icon={CurrencyDollarIcon} />
            <StatBox label="Users" value={usage.users_count || 0} subValue={`${usage.clients_count || 0} CRM clients`} icon={UserGroupIcon} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tenant Info */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Tenant Information</h3>
          <dl className="space-y-3">
            <InfoRow label="Tenant ID" value={tenant.tenant_id} mono />
            <InfoRow label="Name" value={tenant.client?.name} />
            <InfoRow label="Company" value={tenant.client?.company_name} />
            <InfoRow label="Short Name" value={tenant.client?.short_name} />
            <InfoRow label="Currency" value={tenant.client?.currency} />
            <InfoRow label="Timezone" value={tenant.client?.timezone} />
          </dl>
        </div>

        {/* Destinations from BigQuery */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Destinations ({tenant.destinations_count || tenant.destinations?.length || 0})
            </h3>
            <div className="flex gap-4 text-sm text-gray-500">
              <span>{tenant.hotels_count || 0} hotels</span>
              <span>{tenant.rates_count || 0} rates</span>
            </div>
          </div>
          {tenant.destinations?.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {tenant.destinations.map((dest) => (
                <span
                  key={dest.code || dest.name}
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    dest.enabled !== false
                      ? 'bg-blue-50 text-blue-700'
                      : 'bg-gray-100 text-gray-400'
                  }`}
                  title={dest.hotel_count ? `${dest.hotel_count} hotels, ${dest.rate_count} rates` : ''}
                >
                  {dest.name}
                  {dest.hotel_count && <span className="ml-1 text-blue-500">({dest.hotel_count})</span>}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No destinations with active rates</p>
          )}
        </div>

        {/* Infrastructure */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Infrastructure</h3>
          <dl className="space-y-3">
            <InfoRow label="GCP Project" value={tenant.infrastructure?.gcp_project} mono />
            <InfoRow label="GCP Region" value={tenant.infrastructure?.gcp_region} />
            <InfoRow label="Dataset" value={tenant.infrastructure?.dataset} />
            <InfoRow
              label="Supabase"
              value={tenant.infrastructure?.supabase_configured ? 'Configured' : 'Not configured'}
              badge={tenant.infrastructure?.supabase_configured}
            />
          </dl>
        </div>

        {/* Email Configuration */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Email</h3>
          <dl className="space-y-3">
            <InfoRow
              label="SendGrid"
              value={tenant.infrastructure?.email?.sendgrid_configured ? 'Configured' : 'Not configured'}
              badge={tenant.infrastructure?.email?.sendgrid_configured}
            />
            <InfoRow label="From Email" value={tenant.infrastructure?.email?.from_email} />
          </dl>
        </div>

        {/* Consultants */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Consultants ({tenant.consultants?.length || 0})
          </h3>
          {tenant.consultants?.length > 0 ? (
            <div className="space-y-2">
              {tenant.consultants.map((consultant, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">{consultant.name}</p>
                    <p className="text-sm text-gray-500">{consultant.email}</p>
                  </div>
                  <span className={`badge ${consultant.active !== false ? 'badge-success' : 'badge-error'}`}>
                    {consultant.active !== false ? 'Active' : 'Inactive'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No consultants configured</p>
          )}
        </div>
      </div>

      {/* Suspend Modal */}
      {showSuspendModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <ExclamationTriangleIcon className="w-6 h-6 text-yellow-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Suspend Tenant</h3>
            </div>
            <p className="text-gray-600 mb-4">
              This will prevent the tenant from generating quotes, sending emails, and accessing the platform.
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reason for suspension
              </label>
              <textarea
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                placeholder="Enter reason for suspension..."
                className="input h-24 resize-none"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowSuspendModal(false);
                  setSuspendReason('');
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSuspend}
                disabled={actionLoading || suspendReason.length < 5}
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50"
              >
                {actionLoading ? 'Suspending...' : 'Suspend Tenant'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <TrashIcon className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Tenant</h3>
            </div>
            <p className="text-gray-600 mb-2">
              <strong className="text-red-600">Warning:</strong> This action is irreversible!
            </p>
            <p className="text-gray-600 mb-4">
              Deleting this tenant will permanently remove:
            </p>
            <ul className="list-disc list-inside text-gray-600 mb-4 space-y-1">
              <li>All quotes and invoices</li>
              <li>All CRM clients and activities</li>
              <li>All user accounts</li>
              <li>All tenant configuration</li>
            </ul>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {actionLoading ? 'Deleting...' : 'Yes, Delete Tenant'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, subValue, icon: Icon, color = 'zorah' }) {
  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-gray-500">{label}</p>
        <Icon className={`w-5 h-5 text-${color}-600`} />
      </div>
      <p className={`text-xl font-bold text-${color === 'green' ? 'green-600' : 'gray-900'}`}>
        {value}
      </p>
      {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}
    </div>
  );
}

function InfoRow({ label, value, badge, mono }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <dt className="text-sm text-gray-500">{label}</dt>
      <dd className="flex items-center gap-2">
        {badge !== undefined && (
          badge ? (
            <CheckCircleIcon className="w-4 h-4 text-green-500" />
          ) : (
            <XCircleIcon className="w-4 h-4 text-gray-300" />
          )
        )}
        <span className={`font-medium ${mono ? 'font-mono text-xs' : ''}`}>
          {value || '-'}
        </span>
      </dd>
    </div>
  );
}
