import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { crmApi, quotesApi } from '../../services/api';
import {
  ArrowLeftIcon,
  EnvelopeIcon,
  PhoneIcon,
  MapPinIcon,
  PencilIcon,
  TrashIcon,
  PlusIcon,
  DocumentTextIcon,
  ChatBubbleLeftIcon,
  CurrencyDollarIcon,
  CalendarIcon,
  UserIcon,
} from '@heroicons/react/24/outline';

const stageColors = {
  QUOTED: 'bg-blue-100 text-blue-700',
  NEGOTIATING: 'bg-yellow-100 text-yellow-700',
  BOOKED: 'bg-purple-100 text-purple-700',
  PAID: 'bg-green-100 text-green-700',
  TRAVELLED: 'bg-teal-100 text-teal-700',
  LOST: 'bg-red-100 text-red-700',
};

const activityIcons = {
  quote: DocumentTextIcon,
  email: EnvelopeIcon,
  call: PhoneIcon,
  note: ChatBubbleLeftIcon,
  meeting: CalendarIcon,
  payment: CurrencyDollarIcon,
};

export default function ClientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [client, setClient] = useState(null);
  const [activities, setActivities] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [newNote, setNewNote] = useState('');

  useEffect(() => {
    loadClient();
  }, [id]);

  const loadClient = async () => {
    try {
      setLoading(true);
      const [clientRes, activitiesRes] = await Promise.all([
        crmApi.getClient(id),
        crmApi.getActivities(id).catch(() => ({ data: { data: [] } })),
      ]);
      
      setClient(clientRes.data?.data || clientRes.data);
      setActivities(activitiesRes.data?.data || []);
      
      // Load quotes for this client
      if (clientRes.data?.data?.email || clientRes.data?.email) {
        const email = clientRes.data?.data?.email || clientRes.data?.email;
        const quotesRes = await quotesApi.list({ customer_email: email }).catch(() => ({ data: { data: [] } }));
        setQuotes(quotesRes.data?.data || []);
      }
    } catch (error) {
      console.error('Failed to load client:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStageChange = async (newStage) => {
    try {
      await crmApi.updateClient(id, { pipeline_stage: newStage });
      setClient(prev => ({ ...prev, pipeline_stage: newStage }));
    } catch (error) {
      console.error('Failed to update stage:', error);
    }
  };

  const handleAddNote = async () => {
    if (!newNote.trim()) return;
    
    try {
      await crmApi.logActivity(id, {
        type: 'note',
        description: newNote,
      });
      setNewNote('');
      setShowNoteModal(false);
      loadClient();
    } catch (error) {
      console.error('Failed to add note:', error);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-ZA', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('en-ZA', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return `R ${Number(amount).toLocaleString()}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!client) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">Client not found</h2>
        <Link to="/crm/clients" className="btn-primary inline-block mt-4">
          Back to Clients
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/crm/clients')}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeftIcon className="w-5 h-5 text-gray-500" />
          </button>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
              <span className="text-2xl font-bold text-purple-600">
                {client.name?.charAt(0)?.toUpperCase() || '?'}
              </span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{client.name}</h1>
              <div className="flex items-center gap-4 mt-1">
                {client.email && (
                  <span className="text-gray-500 flex items-center gap-1">
                    <EnvelopeIcon className="w-4 h-4" />
                    {client.email}
                  </span>
                )}
                {client.phone && (
                  <span className="text-gray-500 flex items-center gap-1">
                    <PhoneIcon className="w-4 h-4" />
                    {client.phone}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-secondary flex items-center gap-2">
            <PencilIcon className="w-5 h-5" />
            Edit
          </button>
          <Link to="/quotes/new" className="btn-primary flex items-center gap-2">
            <PlusIcon className="w-5 h-5" />
            New Quote
          </Link>
        </div>
      </div>

      {/* Pipeline Stage */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-500 mb-3">Pipeline Stage</h3>
        <div className="flex gap-2 flex-wrap">
          {Object.entries(stageColors).map(([stage, color]) => (
            <button
              key={stage}
              onClick={() => handleStageChange(stage)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                client.pipeline_stage === stage
                  ? `${color} ring-2 ring-offset-2 ring-purple-500`
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {stage}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-8">
          {['overview', 'quotes', 'activities'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium capitalize border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
              {tab === 'quotes' && quotes.length > 0 && (
                <span className="ml-2 bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs">
                  {quotes.length}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Client Details */}
          <div className="lg:col-span-2 space-y-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Client Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Full Name</p>
                  <p className="font-medium text-gray-900">{client.name || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Email</p>
                  <p className="font-medium text-gray-900">{client.email || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Phone</p>
                  <p className="font-medium text-gray-900">{client.phone || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Destination Interest</p>
                  <p className="font-medium text-gray-900">{client.destination || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Source</p>
                  <p className="font-medium text-gray-900 capitalize">{client.source || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created</p>
                  <p className="font-medium text-gray-900">{formatDate(client.created_at)}</p>
                </div>
              </div>
            </div>

            {/* Notes */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Notes</h3>
                <button
                  onClick={() => setShowNoteModal(true)}
                  className="btn-secondary text-sm flex items-center gap-1"
                >
                  <PlusIcon className="w-4 h-4" />
                  Add Note
                </button>
              </div>
              {client.notes ? (
                <p className="text-gray-700 whitespace-pre-wrap">{client.notes}</p>
              ) : (
                <p className="text-gray-400 italic">No notes yet</p>
              )}
            </div>
          </div>

          {/* Sidebar Stats */}
          <div className="space-y-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Value</h3>
              <p className="text-3xl font-bold text-green-600">
                {formatCurrency(client.value)}
              </p>
              <p className="text-sm text-gray-500 mt-1">Total quoted value</p>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Stats</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500">Quotes</span>
                  <span className="font-medium">{quotes.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Activities</span>
                  <span className="font-medium">{activities.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Last Activity</span>
                  <span className="font-medium">{formatDate(client.last_activity)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'quotes' && (
        <div className="card p-0">
          {quotes.length === 0 ? (
            <div className="text-center py-12">
              <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No quotes yet</h3>
              <p className="text-gray-500 mt-1">Create a quote for this client</p>
              <Link to="/quotes/new" className="btn-primary inline-flex items-center gap-2 mt-4">
                <PlusIcon className="w-5 h-5" />
                New Quote
              </Link>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Quote ID</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Destination</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Dates</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {quotes.map((quote) => (
                  <tr key={quote.quote_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <Link to={`/quotes/${quote.quote_id}`} className="text-purple-600 hover:text-purple-700 font-mono">
                        {quote.quote_id?.slice(0, 8)}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-gray-900">{quote.destination}</td>
                    <td className="px-6 py-4 text-gray-600 text-sm">
                      {formatDate(quote.check_in)} - {formatDate(quote.check_out)}
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900">{formatCurrency(quote.total_price)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${stageColors[quote.status?.toUpperCase()] || 'bg-gray-100 text-gray-700'}`}>
                        {quote.status || 'draft'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'activities' && (
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Activity Timeline</h3>
            <button
              onClick={() => setShowNoteModal(true)}
              className="btn-secondary text-sm flex items-center gap-1"
            >
              <PlusIcon className="w-4 h-4" />
              Log Activity
            </button>
          </div>
          
          {activities.length === 0 ? (
            <p className="text-gray-400 text-center py-8">No activities recorded yet</p>
          ) : (
            <div className="space-y-4">
              {activities.map((activity, idx) => {
                const Icon = activityIcons[activity.type] || ChatBubbleLeftIcon;
                return (
                  <div key={idx} className="flex gap-4">
                    <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-purple-600" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 capitalize">{activity.type}</p>
                      <p className="text-gray-600">{activity.description}</p>
                      <p className="text-sm text-gray-400 mt-1">{formatDateTime(activity.created_at)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Add Note Modal */}
      {showNoteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Note</h3>
            <textarea
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              className="input min-h-32"
              placeholder="Enter your note..."
            />
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowNoteModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button onClick={handleAddNote} className="btn-primary">
                Save Note
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
