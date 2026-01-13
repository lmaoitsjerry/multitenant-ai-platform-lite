import { useState, useEffect, useMemo, memo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { crmApi } from '../../services/api';
import {
  PlusIcon,
  UserIcon,
  PhoneIcon,
  EnvelopeIcon,
  MapPinIcon,
  CurrencyDollarIcon,
  ArrowPathIcon,
  Squares2X2Icon,
  TableCellsIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

const STAGES = [
  { id: 'QUOTED', label: 'Quoted', color: 'bg-blue-500' },
  { id: 'NEGOTIATING', label: 'Negotiating', color: 'bg-yellow-500' },
  { id: 'BOOKED', label: 'Booked', color: 'bg-purple-500' },
  { id: 'PAID', label: 'Paid', color: 'bg-green-500' },
  { id: 'TRAVELLED', label: 'Travelled', color: 'bg-teal-500' },
  { id: 'LOST', label: 'Lost', color: 'bg-red-500' },
];

// Memoized ClientCard to prevent re-renders when client data hasn't changed
const ClientCard = memo(function ClientCard({ client }) {
  return (
    <Link
      to={`/crm/clients/${client.client_id}`}
      className="block bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-gray-900 truncate">{client.name}</h4>
        {client.value > 0 && (
          <span className="text-sm font-medium text-green-600">
            R {Number(client.value).toLocaleString()}
          </span>
        )}
      </div>

      {client.destination && (
        <div className="flex items-center gap-1 text-sm text-gray-500 mb-2">
          <MapPinIcon className="w-4 h-4" />
          <span>{client.destination}</span>
        </div>
      )}

      <div className="flex items-center gap-3 text-xs text-gray-400">
        {client.email && (
          <div className="flex items-center gap-1">
            <EnvelopeIcon className="w-3 h-3" />
            <span className="truncate max-w-24">{client.email}</span>
          </div>
        )}
        {client.phone && (
          <div className="flex items-center gap-1">
            <PhoneIcon className="w-3 h-3" />
            <span>{client.phone}</span>
          </div>
        )}
      </div>

      {client.last_activity && (
        <p className="text-xs text-gray-400 mt-2">
          Last activity: {new Date(client.last_activity).toLocaleDateString()}
        </p>
      )}
    </Link>
  );
});

// Memoized PipelineColumn - now receives pre-filtered stageClients instead of filtering internally
const PipelineColumn = memo(function PipelineColumn({ stage, stageClients, onDrop }) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    const clientId = e.dataTransfer.getData('clientId');
    if (clientId) {
      onDrop(clientId, stage.id);
    }
  }, [onDrop, stage.id]);

  return (
    <div
      className={`flex-1 min-w-64 max-w-80 ${isDragOver ? 'bg-purple-50' : 'bg-gray-50'} rounded-lg p-3 transition-colors`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Column Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${stage.color}`}></div>
          <h3 className="font-semibold text-gray-700">{stage.label}</h3>
          <span className="text-sm text-gray-400">({stageClients.length})</span>
        </div>
      </div>

      {/* Cards */}
      <div className="space-y-3 min-h-96">
        {stageClients.map((client) => (
          <div
            key={client.client_id || client.id}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData('clientId', client.client_id || client.id);
            }}
            className="cursor-move"
          >
            <ClientCard client={client} />
          </div>
        ))}

        {stageClients.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            No clients in this stage
          </div>
        )}
      </div>
    </div>
  );
});

function PipelineTable({ clients, stages, onStageChange }) {
  return (
    <div className="card overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Destination</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stage</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Activity</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {clients.map((client) => {
            const stage = stages.find(s => s.id === client.pipeline_stage);
            return (
              <tr key={client.client_id || client.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link to={`/crm/clients/${client.client_id}`} className="text-primary-600 hover:text-primary-900 font-medium">
                    {client.name}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {client.email || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {client.destination || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <select
                    value={client.pipeline_stage || 'QUOTED'}
                    onChange={(e) => onStageChange(client.client_id || client.id, e.target.value)}
                    className="text-sm border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                  >
                    {stages.map((s) => (
                      <option key={s.id} value={s.id}>{s.label}</option>
                    ))}
                  </select>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {client.value > 0 ? `R ${Number(client.value).toLocaleString()}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {client.last_activity ? new Date(client.last_activity).toLocaleDateString() : '-'}
                </td>
              </tr>
            );
          })}
          {clients.length === 0 && (
            <tr>
              <td colSpan="6" className="px-6 py-12 text-center text-gray-500">
                No clients found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function Pipeline() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [viewMode, setViewMode] = useState(() => {
    return localStorage.getItem('pipeline_view') || 'kanban';
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState(null);

  // Memoized loadData to prevent recreation
  const loadData = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true);
      const [clientsRes, statsRes] = await Promise.all([
        crmApi.listClients({ limit: 100 }, forceRefresh),
        crmApi.getPipeline().catch(() => null),
      ]);

      // Use clients data directly - backend now returns enriched data
      setClients(clientsRes.data?.data || []);
      if (statsRes) {
        setStats(statsRes.data?.data);
      }
    } catch (error) {
      console.error('Failed to load pipeline data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    localStorage.setItem('pipeline_view', viewMode);
  }, [viewMode]);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Handle create client
  const handleCreateClient = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    setCreating(true);
    try {
      const response = await crmApi.createClient({
        name: formData.get('name'),
        email: formData.get('email'),
        phone: formData.get('phone') || null,
        source: formData.get('source')
      });

      if (response.data?.success) {
        setShowAddModal(false);
        setToast({ type: 'success', message: 'Client created successfully!' });
        loadData(true); // Force refresh the list (bypass cache)
      } else {
        setToast({ type: 'error', message: response.data?.error || 'Failed to create client' });
      }
    } catch (error) {
      console.error('Failed to create client:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to create client';
      setToast({ type: 'error', message: errorMsg });
    } finally {
      setCreating(false);
    }
  };

  // Memoized stage drop handler
  const handleStageDrop = useCallback(async (clientId, newStage) => {
    // Optimistic update
    setClients(prev => prev.map(c =>
      (c.client_id === clientId || c.id === clientId) ? { ...c, pipeline_stage: newStage } : c
    ));

    try {
      await crmApi.updateStage(clientId, newStage);
    } catch (error) {
      console.error('Failed to update client stage:', error);
      // Revert on error
      loadData();
    }
  }, [loadData]);

  // Memoize total value calculation - only recalculates when clients change
  const totalValue = useMemo(() =>
    clients.reduce((sum, c) => sum + (Number(c.value) || 0), 0),
    [clients]
  );

  // Memoize stage values calculation - only recalculates when clients change
  const stageValues = useMemo(() =>
    STAGES.reduce((acc, stage) => {
      acc[stage.id] = clients
        .filter(c => c.pipeline_stage === stage.id)
        .reduce((sum, c) => sum + (Number(c.value) || 0), 0);
      return acc;
    }, {}),
    [clients]
  );

  // Pre-compute clients grouped by stage - prevents filtering in each PipelineColumn
  const clientsByStage = useMemo(() =>
    STAGES.reduce((acc, stage) => {
      acc[stage.id] = clients.filter(c => c.pipeline_stage === stage.id);
      return acc;
    }, {}),
    [clients]
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-32 bg-gray-200 rounded animate-pulse"></div>
            <div className="h-4 w-48 bg-gray-100 rounded animate-pulse mt-2"></div>
          </div>
          <div className="flex gap-3">
            <div className="h-10 w-24 bg-gray-200 rounded animate-pulse"></div>
            <div className="h-10 w-32 bg-gray-200 rounded animate-pulse"></div>
          </div>
        </div>
        {/* Stats skeleton */}
        <div className="grid grid-cols-6 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="card p-4">
              <div className="h-4 w-20 bg-gray-200 rounded animate-pulse mb-2"></div>
              <div className="h-6 w-24 bg-gray-200 rounded animate-pulse"></div>
            </div>
          ))}
        </div>
        {/* Kanban skeleton */}
        <div className="flex gap-4 overflow-x-auto pb-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="flex-1 min-w-64 max-w-80 bg-gray-50 rounded-lg p-3">
              <div className="h-6 w-24 bg-gray-200 rounded animate-pulse mb-4"></div>
              <div className="space-y-3">
                {[1, 2].map(j => (
                  <div key={j} className="bg-white rounded-lg border border-gray-200 p-4">
                    <div className="h-5 w-32 bg-gray-200 rounded animate-pulse mb-2"></div>
                    <div className="h-4 w-24 bg-gray-100 rounded animate-pulse"></div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
          <p className="text-gray-500 mt-1">
            {clients.length} clients • Total value: R {totalValue.toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View Toggle */}
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            <button
              onClick={() => setViewMode('kanban')}
              className={`px-3 py-2 flex items-center gap-1 text-sm ${
                viewMode === 'kanban'
                  ? 'bg-primary-50 text-primary-700'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              title="Kanban view"
            >
              <Squares2X2Icon className="w-4 h-4" />
              <span className="hidden sm:inline">Kanban</span>
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-2 flex items-center gap-1 text-sm border-l border-gray-300 ${
                viewMode === 'table'
                  ? 'bg-primary-50 text-primary-700'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              title="Table view"
            >
              <TableCellsIcon className="w-4 h-4" />
              <span className="hidden sm:inline">Table</span>
            </button>
          </div>
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
          <Link to="/crm/clients" className="btn-secondary">
            View All Clients
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

      {/* Stats */}
      <div className="grid grid-cols-6 gap-4">
        {STAGES.map((stage) => (
          <div key={stage.id} className="card p-4">
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${stage.color}`}></div>
              <span className="text-sm text-gray-500">{stage.label}</span>
            </div>
            <p className="text-lg font-bold text-gray-900">
              R {(stageValues[stage.id] || 0).toLocaleString()}
            </p>
            <p className="text-xs text-gray-400">
              {clientsByStage[stage.id]?.length || 0} clients
            </p>
          </div>
        ))}
      </div>

      {/* Kanban Board */}
      {viewMode === 'kanban' && (
        <>
          <div className="flex gap-4 overflow-x-auto pb-4">
            {STAGES.map((stage) => (
              <PipelineColumn
                key={stage.id}
                stage={stage}
                stageClients={clientsByStage[stage.id] || []}
                onDrop={handleStageDrop}
              />
            ))}
          </div>
          <p className="text-sm text-gray-400 text-center">
            Drag and drop clients between stages to update their status
          </p>
        </>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <PipelineTable
          clients={clients}
          stages={STAGES}
          onStageChange={handleStageDrop}
        />
      )}

      {/* Add Client Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[9999] overflow-y-auto">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
            onClick={() => setShowAddModal(false)}
          />

          {/* Modal Container */}
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md transform transition-all">
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Add New Client</h3>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleCreateClient} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    name="name"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    placeholder="Client name"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                  <input
                    type="email"
                    name="email"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    placeholder="client@example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    name="phone"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    placeholder="+27 82 123 4567"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
                  <select
                    name="source"
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 appearance-none cursor-pointer"
                    style={{
                      backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                      backgroundPosition: 'right 0.5rem center',
                      backgroundRepeat: 'no-repeat',
                      backgroundSize: '1.5em 1.5em',
                      paddingRight: '2.5rem'
                    }}
                  >
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
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {creating ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <PlusIcon className="w-5 h-5" />
                        Add Client
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-toast">
          <div
            className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg ${
              toast.type === 'success'
                ? 'bg-green-600 text-white'
                : 'bg-red-600 text-white'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircleIcon className="w-5 h-5" />
            ) : (
              <ExclamationCircleIcon className="w-5 h-5" />
            )}
            <span className="text-sm font-medium">{toast.message}</span>
            <button
              onClick={() => setToast(null)}
              className="p-1 hover:bg-white/20 rounded transition-colors"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}