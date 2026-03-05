import { useState, useEffect, useMemo } from 'react';
import {
  PaperAirplaneIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  CalendarIcon,
  UserGroupIcon,
  ArrowsRightLeftIcon,
  ClockIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { flightsApi, travelApi } from '../../services/api';
import { getDestinationIata, DESTINATION_IATA } from '../../utils/destinations';

// Hardcoded flight destinations fallback when Cloud Run is unavailable
const FALLBACK_FLIGHT_DESTINATIONS = [
  { code: 'zanzibar', name: 'Zanzibar', country: 'Tanzania', flights: true },
  { code: 'mauritius', name: 'Mauritius', country: 'Mauritius', flights: true },
  { code: 'maldives', name: 'Maldives', country: 'Maldives', flights: true },
  { code: 'kenya', name: 'Kenya', country: 'Kenya', flights: true },
  { code: 'seychelles', name: 'Seychelles', country: 'Seychelles', flights: true },
  { code: 'cape-town', name: 'Cape Town', country: 'South Africa', flights: true },
  { code: 'durban', name: 'Durban', country: 'South Africa', flights: true },
];

// Cabin class options
const CABIN_CLASSES = [
  { value: 'economy', label: 'Economy' },
  { value: 'premium_economy', label: 'Premium Economy' },
  { value: 'business', label: 'Business' },
  { value: 'first', label: 'First Class' },
];

// Stop filter options
const STOP_FILTERS = [
  { value: 'all', label: 'Any stops' },
  { value: '0', label: 'Non-stop' },
  { value: '1', label: '1 stop' },
  { value: '2+', label: '2+ stops' },
];

// Sort options
const SORT_OPTIONS = [
  { value: 'price_asc', label: 'Price: Low to High' },
  { value: 'price_desc', label: 'Price: High to Low' },
  { value: 'duration', label: 'Duration: Shortest' },
  { value: 'departure', label: 'Departure: Earliest' },
];

/**
 * Fix duplicated/malformed duration strings from upstream RTTC API.
 *
 * Real examples from the API:
 *   "04h04,04H04,04h04,04H04" → "4h 04m"
 *   "14h 25m14h 25m"          → "14h 25m"
 *   "02h30"                   → "2h 30m"
 *
 * Strategy: split on commas, normalize case, deduplicate, then clean up format.
 */
function formatDuration(dur) {
  if (!dur || typeof dur !== 'string') return dur;

  let val = dur.trim();
  if (!val) return val;

  // Step 1: If comma-separated, split and deduplicate (case-insensitive)
  if (val.includes(',')) {
    const segments = val.split(',').map(s => s.trim().toLowerCase());
    const unique = [...new Set(segments)].filter(Boolean);
    val = unique[0] || val; // take the first unique value
  }

  // Step 2: Lowercase for uniform handling
  val = val.toLowerCase().trim();

  // Step 3: Handle exact-half duplication without separator: "14h 25m14h 25m"
  const half = Math.floor(val.length / 2);
  if (half > 0 && val.length % 2 === 0 && val.substring(0, half) === val.substring(half)) {
    val = val.substring(0, half);
  }

  // Step 4: Handle space-separated duplication: "14h 25m 14h 25m"
  const spaceParts = val.split(/\s+/);
  if (spaceParts.length >= 4 && spaceParts.length % 2 === 0) {
    const first = spaceParts.slice(0, spaceParts.length / 2).join(' ');
    const second = spaceParts.slice(spaceParts.length / 2).join(' ');
    if (first === second) val = first;
  }

  // Step 5: Parse hours and minutes from patterns like "04h04", "4h30m", "14h 25m"
  const match = val.match(/(\d+)\s*h\s*(\d+)\s*m?/i);
  if (match) {
    const hours = parseInt(match[1], 10);
    const mins = match[2].padStart(2, '0');
    return `${hours}h ${mins}m`;
  }

  // Step 6: Handle hours-only: "2h"
  const hoursOnly = val.match(/^(\d+)\s*h$/i);
  if (hoursOnly) {
    return `${parseInt(hoursOnly[1], 10)}h 00m`;
  }

  return val;
}

export default function FlightsList() {
  // State
  const [destinations, setDestinations] = useState([]);
  const [selectedDestination, setSelectedDestination] = useState('');
  const [originCity, setOriginCity] = useState('JNB');
  const [departureDate, setDepartureDate] = useState('');
  const [returnDate, setReturnDate] = useState('');
  const [tripType, setTripType] = useState('roundtrip');
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [cabinClass, setCabinClass] = useState('economy');
  const [flights, setFlights] = useState([]);
  const [outboundFlights, setOutboundFlights] = useState([]);
  const [returnFlights, setReturnFlights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [stopFilter, setStopFilter] = useState('all');
  const [sortBy, setSortBy] = useState('price_asc');

  // Load destinations on mount
  useEffect(() => {
    loadDestinations();
  }, []);

  // Set default date
  useEffect(() => {
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    setDepartureDate(nextMonth.toISOString().split('T')[0]);
  }, []);

  const loadDestinations = async () => {
    try {
      const platformResponse = await flightsApi.destinations();
      if (platformResponse.data?.success && platformResponse.data?.destinations?.length > 0) {
        const platformDests = platformResponse.data.destinations.map(d => ({
          code: d.code || d.destination?.toLowerCase(),
          name: d.destination || d.code,
          country: d.country || '',
          flights: true,
          avg_price_zar: d.avg_price_zar,
          date_range: d.date_range,
        }));
        setDestinations(platformDests);
        return;
      }
    } catch (err) {
      console.debug('Platform flight destinations not available:', err.message);
    }

    try {
      const response = await travelApi.destinations();
      if (response.data?.success && response.data?.destinations?.length > 0) {
        setDestinations(response.data.destinations.filter(d => d.flights));
        return;
      }
    } catch (err) {
      console.debug('Travel API destinations not available:', err.message);
    }

    // Hardcoded fallback so the dropdown is never empty
    setDestinations(FALLBACK_FLIGHT_DESTINATIONS);
  };

  const handleSearch = async (e) => {
    e.preventDefault();

    if (!selectedDestination) {
      setError('Please select a destination');
      return;
    }
    if (!departureDate) {
      setError('Please select a departure date');
      return;
    }

    setHasSearched(true);
    setLoading(true);
    setError(null);
    setFlights([]);
    setOutboundFlights([]);
    setReturnFlights([]);
    setStopFilter('all');
    setSortBy('price_asc');

    const destIata = getDestinationIata(selectedDestination);

    try {
      // Try RTTC direct endpoint first (supports round-trip)
      const rttcResponse = await flightsApi.searchRttc(
        originCity,
        destIata,
        departureDate,
        tripType === 'roundtrip' ? returnDate || null : null,
        adults,
        cabinClass !== 'economy' ? cabinClass : null,
      );

      if (rttcResponse.data?.success && (rttcResponse.data?.flights?.length > 0 || rttcResponse.data?.outbound_flights?.length > 0)) {
        const data = rttcResponse.data;
        setFlights(data.flights || []);
        setOutboundFlights(data.outbound_flights || []);
        setReturnFlights(data.return_flights || []);
        setDataSource(data.source || 'rttc');
        setLoading(false);
        return;
      }
    } catch (err) {
      console.debug('RTTC flight search failed, trying fallback:', err.message);
    }

    // Fallback to legacy search — pass IATA code + all user selections
    try {
      const searchParams = {
        destination: destIata,
        origin: originCity,
        departure_date: departureDate,
        adults,
      };
      if (tripType === 'roundtrip' && returnDate) {
        searchParams.return_date = returnDate;
      }
      if (cabinClass !== 'economy') {
        searchParams.cabin_class = cabinClass;
      }

      const response = await flightsApi.search(searchParams);

      if (response.data?.success && response.data?.flights?.length > 0) {
        setFlights(response.data.flights || []);
        setOutboundFlights([]);
        setReturnFlights([]);
        setDataSource(response.data.source || 'platform');
      } else {
        setFlights([]);
        setDataSource(null);
      }
    } catch (err) {
      console.debug('Legacy flight search also failed:', err.message);
      setFlights([]);
      setDataSource(null);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount, currency = 'ZAR') => {
    if (!amount || amount === 0) return 'Price on request';
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatTime = (timeStr) => {
    if (!timeStr || typeof timeStr !== 'string') return '-';
    // Handle "HH:MM" or "HH:MM:SS" format — safe even if shorter than 5 chars
    return timeStr.length >= 5 ? timeStr.substring(0, 5) : timeStr;
  };

  // Determine if we have round-trip sections
  const hasRoundTrip = outboundFlights.length > 0 || returnFlights.length > 0;
  // Detect rich data by checking for fields present in RTTC responses (departure_time, stops, etc.)
  // rather than relying on source label string
  const firstFlight = flights[0] || outboundFlights[0];
  const isRichData = hasRoundTrip || !!(firstFlight && ('departure_time' in firstFlight || 'stops' in firstFlight || 'airline_name' in firstFlight));

  // Filter and sort flights
  const filterAndSort = (flightList) => {
    let filtered = [...flightList];

    // Stop filter
    if (stopFilter !== 'all') {
      filtered = filtered.filter(f => {
        const stops = f.stops ?? (f.is_direct === false ? 1 : 0);
        if (stopFilter === '0') return stops === 0;
        if (stopFilter === '1') return stops === 1;
        if (stopFilter === '2+') return stops >= 2;
        return true;
      });
    }

    // Sort
    filtered.sort((a, b) => {
      const priceA = a.price_adult || a.price_per_person || 0;
      const priceB = b.price_adult || b.price_per_person || 0;
      if (sortBy === 'price_asc') return priceA - priceB;
      if (sortBy === 'price_desc') return priceB - priceA;
      if (sortBy === 'departure') return (a.departure_time || '').localeCompare(b.departure_time || '');
      if (sortBy === 'duration') {
        const durA = a.duration_minutes || 9999;
        const durB = b.duration_minutes || 9999;
        return durA - durB;
      }
      return 0;
    });

    return filtered;
  };

  const filteredFlights = useMemo(() => filterAndSort(flights), [flights, stopFilter, sortBy]);
  const filteredOutbound = useMemo(() => filterAndSort(outboundFlights), [outboundFlights, stopFilter, sortBy]);
  const filteredReturn = useMemo(() => filterAndSort(returnFlights), [returnFlights, stopFilter, sortBy]);

  const FlightCard = ({ flight, idx, section = 'outbound' }) => {
    const airlineName = flight.airline_name || flight.airline || 'Airline';
    const flightNumber = flight.flight_number || '';
    const departTime = flight.departure_time;
    const arriveTime = flight.arrival_time;
    const duration = formatDuration(flight.duration);
    const stops = flight.stops ?? (flight.is_direct === false ? 1 : 0);
    const cabin = flight.cabin_class || cabinClass;
    const baggage = flight.baggage;
    const price = flight.price_adult || flight.price_per_person || 0;
    const priceTotal = flight.price_total || price;
    const logo = flight.airline_logo;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Airline + Flight Info */}
          <div className="flex items-center gap-4 min-w-0 flex-1">
            {/* Airline Logo */}
            <div className="flex-shrink-0 w-12 h-12 flex items-center justify-center">
              {logo ? (
                <img
                  src={logo}
                  alt={airlineName}
                  className="w-10 h-10 object-contain rounded"
                  onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                />
              ) : null}
              <div className={`w-10 h-10 bg-blue-100 rounded flex items-center justify-center ${logo ? 'hidden' : ''}`}>
                <PaperAirplaneIcon className="h-5 w-5 text-blue-600" />
              </div>
            </div>

            {/* Airline + Flight Number */}
            <div className="min-w-0">
              <div className="font-semibold text-gray-900 truncate">{airlineName}</div>
              {flightNumber && (
                <div className="text-xs text-gray-500">{flightNumber}</div>
              )}
            </div>
          </div>

          {/* Center: Times + Route Line */}
          {departTime && arriveTime ? (
            <div className="flex items-center gap-3 flex-shrink-0">
              <div className="text-center">
                <div className="text-lg font-bold text-gray-900">{formatTime(departTime)}</div>
                <div className="text-xs text-gray-500">{flight.origin || originCity}</div>
              </div>
              <div className="flex flex-col items-center px-2 min-w-[120px]">
                {duration && (
                  <div className="text-xs text-gray-500 mb-1">{duration}</div>
                )}
                <div className="flex items-center w-full">
                  <div className={`h-0.5 flex-1 ${stops === 0 ? 'bg-green-500' : 'bg-gray-300'}`} />
                  {stops > 0 && [...Array(Math.min(stops, 3))].map((_, i) => (
                    <div key={i} className="flex items-center">
                      <div className="w-2 h-2 rounded-full bg-amber-500 -mx-0.5 relative z-10" />
                      {i < Math.min(stops, 3) - 1 && <div className="h-0.5 w-3 bg-gray-300" />}
                    </div>
                  ))}
                  {stops > 0 && <div className="h-0.5 flex-1 bg-gray-300" />}
                  <PaperAirplaneIcon className={`h-3.5 w-3.5 -ml-0.5 ${stops === 0 ? 'text-green-600' : 'text-gray-400'}`} />
                </div>
                <div className="text-xs mt-1">
                  {stops === 0 ? (
                    <span className="text-green-600 font-medium">Non-stop</span>
                  ) : (
                    <span className="text-amber-600 font-medium">{stops} stop{stops > 1 ? 's' : ''}</span>
                  )}
                </div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-gray-900">{formatTime(arriveTime)}</div>
                <div className="text-xs text-gray-500">{flight.destination_code || getDestinationIata(selectedDestination)}</div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-gray-500">
              <ClockIcon className="h-4 w-4" />
              <span className="text-sm">Schedule TBC</span>
            </div>
          )}

          {/* Right: Cabin, Baggage, Price */}
          <div className="flex items-center gap-4 flex-shrink-0">
            {/* Badges */}
            <div className="flex flex-col items-end gap-1">
              {cabin && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 capitalize">
                  {cabin.replace('_', ' ')}
                </span>
              )}
              {baggage && (
                <span className="text-xs text-gray-500">{baggage}</span>
              )}
            </div>

            {/* Price */}
            <div className="text-right min-w-[100px]">
              <div className="text-lg font-bold text-blue-600">
                {formatCurrency(price)}
              </div>
              <div className="text-xs text-gray-500">per adult</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Legacy flight row (basic table for non-RTTC data)
  const LegacyFlightRow = ({ flight, idx }) => (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <PaperAirplaneIcon className="h-5 w-5 text-blue-500 mr-2" />
          <span className="font-medium text-gray-900">
            {flight.airline || 'Various Airlines'}
          </span>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
        {flight.departure_date ? new Date(flight.departure_date).toLocaleDateString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short' }) : '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
        {flight.return_date ? new Date(flight.return_date).toLocaleDateString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short' }) : '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right">
        <span className="text-lg font-semibold text-blue-600">
          {formatCurrency(flight.price_per_person, flight.currency)}
        </span>
      </td>
    </tr>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Flights</h1>
          <p className="text-gray-500 mt-1">Search live flight availability and pricing</p>
        </div>
      </div>

      {/* Search Form */}
      <div className="card p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          {/* Trip Type Toggle */}
          <div className="flex items-center gap-4 mb-2">
            <label className="inline-flex items-center">
              <input
                type="radio"
                name="tripType"
                value="roundtrip"
                checked={tripType === 'roundtrip'}
                onChange={(e) => setTripType(e.target.value)}
                className="text-theme-primary focus:ring-theme-primary"
              />
              <span className="ml-2 text-sm text-theme">Round Trip</span>
            </label>
            <label className="inline-flex items-center">
              <input
                type="radio"
                name="tripType"
                value="oneway"
                checked={tripType === 'oneway'}
                onChange={(e) => setTripType(e.target.value)}
                className="text-theme-primary focus:ring-theme-primary"
              />
              <span className="ml-2 text-sm text-theme">One Way</span>
            </label>
          </div>

          {/* Route Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Origin */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <PaperAirplaneIcon className="h-4 w-4 inline mr-1 rotate-[-45deg]" />
                From
              </label>
              <input
                type="text"
                value={originCity}
                onChange={(e) => setOriginCity(e.target.value.toUpperCase())}
                placeholder="JNB"
                maxLength={3}
                className="input uppercase"
              />
            </div>

            {/* Swap Button */}
            <div className="hidden lg:flex items-end justify-center pb-2">
              <button
                type="button"
                onClick={() => {
                  const temp = originCity;
                  setOriginCity(getDestinationIata(selectedDestination));
                  setSelectedDestination(temp);
                }}
                className="p-2 rounded-full hover:bg-theme-border-light text-theme-muted"
              >
                <ArrowsRightLeftIcon className="h-5 w-5" />
              </button>
            </div>

            {/* Destination */}
            <div className="lg:col-span-2">
              <label className="block text-sm font-medium text-theme mb-1">
                <MapPinIcon className="h-4 w-4 inline mr-1" />
                To
              </label>
              <select
                value={selectedDestination}
                onChange={(e) => setSelectedDestination(e.target.value)}
                className="input"
              >
                <option value="">Select Destination</option>
                {destinations.map((dest) => (
                  <option key={dest.code} value={dest.code}>
                    {dest.name}, {dest.country} ({dest.code})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Dates and Passengers Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Departure Date */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <CalendarIcon className="h-4 w-4 inline mr-1" />
                Departure
              </label>
              <input
                type="date"
                value={departureDate}
                onChange={(e) => setDepartureDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="input"
              />
            </div>

            {/* Return Date */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <CalendarIcon className="h-4 w-4 inline mr-1" />
                Return
              </label>
              <input
                type="date"
                value={returnDate}
                onChange={(e) => setReturnDate(e.target.value)}
                min={departureDate || new Date().toISOString().split('T')[0]}
                disabled={tripType === 'oneway'}
                className="input disabled:opacity-50"
              />
            </div>

            {/* Adults */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                <UserGroupIcon className="h-4 w-4 inline mr-1" />
                Adults
              </label>
              <select
                value={adults}
                onChange={(e) => setAdults(parseInt(e.target.value))}
                className="input"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>

            {/* Children */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                Children
              </label>
              <select
                value={children}
                onChange={(e) => setChildren(parseInt(e.target.value))}
                className="input"
              >
                {[0, 1, 2, 3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>

            {/* Cabin Class */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1">
                Class
              </label>
              <select
                value={cabinClass}
                onChange={(e) => setCabinClass(e.target.value)}
                className="input"
              >
                {CABIN_CLASSES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Search Button */}
          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary inline-flex items-center gap-2 disabled:opacity-50"
            >
              <MagnifyingGlassIcon className="h-4 w-4" />
              {loading ? 'Searching...' : 'Search Flights'}
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

      {/* Loading State */}
      {loading && (
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-200 rounded" />
                  <div>
                    <div className="h-4 bg-gray-200 rounded w-24 mb-2" />
                    <div className="h-3 bg-gray-200 rounded w-16" />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="h-6 bg-gray-200 rounded w-12" />
                  <div className="w-20 h-px bg-gray-200" />
                  <div className="h-6 bg-gray-200 rounded w-12" />
                </div>
                <div className="text-right">
                  <div className="h-5 bg-gray-200 rounded w-20 mb-1" />
                  <div className="h-3 bg-gray-200 rounded w-14" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {!loading && hasSearched && (flights.length > 0 || outboundFlights.length > 0) && (
        <div className="space-y-6">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {hasRoundTrip
                ? `${outboundFlights.length} Outbound + ${returnFlights.length} Return Flights`
                : `${flights.length} Flight Options`}
            </h2>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              isRichData
                ? 'bg-green-100 text-green-800'
                : dataSource === 'platform'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-blue-100 text-blue-800'
            }`}>
              {isRichData ? 'Live Flights' : dataSource === 'platform' ? 'Live Data' : 'Sample Data'}
            </span>
          </div>

          {/* Filter Bar */}
          {isRichData && (
            <div className="flex items-center gap-4 flex-wrap bg-gray-50 rounded-lg p-3 border border-gray-200">
              <FunnelIcon className="h-4 w-4 text-gray-500 flex-shrink-0" />
              <div className="flex items-center gap-2">
                <label className="text-xs font-medium text-gray-500 uppercase">Stops</label>
                <div className="flex gap-1">
                  {STOP_FILTERS.map(f => (
                    <button
                      key={f.value}
                      onClick={() => setStopFilter(f.value)}
                      className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${
                        stopFilter === f.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-100'
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2 ml-auto">
                <label className="text-xs font-medium text-gray-500 uppercase">Sort</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="text-xs border border-gray-300 rounded-md px-2 py-1 bg-white"
                >
                  {SORT_OPTIONS.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Round-trip: Separate sections */}
          {hasRoundTrip ? (
            <>
              {/* Outbound Flights */}
              {filteredOutbound.length > 0 && (
                <div>
                  <h3 className="text-md font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <PaperAirplaneIcon className="h-5 w-5 text-blue-500" />
                    Outbound — {originCity} to {getDestinationIata(selectedDestination)}
                    <span className="text-sm font-normal text-gray-500">
                      ({departureDate ? new Date(departureDate).toLocaleDateString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short' }) : ''})
                    </span>
                  </h3>
                  <div className="space-y-3">
                    {filteredOutbound.map((flight, idx) => (
                      <FlightCard key={idx} flight={flight} idx={idx} section="outbound" />
                    ))}
                  </div>
                </div>
              )}

              {/* Return Flights */}
              {filteredReturn.length > 0 && (
                <div>
                  <h3 className="text-md font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <PaperAirplaneIcon className="h-5 w-5 text-orange-500 rotate-180" />
                    Return — {getDestinationIata(selectedDestination)} to {originCity}
                    <span className="text-sm font-normal text-gray-500">
                      ({returnDate ? new Date(returnDate).toLocaleDateString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short' }) : ''})
                    </span>
                  </h3>
                  <div className="space-y-3">
                    {filteredReturn.map((flight, idx) => (
                      <FlightCard key={idx} flight={flight} idx={idx} section="return" />
                    ))}
                  </div>
                </div>
              )}

              {/* No results after filtering */}
              {filteredOutbound.length === 0 && filteredReturn.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <p>No flights match your filters. Try adjusting the stop filter.</p>
                  <button onClick={() => setStopFilter('all')} className="text-blue-600 hover:underline mt-2 text-sm">
                    Clear filters
                  </button>
                </div>
              )}
            </>
          ) : isRichData ? (
            /* Rich RTTC data — use flight cards */
            <div className="space-y-3">
              {filteredFlights.length > 0 ? (
                filteredFlights.map((flight, idx) => (
                  <FlightCard key={idx} flight={flight} idx={idx} section="all" />
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>No flights match your filters. Try adjusting the stop filter.</p>
                  <button onClick={() => setStopFilter('all')} className="text-blue-600 hover:underline mt-2 text-sm">
                    Clear filters
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* Legacy data — use table */
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Airline</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Departure</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Return</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Price per Person</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredFlights.map((flight, idx) => (
                      <LegacyFlightRow key={idx} flight={flight} idx={idx} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!loading && hasSearched && flights.length === 0 && outboundFlights.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="bg-blue-50 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <PaperAirplaneIcon className="h-8 w-8 text-blue-500" />
          </div>
          <h3 className="text-lg font-medium text-gray-900">No flights found for this route</h3>
          <p className="mt-2 text-gray-500 max-w-md mx-auto">
            Try different dates, a different origin, or another destination.
          </p>
        </div>
      )}

      {/* Initial State — no search yet */}
      {!loading && !hasSearched && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="bg-blue-50 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <PaperAirplaneIcon className="h-8 w-8 text-blue-500" />
          </div>
          <h3 className="text-lg font-medium text-gray-900">Search for Flights</h3>
          <p className="mt-2 text-gray-500 max-w-md mx-auto">
            Enter your travel details above and click "Search Flights" to find available options with live airline data.
          </p>
        </div>
      )}
    </div>
  );
}
