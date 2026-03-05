import { useState, useEffect } from 'react';
import {
  SparklesIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  ClockIcon,
  UserGroupIcon,
  TagIcon,
  FunnelIcon,
  CheckCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { activitiesApi, travelApi } from '../../services/api';
import { AddToQuoteButton } from '../../components/travel/FloatingQuoteCart';
import { normalizeActivityPrice } from '../../utils/fieldTransformers';

function ActivityDetailModal({ activity, onClose, formatCurrency, participants, destinationName }) {
  if (!activity) return null;

  const { pricePerPerson } = normalizeActivityPrice(activity);
  const totalAdult = pricePerPerson ? pricePerPerson * participants : 0;
  const totalChild = activity.price_child ? activity.price_child * participants : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {activity.image_url && (
          <img
            src={activity.image_url}
            alt={activity.name}
            className="w-full h-64 object-cover rounded-t-xl"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        )}
        <div className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{activity.name}</h2>
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                {activity.category && (
                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">{activity.category}</span>
                )}
                {activity.source && (
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${activity.source === 'hotelbeds' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                    {activity.source === 'hotelbeds' ? 'Live' : activity.source.toUpperCase()}
                  </span>
                )}
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Key details grid */}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
            {activity.duration && (
              <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                <ClockIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                <div>
                  <div className="text-xs text-gray-500">Duration</div>
                  <div className="text-sm font-medium text-gray-900">{activity.duration}</div>
                </div>
              </div>
            )}
            {destinationName && (
              <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                <MapPinIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                <div>
                  <div className="text-xs text-gray-500">Destination</div>
                  <div className="text-sm font-medium text-gray-900">{destinationName}</div>
                </div>
              </div>
            )}
            <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
              <UserGroupIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
              <div>
                <div className="text-xs text-gray-500">Participants</div>
                <div className="text-sm font-medium text-gray-900">{participants} {participants === 1 ? 'person' : 'people'}</div>
              </div>
            </div>
          </div>

          {activity.description && (
            <div className="mt-4">
              <h3 className="font-medium text-gray-900 mb-2">Description</h3>
              <p className="text-gray-600 leading-relaxed">{activity.description}</p>
            </div>
          )}

          {/* Pricing breakdown */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            {activity.price_adult && activity.price_adult > 0 ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Adult x {participants}</span>
                  <span className="font-medium text-gray-900">
                    {formatCurrency(activity.price_adult, activity.currency)} each
                  </span>
                </div>
                {activity.price_child > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Child price</span>
                    <span className="font-medium text-gray-700">
                      {formatCurrency(activity.price_child, activity.currency)} each
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                  <span className="font-semibold text-gray-900">Estimated Total</span>
                  <span className="text-xl font-bold text-theme-primary">
                    {formatCurrency(activity.total_price || totalAdult, activity.currency)}
                  </span>
                </div>
                <div className="flex justify-end pt-2">
                  <AddToQuoteButton item={{ id: activity.activity_id, type: 'activity', name: activity.name, price: activity.total_price || totalAdult, currency: activity.currency || 'EUR', details: { category: activity.category, duration: activity.duration, participants, destination: destinationName || '' } }} size="md" />
                </div>
              </div>
            ) : (
              <div className="text-center py-2">
                <span className="text-lg font-medium text-amber-600">Price on request</span>
                <p className="text-sm text-gray-500 mt-1">Contact us for a customized quote</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ActivitiesList() {
  // State
  const [destinations, setDestinations] = useState([]);
  const [selectedDestination, setSelectedDestination] = useState('');
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState('sample'); // 'hotelbeds' or 'sample'
  const [participants, setParticipants] = useState(2);
  const [selectedActivity, setSelectedActivity] = useState(null);
  const [visibleCount, setVisibleCount] = useState(12);

  // Load destinations and categories on mount
  useEffect(() => {
    loadDestinations();
    loadCategories();
  }, []);

  // Load activities when destination or category changes
  useEffect(() => {
    if (selectedDestination) {
      loadActivities();
    }
  }, [selectedDestination, selectedCategory]);

  const loadDestinations = async () => {
    try {
      const response = await travelApi.destinations();
      if (response.data?.success) {
        // Filter destinations that have activities
        const withActivities = response.data.destinations.filter(d => d.activities);
        setDestinations(withActivities);
        if (withActivities.length > 0) {
          setSelectedDestination(withActivities[0].code);
        }
      }
    } catch (err) {
      console.error('Failed to load destinations:', err);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await activitiesApi.categories();
      if (response.data?.success) {
        setCategories(response.data.categories || []);
      }
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const loadActivities = async () => {
    setLoading(true);
    setError(null);
    setVisibleCount(12);

    try {
      const response = await activitiesApi.search({
        destination: selectedDestination,
        participants,
        category: selectedCategory || undefined,
        query: searchQuery || undefined,
      });

      if (response.data?.success) {
        const results = response.data.activities || [];
        setActivities(results);
        // Detect source: if any activity has source 'hotelbeds', it's live Cloud Run data
        const isLive = results.some(a => a.source === 'hotelbeds');
        setDataSource(isLive ? 'hotelbeds' : 'sample');
      } else {
        setError(response.data?.error || 'Failed to load activities');
      }
    } catch (err) {
      console.error('Activities load error:', err);
      setError('Failed to load activities');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadActivities();
  };

  const formatCurrency = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Cultural': 'bg-purple-100 text-purple-800',
      'Water Sports': 'bg-blue-100 text-blue-800',
      'Nature': 'bg-green-100 text-green-800',
      'Adventure': 'bg-red-100 text-red-800',
      'Safari': 'bg-amber-100 text-amber-800',
      'Cruises': 'bg-cyan-100 text-cyan-800',
      'Beach': 'bg-teal-100 text-teal-800',
      'Fishing': 'bg-indigo-100 text-indigo-800',
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activities & Excursions</h1>
          <p className="text-gray-500 mt-1">Browse tours, activities and experiences by destination</p>
        </div>
        {dataSource === 'hotelbeds' ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
            <CheckCircleIcon className="h-4 w-4" />
            Live Data
          </span>
        ) : (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800">
            Sample Data
          </span>
        )}
      </div>

      {/* Data Source Notice */}
      {dataSource === 'hotelbeds' ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <CheckCircleIcon className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-green-800">Live Activities</h4>
              <p className="text-sm text-green-700 mt-1">
                Showing real-time activity availability and pricing. Prices are in EUR.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="font-medium text-amber-800">Demo Activities</h4>
              <p className="text-sm text-amber-700 mt-1">
                Live activities not available for this destination. Showing sample data for demonstration.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
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

            {/* Participants */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <UserGroupIcon className="h-4 w-4 inline mr-1" />
                Participants
              </label>
              <select
                value={participants}
                onChange={(e) => setParticipants(parseInt(e.target.value))}
                className="input"
              >
                {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => (
                  <option key={n} value={n}>{n} {n === 1 ? 'person' : 'people'}</option>
                ))}
              </select>
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <FunnelIcon className="h-4 w-4 inline mr-1" />
                Category
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="input"
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            {/* Search Query */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <MagnifyingGlassIcon className="h-4 w-4 inline mr-1" />
                Search
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search activities..."
                className="input"
              />
            </div>

            {/* Search Button */}
            <div className="flex items-end">
              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
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
                    Search
                  </>
                )}
              </button>
            </div>
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden animate-pulse">
              <div className="h-48 bg-gray-200"></div>
              <div className="p-4 space-y-3">
                <div className="h-5 bg-gray-200 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded w-full"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
            </div>
          ))}
        </div>
      ) : activities.length > 0 ? (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {activities.length} Activities in {destinations.find(d => d.code === selectedDestination)?.name || selectedDestination}
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {activities.slice(0, visibleCount).map((activity) => (
              <div
                key={activity.activity_id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setSelectedActivity(activity)}
              >
                {/* Activity Image */}
                <div className="relative h-48">
                  {activity.image_url ? (
                    <img
                      src={activity.image_url}
                      alt={activity.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // Replace broken image with placeholder icon
                        e.target.style.display = 'none';
                        e.target.parentElement.classList.add('bg-gradient-to-br', 'from-blue-50', 'to-purple-50');
                        e.target.parentElement.innerHTML = '<div class="w-full h-full flex items-center justify-center"><svg class="h-12 w-12 text-blue-300" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg></div>';
                      }}
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center">
                      <SparklesIcon className="h-12 w-12 text-blue-300" />
                    </div>
                  )}
                  {/* Category Badge */}
                  {activity.category && (
                    <span className={`absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(activity.category)}`}>
                      {activity.category}
                    </span>
                  )}
                </div>

                {/* Activity Info */}
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {activity.name}
                    </h3>
                    {activity.source && (
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        activity.source === 'hotelbeds' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {activity.source === 'hotelbeds' ? 'Live' : activity.source.toUpperCase()}
                      </span>
                    )}
                  </div>

                  {activity.description && (
                    <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                      {activity.description}
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
                    {activity.duration && (
                      <span className="flex items-center">
                        <ClockIcon className="h-4 w-4 mr-1" />
                        {activity.duration}
                      </span>
                    )}
                  </div>

                  {/* Pricing */}
                  <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                    <div>
                      {activity.price_adult && activity.price_adult > 0 ? (
                        <>
                          <div className="flex items-center gap-2">
                            <UserGroupIcon className="h-4 w-4 text-gray-400" />
                            <span className="text-sm text-gray-600">Adult</span>
                            <span className="font-semibold text-gray-900">
                              {formatCurrency(activity.price_adult, activity.currency)}
                            </span>
                          </div>
                          {activity.price_child && activity.price_child > 0 && (
                            <div className="flex items-center gap-2 mt-1">
                              <div className="h-4 w-4"></div>
                              <span className="text-sm text-gray-600">Child</span>
                              <span className="font-medium text-gray-700">
                                {formatCurrency(activity.price_child, activity.currency)}
                              </span>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="flex items-center gap-2">
                          <UserGroupIcon className="h-4 w-4 text-gray-400" />
                          <span className="text-sm italic text-amber-600 font-medium">
                            Price on request
                          </span>
                        </div>
                      )}
                    </div>
                    {normalizeActivityPrice(activity).pricePerPerson > 0 ? (
                      <div onClick={e => e.stopPropagation()}>
                        <AddToQuoteButton
                          item={{
                            id: activity.activity_id,
                            type: 'activity',
                            name: activity.name,
                            price: activity.total_price || normalizeActivityPrice(activity).pricePerPerson * participants,
                            currency: activity.currency || 'EUR',
                            details: {
                              category: activity.category,
                              duration: activity.duration,
                              participants: participants,
                              destination: selectedDestination,
                            }
                          }}
                          size="sm"
                        />
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400 px-3 py-1 bg-gray-100 rounded-full">
                        Contact for pricing
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          {activities.length > visibleCount && (
            <div className="flex justify-center pt-6">
              <button
                onClick={() => setVisibleCount(prev => prev + 12)}
                className="px-6 py-2.5 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                Show more ({activities.length - visibleCount} remaining)
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <SparklesIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No Activities Found</h3>
          <p className="mt-2 text-gray-500">
            Try selecting a different destination or adjusting your filters.
          </p>
        </div>
      )}

      {selectedActivity && (
        <ActivityDetailModal
          activity={selectedActivity}
          onClose={() => setSelectedActivity(null)}
          formatCurrency={formatCurrency}
          participants={participants}
          destinationName={destinations.find(d => d.code === selectedDestination)?.name || selectedDestination}
        />
      )}
    </div>
  );
}
