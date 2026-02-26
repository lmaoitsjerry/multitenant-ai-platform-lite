import {
  FunnelIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';

// ==================== Shared Filter Sidebar Component ====================
// Extracted from HotelsList.jsx for reuse across travel pages (HotelsList, HolidayPackages, etc.)
export default function FilterSidebar({
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
  ) || filters.priceMin > 0 || (filters.priceMax != null && isFinite(filters.priceMax));

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
