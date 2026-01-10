import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { invoicesApi } from '../../services/api';
import {
  ArrowLeftIcon,
  EnvelopeIcon,
  ArrowDownTrayIcon,
  PrinterIcon,
  PencilIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  XCircleIcon,
  UserIcon,
  MapPinIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  XMarkIcon,
  BanknotesIcon,
  IdentificationIcon,
} from '@heroicons/react/24/outline';

const statusConfig = {
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-700', icon: ClockIcon },
  sent: { label: 'Sent', color: 'bg-blue-100 text-blue-700', icon: EnvelopeIcon },
  viewed: { label: 'Viewed', color: 'bg-purple-100 text-purple-700', icon: CheckCircleIcon },
  paid: { label: 'Paid', color: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
  partial: { label: 'Partial Payment', color: 'bg-yellow-100 text-yellow-700', icon: ClockIcon },
  overdue: { label: 'Overdue', color: 'bg-red-100 text-red-700', icon: ExclamationCircleIcon },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-500', icon: XCircleIcon },
};

// Record Payment Modal
function RecordPaymentModal({ isOpen, onClose, invoice, onSuccess }) {
  const [amount, setAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0]);
  const [paymentMethod, setPaymentMethod] = useState('bank_transfer');
  const [reference, setReference] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await invoicesApi.recordPayment(invoice.invoice_id, {
        amount: parseFloat(amount),
        payment_date: paymentDate,
        payment_method: paymentMethod,
        reference: reference,
      });
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Payment recording failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const outstanding = (invoice.total_amount || 0) - (invoice.paid_amount || 0);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-md mx-4 overflow-hidden shadow-xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Record Payment</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div className="bg-gray-50 p-3 rounded-lg">
            <p className="text-sm text-gray-500">Outstanding Balance</p>
            <p className="text-xl font-bold text-gray-900">R {outstanding.toLocaleString()}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Amount *</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="input"
              placeholder="0.00"
              max={outstanding}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Date</label>
            <input
              type="date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Method</label>
            <select
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className="input"
            >
              <option value="bank_transfer">Bank Transfer / EFT</option>
              <option value="credit_card">Credit Card</option>
              <option value="cash">Cash</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
            <input
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              className="input"
              placeholder="Transaction reference..."
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={!amount || loading}
            className="btn-primary"
          >
            {loading ? 'Recording...' : 'Record Payment'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [toast, setToast] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  useEffect(() => {
    loadInvoice();
  }, [id]);

  const loadInvoice = async () => {
    try {
      setLoading(true);
      const response = await invoicesApi.get(id);
      if (response.data?.success && response.data?.data) {
        setInvoice(response.data.data);
      } else if (response.data) {
        setInvoice(response.data);
      } else {
        showToast('Invoice not found', 'error');
      }
    } catch (error) {
      console.error('Failed to load invoice:', error);
      showToast('Failed to load invoice', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleSendEmail = async () => {
    setActionLoading('email');
    try {
      const response = await invoicesApi.send(id);
      if (response.data?.success) {
        showToast('Invoice sent to customer!', 'success');
        loadInvoice();
      } else {
        showToast(response.data?.error || 'Failed to send invoice', 'error');
      }
    } catch (error) {
      showToast('Failed to send invoice', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDownload = async () => {
    setActionLoading('download');
    try {
      const response = await invoicesApi.download(id);
      // Create blob and download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${invoice?.invoice_id || 'invoice'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast('Invoice downloaded!', 'success');
    } catch (error) {
      console.error('Download failed:', error);
      showToast('Download not available yet', 'warning');
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkAsPaid = async () => {
    setActionLoading('paid');
    try {
      await invoicesApi.updateStatus(id, 'paid');
      showToast('Invoice marked as paid!', 'success');
      loadInvoice();
    } catch (error) {
      showToast('Failed to update status', 'error');
    } finally {
      setActionLoading(null);
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

  if (!invoice) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">Invoice not found</h2>
        <button onClick={() => navigate('/invoices')} className="btn-primary mt-4">
          Back to Invoices
        </button>
      </div>
    );
  }

  const status = statusConfig[invoice.status] || statusConfig.draft;
  const StatusIcon = status.icon;
  const totalAmount = invoice.total_amount || invoice.total || 0;
  const paidAmount = invoice.paid_amount || 0;
  const outstanding = totalAmount - paidAmount;
  const items = invoice.items || [];
  const travelers = invoice.travelers || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/invoices')}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeftIcon className="w-5 h-5 text-gray-500" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Invoice Details</h1>
            <p className="text-gray-500 font-mono">{invoice.invoice_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleDownload}
            disabled={actionLoading === 'download'}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowDownTrayIcon className="w-5 h-5" />
            Download PDF
          </button>
          <button
            onClick={handleSendEmail}
            disabled={actionLoading === 'email'}
            className="btn-secondary flex items-center gap-2"
          >
            {actionLoading === 'email' ? (
              <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <EnvelopeIcon className="w-5 h-5" />
            )}
            Send Email
          </button>
          <button onClick={() => window.print()} className="btn-secondary flex items-center gap-2">
            <PrinterIcon className="w-5 h-5" />
            Print
          </button>
        </div>
      </div>

      {/* Status Banner */}
      <div className={`${status.color} rounded-lg p-4 flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <StatusIcon className="w-5 h-5" />
          <span className="font-medium">Status: {status.label}</span>
        </div>
        {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
          <button
            onClick={() => setShowPaymentModal(true)}
            className="bg-white/50 hover:bg-white/70 px-3 py-1 rounded-lg text-sm font-medium"
          >
            Record Payment
          </button>
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
                <p className="font-medium text-gray-900">{invoice.customer_name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Email</p>
                <p className="font-medium text-gray-900">{invoice.customer_email}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Phone</p>
                <p className="font-medium text-gray-900">{invoice.customer_phone || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Quote Reference</p>
                <p className="font-medium text-purple-600">{invoice.quote_id || '-'}</p>
              </div>
            </div>
          </div>

          {/* Trip Details */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <MapPinIcon className="w-5 h-5 text-purple-600" />
              Trip Details
            </h3>
            {items.length > 0 ? (
              <div className="space-y-4">
                {items.map((item, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="font-semibold text-gray-900">{item.hotel_name || item.description}</p>
                        <p className="text-sm text-gray-500">{item.room_type} • {item.meal_plan}</p>
                      </div>
                      <p className="font-bold text-purple-600">R {(item.amount || 0).toLocaleString()}</p>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div>
                        <p className="text-gray-500">Destination</p>
                        <p className="font-medium">{item.destination || invoice.destination || '-'}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Check-in</p>
                        <p className="font-medium">{formatDate(item.check_in)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Check-out</p>
                        <p className="font-medium">{formatDate(item.check_out)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Nights</p>
                        <p className="font-medium">{item.nights || '-'}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No items</p>
            )}
          </div>

          {/* Travelers */}
          {travelers.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <IdentificationIcon className="w-5 h-5 text-purple-600" />
                Travelers ({travelers.length})
              </h3>
              <div className="space-y-3">
                {travelers.map((traveler, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium text-gray-900">
                        {traveler.is_lead && '👤 '}
                        {traveler.first_name} {traveler.last_name}
                      </p>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        traveler.type === 'child' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                      }`}>
                        {traveler.type === 'child' ? 'Child' : 'Adult'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                      <div>
                        <p className="text-gray-500">DOB</p>
                        <p>{formatDate(traveler.date_of_birth)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Passport</p>
                        <p>{traveler.passport_number || '-'}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Expiry</p>
                        <p>{formatDate(traveler.passport_expiry)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Nationality</p>
                        <p>{traveler.nationality || '-'}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notes */}
          {invoice.notes && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Notes</h3>
              <p className="text-gray-600 whitespace-pre-wrap">{invoice.notes}</p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Payment Summary */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <CurrencyDollarIcon className="w-5 h-5 text-purple-600" />
              Payment Summary
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Total Amount</span>
                <span className="font-bold text-gray-900">R {totalAmount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Paid</span>
                <span className="font-medium text-green-600">R {paidAmount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between border-t border-gray-200 pt-3">
                <span className="font-medium text-gray-900">Outstanding</span>
                <span className={`font-bold ${outstanding > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  R {outstanding.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Timeline */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <ClockIcon className="w-5 h-5 text-purple-600" />
              Timeline
            </h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 bg-purple-600 rounded-full mt-2"></div>
                <div>
                  <p className="font-medium text-gray-900">Created</p>
                  <p className="text-sm text-gray-500">{formatDateTime(invoice.created_at)}</p>
                </div>
              </div>
              {invoice.sent_at && (
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">Sent</p>
                    <p className="text-sm text-gray-500">{formatDateTime(invoice.sent_at)}</p>
                  </div>
                </div>
              )}
              <div className="flex items-start gap-3">
                <div className={`w-2 h-2 rounded-full mt-2 ${outstanding <= 0 ? 'bg-red-500' : 'bg-gray-300'}`}></div>
                <div>
                  <p className="font-medium text-gray-900">Due Date</p>
                  <p className="text-sm text-gray-500">{formatDate(invoice.due_date)}</p>
                </div>
              </div>
              {invoice.paid_at && (
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-green-600 rounded-full mt-2"></div>
                  <div>
                    <p className="font-medium text-gray-900">Paid</p>
                    <p className="text-sm text-gray-500">{formatDateTime(invoice.paid_at)}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Actions</h3>
            <div className="space-y-3">
              {invoice.status !== 'paid' && (
                <button
                  onClick={handleMarkAsPaid}
                  disabled={actionLoading === 'paid'}
                  className="w-full btn-primary flex items-center justify-center gap-2"
                >
                  <BanknotesIcon className="w-5 h-5" />
                  Mark as Paid
                </button>
              )}
              <button
                onClick={() => setShowPaymentModal(true)}
                className="w-full btn-secondary flex items-center justify-center gap-2"
              >
                <CurrencyDollarIcon className="w-5 h-5" />
                Record Payment
              </button>
              <button className="w-full btn-secondary flex items-center justify-center gap-2 text-red-600 hover:bg-red-50">
                Cancel Invoice
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Payment Modal */}
      <RecordPaymentModal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        invoice={invoice}
        onSuccess={() => {
          showToast('Payment recorded!', 'success');
          loadInvoice();
        }}
      />

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 max-w-md ${
          toast.type === 'success' ? 'bg-green-600 text-white' :
          toast.type === 'warning' ? 'bg-yellow-500 text-white' :
          'bg-red-600 text-white'
        }`}>
          <CheckCircleIcon className="w-5 h-5" />
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2">
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
