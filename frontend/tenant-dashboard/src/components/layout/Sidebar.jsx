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
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';

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
          {!collapsed && (
            <>
              <span className="font-medium flex-1 text-left">{item.name}</span>
              <ChevronDownIcon
                className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              />
            </>
          )}
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
          {!collapsed && <span className="font-medium">{item.name}</span>}
        </NavLink>
      )}

      {hasChildren && !collapsed && isExpanded && (
        <div className="ml-8 mt-1 space-y-1">
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
  const { clientInfo, sidebarOpen, setSidebarOpen } = useApp();
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

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-sidebar border-r border-theme transition-all duration-300 z-40 ${
        sidebarOpen ? 'w-64' : 'w-16'
      }`}
    >
      {/* Logo / Company Name */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-theme">
        {sidebarOpen && (
          <div className="flex items-center gap-2">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt={clientInfo?.client_name || 'Logo'}
                className="h-8 w-auto object-contain max-w-[120px]"
              />
            ) : (
              <div className="w-8 h-8 bg-theme-primary rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">
                  {clientInfo?.client_name?.charAt(0) || 'T'}
                </span>
              </div>
            )}
            {!logoUrl && (
              <span className="font-semibold text-sidebar truncate">
                {clientInfo?.client_name || 'Travel Platform'}
              </span>
            )}
          </div>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-1.5 rounded-lg hover:bg-sidebar-hover text-sidebar-muted"
        >
          {sidebarOpen ? (
            <ChevronLeftIcon className="w-5 h-5" />
          ) : (
            <ChevronRightIcon className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-3 space-y-1 overflow-y-auto h-[calc(100vh-4rem)]">
        {navigation.map((item) => (
          <NavItem
            key={item.name}
            item={item}
            collapsed={!sidebarOpen}
            isExpanded={expandedItems[item.name]}
            onToggle={toggleExpanded}
          />
        ))}
      </nav>
    </aside>
  );
}
