import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuoteCart } from '../../context/QuoteCartContext';
import CreateQuoteModal from './CreateQuoteModal';
import {
  ShoppingCartIcon,
  XMarkIcon,
  TrashIcon,
  BuildingOfficeIcon,
  TicketIcon,
  PaperAirplaneIcon,
  TruckIcon,
  GiftIcon,
  ChevronRightIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';

// Type icon mapping
const typeIcons = {
  hotel: BuildingOfficeIcon,
  activity: TicketIcon,
  flight: PaperAirplaneIcon,
  transfer: TruckIcon,
  package: GiftIcon,
};

// Type label mapping
const typeLabels = {
  hotel: 'Hotel',
  activity: 'Activity',
  flight: 'Flight',
  transfer: 'Transfer',
  package: 'Package',
};

// Type color mapping
const typeColors = {
  hotel: 'bg-blue-100 text-blue-700',
  activity: 'bg-green-100 text-green-700',
  flight: 'bg-purple-100 text-purple-700',
  transfer: 'bg-orange-100 text-orange-700',
  package: 'bg-pink-100 text-pink-700',
};

function formatCurrency(amount, currency = 'ZAR') {
  if (!amount && amount !== 0) return '-';
  const formatter = new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  return formatter.format(amount);
}

export default function FloatingQuoteCart() {
  const navigate = useNavigate();
  const location = useLocation();
  const [showQuoteModal, setShowQuoteModal] = useState(false);
  const [includeFlights, setIncludeFlights] = useState(false);
  const {
    items,
    itemCount,
    isExpanded,
    toggleExpanded,
    setIsExpanded,
    removeItem,
    clearCart,
    getTotal,
  } = useQuoteCart();

  // Only show on Travel Services pages and quotes page
  // Hide on all other pages (website, knowledge, dashboard, crm, invoices, analytics, settings)
  const allowedRoutes = ['/travel', '/quotes'];
  const showCart = allowedRoutes.some(route => location.pathname.startsWith(route));

  // Always hide on non-travel pages, regardless of whether there are items in cart
  if (!showCart) {
    return null;
  }

  const totals = getTotal();
  const currencies = Object.keys(totals);

  const handleCreateQuote = () => {
    // Open the quote creation modal
    setShowQuoteModal(true);
  };

  const handleAddMore = () => {
    // Close modal and panel, navigate to travel services
    setShowQuoteModal(false);
    setIsExpanded(false);
    navigate('/travel/hotels');
  };

  return (
    <>
      {/* Collapsed Button */}
      {!isExpanded && (
        <button
          onClick={toggleExpanded}
          className="fixed right-6 bottom-6 z-50 flex items-center gap-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] text-white px-4 py-3 rounded-full shadow-lg hover:shadow-xl transition-all duration-200"
        >
          <ShoppingCartIcon className="h-5 w-5" />
          <span className="font-medium">Quote Builder</span>
          {itemCount > 0 && (
            <span className="flex items-center justify-center min-w-[1.5rem] h-6 px-1.5 bg-white text-purple-600 rounded-full text-sm font-bold">
              {itemCount}
            </span>
          )}
        </button>
      )}

      {/* Expanded Panel */}
      {isExpanded && (
        <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col border-l border-gray-200">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-[var(--color-primary)] text-white">
            <div className="flex items-center gap-2">
              <ShoppingCartIcon className="h-5 w-5" />
              <h3 className="font-semibold">Quote Builder</h3>
              {itemCount > 0 && (
                <span className="bg-white/20 px-2 py-0.5 rounded-full text-sm">
                  {itemCount} items
                </span>
              )}
            </div>
            <button
              onClick={toggleExpanded}
              className="p-1 hover:bg-white/20 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Items List */}
          <div className="flex-1 overflow-y-auto p-4">
            {items.length === 0 ? (
              <div className="text-center py-12">
                <ShoppingCartIcon className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                <h4 className="text-gray-500 font-medium mb-2">Your quote is empty</h4>
                <p className="text-sm text-gray-400">
                  Search for hotels, activities, or other services and click "Add to Quote" to build your custom package.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item) => {
                  const TypeIcon = typeIcons[item.type] || GiftIcon;
                  const typeColor = typeColors[item.type] || 'bg-gray-100 text-gray-700';

                  return (
                    <div
                      key={`${item.type}-${item.id}`}
                      className="bg-gray-50 rounded-lg p-3 border border-gray-200 hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${typeColor}`}>
                          <TypeIcon className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="font-medium text-gray-900 truncate">
                                {item.name}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                {typeLabels[item.type] || item.type}
                                {item.details?.room_type && ` - ${item.details.room_type}`}
                                {item.details?.meal_plan && ` - ${item.details.meal_plan}`}
                              </p>
                            </div>
                            <button
                              onClick={() => removeItem(item.id, item.type)}
                              className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                              title="Remove from quote"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </div>
                          <div className="flex items-center justify-between mt-2">
                            <span className="text-sm font-semibold text-purple-600">
                              {formatCurrency(item.price, item.currency)}
                            </span>
                            {item.details?.check_in && (
                              <span className="text-xs text-gray-400">
                                {item.details.check_in}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          {items.length > 0 && (
            <div className="border-t border-gray-200 p-4 bg-gray-50">
              {/* Totals */}
              <div className="mb-4">
                <div className="flex items-center justify-between text-sm text-gray-500 mb-1">
                  <span>Estimated Total</span>
                  <button
                    onClick={clearCart}
                    className="text-red-500 hover:text-red-700 text-xs"
                  >
                    Clear all
                  </button>
                </div>
                {currencies.map(currency => (
                  <div key={currency} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">{currency}</span>
                    <span className="text-xl font-bold text-gray-900">
                      {formatCurrency(totals[currency], currency)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Include Flights Option */}
              <div className="flex items-center gap-2 mb-3">
                <input
                  type="checkbox"
                  id="cart_include_flights"
                  checked={includeFlights}
                  onChange={(e) => setIncludeFlights(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                />
                <label htmlFor="cart_include_flights" className="text-sm text-gray-600 flex items-center gap-1.5">
                  <PaperAirplaneIcon className="h-3.5 w-3.5 text-purple-500" />
                  Include flights
                </label>
              </div>

              {/* Create Quote Button */}
              <button
                onClick={handleCreateQuote}
                className="w-full flex items-center justify-center gap-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] text-white py-3 px-4 rounded-lg font-medium transition-all shadow-sm hover:shadow"
              >
                Create Quote
                <ChevronRightIcon className="h-4 w-4" />
              </button>

              <p className="text-xs text-center text-gray-400 mt-2">
                You'll be able to add customer details on the next step
              </p>
            </div>
          )}
        </div>
      )}

      {/* Backdrop when expanded */}
      {isExpanded && (
        <div
          className="fixed inset-0 bg-black/20 z-40"
          onClick={toggleExpanded}
        />
      )}

      {/* Quote Creation Modal */}
      <CreateQuoteModal
        isOpen={showQuoteModal}
        onClose={() => setShowQuoteModal(false)}
        items={items}
        totals={totals}
        onRemoveItem={removeItem}
        onClearCart={clearCart}
        onAddMore={handleAddMore}
        initialIncludeFlights={includeFlights}
      />
    </>
  );
}

/**
 * Add to Quote Button Component
 * Use this on travel service result cards
 */
export function AddToQuoteButton({
  item,
  size = 'md',
  className = '',
}) {
  const { addItem, removeItem, isInCart } = useQuoteCart();
  const inCart = isInCart(item.id, item.type);

  const handleClick = (e) => {
    e.stopPropagation();
    if (inCart) {
      removeItem(item.id, item.type);
    } else {
      addItem(item);
    }
  };

  const sizes = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  return (
    <button
      onClick={handleClick}
      className={`
        inline-flex items-center gap-1.5 font-medium rounded-lg transition-all
        ${sizes[size]}
        ${inCart
          ? 'bg-green-100 text-green-700 hover:bg-green-200'
          : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
        }
        ${className}
      `}
    >
      {inCart ? (
        <>
          <XMarkIcon className="h-4 w-4" />
          Remove
        </>
      ) : (
        <>
          <PlusIcon className="h-4 w-4" />
          Add to Quote
        </>
      )}
    </button>
  );
}
