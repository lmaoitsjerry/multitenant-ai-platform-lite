import { useState, useEffect, useRef, useMemo } from 'react';
import {
  BuildingOfficeIcon,
  MagnifyingGlassIcon,
  StarIcon,
  CalendarIcon,
  UserGroupIcon,
  MapPinIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  MinusIcon,
  PlusIcon,
  FunnelIcon,
  XMarkIcon,
  AdjustmentsHorizontalIcon,
  WifiIcon,
  ShieldCheckIcon,
  GlobeAltIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import { hotelsApi, travelApi } from '../../services/api';
import { AddToQuoteButton } from '../../components/travel/FloatingQuoteCart';

// ==================== Filter Sidebar Component ====================
// Also available as shared component: import FilterSidebar from '../../components/travel/HotelFilters';
function FilterSidebar({
  filters,
  setFilters,
  facets,
  onClearFilters,
  isOpen,
  onClose,
}) {
  const toggleFilter = (filterType, value) => {
    setFilters((prev) => {
      const current = prev[filterType] || [];
      const newValues = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return { ...prev, [filterType]: newValues };
    });
  };

  const hasActiveFilters = Object.values(filters).some(
    (arr) => Array.isArray(arr) && arr.length > 0
  ) || filters.priceMin > 0 || filters.priceMax < Infinity;

  return (
    <div
      className={`
        md:block md:sticky md:top-4
        ${isOpen ? 'fixed inset-0 z-50 bg-black/50 md:bg-transparent md:relative md:inset-auto' : 'hidden'}
      `}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={`
          bg-theme-surface border border-theme rounded-lg p-4 space-y-5
          ${isOpen ? 'fixed right-0 top-0 h-full w-80 overflow-y-auto md:relative md:w-auto md:h-auto' : ''}
        `}
      >
        {/* Mobile Header */}
        <div className="flex items-center justify-between md:hidden">
          <h3 className="font-semibold text-theme">Filters</h3>
          <button onClick={onClose} className="p-1 hover:bg-theme-border-light rounded">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Header with Clear */}
        <div className="hidden md:flex items-center justify-between">
          <h3 className="font-semibold text-theme flex items-center gap-2">
            <FunnelIcon className="h-4 w-4" />
            Filters
          </h3>
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="text-xs text-theme-primary hover:text-theme-primary-dark"
            >
              Clear all
            </button>
          )}
        </div>

        {/* Star Rating Filter */}
        <div>
          <h4 className="text-sm font-medium text-theme mb-2">Star Rating</h4>
          <div className="space-y-1">
            {[5, 4, 3, 2, 1].map((star) => {
              const count = facets.stars?.[star] || 0;
              if (count === 0) return null;
              return (
                <label
                  key={star}
                  className="flex items-center gap-2 cursor-pointer hover:bg-theme-border-light p-1 rounded"
                >
                  <input
                    type="checkbox"
                    checked={filters.stars?.includes(star)}
                    onChange={() => toggleFilter('stars', star)}
                    className="rounded border-gray-300 text-theme-primary focus:ring-theme-primary"
                  />
                  <span className="flex items-center gap-1">
                    {[...Array(star)].map((_, i) => (
                      <StarIconSolid key={i} className="h-3.5 w-3.5 text-yellow-400" />
                    ))}
                  </span>
                  <span className="text-xs text-theme-muted ml-auto">({count})</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Meal Plan Filter */}
        {Object.keys(facets.mealPlan || {}).length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-theme mb-2">Meal Plan</h4>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {Object.entries(facets.mealPlan || {})
                .sort((a, b) => b[1] - a[1])
                .map(([plan, count]) => (
                  <label
                    key={plan}
                    className="flex items-center gap-2 cursor-pointer hover:bg-theme-border-light p-1 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={filters.mealPlan?.includes(plan)}
                      onChange={() => toggleFilter('mealPlan', plan)}
                      className="rounded border-gray-300 text-theme-primary focus:ring-theme-primary"
                    />
                    <span className="text-sm text-theme truncate flex-1">{plan}</span>
                    <span className="text-xs text-theme-muted">({count})</span>
                  </label>
                ))}
            </div>
          </div>
        )}

        {/* Price Range Filter */}
        <div>
          <h4 className="text-sm font-medium text-theme mb-2">
            Price Range ({facets.currency || 'ZAR'})
          </h4>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <input
                type="number"
                placeholder="Min"
                value={filters.priceMin || ''}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    priceMin: e.target.value ? Number(e.target.value) : 0,
                  }))
                }
                className="input text-sm py-1.5 w-full"
              />
              <span className="text-theme-muted">-</span>
              <input
                type="number"
                placeholder="Max"
                value={filters.priceMax === Infinity ? '' : filters.priceMax || ''}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    priceMax: e.target.value ? Number(e.target.value) : Infinity,
                  }))
                }
                className="input text-sm py-1.5 w-full"
              />
            </div>
            {facets.priceRange && (
              <p className="text-xs text-theme-muted">
                Range: {new Intl.NumberFormat('en-ZA', { style: 'currency', currency: facets.currency || 'ZAR', minimumFractionDigits: 0 }).format(facets.priceRange.min)} -{' '}
                {new Intl.NumberFormat('en-ZA', { style: 'currency', currency: facets.currency || 'ZAR', minimumFractionDigits: 0 }).format(facets.priceRange.max)}
              </p>
            )}
          </div>
        </div>

        {/* Location/Zone Filter */}
        {Object.keys(facets.zone || {}).length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-theme mb-2">Location</h4>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {Object.entries(facets.zone || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([zone, count]) => (
                  <label
                    key={zone}
                    className="flex items-center gap-2 cursor-pointer hover:bg-theme-border-light p-1 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={filters.zone?.includes(zone)}
                      onChange={() => toggleFilter('zone', zone)}
                      className="rounded border-gray-300 text-theme-primary focus:ring-theme-primary"
                    />
                    <span className="text-sm text-theme truncate flex-1">{zone}</span>
                    <span className="text-xs text-theme-muted">({count})</span>
                  </label>
                ))}
            </div>
          </div>
        )}

        {/* Mobile Apply Button */}
        <div className="md:hidden pt-4 border-t border-theme">
          <button
            onClick={onClose}
            className="w-full btn-primary"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================== Hotel Detail Modal ====================
