import { useState, useEffect } from 'react';
import { pricingApi } from '../../services/api';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  ArrowUpTrayIcon,
  ArrowDownTrayIcon,
  BuildingOfficeIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';

export default function PricingRates() {
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [destinations, setDestinations] = useState([]);
  const [filters, setFilters] = useState({
    destination: '',
    hotel_name: '',
    meal_plan: '',
  });
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadRates();
  }, [filters]);

  const loadData = async () => {
    try {
      const [statsRes, destRes] = await Promise.all([
        pricingApi.getStats(),
        pricingApi.listDestinations(),
      ]);
      setStats(statsRes.data?.data);
      setDestinations(destRes.data?.data || []);
    } catch (error) {
      console.error('Failed to load pricing data:', error);
    }
  };

  const loadRates = async () => {
    try {
      setLoading(true);
      const params = { limit: 100 };
      if (filters.destination) params.destination = filters.destination;
      if (filters.hotel_name) params.hotel_name = filters.hotel_name;
      if (filters.meal_plan) params.meal_plan = filters.meal_plan;
      
      const response = await pricingApi.listRates(params);
      setRates(response.data?.data || []);
    } catch (error) {
      console.error('Failed to load rates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await pricingApi.exportRates({ destination: filters.destination });
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rates_export_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
    } catch (error) {
      alert('Failed to export rates');
    }
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const result = await pricingApi.importRates(file);
      alert(`Imported ${result.data?.imported || 0} rates`);
      loadRates();
    } catch (error) {
      alert('Failed to import rates');
    }
    e.target.value = '';
  };

  const filteredRates = rates.filter(rate => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      rate.hotel_name?.toLowerCase().includes(searchLower) ||
      rate.room_type?.toLowerCase().includes(searchLower) ||
      rate.destination?.toLowerCase().includes(searchLower)
    );
  });

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return `R ${Number(amount).toLocaleString()}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-ZA', {
      day: '2-digit',
      month: 'short',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pricing Rates</h1>
          <p className="text-gray-500 mt-1">
            Manage hotel rates used by the quote system
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="btn-secondary flex items-center gap-2 cursor-pointer">
            <ArrowUpTrayIcon className="w-5 h-5" />
            Import CSV
            <input
              type="file"
              accept=".csv"
              onChange={handleImport}
              className="hidden"
            />
          </label>
          <button onClick={handleExport} className="btn-secondary flex items-center gap-2">
            <ArrowDownTrayIcon className="w-5 h-5" />
            Export
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-sm text-gray-500">Total Rates</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_rates?.toLocaleString()}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-500">Hotels</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_hotels}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-500">Avg Price/Night</p>
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(stats.avg_price)}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-500">Price Range</p>
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(stats.min_price)} - {formatCurrency(stats.max_price)}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <div className="relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search hotels, room types..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>

          {/* Destination Filter */}
          <select
            value={filters.destination}
            onChange={(e) => setFilters(f => ({ ...f, destination: e.target.value }))}
            className="input w-44"
          >
            <option value="">All Destinations</option>
            {destinations.map((dest) => (
              <option key={dest.destination} value={dest.destination}>
                {dest.destination} ({dest.hotel_count})
              </option>
            ))}
          </select>

          {/* Meal Plan Filter */}
          <select
            value={filters.meal_plan}
            onChange={(e) => setFilters(f => ({ ...f, meal_plan: e.target.value }))}
            className="input w-40"
          >
            <option value="">All Meal Plans</option>
            <option value="BB">Bed & Breakfast</option>
            <option value="HB">Half Board</option>
            <option value="FB">Full Board</option>
            <option value="AI">All Inclusive</option>
          </select>

          {/* Refresh */}
          <button
            onClick={loadRates}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowPathIcon className="w-5 h-5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Rates Table */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredRates.length === 0 ? (
          <div className="text-center py-12">
            <BuildingOfficeIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No rates found</h3>
            <p className="text-gray-500 mt-1">Try adjusting your filters or import new rates</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Hotel</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Room Type</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Meal Plan</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Valid Period</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Nights</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Per Person (Share)</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Single</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Child</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredRates.map((rate, idx) => (
                  <tr key={rate.rate_id || idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{rate.hotel_name}</div>
                      <div className="text-sm text-gray-500">{rate.destination}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{rate.room_type}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-700">
                        {rate.meal_plan}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-sm">
                      {formatDate(rate.check_in_date)} - {formatDate(rate.check_out_date)}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{rate.nights}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                      {formatCurrency(rate.total_7nights_pps)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {formatCurrency(rate.total_7nights_single)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {formatCurrency(rate.total_7nights_child)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Count */}
      {!loading && filteredRates.length > 0 && (
        <div className="text-sm text-gray-500 text-center">
          Showing {filteredRates.length} rate{filteredRates.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
