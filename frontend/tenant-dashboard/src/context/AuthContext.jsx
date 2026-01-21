import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, dashboardApi, clientApi, setTenantId, clearTenantId } from '../services/api';

const AuthContext = createContext(null);

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize auth state from localStorage
  useEffect(() => {
    initializeAuth();
  }, []);

  // Listen for session expiration events from axios interceptor
  useEffect(() => {
    const handleSessionExpired = () => {
      console.log('[Auth] Session expired event received');
      clearAuth();
    };

    window.addEventListener('auth:session-expired', handleSessionExpired);
    return () => {
      window.removeEventListener('auth:session-expired', handleSessionExpired);
    };
  }, []);

  const initializeAuth = async () => {
    console.log('[Auth] Initializing auth...');
    try {
      const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
      const storedUser = localStorage.getItem(USER_KEY);

      if (accessToken && storedUser) {
        // Set user from cache immediately for faster UI
        setUser(JSON.parse(storedUser));
        console.log('[Auth] Found stored user, verifying token...');

        // Verify token is still valid by fetching current user
        try {
          const response = await authApi.me();
          if (response.data.success) {
            setUser(response.data.user);
            localStorage.setItem(USER_KEY, JSON.stringify(response.data.user));
            console.log('[Auth] Token verified successfully');
          }
        } catch (err) {
          console.warn('[Auth] Token verification failed, trying refresh:', err.message);
          // Token might be expired, try to refresh
          await tryRefreshToken();
        }
      } else {
        console.log('[Auth] No stored credentials found');
      }
    } catch (err) {
      console.error('[Auth] Initialization error:', err);
      clearAuth();
    } finally {
      console.log('[Auth] Initialization complete, setting loading=false');
      setLoading(false);
    }
  };

  const tryRefreshToken = async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      console.log('[Auth] No refresh token available');
      clearAuth();
      return false;
    }

    console.log('[Auth] Attempting token refresh...');
    try {
      const response = await authApi.refresh(refreshToken);
      if (response.data.success) {
        localStorage.setItem(ACCESS_TOKEN_KEY, response.data.access_token);
        localStorage.setItem(REFRESH_TOKEN_KEY, response.data.refresh_token);
        console.log('[Auth] Token refreshed successfully');

        // Re-fetch user info
        const userResponse = await authApi.me();
        if (userResponse.data.success) {
          setUser(userResponse.data.user);
          localStorage.setItem(USER_KEY, JSON.stringify(userResponse.data.user));
          console.log('[Auth] User info refreshed');
        }
        return true;
      }
    } catch (err) {
      console.error('[Auth] Token refresh failed:', err.message);
    }

    clearAuth();
    return false;
  };

  const login = async (email, password, tenantId = null) => {
    setError(null);
    console.log('[Auth] Attempting login for:', email);
    try {
      const response = await authApi.login(email, password, tenantId);
      console.log('[Auth] Login response:', { success: response.data.success, hasError: !!response.data.error });

      if (response.data.success) {
        const { access_token, refresh_token, user: userData } = response.data;

        // Store tokens and user
        localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
        localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
        localStorage.setItem(USER_KEY, JSON.stringify(userData));

        // CRITICAL: Store tenant_id from user object for subsequent API calls
        // This ensures all API requests use the correct tenant's X-Client-ID header
        if (userData?.tenant_id) {
          setTenantId(userData.tenant_id);
          console.log('[Auth] Stored tenant_id:', userData.tenant_id);
        }

        setUser(userData);

        // Prefetch dashboard data in background (non-blocking)
        // This triggers BigQuery cold start while user is navigating
        Promise.all([
          dashboardApi.getAll().catch(() => null),
          clientApi.getInfo().catch(() => null)
        ]).then(() => {
          console.log('[Auth] Dashboard data prefetched');
        });

        return { success: true };
      } else {
        const errorMsg = response.data.error || 'Login failed';
        console.log('[Auth] Login failed:', errorMsg);
        setError(errorMsg);
        return { success: false, error: errorMsg };
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || 'Login failed';
      console.log('[Auth] Login error:', errorMsg, err);
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      clearAuth();
    }
  }, []);

  const clearAuth = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    clearTenantId();  // Clear tenant_id so next login uses correct tenant
    setUser(null);
    setError(null);
  };

  const updateUser = (userData) => {
    setUser(userData);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
  };

  // Check if user is authenticated
  const isAuthenticated = !!user;

  // Check if user is admin
  const isAdmin = user?.role === 'admin';

  // Check if user is consultant
  const isConsultant = user?.role === 'consultant';

  // Get access token for API calls
  const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY);

  const value = {
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    isConsultant,
    login,
    logout,
    updateUser,
    getAccessToken,
    tryRefreshToken,
    clearError: () => setError(null),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

export default AuthContext;