function HotelDetailModal({ hotel, onClose, formatCurrency, renderStars, formatRoomType, getProviderStyle, checkIn, checkOut, calculateNights }) {
  if (!hotel) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {hotel.image_url && (
          <img src={hotel.image_url} alt={hotel.hotel_name} className="w-full h-72 object-cover rounded-t-xl" onError={(e) => { e.target.style.display = 'none'; }} />
        )}
        <div className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-gray-900">{hotel.hotel_name}</h2>
                {(hotel.source || hotel.provider) && (
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getProviderStyle(hotel.source || hotel.provider)}`}>
                    {(hotel.source || hotel.provider).toUpperCase()}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-2">
                {renderStars(hotel.stars)}
                {hotel.zone && <span className="text-sm text-gray-500"><MapPinIcon className="h-4 w-4 inline" /> {hotel.zone}</span>}
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {hotel.description && (
            <div className="mt-4">
              <h3 className="font-medium text-gray-900 mb-2">About</h3>
              <p className="text-gray-600 leading-relaxed">{hotel.description}</p>
            </div>
          )}

          {hotel.options && hotel.options.length > 0 && (
            <div className="mt-6">
              <h3 className="font-medium text-gray-900 mb-3">Room Options ({hotel.options.length})</h3>
              <div className="space-y-2">
                {hotel.options.map((option, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div>
                      <span className="font-medium text-gray-900">{formatRoomType(option.room_type)}</span>
                      <span className="text-gray-400 mx-2">&middot;</span>
                      <span className="text-gray-600">{option.meal_plan}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className="font-semibold text-gray-900">{formatCurrency(option.price_total, option.currency)}</span>
                        {option.price_per_night > 0 && (
                          <div className="text-xs text-gray-500">{formatCurrency(option.price_per_night, option.currency)}/night</div>
                        )}
                      </div>
                      <AddToQuoteButton item={{ id: `${hotel.hotel_id}-${idx}`, type: 'hotel', name: hotel.hotel_name, price: option.price_total, currency: option.currency || 'EUR', details: { hotel_id: hotel.hotel_id, room_type: option.room_type, meal_plan: option.meal_plan, stars: hotel.stars, check_in: checkIn, check_out: checkOut } }} size="sm" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ==================== Main Component ====================
export default function HotelsList() {
  // State
  const [destinations, setDestinations] = useState([]);
  const [selectedDestination, setSelectedDestination] = useState('');
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');

  // Room/Pax state
  const [rooms, setRooms] = useState([{ adults: 2, children: 0 }]);
  const [showRoomSelector, setShowRoomSelector] = useState(false);
  const roomSelectorRef = useRef(null);

  const [hotels, setHotels] = useState([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const [searchTime, setSearchTime] = useState(null);
  const [ratesAvailable, setRatesAvailable] = useState(null);
  const [expandedHotel, setExpandedHotel] = useState(null);
  const [selectedHotel, setSelectedHotel] = useState(null);
  const [showAllOptions, setShowAllOptions] = useState({}); // Track which hotels show all room options

  // Filter state
  const [filters, setFilters] = useState({
    stars: [],
    mealPlan: [],
    zone: [],
    priceMin: 0,
    priceMax: Infinity,
  });
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [sortBy, setSortBy] = useState('price_asc');

  // Load destinations on mount
  useEffect(() => {
    loadDestinations();
    checkRatesHealth();
  }, []);

  // Set default dates
  useEffect(() => {
    const today = new Date();
    const nextWeek = new Date(today);
    nextWeek.setDate(today.getDate() + 30);
    const checkOutDate = new Date(nextWeek);
    checkOutDate.setDate(nextWeek.getDate() + 5);

    setCheckIn(nextWeek.toISOString().split('T')[0]);
    setCheckOut(checkOutDate.toISOString().split('T')[0]);
  }, []);

  // Close room selector when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (roomSelectorRef.current && !roomSelectorRef.current.contains(event.target)) {
        setShowRoomSelector(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Extract filter facets from hotels
  const facets = useMemo(() => {
    if (!hotels.length) return {};

    const starsCount = {};
    const mealPlanCount = {};
    const zoneCount = {};
    let minPrice = Infinity;
    let maxPrice = 0;
    let currency = 'ZAR';

    hotels.forEach((hotel) => {
      // Stars
      const stars = Math.floor(hotel.stars || 0);
      if (stars > 0) {
        starsCount[stars] = (starsCount[stars] || 0) + 1;
      }

      // Zone
      if (hotel.zone) {
        zoneCount[hotel.zone] = (zoneCount[hotel.zone] || 0) + 1;
      }

      // Meal plans (from all options)
      if (hotel.options?.length) {
        hotel.options.forEach((opt) => {
          if (opt.meal_plan) {
            mealPlanCount[opt.meal_plan] = (mealPlanCount[opt.meal_plan] || 0) + 1;
          }
          // Price range
          if (opt.price_total) {
            minPrice = Math.min(minPrice, opt.price_total);
            maxPrice = Math.max(maxPrice, opt.price_total);
          }
          if (opt.currency) {
            currency = opt.currency;
          }
        });
      } else if (hotel.cheapest_price) {
        minPrice = Math.min(minPrice, hotel.cheapest_price);
        maxPrice = Math.max(maxPrice, hotel.cheapest_price);
        if (hotel.cheapest_meal_plan) {
          mealPlanCount[hotel.cheapest_meal_plan] = (mealPlanCount[hotel.cheapest_meal_plan] || 0) + 1;
        }
      }
    });

    return {
      stars: starsCount,
      mealPlan: mealPlanCount,
      zone: zoneCount,
      priceRange: minPrice !== Infinity ? { min: minPrice, max: maxPrice } : null,
      currency,
    };
  }, [hotels]);

  // Apply filters to hotels
  const filteredHotels = useMemo(() => {
    if (!hotels.length) return [];

    let result = hotels.filter((hotel) => {
      // Star filter
      if (filters.stars.length > 0) {
        const hotelStars = Math.floor(hotel.stars || 0);
        if (!filters.stars.includes(hotelStars)) return false;
      }

      // Meal plan filter
      if (filters.mealPlan.length > 0) {
        const hotelMealPlans = hotel.options?.map((o) => o.meal_plan) || [hotel.cheapest_meal_plan];
        if (!filters.mealPlan.some((mp) => hotelMealPlans.includes(mp))) return false;
      }

      // Zone filter
      if (filters.zone.length > 0) {
        if (!filters.zone.includes(hotel.zone)) return false;
      }

      // Price filter
      const price = hotel.cheapest_price || hotel.options?.[0]?.price_total || 0;
      if (price < filters.priceMin) return false;
      if (filters.priceMax !== Infinity && price > filters.priceMax) return false;

      return true;
    });

    // Sort
    switch (sortBy) {
      case 'price_asc':
        result.sort((a, b) => (a.cheapest_price || 0) - (b.cheapest_price || 0));
        break;
      case 'price_desc':
        result.sort((a, b) => (b.cheapest_price || 0) - (a.cheapest_price || 0));
        break;
      case 'stars_desc':
        result.sort((a, b) => (b.stars || 0) - (a.stars || 0));
        break;
      case 'name_asc':
        result.sort((a, b) => (a.hotel_name || '').localeCompare(b.hotel_name || ''));
        break;
      default:
        break;
    }

    return result;
  }, [hotels, filters, sortBy]);

  const clearFilters = () => {
    setFilters({
      stars: [],
      mealPlan: [],
      zone: [],
      priceMin: 0,
      priceMax: Infinity,
    });
  };

  // Room selector helpers
  const getTotalGuests = () => {
    return rooms.reduce((sum, room) => sum + room.adults + room.children, 0);
  };

  const getRoomSummary = () => {
    const totalRooms = rooms.length;
    const totalGuests = getTotalGuests();
    return `${totalRooms} ROOM${totalRooms > 1 ? 'S' : ''} / ${totalGuests} pers`;
  };

  const updateRoom = (index, field, value) => {
    const newRooms = [...rooms];
    newRooms[index] = { ...newRooms[index], [field]: Math.max(field === 'adults' ? 1 : 0, value) };
    setRooms(newRooms);
  };

  const addRoom = () => {
    if (rooms.length < 4) {
      setRooms([...rooms, { adults: 2, children: 0 }]);
    }
  };

  const removeRoom = (index) => {
    if (rooms.length > 1) {
      setRooms(rooms.filter((_, i) => i !== index));
    }
  };

  const loadDestinations = async () => {
    try {
      const response = await travelApi.destinations();
      if (response.data?.success) {
        setDestinations(response.data.destinations);
        if (response.data.destinations.length > 0) {
          setSelectedDestination(response.data.destinations[0].code);
        }
      }
    } catch (err) {
      console.error('Failed to load destinations:', err);
    }
  };

  const checkRatesHealth = async () => {
    try {
      const response = await hotelsApi.health();
      setRatesAvailable(response.data?.available || false);
    } catch {
      setRatesAvailable(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!selectedDestination || !checkIn || !checkOut) {
      setError('Please fill in all required fields');
      return;
    }

    setSearching(true);
    setError(null);
    setHotels([]);
    setSearchTime(null);
    clearFilters(); // Reset filters on new search

    // Calculate total adults from all rooms (API currently supports single room)
    const totalAdults = rooms.reduce((sum, room) => sum + room.adults, 0);
    const totalChildren = rooms.reduce((sum, room) => sum + room.children, 0);
    // Create children ages array (assume ages 8 for simplicity)
    const childrenAges = Array(totalChildren).fill(8);

    try {
      const response = await hotelsApi.search({
        destination: selectedDestination,
        check_in: checkIn,
        check_out: checkOut,
        adults: totalAdults,
        children_ages: childrenAges,
        max_hotels: 50 // Default to 50 for good performance
      });

      if (response.data?.success) {
        setHotels(response.data.hotels || []);
        setSearchTime(response.data.search_time_seconds);
      } else {
        setError(response.data?.error || 'Search failed');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to search hotels');
    } finally {
      setSearching(false);
    }
  };

  const formatCurrency = (amount, currency = 'ZAR') => {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const renderStars = (stars) => {
    const starCount = Math.floor(stars || 0);
    return (
      <div className="flex items-center">
        {[...Array(5)].map((_, i) => (
          i < starCount ? (
            <StarIconSolid key={i} className="h-4 w-4 text-yellow-400" />
          ) : (
            <StarIcon key={i} className="h-4 w-4 text-gray-300" />
          )
        ))}
      </div>
    );
  };

  const calculateNights = () => {
    if (!checkIn || !checkOut) return 0;
    const start = new Date(checkIn);
    const end = new Date(checkOut);
    return Math.ceil((end - start) / (1000 * 60 * 60 * 24));
  };

  // Detect encoded/garbled room type strings and replace with readable fallback
  const formatRoomType = (roomType) => {
    if (!roomType) return 'Standard Room';
    // Detect encoded Juniper room hashes: long strings with high density of Base64 chars
    if (roomType.length > 40 && /[+/=]{2,}/.test(roomType)) return 'Room';
    return roomType;
  };

  // Provider badge colors
  const getProviderStyle = (provider) => {
    const styles = {
      juniper: 'bg-blue-100 text-blue-700',
      hotelbeds: 'bg-orange-100 text-orange-700',
      hummingbird: 'bg-green-100 text-green-700',
      rttc: 'bg-purple-100 text-purple-700',
      default: 'bg-gray-100 text-gray-600'
    };
    return styles[provider?.toLowerCase()] || styles.default;
  };

  const activeFilterCount = [
    filters.stars.length,
    filters.mealPlan.length,
    filters.zone.length,
    filters.priceMin > 0 ? 1 : 0,
    filters.priceMax < Infinity ? 1 : 0,
  ].reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-theme">Hotels</h1>
          <p className="text-theme-muted mt-1">Search live hotel availability and pricing</p>
        </div>
        <div className="flex items-center gap-2">
          {ratesAvailable === true && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
              <CheckCircleIcon className="h-4 w-4" />
              Live Rates Available
            </span>
          )}
          {ratesAvailable === false && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
              <XCircleIcon className="h-4 w-4" />
              Rates Unavailable
            </span>
          )}
        </div>
      </div>

      {/* Search Form */}
      <div className="card p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Destination */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <MapPinIcon className="h-4 w-4 inline mr-1" />
                Destination
              </label>
              <select
                value={selectedDestination}
                onChange={(e) => setSelectedDestination(e.target.value)}
                className="input"
              >
                <option value="">Choose destination</option>
                {destinations.map((dest) => (
                  <option key={dest.code} value={dest.code}>
                    {dest.name}, {dest.country}
                  </option>
                ))}
              </select>
            </div>

            {/* Departure Date (Check-in) */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <CalendarIcon className="h-4 w-4 inline mr-1" />
                Departure date
              </label>
              <input
                type="date"
                value={checkIn}
                onChange={(e) => setCheckIn(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="input"
              />
            </div>

            {/* Return Date (Check-out) */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <CalendarIcon className="h-4 w-4 inline mr-1" />
                Return date
              </label>
              <input
                type="date"
                value={checkOut}
                onChange={(e) => setCheckOut(e.target.value)}
                min={checkIn || new Date().toISOString().split('T')[0]}
                className="input"
              />
            </div>

            {/* Room/Pax Selector */}
            <div className="relative" ref={roomSelectorRef}>
              <label className="block text-sm font-medium text-theme mb-1">
                <UserGroupIcon className="h-4 w-4 inline mr-1" />
                Rooms & Guests
              </label>
              <button
                type="button"
                onClick={() => setShowRoomSelector(!showRoomSelector)}
                className="input w-full text-left flex items-center justify-between"
              >
                <span className="font-medium">{getRoomSummary()}</span>
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${showRoomSelector ? 'rotate-180' : ''}`} />
              </button>

              {/* Room Selector Dropdown */}
              {showRoomSelector && (
                <div className="absolute z-50 mt-1 right-0 w-72 max-w-[calc(100vw-2rem)] bg-theme-surface rounded-lg shadow-lg border border-theme p-4 max-h-96 overflow-y-auto">
                  <div className="space-y-4">
                    {rooms.map((room, index) => (
                      <div key={index} className="pb-4 border-b border-theme-light last:border-0 last:pb-0">
                        <div className="flex items-center justify-between mb-3">
                          <span className="font-medium text-theme">Room {index + 1}</span>
                          {rooms.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeRoom(index)}
                              className="text-red-500 hover:text-red-700 text-sm"
                            >
                              Remove
                            </button>
                          )}
                        </div>

                        {/* Adults */}
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-theme-secondary">Adults</span>
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => updateRoom(index, 'adults', room.adults - 1)}
                              disabled={room.adults <= 1}
                              className="p-1 rounded-full border border-theme hover:bg-theme-border-light disabled:opacity-50"
                            >
                              <MinusIcon className="h-4 w-4" />
                            </button>
                            <span className="w-8 text-center font-medium">{room.adults}</span>
                            <button
                              type="button"
                              onClick={() => updateRoom(index, 'adults', room.adults + 1)}
                              disabled={room.adults >= 6}
                              className="p-1 rounded-full border border-theme hover:bg-theme-border-light disabled:opacity-50"
                            >
                              <PlusIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>

                        {/* Children */}
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-theme-secondary">Children</span>
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => updateRoom(index, 'children', room.children - 1)}
                              disabled={room.children <= 0}
                              className="p-1 rounded-full border border-theme hover:bg-theme-border-light disabled:opacity-50"
                            >
                              <MinusIcon className="h-4 w-4" />
                            </button>
                            <span className="w-8 text-center font-medium">{room.children}</span>
                            <button
                              type="button"
                              onClick={() => updateRoom(index, 'children', room.children + 1)}
                              disabled={room.children >= 4}
                              className="p-1 rounded-full border border-theme hover:bg-theme-border-light disabled:opacity-50"
                            >
                              <PlusIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Add Room Button */}
                    {rooms.length < 4 && (
                      <button
                        type="button"
                        onClick={addRoom}
                        className="w-full py-2 text-sm text-theme-primary hover:text-theme-primary-dark font-medium border border-dashed border-gray-300 rounded-lg hover:border-theme-primary"
                      >
                        + Add another room
                      </button>
                    )}

                    {/* Done Button */}
                    <button
                      type="button"
                      onClick={() => setShowRoomSelector(false)}
                      className="w-full py-2 bg-theme-primary text-white rounded-lg hover:bg-theme-primary-dark font-medium"
                    >
                      Done
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">
              {checkIn && checkOut && (
                <span>{calculateNights()} nights</span>
              )}
            </div>
            <button
              type="submit"
              disabled={searching || !ratesAvailable}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {searching ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Searching...
                </>
              ) : (
                <>
                  <MagnifyingGlassIcon className="h-4 w-4 mr-2" />
                  Search hotel
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Search Results */}
      {hotels.length > 0 && (
        <div className="flex gap-6">
          {/* Filter Sidebar - Desktop (visible at md+) */}
          <div className="hidden md:block w-64 flex-shrink-0">
            <FilterSidebar
              filters={filters}
              setFilters={setFilters}
              facets={facets}
              onClearFilters={clearFilters}
              isOpen={true}
              onClose={() => {}}
            />
          </div>

          {/* Results */}
          <div className="flex-1 space-y-4">
            {/* Results Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold text-theme">
                  {filteredHotels.length} of {hotels.length} Hotels
                </h2>
                {searchTime && (
                  <span className="text-sm text-theme-muted">
                    ({searchTime.toFixed(1)}s)
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3">
                {/* Mobile Filter Button */}
                <button
                  onClick={() => setShowMobileFilters(true)}
                  className="md:hidden flex items-center gap-2 px-3 py-2 border border-theme rounded-lg text-sm"
                >
                  <AdjustmentsHorizontalIcon className="h-4 w-4" />
                  Filters
                  {activeFilterCount > 0 && (
                    <span className="bg-theme-primary text-white text-xs px-1.5 py-0.5 rounded-full">
                      {activeFilterCount}
                    </span>
                  )}
                </button>

                {/* Sort Dropdown */}
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="input text-sm py-1.5"
                >
                  <option value="price_asc">Price: Low to High</option>
                  <option value="price_desc">Price: High to Low</option>
                  <option value="stars_desc">Star Rating</option>
                  <option value="name_asc">Name A-Z</option>
                </select>
              </div>
            </div>

            {/* Active Filters Pills */}
            {activeFilterCount > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {filters.stars.map((star) => (
                  <span
                    key={`star-${star}`}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-theme-primary/10 text-theme-primary rounded-full text-sm"
                  >
                    {star} stars
                    <button
                      onClick={() => setFilters((prev) => ({ ...prev, stars: prev.stars.filter((s) => s !== star) }))}
                      className="hover:text-theme-primary-dark"
                    >
                      <XMarkIcon className="h-3.5 w-3.5" />
                    </button>
                  </span>
                ))}
                {filters.mealPlan.map((plan) => (
                  <span
                    key={`meal-${plan}`}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-theme-primary/10 text-theme-primary rounded-full text-sm"
                  >
                    {plan}
                    <button
                      onClick={() => setFilters((prev) => ({ ...prev, mealPlan: prev.mealPlan.filter((m) => m !== plan) }))}
                      className="hover:text-theme-primary-dark"
                    >
                      <XMarkIcon className="h-3.5 w-3.5" />
                    </button>
                  </span>
                ))}
                {filters.zone.map((zone) => (
                  <span
                    key={`zone-${zone}`}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-theme-primary/10 text-theme-primary rounded-full text-sm"
                  >
                    {zone}
                    <button
                      onClick={() => setFilters((prev) => ({ ...prev, zone: prev.zone.filter((z) => z !== zone) }))}
                      className="hover:text-theme-primary-dark"
                    >
                      <XMarkIcon className="h-3.5 w-3.5" />
                    </button>
                  </span>
                ))}
                <button
                  onClick={clearFilters}
                  className="text-sm text-theme-muted hover:text-theme"
                >
                  Clear all
                </button>
              </div>
            )}

            {/* Hotel Cards */}
            {filteredHotels.length > 0 ? (
              <div className="grid gap-4">
                {filteredHotels.map((hotel) => (
                  <div
                    key={hotel.hotel_id}
                    className="card overflow-hidden hover:shadow-md transition-shadow"
                  >
                    <div className="flex">
                      {/* Hotel Image */}
                      <div className="w-48 h-40 flex-shrink-0 cursor-pointer" onClick={() => setSelectedHotel(hotel)}>
                        {hotel.image_url ? (
                          <img
                            src={hotel.image_url}
                            alt={hotel.hotel_name}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.target.src = 'https://via.placeholder.com/200x160?text=No+Image';
                            }}
                          />
                        ) : (
                          <div className="w-full h-full bg-gray-200 flex items-center justify-center">
                            <BuildingOfficeIcon className="h-12 w-12 text-gray-400" />
                          </div>
                        )}
                      </div>

                      {/* Hotel Info */}
                      <div className="flex-1 p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h3 className="text-lg font-semibold text-theme cursor-pointer hover:text-theme-primary" onClick={() => setSelectedHotel(hotel)}>
                                {hotel.hotel_name}
                              </h3>
                              {(hotel.source || hotel.provider) && (
                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getProviderStyle(hotel.source || hotel.provider)}`}>
                                  {(hotel.source || hotel.provider).toUpperCase()}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                              {renderStars(hotel.stars)}
                              {hotel.zone && (
                                hotel.latitude && hotel.longitude ? (
                                  <a
                                    href={`https://www.google.com/maps?q=${hotel.latitude},${hotel.longitude}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-theme-primary hover:text-theme-primary-dark inline-flex items-center gap-0.5"
                                    title="Open in Google Maps"
                                  >
                                    <MapPinIcon className="h-4 w-4" /> {hotel.zone}
                                  </a>
                                ) : (
                                  <span className="text-sm text-gray-500">
                                    <MapPinIcon className="h-4 w-4 inline" /> {hotel.zone}
                                  </span>
                                )
                              )}
                              {hotel.address && !hotel.zone && (
                                <span className="text-sm text-gray-500 truncate">
                                  <MapPinIcon className="h-4 w-4 inline" /> {hotel.address}
                                </span>
                              )}
                            </div>

                            {/* Description */}
                            {hotel.description && (
                              <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                                {hotel.description}
                              </p>
                            )}

                            {/* Amenities */}
                            {hotel.amenities && hotel.amenities.length > 0 && (
                              <div className="flex items-center gap-2 mt-2 flex-wrap">
                                {hotel.amenities.slice(0, 6).map((amenity, i) => (
                                  <span
                                    key={i}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                                    title={amenity}
                                  >
                                    {amenity.toLowerCase().includes('wifi') || amenity.toLowerCase().includes('internet') ? (
                                      <WifiIcon className="h-3 w-3" />
                                    ) : amenity.toLowerCase().includes('pool') || amenity.toLowerCase().includes('swim') ? (
                                      <GlobeAltIcon className="h-3 w-3" />
                                    ) : null}
                                    {amenity}
                                  </span>
                                ))}
                                {hotel.amenities.length > 6 && (
                                  <span className="text-xs text-gray-400">+{hotel.amenities.length - 6} more</span>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="text-right ml-4 flex-shrink-0">
                            <div className="text-2xl font-bold text-theme-primary">
                              {formatCurrency(hotel.cheapest_price, hotel.options?.[0]?.currency || 'ZAR')}
                            </div>
                            <div className="text-sm text-gray-500">
                              total {hotel.cheapest_meal_plan ? `\u00b7 ${hotel.cheapest_meal_plan}` : ''}
                            </div>
                          </div>
                        </div>

                        {/* Room Options Summary */}
                        <div className="mt-3 flex items-center justify-between">
                          <button
                            onClick={() => setExpandedHotel(expandedHotel === hotel.hotel_id ? null : hotel.hotel_id)}
                            className="text-sm text-theme-primary hover:text-theme-primary-dark"
                          >
                            {hotel.options?.length || 0} room options available
                            {expandedHotel === hotel.hotel_id ? ' (hide)' : ' (show)'}
                          </button>
                          {/* Quick Add - adds cheapest option */}
                          <AddToQuoteButton
                            item={{
                              id: `${hotel.hotel_id}-${hotel.options?.[0]?.room_type || 'default'}`,
                              type: 'hotel',
                              name: hotel.hotel_name,
                              price: hotel.cheapest_price,
                              currency: hotel.options?.[0]?.currency || 'EUR',
                              details: {
                                hotel_id: hotel.hotel_id,
                                room_type: hotel.options?.[0]?.room_type || 'Standard Room',
                                meal_plan: hotel.cheapest_meal_plan,
                                stars: hotel.stars,
                                check_in: checkIn,
                                check_out: checkOut,
                                image_url: hotel.image_url,
                              }
                            }}
                            size="sm"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Expanded Room Options */}
                    {expandedHotel === hotel.hotel_id && hotel.options && (
                      <div className="border-t border-gray-200 bg-gray-50 p-4">
                        <div className="grid gap-2">
                          {(showAllOptions[hotel.hotel_id] ? hotel.options : hotel.options.slice(0, 10)).map((option, idx) => (
                            <div
                              key={idx}
                              className="bg-white rounded-md p-3 border border-gray-200"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-medium text-gray-900">{formatRoomType(option.room_type)}</span>
                                    <span className="text-gray-400">&middot;</span>
                                    <span className="text-gray-600">{option.meal_plan}</span>
                                    {/* Provider badge */}
                                    {option.provider && (
                                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                                        option.provider === 'hotelbeds'
                                          ? 'bg-orange-100 text-orange-700'
                                          : option.provider === 'juniper'
                                            ? 'bg-blue-100 text-blue-700'
                                            : 'bg-gray-100 text-gray-600'
                                      }`}>
                                        {option.provider === 'hotelbeds' ? 'HotelBeds' :
                                         option.provider === 'juniper' ? 'Juniper' :
                                         option.provider}
                                      </span>
                                    )}
                                    {/* Cancellation badge */}
                                    {option.refundable !== undefined && option.refundable !== null && (
                                      option.refundable ? (
                                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                                          <CheckCircleIcon className="h-3 w-3" /> Free cancellation
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
                                          <XCircleIcon className="h-3 w-3" /> Non-refundable
                                        </span>
                                      )
                                    )}
                                    {option.cancellation_policy && option.refundable === undefined && (
                                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                        <ShieldCheckIcon className="h-3 w-3" /> {option.cancellation_policy}
                                      </span>
                                    )}
                                  </div>
                                  {/* Room details line */}
                                  {(option.bed_type || option.view || option.room_size || option.room_description) && (
                                    <div className="text-xs text-gray-500 mt-1 flex items-center gap-2 flex-wrap">
                                      {option.bed_type && <span>{option.bed_type}</span>}
                                      {option.view && <><span className="text-gray-300">&middot;</span><span>{option.view}</span></>}
                                      {option.room_size && <><span className="text-gray-300">&middot;</span><span>{option.room_size}</span></>}
                                      {option.room_description && !option.bed_type && !option.view && (
                                        <span className="truncate max-w-xs">{option.room_description}</span>
                                      )}
                                    </div>
                                  )}
                                </div>
                                <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                                  <div className="text-right">
                                    <span className="font-semibold text-gray-900">
                                      {formatCurrency(option.price_total, option.currency)}
                                    </span>
                                    <span className="text-sm text-gray-500 ml-2">
                                      ({formatCurrency(option.price_per_night, option.currency)}/night)
                                    </span>
                                  </div>
                                  <AddToQuoteButton
                                    item={{
                                      id: `${hotel.hotel_id}-${option.room_type}-${option.meal_plan}`,
                                      type: 'hotel',
                                      name: hotel.hotel_name,
                                      price: option.price_total,
                                      currency: option.currency,
                                      details: {
                                        hotel_id: hotel.hotel_id,
                                        room_type: option.room_type,
                                        meal_plan: option.meal_plan,
                                        price_per_night: option.price_per_night,
                                        stars: hotel.stars,
                                        check_in: checkIn,
                                        check_out: checkOut,
                                        image_url: hotel.image_url,
                                      }
                                    }}
                                    size="sm"
                                  />
                                </div>
                              </div>
                            </div>
                          ))}
                          {hotel.options.length > 10 && (
                            <button
                              onClick={() => setShowAllOptions(prev => ({
                                ...prev,
                                [hotel.hotel_id]: !prev[hotel.hotel_id]
                              }))}
                              className="w-full text-sm text-theme-primary hover:text-theme-primary-dark font-medium py-2 hover:bg-gray-100 rounded-md transition-colors"
                            >
                              {showAllOptions[hotel.hotel_id]
                                ? 'Show less'
                                : `Show all ${hotel.options.length} options`}
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="card p-8 text-center">
                <FunnelIcon className="mx-auto h-12 w-12 text-theme-muted" />
                <h3 className="mt-4 text-lg font-medium text-theme">No hotels match your filters</h3>
                <p className="mt-2 text-theme-muted">
                  Try adjusting your filters or clearing them to see more results.
                </p>
                <button
                  onClick={clearFilters}
                  className="mt-4 btn-secondary"
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Mobile Filter Sidebar */}
      <FilterSidebar
        filters={filters}
        setFilters={setFilters}
        facets={facets}
        onClearFilters={clearFilters}
        isOpen={showMobileFilters}
        onClose={() => setShowMobileFilters(false)}
      />

      {/* Empty State */}
      {!searching && hotels.length === 0 && !error && (
        <div className="card p-12 text-center">
          <BuildingOfficeIcon className="mx-auto h-12 w-12 text-theme-muted" />
          <h3 className="mt-4 text-lg font-medium text-theme">Search for Hotels</h3>
          <p className="mt-2 text-theme-muted">
            Select a destination and dates to see live hotel availability and pricing.
          </p>
        </div>
      )}

      {/* Loading State */}
      {searching && (
        <div className="card p-12 text-center">
          <svg className="animate-spin mx-auto h-12 w-12 text-theme-primary" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <h3 className="mt-4 text-lg font-medium text-theme">Searching Hotels...</h3>
          <p className="mt-2 text-theme-muted">
            This may take 30-60 seconds as we query live availability.
          </p>
        </div>
      )}

      {selectedHotel && (
        <HotelDetailModal
          hotel={selectedHotel}
          onClose={() => setSelectedHotel(null)}
          formatCurrency={formatCurrency}
          renderStars={renderStars}
          formatRoomType={formatRoomType}
          getProviderStyle={getProviderStyle}
          checkIn={checkIn}
          checkOut={checkOut}
          calculateNights={calculateNights}
        />
      )}
    </div>
  );
}
