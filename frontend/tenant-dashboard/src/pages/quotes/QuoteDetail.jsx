import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { quotesApi, crmApi, invoicesApi } from '../../services/api';
import { pdfUrl } from '../../config/environment';
import { normalizeQuoteStatus } from '../../utils/fieldTransformers';
import {
  ArrowLeftIcon,
  EnvelopeIcon,
  DocumentDuplicateIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  UserIcon,
  MapPinIcon,
  CalendarIcon,
  BuildingOfficeIcon,
  CurrencyDollarIcon,
  UserPlusIcon,
  DocumentTextIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
  ArrowDownTrayIcon,
  EyeIcon,
  PaperAirplaneIcon,
  TicketIcon,
  TruckIcon,
} from '@heroicons/react/24/outline';

const statusConfig = {
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-700', icon: ClockIcon },
  quoted: { label: 'Quoted', color: 'bg-blue-100 text-blue-700', icon: ClockIcon },
  generated: { label: 'Quoted', color: 'bg-blue-100 text-blue-700', icon: ClockIcon },
  sent: { label: 'Sent', color: 'bg-blue-100 text-blue-700', icon: EnvelopeIcon },
  viewed: { label: 'Viewed', color: 'bg-purple-100 text-purple-700', icon: CheckCircleIcon },
  accepted: { label: 'Accepted', color: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
  declined: { label: 'Declined', color: 'bg-red-100 text-red-700', icon: XCircleIcon },
  rejected: { label: 'Declined', color: 'bg-red-100 text-red-700', icon: XCircleIcon },
  expired: { label: 'Expired', color: 'bg-orange-100 text-orange-700', icon: ClockIcon },
  converted: { label: 'Converted', color: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
};

// Service type config for invoice modal
const serviceTypeConfig = {
  hotel: { title: 'Hotel Options', icon: BuildingOfficeIcon },
  activity: { title: 'Activities', icon: TicketIcon },
  transfer: { title: 'Transfers', icon: TruckIcon },
  flight: { title: 'Flights', icon: PaperAirplaneIcon },
};

// Convert to Invoice Modal
function ConvertToInvoiceModal({ isOpen, onClose, quote, onSuccess }) {
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [dueDate, setDueDate] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const allItems = quote?.hotels || [];

  // Group items by type, matching the detail view pattern
  const serviceGroups = [
    { type: 'hotel', ...serviceTypeConfig.hotel, items: allItems.filter(h => !h.type || h.type === 'hotel') },
    { type: 'activity', ...serviceTypeConfig.activity, items: allItems.filter(h => h.type === 'activity') },
    { type: 'transfer', ...serviceTypeConfig.transfer, items: allItems.filter(h => h.type === 'transfer') },
    { type: 'flight', ...serviceTypeConfig.flight, items: allItems.filter(h => h.type === 'flight') },
  ].filter(g => g.items.length > 0);

  useEffect(() => {
    if (allItems.length > 0 && selectedItems.size === 0) {
      setSelectedItems(new Set([0]));
    }
    const due = new Date();
    due.setDate(due.getDate() + 14);
    setDueDate(due.toISOString().split('T')[0]);
  }, [allItems.length]);

  const toggleItem = (globalIdx) => {
    setSelectedItems(prev => {
      const next = new Set(prev);
      if (next.has(globalIdx)) next.delete(globalIdx);
      else next.add(globalIdx);
      return next;
    });
  };

  const handleConvert = async () => {
    if (selectedItems.size === 0) return;

    setLoading(true);
    setError(null);

    try {
      const items = [...selectedItems].map(idx => {
        const item = allItems[idx];
        const type = item.type || 'hotel';
        const typeLabel = serviceTypeConfig[type]?.title?.replace(/s$/, '') || 'Service';
        const name = item.name || item.hotel_name;
        return {
          description: `[${typeLabel}] ${name}${quote.nights ? ` - ${quote.nights} nights` : ''} (${quote.destination})`,
          hotel_name: name,
          room_type: item.room_type,
          meal_plan: item.meal_plan,
          amount: item.total_price,
        };
      });

      const response = await invoicesApi.create({
        quote_id: quote.quote_id,
        items,
        due_days: Math.ceil((new Date(dueDate) - new Date()) / (1000 * 60 * 60 * 24)),
        notes: notes,
      });

      if (response.data?.success) {
        onSuccess(response.data.data);
        onClose();
      } else {
        setError(response.data?.error || 'Failed to create invoice');
      }
    } catch (err) {
      console.error('Invoice creation error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to create invoice');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-theme-surface rounded-xl w-full max-w-lg mx-4 overflow-hidden shadow-xl border border-theme">
        <div className="flex items-center justify-between px-6 py-4 border-b border-theme">
          <h3 className="text-lg font-semibold text-theme">Convert to Invoice</h3>
          <button onClick={onClose} className="p-1 hover:bg-theme-surface-elevated rounded-lg transition-colors">
            <XMarkIcon className="w-5 h-5 text-theme-muted" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-start gap-2">
              <ExclamationTriangleIcon className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-theme-secondary mb-2">
              Select Services <span className="text-red-500">*</span>
            </label>
            <div className="space-y-3">
              {serviceGroups.map(group => {
                const GroupIcon = group.icon;
                return (
                  <div key={group.type}>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <GroupIcon className="w-4 h-4 text-theme-primary" />
                      <span className="text-xs font-semibold text-theme-secondary uppercase tracking-wide">{group.title}</span>
                    </div>
                    <div className="space-y-2">
                      {group.items.map(item => {
                        const globalIdx = allItems.indexOf(item);
                        return (
                          <label
                            key={globalIdx}
                            className={`flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-all ${
                              selectedItems.has(globalIdx)
                                ? 'border-theme-primary bg-theme-primary/10 ring-1 ring-theme-primary'
                                : 'border-theme hover:border-theme-primary/50 bg-theme-surface'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                checked={selectedItems.has(globalIdx)}
                                onChange={() => toggleItem(globalIdx)}
                                className="w-4 h-4 accent-[var(--color-primary)]"
                              />
                              <div>
                                <p className="font-medium text-theme">{item.name || item.hotel_name}</p>
                                <p className="text-sm text-theme-muted">
                                  {[item.room_type, item.meal_plan].filter(Boolean).join(' • ') || group.type}
                                </p>
                              </div>
                            </div>
                            <span className="font-semibold text-theme-primary">
                              R {(item.total_price || 0).toLocaleString()}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-theme-secondary mb-1">
              Due Date
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-theme-secondary mb-1">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input min-h-20"
              placeholder="Any additional notes for this invoice..."
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-theme bg-theme-surface-elevated">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={handleConvert}
            disabled={selectedItems.size === 0 || loading}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Creating...
              </>
            ) : (
              <>
                <DocumentTextIcon className="w-4 h-4" />
                Create Invoice
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function QuoteDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [toast, setToast] = useState(null);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);

  useEffect(() => {
    loadQuote();
  }, [id]);

  const loadQuote = async () => {
    try {
      setLoading(true);
      const response = await quotesApi.get(id);
      if (response.data?.success && response.data?.data) {
        setQuote(response.data.data);
      } else {
        showToast('Quote not found', 'error');
      }
    } catch (error) {
      console.error('Failed to load quote:', error);
      showToast('Failed to load quote', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleResendEmail = async () => {
    setActionLoading('resend');
    try {
      const response = await quotesApi.resend(id);
      
      if (response.data?.success && response.data?.email_sent) {
        showToast('Quote email sent successfully!', 'success');
        loadQuote(); // Refresh to get updated status
      } else if (response.data?.success && !response.data?.email_sent) {
        showToast('Quote regenerated but email failed to send. Check SendGrid configuration.', 'warning');
      } else {
        showToast(response.data?.error || 'Failed to send email', 'error');
      }
    } catch (error) {
      console.error('Resend failed:', error);
      showToast(error.response?.data?.detail || 'Failed to resend quote', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSendDraft = async () => {
    setActionLoading('send');
    try {
      const response = await quotesApi.sendDraft(id);
      if (response.data?.success) {
        showToast('Quote sent to client!', 'success');
        loadQuote(); // Refresh to show updated status
      } else {
        showToast(response.data?.error || 'Failed to send quote', 'error');
      }
    } catch (error) {
      console.error('Send draft failed:', error);
      showToast(error.response?.data?.detail || 'Failed to send quote', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleAddToCRM = async () => {
    if (!quote) return;
    
    setActionLoading('crm');
    try {
      const response = await crmApi.createClient({
        email: quote.customer_email,
        name: quote.customer_name,
        phone: quote.customer_phone,
        source: 'quote',
      });

      if (response.data?.success) {
        const clientData = response.data.data;
        if (clientData.created) {
          showToast('Client added to CRM in Quoted stage', 'success');
        } else {
          showToast('Client already exists in CRM', 'info');
        }
      } else {
        showToast('Failed to add to CRM', 'error');
      }
    } catch (error) {
      console.error('Add to CRM failed:', error);
      showToast(error.response?.data?.detail || 'Failed to add to CRM', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleInvoiceCreated = (invoice) => {
    showToast(`Invoice ${invoice.invoice_id} created successfully!`, 'success');
    navigate(`/invoices/${invoice.invoice_id}`);
  };

  const handleDuplicate = () => {
    // Navigate to generate quote with prefilled data
    navigate('/quotes/new', { 
      state: { 
        prefill: {
          name: quote.customer_name,
          email: quote.customer_email,
          phone: quote.customer_phone,
          destination: quote.destination,
          adults: quote.adults,
          children: quote.children,
        }
      }
    });
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
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!quote) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">Quote not found</h2>
        <button onClick={() => navigate('/quotes')} className="btn-primary mt-4">
          Back to Quotes
        </button>
      </div>
    );
  }

  const status = statusConfig[normalizeQuoteStatus(quote.status)] || statusConfig.draft;
  const StatusIcon = status.icon;
  const hotels = quote.hotels || [];

  return (
    <div className="space-y-6 print-content">
      {/* Header - Hidden when printing */}
      <div className="flex items-start justify-between no-print">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/quotes')}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeftIcon className="w-5 h-5 text-gray-500" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Quote Details</h1>
            <p className="text-gray-500 font-mono">{quote.quote_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {normalizeQuoteStatus(quote.status) === 'draft' ? (
            <button
              onClick={handleSendDraft}
              disabled={actionLoading === 'send'}
              className="btn-primary flex items-center gap-2"
            >
              {actionLoading === 'send' ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <PaperAirplaneIcon className="w-5 h-5" />
              )}
              Send to Client
            </button>
          ) : (
            <button
              onClick={handleResendEmail}
              disabled={actionLoading === 'resend'}
              className="btn-secondary flex items-center gap-2"
            >
              {actionLoading === 'resend' ? (
                <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <EnvelopeIcon className="w-5 h-5" />
              )}
              Resend Email
            </button>
          )}
          <button onClick={handleDuplicate} className="btn-secondary flex items-center gap-2">
            <DocumentDuplicateIcon className="w-5 h-5" />
            Duplicate
          </button>
        </div>
      </div>

      {/* Print Header - Only visible when printing */}
      <div className="print-only">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Travel Quote</h1>
        <p className="text-gray-600 font-mono">{quote.quote_id}</p>
      </div>

      {/* Email Status Warning - Hidden when printing */}
      {quote.status === 'generated' && !quote.email_sent && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3 no-print">
          <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-yellow-800">Email Not Sent</p>
            <p className="text-sm text-yellow-700">
              This quote was generated but the email was not sent. Check your SendGrid configuration or resend manually.
            </p>
          </div>
        </div>
      )}

      {/* Status Banner - Hidden when printing */}
      <div className={`${status.color} rounded-lg p-4 flex items-center gap-3 no-print`}>
        <StatusIcon className="w-5 h-5" />
        <span className="font-medium">Status: {status.label}</span>
        {quote.email_sent && (
          <span className="text-sm ml-2">(Email sent successfully)</span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Customer Info */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <UserIcon className="w-5 h-5 text-purple-600" />
              Customer Information
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Name</p>
                <p className="font-medium text-gray-900">{quote.customer_name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Email</p>
                <p className="font-medium text-gray-900">{quote.customer_email}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Phone</p>
                <p className="font-medium text-gray-900">{quote.customer_phone || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Source</p>
                <p className="font-medium text-gray-900 capitalize">{quote.source || 'Manual'}</p>
              </div>
            </div>
          </div>

          {/* Trip Details */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <MapPinIcon className="w-5 h-5 text-purple-600" />
              Trip Details
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-500">Destination</p>
                <p className="font-medium text-gray-900">{quote.destination}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Check-in</p>
                <p className="font-medium text-gray-900">{formatDate(quote.check_in)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Check-out</p>
                <p className="font-medium text-gray-900">{formatDate(quote.check_out)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Nights</p>
                <p className="font-medium text-gray-900">{quote.nights}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Adults</p>
                <p className="font-medium text-gray-900">{quote.adults}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Children</p>
                <p className="font-medium text-gray-900">{quote.children || 0}</p>
              </div>
            </div>
          </div>

          {/* Service Options — grouped by type */}
          {(() => {
            const serviceGroups = [
              { items: hotels.filter(h => !h.type || h.type === 'hotel'), title: 'Hotel Options', icon: BuildingOfficeIcon },
              { items: hotels.filter(h => h.type === 'activity'), title: 'Activities', icon: TicketIcon },
              { items: hotels.filter(h => h.type === 'transfer'), title: 'Transfers', icon: TruckIcon },
              { items: hotels.filter(h => h.type === 'flight'), title: 'Flights', icon: PaperAirplaneIcon },
            ].filter(g => g.items.length > 0);

            return serviceGroups.length > 0 ? serviceGroups.map(group => (
              <div key={group.title} className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <group.icon className="w-5 h-5 text-purple-600" />
                  {group.title}
                </h3>
                <div className="space-y-4">
                  {group.items.map((hotel, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-purple-300 transition-colors"
                    >
                      <div>
                        <p className="font-semibold text-gray-900">{hotel.name || hotel.hotel_name}</p>
                        <p className="text-sm text-gray-500">
                          {hotel.room_type}{hotel.meal_plan ? ` • ${hotel.meal_plan}` : ''}
                        </p>
                        {hotel.nights && (
                          <p className="text-sm text-gray-400">{hotel.nights} nights</p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold text-purple-600">
                          R {(hotel.total_price || 0).toLocaleString()}
                        </p>
                        <p className="text-sm text-gray-500">Total</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )) : (
              <div className="card">
                <p className="text-gray-500 text-center py-4">No options available</p>
              </div>
            );
          })()}

          {/* Quote Preview */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <EyeIcon className="w-5 h-5 text-purple-600" />
              Quote Preview
            </h3>
            <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
              <iframe
                src={`${pdfUrl('quotes', quote.quote_id)}`}
                className="w-full h-[600px]"
                title="Quote Preview"
              />
            </div>
            <div className="mt-3 flex justify-center gap-3">
              <a
                href={`${pdfUrl('quotes', quote.quote_id)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-sm inline-flex items-center gap-1"
              >
                <ArrowDownTrayIcon className="w-4 h-4" />
                Open in New Tab
              </a>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Pricing Summary */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <CurrencyDollarIcon className="w-5 h-5 text-purple-600" />
              Pricing Summary
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Total</span>
                <span className="text-2xl font-bold text-purple-600">
                  R {(quote.total_price || hotels[0]?.total_price || 0).toLocaleString()}
                </span>
              </div>
              {hotels[0]?.price_per_person && (
                <p className="text-sm text-gray-500 text-right">
                  R {hotels[0].price_per_person.toLocaleString()} per person
                </p>
              )}
            </div>
          </div>

          {/* Timeline - Hidden when printing */}
          <div className="card no-print">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <ClockIcon className="w-5 h-5 text-purple-600" />
              Timeline
            </h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 bg-purple-600 rounded-full mt-2"></div>
                <div>
                  <p className="font-medium text-gray-900">Created</p>
                  <p className="text-sm text-gray-500">{formatDateTime(quote.created_at)}</p>
                </div>
              </div>
              {(quote.email_sent_at || quote.sent_at) && (
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">Sent</p>
                    <p className="text-sm text-gray-500">{formatDateTime(quote.email_sent_at || quote.sent_at)}</p>
                  </div>
                </div>
              )}
              {quote.viewed_at && (
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-purple-600 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">Viewed</p>
                    <p className="text-sm text-gray-500">{formatDateTime(quote.viewed_at)}</p>
                  </div>
                </div>
              )}
              {quote.accepted_at && (
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-green-600 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">Accepted</p>
                    <p className="text-sm text-gray-500">{formatDateTime(quote.accepted_at)}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Actions - Hidden when printing */}
          <div className="card no-print">
            <h3 className="font-semibold text-gray-900 mb-4">Actions</h3>
            <div className="space-y-3">
              <button
                onClick={() => setShowInvoiceModal(true)}
                className="w-full btn-primary flex items-center justify-center gap-2"
              >
                <DocumentTextIcon className="w-5 h-5" />
                Convert to Invoice
              </button>
              <button
                onClick={handleAddToCRM}
                disabled={actionLoading === 'crm'}
                className="w-full btn-secondary flex items-center justify-center gap-2"
              >
                {actionLoading === 'crm' ? (
                  <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <UserPlusIcon className="w-5 h-5" />
                )}
                Add to CRM
              </button>
              <button className="w-full btn-secondary text-red-600 hover:bg-red-50">
                Delete Quote
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Convert to Invoice Modal */}
      <ConvertToInvoiceModal
        isOpen={showInvoiceModal}
        onClose={() => setShowInvoiceModal(false)}
        quote={quote}
        onSuccess={handleInvoiceCreated}
      />

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 max-w-md ${
          toast.type === 'success' ? 'bg-green-600 text-white' :
          toast.type === 'warning' ? 'bg-yellow-500 text-white' :
          toast.type === 'info' ? 'bg-blue-600 text-white' :
          'bg-red-600 text-white'
        }`}>
          {toast.type === 'success' ? <CheckCircleIcon className="w-5 h-5" /> :
           toast.type === 'warning' ? <ExclamationTriangleIcon className="w-5 h-5" /> :
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
