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
  PhoneIcon,
} from '@heroicons/react/24/outline';
import { tenantsApi, provisioningApi } from '../services/api';

export default function TenantDetail() {
  const { tenantId } = useParams();
  const [tenant, setTenant] = useState(null);
  const [usage, setUsage] = useState(null);
  const [vapiStatus, setVapiStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('month');

  useEffect(() => {
    loadData();
  }, [tenantId, period]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [tenantRes, usageRes, vapiRes] = await Promise.all([
        tenantsApi.get(tenantId),
        tenantsApi.getUsage(tenantId, period),
        provisioningApi.getVAPIStatus(tenantId).catch(() => null),
      ]);

      setTenant(tenantRes.data);
      setUsage(usageRes.data);
      setVapiStatus(vapiRes?.data);
    } catch (error) {
      console.error('Failed to load tenant:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => `R ${Number(amount || 0).toLocaleString()}`;

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
              {tenant.client?.company_name || tenantId}
            </h1>
            <p className="text-gray-500">{tenantId}</p>
          </div>
        </div>
        <button onClick={loadData} className="btn-secondary flex items-center gap-2">
          <ArrowPathIcon className="w-5 h-5" />
          Refresh
        </button>
      </div>

      {/* Usage Stats */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Usage Statistics</h3>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="input w-36"
          >
            <option value="day">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
          </select>
        </div>

        {usage && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatBox label="Quotes" value={usage.quotes_generated} icon={GlobeAltIcon} />
            <StatBox label="Invoices" value={usage.invoices_created} subValue={`${usage.invoices_paid} paid`} icon={CurrencyDollarIcon} />
            <StatBox label="Revenue" value={formatCurrency(usage.total_revenue)} color="green" icon={CurrencyDollarIcon} />
            <StatBox label="Active Users" value={usage.active_users} icon={UserGroupIcon} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tenant Info */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Tenant Information</h3>
          <dl className="space-y-3">
            <InfoRow label="Name" value={tenant.client?.name} />
            <InfoRow label="Company" value={tenant.client?.company_name} />
            <InfoRow label="Short Name" value={tenant.client?.short_name} />
            <InfoRow label="Currency" value={tenant.client?.currency} />
            <InfoRow label="Timezone" value={tenant.client?.timezone} />
          </dl>
        </div>

        {/* Destinations */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Destinations ({tenant.destinations?.length || 0})
          </h3>
          <div className="flex flex-wrap gap-2">
            {tenant.destinations?.map((dest) => (
              <span
                key={dest.code || dest.name}
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  dest.enabled !== false
                    ? 'bg-blue-50 text-blue-700'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {dest.name}
              </span>
            )) || <p className="text-gray-500">No destinations configured</p>}
          </div>
        </div>

        {/* Infrastructure */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Infrastructure</h3>
          <dl className="space-y-3">
            <InfoRow label="GCP Project" value={tenant.infrastructure?.gcp_project} />
            <InfoRow label="Region" value={tenant.infrastructure?.gcp_region} />
            <InfoRow label="Dataset" value={tenant.infrastructure?.dataset} />
            <InfoRow
              label="Supabase"
              value={tenant.infrastructure?.supabase_configured ? 'Configured' : 'Not configured'}
              badge={tenant.infrastructure?.supabase_configured}
            />
          </dl>
        </div>

        {/* VAPI Status */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Voice (VAPI)</h3>
          {vapiStatus ? (
            <dl className="space-y-3">
              <InfoRow
                label="VAPI Configured"
                value={vapiStatus.vapi_configured ? 'Yes' : 'No'}
                badge={vapiStatus.vapi_configured}
              />
              <InfoRow
                label="Ready for Calls"
                value={vapiStatus.ready_for_calls ? 'Yes' : 'No'}
                badge={vapiStatus.ready_for_calls}
              />
              <InfoRow label="Inbound Assistant" value={vapiStatus.inbound_assistant_id || '-'} mono />
              <InfoRow label="Outbound Assistant" value={vapiStatus.outbound_assistant_id || '-'} mono />
              <InfoRow label="Phone Number ID" value={vapiStatus.phone_number_id || '-'} mono />
            </dl>
          ) : (
            <p className="text-gray-500">VAPI not configured</p>
          )}
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
