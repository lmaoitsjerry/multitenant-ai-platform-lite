import { useState } from 'react';
import {
  CalendarIcon,
  MapPinIcon,
  CheckCircleIcon,
  XCircleIcon,
  XMarkIcon,
  WifiIcon,
  GlobeAltIcon,
  StarIcon,
  BuildingOfficeIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import { AddToQuoteButton } from './FloatingQuoteCart';

function renderStars(count) {
  if (!count) return null;
  return (
    <div className="flex items-center gap-0.5">
      {[...Array(5)].map((_, i) =>
        i < count ? (
          <StarIconSolid key={i} className="h-4 w-4 text-yellow-400" />
        ) : (
          <StarIcon key={i} className="h-4 w-4 text-gray-300" />
        )
      )}
    </div>
  );
}

function formatRoomType(type) {
  if (!type) return 'Standard Room';
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getProviderStyle(provider) {
  if (!provider) return 'bg-gray-100 text-gray-600';
  const p = provider.toLowerCase();
  if (p === 'hotelbeds') return 'bg-orange-100 text-orange-700';
  if (p === 'juniper') return 'bg-blue-100 text-blue-700';
  if (p === 'hummingbird') return 'bg-green-100 text-green-700';
  if (p === 'rttc') return 'bg-purple-100 text-purple-700';
  if (p === 'bigquery') return 'bg-cyan-100 text-cyan-700';
  return 'bg-gray-100 text-gray-600';
}

const AMENITY_ICONS = {
  wifi: WifiIcon,
  internet: WifiIcon,
  pool: GlobeAltIcon,
  swim: GlobeAltIcon,
};

function getAmenityIcon(amenity) {
  const lower = amenity.toLowerCase();
  for (const [keyword, Icon] of Object.entries(AMENITY_ICONS)) {
    if (lower.includes(keyword)) return Icon;
  }
  return CheckCircleIcon;
}

// ---------------------------------------------------------------------------
// Image Gallery — handles single image_url OR images[] array
// ---------------------------------------------------------------------------
function ImageGallery({ hotel }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [imgError, setImgError] = useState({});

  // Build image list: prefer images array, fall back to single image_url
  const allImages = [];
  if (hotel.images && Array.isArray(hotel.images) && hotel.images.length > 0) {
    hotel.images.forEach((img) => {
      const url = typeof img === 'string' ? img : img?.url || img?.image_url;
      if (url) allImages.push(url);
    });
  }
  if (allImages.length === 0 && hotel.image_url) {
    allImages.push(hotel.image_url);
  }

  if (allImages.length === 0) {
    return (
      <div className="w-full h-72 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center rounded-t-xl">
        <BuildingOfficeIcon className="h-16 w-16 text-gray-400" />
      </div>
    );
  }

  // Filter out errored images
  const validImages = allImages.filter((_, i) => !imgError[i]);
  if (validImages.length === 0) {
    return (
      <div className="w-full h-72 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center rounded-t-xl">
        <BuildingOfficeIcon className="h-16 w-16 text-gray-400" />
      </div>
    );
  }

  const safeIndex = Math.min(currentIndex, validImages.length - 1);
  const showNav = validImages.length > 1;

  return (
    <div className="relative w-full h-72 bg-gray-900 rounded-t-xl overflow-hidden group">
      <img
        src={validImages[safeIndex]}
        alt={`${hotel.hotel_name} - ${safeIndex + 1}`}
        className="w-full h-full object-cover"
        onError={() => {
          const originalIndex = allImages.indexOf(validImages[safeIndex]);
          setImgError(prev => ({ ...prev, [originalIndex]: true }));
        }}
      />
      {/* Gradient overlay at bottom */}
      <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/40 to-transparent" />
      {/* Navigation arrows */}
      {showNav && (
        <>
          <button
            onClick={(e) => { e.stopPropagation(); setCurrentIndex((safeIndex - 1 + validImages.length) % validImages.length); }}
            className="absolute left-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-black/40 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/60"
          >
            <ChevronLeftIcon className="h-5 w-5" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); setCurrentIndex((safeIndex + 1) % validImages.length); }}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-black/40 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/60"
          >
            <ChevronRightIcon className="h-5 w-5" />
          </button>
          {/* Dots indicator */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
            {validImages.map((_, i) => (
              <button
                key={i}
                onClick={(e) => { e.stopPropagation(); setCurrentIndex(i); }}
                className={`w-2 h-2 rounded-full transition-all ${i === safeIndex ? 'bg-white w-4' : 'bg-white/50 hover:bg-white/75'}`}
              />
            ))}
          </div>
        </>
      )}
      {/* Image counter */}
      {showNav && (
        <span className="absolute top-3 right-3 bg-black/50 text-white text-xs px-2 py-1 rounded-full">
          {safeIndex + 1} / {validImages.length}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Description with expand/collapse
// ---------------------------------------------------------------------------
function DescriptionSection({ description }) {
  const [expanded, setExpanded] = useState(false);
  if (!description) return null;

  const isLong = description.length > 300;

  return (
    <div>
      <h3 className="font-semibold text-gray-900 mb-2">About This Hotel</h3>
      <p className={`text-gray-600 leading-relaxed text-sm ${!expanded && isLong ? 'line-clamp-4' : ''}`}>
        {description}
      </p>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1 text-sm text-theme-primary hover:underline inline-flex items-center gap-0.5"
        >
          {expanded ? (
            <><ChevronUpIcon className="h-4 w-4" /> Show less</>
          ) : (
            <><ChevronDownIcon className="h-4 w-4" /> Read more</>
          )}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Location section
// ---------------------------------------------------------------------------
function LocationSection({ hotel }) {
  const hasCoords = hotel.latitude && hotel.longitude;
  const hasLocation = hotel.zone || hotel.address || hasCoords;

  if (!hasLocation) return null;

  const mapUrl = hasCoords
    ? `https://www.google.com/maps?q=${hotel.latitude},${hotel.longitude}`
    : null;

  return (
    <div>
      <h3 className="font-semibold text-gray-900 mb-2">Location</h3>
      <div className="space-y-1.5">
        {hotel.address && (
          <p className="text-sm text-gray-600">{hotel.address}</p>
        )}
        {hotel.zone && (
          <p className="text-sm text-gray-500 inline-flex items-center gap-1">
            <MapPinIcon className="h-4 w-4 flex-shrink-0" /> {hotel.zone}
          </p>
        )}
        {mapUrl && (
          <a
            href={mapUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-theme-primary hover:underline mt-1"
          >
            <GlobeAltIcon className="h-4 w-4" /> View on Google Maps
          </a>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Facilities/Amenities section
// ---------------------------------------------------------------------------
function FacilitiesSection({ amenities }) {
  const [showAll, setShowAll] = useState(false);
  if (!amenities || amenities.length === 0) return null;

  const INITIAL_COUNT = 12;
  const displayAmenities = showAll ? amenities : amenities.slice(0, INITIAL_COUNT);

  return (
    <div>
      <h3 className="font-semibold text-gray-900 mb-2">Facilities & Amenities</h3>
      <div className="flex flex-wrap gap-2">
        {displayAmenities.map((amenity, i) => {
          const Icon = getAmenityIcon(amenity);
          return (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 border border-gray-200 text-gray-700 rounded-lg text-xs"
            >
              <Icon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
              {amenity}
            </span>
          );
        })}
      </div>
      {amenities.length > INITIAL_COUNT && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-2 text-sm text-theme-primary hover:underline"
        >
          {showAll ? 'Show fewer' : `Show all ${amenities.length} amenities`}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Room Options section
// ---------------------------------------------------------------------------
function RoomOptionsSection({ hotel, checkIn, checkOut, formatCurrency }) {
  if (!hotel.options || hotel.options.length === 0) return null;

  return (
    <div>
      <h3 className="font-semibold text-gray-900 mb-3">
        Room Options <span className="text-sm font-normal text-gray-500">({hotel.options.length})</span>
      </h3>
      <div className="space-y-2">
        {hotel.options.map((option, idx) => (
          <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-gray-900">{formatRoomType(option.room_type)}</span>
                  {option.meal_plan && (
                    <>
                      <span className="text-gray-400">&middot;</span>
                      <span className="text-gray-600 text-sm">{option.meal_plan}</span>
                    </>
                  )}
                  {(option.source || option.provider) && (
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${getProviderStyle(option.source || option.provider)}`}>
                      {(option.source || option.provider) === 'hotelbeds' ? 'HotelBeds'
                        : (option.source || option.provider) === 'juniper' ? 'Juniper'
                        : (option.source || option.provider)}
                    </span>
                  )}
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
                </div>
                {(option.bed_type || option.view || option.room_size) && (
                  <div className="text-xs text-gray-500 mt-1 flex items-center gap-2 flex-wrap">
                    {option.bed_type && <span>{option.bed_type}</span>}
                    {option.view && <><span className="text-gray-300">&middot;</span><span>{option.view}</span></>}
                    {option.room_size && <><span className="text-gray-300">&middot;</span><span>{option.room_size}</span></>}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                <div className="text-right">
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(
                      option.rate_per_night_zar || option.price_total || option.price_per_night || 0,
                      option.rate_per_night_zar ? 'ZAR' : option.currency || 'ZAR'
                    )}
                  </span>
                  {(option.price_per_night || option.rate_per_night) && (
                    <div className="text-xs text-gray-500">
                      {formatCurrency(option.price_per_night || option.rate_per_night, option.currency || 'ZAR')}/night
                    </div>
                  )}
                </div>
                <AddToQuoteButton
                  item={{
                    id: `${hotel.hotel_id}-${idx}`,
                    type: 'hotel',
                    name: hotel.hotel_name,
                    price: option.rate_per_night_zar || option.price_total || option.price_per_night || 0,
                    currency: option.rate_per_night_zar ? 'ZAR' : option.currency || 'ZAR',
                    details: {
                      hotel_id: hotel.hotel_id,
                      room_type: option.room_type,
                      meal_plan: option.meal_plan,
                      stars: hotel.stars || hotel.star_rating,
                      check_in: checkIn,
                      check_out: checkOut,
                    },
                  }}
                  size="sm"
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Modal Component
// ---------------------------------------------------------------------------
export default function HotelDetailModal({ hotel, onClose, checkIn, checkOut, nights, formatCurrency: formatCurrencyProp }) {
  const [activeTab, setActiveTab] = useState('details');

  if (!hotel) return null;

  const formatCurrency = formatCurrencyProp || ((amount, currency = 'ZAR') => {
    if (!amount) return '-';
    return `${currency} ${Number(amount).toLocaleString()}`;
  });

  const hasDetails = hotel.description || hotel.address || hotel.zone || hotel.latitude;
  const hasFacilities = hotel.amenities && hotel.amenities.length > 0;
  const hasRooms = hotel.options && hotel.options.length > 0;

  // Determine which tabs to show
  const tabs = [];
  if (hasDetails || !hasFacilities) tabs.push({ id: 'details', label: 'Details' });
  if (hasFacilities) tabs.push({ id: 'facilities', label: 'Facilities' });
  if (hasRooms) tabs.push({ id: 'rooms', label: `Rooms (${hotel.options.length})` });

  // If no tabs have content, default to details
  if (tabs.length === 0) tabs.push({ id: 'details', label: 'Details' });

  // Ensure active tab is valid
  const validTab = tabs.find(t => t.id === activeTab) ? activeTab : tabs[0].id;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
        {/* Image Gallery */}
        <ImageGallery hotel={hotel} />

        {/* Header */}
        <div className="px-6 pt-5 pb-0">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-2xl font-bold text-gray-900">{hotel.hotel_name}</h2>
                {hotel.sources && hotel.sources.length > 0 && hotel.sources.map((src, i) => (
                  <span key={i} className={`px-2 py-0.5 rounded-full text-xs font-medium ${getProviderStyle(src)}`}>
                    {src.toUpperCase()}
                  </span>
                ))}
                {!hotel.sources?.length && (hotel.source || hotel.provider) && (
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getProviderStyle(hotel.source || hotel.provider)}`}>
                    {(hotel.source || hotel.provider).toUpperCase()}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                {renderStars(hotel.stars || hotel.star_rating)}
                {hotel.zone && (
                  hotel.latitude && hotel.longitude ? (
                    <a
                      href={`https://www.google.com/maps?q=${hotel.latitude},${hotel.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-theme-primary hover:underline inline-flex items-center gap-0.5"
                    >
                      <MapPinIcon className="h-4 w-4" /> {hotel.zone}
                    </a>
                  ) : (
                    <span className="text-sm text-gray-500 inline-flex items-center gap-0.5">
                      <MapPinIcon className="h-4 w-4" /> {hotel.zone}
                    </span>
                  )
                )}
                {hotel.cheapest_price && (
                  <span className="text-sm font-semibold text-theme-primary ml-auto">
                    From {formatCurrency(hotel.cheapest_price, 'ZAR')}/night
                  </span>
                )}
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 ml-2 flex-shrink-0">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Trip Details Bar */}
          {(checkIn || checkOut || nights > 0) && (
            <div className="mt-4 flex items-center gap-4 text-sm bg-blue-50 rounded-lg p-3">
              {checkIn && <span className="text-blue-700"><CalendarIcon className="h-4 w-4 inline mr-1" />Check-in: {checkIn}</span>}
              {checkOut && <span className="text-blue-700"><CalendarIcon className="h-4 w-4 inline mr-1" />Check-out: {checkOut}</span>}
              {nights > 0 && <span className="text-blue-700 font-medium">{nights} night{nights !== 1 ? 's' : ''}</span>}
            </div>
          )}

          {/* Tab Navigation */}
          {tabs.length > 1 && (
            <div className="mt-4 flex border-b border-gray-200">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                    validTab === tab.id
                      ? 'border-theme-primary text-theme-primary'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Tab Content — scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {validTab === 'details' && (
            <div className="space-y-5">
              <DescriptionSection description={hotel.description} />
              <LocationSection hotel={hotel} />
              {/* If no description and no location, show a minimal message */}
              {!hotel.description && !hotel.zone && !hotel.address && (
                <p className="text-sm text-gray-400 italic">
                  Detailed hotel information is not available for this property. Please see room options for pricing and availability.
                </p>
              )}
            </div>
          )}

          {validTab === 'facilities' && (
            <FacilitiesSection amenities={hotel.amenities} />
          )}

          {validTab === 'rooms' && (
            <RoomOptionsSection hotel={hotel} checkIn={checkIn} checkOut={checkOut} formatCurrency={formatCurrency} />
          )}

          {/* When only one tab exists, show rooms inline below details */}
          {tabs.length <= 1 && hasRooms && (
            <div className="mt-5 pt-5 border-t border-gray-200">
              <RoomOptionsSection hotel={hotel} checkIn={checkIn} checkOut={checkOut} formatCurrency={formatCurrency} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
