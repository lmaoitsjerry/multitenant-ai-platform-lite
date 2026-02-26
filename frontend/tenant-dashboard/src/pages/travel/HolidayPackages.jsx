import { useState, useEffect, useRef } from 'react';
import {
  GlobeAltIcon,
  MagnifyingGlassIcon,
  CalendarIcon,
  UserGroupIcon,
  MapPinIcon,
  PaperAirplaneIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  MinusIcon,
  PlusIcon,
  BuildingOfficeIcon,
  InformationCircleIcon,
  ArrowPathIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import { hotelsApi, flightsApi, activitiesApi, transfersApi, travelApi } from '../../services/api';
import { AddToQuoteButton } from '../../components/travel/FloatingQuoteCart';

// Departure airports for South African travelers
const DEPARTURE_AIRPORTS = [
  { code: 'JNB', name: 'Johannesburg (OR Tambo)', city: 'Johannesburg' },
  { code: 'CPT', name: 'Cape Town International', city: 'Cape Town' },
  { code: 'DUR', name: 'King Shaka (Durban)', city: 'Durban' },
];

export default function HolidayPackages() {
  // State
  const [destinations, setDestinations] = useState([]);
  const [selectedDeparture, setSelectedDeparture] = useState('JNB');
  const [selectedDestination, setSelectedDestination] = useState('');
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [directFlightsOnly, setDirectFlightsOnly] = useState(false);

  // Room/Pax state
  const [rooms, setRooms] = useState([{ adults: 2, children: 0 }]);
  const [showRoomSelector, setShowRoomSelector] = useState(false);
  const roomSelectorRef = useRef(null);

  // Results state
  const [hotels, setHotels] = useState([]);
  const [flights, setFlights] = useState([]);
  const [activities, setActivities] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [searching, setSearching] = useState(false);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [transfersLoading, setTransfersLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hotelError, setHotelError] = useState(null); // Hotel-specific error (non-fatal when other tabs have data)
  const [searchTime, setSearchTime] = useState(null);
  const [ratesAvailable, setRatesAvailable] = useState(null);
  const [flightsAvailable, setFlightsAvailable] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeTab, setActiveTab] = useState('hotels');
  const [expandedHotel, setExpandedHotel] = useState(null);
  const [showAllOptions, setShowAllOptions] = useState({}); // Track which hotels show all options
  const [aggregation, setAggregation] = useState(null); // Multi-provider aggregation metadata

  // Load destinations on mount
  useEffect(() => {
    loadDestinations();
    checkRatesHealth();
  }, []);

  // Set default dates
  useEffect(() => {
    const today = new Date();
    const nextMonth = new Date(today);
    nextMonth.setDate(today.getDate() + 30);
    const returnDate = new Date(nextMonth);
    returnDate.setDate(nextMonth.getDate() + 7);

    setCheckIn(nextMonth.toISOString().split('T')[0]);
    setCheckOut(returnDate.toISOString().split('T')[0]);
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

  const loadDestinations = async () => {
    try {
      const response = await travelApi.destinations();
      if (response.data?.success) {
        setDestinations(response.data.destinations);
        if (response.data.destinations.length > 0) {
          setSelectedDestination(response.data.destinations[0].code);
        }
      }
    } catch {
      console.error('Failed to load destinations');
    }
  };

  const checkRatesHealth = async () => {
    try {
      const response = await hotelsApi.health();
      // Treat both true and null as potentially available (cold start handling)
      const available = response.data?.available;
      setRatesAvailable(available !== false);
    } catch {
      // On error, assume potentially available (don't block UI on network issues)
      setRatesAvailable(null);
    }
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

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!selectedDestination || !checkIn || !checkOut) {
      setError('Please fill in all required fields');
      return;
    }

    setSearching(true);
    setActivitiesLoading(true);
    setTransfersLoading(true);
    setError(null);
    setHotelError(null);
    setHotels([]);
    setFlights([]);
    setActivities([]);
    setTransfers([]);
    setSearchTime(null);
    setHasSearched(true);
    setActiveTab('hotels');

    const totalAdults = rooms.reduce((sum, room) => sum + room.adults, 0);
    const totalChildren = rooms.reduce((sum, room) => sum + room.children, 0);
    const childrenAges = Array(totalChildren).fill(8);

    try {
      // Search hotels, flights, activities, and transfers in parallel
      const [hotelResponse, flightResponse, activitiesResponse, transfersResponse] = await Promise.all([
        hotelsApi.searchAggregated({
          destination: selectedDestination,
          check_in: checkIn,
          check_out: checkOut,
          adults: totalAdults,
          children: totalChildren,
        }).catch(() =>
          // Fall back to standard Juniper-only search if aggregated fails
          hotelsApi.search({
            destination: selectedDestination,
            check_in: checkIn,
            check_out: checkOut,
            adults: totalAdults,
            children_ages: childrenAges,
            max_hotels: 50
          })
        ),
        flightsApi.search(selectedDestination, checkIn, checkOut).catch(() => ({ data: { success: false, flights: [] } })),
        activitiesApi.search(selectedDestination).catch(() => ({ data: { success: false, activities: [] } })),
        transfersApi.search(selectedDestination).catch(() => ({ data: { success: false, transfers: [] } }))
      ]);

      // Process hotel results
      let hotelsOk = false;
      if (hotelResponse.data?.success) {
        setHotels(hotelResponse.data.hotels || []);
        setSearchTime(hotelResponse.data.search_time_seconds);
        setAggregation(hotelResponse.data.aggregation || null);
        hotelsOk = (hotelResponse.data.hotels || []).length > 0;
      } else {
        // Store hotel error separately — don't block other tabs
        setHotelError(hotelResponse.data?.error || 'Hotel search failed');
        setAggregation(null);
      }

      // Process flight results (graceful handling)
      let flightsOk = false;
      if (flightResponse.data?.success && flightResponse.data?.flights?.length > 0) {
        let flightResults = flightResponse.data.flights;

        // Apply direct flights filter (client-side) if enabled
        if (directFlightsOnly) {
          flightResults = flightResults.filter(f => !f.stops || f.stops === 0);
        }

        setFlights(flightResults);
        setFlightsAvailable(true);
        flightsOk = flightResults.length > 0;
      } else {
        setFlights([]);
        setFlightsAvailable(false);
      }

      // Process activities results
      let activitiesOk = false;
      if (activitiesResponse.data?.success && activitiesResponse.data?.activities?.length > 0) {
        setActivities(activitiesResponse.data.activities);
        activitiesOk = true;
      } else {
        setActivities([]);
      }
      setActivitiesLoading(false);

      // Process transfers results
      let transfersOk = false;
      if (transfersResponse.data?.success && transfersResponse.data?.transfers?.length > 0) {
        setTransfers(transfersResponse.data.transfers);
        transfersOk = true;
      } else {
        setTransfers([]);
      }
      setTransfersLoading(false);

      // Auto-switch to first tab with results if hotels failed
      if (!hotelsOk) {
        if (flightsOk) setActiveTab('flights');
        else if (activitiesOk) setActiveTab('activities');
        else if (transfersOk) setActiveTab('transfers');
      }

      // Only show global error if ALL tabs failed
      if (!hotelsOk && !flightsOk && !activitiesOk && !transfersOk) {
        setError(hotelResponse.data?.error || 'No results found. Please try different dates or destination.');
      }

    } catch (err) {
      const statusCode = err.response?.status;
      const errorMsg = err.response?.data?.error;

      if (statusCode === 504 || err.code === 'ECONNABORTED') {
        setError('Search is taking longer than expected. The rates service may be starting up. Please try again in a moment.');
      } else if (statusCode === 503 || statusCode === 502) {
        setError('The hotel rates service is temporarily unavailable. Please try again in a few moments.');
      } else if (err.message?.includes('timeout')) {
        setError('Search timed out. The rates service may be handling a lot of requests. Please try again.');
      } else {
        setError(errorMsg || 'Search failed. Please try again.');
      }
    } finally {
      setSearching(false);
      setActivitiesLoading(false);
      setTransfersLoading(false);
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
          <StarIconSolid
            key={i}
            className={`h-4 w-4 ${i < starCount ? 'text-yellow-400' : 'text-gray-300'}`}
          />
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

  // Toggle show all options for a hotel
  const toggleShowAllOptions = (hotelId) => {
    setShowAllOptions(prev => ({
      ...prev,
      [hotelId]: !prev[hotelId]
    }));
  };

  const VISIBLE_OPTIONS_COUNT = 6;

  // Detect encoded/garbled room type strings and replace with readable fallback
  const formatRoomType = (roomType) => {
    if (!roomType) return 'Standard Room';
    // Detect encoded Juniper room hashes: long strings with high density of Base64 chars
    if (roomType.length > 40 && /[+/=]{2,}/.test(roomType)) return 'Room';
    return roomType;
  };

  // Filter out zero-price hotels
  const displayHotels = hotels.filter(h => h.cheapest_price > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-theme">Holiday Packages</h1>
          <p className="text-theme-muted mt-1">Search flights and hotels together for the best deals</p>
        </div>
        <div className="flex items-center gap-2">
          {ratesAvailable === true && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
              <CheckCircleIcon className="h-4 w-4" />
              Hotels Available
            </span>
          )}
          {ratesAvailable === false && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800">
              <InformationCircleIcon className="h-4 w-4" />
              Service Starting
            </span>
          )}
          {ratesAvailable === null && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-600">
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
              Checking...
            </span>
          )}
        </div>
      </div>

      {/* Search Form */}
      <div className="card p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Departure Airport */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <PaperAirplaneIcon className="h-4 w-4 inline mr-1" />
                Departure
              </label>
              <select
                value={selectedDeparture}
                onChange={(e) => setSelectedDeparture(e.target.value)}
                className="input"
              >
                <option value="">Choose departure</option>
                {DEPARTURE_AIRPORTS.map((airport) => (
                  <option key={airport.code} value={airport.code}>
                    {airport.name}
                  </option>
                ))}
              </select>
            </div>

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

            {/* Departure Date */}
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

            {/* Return Date */}
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
                              className="p-1 rounded-full border border-gray-300 hover:bg-gray-100 disabled:opacity-50"
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

          {/* Direct Flights Checkbox & Search Button */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={directFlightsOnly}
                  onChange={(e) => setDirectFlightsOnly(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-theme-primary focus:ring-theme-primary"
                />
                <span className="text-sm font-medium text-gray-700 uppercase tracking-wide">
                  Only direct flights
                </span>
              </label>
              {checkIn && checkOut && (
                <span className="text-sm text-gray-500">
                  {calculateNights()} nights
                </span>
              )}
            </div>
            <button
              type="submit"
              disabled={searching}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed px-8"
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
                  Search offers
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

      {/* Direct Flights Notice */}
      {hasSearched && directFlightsOnly && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <InformationCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-blue-800">Direct flights filter</h4>
              <p className="text-sm text-blue-700 mt-1">
                The "direct flights only" filter will be applied to search results when flight data becomes available.
                Currently showing all hotel options.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      {hasSearched && !searching && (
        <div className="border-b border-gray-200">
          <nav className="flex gap-4">
            {[
              { id: 'hotels', label: 'Hotels', count: displayHotels.length },
              { id: 'flights', label: 'Flights', count: flights.length },
              { id: 'activities', label: 'Activities', count: activities.length },
              { id: 'transfers', label: 'Transfers', count: transfers.length },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-theme-primary text-theme-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label} {tab.count > 0 && <span className="ml-1 text-xs bg-gray-100 px-2 py-0.5 rounded-full">{tab.count}</span>}
              </button>
            ))}
          </nav>
        </div>
      )}

      {/* Search Results */}
      {activeTab === 'hotels' && displayHotels.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-theme">
                {displayHotels.length} Hotels Found
              </h2>
              {aggregation?.by_provider && (
                <div className="flex items-center gap-1.5">
                  {Object.entries(aggregation.by_provider).map(([provider, count]) => (
                    <span key={provider} className={`px-2 py-0.5 rounded-full text-xs font-medium ${getProviderStyle(provider)}`}>
                      {provider.toUpperCase()}: {count}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {searchTime && (
              <span className="text-sm text-theme-muted">
                Search completed in {searchTime.toFixed(1)}s
              </span>
            )}
          </div>

          <div className="grid gap-4">
            {displayHotels.map((hotel) => (
              <div
                key={hotel.hotel_id}
                className="card overflow-hidden hover:shadow-md transition-shadow"
              >
                <div className="flex">
                  {/* Hotel Image */}
                  <div className="w-48 h-40 flex-shrink-0">
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
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold text-theme">
                            {hotel.hotel_name}
                          </h3>
                          {/* Provider Badge */}
                          {(hotel.source || hotel.provider) && (
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getProviderStyle(hotel.source || hotel.provider)}`}>
                              {(hotel.source || hotel.provider).toUpperCase()}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          {renderStars(hotel.stars)}
                          {hotel.zone && (
                            <span className="text-sm text-gray-500">
                              <MapPinIcon className="h-4 w-4 inline" /> {hotel.zone}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-theme-primary">
                          {formatCurrency(hotel.cheapest_price, hotel.options?.[0]?.currency || 'ZAR')}
                        </div>
                        <div className="text-sm text-gray-500">
                          hotel only • {hotel.cheapest_meal_plan}
                        </div>
                        <div className="mt-2">
                          <AddToQuoteButton
                            item={{
                              id: hotel.hotel_id,
                              type: 'hotel',
                              name: hotel.hotel_name,
                              price: hotel.cheapest_price,
                              currency: hotel.options?.[0]?.currency || 'ZAR',
                              details: {
                                stars: hotel.stars,
                                zone: hotel.zone,
                                room_type: hotel.options?.[0]?.room_type,
                                meal_plan: hotel.cheapest_meal_plan,
                                check_in: checkIn,
                                check_out: checkOut,
                                nights: calculateNights(),
                                destination: selectedDestination,
                              }
                            }}
                            size="sm"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Room Options Summary */}
                    <div className="mt-3">
                      <button
                        onClick={() => setExpandedHotel(expandedHotel === hotel.hotel_id ? null : hotel.hotel_id)}
                        className="text-sm text-theme-primary hover:text-theme-primary-dark"
                      >
                        {hotel.options?.length || 0} room options available
                        {expandedHotel === hotel.hotel_id ? ' (hide)' : ' (show)'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Room Options */}
                {expandedHotel === hotel.hotel_id && hotel.options && (
                  <div className="border-t border-gray-200 bg-gray-50 p-4">
                    <div className="grid gap-2">
                      {(showAllOptions[hotel.hotel_id]
                        ? hotel.options
                        : hotel.options.slice(0, VISIBLE_OPTIONS_COUNT)
                      ).map((option, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between bg-white rounded-lg p-3 border border-gray-200 hover:border-gray-300 transition-colors"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-gray-900">{formatRoomType(option.room_type)}</span>
                              <span className="text-gray-400">•</span>
                              <span className="text-gray-600">{option.meal_plan}</span>
                              {/* Provider badge on rate */}
                              {(option.source || option.provider || hotel.source || hotel.provider) && (
                                <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${getProviderStyle(option.source || option.provider || hotel.source || hotel.provider)}`}>
                                  {(option.source || option.provider || hotel.source || hotel.provider).toUpperCase()}
                                </span>
                              )}
                            </div>
                            {/* Additional details row */}
                            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                              {option.bed_type && (
                                <span>{option.bed_type}</span>
                              )}
                              {option.cancellation_policy && (
                                <span className={`px-1.5 py-0.5 rounded ${
                                  option.cancellation_policy.toLowerCase().includes('free')
                                    ? 'bg-green-50 text-green-700'
                                    : option.cancellation_policy.toLowerCase().includes('non')
                                    ? 'bg-red-50 text-red-700'
                                    : 'bg-gray-50 text-gray-600'
                                }`}>
                                  {option.cancellation_policy}
                                </span>
                              )}
                              {option.board_basis && option.board_basis !== option.meal_plan && (
                                <span className="text-gray-400">{option.board_basis}</span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-3 ml-4">
                            <div className="text-right">
                              <span className="font-semibold text-gray-900">
                                {formatCurrency(option.price_total, option.currency)}
                              </span>
                              <div className="text-sm text-gray-500">
                                {formatCurrency(option.price_per_night, option.currency)}/night
                              </div>
                            </div>
                            <AddToQuoteButton
                              item={{
                                id: `${hotel.hotel_id}-${idx}`,
                                type: 'hotel',
                                name: hotel.hotel_name,
                                price: option.price_total,
                                currency: option.currency || 'ZAR',
                                details: {
                                  stars: hotel.stars,
                                  zone: hotel.zone,
                                  room_type: option.room_type,
                                  meal_plan: option.meal_plan,
                                  check_in: checkIn,
                                  check_out: checkOut,
                                  nights: calculateNights(),
                                  destination: selectedDestination,
                                  price_per_night: option.price_per_night,
                                  provider: option.source || option.provider || hotel.source || hotel.provider,
                                }
                              }}
                              size="sm"
                            />
                          </div>
                        </div>
                      ))}

                      {/* Show All / Show Less Toggle */}
                      {hotel.options.length > VISIBLE_OPTIONS_COUNT && (
                        <button
                          onClick={() => toggleShowAllOptions(hotel.hotel_id)}
                          className="w-full py-3 text-center text-theme-primary hover:text-theme-primary-dark font-medium border-t border-gray-100 transition-colors mt-2"
                        >
                          {showAllOptions[hotel.hotel_id]
                            ? 'Show less'
                            : `+ Show all ${hotel.options.length - VISIBLE_OPTIONS_COUNT} more options`
                          }
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hotels Empty State (tab-specific) */}
      {activeTab === 'hotels' && !searching && displayHotels.length === 0 && hasSearched && !error && (
        <div className="card p-12 text-center">
          <BuildingOfficeIcon className="mx-auto h-12 w-12 text-theme-muted" />
          <h3 className="mt-4 text-lg font-medium text-theme">No Hotels Found</h3>
          <p className="mt-2 text-theme-muted max-w-md mx-auto">
            {hotelError
              ? `Hotel search encountered an issue: ${hotelError}. Try different dates or check back later.`
              : 'No hotels are available for your selected dates and destination. Try different dates or another destination.'}
          </p>
        </div>
      )}

      {/* Flights Tab */}
      {activeTab === 'flights' && hasSearched && !searching && (
        flights.length > 0 ? (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-theme">{flights.length} Flights Found</h2>
            <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Airline</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Departure</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Return</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Price/Person</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {flights.map((flight, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{flight.airline || 'Various'}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{flight.departure_date ? new Date(flight.departure_date).toLocaleDateString() : '-'}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{flight.return_date ? new Date(flight.return_date).toLocaleDateString() : '-'}</td>
                      <td className="px-6 py-4 text-sm text-right font-semibold text-blue-600">{formatCurrency(flight.price_per_person, flight.currency)}</td>
                      <td className="px-6 py-4 text-right">
                        <AddToQuoteButton item={{ id: `flight-${idx}`, type: 'flight', name: `${flight.airline || 'Flight'} to ${selectedDestination}`, price: flight.price_per_person, currency: flight.currency || 'ZAR', details: { airline: flight.airline, destination: selectedDestination, departure_date: flight.departure_date, return_date: flight.return_date } }} size="sm" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="card p-8 text-center">
            <PaperAirplaneIcon className="mx-auto h-10 w-10 text-gray-400" />
            <p className="mt-2 text-gray-500">No flights available for this route</p>
          </div>
        )
      )}

      {/* Activities Tab */}
      {activeTab === 'activities' && hasSearched && !searching && (
        activities.length > 0 ? (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-theme">{activities.length} Activities Found</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activities.map((activity) => (
                <div key={activity.activity_id} className="card overflow-hidden hover:shadow-md transition-shadow">
                  {activity.image_url && (
                    <img src={activity.image_url} alt={activity.name} className="w-full h-40 object-cover" onError={(e) => { e.target.style.display = 'none'; }} />
                  )}
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900">{activity.name}</h3>
                    {activity.description && <p className="text-sm text-gray-600 mt-1 line-clamp-2">{activity.description}</p>}
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                      <span className="font-semibold text-theme-primary">
                        {(activity.price_per_person || activity.price_adult) > 0 ? formatCurrency(activity.price_per_person || activity.price_adult, activity.currency) : 'Price on request'}
                      </span>
                      {(activity.price_per_person || activity.price_adult) > 0 && (
                        <AddToQuoteButton item={{ id: activity.activity_id, type: 'activity', name: activity.name, price: activity.price_per_person || activity.price_adult, currency: activity.currency || 'EUR', details: { category: activity.category, destination: selectedDestination } }} size="sm" />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="card p-8 text-center">
            <SparklesIcon className="mx-auto h-10 w-10 text-gray-400" />
            <p className="mt-2 text-gray-500">No activities available for this destination</p>
          </div>
        )
      )}

      {/* Transfers Tab */}
      {activeTab === 'transfers' && hasSearched && !searching && (
        transfers.length > 0 ? (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-theme">{transfers.length} Transfers Found</h2>
            <div className="grid gap-3">
              {transfers.map((transfer, idx) => (
                <div key={idx} className="card p-4 flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">{transfer.name || transfer.type || 'Airport Transfer'}</h3>
                    <p className="text-sm text-gray-500">{transfer.description || `${transfer.from || 'Airport'} → ${transfer.to || 'Hotel'}`}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-theme-primary">
                      {transfer.price > 0 ? formatCurrency(transfer.price, transfer.currency) : 'Price on request'}
                    </span>
                    {transfer.price > 0 && (
                      <AddToQuoteButton item={{ id: `transfer-${idx}`, type: 'transfer', name: transfer.name || 'Airport Transfer', price: transfer.price, currency: transfer.currency || 'ZAR', details: { type: transfer.type, destination: selectedDestination } }} size="sm" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="card p-8 text-center">
            <MapPinIcon className="mx-auto h-10 w-10 text-gray-400" />
            <p className="mt-2 text-gray-500">No transfers available for this destination</p>
          </div>
        )
      )}

      {/* Empty State (before any search) */}
      {!searching && hotels.length === 0 && !error && !hasSearched && (
        <div className="card p-12 text-center">
          <GlobeAltIcon className="mx-auto h-12 w-12 text-theme-muted" />
          <h3 className="mt-4 text-lg font-medium text-theme">Search Holiday Packages</h3>
          <p className="mt-2 text-theme-muted max-w-md mx-auto">
            Select your departure city, destination, and dates to find available holiday packages with flights and hotels.
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
          <h3 className="mt-4 text-lg font-medium text-theme">Searching Packages...</h3>
          <p className="mt-2 text-theme-muted">
            Checking availability for hotels, flights, activities, and transfers. This may take 30-60 seconds.
          </p>
        </div>
      )}
    </div>
  );
}
