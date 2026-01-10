import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { invoicesApi, quotesApi } from '../../services/api';
import { SkeletonTable } from '../../components/ui/Skeleton';
import {
  DocumentTextIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  ArrowDownTrayIcon,
  EnvelopeIcon,
  XMarkIcon,
  UserIcon,
  EyeIcon,
  LinkIcon,
  PrinterIcon,
} from '@heroicons/react/24/outline';

// Invoice Success Modal
function InvoiceSuccessModal({ invoice, isOpen, onClose, onSendEmail, onDownloadPdf, onViewInvoice }) {
  const [sending, setSending] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!isOpen || !invoice) return null;

  const handleCopyLink = async () => {
    // Use public PDF endpoint for direct, shareable PDF link
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8080';
    const clientId = localStorage.getItem('clientId') || 'africastay';
    const link = `${apiBase}/api/v1/public/invoices/${invoice.invoice_id}/pdf`;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleSendEmail = async () => {
    setSending(true);
    try {
      await onSendEmail(invoice.invoice_id);
    } finally {
      setSending(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await onDownloadPdf(invoice.invoice_id);
    } finally {
      setDownloading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount) return 'R 0';
    return `R ${Number(amount).toLocaleString()}`;
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full">
        {/* Success Header */}
        <div className="bg-gradient-to-r from-green-500 to-emerald-500 p-6 rounded-t-xl text-white text-center">
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircleIcon className="w-10 h-10" />
          </div>
          <h2 className="text-2xl font-bold">Invoice Created!</h2>
          <p className="text-green-100 mt-1">Invoice #{invoice.invoice_id}</p>
        </div>

        {/* Invoice Summary */}
        <div className="p-6">
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Customer</p>
                <p className="font-medium text-gray-900">{invoice.customer_name}</p>
              </div>
              <div>
                <p className="text-gray-500">Amount</p>
                <p className="font-bold text-lg text-gray-900">{formatCurrency(invoice.total_amount)}</p>
              </div>
              <div>
                <p className="text-gray-500">Email</p>
                <p className="font-medium text-gray-900 truncate">{invoice.customer_email}</p>
              </div>
              <div>
                <p className="text-gray-500">Due Date</p>
                <p className="font-medium text-gray-900">
                  {invoice.due_date ? new Date(invoice.due_date).toLocaleDateString() : '-'}
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={handleSendEmail}
                disabled={sending}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                <EnvelopeIcon className="w-5 h-5" />
                {sending ? 'Sending...' : 'Send to Client'}
              </button>
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                <ArrowDownTrayIcon className="w-5 h-5" />
                {downloading ? 'Downloading...' : 'Download PDF'}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => onViewInvoice(invoice.invoice_id)}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <EyeIcon className="w-5 h-5" />
                View Invoice
              </button>
              <button
                onClick={handleCopyLink}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <LinkIcon className="w-5 h-5" />
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="w-full mt-4 px-4 py-2 text-gray-500 hover:text-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

const statusConfig = {
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-700', icon: ClockIcon },
  sent: { label: 'Sent', color: 'bg-blue-100 text-blue-700', icon: EnvelopeIcon },
  viewed: { label: 'Viewed', color: 'bg-purple-100 text-purple-700', icon: CheckCircleIcon },
  paid: { label: 'Paid', color: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
  partial: { label: 'Partial', color: 'bg-yellow-100 text-yellow-700', icon: ClockIcon },
  overdue: { label: 'Overdue', color: 'bg-red-100 text-red-700', icon: ExclamationCircleIcon },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-500', icon: ExclamationCircleIcon },
};

// Traveler Form Component
function TravelerForm({ index, traveler, onChange, onRemove, isLead }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900">
          {isLead ? '👤 Lead Traveler' : `Traveler ${index + 1}`}
        </h4>
        {!isLead && (
          <button type="button" onClick={onRemove} className="text-red-500 hover:text-red-700 text-sm">
            Remove
          </button>
        )}
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">First Name *</label>
          <input
            type="text"
            value={traveler.first_name || ''}
            onChange={(e) => onChange({ ...traveler, first_name: e.target.value })}
            className="input text-sm"
            placeholder="John"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Last Name *</label>
          <input
            type="text"
            value={traveler.last_name || ''}
            onChange={(e) => onChange({ ...traveler, last_name: e.target.value })}
            className="input text-sm"
            placeholder="Smith"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Date of Birth</label>
          <input
            type="date"
            value={traveler.date_of_birth || ''}
            onChange={(e) => onChange({ ...traveler, date_of_birth: e.target.value })}
            className="input text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Passport Number</label>
          <input
            type="text"
            value={traveler.passport_number || ''}
            onChange={(e) => onChange({ ...traveler, passport_number: e.target.value })}
            className="input text-sm"
            placeholder="AB1234567"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Passport Expiry</label>
          <input
            type="date"
            value={traveler.passport_expiry || ''}
            onChange={(e) => onChange({ ...traveler, passport_expiry: e.target.value })}
            className="input text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Nationality</label>
          <input
            type="text"
            value={traveler.nationality || ''}
            onChange={(e) => onChange({ ...traveler, nationality: e.target.value })}
            className="input text-sm"
            placeholder="South African"
          />
        </div>
      </div>

      {isLead && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
            <input
              type="email"
              value={traveler.email || ''}
              onChange={(e) => onChange({ ...traveler, email: e.target.value })}
              className="input text-sm"
              placeholder="john@example.com"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
            <input
              type="tel"
              value={traveler.phone || ''}
              onChange={(e) => onChange({ ...traveler, phone: e.target.value })}
              className="input text-sm"
              placeholder="+27 82 123 4567"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Line Item Component for Manual Invoice
function LineItemRow({ item, index, onChange, onRemove, canRemove }) {
  return (
    <div className="flex gap-2 items-start">
      <div className="flex-1">
        <input
          type="text"
          value={item.description || ''}
          onChange={(e) => onChange({ ...item, description: e.target.value })}
          placeholder="Description"
          className="input text-sm w-full"
        />
      </div>
      <div className="w-20">
        <input
          type="number"
          value={item.quantity || 1}
          onChange={(e) => onChange({ ...item, quantity: parseInt(e.target.value) || 1 })}
          placeholder="Qty"
          min="1"
          className="input text-sm w-full"
        />
      </div>
      <div className="w-28">
        <input
          type="number"
          value={item.unit_price || ''}
          onChange={(e) => onChange({ ...item, unit_price: parseFloat(e.target.value) || 0 })}
          placeholder="Unit Price"
          min="0"
          step="0.01"
          className="input text-sm w-full"
        />
      </div>
      <div className="w-28 flex items-center">
        <span className="text-sm font-medium text-gray-700">
          R {((item.quantity || 1) * (item.unit_price || 0)).toLocaleString()}
        </span>
      </div>
      {canRemove && (
        <button type="button" onClick={onRemove} className="p-2 text-red-500 hover:bg-red-50 rounded">
          <XMarkIcon className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// Create Invoice Modal
function CreateInvoiceModal({ isOpen, onClose, onCreated, quotes, preSelectedQuote }) {
  // Mode: 'quote' or 'manual'
  const [mode, setMode] = useState(preSelectedQuote ? 'quote' : 'quote');
  const [step, setStep] = useState(1);
  const [selectedQuoteId, setSelectedQuoteId] = useState(preSelectedQuote?.quote_id || '');
  const [selectedQuote, setSelectedQuote] = useState(preSelectedQuote || null);
  const [selectedHotelIndex, setSelectedHotelIndex] = useState(0);
  const [dueDate, setDueDate] = useState('');
  const [notes, setNotes] = useState('');
  const [travelers, setTravelers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Manual invoice state
  const [manualCustomer, setManualCustomer] = useState({
    name: '',
    email: '',
    phone: '',
  });
  const [lineItems, setLineItems] = useState([
    { description: '', quantity: 1, unit_price: 0 }
  ]);
  const [destination, setDestination] = useState('');

  useEffect(() => {
    if (isOpen) {
      const defaultDue = new Date();
      defaultDue.setDate(defaultDue.getDate() + 14);
      setDueDate(defaultDue.toISOString().split('T')[0]);

      if (preSelectedQuote) {
        setMode('quote');
        setSelectedQuoteId(preSelectedQuote.quote_id);
        setSelectedQuote(preSelectedQuote);
        initializeTravelers(preSelectedQuote);
      }
    }
  }, [isOpen, preSelectedQuote]);

  useEffect(() => {
    if (selectedQuoteId && quotes.length > 0) {
      const quote = quotes.find(q => q.quote_id === selectedQuoteId);
      if (quote) {
        setSelectedQuote(quote);
        initializeTravelers(quote);
      }
    }
  }, [selectedQuoteId, quotes]);

  const initializeTravelers = (quote) => {
    if (!quote) return;
    const numAdults = quote.adults || 2;
    const numChildren = quote.children || 0;
    
    const newTravelers = [{
      type: 'adult',
      is_lead: true,
      first_name: quote.customer_name?.split(' ')[0] || '',
      last_name: quote.customer_name?.split(' ').slice(1).join(' ') || '',
      email: quote.customer_email || '',
      phone: quote.customer_phone || '',
      nationality: 'South African',
    }];
    
    for (let i = 1; i < numAdults; i++) {
      newTravelers.push({ type: 'adult', is_lead: false, nationality: 'South African' });
    }
    
    for (let i = 0; i < numChildren; i++) {
      newTravelers.push({ type: 'child', is_lead: false, nationality: 'South African' });
    }
    
    setTravelers(newTravelers);
  };

  const updateTraveler = (index, data) => {
    const updated = [...travelers];
    updated[index] = data;
    setTravelers(updated);
  };

  const removeTraveler = (index) => {
    setTravelers(travelers.filter((_, i) => i !== index));
  };

  const getSelectedHotel = () => {
    if (!selectedQuote?.hotels) return null;
    return selectedQuote.hotels[selectedHotelIndex];
  };

  // Handle line items for manual invoice
  const updateLineItem = (index, data) => {
    const updated = [...lineItems];
    updated[index] = data;
    setLineItems(updated);
  };

  const addLineItem = () => {
    setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0 }]);
  };

  const removeLineItem = (index) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const getManualTotal = () => {
    return lineItems.reduce((sum, item) => sum + (item.quantity || 1) * (item.unit_price || 0), 0);
  };

  const handleCreate = async () => {
    setLoading(true);
    setError(null);

    try {
      let response;

      if (mode === 'quote') {
        // Create from quote
        const hotel = getSelectedHotel();
        if (!hotel || !selectedQuote) {
          setError('Please select a quote and hotel package');
          setLoading(false);
          return;
        }

        response = await invoicesApi.create({
          quote_id: selectedQuote.quote_id,
          customer_name: selectedQuote.customer_name,
          customer_email: selectedQuote.customer_email,
          customer_phone: selectedQuote.customer_phone,
          destination: selectedQuote.destination,
          items: [{
            description: `${hotel.name || hotel.hotel_name} - ${selectedQuote.nights} nights`,
            hotel_name: hotel.name || hotel.hotel_name,
            room_type: hotel.room_type,
            meal_plan: hotel.meal_plan,
            destination: selectedQuote.destination,
            check_in: selectedQuote.check_in_date,
            check_out: selectedQuote.check_out_date,
            nights: selectedQuote.nights,
            amount: hotel.total_price,
          }],
          total_amount: hotel.total_price,
          travelers: travelers,
          due_date: dueDate,
          notes: notes,
        });
      } else {
        // Create manual invoice
        if (!manualCustomer.name || !manualCustomer.email) {
          setError('Customer name and email are required');
          setLoading(false);
          return;
        }

        const validItems = lineItems.filter(item => item.description && item.unit_price > 0);
        if (validItems.length === 0) {
          setError('At least one valid line item is required');
          setLoading(false);
          return;
        }

        // Calculate due days from due date
        const dueDateObj = new Date(dueDate);
        const today = new Date();
        const dueDays = Math.max(1, Math.ceil((dueDateObj - today) / (1000 * 60 * 60 * 24)));

        response = await invoicesApi.createManual({
          customer_name: manualCustomer.name,
          customer_email: manualCustomer.email,
          customer_phone: manualCustomer.phone || null,
          items: validItems.map(item => ({
            description: item.description,
            quantity: item.quantity || 1,
            unit_price: item.unit_price || 0,
            amount: (item.quantity || 1) * (item.unit_price || 0),
          })),
          notes: notes,
          due_days: dueDays,
          destination: destination || null,
        });
      }

      if (response.data?.success || response.data?.invoice_id) {
        onCreated(response.data.data || response.data);
        resetForm();
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

  const resetForm = () => {
    setMode('quote');
    setStep(1);
    setSelectedQuoteId('');
    setSelectedQuote(null);
    setSelectedHotelIndex(0);
    setTravelers([]);
    setNotes('');
    setError(null);
    // Reset manual invoice state
    setManualCustomer({ name: '', email: '', phone: '' });
    setLineItems([{ description: '', quantity: 1, unit_price: 0 }]);
    setDestination('');
  };

  if (!isOpen) return null;

  const hotel = getSelectedHotel();

  // Get step info based on mode
  const getStepInfo = () => {
    if (mode === 'manual') {
      return {
        total: 2,
        labels: { 1: 'Invoice Details', 2: 'Review' }
      };
    }
    return {
      total: 3,
      labels: { 1: 'Select Package', 2: 'Traveler Details', 3: 'Review' }
    };
  };

  const stepInfo = getStepInfo();

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Create Invoice</h3>
            <p className="text-sm text-gray-500">
              Step {step} of {stepInfo.total}: {stepInfo.labels[step]}
            </p>
          </div>
          <button onClick={() => { resetForm(); onClose(); }} className="p-1 hover:bg-gray-100 rounded-lg">
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-2 bg-gray-50">
          <div className="flex gap-2">
            {Array.from({ length: stepInfo.total }, (_, i) => i + 1).map((s) => (
              <div key={s} className={`flex-1 h-2 rounded-full ${s <= step ? 'bg-purple-600' : 'bg-gray-200'}`} />
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              {/* Mode Toggle - only show if no pre-selected quote */}
              {!preSelectedQuote && (
                <div className="flex border-b border-gray-200 mb-4">
                  <button
                    type="button"
                    onClick={() => { setMode('quote'); setStep(1); }}
                    className={`px-4 py-2 text-sm font-medium border-b-2 ${
                      mode === 'quote'
                        ? 'border-purple-600 text-purple-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    From Quote
                  </button>
                  <button
                    type="button"
                    onClick={() => { setMode('manual'); setStep(1); }}
                    className={`px-4 py-2 text-sm font-medium border-b-2 ${
                      mode === 'manual'
                        ? 'border-purple-600 text-purple-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Manual Entry
                  </button>
                </div>
              )}

              {mode === 'quote' ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Select Quote *</label>
                    <select value={selectedQuoteId} onChange={(e) => setSelectedQuoteId(e.target.value)} className="input">
                      <option value="">Choose a quote...</option>
                      {quotes.map((quote) => (
                        <option key={quote.quote_id} value={quote.quote_id}>
                          {quote.customer_name} - {quote.destination} (R {(quote.total_price || 0).toLocaleString()})
                        </option>
                      ))}
                    </select>
                  </div>

                  {selectedQuote?.hotels?.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Select Hotel Package *</label>
                      <div className="space-y-2">
                        {selectedQuote.hotels.map((h, idx) => (
                          <label key={idx} className={`flex items-center justify-between p-4 border rounded-lg cursor-pointer ${
                            selectedHotelIndex === idx ? 'border-purple-500 bg-purple-50' : 'border-gray-200'
                          }`}>
                            <div className="flex items-center gap-3">
                              <input type="radio" checked={selectedHotelIndex === idx} onChange={() => setSelectedHotelIndex(idx)} className="w-4 h-4 text-purple-600" />
                              <div>
                                <p className="font-medium">{h.name || h.hotel_name}</p>
                                <p className="text-sm text-gray-500">{h.room_type} • {h.meal_plan}</p>
                              </div>
                            </div>
                            <span className="font-semibold text-purple-600">R {(h.total_price || 0).toLocaleString()}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                    <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="input" min={new Date().toISOString().split('T')[0]} />
                  </div>
                </>
              ) : (
                <>
                  {/* Manual Invoice - Customer Info */}
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900 flex items-center gap-2">
                      <UserIcon className="w-4 h-4" /> Customer Information
                    </h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Name *</label>
                        <input
                          type="text"
                          value={manualCustomer.name}
                          onChange={(e) => setManualCustomer({ ...manualCustomer, name: e.target.value })}
                          className="input"
                          placeholder="Customer name"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Email *</label>
                        <input
                          type="email"
                          value={manualCustomer.email}
                          onChange={(e) => setManualCustomer({ ...manualCustomer, email: e.target.value })}
                          className="input"
                          placeholder="customer@example.com"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
                        <input
                          type="tel"
                          value={manualCustomer.phone}
                          onChange={(e) => setManualCustomer({ ...manualCustomer, phone: e.target.value })}
                          className="input"
                          placeholder="+27 82 123 4567"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Destination</label>
                        <input
                          type="text"
                          value={destination}
                          onChange={(e) => setDestination(e.target.value)}
                          className="input"
                          placeholder="e.g., Zanzibar"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Line Items */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-900">Line Items</h4>
                      <button type="button" onClick={addLineItem} className="text-sm text-purple-600 hover:text-purple-800">
                        + Add Item
                      </button>
                    </div>
                    <div className="text-xs text-gray-500 grid grid-cols-[1fr_80px_112px_112px_32px] gap-2 px-1">
                      <span>Description</span>
                      <span>Qty</span>
                      <span>Unit Price</span>
                      <span>Amount</span>
                      <span></span>
                    </div>
                    <div className="space-y-2">
                      {lineItems.map((item, idx) => (
                        <LineItemRow
                          key={idx}
                          item={item}
                          index={idx}
                          onChange={(data) => updateLineItem(idx, data)}
                          onRemove={() => removeLineItem(idx)}
                          canRemove={lineItems.length > 1}
                        />
                      ))}
                    </div>
                    <div className="flex justify-end pt-2 border-t border-gray-200">
                      <div className="text-right">
                        <span className="text-sm text-gray-500">Total: </span>
                        <span className="text-lg font-bold text-purple-600">R {getManualTotal().toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Due Date */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                    <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="input" min={new Date().toISOString().split('T')[0]} />
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 2 for Quote mode: Traveler Details */}
          {step === 2 && mode === 'quote' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-medium">Travelers ({travelers.length})</h4>
                <button type="button" onClick={() => setTravelers([...travelers, { type: 'adult', is_lead: false, nationality: 'South African' }])} className="text-sm text-purple-600">+ Add Traveler</button>
              </div>
              {travelers.map((traveler, idx) => (
                <TravelerForm key={idx} index={idx} traveler={traveler} onChange={(data) => updateTraveler(idx, data)} onRemove={() => removeTraveler(idx)} isLead={traveler.is_lead} />
              ))}
            </div>
          )}

          {/* Step 2 for Manual mode: Review */}
          {step === 2 && mode === 'manual' && (
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium mb-3">Invoice Summary</h4>
                <div className="text-sm space-y-2">
                  <div className="flex justify-between"><span className="text-gray-600">Customer:</span><span className="font-medium">{manualCustomer.name}</span></div>
                  <div className="flex justify-between"><span className="text-gray-600">Email:</span><span>{manualCustomer.email}</span></div>
                  {destination && <div className="flex justify-between"><span className="text-gray-600">Destination:</span><span>{destination}</span></div>}
                  <div className="flex justify-between"><span className="text-gray-600">Due Date:</span><span>{dueDate}</span></div>
                </div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium mb-2">Line Items ({lineItems.filter(i => i.description).length})</h4>
                <div className="space-y-1">
                  {lineItems.filter(i => i.description).map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span>{item.description} x{item.quantity || 1}</span>
                      <span className="font-medium">R {((item.quantity || 1) * (item.unit_price || 0)).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
                <div className="border-t pt-2 mt-2 flex justify-between">
                  <span className="font-medium">Total:</span>
                  <span className="font-bold text-purple-600">R {getManualTotal().toLocaleString()}</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} className="input min-h-20" placeholder="Additional notes..." />
              </div>
            </div>
          )}

          {/* Step 3 for Quote mode: Review */}
          {step === 3 && mode === 'quote' && (
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium mb-3">Package Summary</h4>
                {hotel && (
                  <div className="text-sm space-y-2">
                    <div className="flex justify-between"><span className="text-gray-600">Hotel:</span><span className="font-medium">{hotel.name || hotel.hotel_name}</span></div>
                    <div className="flex justify-between"><span className="text-gray-600">Destination:</span><span>{selectedQuote?.destination}</span></div>
                    <div className="flex justify-between"><span className="text-gray-600">Nights:</span><span>{selectedQuote?.nights}</span></div>
                    <div className="flex justify-between border-t pt-2 mt-2"><span className="font-medium">Total:</span><span className="font-bold text-purple-600">R {(hotel.total_price || 0).toLocaleString()}</span></div>
                  </div>
                )}
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium mb-2">Travelers ({travelers.length})</h4>
                {travelers.map((t, idx) => <p key={idx} className="text-sm">{t.is_lead ? '👤 ' : ''}{t.first_name} {t.last_name}</p>)}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} className="input min-h-20" placeholder="Additional notes..." />
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button onClick={() => step > 1 ? setStep(step - 1) : (resetForm(), onClose())} className="btn-secondary">
            {step === 1 ? 'Cancel' : 'Back'}
          </button>
          {step < stepInfo.total ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={step === 1 && mode === 'quote' && !selectedQuote}
              className="btn-primary"
            >
              Continue
            </button>
          ) : (
            <button onClick={handleCreate} disabled={loading} className="btn-primary">
              {loading ? 'Creating...' : 'Create Invoice'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InvoicesList() {
  const navigate = useNavigate();
  const location = useLocation();
  const [invoices, setInvoices] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [stats, setStats] = useState({ total: 0, paid: 0, pending: 0, overdue: 0 });
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [preSelectedQuote, setPreSelectedQuote] = useState(null);
  const [toast, setToast] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [createdInvoice, setCreatedInvoice] = useState(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  useEffect(() => {
    loadData();
    if (location.state?.convertQuote) {
      setPreSelectedQuote(location.state.convertQuote);
      setShowCreateModal(true);
    }
  }, [statusFilter, location.state]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [invoicesRes, quotesRes] = await Promise.all([
        invoicesApi.list({ status: statusFilter || undefined, limit: 50 }),
        quotesApi.list({ limit: 50 }),
      ]);
      
      const invoiceData = invoicesRes.data?.data || invoicesRes.data || [];
      setInvoices(Array.isArray(invoiceData) ? invoiceData : []);
      setQuotes(quotesRes.data?.data || []);
      
      const invoiceList = Array.isArray(invoiceData) ? invoiceData : [];
      setStats({
        total: invoiceList.reduce((sum, inv) => sum + (inv.total_amount || inv.total || 0), 0),
        paid: invoiceList.filter(i => i.status === 'paid').reduce((sum, inv) => sum + (inv.total_amount || inv.total || 0), 0),
        pending: invoiceList.filter(i => ['sent', 'viewed', 'partial', 'draft'].includes(i.status)).length,
        overdue: invoiceList.filter(i => i.status === 'overdue').length,
      });
    } catch (error) {
      console.error('Failed to load data:', error);
      showToast('Failed to load invoices', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleDownload = async (e, invoiceId) => {
    e.stopPropagation();
    setActionLoading(invoiceId + '-download');
    try {
      const response = await invoicesApi.download(invoiceId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${invoiceId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast('Invoice downloaded!', 'success');
    } catch (error) {
      showToast('Download not available', 'warning');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSendEmail = async (e, invoiceId) => {
    e.stopPropagation();
    setActionLoading(invoiceId + '-email');
    try {
      const response = await invoicesApi.send(invoiceId);
      if (response.data?.success) {
        showToast('Invoice sent!', 'success');
        loadData();
      } else {
        showToast('Failed to send invoice', 'error');
      }
    } catch (error) {
      showToast('Failed to send invoice', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  // Modal handlers (without event object)
  const handleModalSendEmail = async (invoiceId) => {
    try {
      const response = await invoicesApi.send(invoiceId);
      if (response.data?.success) {
        showToast('Invoice sent to client!', 'success');
        loadData();
      } else {
        showToast('Failed to send invoice', 'error');
      }
    } catch (error) {
      showToast('Failed to send invoice', 'error');
    }
  };

  const handleModalDownload = async (invoiceId) => {
    try {
      const response = await invoicesApi.download(invoiceId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${invoiceId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast('Invoice downloaded!', 'success');
    } catch (error) {
      showToast('Download not available', 'warning');
    }
  };

  const handleInvoiceCreated = (invoice) => {
    setCreatedInvoice(invoice);
    setShowSuccessModal(true);
    loadData();
  };

  const handleCloseSuccessModal = () => {
    setShowSuccessModal(false);
    setCreatedInvoice(null);
  };

  const filteredInvoices = invoices.filter(invoice => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      invoice.customer_name?.toLowerCase().includes(searchLower) ||
      invoice.customer_email?.toLowerCase().includes(searchLower) ||
      invoice.invoice_id?.toLowerCase().includes(searchLower) ||
      invoice.destination?.toLowerCase().includes(searchLower)
    );
  });

  const formatCurrency = (amount) => `R ${Number(amount || 0).toLocaleString()}`;

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="text-gray-500 mt-1">Manage and track customer invoices</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
          <button onClick={() => { setPreSelectedQuote(null); setShowCreateModal(true); }} className="btn-primary flex items-center gap-2">
            <PlusIcon className="w-5 h-5" />
            Create Invoice
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-500">Total Invoiced</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(stats.total)}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-500">Total Paid</p>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(stats.paid)}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-500">Pending</p>
          <p className="text-2xl font-bold text-blue-600">{stats.pending}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-500">Overdue</p>
          <p className="text-2xl font-bold text-red-600">{stats.overdue}</p>
        </div>
      </div>

      <div className="card">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input type="text" placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} className="input pl-10" />
            </div>
          </div>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input w-40">
            <option value="">All Status</option>
            {Object.entries(statusConfig).map(([key, config]) => (
              <option key={key} value={key}>{config.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        {loading ? (
          <SkeletonTable rows={5} columns={8} />
        ) : filteredInvoices.length === 0 ? (
          <div className="text-center py-12">
            <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No invoices found</h3>
            <button onClick={() => setShowCreateModal(true)} className="btn-primary mt-4">Create Invoice</button>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Invoice</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Customer</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Destination</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Amount</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Paid</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Due Date</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredInvoices.map((invoice) => {
                const status = statusConfig[invoice.status] || statusConfig.draft;
                const StatusIcon = status.icon;
                const invoiceId = invoice.invoice_id || invoice.id;
                
                return (
                  <tr key={invoiceId} onClick={() => navigate(`/invoices/${invoiceId}`)} onMouseEnter={() => invoicesApi.prefetch(invoiceId)} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-6 py-4">
                      <span className="font-mono font-medium text-purple-600">{invoiceId?.slice(0, 15)}</span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">{invoice.customer_name}</p>
                      <p className="text-sm text-gray-500">{invoice.customer_email}</p>
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {invoice.destination || invoice.items?.[0]?.destination || '-'}
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900">
                      {formatCurrency(invoice.total_amount || invoice.total)}
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {formatCurrency(invoice.paid_amount)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${status.color}`}>
                        <StatusIcon className="w-3.5 h-3.5" />
                        {status.label}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-600 text-sm">{formatDate(invoice.due_date)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/invoices/${invoiceId}`); }}
                          className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                          title="View"
                        >
                          <EyeIcon className="w-5 h-5" />
                        </button>
                        <button
                          onClick={(e) => handleDownload(e, invoiceId)}
                          disabled={actionLoading === invoiceId + '-download'}
                          className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                          title="Download PDF"
                        >
                          <ArrowDownTrayIcon className="w-5 h-5" />
                        </button>
                        <button
                          onClick={(e) => handleSendEmail(e, invoiceId)}
                          disabled={actionLoading === invoiceId + '-email'}
                          className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                          title="Send Email"
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

      {!loading && filteredInvoices.length > 0 && (
        <p className="text-sm text-gray-500 text-center">Showing {filteredInvoices.length} invoice{filteredInvoices.length !== 1 ? 's' : ''}</p>
      )}

      <CreateInvoiceModal
        isOpen={showCreateModal}
        onClose={() => { setShowCreateModal(false); setPreSelectedQuote(null); }}
        onCreated={handleInvoiceCreated}
        quotes={quotes}
        preSelectedQuote={preSelectedQuote}
      />

      <InvoiceSuccessModal
        invoice={createdInvoice}
        isOpen={showSuccessModal}
        onClose={handleCloseSuccessModal}
        onSendEmail={handleModalSendEmail}
        onDownloadPdf={handleModalDownload}
        onViewInvoice={(id) => navigate(`/invoices/${id}`)}
      />

      {toast && (
        <div className={`fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 ${toast.type === 'success' ? 'bg-green-600' : toast.type === 'warning' ? 'bg-yellow-500' : 'bg-red-600'} text-white`}>
          <CheckCircleIcon className="w-5 h-5" />
          {toast.message}
          <button onClick={() => setToast(null)}><XMarkIcon className="w-4 h-4" /></button>
        </div>
      )}
    </div>
  );
}
