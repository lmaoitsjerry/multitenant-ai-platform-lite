import { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { notificationsApi } from '../../services/api';
import {
  MagnifyingGlassIcon,
  BellIcon,
  EnvelopeIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  ShieldCheckIcon,
  UserPlusIcon,
  CurrencyDollarIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

const pageTitles = {
  '/': 'Dashboard',
  '/quotes': 'Quotes',
  '/quotes/new': 'Generate Quote',
  '/crm/pipeline': 'Pipeline',
  '/crm/clients': 'Clients',
  '/invoices': 'Invoices',
  '/pricing/rates': 'Pricing Rates',
  '/pricing/hotels': 'Hotels',
  '/knowledge': 'Knowledge Base',
  '/knowledge/documents': 'Knowledge Base',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
};

// Map notification types to icons
const notificationIcons = {
  quote_request: DocumentTextIcon,
  email_received: EnvelopeIcon,
  invoice_paid: CurrencyDollarIcon,
  invoice_overdue: ExclamationCircleIcon,
  booking_confirmed: CheckCircleIcon,
  client_added: UserPlusIcon,
  team_invite: UserPlusIcon,
  system: BellIcon,
  mention: BellIcon,
};

function UserDropdown({ isOpen, onClose, user, isAdmin, isConsultant, logout, clientInfo }) {
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const userName = user?.name || 'User';
  const userEmail = user?.email || 'user@example.com';
  const userRole = user?.role || 'user';

  return (
    <div
      ref={dropdownRef}
      className="absolute right-0 top-full mt-2 w-64 bg-theme-surface rounded-xl shadow-lg border-theme overflow-hidden z-50 animate-dropdown"
    >
      {/* User Info Header */}
      <div className="px-4 py-3 border-b border-theme bg-theme-surface-elevated">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold bg-theme-primary"
          >
            {userName.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-medium text-theme truncate">{userName}</p>
              {isAdmin && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                  <ShieldCheckIcon className="w-3 h-3" />
                  Admin
                </span>
              )}
              {isConsultant && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                  Consultant
                </span>
              )}
            </div>
            <p className="text-sm text-theme-muted truncate">{userEmail}</p>
          </div>
        </div>
      </div>

      {/* Menu Items */}
      <div className="py-1">
        <Link
          to="/settings"
          onClick={onClose}
          className="flex items-center gap-3 px-4 py-2.5 text-sm text-theme-secondary hover:bg-theme-border-light"
        >
          <Cog6ToothIcon className="w-5 h-5 text-theme-muted" />
          Settings
        </Link>
        <button
          onClick={() => {
            logout();
            onClose();
          }}
          className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-theme-secondary hover:bg-theme-border-light"
        >
          <ArrowRightOnRectangleIcon className="w-5 h-5 text-theme-muted" />
          Sign Out
        </button>
      </div>

      {/* Footer with tenant info */}
      <div className="px-4 py-2 border-t border-theme bg-theme-surface-elevated">
        <p className="text-xs text-theme-muted">
          {clientInfo?.timezone || 'UTC'} · {clientInfo?.currency || 'USD'}
        </p>
      </div>
    </div>
  );
}

function NotificationsDropdown({ isOpen, onClose, notifications, onMarkAllRead, onNotificationClick, loading }) {
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleNotificationClick = (notification) => {
    onNotificationClick(notification);

    // Navigate to related entity if available
    if (notification.entity_type && notification.entity_id) {
      const routes = {
        quote: `/quotes/${notification.entity_id}`,
        invoice: `/invoices/${notification.entity_id}`,
        client: `/crm/clients/${notification.entity_id}`,
      };
      const route = routes[notification.entity_type];
      if (route) {
        navigate(route);
        onClose();
      }
    }
  };

  return (
    <div
      ref={dropdownRef}
      className="absolute right-0 top-full mt-2 w-80 bg-theme-surface rounded-xl shadow-lg border-theme overflow-hidden z-50 animate-dropdown custom-scrollbar"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-theme bg-theme-surface-elevated">
        <h3 className="font-semibold text-theme">Notifications</h3>
        {unreadCount > 0 && (
          <button
            onClick={onMarkAllRead}
            className="text-sm text-theme-primary hover:text-theme-primary-light"
          >
            Mark all read
          </button>
        )}
      </div>

      {/* Notifications List */}
      <div className="max-h-80 overflow-y-auto">
        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-theme-primary mx-auto mb-2"></div>
            <p className="text-sm text-theme-muted">Loading...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-8">
            <BellIcon className="w-8 h-8 text-theme-muted mx-auto mb-2" />
            <p className="text-sm text-theme-muted">No notifications</p>
          </div>
        ) : (
          notifications.map((notification) => {
            const IconComponent = notificationIcons[notification.type] || BellIcon;
            return (
              <div
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                className={`flex gap-3 p-4 list-item-interactive cursor-pointer border-b border-theme-light ${
                  !notification.read ? 'bg-primary-50/50' : ''
                }`}
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                  !notification.read ? 'bg-primary-100' : 'bg-theme-surface-elevated'
                }`}>
                  <IconComponent className={`w-5 h-5 ${
                    !notification.read ? 'text-theme-primary' : 'text-theme-muted'
                  }`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${!notification.read ? 'font-semibold text-theme' : 'text-theme-secondary'}`}>
                    {notification.title}
                  </p>
                  <p className="text-sm text-theme-muted truncate">{notification.message}</p>
                  <p className="text-xs text-theme-muted mt-1">{notification.time_ago || notification.time}</p>
                </div>
                {!notification.read && (
                  <div className="w-2 h-2 bg-theme-primary rounded-full flex-shrink-0 mt-2"></div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-theme bg-theme-surface-elevated">
        <Link
          to="/settings?tab=notifications"
          onClick={onClose}
          className="text-sm text-theme-primary hover:text-theme-primary-light w-full text-center block"
        >
          Notification settings
        </Link>
      </div>
    </div>
  );
}

export default function Header() {
  const location = useLocation();
  const { clientInfo } = useApp();
  const { user, isAdmin, isConsultant, logout } = useAuth();
  const { branding, darkMode } = useTheme();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Get the appropriate logo based on dark mode
  // Priority: branding logo (uploaded) > clientInfo logo (config file)
  const logoUrl = darkMode
    ? (branding?.logos?.dark || branding?.logos?.primary || clientInfo?.logo_url)
    : (branding?.logos?.primary || clientInfo?.logo_url);

  // Fetch notifications when dropdown opens
  const fetchNotifications = useCallback(async () => {
    setNotificationsLoading(true);
    try {
      const response = await notificationsApi.list({ limit: 10 });
      if (response.data?.success) {
        setNotifications(response.data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setNotificationsLoading(false);
    }
  }, []);

  // Fetch unread count on mount and periodically
  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await notificationsApi.getUnreadCount();
      if (response.data?.success) {
        setUnreadCount(response.data.unread_count || 0);
      }
    } catch (error) {
      // Silently fail for unread count
    }
  }, []);

  // Initial fetch and polling
  useEffect(() => {
    fetchUnreadCount();

    // Poll for new notifications every 30 seconds
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // Fetch notifications when dropdown opens
  useEffect(() => {
    if (showNotifications) {
      fetchNotifications();
    }
  }, [showNotifications, fetchNotifications]);

  const getPageTitle = () => {
    const path = location.pathname;
    if (pageTitles[path]) return pageTitles[path];
    if (path.startsWith('/quotes/')) return 'Quote Details';
    if (path.startsWith('/crm/clients/')) return 'Client Details';
    return 'Dashboard';
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all read:', error);
    }
  };

  const handleNotificationClick = async (notification) => {
    if (!notification.read) {
      try {
        await notificationsApi.markRead(notification.id);
        setNotifications(prev =>
          prev.map(n => n.id === notification.id ? { ...n, read: true } : n)
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      } catch (error) {
        console.error('Failed to mark notification read:', error);
      }
    }
  };

  return (
    <header className="h-16 bg-theme-surface border-b border-theme flex items-center justify-between px-6">
      {/* Left Side - Tenant Branding & Page Title */}
      <div className="flex items-center gap-4">
        {/* Tenant Logo & Name */}
        <Link to="/" className="flex items-center gap-3 pr-4 border-r border-theme">
          {logoUrl ? (
            <img
              src={logoUrl}
              alt={clientInfo?.client_name || 'Logo'}
              className="h-8 w-auto object-contain"
            />
          ) : (
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm bg-theme-primary">
              {clientInfo?.client_name?.charAt(0)?.toUpperCase() || 'T'}
            </div>
          )}
          <span className="font-semibold text-theme-primary hidden sm:block">
            {clientInfo?.client_name || 'Dashboard'}
          </span>
        </Link>

        {/* Page Title */}
        <h1 className="text-lg font-medium text-theme-secondary">{getPageTitle()}</h1>
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative hidden md:block">
          <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-theme-muted" />
          <input
            type="text"
            placeholder="Search..."
            className="pl-10 pr-4 py-2 bg-theme-surface-elevated rounded-lg text-sm text-theme focus:outline-none focus:ring-2 focus:ring-primary-500 w-64"
          />
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => {
              setShowNotifications(!showNotifications);
              setShowUserMenu(false);
            }}
            className="relative p-2 text-theme-muted hover:text-theme-secondary hover:bg-theme-border-light rounded-lg"
          >
            <BellIcon className="w-6 h-6" />
            {unreadCount > 0 && (
              <span className="absolute top-0 right-0 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          <NotificationsDropdown
            isOpen={showNotifications}
            onClose={() => setShowNotifications(false)}
            notifications={notifications}
            onMarkAllRead={handleMarkAllRead}
            onNotificationClick={handleNotificationClick}
            loading={notificationsLoading}
          />
        </div>

        {/* User Menu */}
        <div className="relative">
          <button
            onClick={() => {
              setShowUserMenu(!showUserMenu);
              setShowNotifications(false);
            }}
            className="flex items-center gap-2 p-2 hover:bg-theme-border-light rounded-lg"
          >
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-white font-medium text-sm bg-theme-primary">
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <span className="text-sm font-medium text-theme-secondary hidden sm:block">
              {user?.name || 'User'}
            </span>
            {isAdmin && (
              <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                Admin
              </span>
            )}
            {isConsultant && (
              <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                Consultant
              </span>
            )}
            <ChevronDownIcon className="w-4 h-4 text-theme-muted hidden sm:block" />
          </button>

          <UserDropdown
            isOpen={showUserMenu}
            onClose={() => setShowUserMenu(false)}
            user={user}
            isAdmin={isAdmin}
            isConsultant={isConsultant}
            logout={logout}
            clientInfo={clientInfo}
          />
        </div>
      </div>
    </header>
  );
}
