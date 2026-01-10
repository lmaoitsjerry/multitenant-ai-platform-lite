/**
 * Prefetch Hooks
 *
 * Provides prefetching capabilities for faster navigation.
 * Data is loaded on hover so it's ready when user clicks.
 */

import { useCallback, useRef } from 'react';

// Simple in-memory cache for prefetched data
const prefetchCache = new Map();
const PREFETCH_STALE_TIME = 60000; // 1 minute

/**
 * Check if cached data is still fresh
 */
function isCacheFresh(key) {
  const cached = prefetchCache.get(key);
  if (!cached) return false;
  return Date.now() - cached.timestamp < PREFETCH_STALE_TIME;
}

/**
 * Generic prefetch hook
 * @param {Function} fetchFn - Function to fetch data
 * @param {string} cacheKey - Key to cache the result
 * @returns {Object} - { prefetch, getCached }
 */
export function usePrefetch(fetchFn, cacheKey) {
  const pendingRef = useRef(false);

  const prefetch = useCallback(async () => {
    // Don't prefetch if already cached and fresh
    if (isCacheFresh(cacheKey) || pendingRef.current) {
      return;
    }

    pendingRef.current = true;

    try {
      const data = await fetchFn();
      prefetchCache.set(cacheKey, {
        data,
        timestamp: Date.now(),
      });
    } catch (error) {
      console.debug(`Prefetch failed for ${cacheKey}:`, error);
    } finally {
      pendingRef.current = false;
    }
  }, [fetchFn, cacheKey]);

  const getCached = useCallback(() => {
    const cached = prefetchCache.get(cacheKey);
    return cached?.data || null;
  }, [cacheKey]);

  return { prefetch, getCached };
}

/**
 * Prefetch on hover handler
 * Returns props to spread on hoverable elements
 */
export function usePrefetchOnHover(fetchFn, cacheKey) {
  const { prefetch } = usePrefetch(fetchFn, cacheKey);
  const timeoutRef = useRef(null);

  const onMouseEnter = useCallback(() => {
    // Small delay to avoid prefetching when user just passes over
    timeoutRef.current = setTimeout(() => {
      prefetch();
    }, 100);
  }, [prefetch]);

  const onMouseLeave = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  return { onMouseEnter, onMouseLeave };
}

/**
 * Clear all prefetch cache
 */
export function clearPrefetchCache() {
  prefetchCache.clear();
}

/**
 * Clear specific cache entry
 */
export function clearPrefetchCacheKey(key) {
  prefetchCache.delete(key);
}

export default usePrefetch;
