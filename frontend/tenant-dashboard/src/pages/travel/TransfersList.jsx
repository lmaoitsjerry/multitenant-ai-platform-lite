import { useState, useEffect } from 'react';
import {
  TruckIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  CalendarIcon,
  UserGroupIcon,
  ClockIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { transfersApi, travelApi } from '../../services/api';
import { getDestinationIata } from '../../utils/destinations';
import { AddToQuoteButton } from '../../components/travel/FloatingQuoteCart';
import { normalizeTransferPrice } from '../../utils/fieldTransformers';

// Common transfer routes by destination
const COMMON_ROUTES = {
  zanzibar: [
    'Zanzibar Airport to Stone Town',
    'Zanzibar Airport to Nungwi',
    'Zanzibar Airport to Kendwa',
    'Zanzibar Airport to Paje',
    'Zanzibar Airport to Jambiani',
  ],
  mauritius: [
    'Mauritius Airport to Port Louis',
    'Mauritius Airport to Grand Baie',
    'Mauritius Airport to Flic en Flac',
    'Mauritius Airport to Belle Mare',
  ],
  maldives: [
    'Male Airport to Male City',
    'Male Airport to Hulhumale',
  ],
  kenya: [
    'Nairobi Airport to City Center',
    'Nairobi Airport to Westlands',
    'Mombasa Airport to Diani Beach',
  ],
  dubai: [
    'Dubai Airport to Downtown Dubai',
    'Dubai Airport to Marina',
    'Dubai Airport to Palm Jumeirah',
  ],
};

// Normalize transfers from different sources to a common shape
function normalizeTransfer(raw, source) {
  if (source === 'cloud_run') {
    return {
      transfer_id: raw.transfer_id,
      route: raw.route,
      vehicle_type: raw.vehicle_type,
      vehicle_category: raw.vehicle_category,
      price: raw.price_per_transfer,
      price_child: null,
      currency: raw.currency || 'EUR',
      max_passengers: raw.max_passengers,
      duration_minutes: raw.duration_minutes,
      pricing_type: 'per_transfer',
      source: 'cloud_run',
      hotel_name: null,
    };
  }
  // BigQuery format
  return {
    transfer_id: `bq_${raw.hotel_name}`,
    route: `Airport to ${raw.hotel_name}`,
    vehicle_type: 'Shared Transfer',
    vehicle_category: 'Standard',
    price: raw.transfers_adult,
    price_child: raw.transfers_child,
    currency: raw.currency || 'ZAR',
    max_passengers: null,
    duration_minutes: null,
    pricing_type: 'per_person',
    source: 'bigquery',
    hotel_name: raw.hotel_name,
  };
}

export default function TransfersList() {
  // State
  const [destinations, setDestinations] = useState([]);
  const [selectedDestination, setSelectedDestination] = useState('');
  const [route, setRoute] = useState('');
  const [transferDate, setTransferDate] = useState('');
  const [passengers, setPassengers] = useState(2);
  const [transfers, setTransfers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState(null); // 'cloud_run' or 'bigquery'
  const [hasSearched, setHasSearched] = useState(false);

  // Set default transfer date (30 days from now)
  useEffect(() => {
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() + 30);
    setTransferDate(defaultDate.toISOString().split('T')[0]);
  }, []);

  // Load destinations on mount
  useEffect(() => {
    loadDestinations();
  }, []);

  // Update route suggestions when destination changes
  useEffect(() => {
    if (selectedDestination && COMMON_ROUTES[selectedDestination]) {
      // Set first suggested route as default
      setRoute(COMMON_ROUTES[selectedDestination][0]);
    }
  }, [selectedDestination]);

  const loadDestinations = async () => {
    try {
      const response = await travelApi.destinations();
      if (response.data?.success) {
        setDestinations(response.data.destinations);
        // Set first destination as default
        if (response.data.destinations.length > 0) {
          setSelectedDestination(response.data.destinations[0].code);
        }
      }
    } catch (err) {
      console.error('Failed to load destinations:', err);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();

    if (!route || !transferDate) {
      setError('Please enter a route and select a date');
      return;
    }

    setLoading(true);
    setError(null);
    setTransfers([]);
    setHasSearched(true);

    try {
      const iataCode = getDestinationIata(selectedDestination);
      const response = await transfersApi.search({
        destination: selectedDestination,
        from_code: iataCode,
        to_code: iataCode,
        date: transferDate,
        passengers,
      });

      if (response.data?.success && response.data?.transfers?.length > 0) {
        const rawTransfers = response.data.transfers;
        // Detect source: if any transfer has vehicle_type it's Cloud Run; if hotel_name it's BigQuery
        const source = rawTransfers[0].vehicle_type ? 'cloud_run' : 'bigquery';
        const normalized = rawTransfers.map(t => normalizeTransfer(t, source));

        setTransfers(normalized);
        setDataSource(source);
      } else {
        setTransfers([]);
        setDataSource(null);
      }
    } catch (err) {
      console.error('Transfer search error:', err);
      setError('Failed to search transfers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount, currency = 'EUR') => {
    const locale = currency === 'EUR' ? 'en-EU' : 'en-ZA';
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const suggestedRoutes = COMMON_ROUTES[selectedDestination] || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transfers</h1>
          <p className="text-gray-500 mt-1">Airport and hotel transfer pricing</p>
        </div>
        {dataSource === 'cloud_run' && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
            <CheckCircleIcon className="h-4 w-4" />
            Live Data
          </span>
        )}
        {dataSource === 'bigquery' && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800">
            Cached Data
          </span>
        )}
      </div>

      {/* Search Form */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Destination */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <MapPinIcon className="h-4 w-4 inline mr-1" />
                Destination
              </label>
              <select
                value={selectedDestination}
                onChange={(e) => setSelectedDestination(e.target.value)}
                className="input"
              >
                {destinations.map((dest) => (
                  <option key={dest.code} value={dest.code}>
                    {dest.name}, {dest.country}
                  </option>
                ))}
              </select>
            </div>

            {/* Route */}
            <div className="lg:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <TruckIcon className="h-4 w-4 inline mr-1" />
                Route
              </label>
              <input
                type="text"
                value={route}
                onChange={(e) => setRoute(e.target.value)}
                placeholder="e.g., Zanzibar Airport to Stone Town"
                list="route-suggestions"
                className="input"
              />
              <datalist id="route-suggestions">
                {suggestedRoutes.map((r, idx) => (
                  <option key={idx} value={r} />
                ))}
              </datalist>
            </div>

            {/* Transfer Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <CalendarIcon className="h-4 w-4 inline mr-1" />
                Transfer Date
              </label>
              <input
                type="date"
                value={transferDate}
                onChange={(e) => setTransferDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="input"
              />
            </div>

            {/* Passengers */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <UserGroupIcon className="h-4 w-4 inline mr-1" />
                Passengers
              </label>
              <select
                value={passengers}
                onChange={(e) => setPassengers(parseInt(e.target.value))}
                className="input"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20].map((n) => (
                  <option key={n} value={n}>{n} {n === 1 ? 'passenger' : 'passengers'}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Search Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? (
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
                  Search Transfers
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Data Source Notice */}
      {dataSource === 'cloud_run' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <CheckCircleIcon className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-green-800">Live Transfer Data</h4>
              <p className="text-sm text-green-700 mt-1">
                Showing real-time transfer availability and pricing. Prices are in EUR per transfer (not per person).
              </p>
            </div>
          </div>
        </div>
      )}

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
            <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
              <div className="grid grid-cols-3 gap-4">
                <div className="h-4 bg-gray-200 rounded"></div>
                <div className="h-4 bg-gray-200 rounded"></div>
                <div className="h-4 bg-gray-200 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      ) : transfers.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {transfers.length} Transfer Options
            </h2>
          </div>

          <div className="grid gap-4">
            {transfers.map((transfer, idx) => (
              <div
                key={transfer.transfer_id || idx}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  {/* Route & Vehicle Info */}
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {transfer.vehicle_type || 'Transfer'}
                    </h3>
                    <p className="text-gray-600 mt-1">{transfer.route}</p>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      {transfer.vehicle_category && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                          {transfer.vehicle_category}
                        </span>
                      )}
                      {transfer.max_passengers && (
                        <span className="flex items-center">
                          <UserGroupIcon className="h-4 w-4 mr-1" />
                          Up to {transfer.max_passengers} passengers
                        </span>
                      )}
                      {transfer.duration_minutes && (
                        <span className="flex items-center">
                          <ClockIcon className="h-4 w-4 mr-1" />
                          ~{transfer.duration_minutes} min
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Pricing */}
                  <div className="text-right flex items-center gap-4">
                    <div>
                      <div className="text-2xl font-bold text-blue-600">
                        {formatCurrency(transfer.price, transfer.currency)}
                      </div>
                      <div className="text-sm text-gray-500">
                        {normalizeTransferPrice(transfer).pricingModel === 'per_transfer' ? 'per transfer' : 'per person'}
                      </div>
                    </div>
                    <AddToQuoteButton
                      item={{
                        id: transfer.transfer_id,
                        type: 'transfer',
                        name: `${transfer.vehicle_type || 'Transfer'} - ${transfer.route}`,
                        price: normalizeTransferPrice(transfer).pricingModel === 'per_person'
                          ? normalizeTransferPrice(transfer).price * passengers
                          : normalizeTransferPrice(transfer).price,
                        currency: transfer.currency || 'EUR',
                        details: {
                          route: transfer.route,
                          vehicle_type: transfer.vehicle_type,
                          vehicle_category: transfer.vehicle_category,
                          max_passengers: transfer.max_passengers,
                          duration_minutes: transfer.duration_minutes,
                          transfer_date: transferDate,
                          passengers: passengers,
                          pricing_model: normalizeTransferPrice(transfer).pricingModel,
                        }
                      }}
                      size="md"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : hasSearched ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="bg-amber-50 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <TruckIcon className="h-8 w-8 text-amber-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-900">No Transfers Found</h3>
          <p className="mt-2 text-gray-500 max-w-md mx-auto">
            No transfer options found for this route. Try a different route or destination.
            Transfer costs can also be included in the Quote Generator for complete package pricing.
          </p>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="/quotes/new"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              Generate a Quote
            </a>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <TruckIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">Search Transfers</h3>
          <p className="mt-2 text-gray-500 max-w-md mx-auto">
            Enter a route and date to search for available transfer options. You can also select from
            suggested routes for your destination.
          </p>
        </div>
      )}

      {/* Info Card */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <TruckIcon className="h-5 w-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-blue-900">Transfer Pricing Information</h3>
            <p className="mt-1 text-sm text-blue-700">
              Live transfer prices are per vehicle/transfer (shared or private).
              Price varies by vehicle type, distance, and number of passengers.
              For return transfers, book two separate one-way transfers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
