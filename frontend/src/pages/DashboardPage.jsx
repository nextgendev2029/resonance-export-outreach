import React from 'react';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import {
  Users,
  CheckCircle2,
  Building2,
  Send,
  AlertTriangle,
  RotateCcw,
  Percent,
  Search,
  ArrowRight,
  ShieldCheck,
  FileSearch
} from 'lucide-react';

export default function DashboardPage({ stats, reports, setTab }) {
  const recentActivity = reports?.recent_activity || [];
  const sources = stats?.source_distribution || {};
  const countries = stats?.country_distribution || {};

  const realCount = stats?.real_leads_count || 0;
  const demoCount = stats?.demo_leads_count || 0;

  return (
    <div>
      {/* Notice Banner */}
      <div className="notice-box">
        <div>
          <strong>Resonance Export Intelligence Active.</strong> Multi-source prospecting pipeline configured for <strong>Singing Bowls</strong> export operations. Discovered buyer contacts are syntactically validated and segmented before campaign staging.
        </div>
      </div>

      {/* Metrics Row 1 */}
      <div className="metrics-grid">
        <MetricCard
          label="Real Discovered Leads"
          value={realCount}
          subtext={`${demoCount} demo sample leads isolated`}
          icon={Users}
        />
        <MetricCard
          label="Valid Email Addresses"
          value={stats?.valid_emails || 0}
          subtext={`${stats?.missing_emails || 0} missing • ${stats?.invalid_emails || 0} invalid`}
          icon={CheckCircle2}
        />
        <MetricCard
          label="B2B Wholesale Contacts"
          value={stats?.business_contacts || 0}
          subtext="Target export buyers"
          icon={Building2}
        />
        <MetricCard
          label="Individual / Retail"
          value={stats?.individual_contacts || 0}
          subtext="Practitioners & solo buyers"
        />
        <MetricCard
          label="Outreach Deliveries"
          value={stats?.successful_deliveries || 0}
          subtext={`Global log: ${stats?.failed_sends || 0} failed attempts`}
          icon={Send}
        />
        <MetricCard
          label="Duplicates Suppressed"
          value={stats?.duplicates_skipped || 0}
          subtext="De-duplication safety"
          icon={RotateCcw}
        />
        <MetricCard
          label="Outreach Success Rate"
          value={`${stats?.success_rate || 0}%`}
          subtext="Confirmed delivery ratio"
          icon={Percent}
        />
      </div>

      {/* 2-Column Split: Recent Outreach Activity & Source Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px' }}>
        {/* Recent Send / Audit Log Panel */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Recent Outreach & Delivery Log</h2>
              <p className="panel-description">Global SMTP dispatch attempts recorded in sent_log.csv (includes tests & campaign runs)</p>
            </div>
            <button className="btn btn-sm" onClick={() => setTab('report')}>
              View All Logs <ArrowRight size={12} />
            </button>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            {recentActivity.length === 0 ? (
              <div className="empty-state-box" style={{ padding: '30px' }}>
                <div className="empty-state-title">No Outreach History Yet</div>
                <div className="empty-state-desc">
                  Compose and dispatch an outreach campaign targeting verified B2B buyers from the Campaigns view.
                </div>
                <button className="btn btn-sm btn-primary" onClick={() => setTab('campaigns')}>
                  <Send size={12} /> Go to Campaigns
                </button>
              </div>
            ) : (
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Recipient</th>
                    <th>Status</th>
                    <th>Subject</th>
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.slice(0, 7).map((log, idx) => (
                    <tr key={idx}>
                      <td className="mono-cell" style={{ color: '#64748B', whiteSpace: 'nowrap' }}>
                        {log.timestamp ? log.timestamp.split('T')[0] : '-'}
                      </td>
                      <td className="mono-cell" style={{ fontWeight: 500 }}>
                        {log.email}
                      </td>
                      <td>
                        <StatusBadge type="outreach" value={log.status} />
                      </td>
                      <td style={{ color: '#475569', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.campaign_subject || 'Standard Wholesale Intro'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Source Channels & Quick Operations Panel */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Channels & Pipeline Operations</h2>
              <p className="panel-description">Lead distribution by source platform and quick discovery actions</p>
            </div>
            <button className="btn btn-sm btn-primary" onClick={() => setTab('discovery')}>
              <Search size={12} /> Run Discovery
            </button>
          </div>
          <div className="panel-body">
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#475569', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.3px' }}>
                PROSPECTING CHANNELS
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
                {Object.entries(sources).length > 0 ? (
                  Object.entries(sources).map(([src, count]) => (
                    <div key={src} style={{ padding: '8px 10px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px' }}>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>{src}</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A' }}>{count}</div>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#94A3B8', fontSize: '12px' }}>No channel data yet.</div>
                )}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#475569', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.3px' }}>
                TOP BUYER MARKETS
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {Object.entries(countries).length > 0 ? (
                  Object.entries(countries).map(([country, count]) => (
                    <span key={country} className="badge badge-ind" style={{ padding: '4px 8px' }}>
                      {country}: <strong>{count}</strong>
                    </span>
                  ))
                ) : (
                  <span style={{ color: '#94A3B8', fontSize: '12px' }}>No geographic data yet.</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
