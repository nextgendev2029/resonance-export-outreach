import React, { useState, useEffect } from 'react';
import { api } from './api';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardPage from './pages/DashboardPage';
import LeadsPage from './pages/LeadsPage';
import DiscoveryPage from './pages/DiscoveryPage';
import ClassificationPage from './pages/ClassificationPage';
import LeadIntelligencePage from './pages/LeadIntelligencePage';
import CampaignsPage from './pages/CampaignsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SendCampaignPage from './pages/SendCampaignPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';

function getTabFromPath() {
  const p = window.location.pathname.replace(/^\//, '').toLowerCase();
  if (['leads', 'upload'].includes(p)) return 'leads';
  if (['discovery', 'search'].includes(p)) return 'discovery';
  if (['intelligence', 'intel', 'enrichment'].includes(p)) return 'intelligence';
  if (['classify', 'classification'].includes(p)) return 'classify';
  if (['campaigns', 'campaign'].includes(p)) return 'campaigns';
  if (['analytics', 'telemetry', 'performance'].includes(p)) return 'analytics';
  if (['send'].includes(p)) return 'send';
  if (['report', 'reports', 'audit'].includes(p)) return 'report';
  if (['settings', 'config'].includes(p)) return 'settings';
  return 'dashboard';
}


export default function App() {
  const [currentTab, setCurrentTab] = useState(getTabFromPath);
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchGlobalData = async () => {
    try {
      const [statsData, reportsData] = await Promise.all([
        api.getStats(),
        api.getReports(),
      ]);
      setStats(statsData);
      setReports(reportsData);
    } catch (err) {
      console.error('Error fetching global telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGlobalData();
    const handlePopState = () => {
      setCurrentTab(getTabFromPath());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleTabChange = (tab) => {
    setCurrentTab(tab);
    const path = tab === 'dashboard' ? '/' : `/${tab}`;
    window.history.pushState(null, '', path);
  };

  const renderContent = () => {
    switch (currentTab) {
      case 'dashboard':
        return <DashboardPage stats={stats} reports={reports} setTab={handleTabChange} />;
      case 'leads':
        return <LeadsPage onRefreshStats={fetchGlobalData} />;
      case 'discovery':
        return <DiscoveryPage onRefreshStats={fetchGlobalData} />;
      case 'intelligence':
        return <LeadIntelligencePage onRefreshStats={fetchGlobalData} setTab={handleTabChange} />;
      case 'classify':
        return <ClassificationPage onRefreshStats={fetchGlobalData} stats={stats} />;
      case 'campaigns':
        return <CampaignsPage onRefreshStats={fetchGlobalData} stats={stats} />;
      case 'analytics':
        return <AnalyticsPage setTab={handleTabChange} stats={stats} />;
      case 'send':
        return <SendCampaignPage onRefreshStats={fetchGlobalData} stats={stats} />;

      case 'report':
        return <ReportsPage stats={stats} reports={reports} />;
      case 'settings':
        return <SettingsPage onRefreshStats={fetchGlobalData} />;
      default:
        return <DashboardPage stats={stats} reports={reports} setTab={handleTabChange} />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar currentTab={currentTab} setTab={handleTabChange} stats={stats} />
      <div className="main-wrapper">
        <Header
          currentTab={currentTab}
          onRefresh={fetchGlobalData}
          stats={stats}
          setTab={handleTabChange}
        />
        <main className="content-body">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
