import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { quotesApi, pricingApi } from '../../services/api';
import { SkeletonTable } from '../../components/ui/Skeleton';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  EyeIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

const statusConfig = {
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-700' },
  generated: { label: 'Generated', color: 'bg-blue-100 text-blue-700' },
  sent: { label: 'Sent', color: 'bg-blue-100 text-blue-700' },
  viewed: { label: 'Viewed', color: 'bg-purple-100 text-purple-700' },
  accepted: { label: 'Accepted', color: 'bg-green-100 text-green-700' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700' },
  expired: { label: 'Expired', color: 'bg-orange-100 text-orange-700' },
};

export default function QuotesList() {
  const navigate = useNavigate();
  const [quotes, setQuotes] = useState([]);
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [destinationFilter, setDestinationFilter] = useState('');
  const [toast, setToast] = useState(null);

  useEffect(() => {
    loadData();
  }, [statusFilter, destinationFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [quotesRes, destRes] = await Promise.all([
        quotesApi.list({ status: statusFilter || undefined, limit: 50 }),
        pricingApi.listDestinations().catch(() => ({ data: [] })),
      ]);

      setQuotes(quotesRes.data?.data || []);
      setDestinations(destRes.data?.data || destRes.data || []);
    } catch (error) {
      console.error('Failed to load quotes:', error);
      showToast('Failed to load quotes', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleResendEmail = async (e, quoteId) => {
    e.stopPropagation();
    try {
      const response = await quotesApi.resend(quoteId);
      if (response.data?.success && response.data?.email_sent) {
        showToast('Quote email sent successfully!', 'success');
        loadData();
      } else if (response.data?.success && !response.data?.email_sent) {
        showToast('Quote regenerated but email failed to send', 'warning');
      } else {
        showToast(response.data?.error || 'Failed to send email', 'error');
      }
    } catch (error) {
      console.error('Resend failed:', error);
      showToast('Failed to resend quote', 'error');
    }
  };

  const filteredQuotes = quotes.filter((quote) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      quote.customer_name?.toLowerCase().includes(searchLower) ||
      quote.customer_email?.toLowerCase().includes(searchLower) ||
      quote.destination?.toLowerCase().includes(searchLower) ||
      quote.quote_id?.toLowerCase().includes(searchLower)
    );
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-ZA', {
        day: '2-digit',
        month: 'short',
      });
    } catch {
      return '-';
    }
  };

  const formatDateRange = (checkIn, checkOut) => {
    if (!checkIn && !checkOut) return '-';
    const start = formatDate(checkIn);
    const end = formatDate(checkOut);
    if (start === '-' && end === '-') return '-';
    return `${start} - ${end}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quotes</h1>
          <p className="text-gray-500 mt-1">Manage and track your travel quotes</p>
        </div>
        <Link to="/quotes/new" className="btn-primary flex items-center gap-2">
          <PlusIcon className="w-5 h-5" />
          Generate Quote
        </Link>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name, email, destination..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input w-40"
          >
            <option value="">All Status</option>
            {Object.entries(statusConfig).map(([key, config]) => (
              <option key={key} value={key}>{config.label}</option>
            ))}
          </select>
          <select
            value={destinationFilter}
            onChange={(e) => setDestinationFilter(e.target.value)}
            className="input w-40"
          >
            <option value="">All Destinations</option>
            {destinations.map((dest, idx) => (
              <option key={idx} value={dest.destination || dest}>
                {dest.destination || dest}
              </option>
            ))}
          </select>
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Quotes Table */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <SkeletonTable rows={5} columns={7} />
        ) : filteredQuotes.length === 0 ? (
          <div className="text-center py-12">
            <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No quotes found</h3>
            <p className="text-gray-500 mt-1">Get started by generating a new quote</p>
            <Link to="/quotes/new" className="btn-primary inline-flex items-center gap-2 mt-4">
              <PlusIcon className="w-5 h-5" />
              Generate Quote
            </Link>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Customer</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Destination</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Dates</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Travelers</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Total</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredQuotes.map((quote) => {
                const status = statusConfig[quote.status] || statusConfig.draft;
                return (
                  <tr
                    key={quote.quote_id}
                    onClick={() => navigate(`/quotes/${quote.quote_id}`)}
                    onMouseEnter={() => quotesApi.prefetch(quote.quote_id)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-gray-900">{quote.customer_name}</p>
                        <p className="text-sm text-gray-500">{quote.customer_email}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-900">{quote.destination}</td>
                    <td className="px-6 py-4 text-gray-600 text-sm">
                      {formatDateRange(quote.check_in_date, quote.check_out_date)}
                      {quote.nights && <span className="text-gray-400 ml-1">({quote.nights}n)</span>}
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {quote.adults} adult{quote.adults !== 1 ? 's' : ''}
                      {quote.children > 0 && `, ${quote.children} child${quote.children !== 1 ? 'ren' : ''}`}
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900">
                      R {(quote.total_price || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.color}`}>
                        {status.label}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/quotes/${quote.quote_id}`);
                          }}
                          className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                          title="View Quote"
                        >
                          <EyeIcon className="w-5 h-5" />
                        </button>
                        <button
                          onClick={(e) => handleResendEmail(e, quote.quote_id)}
                          className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                          title="Resend Email"
                        >
                          <EnvelopeIcon className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Count */}
      {!loading && filteredQuotes.length > 0 && (
        <p className="text-sm text-gray-500 text-center">
          Showing {filteredQuotes.length} quote{filteredQuotes.length !== 1 ? 's' : ''}
        </p>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 max-w-md ${
          toast.type === 'success' ? 'bg-green-600 text-white' :
          toast.type === 'warning' ? 'bg-yellow-500 text-white' :
          'bg-red-600 text-white'
        }`}>
          {toast.type === 'success' ? <CheckCircleIcon className="w-5 h-5" /> :
           toast.type === 'warning' ? <ClockIcon className="w-5 h-5" /> :
           <XCircleIcon className="w-5 h-5" />}
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2">
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
