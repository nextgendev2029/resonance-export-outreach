import React, { useState, useEffect } from 'react';
import { api } from '../api';
import {
  BarChart3,
  RefreshCw,
  Layers,
  CheckCircle2,
  Clock,
  Send,
  AlertTriangle,
  ShieldBan,
  Download,
  Search,
  ExternalLink,
  Info
} from 'lucide-react';

export default function AnalyticsPage({ setTab }) {
  const [overview, setOverview] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activityFilter, setActivityFilter] = useState('');
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [campaignDetail, setCampaignDetail] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [overviewData, campaignsData, activityData] = await Promise.all([
        api.getAnalyticsOverview(),
        api.getAnalyticsCampaigns(),
        api.getAnalyticsRecentActivity(50)
      ]);
      setOverview(overviewData);
      setCampaigns(campaignsData);
      setActivity(activityData);
    } catch (err) {
      console.error('Error fetching analytics telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectCampaign = async (cid) => {
    if (selectedCampaign === cid) {
      setSelectedCampaign(null);
      setCampaignDetail(null);
      return;
    }
    setSelectedCampaign(cid);
    try {
      const detail = await api.getAnalyticsCampaignDetail(cid);
      setCampaignDetail(detail);
    } catch (err) {
      console.error('Error fetching campaign detail:', err);
    }
  };

  const filteredActivity = activity.filter((item) => {
    if (!activityFilter) return true;
    const q = activityFilter.toLowerCase();
    return (
      (item.recipient_email && item.recipient_email.toLowerCase().includes(q)) ||
      (item.campaign_name && item.campaign_name.toLowerCase().includes(q)) ||
      (item.event && item.event.toLowerCase().includes(q)) ||
      (item.status && item.status.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    if (s === 'completed') return <span className="status-badge valid">Completed</span>;
    if (s === 'completed with errors') return <span className="status-badge risky">Completed With Errors</span>;
    if (s === 'sending') return <span className="status-badge neutral" style={{ background: '#E0F2FE', color: '#0369A1' }}>Sending</span>;
    if (s === 'queued') return <span className="status-badge neutral" style={{ background: '#FEF3C7', color: '#B45309' }}>Queued</span>;
    if (s === 'paused') return <span className="status-badge neutral" style={{ background: '#F1F5F9', color: '#475569' }}>Paused</span>;
    if (s === 'cancelled') return <span className="status-badge invalid">Cancelled</span>;
    if (s === 'approved') return <span className="status-badge valid">Approved</span>;
    return <span className="status-badge neutral">{status || 'Draft'}</span>;
  };

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="section-header" style={{ marginBottom: 20 }}>
        <div>
          <h2 className="section-title">Campaign Delivery & Operations Telemetry</h2>
          <p className="section-desc">
            Audited SMTP submission counts, queue progression, and contact suppression metrics.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <a href="/download-dispatch-log" className="btn btn-sm" title="Export Dispatch Queue Log CSV">
            <Download size={13} />
            <span>Export Dispatch Log</span>
          </a>
          <button className="btn btn-sm" onClick={fetchAnalytics} disabled={loading}>
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Telemetry Scope & Integrity Notice */}
      <div className="info-banner" style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', gap: 12, background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px 16px', borderRadius: 6, fontSize: 13, color: '#334155' }}>
        <Info size={18} style={{ flexShrink: 0, color: '#0F766E', marginTop: 2 }} />
        <div>
          <div style={{ fontWeight: 600, color: '#0F172A', marginBottom: 2 }}>
            Telemetry Scope & Factual Standard
          </div>
          <div>
            Metrics reflect verified system dispatch queue events (<code style={{ fontSize: 11, background: '#E2E8F0', padding: '1px 4px', borderRadius: 3 }}>dispatch_queue.json</code>) and historical SMTP submission records (<code style={{ fontSize: 11, background: '#E2E8F0', padding: '1px 4px', borderRadius: 3 }}>sent_log.csv</code>).
            {overview && overview.campaigns_count === 0 && (
              <span style={{ display: 'block', marginTop: 4, color: '#0F766E', fontWeight: 500 }}>
                Scope Notice: 0 structured campaigns are currently active in the Campaigns workspace. Historical delivery totals represent global system runs and test dispatches. Campaign-specific attribution activates upon campaign dispatch.
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#F0FDFA', color: '#0F766E' }}>
            <Layers size={18} />
          </div>
          <div className="stat-label">Active Campaigns</div>
          <div className="stat-value">{overview ? overview.campaigns_count : '-'}</div>
          <div className="stat-sub">{overview ? `${overview.drafts_count} total drafts generated` : 'Loading...'}</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ECFDF5', color: '#059669' }}>
            <CheckCircle2 size={18} />
          </div>
          <div className="stat-label">Approved Campaign Drafts</div>
          <div className="stat-value">{overview ? overview.approved_count : '-'}</div>
          <div className="stat-sub">Operator confirmed in workspace</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#FEF3C7', color: '#D97706' }}>
            <Clock size={18} />
          </div>
          <div className="stat-label">Dispatch Queue Active</div>
          <div className="stat-value">{overview ? overview.queued_count + overview.sending_count : '-'}</div>
          <div className="stat-sub">
            {overview ? `${overview.sending_count} currently sending` : '-'}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#F0FDF4', color: '#16A34A' }}>
            <Send size={18} />
          </div>
          <div className="stat-label">Accepted by SMTP (Global)</div>
          <div className="stat-value">{overview ? overview.sent_count : '-'}</div>
          <div className="stat-sub">Confirmed Gmail submissions</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#FEF2F2', color: '#DC2626' }}>
            <AlertTriangle size={18} />
          </div>
          <div className="stat-label">Failed Submissions (Global)</div>
          <div className="stat-value">{overview ? overview.failed_count : '-'}</div>
          <div className="stat-sub">Retry exhausted or permanent errors</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#F8FAFC', color: '#475569' }}>
            <ShieldBan size={18} />
          </div>
          <div className="stat-label">Suppressed Contacts</div>
          <div className="stat-value">{overview ? overview.suppressed_count : '-'}</div>
          <div className="stat-sub">Active suppression list entries</div>
        </div>
      </div>

      {/* Untracked Metrics Disclosure Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
        <div style={{ padding: '10px 14px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}>
          <span style={{ color: '#64748B' }}>Open Tracking: </span>
          <strong style={{ color: '#475569' }}>Not available</strong>
        </div>
        <div style={{ padding: '10px 14px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}>
          <span style={{ color: '#64748B' }}>Reply Tracking: </span>
          <strong style={{ color: '#475569' }}>Not available</strong>
        </div>
        <div style={{ padding: '10px 14px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}>
          <span style={{ color: '#64748B' }}>Conversion Tracking: </span>
          <strong style={{ color: '#475569' }}>Not available</strong>
        </div>
      </div>

      {/* Campaign Performance Table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="card-title">Campaign Operational Breakdown</h3>
            <p className="card-subtitle">Real-time status, audience scale, and dispatch fulfillment.</p>
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Campaign</th>
                <th>Audience</th>
                <th>Approved</th>
                <th>Queued</th>
                <th>Sent</th>
                <th>Failed</th>
                <th>Suppressed</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '36px 16px', color: '#64748B' }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#0F172A', marginBottom: 4 }}>
                      No Active Campaigns Created Yet
                    </div>
                    <div style={{ fontSize: 12, color: '#64748B', maxWidth: 480, margin: '0 auto 12px' }}>
                      Dispatch metrics above reflect global system queue events. Once you create and launch a campaign, individual campaign breakdown will appear here.
                    </div>
                    {setTab && (
                      <button className="btn btn-sm btn-primary" onClick={() => setTab('campaigns')}>
                        Go to Campaigns Workspace
                      </button>
                    )}
                  </td>
                </tr>
              ) : (
                campaigns.map((c) => (
                  <tr
                    key={c.campaign_id}
                    onClick={() => handleSelectCampaign(c.campaign_id)}
                    style={{
                      cursor: 'pointer',
                      background: selectedCampaign === c.campaign_id ? '#F0FDFA' : 'inherit'
                    }}
                  >
                    <td>
                      <div style={{ fontWeight: 600, color: '#0F172A' }}>{c.name}</div>
                      <div style={{ fontSize: 11, color: '#64748B', fontFamily: 'monospace' }}>
                        {c.campaign_id}
                      </div>
                    </td>
                    <td>{c.audience_count}</td>
                    <td>{c.approved_count}</td>
                    <td>{c.queued_count}</td>
                    <td>
                      <span style={{ fontWeight: 600, color: c.sent_count > 0 ? '#0F766E' : 'inherit' }}>
                        {c.sent_count}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: c.failed_count > 0 ? '#DC2626' : 'inherit' }}>
                        {c.failed_count}
                      </span>
                    </td>
                    <td>{c.suppressed_count}</td>
                    <td>{getStatusBadge(c.status)}</td>
                    <td style={{ fontSize: 12, color: '#64748B' }}>
                      {c.updated_at ? new Date(c.updated_at).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Campaign Detailed Metrics Drawer / Card */}
      {selectedCampaign && campaignDetail && (
        <div className="card" style={{ marginBottom: 24, border: '1px solid #0F766E' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 className="card-title">Campaign Detail: {campaignDetail.name}</h3>
              <p className="card-subtitle">Detailed draft and dispatch queue breakdown.</p>
            </div>
            <button className="btn btn-sm" onClick={() => setSelectedCampaign(null)}>
              Close
            </button>
          </div>
          <div style={{ padding: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
              <div style={{ background: '#F8FAFC', padding: 12, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: '#64748B' }}>Draft Status Breakdown</div>
                <div style={{ marginTop: 6, fontSize: 13 }}>
                  <div>Approved: <strong>{campaignDetail.drafts?.breakdown?.Approved || 0}</strong></div>
                  <div>Needs Review: <strong>{campaignDetail.drafts?.breakdown?.['Needs Review'] || 0}</strong></div>
                  <div>Draft: <strong>{campaignDetail.drafts?.breakdown?.Draft || 0}</strong></div>
                  <div>Rejected: <strong>{campaignDetail.drafts?.breakdown?.Rejected || 0}</strong></div>
                </div>
              </div>
              <div style={{ background: '#F8FAFC', padding: 12, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: '#64748B' }}>Queue Fulfillment</div>
                <div style={{ marginTop: 6, fontSize: 13 }}>
                  <div>Total Queued: <strong>{campaignDetail.dispatch?.total_queued || 0}</strong></div>
                  <div>Sent: <strong style={{ color: '#0F766E' }}>{campaignDetail.dispatch?.breakdown?.Sent || 0}</strong></div>
                  <div>Failed: <strong style={{ color: '#DC2626' }}>{campaignDetail.dispatch?.breakdown?.Failed || 0}</strong></div>
                  <div>Blocked: <strong>{campaignDetail.dispatch?.breakdown?.Blocked || 0}</strong></div>
                </div>
              </div>
              <div style={{ background: '#F8FAFC', padding: 12, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: '#64748B' }}>Success Ratio</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#0F766E', marginTop: 4 }}>
                  {campaignDetail.dispatch?.sent_success_rate || '0.0%'}
                </div>
                <div style={{ fontSize: 11, color: '#64748B' }}>Successful SMTP submission rate</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Delivery Activity Log */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
          <div>
            <h3 className="card-title">Recent Delivery Telemetry</h3>
            <p className="card-subtitle">Granular event trail from persistent dispatch log.</p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ position: 'relative', width: 220 }}>
              <input
                type="text"
                className="input input-sm"
                placeholder="Filter events..."
                value={activityFilter}
                onChange={(e) => setActivityFilter(e.target.value)}
                style={{ paddingLeft: 28 }}
              />
              <Search size={13} style={{ position: 'absolute', left: 8, top: 9, color: '#94A3B8' }} />
            </div>
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Campaign</th>
                <th>Recipient</th>
                <th>Event</th>
                <th>Status</th>
                <th>Error / Details</th>
              </tr>
            </thead>
            <tbody>
              {filteredActivity.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px 16px', color: '#64748B' }}>
                    No delivery events recorded yet.
                  </td>
                </tr>
              ) : (
                filteredActivity.map((ev, idx) => (
                  <tr key={idx}>
                    <td style={{ fontSize: 11, fontFamily: 'monospace', color: '#64748B', whiteSpace: 'nowrap' }}>
                      {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '-'}
                    </td>
                    <td style={{ fontSize: 12, fontWeight: 500 }}>
                      {ev.campaign_name === 'System' || !ev.campaign_id ? (
                        <span className="badge" style={{ background: '#F1F5F9', color: '#475569', fontSize: 10, padding: '2px 6px' }}>
                          System Telemetry
                        </span>
                      ) : (
                        ev.campaign_name
                      )}
                    </td>
                    <td style={{ fontSize: 12 }}>
                      {ev.recipient_email}
                    </td>
                    <td>
                      <span className="badge" style={{ textTransform: 'capitalize', fontSize: 11 }}>
                        {ev.event}
                      </span>
                    </td>
                    <td>{getStatusBadge(ev.status)}</td>
                    <td style={{ fontSize: 11, color: ev.error ? '#DC2626' : '#64748B', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {ev.error || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
