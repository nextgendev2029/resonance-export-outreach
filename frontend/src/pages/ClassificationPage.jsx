import React, { useState, useEffect } from 'react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';
import { Tags, Building2, User, Play, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

export default function ClassificationPage({ onRefreshStats, stats }) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Ready to classify contacts.');
  const [batchSize, setBatchSize] = useState(20);
  const [forceAll, setForceAll] = useState(false);
  const [activeTab, setActiveTab] = useState('business');
  const [leads, setLeads] = useState([]);
  const [loadingLeads, setLoadingLeads] = useState(false);
  const [classificationNotice, setClassificationNotice] = useState(null);

  const fetchLeads = async () => {
    setLoadingLeads(true);
    try {
      const data = await api.getLeads({ classification: activeTab });
      setLeads(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingLeads(false);
    }
  };

  const pollStatus = async () => {
    try {
      const res = await api.getClassifyStatus();
      setRunning(res.is_running);
      setProgress(res.progress);
      setStatusMessage(res.status_message);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    pollStatus();
    fetchLeads();
  }, [activeTab]);

  useEffect(() => {
    let interval = null;
    if (running) {
      interval = setInterval(() => {
        pollStatus();
      }, 1500);
    } else if (interval) {
      clearInterval(interval);
      fetchLeads();
      if (onRefreshStats) onRefreshStats();
    }
    return () => clearInterval(interval);
  }, [running]);

  const handleClassifyUnclassified = async () => {
    setRunning(true);
    setStatusMessage('Classifying unclassified prospects with AI intelligence...');
    try {
      const res = await api.classifyLeads({ force_all: false, allow_demo: false });
      setClassificationNotice(
        `Classification completed: ${res.business_count || 0} Business, ${res.individual_count || 0} Individual, ${res.unclassified_count || 0} Unclassified.`
      );
      fetchLeads();
      if (onRefreshStats) onRefreshStats();
    } catch (err) {
      alert('Classification error: ' + err.message);
    } finally {
      setRunning(false);
    }
  };

  const handleReclassifyAll = async () => {
    if (!window.confirm('Reclassify all leads using current AI intelligence?')) return;
    setRunning(true);
    setStatusMessage('Re-evaluating all leads...');
    try {
      const res = await api.classifyLeads({ force_all: true, allow_demo: false });
      setClassificationNotice(
        `Reclassification completed: ${res.business_count || 0} Business, ${res.individual_count || 0} Individual, ${res.unclassified_count || 0} Unclassified.`
      );
      fetchLeads();
      if (onRefreshStats) onRefreshStats();
    } catch (err) {
      alert('Classification error: ' + err.message);
    } finally {
      setRunning(false);
    }
  };

  const totalLeads = stats?.total_leads || 0;
  const bizCount = stats?.business_contacts || 0;
  const indCount = stats?.individual_contacts || 0;
  const uncCount = stats?.unclassified_contacts || 0;

  const bizPct = totalLeads > 0 ? Math.round((bizCount / totalLeads) * 100) : 0;
  const indPct = totalLeads > 0 ? Math.round((indCount / totalLeads) * 100) : 0;
  const uncPct = totalLeads > 0 ? Math.round((uncCount / totalLeads) * 100) : 0;

  return (
    <div>
      {/* Overview & Action Panel */}
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">AI Intent & Segment Classifier</h2>
            <p className="panel-description">
              Deduplicates contacts and partitions buyer emails into B2B Wholesale vs Individual Retail audiences using Gemini intelligence.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-sm btn-primary"
              onClick={handleClassifyUnclassified}
              disabled={running}
            >
              <Tags size={13} />
              <span>{running ? 'Classifying...' : 'Classify Unclassified Leads'}</span>
            </button>
            <button
              className="btn btn-sm"
              onClick={handleReclassifyAll}
              disabled={running}
              title="Force reclassification across all records"
            >
              <RefreshCw size={13} />
              <span>Reclassify All</span>
            </button>
          </div>
        </div>

        <div className="panel-body">
          {classificationNotice && (
            <div style={{ marginBottom: 14, padding: '8px 12px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 6, fontSize: 12.5, color: '#166534', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>{classificationNotice}</span>
              <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#166534' }} onClick={() => setClassificationNotice(null)}>✕</button>
            </div>
          )}

          {/* Segment Statistics Mini-Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '16px' }}>
            <div style={{ padding: '12px 14px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, color: '#166534', textTransform: 'uppercase' }}>
                  <Building2 size={13} />
                  <span>Business (B2B) Emails</span>
                </div>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#166534' }}>{bizPct}%</span>
              </div>
              <div style={{ fontSize: '22px', fontWeight: 700, color: '#14532D', marginTop: '4px' }}>
                {bizCount}
              </div>
              <div style={{ fontSize: '11px', color: '#166534' }}>Wholesale distributors, studios & academies</div>
            </div>

            <div style={{ padding: '12px 14px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, color: '#475569', textTransform: 'uppercase' }}>
                  <User size={13} />
                  <span>Individual Retail</span>
                </div>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#475569' }}>{indPct}%</span>
              </div>
              <div style={{ fontSize: '22px', fontWeight: 700, color: '#0F172A', marginTop: '4px' }}>
                {indCount}
              </div>
              <div style={{ fontSize: '11px', color: '#64748B' }}>Solo collectors & meditation practitioners</div>
            </div>

            <div style={{ padding: '12px 14px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#92400E', textTransform: 'uppercase' }}>
                  Unclassified Pending
                </div>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#92400E' }}>{uncPct}%</span>
              </div>
              <div style={{ fontSize: '22px', fontWeight: 700, color: '#78350F', marginTop: '4px' }}>
                {uncCount}
              </div>
              <div style={{ fontSize: '11px', color: '#92400E' }}>Ambiguous evidence / awaiting review</div>
            </div>
          </div>

          {/* Progress Indicator */}
          {(running || progress > 0) && (
            <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid #E2E8F0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ fontWeight: 600, color: '#0F172A' }}>Classification Engine:</span>
                <span style={{ color: '#0F766E', fontWeight: 600 }}>{progress}%</span>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>
                {statusMessage}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Segment Breakdown Table */}
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Segment Audience Review</h2>
            <p className="panel-description">Review classified prospects before launching tailored campaigns</p>
          </div>
          <div className="tabs-bar" style={{ margin: 0, border: 'none' }}>
            <button
              className={`tab-btn ${activeTab === 'business' ? 'active' : ''}`}
              onClick={() => setActiveTab('business')}
            >
              <Building2 size={13} />
              <span>Business ({bizCount})</span>
            </button>
            <button
              className={`tab-btn ${activeTab === 'individual' ? 'active' : ''}`}
              onClick={() => setActiveTab('individual')}
            >
              <User size={13} />
              <span>Individual ({indCount})</span>
            </button>
            <button
              className={`tab-btn ${activeTab === 'unclassified' ? 'active' : ''}`}
              onClick={() => setActiveTab('unclassified')}
            >
              <span>Unclassified ({uncCount})</span>
            </button>
          </div>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          {loadingLeads ? (
            <div style={{ padding: '30px', textAlign: 'center', color: '#64748B' }}>Loading segment...</div>
          ) : leads.length === 0 ? (
            <div className="empty-state-box" style={{ padding: '32px 16px' }}>
              <div className="empty-state-title">No {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Leads Found</div>
              <div className="empty-state-desc">
                Run the AI intent classifier or import new prospects to populate this segment.
              </div>
            </div>
          ) : (
            <div className="table-container" style={{ border: 'none' }}>
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Company / Name</th>
                    <th>Country</th>
                    <th>Source</th>
                    <th>Validation</th>
                    <th>Outreach Status</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((b) => (
                    <tr key={b.lead_id || b.email}>
                      <td className="mono-cell" style={{ fontWeight: 500 }}>
                        {b.email || '(No email)'}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{b.company_name}</div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>{b.buyer_name}</div>
                      </td>
                      <td>{b.country || 'Global'}</td>
                      <td>{b.source_platform}</td>
                      <td>
                        <StatusBadge type="validation" value={b.validation_status} />
                      </td>
                      <td>
                        <StatusBadge type="outreach" value={b.outreach_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
