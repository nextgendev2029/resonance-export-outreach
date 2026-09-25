import React from 'react';
import { Download, RefreshCw, Send } from 'lucide-react';

const TAB_TITLES = {
  dashboard: 'Executive Operations Dashboard',
  leads: 'Buyer Leads Directory & Intelligence',
  discovery: 'Buyer Discovery',
  intelligence: 'Lead Intelligence & Enrichment',
  classify: 'AI Intent Classification',
  campaigns: 'Campaign Intelligence & Outreach Queue',
  analytics: 'Campaign Delivery & Operations Telemetry',
  send: 'Campaign Outreach Composer',
  report: 'Campaign Audit & Delivery Reports',
  settings: 'System Configuration & Credentials',
};


export default function Header({ currentTab, onRefresh, stats, setTab }) {
  return (
    <header className="top-header">
      <div className="header-left">
        <h1 className="page-title">{TAB_TITLES[currentTab] || 'Resonance Operations'}</h1>
        <span className="pipeline-badge">
          Target: <strong>Singing Bowls Export</strong>
        </span>
      </div>

      <div className="header-right">
        <button
          className="btn btn-sm"
          onClick={onRefresh}
          title="Refresh Data"
        >
          <RefreshCw size={13} />
          <span>Refresh</span>
        </button>

        <a
          href="/download-report"
          className="btn btn-sm"
          title="Download complete CSV report"
        >
          <Download size={13} />
          <span>Export CSV</span>
        </a>

        {currentTab !== 'campaigns' && (
          <button
            className="btn btn-sm btn-primary"
            onClick={() => setTab('campaigns')}
          >
            <span>Campaigns Queue</span>
          </button>
        )}
      </div>
    </header>
  );
}
