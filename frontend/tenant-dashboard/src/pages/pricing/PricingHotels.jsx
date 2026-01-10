import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { pricingApi } from '../../services/api';
import {
  BuildingOfficeIcon,
  MapPinIcon,
  StarIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';

export default function PricingHotels() {
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [destinations, setDestinations] = useState([]);
  const [destinationFilter, setDestinationFilter] = useState('');
  const [search, setSearch] = useState('');
  const [expandedHotel, setExpandedHotel] = useState(null);
  const [hotelRates, setHotelRates] = useState({});

  useEffect(() => {
    loadData();
  }, [destinationFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [hotelsRes, destRes] = await Promise.all([
        pricingApi.listHotels({ destination: destinationFilter || undefined }),
        pricingApi.listDestinations(),
      ]);
      setHotels(hotelsRes.data?.data || []);
      setDestinations(destRes.data?.data || []);
    } catch (error) {
      console.error('Failed to load hotels:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadHotelRates = async (hotelName) => {
    if (hotelRates[hotelName]) return;

    try {
      const response = await pricingApi.getHotelRates(hotelName);
      setHotelRates(prev => ({
        ...prev,
        [hotelName]: response.data?.data || [],
      }));
    } catch (error) {
      console.error('Failed to load hotel rates:', error);
    }
  };

  const handleExpand = (hotelName) => {
    if (expandedHotel === hotelName) {
      setExpandedHotel(null);
    } else {
      setExpandedHotel(hotelName);
      loadHotelRates(hotelName);
    }
  };

  const filteredHotels = hotels.filter(hotel => {
    if (!search) return true;
    return hotel.hotel_name?.toLowerCase().includes(search.toLowerCase());
  });

  // Group hotels by destination
  const groupedHotels = filteredHotels.reduce((acc, hotel) => {
    const dest = hotel.destination || 'Unknown';
    if (!acc[dest]) acc[dest] = [];
    acc[dest].push(hotel);
    return acc;
  }, {});

  const renderStars = (rating) => {
    if (!rating) return null;
    const numStars = parseInt(rating) || 0;
    return (
      <div className="flex items-center gap-0.5">
        {[...Array(5)].map((_, i) => (
          i < numStars ? (
            <StarIconSolid key={i} className="w-4 h-4 text-yellow-400" />
          ) : (
            <StarIcon key={i} className="w-4 h-4 text-gray-300" />
          )
        ))}
      </div>
    );
  };

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return `R ${Number(amount).toLocaleString()}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Hotels</h1>
          <p className="text-gray-500 mt-1">
            {hotels.length} hotels across {destinations.length} destinations
          </p>
        </div>
      </div>

      {/* Destination Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {destinations.map((dest) => (
          <button
            key={dest.destination}
            onClick={() => setDestinationFilter(
              destinationFilter === dest.destination ? '' : dest.destination
            )}
            className={`card p-4 text-left transition-all ${
              destinationFilter === dest.destination
                ? 'ring-2 ring-purple-500 bg-purple-50'
                : 'hover:shadow-md'
            }`}
          >
            <p className="font-semibold text-gray-900">{dest.destination}</p>
            <p className="text-sm text-gray-500">{dest.hotel_count} hotels</p>
            <p className="text-xs text-gray-400 mt-1">
              {formatCurrency(dest.min_price)} - {formatCurrency(dest.max_price)}
            </p>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search hotels..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Hotels List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : filteredHotels.length === 0 ? (
        <div className="card text-center py-12">
          <BuildingOfficeIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No hotels found</h3>
          <p className="text-gray-500 mt-1">Try adjusting your search or filters</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedHotels).map(([destination, destHotels]) => (
            <div key={destination}>
              <div className="flex items-center gap-2 mb-4">
                <MapPinIcon className="w-5 h-5 text-purple-600" />
                <h2 className="text-lg font-semibold text-gray-900">{destination}</h2>
                <span className="text-sm text-gray-500">({destHotels.length} hotels)</span>
              </div>

              <div className="space-y-3">
                {destHotels.map((hotel) => (
                  <div key={hotel.hotel_name} className="card p-0 overflow-hidden">
                    {/* Hotel Header */}
                    <div className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                      <div className="flex items-center gap-4 flex-1">
                        <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                          <BuildingOfficeIcon className="w-6 h-6 text-purple-600" />
                        </div>
                        <div className="text-left">
                          <Link 
                            to={`/pricing/hotels/${encodeURIComponent(hotel.hotel_name)}`}
                            className="font-semibold text-gray-900 hover:text-purple-600 flex items-center gap-2"
                          >
                            {hotel.hotel_name}
                            <ArrowTopRightOnSquareIcon className="w-4 h-4 opacity-50" />
                          </Link>
                          <div className="flex items-center gap-3 mt-1">
                            {renderStars(hotel.star_rating)}
                            {hotel.star_rating && (
                              <span className="text-sm text-gray-500">{hotel.star_rating}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleExpand(hotel.hotel_name)}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                      >
                        {expandedHotel === hotel.hotel_name ? (
                          <ChevronUpIcon className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronDownIcon className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                    </div>

                    {/* Expanded Rates */}
                    {expandedHotel === hotel.hotel_name && (
                      <div className="border-t border-gray-200 bg-gray-50 p-6">
                        {hotelRates[hotel.hotel_name] ? (
                          hotelRates[hotel.hotel_name].length > 0 ? (
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="text-left text-gray-500">
                                    <th className="pb-2 font-medium">Room Type</th>
                                    <th className="pb-2 font-medium">Meal Plan</th>
                                    <th className="pb-2 font-medium">Valid Period</th>
                                    <th className="pb-2 font-medium">Nights</th>
                                    <th className="pb-2 font-medium text-right">Per Person</th>
                                    <th className="pb-2 font-medium text-right">Single</th>
                                    <th className="pb-2 font-medium text-right">Child</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                  {hotelRates[hotel.hotel_name].slice(0, 10).map((rate, idx) => (
                                    <tr key={idx} className="text-gray-700">
                                      <td className="py-2">{rate.room_type}</td>
                                      <td className="py-2">
                                        <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                                          {rate.meal_plan}
                                        </span>
                                      </td>
                                      <td className="py-2 text-gray-500">
                                        {new Date(rate.check_in_date).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short' })} -
                                        {new Date(rate.check_out_date).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short' })}
                                      </td>
                                      <td className="py-2">{rate.nights}</td>
                                      <td className="py-2 text-right font-medium">{formatCurrency(rate.total_7nights_pps)}</td>
                                      <td className="py-2 text-right">{formatCurrency(rate.total_7nights_single)}</td>
                                      <td className="py-2 text-right">{formatCurrency(rate.total_7nights_child)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                              {hotelRates[hotel.hotel_name].length > 10 && (
                                <div className="mt-3 flex items-center justify-between">
                                  <p className="text-sm text-gray-500">
                                    Showing 10 of {hotelRates[hotel.hotel_name].length} rates
                                  </p>
                                  <Link 
                                    to={`/pricing/hotels/${encodeURIComponent(hotel.hotel_name)}`}
                                    className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                                  >
                                    View all rates →
                                  </Link>
                                </div>
                              )}
                            </div>
                          ) : (
                            <p className="text-gray-500 text-center py-4">No rates found for this hotel</p>
                          )
                        ) : (
                          <div className="flex items-center justify-center py-4">
                            <div className="w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}