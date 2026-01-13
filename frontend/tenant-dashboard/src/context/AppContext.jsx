import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { clientApi } from '../services/api';
import { useAuth } from './AuthContext';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [clientInfo, setClientInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const hasLoadedRef = useRef(false);

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
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        setLoading(true);
        setError(null);
        const response = await clientApi.getInfo();
        // Extract actual data from response wrapper { success: true, data: {...} }
        const actualData = response.data?.data || response.data;
        setClientInfo(actualData);
        setLoading(false);
        return; // Success, exit
      } catch (err) {
        if (attempt === retries) {
          setError('Failed to connect to server');
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
