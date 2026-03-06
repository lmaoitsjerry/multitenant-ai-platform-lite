import { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';

// Shared hook for click-outside dropdown dismissal
function useClickOutside(isOpen, onClose) {
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  return ref;
}
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { notificationsApi, quotesApi, crmApi, invoicesApi, inboundApi } from '../../services/api';
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
  SunIcon,
  MoonIcon,
  UserIcon,
  MapPinIcon,
  QuestionMarkCircleIcon,
  InboxArrowDownIcon,
} from '@heroicons/react/24/outline';
import HelpDeskPanel from './HelpDeskPanel';

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

// Map notification types to icons and labels
const notificationTypeConfig = {
  quote_request: { icon: DocumentTextIcon, label: 'Quote', color: 'text-blue-500 bg-blue-500/10' },
  email_received: { icon: EnvelopeIcon, label: 'Enquiry', color: 'text-orange-500 bg-orange-500/10' },
  invoice_paid: { icon: CurrencyDollarIcon, label: 'Payment', color: 'text-green-500 bg-green-500/10' },
  invoice_overdue: { icon: ExclamationCircleIcon, label: 'Overdue', color: 'text-red-500 bg-red-500/10' },
  booking_confirmed: { icon: CheckCircleIcon, label: 'Booking', color: 'text-emerald-500 bg-emerald-500/10' },
  client_added: { icon: UserPlusIcon, label: 'Client', color: 'text-purple-500 bg-purple-500/10' },
  team_invite: { icon: UserPlusIcon, label: 'Team', color: 'text-indigo-500 bg-indigo-500/10' },
  system: { icon: BellIcon, label: 'System', color: 'text-gray-500 bg-gray-500/10' },
  mention: { icon: BellIcon, label: 'Mention', color: 'text-yellow-500 bg-yellow-500/10' },
};

// Kept for backwards compat
const notificationIcons = Object.fromEntries(
  Object.entries(notificationTypeConfig).map(([k, v]) => [k, v.icon])
);

