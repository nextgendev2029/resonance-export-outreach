import React from 'react';
import {
  LayoutDashboard,
  Users,
  Search,
  Compass,
  Tags,
  Layers,
  FileBarChart,
  Settings,
  ShieldCheck
} from 'lucide-react';

export default function Sidebar({ currentTab, setTab, stats }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'leads', label: 'Leads & Data', icon: Users, count: stats?.total_leads || 0 },
    { id: 'discovery', label: 'Buyer Discovery', icon: Search },
    { id: 'intelligence', label: 'Lead Intelligence', icon: Compass },
    { id: 'classify', label: 'Classification', icon: Tags },
    { id: 'campaigns', label: 'Campaigns', icon: Layers },
    { id: 'analytics', label: 'Analytics', icon: FileBarChart },
    { id: 'report', label: 'Reports & Audit', icon: ShieldCheck },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];


  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="brand-badge">RS</span>
        <div className="brand-info">
          <span className="brand-title">Resonance</span>
          <span className="brand-subtitle">Export Outreach & Operations</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <span className="nav-label">Operations</span>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setTab(item.id)}
            >
              <Icon size={16} />
              <span className="nav-text">{item.label}</span>
              {typeof item.count === 'number' && item.count > 0 && (
                <span className="nav-count">{item.count}</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="system-status-indicator">
          <span className="status-dot"></span>
          <span>Singing Bowls • B2B Pipeline</span>
        </div>
      </div>
    </aside>
  );
}
