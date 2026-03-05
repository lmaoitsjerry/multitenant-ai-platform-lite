import { createContext, useContext, useState, useEffect, useCallback } from 'react';

/**
 * Quote Cart Context
 *
 * Manages a shopping-cart-like experience for building quotes from Travel Services.
 * Items can be hotels, activities, flights, transfers, or packages.
 */

const QuoteCartContext = createContext(null);

const CART_STORAGE_KEY = 'quote_cart';

export function QuoteCartProvider({ children }) {
  const [items, setItems] = useState([]);
  const [isExpanded, setIsExpanded] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(CART_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Validate it's an array
        if (Array.isArray(parsed)) {
          setItems(parsed);
        }
      }
    } catch (e) {
      console.warn('Failed to load cart from storage:', e);
    }
  }, []);

  // Save to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      console.warn('Failed to save cart to storage:', e);
    }
  }, [items]);

  /**
   * Add an item to the cart
   * @param {Object} item - Item to add
   * @param {string} item.id - Unique identifier
   * @param {string} item.type - hotel, activity, flight, transfer, package
   * @param {string} item.name - Display name
   * @param {number} item.price - Total price
   * @param {string} item.currency - Currency code (EUR, ZAR, etc.)
   * @param {Object} item.details - Type-specific details (room_type, meal_plan, dates, etc.)
   */
  const addItem = useCallback((item) => {
    setItems(prev => {
      // Check if item already exists
      const exists = prev.some(i => i.id === item.id && i.type === item.type);
      if (exists) {
        // Update existing item
        return prev.map(i =>
          i.id === item.id && i.type === item.type ? { ...i, ...item } : i
        );
      }
      // Add new item
      return [...prev, { ...item, addedAt: new Date().toISOString() }];
    });
    // Expand cart when item is added
    setIsExpanded(true);
  }, []);

  /**
   * Remove an item from the cart
   * @param {string} id - Item ID
   * @param {string} type - Item type
   */
  const removeItem = useCallback((id, type) => {
    setItems(prev => prev.filter(i => !(i.id === id && i.type === type)));
  }, []);

  /**
   * Check if an item is in the cart
   */
  const isInCart = useCallback((id, type) => {
    return items.some(i => i.id === id && i.type === type);
  }, [items]);

  /**
   * Clear all items from the cart
   */
  const clearCart = useCallback(() => {
    setItems([]);
    setIsExpanded(false);
  }, []);

  /**
   * Get total price of all items
   */
  const getTotal = useCallback(() => {
    // Group by currency and sum
    const totals = items.reduce((acc, item) => {
      const currency = item.currency || 'ZAR';
      acc[currency] = (acc[currency] || 0) + (item.price || 0);
      return acc;
    }, {});
    return totals;
  }, [items]);

  /**
   * Toggle cart expanded state
   */
  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  /**
   * Get items formatted for quote creation
   */
  const getQuoteItems = useCallback(() => {
    return items.map(item => ({
      type: item.type,
      name: item.name,
      price: item.price,
      currency: item.currency,
      ...item.details
    }));
  }, [items]);

  const value = {
    items,
    itemCount: items.length,
    isExpanded,
    setIsExpanded,
    toggleExpanded,
    addItem,
    removeItem,
    isInCart,
    clearCart,
    getTotal,
    getQuoteItems,
  };

  return (
    <QuoteCartContext.Provider value={value}>
      {children}
    </QuoteCartContext.Provider>
  );
}

export function useQuoteCart() {
  const context = useContext(QuoteCartContext);
  if (!context) {
    throw new Error('useQuoteCart must be used within a QuoteCartProvider');
  }
  return context;
}

export default QuoteCartContext;
