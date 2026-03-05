import { useState, useEffect } from 'react';
import { websiteBuilderApi } from '../../services/api';
import {
  InboxIcon,
  PhoneIcon,
  EnvelopeIcon,
  CalendarIcon,
  UserGroupIcon,
  ArrowPathIcon,
  EyeIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

const STATUS_OPTIONS = ['all', 'new', 'contacted', 'quoted', 'booked', 'cancelled'];

const STATUS_COLORS = {
  new: 'bg-blue-100 text-blue-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  quoted: 'bg-purple-100 text-purple-700',
  booked: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
};

function formatDate(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('en-ZA', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function formatCurrency(amount, currency = 'ZAR') {
  if (!amount) return '-';
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
  }).format(amount);
}

export default function WebsiteBookings() {
  const [loading, setLoading] = useState(true);
  const [bookings, setBookings] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadBookings();
  }, [statusFilter]);

  async function loadBookings() {
    setLoading(true);
    setError(null);
    try {
      const filters = statusFilter !== 'all' ? { status: statusFilter } : {};
      const response = await websiteBuilderApi.getBookings(filters);
      // Handle both 'bookings' and 'bookingRequests' response formats
      setBookings(response.data?.bookings || response.data?.bookingRequests || []);
    } catch (err) {
      console.error('Failed to load bookings:', err);
      setError('Failed to load bookings. Check Website Builder connection.');
    } finally {
      setLoading(false);
    }
  }

  async function updateStatus(bookingId, newStatus) {
    try {
      await websiteBuilderApi.updateBookingStatus(bookingId, newStatus);
      setBookings(prev =>
        prev.map(b => b.id === bookingId ? { ...b, status: newStatus } : b)
      );
      if (selectedBooking?.id === bookingId) {
        setSelectedBooking(prev => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      console.error('Failed to update status:', err);
      setError('Failed to update booking status');
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Website Bookings</h1>
          <p className="text-gray-500">Manage booking requests from your website</p>
        </div>
        <button onClick={loadBookings} className="btn-secondary flex items-center gap-2">
          <ArrowPathIcon className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Status Filters */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_OPTIONS.map(status => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
              statusFilter === status
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Bookings Table */}
      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="animate-pulse">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 border-b border-gray-200" />
            ))}
          </div>
        </div>
      ) : bookings.length === 0 ? (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 text-center">
          <InboxIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Bookings Yet</h3>
          <p className="text-gray-500">
            Booking requests from your website will appear here.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Reference</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Guest</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Product</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Dates</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Status</th>
                <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {bookings.map(booking => (
                <tr key={booking.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm">{booking.reference_number}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{booking.guest_name}</div>
                    <div className="text-sm text-gray-500">{booking.guest_email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-gray-900">{booking.product_data?.name}</div>
                    <div className="text-sm text-gray-500">{booking.product_data?.destination}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatDate(booking.product_data?.checkIn)} - {formatDate(booking.product_data?.checkOut)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[booking.status]}`}>
                      {booking.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setSelectedBooking(booking)}
                      className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                    >
                      <EyeIcon className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Booking Detail Modal */}
      {selectedBooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setSelectedBooking(null)} />
          <div className="relative bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white">
              <div>
                <h3 className="font-semibold text-gray-900">Booking Details</h3>
                <p className="text-sm text-gray-500">{selectedBooking.reference_number}</p>
              </div>
              <button onClick={() => setSelectedBooking(null)} className="p-1 hover:bg-gray-100 rounded">
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {/* Guest Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Guest Information</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-gray-600">
                    <UserGroupIcon className="w-4 h-4" />
                    <span>{selectedBooking.guest_name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-600">
                    <EnvelopeIcon className="w-4 h-4" />
                    <a href={`mailto:${selectedBooking.guest_email}`} className="text-purple-600 hover:underline">
                      {selectedBooking.guest_email}
                    </a>
                  </div>
                  {selectedBooking.guest_phone && (
                    <div className="flex items-center gap-2 text-gray-600">
                      <PhoneIcon className="w-4 h-4" />
                      <a href={`tel:${selectedBooking.guest_phone}`} className="text-purple-600 hover:underline">
                        {selectedBooking.guest_phone}
                      </a>
                    </div>
                  )}
                </div>
              </div>

              {/* Product Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Booking Details</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Product:</span>
                    <span className="text-gray-900 font-medium">{selectedBooking.product_data?.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Destination:</span>
                    <span className="text-gray-900">{selectedBooking.product_data?.destination}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Check-in:</span>
                    <span className="text-gray-900">{formatDate(selectedBooking.product_data?.checkIn)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Check-out:</span>
                    <span className="text-gray-900">{formatDate(selectedBooking.product_data?.checkOut)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Guests:</span>
                    <span className="text-gray-900">
                      {selectedBooking.product_data?.adults || 2} adults
                      {selectedBooking.product_data?.children > 0 && `, ${selectedBooking.product_data.children} children`}
                    </span>
                  </div>
                  <div className="flex justify-between pt-2 border-t">
                    <span className="text-gray-500">Price:</span>
                    <span className="text-gray-900 font-semibold">
                      {formatCurrency(selectedBooking.product_data?.price, selectedBooking.product_data?.currency)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Special Requests */}
              {selectedBooking.special_requests && (
                <div className="bg-yellow-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-yellow-800 mb-2">Special Requests</h4>
                  <p className="text-sm text-yellow-700">{selectedBooking.special_requests}</p>
                </div>
              )}

              {/* Status Update */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Update Status</h4>
                <select
                  value={selectedBooking.status}
                  onChange={(e) => updateStatus(selectedBooking.id, e.target.value)}
                  className="input"
                >
                  <option value="new">New</option>
                  <option value="contacted">Contacted</option>
                  <option value="quoted">Quoted</option>
                  <option value="booked">Booked</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
