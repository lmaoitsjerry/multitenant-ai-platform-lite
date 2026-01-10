import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { pricingApi } from '../../services/api';
import {
  ArrowLeftIcon,
  BuildingOfficeIcon,
  MapPinIcon,
  StarIcon,
  PhotoIcon,
  CalendarDaysIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';

export default function HotelDetail() {
  const { hotelName } = useParams();
  const [hotel, setHotel] = useState(null);
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('rates');

  useEffect(() => {
    if (hotelName) {
      loadHotelData();
    }
  }, [hotelName]);

  const loadHotelData = async () => {
    try {
      setLoading(true);
      const decodedName = decodeURIComponent(hotelName);
      
      // Load hotel info and rates in parallel
      const [hotelRes, ratesRes] = await Promise.all([
        pricingApi.getHotel(decodedName).catch(() => null),
        pricingApi.getHotelRates(decodedName).catch(() => ({ data: { data: [] } })),
      ]);

      // If no specific hotel endpoint, construct from rates
      if (hotelRes?.data?.data) {
        setHotel(hotelRes.data.data);
      } else if (ratesRes?.data?.data?.length > 0) {
        // Build hotel info from first rate
        const firstRate = ratesRes.data.data[0];
        setHotel({
          hotel_name: firstRate.hotel_name,
          destination: firstRate.destination,
          star_rating: firstRate.hotel_rating || firstRate.star_rating,
        });
      } else {
        // Fallback - just use the name
        setHotel({
          hotel_name: decodedName,
          destination: 'Unknown',
          star_rating: null,
        });
      }

      setRates(ratesRes?.data?.data || []);
    } catch (error) {
      console.error('Failed to load hotel data:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderStars = (rating) => {
    if (!rating) return null;
    const numStars = parseInt(rating) || 0;
    return (
      <div className="flex items-center gap-0.5">
        {[...Array(5)].map((_, i) => (
          i < numStars ? (
            <StarIconSolid key={i} className="w-5 h-5 text-yellow-400" />
          ) : (
            <StarIcon key={i} className="w-5 h-5 text-gray-300" />
          )
        ))}
        <span className="ml-2 text-gray-600">{numStars} Star</span>
      </div>
    );
  };

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return `R ${Number(amount).toLocaleString()}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-ZA', { 
      day: '2-digit', 
      month: 'short',
      year: 'numeric'
    });
  };

  // Group rates by room type
  const ratesByRoom = rates.reduce((acc, rate) => {
    const roomType = rate.room_type || 'Standard';
    if (!acc[roomType]) acc[roomType] = [];
    acc[roomType].push(rate);
    return acc;
  }, {});

  // Get unique meal plans
  const mealPlans = [...new Set(rates.map(r => r.meal_plan).filter(Boolean))];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!hotel) {
    return (
      <div className="space-y-6">
        <Link to="/pricing/hotels" className="inline-flex items-center gap-2 text-purple-600 hover:text-purple-700">
          <ArrowLeftIcon className="w-4 h-4" />
          Back to Hotels
        </Link>
        <div className="card text-center py-12">
          <BuildingOfficeIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Hotel not found</h3>
          <p className="text-gray-500 mt-1">The hotel you're looking for doesn't exist.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link to="/pricing/hotels" className="inline-flex items-center gap-2 text-purple-600 hover:text-purple-700">
        <ArrowLeftIcon className="w-4 h-4" />
        Back to Hotels
      </Link>

      {/* Hotel Header */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-6">
          {/* Hotel Image Placeholder */}
          <div className="w-full md:w-80 h-48 bg-gradient-to-br from-purple-100 to-purple-200 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <PhotoIcon className="w-16 h-16 text-purple-400 mx-auto mb-2" />
              <p className="text-sm text-purple-500">No images available</p>
            </div>
          </div>

          {/* Hotel Info */}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">{hotel.hotel_name}</h1>
            
            <div className="flex items-center gap-4 mt-2">
              {renderStars(hotel.star_rating)}
            </div>

            <div className="flex items-center gap-2 mt-3 text-gray-600">
              <MapPinIcon className="w-5 h-5 text-purple-600" />
              <span>{hotel.destination}</span>
            </div>

            {hotel.description && (
              <p className="mt-4 text-gray-600">{hotel.description}</p>
            )}

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-4 mt-6">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-500">Room Types</p>
                <p className="text-xl font-bold text-gray-900">{Object.keys(ratesByRoom).length}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-500">Meal Plans</p>
                <p className="text-xl font-bold text-gray-900">{mealPlans.length}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-500">Rate Options</p>
                <p className="text-xl font-bold text-gray-900">{rates.length}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-8">
          <button
            onClick={() => setActiveTab('rates')}
            className={`py-3 border-b-2 text-sm font-medium transition-colors ${
              activeTab === 'rates'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Rates & Availability
          </button>
          <button
            onClick={() => setActiveTab('rooms')}
            className={`py-3 border-b-2 text-sm font-medium transition-colors ${
              activeTab === 'rooms'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Room Types
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'rates' && (
        <div className="card p-0 overflow-hidden">
          {rates.length === 0 ? (
            <div className="text-center py-12">
              <CalendarDaysIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No rates available</h3>
              <p className="text-gray-500 mt-1">No pricing data found for this hotel.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Room Type</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Meal Plan</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Valid Period</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Nights</th>
                    <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Per Person (Share)</th>
                    <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Single</th>
                    <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Child</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {rates.slice(0, 50).map((rate, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 font-medium text-gray-900">{rate.room_type}</td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                          {rate.meal_plan}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-600 text-sm">
                        {formatDate(rate.check_in_date)} - {formatDate(rate.check_out_date)}
                      </td>
                      <td className="px-6 py-4 text-gray-600">{rate.nights}</td>
                      <td className="px-6 py-4 text-right font-semibold text-gray-900">
                        {formatCurrency(rate.total_7nights_pps)}
                      </td>
                      <td className="px-6 py-4 text-right text-gray-600">
                        {formatCurrency(rate.total_7nights_single)}
                      </td>
                      <td className="px-6 py-4 text-right text-gray-600">
                        {formatCurrency(rate.total_7nights_child)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rates.length > 50 && (
                <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
                  Showing 50 of {rates.length} rates
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'rooms' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(ratesByRoom).map(([roomType, roomRates]) => {
            const minPrice = Math.min(...roomRates.map(r => r.total_7nights_pps || Infinity));
            const mealPlansForRoom = [...new Set(roomRates.map(r => r.meal_plan).filter(Boolean))];
            
            return (
              <div key={roomType} className="card">
                <div className="w-full h-32 bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg mb-4 flex items-center justify-center">
                  <PhotoIcon className="w-10 h-10 text-gray-400" />
                </div>
                <h3 className="font-semibold text-gray-900">{roomType}</h3>
                <div className="flex flex-wrap gap-1 mt-2">
                  {mealPlansForRoom.map(mp => (
                    <span key={mp} className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                      {mp}
                    </span>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-sm text-gray-500">From</p>
                  <p className="text-lg font-bold text-purple-600">
                    {minPrice === Infinity ? '-' : formatCurrency(minPrice)}
                  </p>
                  <p className="text-xs text-gray-400">per person sharing</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}