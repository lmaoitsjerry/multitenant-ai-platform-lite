import { Routes, Route, NavLink } from 'react-router-dom';
import {
  HomeIcon,
  BuildingOffice2Icon,
  ChartBarIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline';
import Dashboard from './pages/Dashboard';
import TenantsList from './pages/TenantsList';
import TenantDetail from './pages/TenantDetail';
import UsageStats from './pages/UsageStats';
import KnowledgeManager from './pages/KnowledgeManager';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Tenants', href: '/tenants', icon: BuildingOffice2Icon },
  { name: 'Usage', href: '/usage', icon: ChartBarIcon },
  { name: 'Knowledge', href: '/knowledge', icon: BookOpenIcon },
];

function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900 text-white">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-zorah-500 rounded-lg flex items-center justify-center">
            <span className="font-bold text-sm">Z</span>
          </div>
          <div>
            <span className="font-semibold">Zorah Admin</span>
            <p className="text-xs text-gray-400">Internal Dashboard</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-1">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
                isActive
                  ? 'bg-zorah-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-800">
        <p className="text-xs text-gray-500 text-center">
          Zorah AI Platform v1.0
        </p>
      </div>
    </aside>
  );
}

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <main className="ml-64 p-8">
        {children}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tenants" element={<TenantsList />} />
        <Route path="/tenants/:tenantId" element={<TenantDetail />} />
        <Route path="/usage" element={<UsageStats />} />
        <Route path="/knowledge" element={<KnowledgeManager />} />
      </Routes>
    </Layout>
  );
}
