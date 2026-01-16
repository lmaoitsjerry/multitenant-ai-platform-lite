import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { clientApi } from '../services/api';
import { useAuth } from './AuthContext';

const AppContext = createContext(null);

// Client info cache in localStorage for instant load
const CLIENT_INFO_CACHE_KEY = 'client_info_cache';

function getCachedClientInfo() {
  try {
    const cached = localStorage.getItem(CLIENT_INFO_CACHE_KEY);
    if (cached) {
      const { data, timestamp } = JSON.parse(cached);
      // Use cached data if less than 30 minutes old
      if (Date.now() - timestamp < 30 * 60 * 1000) {
        return data;
      }
    }
  } catch (e) {
    // Ignore localStorage errors
  }
  return null;
}

function setCachedClientInfo(data) {
  try {
    localStorage.setItem(CLIENT_INFO_CACHE_KEY, JSON.stringify({
      data,
      timestamp: Date.now()
    }));
  } catch (e) {
    // Ignore localStorage errors
  }
}

export function AppProvider({ children }) {
  const { isAuthenticated, loading: authLoading } = useAuth();
  // Initialize with cached data for instant display
  const [clientInfo, setClientInfo] = useState(() => getCachedClientInfo());
  // Don't block on loading if we have cached data
  const [loading, setLoading] = useState(() => !getCachedClientInfo());
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  // Sidebar pinned state - persisted in localStorage
  const [sidebarPinned, setSidebarPinned] = useState(() => {
    const stored = localStorage.getItem('sidebarPinned');
    return stored === 'true';
  });
  // Sidebar hover state - shared so Layout can respond
  const [sidebarHovered, setSidebarHovered] = useState(false);
  const hasLoadedRef = useRef(false);

  // Computed: sidebar is expanded when pinned OR hovered
  const sidebarExpanded = sidebarPinned || sidebarHovered;

  // Persist sidebar pinned state
  const toggleSidebarPinned = () => {
    setSidebarPinned(prev => {
      const newValue = !prev;
      localStorage.setItem('sidebarPinned', String(newValue));
      return newValue;
    });
  };

  // Wait for auth to be checked, then load client info only when authenticated
  useEffect(() => {
    // Don't do anything while auth is still loading
    if (authLoading) {
      return;
    }

    // If authenticated and haven't loaded yet, load client info
    if (isAuthenticated && !hasLoadedRef.current) {
      hasLoadedRef.current = true;
      // Small delay to ensure auth tokens are fully settled before making API calls
      // This prevents race conditions where API call fires before token is ready
      const timeoutId = setTimeout(() => {
        loadClientInfo();
      }, 50);
      return () => clearTimeout(timeoutId);
    } else if (!isAuthenticated) {
      // Not authenticated, don't show loading/error - just reset
      setLoading(false);
      setClientInfo(null);
      setError(null);
      hasLoadedRef.current = false;
    }
  }, [isAuthenticated, authLoading]);

  const loadClientInfo = async (retries = 3, delay = 1000) => {
    // Only show loading spinner if we don't have cached data
    const hasCachedData = !!clientInfo;
    if (!hasCachedData) {
      setLoading(true);
    }

    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        setError(null);
        const response = await clientApi.getInfo();
        // Extract actual data from response wrapper { success: true, data: {...} }
        const actualData = response.data?.data || response.data;
        setClientInfo(actualData);
        setCachedClientInfo(actualData); // Cache for next visit
        setLoading(false);
        return; // Success, exit
      } catch (err) {
        if (attempt === retries) {
          // Only show error if we don't have cached data
          if (!hasCachedData) {
            setError('Failed to connect to server');
          }
          setLoading(false);
        } else {
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
  };

  // Update client info locally (for immediate UI updates)
  const updateClientInfo = (updates) => {
    setClientInfo(prev => prev ? { ...prev, ...updates } : updates);
  };

  const value = {
    clientInfo,
    loading,
    error,
    sidebarOpen,
    setSidebarOpen,
    sidebarPinned,
    toggleSidebarPinned,
    sidebarHovered,
    setSidebarHovered,
    sidebarExpanded,
    refreshClientInfo: loadClientInfo,
    updateClientInfo,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}

export default AppContext;
