import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  ArrowPathIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import { tenantsApi } from '../services/api';

export default function TenantsList() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      setLoading(true);
      const response = await tenantsApi.listSummary();
      setTenants(response.data?.data || response.data?.tenants || []);
    } catch (error) {
      console.error('Failed to load tenants:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTenants = tenants.filter((tenant) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      tenant.tenant_id?.toLowerCase().includes(searchLower) ||
      tenant.company_name?.toLowerCase().includes(searchLower) ||
      tenant.name?.toLowerCase().includes(searchLower)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tenants</h1>
          <p className="text-gray-500 mt-1">{tenants.length} registered tenants</p>
        </div>
        <button onClick={loadTenants} className="btn-secondary flex items-center gap-2">
          <ArrowPathIcon className="w-5 h-5" />
          Refresh
        </button>
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search tenants by name or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Tenants Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 bg-gray-200 rounded-lg"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-2/3 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
              <div className="h-20 bg-gray-100 rounded"></div>
            </div>
          ))}
        </div>
      ) : filteredTenants.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No tenants found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTenants.map((tenant) => (
            <div key={tenant.tenant_id} className="card hover:shadow-md transition-shadow">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-zorah-100 rounded-lg flex items-center justify-center">
                    <span className="font-bold text-xl text-zorah-600">
                      {tenant.company_name?.charAt(0) || 'T'}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tenant.company_name}</h3>
                    <p className="text-sm text-gray-500">{tenant.tenant_id}</p>
                  </div>
                </div>
                <span className={`badge ${tenant.status === 'active' ? 'badge-success' : 'badge-error'}`}>
                  {tenant.status || 'active'}
                </span>
              </div>

              {/* Usage Stats */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Currency</span>
                  <span className="font-medium">{tenant.currency || 'ZAR'}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Quotes</span>
                  <span className="font-medium">{tenant.quote_count || 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Invoices</span>
                  <span className="font-medium">{tenant.invoice_count || 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Total Invoiced</span>
                  <span className="font-medium text-green-600">R {Number(tenant.total_invoiced || 0).toLocaleString()}</span>
                </div>
              </div>

              {/* Actions */}
              <Link
                to={`/tenants/${tenant.tenant_id}`}
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                <EyeIcon className="w-4 h-4" />
                View Details
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
