import { NavLink, useLocation } from 'react-router-dom';
import { useState, useCallback } from 'react';
import { useApp } from '../../context/AppContext';
import { useTheme } from '../../context/ThemeContext';
import { quotesApi, invoicesApi, crmApi, dashboardApi, analyticsApi, brandingApi, hotelsApi, activitiesApi, flightsApi, transfersApi, inboundApi } from '../../services/api';
import {
  HomeIcon,
  DocumentTextIcon,
  UsersIcon,
  DocumentDuplicateIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ChevronDownIcon,
  GlobeAltIcon,
  BuildingOfficeIcon,
  SparklesIcon,
  PaperAirplaneIcon,
  TruckIcon,
  BookOpenIcon,
  InboxIcon,
  ComputerDesktopIcon,
  SwatchIcon,
  PhotoIcon,
  CubeIcon,
  ClipboardDocumentListIcon,
  EyeIcon,
  PresentationChartLineIcon,
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
      { name: 'Enquiry Triage', href: '/crm/triage', icon: InboxIcon },
      { name: 'Pipeline', href: '/crm/pipeline' },
      { name: 'All Clients', href: '/crm/clients' },
    ]
  },
  { name: 'Invoices', href: '/invoices', icon: DocumentDuplicateIcon },
  {
    name: 'Travel Services',
    href: '/travel',
    icon: GlobeAltIcon,
    children: [
      { name: 'Holiday Packages', href: '/travel/packages', icon: GlobeAltIcon },
      { name: 'Hotels', href: '/travel/hotels', icon: BuildingOfficeIcon },
      { name: 'Activities', href: '/travel/activities', icon: SparklesIcon },
      { name: 'Flights', href: '/travel/flights', icon: PaperAirplaneIcon },
      { name: 'Transfers', href: '/travel/transfers', icon: TruckIcon },
    ]
  },
  {
    name: 'Website',
    href: '/website',
    icon: ComputerDesktopIcon,
    children: [
      { name: 'Overview', href: '/website', icon: PresentationChartLineIcon },
      { name: 'Templates', href: '/website/templates', icon: SwatchIcon },
      { name: 'Branding', href: '/website/branding', icon: SwatchIcon },
      { name: 'Media Library', href: '/website/media', icon: PhotoIcon },
      { name: 'Products', href: '/website/products', icon: CubeIcon },
      { name: 'Bookings', href: '/website/bookings', icon: ClipboardDocumentListIcon },
      { name: 'Preview', href: '/website/preview', icon: EyeIcon },
    ]
  },
  { name: 'Knowledge Base', href: '/knowledge', icon: BookOpenIcon },
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
  '/crm/triage': () => inboundApi.listTickets({ status: 'open', limit: 20 }),
  '/travel/packages': () => hotelsApi.destinations(),
  '/travel/hotels': () => hotelsApi.destinations(),
  '/travel/activities': () => activitiesApi.list({ limit: 20 }),
  '/travel/flights': () => flightsApi.list({ limit: 20 }),
  '/travel/transfers': () => transfersApi.list({ limit: 20 }),
  '/knowledge': () => import('../../services/api').then(m => m.knowledgeApi.listDocuments()),
  '/analytics': () => analyticsApi.getQuoteAnalytics('30d'),
  '/settings': () => brandingApi.get(),
};

function NavItem({ item, collapsed, isExpanded, onToggle }) {
  const location = useLocation();
  const hasChildren = item.children && item.children.length > 0;

  // Check if any child route is active
  // Special case: when child.href === item.href (e.g., Overview at /website),
  // use exact matching only to prevent it from matching all sub-routes
  const isChildActive = hasChildren && item.children.some(child => {
    const isOverviewItem = child.href === item.href;
    if (isOverviewItem) {
      // Exact match only for "Overview" type items
      return location.pathname === child.href;
    }
    // For other items, allow sub-route matching
    return location.pathname === child.href || location.pathname.startsWith(child.href + '/');
  });

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
            maxHeight: (!collapsed && isExpanded) ? '400px' : '0px',
            opacity: (!collapsed && isExpanded) ? 1 : 0,
            transition: 'max-height 300ms ease, opacity 300ms ease',
          }}
        >
          {item.children.map((child) => {
            const childPrefetch = prefetchHandlers[child.href];
            // Use exact matching (end) when child href equals parent href
            // This prevents Overview from staying active when on sub-pages
            const useExactMatch = child.href === item.href;
            return (
              <NavLink
                key={child.href}
                to={child.href}
                end={useExactMatch}
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
      className="fixed left-0 top-0 h-full bg-sidebar border-r border-theme z-40 flex flex-col"
    >
      {/* Logo / Company Name - Fixed header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-theme overflow-hidden flex-shrink-0">
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
            {clientInfo?.client_name || 'HT-ITC-Lite'}
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

      {/* Navigation - Scrollable section */}
      <nav className="p-3 space-y-1 overflow-y-auto flex-1 min-h-0 custom-scrollbar">
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
