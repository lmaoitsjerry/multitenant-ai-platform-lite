import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { crmApi } from '../../services/api';
import { SkeletonTable } from '../../components/ui/Skeleton';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  UserIcon,
  EnvelopeIcon,
  PhoneIcon,
  MapPinIcon,
} from '@heroicons/react/24/outline';

const stageColors = {
  QUOTED: 'bg-blue-100 text-blue-700',
  NEGOTIATING: 'bg-yellow-100 text-yellow-700',
  BOOKED: 'bg-purple-100 text-purple-700',
  PAID: 'bg-green-100 text-green-700',
  TRAVELLED: 'bg-teal-100 text-teal-700',
  LOST: 'bg-red-100 text-red-700',
};

export default function ClientsList() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadClients();
  }, [stageFilter]);

  const handleCreateClient = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    setCreating(true);
    try {
      await crmApi.createClient({
        name: formData.get('name'),
        email: formData.get('email'),
        phone: formData.get('phone') || null,
        source: formData.get('source')
      });
      setShowAddModal(false);
      loadClients(); // Refresh the list
    } catch (error) {
      console.error('Failed to create client:', error);
      alert('Failed to create client. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const loadClients = async () => {
    try {
      setLoading(true);
      const params = { limit: 100 };
      if (stageFilter) params.pipeline_stage = stageFilter;
      
      const response = await crmApi.listClients(params);
      setClients(response.data?.data || []);
    } catch (error) {
      console.error('Failed to load clients:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredClients = clients.filter(client => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      client.name?.toLowerCase().includes(searchLower) ||
      client.email?.toLowerCase().includes(searchLower) ||
      client.phone?.includes(search) ||
      client.destination?.toLowerCase().includes(searchLower)
    );
  });

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return `R ${Number(amount).toLocaleString()}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
          <p className="text-gray-500 mt-1">{clients.length} total clients</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/crm/pipeline" className="btn-secondary">
            View Pipeline
          </Link>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <PlusIcon className="w-5 h-5" />
            Add Client
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <div className="relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name, email, phone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>

          {/* Stage Filter */}
          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="input w-44"
          >
            <option value="">All Stages</option>
            <option value="QUOTED">Quoted</option>
            <option value="NEGOTIATING">Negotiating</option>
            <option value="BOOKED">Booked</option>
            <option value="PAID">Paid</option>
            <option value="TRAVELLED">Travelled</option>
            <option value="LOST">Lost</option>
          </select>

          {/* Refresh */}
          <button
            onClick={loadClients}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Clients Table */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <SkeletonTable rows={5} columns={6} />
        ) : filteredClients.length === 0 ? (
          <div className="text-center py-12">
            <UserIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No clients found</h3>
            <p className="text-gray-500 mt-1">Add your first client to get started</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-primary inline-flex items-center gap-2 mt-4"
            >
              <PlusIcon className="w-5 h-5" />
              Add Client
            </button>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Contact</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Destination</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Stage</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Last Activity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredClients.map((client) => (
                <tr key={client.id} className="hover:bg-gray-50" onMouseEnter={() => crmApi.prefetch(client.id)}>
                  <td className="px-6 py-4">
                    <Link to={`/crm/clients/${client.id}`} className="flex items-center gap-3 hover:text-purple-600">
                      <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                        <span className="text-purple-600 font-medium">
                          {client.name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                      <span className="font-medium text-gray-900">{client.name}</span>
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <div className="space-y-1">
                      {client.email && (
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <EnvelopeIcon className="w-4 h-4 text-gray-400" />
                          {client.email}
                        </div>
                      )}
                      {client.phone && (
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <PhoneIcon className="w-4 h-4 text-gray-400" />
                          {client.phone}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {client.destination ? (
                      <div className="flex items-center gap-1 text-gray-600">
                        <MapPinIcon className="w-4 h-4 text-gray-400" />
                        {client.destination}
                      </div>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 font-medium text-gray-900">
                    {formatCurrency(client.value)}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${stageColors[client.pipeline_stage] || 'bg-gray-100 text-gray-700'}`}>
                      {client.pipeline_stage || 'New'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {client.last_activity 
                      ? new Date(client.last_activity).toLocaleDateString()
                      : '-'
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Client Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add New Client</h3>
            <form onSubmit={handleCreateClient} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  name="name"
                  required
                  className="input"
                  placeholder="Client name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  name="email"
                  required
                  className="input"
                  placeholder="client@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  type="tel"
                  name="phone"
                  className="input"
                  placeholder="+27 82 123 4567"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
                <select name="source" className="input">
                  <option value="manual">Manual Entry</option>
                  <option value="referral">Referral</option>
                  <option value="website">Website</option>
                  <option value="email">Email Inquiry</option>
                </select>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="btn-primary flex-1"
                >
                  {creating ? 'Creating...' : 'Add Client'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
