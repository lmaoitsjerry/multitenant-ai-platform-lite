import { NavLink, useLocation } from 'react-router-dom';
import { useState, useCallback } from 'react';
import { useApp } from '../../context/AppContext';
import { useTheme } from '../../context/ThemeContext';
import { quotesApi, invoicesApi, crmApi, pricingApi, dashboardApi, analyticsApi, brandingApi } from '../../services/api';
import {
  HomeIcon,
  DocumentTextIcon,
  UsersIcon,
  DocumentDuplicateIcon,
  CurrencyDollarIcon,
  QuestionMarkCircleIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { MapPinIcon } from '@heroicons/react/24/solid';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Quotes', href: '/quotes', icon: DocumentTextIcon },
  {
    name: 'CRM',
    href: '/crm',
    icon: UsersIcon,
    children: [
      { name: 'Pipeline', href: '/crm/pipeline' },
      { name: 'All Clients', href: '/crm/clients' },
    ]
  },
  { name: 'Invoices', href: '/invoices', icon: DocumentDuplicateIcon },
  {
    name: 'Pricing Guide',
    href: '/pricing',
    icon: CurrencyDollarIcon,
    children: [
      { name: 'Rates', href: '/pricing/rates' },
      { name: 'Hotels', href: '/pricing/hotels' },
    ]
  },
  { name: 'Helpdesk', href: '/helpdesk', icon: QuestionMarkCircleIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

// Prefetch mapping - which data to load when hovering over nav items
const prefetchHandlers = {
  '/': () => dashboardApi.getAll(),
  '/quotes': () => quotesApi.list({ limit: 10 }),
  '/invoices': () => invoicesApi.list({ limit: 10 }),
  '/crm/clients': () => crmApi.listClients({ limit: 20 }),
  '/crm/pipeline': () => crmApi.getPipeline(),
  '/pricing/rates': () => pricingApi.listRates(),
  '/pricing/hotels': () => pricingApi.listHotels(),
  '/analytics': () => analyticsApi.getQuoteAnalytics('30d'),
  '/settings': () => brandingApi.get(),
};

function NavItem({ item, collapsed, isExpanded, onToggle }) {
  const location = useLocation();
  const hasChildren = item.children && item.children.length > 0;

  // Check if any child route is active
  const isChildActive = hasChildren && item.children.some(child =>
    location.pathname === child.href || location.pathname.startsWith(child.href + '/')
  );

  // Check if this item or its children are active
  const isActive = location.pathname === item.href || isChildActive;

  // Prefetch data on hover
  const handleMouseEnter = useCallback(() => {
    if (hasChildren) {
      // Prefetch first child's data
      const handler = prefetchHandlers[item.children[0].href];
      if (handler) handler().catch(() => {});
    } else {
      const handler = prefetchHandlers[item.href];
      if (handler) handler().catch(() => {});
    }
  }, [item, hasChildren]);

  // Handle click for items with children
  const handleClick = (e) => {
    if (hasChildren && !collapsed) {
      e.preventDefault();
      onToggle(item.name);
    }
  };

  // Shared text transition styles
  const textStyle = {
    opacity: collapsed ? 0 : 1,
    transform: collapsed ? 'translateX(-10px)' : 'translateX(0)',
    transition: 'opacity 300ms ease, transform 300ms ease',
    transitionDelay: collapsed ? '0ms' : '100ms',
    whiteSpace: 'nowrap',
  };

  return (
    <div>
      {hasChildren ? (
        <button
          onClick={handleClick}
          onMouseEnter={handleMouseEnter}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
            isActive
              ? 'bg-sidebar-active text-sidebar-active'
              : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar'
          }`}
        >
          <item.icon className="w-5 h-5 flex-shrink-0" />
          <span className="font-medium flex-1 text-left overflow-hidden" style={textStyle}>
            {item.name}
          </span>
          <ChevronDownIcon
            className="w-4 h-4 flex-shrink-0"
            style={{
              ...textStyle,
              transform: collapsed ? 'translateX(-10px)' : (isExpanded ? 'rotate(180deg)' : 'rotate(0deg)'),
              transition: 'opacity 300ms ease, transform 300ms ease',
            }}
          />
        </button>
      ) : (
        <NavLink
          to={item.href}
          onMouseEnter={handleMouseEnter}
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              isActive
                ? 'bg-sidebar-active text-sidebar-active'
                : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar'
            }`
          }
        >
          <item.icon className="w-5 h-5 flex-shrink-0" />
          <span className="font-medium overflow-hidden" style={textStyle}>{item.name}</span>
        </NavLink>
      )}

      {hasChildren && (
        <div
          className="ml-8 mt-1 space-y-1 overflow-hidden"
          style={{
            maxHeight: (!collapsed && isExpanded) ? '200px' : '0px',
            opacity: (!collapsed && isExpanded) ? 1 : 0,
            transition: 'max-height 300ms ease, opacity 300ms ease',
          }}
        >
          {item.children.map((child) => {
            const childPrefetch = prefetchHandlers[child.href];
            return (
              <NavLink
                key={child.href}
                to={child.href}
                onMouseEnter={childPrefetch ? () => childPrefetch().catch(() => {}) : undefined}
                className={({ isActive }) =>
                  `block px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-sidebar-active text-sidebar-active'
                      : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar'
                  }`
                }
              >
                {child.name}
              </NavLink>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Sidebar() {
  const { clientInfo, sidebarPinned, toggleSidebarPinned, setSidebarHovered, sidebarExpanded } = useApp();
  const { branding, darkMode } = useTheme();
  const location = useLocation();

  // Get the appropriate logo based on dark mode
  // Priority: branding logo (uploaded) > clientInfo logo (config file)
  const logoUrl = darkMode
    ? (branding?.logos?.dark || branding?.logos?.primary || clientInfo?.logo_url)
    : (branding?.logos?.primary || clientInfo?.logo_url);

  // Track which dropdowns are expanded - auto-expand if child is active
  const [expandedItems, setExpandedItems] = useState(() => {
    const initial = {};
    navigation.forEach(item => {
      if (item.children) {
        const isChildActive = item.children.some(child =>
          location.pathname === child.href || location.pathname.startsWith(child.href + '/')
        );
        if (isChildActive) initial[item.name] = true;
      }
    });
    return initial;
  });

  const toggleExpanded = (itemName) => {
    setExpandedItems(prev => ({
      ...prev,
      [itemName]: !prev[itemName]
    }));
  };

  // Use sidebarExpanded from context (pinned OR hovered)
  const isExpanded = sidebarExpanded;

  return (
    <aside
      onMouseEnter={() => setSidebarHovered(true)}
      onMouseLeave={() => setSidebarHovered(false)}
      style={{
        width: isExpanded ? '16rem' : '4rem',
        transition: 'width 400ms cubic-bezier(0.4, 0, 0.2, 1)',
      }}
      className="fixed left-0 top-0 h-full bg-sidebar border-r border-theme z-40"
    >
      {/* Logo / Company Name */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-theme overflow-hidden">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {logoUrl ? (
            <img
              src={logoUrl}
              alt={clientInfo?.client_name || 'Logo'}
              className="h-8 w-8 object-contain flex-shrink-0"
              style={{
                maxWidth: isExpanded ? '120px' : '32px',
                width: isExpanded ? 'auto' : '32px',
                transition: 'all 400ms cubic-bezier(0.4, 0, 0.2, 1)',
              }}
            />
          ) : (
            <div className="w-8 h-8 bg-theme-primary rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-sm">
                {clientInfo?.client_name?.charAt(0) || 'T'}
              </span>
            </div>
          )}
          <span
            className="font-semibold text-sidebar truncate whitespace-nowrap"
            style={{
              opacity: isExpanded ? 1 : 0,
              transform: isExpanded ? 'translateX(0)' : 'translateX(-10px)',
              transition: 'opacity 300ms ease, transform 300ms ease',
              transitionDelay: isExpanded ? '100ms' : '0ms',
            }}
          >
            {clientInfo?.client_name || 'Travel Platform'}
          </span>
        </div>

        {/* Pin Button - only visible when expanded */}
        <button
          onClick={toggleSidebarPinned}
          className={`p-1.5 rounded-lg transition-all duration-300 flex-shrink-0 ${
            sidebarPinned
              ? 'bg-theme-primary text-white'
              : 'hover:bg-sidebar-hover text-sidebar-muted hover:text-sidebar'
          }`}
          style={{
            opacity: isExpanded ? 1 : 0,
            transform: isExpanded ? 'scale(1)' : 'scale(0.8)',
            transition: 'opacity 300ms ease, transform 300ms ease, background-color 200ms ease',
            transitionDelay: isExpanded ? '150ms' : '0ms',
            pointerEvents: isExpanded ? 'auto' : 'none',
          }}
          title={sidebarPinned ? 'Unpin sidebar' : 'Pin sidebar open'}
        >
          <MapPinIcon
            className="w-4 h-4"
            style={{
              transform: sidebarPinned ? 'rotate(0deg)' : 'rotate(45deg)',
              transition: 'transform 200ms ease',
            }}
          />
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-3 space-y-1 overflow-y-auto h-[calc(100vh-4rem)]">
        {navigation.map((item) => (
          <NavItem
            key={item.name}
            item={item}
            collapsed={!isExpanded}
            isExpanded={expandedItems[item.name]}
            onToggle={toggleExpanded}
          />
        ))}
      </nav>
    </aside>
  );
}