function UserDropdown({ isOpen, onClose, user, isAdmin, isConsultant, logout, clientInfo }) {
  const dropdownRef = useClickOutside(isOpen, onClose);

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
  const dropdownRef = useClickOutside(isOpen, onClose);
  const navigate = useNavigate();

  if (!isOpen) return null;

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleNotificationClick = (notification) => {
    onNotificationClick(notification);

    // Navigate to related entity if available
    if (notification.entity_type) {
      const routes = {
        quote: `/quotes/${notification.entity_id}`,
        invoice: `/invoices/${notification.entity_id}`,
        client: `/crm/clients/${notification.entity_id}`,
        ticket: '/crm/triage',
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
      <div className="max-h-96 overflow-y-auto">
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
        ) : (() => {
          // Group by time: Today / Earlier
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const todayItems = notifications.filter(n => new Date(n.created_at) >= today);
          const earlierItems = notifications.filter(n => new Date(n.created_at) < today);

          const renderNotification = (notification) => {
            const typeConfig = notificationTypeConfig[notification.type] || notificationTypeConfig.system;
            const IconComponent = typeConfig.icon;
            const isClickable = notification.entity_type && (notification.entity_id || notification.entity_type === 'ticket');

            return (
              <div
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                className={`flex gap-3 p-3.5 cursor-pointer transition-colors border-b border-theme-light ${
                  !notification.read ? 'bg-[var(--color-primary)]/8 hover:bg-[var(--color-primary)]/12' : 'hover:bg-theme-border-light'
                }`}
              >
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${typeConfig.color}`}>
                  <IconComponent className="w-4.5 h-4.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className={`text-sm leading-snug ${!notification.read ? 'font-semibold text-theme' : 'text-theme-secondary'}`}>
                      {notification.title}
                    </p>
                    <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${typeConfig.color}`}>
                      {typeConfig.label}
                    </span>
                  </div>
                  <p className="text-xs text-theme-muted mt-0.5 line-clamp-2">{notification.message}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[11px] text-theme-muted">{notification.time_ago || notification.time}</span>
                    {isClickable && (
                      <span className="text-[11px] text-theme-primary">View &rarr;</span>
                    )}
                  </div>
                </div>
                {!notification.read && (
                  <div className="w-2 h-2 bg-theme-primary rounded-full flex-shrink-0 mt-2"></div>
                )}
              </div>
            );
          };

          return (
            <>
              {todayItems.length > 0 && (
                <>
                  <div className="px-4 py-1.5 bg-theme-surface-elevated text-[11px] font-semibold text-theme-muted uppercase tracking-wider">Today</div>
                  {todayItems.map(renderNotification)}
                </>
              )}
              {earlierItems.length > 0 && (
                <>
                  <div className="px-4 py-1.5 bg-theme-surface-elevated text-[11px] font-semibold text-theme-muted uppercase tracking-wider">Earlier</div>
                  {earlierItems.map(renderNotification)}
                </>
              )}
            </>
          );
        })()}
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

function SearchDropdown({ isOpen, onClose, searchQuery, results, loading }) {
  const dropdownRef = useClickOutside(isOpen, onClose);
  const navigate = useNavigate();

  if (!isOpen || !searchQuery) return null;

  const handleClick = (type, id) => {
    const routes = {
      quote: `/quotes/${id}`,
      client: `/crm/clients/${id}`,
      invoice: `/invoices/${id}`,
    };
    navigate(routes[type] || '/');
    onClose();
  };

  return (
    <div
      ref={dropdownRef}
      className="absolute left-0 top-full mt-2 w-80 bg-theme-surface rounded-xl shadow-lg border-theme overflow-hidden z-50 animate-dropdown"
    >
      {loading ? (
        <div className="text-center py-6">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-theme-primary mx-auto mb-2"></div>
          <p className="text-sm text-theme-muted">Searching...</p>
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-6">
          <MagnifyingGlassIcon className="w-8 h-8 text-theme-muted mx-auto mb-2" />
          <p className="text-sm text-theme-muted">No results for "{searchQuery}"</p>
        </div>
      ) : (
        <div className="max-h-80 overflow-y-auto">
          {[
            { type: 'client', label: 'Clients', icon: UserIcon, iconClass: 'bg-[var(--color-primary)]/10', textClass: 'text-theme-primary' },
            { type: 'quote', label: 'Quotes', icon: DocumentTextIcon, iconClass: 'bg-[var(--color-secondary)]/10', textClass: 'text-[var(--color-secondary)]' },
            { type: 'invoice', label: 'Invoices', icon: CurrencyDollarIcon, iconClass: 'bg-green-500/10', textClass: 'text-green-600' },
          ].map(({ type, label, icon: Icon, iconClass, textClass }) => {
            const items = results.filter(r => r.type === type);
            if (items.length === 0) return null;
            return (
              <div key={type}>
                <div className="px-4 py-2 bg-theme-surface-elevated text-xs font-semibold text-theme-muted uppercase">
                  {label}
                </div>
                {items.map((result) => (
                  <div
                    key={`${type}-${result.id}`}
                    onClick={() => handleClick(type, result.id)}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-theme-border-light cursor-pointer border-b border-theme-light"
                  >
                    <div className={`p-2 rounded-lg ${iconClass}`}>
                      <Icon className={`w-4 h-4 ${textClass}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-theme truncate">{result.name}</p>
                      <p className="text-xs text-theme-muted truncate">
                        {type === 'client' ? result.email :
                         type === 'invoice' ? (result.total ? `R ${Number(result.total).toLocaleString()}` : '') :
                         (result.destination && <span className="inline-flex items-center gap-1"><MapPinIcon className="w-3 h-3" />{result.destination}</span>)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { clientInfo } = useApp();
  const { user, isAdmin, isConsultant, logout } = useAuth();
  const { branding, darkMode, toggleDarkMode } = useTheme();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showHelpDesk, setShowHelpDesk] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [enquiryCount, setEnquiryCount] = useState(0);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const searchTimeoutRef = useRef(null);

  // Debounced search function
  const performSearch = useCallback(async (query) => {
    if (!query || query.length < 2) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    setSearchLoading(true);
    setShowSearchResults(true);

    try {
      const [clientsRes, quotesRes, invoicesRes] = await Promise.all([
        crmApi.listClients({ limit: 5, query }).catch(() => ({ data: { data: [] } })),
        quotesApi.list({ limit: 5, search: query }).catch(() => ({ data: { data: [] } })),
        invoicesApi.list({ limit: 5, search: query }).catch(() => ({ data: { data: [] } })),
      ]);

      const clients = (clientsRes.data?.data || [])
        .slice(0, 5)
        .map(c => ({ type: 'client', id: c.client_id || c.id, name: c.name, email: c.email }));

      const quotes = (quotesRes.data?.data || [])
        .slice(0, 5)
        .map(q => ({ type: 'quote', id: q.quote_id, name: q.customer_name, destination: q.destination }));

      const invoices = (invoicesRes.data?.data || [])
        .slice(0, 5)
        .map(inv => ({ type: 'invoice', id: inv.invoice_id, name: inv.customer_name, total: inv.total_amount }));

      setSearchResults([...clients, ...quotes, ...invoices]);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  // Handle search input change with debounce
  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      performSearch(query);
    }, 300);
  };

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

  // Fetch open enquiry count
  const fetchEnquiryCount = useCallback(async () => {
    try {
      const response = await inboundApi.listTickets({ status: 'open', limit: 1 });
      if (response.data?.success) {
        setEnquiryCount(response.data.stats?.open || 0);
      }
    } catch (error) {
      // Silently fail for enquiry count
    }
  }, []);

  // Initial fetch and polling
  useEffect(() => {
    fetchUnreadCount();
    fetchEnquiryCount();

    // Poll for new notifications every 15 seconds
    const interval = setInterval(() => {
      fetchUnreadCount();
      fetchEnquiryCount();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount, fetchEnquiryCount]);

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
    <>
    <header className="h-16 bg-theme-surface border-b border-theme flex items-center justify-between px-6">
      {/* Left Side - Theme Toggle & Page Title */}
      <div className="flex items-center gap-4">
        {/* Dark Mode Toggle */}
        <button
          onClick={toggleDarkMode}
          className={`p-2 rounded-lg transition-all duration-200 ${
            darkMode
              ? 'bg-amber-100 text-amber-600 hover:bg-amber-200'
              : 'bg-indigo-100 text-indigo-600 hover:bg-indigo-200'
          }`}
          aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {darkMode ? (
            <SunIcon className="w-5 h-5" />
          ) : (
            <MoonIcon className="w-5 h-5" />
          )}
        </button>

        {/* Page Title */}
        <h1 className="text-lg font-medium text-theme-secondary">{getPageTitle()}</h1>
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative hidden md:block">
          <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-theme-muted z-10" />
          <input
            type="text"
            placeholder="Search clients, quotes..."
            value={searchQuery}
            onChange={handleSearchChange}
            onFocus={() => searchQuery.length >= 2 && setShowSearchResults(true)}
            className="pl-10 pr-4 py-2 bg-theme-surface-elevated rounded-lg text-sm text-theme focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] w-72 border border-transparent focus:border-[var(--color-primary)]/30"
          />
          <SearchDropdown
            isOpen={showSearchResults}
            onClose={() => setShowSearchResults(false)}
            searchQuery={searchQuery}
            results={searchResults}
            loading={searchLoading}
          />
        </div>

        {/* Enquiry Triage */}
        <button
          onClick={() => navigate('/crm/triage')}
          className="relative p-2 text-theme-muted hover:text-theme-secondary hover:bg-theme-border-light rounded-lg"
          title="Enquiry Triage"
        >
          <InboxArrowDownIcon className="w-6 h-6" />
          {enquiryCount > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[20px] h-5 bg-orange-500 text-white text-xs font-bold rounded-full flex items-center justify-center px-1">
              {enquiryCount > 99 ? '99+' : enquiryCount}
            </span>
          )}
        </button>

        {/* Help Desk */}
        <button
          onClick={() => setShowHelpDesk(true)}
          className="p-2 text-theme-muted hover:text-theme-secondary hover:bg-theme-border-light rounded-lg"
          title="AI Help Desk"
        >
          <QuestionMarkCircleIcon className="w-6 h-6" />
        </button>

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

    {/* Help Desk Slide-in Panel */}
    <HelpDeskPanel
      isOpen={showHelpDesk}
      onClose={() => setShowHelpDesk(false)}
    />
    </>
  );
}
