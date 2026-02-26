import { useState, useEffect } from 'react';
import {
  PaperAirplaneIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  CalendarIcon,
  UserGroupIcon,
  ArrowRightIcon,
  ArrowsRightLeftIcon,
} from '@heroicons/react/24/outline';
import { flightsApi, travelApi } from '../../services/api';
import { AddToQuoteButton } from '../../components/travel/FloatingQuoteCart';

// Cabin class options
const CABIN_CLASSES = [
  { value: 'economy', label: 'Economy' },
  { value: 'premium_economy', label: 'Premium Economy' },
  { value: 'business', label: 'Business' },
  { value: 'first', label: 'First Class' },
];

export default function FlightsList() {
  // State
  const [destinations, setDestinations] = useState([]);
  const [selectedDestination, setSelectedDestination] = useState('');
  const [originCity, setOriginCity] = useState('JNB'); // Default to Johannesburg
  const [departureDate, setDepartureDate] = useState('');
  const [returnDate, setReturnDate] = useState('');
  const [tripType, setTripType] = useState('roundtrip'); // 'oneway' or 'roundtrip'
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [cabinClass, setCabinClass] = useState('economy');
  const [flights, setFlights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState(null); // "platform" or "bigquery"
  const [hasSearched, setHasSearched] = useState(false);

  // Load destinations on mount
  useEffect(() => {
    loadDestinations();
    loadAllFlights();
  }, []);

  // Set default date
  useEffect(() => {
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    setDepartureDate(nextMonth.toISOString().split('T')[0]);
  }, []);

  const loadDestinations = async () => {
    try {
      // Try platform flight destinations first (has real date ranges and avg prices)
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

    // Fall back to general travel destinations
    try {
      const response = await travelApi.destinations();
      if (response.data?.success) {
        setDestinations(response.data.destinations.filter(d => d.flights));
      }
    } catch (err) {
      console.error('Failed to load destinations:', err);
    }
  };

  const loadAllFlights = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await flightsApi.list({ limit: 100 });
      if (response.data?.success) {
        setFlights(response.data.flights || []);
        setDataSource(response.data.source || (response.data.flights?.[0]?.source) || null);
      } else {
        console.debug('Flights API returned:', response.data?.error || 'No flights');
        setFlights([]);
        setDataSource(null);
      }
    } catch (err) {
      console.debug('Failed to fetch flights:', err.message);
      setFlights([]);
      setDataSource(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();

    if (!selectedDestination) {
      loadAllFlights();
      return;
    }

    setHasSearched(true);
    setLoading(true);
    setError(null);

    try {
      const response = await flightsApi.search(
        selectedDestination,
        departureDate || null,
        returnDate || null
      );

      if (response.data?.success) {
        setFlights(response.data.flights || []);
        setDataSource(response.data.source || (response.data.flights?.[0]?.source) || null);
      } else {
        console.debug('Flight search returned:', response.data?.error || 'No results');
        setFlights([]);
        setDataSource(null);
      }
    } catch (err) {
      console.debug('Failed to search flights:', err.message);
      setFlights([]);
      setDataSource(null);
    } finally {
      setLoading(false);
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

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-ZA', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  // Group flights by destination
  const groupedFlights = flights.reduce((acc, flight) => {
    const dest = flight.destination || 'Unknown';
    if (!acc[dest]) {
      acc[dest] = [];
    }
    acc[dest].push(flight);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Flights</h1>
          <p className="text-gray-500 mt-1">View flight pricing by destination</p>
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

            {/* Swap Button (visual only) */}
            <div className="hidden lg:flex items-end justify-center pb-2">
              <button
                type="button"
                onClick={() => {
                  const temp = originCity;
                  setOriginCity(selectedDestination);
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
              className="btn-primary inline-flex items-center gap-2"
            >
              <MagnifyingGlassIcon className="h-4 w-4" />
              Search Flights
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

      {/* Results */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 animate-pulse">
              <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
              <div className="space-y-3">
                <div className="h-4 bg-gray-200 rounded w-full"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
            </div>
          ))}
        </div>
      ) : flights.length > 0 ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {flights.length} Flight Options
            </h2>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              dataSource === 'platform'
                ? 'bg-green-100 text-green-800'
                : 'bg-blue-100 text-blue-800'
            }`}>
              {dataSource === 'platform' ? 'Live Data — RTTC' : 'Sample Data'}
            </span>
          </div>

          {Object.entries(groupedFlights).map(([destination, destFlights]) => (
            <div key={destination} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              {/* Destination Header */}
              <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
                <div className="flex items-center">
                  <MapPinIcon className="h-5 w-5 text-gray-400 mr-2" />
                  <h3 className="text-lg font-semibold text-gray-900 capitalize">
                    {destination}
                  </h3>
                  <span className="ml-2 text-sm text-gray-500">
                    ({destFlights.length} flights)
                  </span>
                </div>
              </div>

              {/* Flights Table */}
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Airline
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Departure
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Return
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Price per Person
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {destFlights.map((flight, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <PaperAirplaneIcon className="h-5 w-5 text-blue-500 mr-2" />
                            <span className="font-medium text-gray-900">
                              {flight.airline || 'Various Airlines'}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <CalendarIcon className="h-4 w-4 text-gray-400 mr-2" />
                            <span className="text-gray-900">
                              {formatDate(flight.departure_date)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <CalendarIcon className="h-4 w-4 text-gray-400 mr-2" />
                            <span className="text-gray-900">
                              {formatDate(flight.return_date)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <div className="flex items-center justify-end">
                            <UserGroupIcon className="h-4 w-4 text-gray-400 mr-2" />
                            <span className="text-lg font-semibold text-blue-600">
                              {formatCurrency(flight.price_per_person, flight.currency)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <AddToQuoteButton
                            item={{
                              id: `flight-${destination}-${idx}`,
                              type: 'flight',
                              name: `${flight.airline || 'Flight'} to ${destination}`,
                              price: flight.price_per_person,
                              currency: flight.currency || 'ZAR',
                              details: {
                                airline: flight.airline,
                                destination: destination,
                                departure_date: flight.departure_date,
                                return_date: flight.return_date,
                              }
                            }}
                            size="sm"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="bg-blue-50 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <PaperAirplaneIcon className="h-8 w-8 text-blue-500" />
          </div>
          <h3 className="text-lg font-medium text-gray-900">
            {hasSearched ? 'No flights found for this route' : 'Search for Flights'}
          </h3>
          <p className="mt-2 text-gray-500 max-w-md mx-auto">
            {hasSearched
              ? 'Try different dates, a different origin, or another destination.'
              : 'Enter your travel details above and click "Search Flights" to find available options.'}
          </p>
        </div>
      )}
    </div>
  );
}
