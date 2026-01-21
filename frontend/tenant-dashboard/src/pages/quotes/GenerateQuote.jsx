import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { quotesApi, pricingApi } from '../../services/api';
import {
  UserIcon,
  EnvelopeIcon,
  PhoneIcon,
  MapPinIcon,
  CalendarIcon,
  UsersIcon,
  CurrencyDollarIcon,
  PaperAirplaneIcon,
  ArrowLeftIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  BuildingOfficeIcon,
  XMarkIcon,
  StarIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid, CheckIcon } from '@heroicons/react/24/solid';

export default function GenerateQuote() {
  const navigate = useNavigate();
  const [destinations, setDestinations] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [loadingHotels, setLoadingHotels] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    destination: '',
    check_in: '',
    check_out: '',
    adults: 2,
    children: 0,
    children_ages: '',
    budget: '',
    message: '',
    send_email: true,
    selected_hotels: [], // Array of hotel names
  });

  useEffect(() => {
    loadDestinations();
  }, []);

  // Load hotels when destination changes
  useEffect(() => {
    if (formData.destination) {
      loadHotels(formData.destination);
    } else {
      setHotels([]);
      setFormData(prev => ({ ...prev, selected_hotels: [] }));
    }
  }, [formData.destination]);

  const loadHotels = async (destination) => {
    setLoadingHotels(true);
    try {
      const response = await pricingApi.listHotels({ destination });
      const hotelList = response.data?.data || response.data || [];
      setHotels(hotelList);
    } catch (err) {
      console.error('Failed to load hotels:', err);
      setHotels([]);
    } finally {
      setLoadingHotels(false);
    }
  };

  const toggleHotel = (hotelName) => {
    setFormData(prev => {
      const selected = prev.selected_hotels;
      if (selected.includes(hotelName)) {
        return { ...prev, selected_hotels: selected.filter(h => h !== hotelName) };
      } else {
        return { ...prev, selected_hotels: [...selected, hotelName] };
      }
    });
  };

  const loadDestinations = async () => {
    try {
      const response = await pricingApi.listDestinations();
      const dests = response.data?.data || response.data || [];
      setDestinations(dests);
      // Set first destination as default
      if (dests.length > 0 && !formData.destination) {
        setFormData(prev => ({ ...prev, destination: dests[0].destination || dests[0] }));
      }
    } catch (err) {
      console.error('Failed to load destinations:', err);
      // Fallback destinations
      setDestinations([
        { destination: 'Zanzibar' },
        { destination: 'Mauritius' },
        { destination: 'Maldives' },
        { destination: 'Kenya' },
        { destination: 'Victoria Falls' },
      ]);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const validateForm = () => {
    if (!formData.name.trim()) return 'Name is required';
    if (!formData.email.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) return 'Invalid email format';
    if (!formData.destination) return 'Destination is required';
    if (!formData.check_in) return 'Check-in date is required';
    if (!formData.check_out) return 'Check-out date is required';
    if (new Date(formData.check_out) <= new Date(formData.check_in)) {
      return 'Check-out must be after check-in';
    }
    if (formData.adults < 1) return 'At least 1 adult is required';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      // Parse children ages
      let childrenAges = [];
      if (formData.children > 0 && formData.children_ages) {
        childrenAges = formData.children_ages
          .split(',')
          .map(age => parseInt(age.trim()))
          .filter(age => !isNaN(age) && age >= 0 && age < 18);
      }

      // Build the request payload - matching the API's QuoteGenerateRequest schema
      const payload = {
        inquiry: {
          name: formData.name.trim(),
          email: formData.email.trim(),
          phone: formData.phone.trim() || null,
          destination: formData.destination,
          check_in: formData.check_in,
          check_out: formData.check_out,
          adults: parseInt(formData.adults) || 2,
          children: parseInt(formData.children) || 0,
          children_ages: childrenAges.length > 0 ? childrenAges : null,
          budget: formData.budget ? parseFloat(formData.budget) : null,
          message: formData.message.trim() || null,
        },
        send_email: formData.send_email,
        assign_consultant: true,
        // Include selected hotels if any (otherwise backend will auto-select)
        selected_hotels: formData.selected_hotels.length > 0 ? formData.selected_hotels : null,
      };

      console.log('Sending quote request:', payload);

      const response = await quotesApi.generate(payload);
      console.log('Quote response:', response.data);

      if (response.data?.success) {
        setSuccess({
          quote_id: response.data.quote_id,
          email_sent: response.data.email_sent,
          hotels_count: response.data.hotels_count,
        });
      } else {
        setError(response.data?.error || 'Failed to generate quote');
      }
    } catch (err) {
      console.error('Quote generation error:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to generate quote';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // Success screen
  if (success) {
    return (
      <div className="max-w-lg mx-auto">
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-[var(--color-success)]/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircleIcon className="w-10 h-10 text-[var(--color-success)]" />
          </div>
          <h2 className="text-2xl font-bold text-theme mb-2">Quote Generated!</h2>
          <p className="text-theme-secondary mb-6">
            Quote ID: <span className="font-mono font-medium">{success.quote_id}</span>
          </p>

          <div className="bg-theme-surface-elevated rounded-lg p-4 mb-6 text-left border border-theme">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-theme-muted">Hotels Found:</span>
                <span className="font-medium text-theme">{success.hotels_count || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-theme-muted">Email Sent:</span>
                <span className={`font-medium ${success.email_sent ? 'text-[var(--color-success)]' : 'text-[var(--color-warning)]'}`}>
                  {success.email_sent ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex gap-3 justify-center">
            <button
              onClick={() => navigate(`/quotes/${success.quote_id}`)}
              className="btn-primary"
            >
              View Quote
            </button>
            <button
              onClick={() => {
                setSuccess(null);
                setFormData({
                  name: '',
                  email: '',
                  phone: '',
                  destination: destinations[0]?.destination || '',
                  check_in: '',
                  check_out: '',
                  adults: 2,
                  children: 0,
                  children_ages: '',
                  budget: '',
                  message: '',
                  send_email: true,
                  selected_hotels: [],
                });
              }}
              className="btn-secondary"
            >
              Create Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/quotes')}
          className="p-2 hover:bg-theme-border-light rounded-lg transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5 text-theme-muted" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-theme">Generate Quote</h1>
          <p className="text-theme-muted">Create a personalized travel quote</p>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-lg p-4 mb-6 flex items-start gap-3">
          <ExclamationCircleIcon className="w-5 h-5 text-[var(--color-error)] flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-[var(--color-error)]">Error</p>
            <p className="text-[var(--color-error)]/80 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="card">
        <div className="space-y-6">
          {/* Customer Info Section */}
          <div>
            <h3 className="text-lg font-semibold text-theme mb-4 flex items-center gap-2">
              <UserIcon className="w-5 h-5 text-theme-primary" />
              Customer Information
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Full Name <span className="text-[var(--color-error)]">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="input"
                  placeholder="John Smith"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Email <span className="text-[var(--color-error)]">*</span>
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="input"
                  placeholder="john@example.com"
                  required
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-theme-secondary mb-1">
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

          {/* Trip Details Section */}
          <div>
            <h3 className="text-lg font-semibold text-theme mb-4 flex items-center gap-2">
              <MapPinIcon className="w-5 h-5 text-theme-primary" />
              Trip Details
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Destination <span className="text-[var(--color-error)]">*</span>
                </label>
                <select
                  name="destination"
                  value={formData.destination}
                  onChange={handleChange}
                  className="input"
                  required
                >
                  <option value="">Select destination</option>
                  {destinations.map((dest, idx) => (
                    <option key={idx} value={dest.destination || dest}>
                      {dest.destination || dest}
                    </option>
                  ))}
                </select>
              </div>

              {/* Hotel Selection - Optional */}
              {formData.destination && (
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-theme-secondary mb-1">
                    <BuildingOfficeIcon className="w-4 h-4 inline mr-1" />
                    Select Hotels (optional)
                  </label>
                  <p className="text-xs text-theme-muted mb-3">
                    Leave empty to auto-select based on availability, or choose specific hotels
                  </p>

                  {loadingHotels ? (
                    <div className="flex items-center gap-2 text-theme-muted py-2">
                      <div className="w-4 h-4 border-2 border-theme-primary border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm">Loading hotels...</span>
                    </div>
                  ) : hotels.length > 0 ? (
                    <div className="space-y-3">
                      {/* Selected Hotels Pills */}
                      {formData.selected_hotels.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {formData.selected_hotels.map(hotelName => (
                            <span
                              key={hotelName}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-primary)]/10 text-theme-primary rounded-full text-sm font-medium"
                            >
                              {hotelName}
                              <button
                                type="button"
                                onClick={() => toggleHotel(hotelName)}
                                className="hover:bg-[var(--color-primary)]/20 rounded-full p-0.5 transition-colors"
                              >
                                <XMarkIcon className="w-3.5 h-3.5" />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Hotel Checkboxes */}
                      <div className="max-h-56 overflow-y-auto border border-theme-border rounded-xl divide-y divide-theme-border bg-theme-surface">
                        {hotels.map((hotel, idx) => {
                          const hotelName = hotel.hotel_name || hotel.name || hotel;
                          const isSelected = formData.selected_hotels.includes(hotelName);
                          const starRating = hotel.star_rating || 0;
                          return (
                            <label
                              key={idx}
                              className={`flex items-center gap-3 p-3.5 cursor-pointer transition-all duration-200 ${
                                isSelected
                                  ? 'bg-[var(--color-primary)]/10 border-l-2 border-l-[var(--color-primary)]'
                                  : 'hover:bg-theme-surface-elevated border-l-2 border-l-transparent'
                              }`}
                            >
                              {/* Custom Checkbox */}
                              <div className="relative flex-shrink-0">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleHotel(hotelName)}
                                  className="sr-only"
                                />
                                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-200 ${
                                  isSelected
                                    ? 'bg-[var(--color-primary)] border-[var(--color-primary)]'
                                    : 'border-theme-border bg-theme-surface hover:border-theme-muted'
                                }`}>
                                  {isSelected && (
                                    <CheckIcon className="w-3.5 h-3.5 text-white" />
                                  )}
                                </div>
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-theme truncate">{hotelName}</p>
                                {starRating > 0 && (
                                  <div className="flex items-center gap-1.5 mt-0.5">
                                    <div className="flex">
                                      {[...Array(5)].map((_, i) => (
                                        i < starRating ? (
                                          <StarIconSolid key={i} className="w-3.5 h-3.5 text-amber-400" />
                                        ) : (
                                          <StarIcon key={i} className="w-3.5 h-3.5 text-theme-muted/40" />
                                        )
                                      ))}
                                    </div>
                                    {hotel.room_type && (
                                      <span className="text-xs text-theme-muted ml-1">{hotel.room_type}</span>
                                    )}
                                  </div>
                                )}
                              </div>
                              {isSelected && (
                                <CheckCircleIcon className="w-5 h-5 text-theme-primary flex-shrink-0" />
                              )}
                            </label>
                          );
                        })}
                      </div>
                      <p className="text-xs text-theme-muted">
                        {formData.selected_hotels.length} of {hotels.length} hotels selected
                      </p>
                    </div>
                  ) : (
                    <p className="text-sm text-theme-muted italic py-2">
                      No hotels found for this destination
                    </p>
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Check-in Date <span className="text-[var(--color-error)]">*</span>
                </label>
                <input
                  type="date"
                  name="check_in"
                  value={formData.check_in}
                  onChange={handleChange}
                  className="input"
                  min={new Date().toISOString().split('T')[0]}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Check-out Date <span className="text-[var(--color-error)]">*</span>
                </label>
                <input
                  type="date"
                  name="check_out"
                  value={formData.check_out}
                  onChange={handleChange}
                  className="input"
                  min={formData.check_in || new Date().toISOString().split('T')[0]}
                  required
                />
              </div>
            </div>
          </div>

          {/* Travelers Section */}
          <div>
            <h3 className="text-lg font-semibold text-theme mb-4 flex items-center gap-2">
              <UsersIcon className="w-5 h-5 text-theme-primary" />
              Travelers
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Adults <span className="text-[var(--color-error)]">*</span>
                </label>
                <input
                  type="number"
                  name="adults"
                  value={formData.adults}
                  onChange={handleChange}
                  className="input"
                  min="1"
                  max="20"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Children
                </label>
                <input
                  type="number"
                  name="children"
                  value={formData.children}
                  onChange={handleChange}
                  className="input"
                  min="0"
                  max="10"
                />
              </div>
              {formData.children > 0 && (
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-theme-secondary mb-1">
                    Children Ages (comma-separated)
                  </label>
                  <input
                    type="text"
                    name="children_ages"
                    value={formData.children_ages}
                    onChange={handleChange}
                    className="input"
                    placeholder="e.g., 5, 8, 12"
                  />
                  <p className="text-xs text-theme-muted mt-1">
                    Enter ages separated by commas (e.g., 5, 8, 12)
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Budget & Notes Section */}
          <div>
            <h3 className="text-lg font-semibold text-theme mb-4 flex items-center gap-2">
              <CurrencyDollarIcon className="w-5 h-5 text-theme-primary" />
              Budget & Notes
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Total Budget (optional)
                </label>
                <input
                  type="number"
                  name="budget"
                  value={formData.budget}
                  onChange={handleChange}
                  className="input"
                  placeholder="e.g., 50000"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Special Requests / Notes
                </label>
                <textarea
                  name="message"
                  value={formData.message}
                  onChange={handleChange}
                  className="input min-h-24"
                  placeholder="Any special requirements, preferences, or notes..."
                />
              </div>
            </div>
          </div>

          {/* Email Option */}
          <div className="flex items-center gap-3 p-4 bg-theme-surface-elevated rounded-lg border border-theme">
            <input
              type="checkbox"
              id="send_email"
              name="send_email"
              checked={formData.send_email}
              onChange={handleChange}
              className="w-4 h-4 rounded border-theme text-theme-primary focus:ring-[var(--color-primary)]"
            />
            <label htmlFor="send_email" className="text-sm text-theme-secondary">
              Send quote to customer via email
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Generating Quote...
              </>
            ) : (
              <>
                <PaperAirplaneIcon className="w-5 h-5" />
                Generate Quote
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
