import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  XMarkIcon,
  UserIcon,
  EnvelopeIcon,
  PhoneIcon,
  MapPinIcon,
  CalendarIcon,
  UsersIcon,
  BuildingOfficeIcon,
  TicketIcon,
  PaperAirplaneIcon,
  TruckIcon,
  GiftIcon,
  TrashIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import { quotesApi } from '../../services/api';

// Type icon mapping
const typeIcons = {
  hotel: BuildingOfficeIcon,
  activity: TicketIcon,
  flight: PaperAirplaneIcon,
  transfer: TruckIcon,
  package: GiftIcon,
};

// Type colors
const typeColors = {
  hotel: 'bg-blue-100 text-blue-700',
  activity: 'bg-green-100 text-green-700',
  flight: 'bg-purple-100 text-purple-700',
  transfer: 'bg-orange-100 text-orange-700',
  package: 'bg-pink-100 text-pink-700',
};

function formatCurrency(amount, currency = 'ZAR') {
  if (!amount && amount !== 0) return '-';
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function CreateQuoteModal({
  isOpen,
  onClose,
  items,
  totals,
  onRemoveItem,
  onClearCart,
  onAddMore,
}) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    send_email: true,
  });

  // Reset form state when modal opens
  useEffect(() => {
    if (isOpen) {
      setError(null);
      setSuccess(null);
      setLoading(false);
    }
  }, [isOpen]);

  // Extract dates, destination, and occupancy from cart items
  const extractedDetails = (() => {
    let destination = '';
    let checkIn = '';
    let checkOut = '';
    let adults = 2;
    let children = 0;
    let rooms = null;
    let roomCount = 1;

    for (const item of items) {
      if (item.details?.destination && !destination) {
        destination = item.details.destination;
      }
      if (item.details?.check_in && !checkIn) {
        checkIn = item.details.check_in;
      }
      if (item.details?.check_out && !checkOut) {
        checkOut = item.details.check_out;
      }
      if (item.details?.adults) {
        adults = item.details.adults;
      }
      if (item.details?.children !== undefined && item.details?.children !== null) {
        children = item.details.children;
      }
      if (item.details?.rooms && !rooms) {
        rooms = item.details.rooms;
        roomCount = item.details.room_count || item.details.rooms.length;
      }
    }

    return { destination, checkIn, checkOut, adults, children, rooms, roomCount };
  })();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const validateForm = () => {
    if (!formData.name.trim()) return 'Customer name is required';
    if (!formData.email.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) return 'Invalid email format';
    if (items.length === 0) return 'No items in quote';
    return null;
  };

  const handleSubmit = async (asDraft = false) => {
    setError(null);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      // Build line items from cart
      const lineItems = items.map(item => ({
        type: item.type,
        name: item.name,
        description: [
          item.details?.room_type,
          item.details?.meal_plan,
          item.details?.category,
          item.details?.route,
        ].filter(Boolean).join(' - ') || null,
        price: item.price,
        currency: item.currency || 'ZAR',
        quantity: 1,
        nights: item.details?.nights || null,
        check_in: item.details?.check_in || null,
        check_out: item.details?.check_out || null,
        raw_data: item.details || null,
      }));

      // Build payload
      const payload = {
        inquiry: {
          name: formData.name.trim(),
          email: formData.email.trim(),
          phone: formData.phone.trim() || null,
          destination: extractedDetails.destination || 'Multiple',
          check_in: extractedDetails.checkIn || null,
          check_out: extractedDetails.checkOut || null,
          adults: extractedDetails.adults || 2,
          children: extractedDetails.children || 0,
          rooms: extractedDetails.rooms || null,
          room_count: extractedDetails.roomCount || 1,
          message: `Quote built from shopping cart with ${items.length} items`,
        },
        send_email: !asDraft && formData.send_email,
        assign_consultant: true,
        line_items: lineItems,
        save_as_draft: asDraft,
      };

      const response = await quotesApi.createWithItems(payload);

      if (response.data?.success) {
        setSuccess({
          quote_id: response.data.quote_id,
          email_sent: response.data.email_sent,
          is_draft: asDraft,
        });

        // Clear the cart
        onClearCart();
      } else {
        setError(response.data?.error || 'Failed to create quote');
      }
    } catch (err) {
      console.error('Quote creation error:', err);

      // Provide more helpful error messages
      let errorMsg = 'Failed to create quote';

      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
        // Network error - backend likely not running
        errorMsg = 'Cannot connect to server. Please ensure the backend is running on the correct port.';
      } else if (err.response?.status === 422) {
        // Validation error
        const detail = err.response?.data?.detail;
        if (Array.isArray(detail)) {
          errorMsg = detail.map(d => d.msg || d.message).join(', ');
        } else {
          errorMsg = detail || 'Invalid quote data. Please check all fields.';
        }
      } else if (err.response?.status === 401) {
        errorMsg = 'Session expired. Please log in again.';
      } else if (err.response?.status === 403) {
        errorMsg = 'You do not have permission to create quotes.';
      } else if (err.response?.data?.detail) {
        errorMsg = err.response.data.detail;
      } else if (err.message) {
        errorMsg = err.message;
      }

      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleViewQuote = () => {
    navigate(`/quotes/${success.quote_id}`);
    onClose();
  };

  const handleAddMore = () => {
    onAddMore?.();
    onClose();
  };

  if (!isOpen) return null;

  const currencies = Object.keys(totals);

  return (
    <div className="fixed inset-0 z-[60] overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-[var(--color-primary)] text-white">
            <h2 className="text-xl font-semibold">Create Quote</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-white/20 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Success State */}
          {success ? (
            <div className="p-6 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircleIcon className="h-10 w-10 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {success.is_draft ? 'Draft Saved!' : 'Quote Created!'}
              </h3>
              <p className="text-gray-500 mb-4">
                Quote ID: <span className="font-mono font-medium">{success.quote_id}</span>
              </p>
              {success.email_sent && (
                <p className="text-sm text-green-600 mb-4">
                  Quote sent to {formData.email}
                </p>
              )}
              <div className="flex gap-3 justify-center">
                <button onClick={handleViewQuote} className="btn-primary">
                  View Quote
                </button>
                <button onClick={onClose} className="btn-secondary">
                  Close
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Error */}
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
                    {error}
                  </div>
                )}

                {/* Customer Details */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                    <UserIcon className="h-4 w-4" />
                    Customer Details
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-600 mb-1">
                        Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        name="name"
                        value={formData.name}
                        onChange={handleChange}
                        className="input"
                        placeholder="Customer name"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-600 mb-1">
                        Email <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        className="input"
                        placeholder="customer@example.com"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-600 mb-1">
                        Phone
                      </label>
                      <input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        className="input"
                        placeholder="+27 82 123 4567"
                      />
                    </div>
                  </div>
                </div>

                {/* Trip Details (auto-extracted) */}
                {(extractedDetails.destination || extractedDetails.checkIn) && (
                  <div className="bg-purple-50 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-purple-800 mb-2">Trip Details</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {extractedDetails.destination && (
                        <div className="flex items-center gap-1.5 text-purple-700">
                          <MapPinIcon className="h-4 w-4" />
                          {extractedDetails.destination}
                        </div>
                      )}
                      {extractedDetails.checkIn && (
                        <div className="flex items-center gap-1.5 text-purple-700">
                          <CalendarIcon className="h-4 w-4" />
                          {extractedDetails.checkIn}
                        </div>
                      )}
                      {(extractedDetails.adults || extractedDetails.children > 0) && (
                        <div className="flex items-center gap-1.5 text-purple-700">
                          <UsersIcon className="h-4 w-4" />
                          {extractedDetails.adults} adult{extractedDetails.adults !== 1 ? 's' : ''}
                          {extractedDetails.children > 0 && `, ${extractedDetails.children} child${extractedDetails.children !== 1 ? 'ren' : ''}`}
                        </div>
                      )}
                      {extractedDetails.roomCount > 1 && (
                        <div className="flex items-center gap-1.5 text-purple-700">
                          <BuildingOfficeIcon className="h-4 w-4" />
                          {extractedDetails.roomCount} rooms
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Quote Items */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                    <DocumentTextIcon className="h-4 w-4" />
                    Quote Items ({items.length})
                  </h3>
                  <div className="space-y-2">
                    {items.map((item) => {
                      const TypeIcon = typeIcons[item.type] || GiftIcon;
                      const colorClass = typeColors[item.type] || 'bg-gray-100 text-gray-700';

                      return (
                        <div
                          key={`${item.type}-${item.id}`}
                          className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
                        >
                          <div className={`p-1.5 rounded-lg ${colorClass}`}>
                            <TypeIcon className="h-4 w-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900 text-sm truncate">
                              {item.name}
                            </p>
                            <p className="text-xs text-gray-500">
                              {item.type.charAt(0).toUpperCase() + item.type.slice(1)}
                            </p>
                          </div>
                          <span className="font-semibold text-purple-600 text-sm">
                            {formatCurrency(item.price, item.currency)}
                          </span>
                          <button
                            onClick={() => onRemoveItem(item.id, item.type)}
                            className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        </div>
                      );
                    })}
                  </div>

                  {/* Add More Button */}
                  <button
                    onClick={handleAddMore}
                    className="mt-3 w-full flex items-center justify-center gap-2 py-2 px-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-purple-400 hover:text-purple-600 transition-colors"
                  >
                    <PlusIcon className="h-4 w-4" />
                    Add More Services
                  </button>
                </div>

                {/* Totals */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-sm text-gray-500 mb-2">Estimated Total</div>
                  {currencies.map(currency => (
                    <div key={currency} className="flex items-center justify-between">
                      <span className="text-gray-600">{currency}</span>
                      <span className="text-xl font-bold text-gray-900">
                        {formatCurrency(totals[currency], currency)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Options */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="send_email"
                      name="send_email"
                      checked={formData.send_email}
                      onChange={handleChange}
                      className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                    />
                    <label htmlFor="send_email" className="text-sm text-gray-600">
                      Send quote to customer via email
                    </label>
                  </div>
                </div>
              </div>

              {/* Footer Actions */}
              <div className="flex-shrink-0 border-t border-gray-200 p-4 bg-gray-50 space-y-3">
                <button
                  onClick={() => handleSubmit(false)}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] text-white py-3 px-4 rounded-lg font-medium transition-all shadow-sm hover:shadow disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Creating...
                    </>
                  ) : (
                    <>
                      <CheckCircleIcon className="h-5 w-5" />
                      Confirm & Send
                    </>
                  )}
                </button>

                <button
                  onClick={() => handleSubmit(true)}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-white border border-gray-300 text-gray-700 py-2.5 px-4 rounded-lg font-medium hover:bg-gray-50 transition-all disabled:opacity-50"
                >
                  <DocumentTextIcon className="h-4 w-4" />
                  Save as Draft
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
