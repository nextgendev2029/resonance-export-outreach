import React, { useState, useEffect } from 'react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';
import {
  Compass,
  Search,
  RefreshCw,
  Play,
  ExternalLink,
  Building2,
  User,
  Globe,
  Mail,
  Phone,
  MapPin,
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  X,
  Copy,
  Check,
  Save,
  Layers,
  Settings
} from 'lucide-react';

export default function LeadIntelligencePage({ onRefreshStats, setTab }) {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [datasetFilter, setDatasetFilter] = useState('real'); // 'real', 'all', 'demo'
  const [statusFilter, setStatusFilter] = useState('all');
  const [classFilter, setClassFilter] = useState('all');
  const [relevanceFilter, setRelevanceFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Active Run & Polling
  const [runStatus, setRunStatus] = useState({ is_running: false });
  const [activePolling, setActivePolling] = useState(false);

  // Lead Detail Drawer
  const [selectedLead, setSelectedLead] = useState(null);
  const [drawerNotes, setDrawerNotes] = useState('');
  const [drawerClassification, setDrawerClassification] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [enrichingSingle, setEnrichingSingle] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const fetchStats = async () => {
    try {
      const s = await api.getIntelligenceStats();
      setStats(s);
    } catch (err) {
      console.error('Failed to load intelligence stats:', err);
    }
  };

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const data = await api.getIntelligenceLeads({
        dataset: datasetFilter,
        status: statusFilter,
        classification: classFilter,
        relevance: relevanceFilter,
        search: searchTerm,
      });
      setLeads(data);
    } catch (err) {
      console.error('Failed to load intelligence leads:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchLeads();
    }, 150);
    return () => clearTimeout(timer);
  }, [datasetFilter, statusFilter, classFilter, relevanceFilter, searchTerm]);

  // Polling active intelligence run
  useEffect(() => {
    let interval = null;
    if (activePolling) {
      interval = setInterval(async () => {
        try {
          const st = await api.getIntelligenceStatus();
          setRunStatus(st);
          if (!st.is_running) {
            setActivePolling(false);
            fetchStats();
            fetchLeads();
            if (onRefreshStats) onRefreshStats();
          }
        } catch (_) {
          setActivePolling(false);
        }
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activePolling]);

  const handleStartEnrichment = async () => {
    try {
      await api.startIntelligenceRun({
        force_refresh: false,
        allow_demo: datasetFilter === 'demo',
      });
      setActivePolling(true);
      setRunStatus({ is_running: true, progress: 5, status_message: 'Initializing intelligence run...' });
    } catch (err) {
      alert(`Could not start enrichment: ${err.message}`);
    }
  };

  const openLeadDrawer = async (lead) => {
    setSelectedLead(lead);
    setDrawerNotes(lead.notes || '');
    setDrawerClassification(lead.classification || 'Unclassified');

    // Fetch freshest intelligence details
    try {
      const fresh = await api.getIntelligenceLeadDetail(lead.lead_id);
      setSelectedLead(fresh);
      setDrawerNotes(fresh.notes || '');
      setDrawerClassification(fresh.classification || 'Unclassified');
    } catch (_) {}
  };

  const handleEnrichSingle = async () => {
    if (!selectedLead) return;
    setEnrichingSingle(true);
    try {
      const res = await api.enrichSingleLead(selectedLead.lead_id);
      if (res && res.enrichment) {
        const updated = { ...selectedLead, enrichment: res.enrichment };
        setSelectedLead(updated);
        fetchStats();
        fetchLeads();
        if (onRefreshStats) onRefreshStats();
      }
    } catch (err) {
      alert(`Enrichment failed: ${err.message}`);
    } finally {
      setEnrichingSingle(false);
    }
  };

  const handleSaveDrawerNotes = async () => {
    if (!selectedLead) return;
    setSavingNotes(true);
    try {
      await api.updateLead(selectedLead.lead_id, {
        notes: drawerNotes,
        classification: drawerClassification,
      });
      setSelectedLead((prev) => ({
        ...prev,
        notes: drawerNotes,
        classification: drawerClassification,
      }));
      fetchLeads();
      if (onRefreshStats) onRefreshStats();
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSavingNotes(false);
    }
  };

  const copyEmail = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  const enrichmentData = selectedLead?.enrichment || {};
  const publicContact = enrichmentData.public_contact || {};
  const businessDetails = enrichmentData.business_details || {};
  const buyerRelevance = enrichmentData.buyer_relevance || {};
  const classificationObj = enrichmentData.classification || {};
  const evidenceList = enrichmentData.evidence || [];
  const pagesCrawled = enrichmentData.pages_crawled || [];

  return (
    <div className="page-container">
      {/* Header section */}
      <div className="section-header-row" style={{ marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            Lead Intelligence
          </h2>
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
            Enrich and verify discovered prospects using public business information and AI-assisted classification.
          </p>
        </div>

        {/* AI Provider Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {stats?.ai_status?.is_configured ? (
            <div className="badge badge-valid" style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px' }}>
              <ShieldCheck size={13} />
              <span>Gemini 3 Flash ({stats.ai_status.model || 'gemini-3-flash-preview'}) • Ready</span>
            </div>
          ) : (
            <button
              className="badge badge-warn"
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px', cursor: 'pointer', border: '1px solid #F59E0B' }}
              onClick={() => setTab && setTab('settings')}
              title="Click to configure Gemini API Key in Settings"
            >
              <AlertCircle size={13} />
              <span>Gemini: Not Configured (Configure)</span>
            </button>
          )}

          <button
            className="btn btn-sm btn-primary"
            onClick={handleStartEnrichment}
            disabled={runStatus.is_running || loading}
          >
            <Play size={13} />
            <span>Run Enrichment</span>
          </button>
        </div>
      </div>

      {/* KPI Overview Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginBottom: 16 }}>
        <div className="stat-card" style={{ padding: '10px 14px' }}>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Real Leads</span>
          <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>{stats?.total_real_leads ?? '-'}</span>
        </div>
        <div className="stat-card" style={{ padding: '10px 14px' }}>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Enriched</span>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#0F766E', marginTop: 2 }}>{stats?.total_enriched ?? '-'}</span>
        </div>
        <div className="stat-card" style={{ padding: '10px 14px' }}>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Needs Enrichment</span>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#D97706', marginTop: 2 }}>{stats?.needs_enrichment ?? '-'}</span>
        </div>
        <div className="stat-card" style={{ padding: '10px 14px' }}>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>High Relevance</span>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#047857', marginTop: 2 }}>{stats?.relevance_distribution?.High ?? 0}</span>
        </div>
        <div className="stat-card" style={{ padding: '10px 14px' }}>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Medium Relevance</span>
          <span style={{ fontSize: 18, fontWeight: 700, color: '#0F766E', marginTop: 2 }}>{stats?.relevance_distribution?.Medium ?? 0}</span>
        </div>
        <div className="stat-card" style={{ padding: '10px 14px' }}>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Uncertain / Unknown</span>
          <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-muted)', marginTop: 2 }}>{stats?.relevance_distribution?.Unknown ?? 0}</span>
        </div>
      </div>

      {/* Live Enrichment Progress Banner */}
      {runStatus.is_running && (
        <div className="panel" style={{ marginBottom: 16, borderColor: 'var(--accent-primary)', background: '#F0FDFA' }}>
          <div className="panel-body" style={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <RefreshCw size={14} className="spin" style={{ color: 'var(--accent-primary)' }} />
                <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {runStatus.status_message}
                </span>
              </div>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-primary)' }}>
                {runStatus.progress}%
              </span>
            </div>
            <div style={{ width: '100%', height: 5, background: '#E2E8F0', borderRadius: 3, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${runStatus.progress}%`,
                  height: '100%',
                  background: 'var(--accent-primary)',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Operational Toolbar */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-body" style={{ padding: '12px 16px' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', flex: 1 }}>
              {/* Search */}
              <div style={{ position: 'relative', minWidth: 220 }}>
                <Search size={14} style={{ position: 'absolute', left: 9, top: 9, color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search company, contact, country..."
                  className="input-field"
                  style={{ paddingLeft: 28, height: 32, fontSize: 12 }}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>

              {/* Dataset Filter */}
              <select
                className="select-field"
                style={{ height: 32, fontSize: 12 }}
                value={datasetFilter}
                onChange={(e) => setDatasetFilter(e.target.value)}
              >
                <option value="real">Real Discovered Only</option>
                <option value="all">All Leads (Real + Demo)</option>
                <option value="demo">Demo / Seed Only</option>
              </select>

              {/* Status Filter */}
              <select
                className="select-field"
                style={{ height: 32, fontSize: 12 }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All Enrichment Status</option>
                <option value="needs_enrichment">Needs Enrichment</option>
                <option value="enriched">Enriched</option>
                <option value="failed">Failed</option>
                <option value="blocked">Blocked</option>
              </select>

              {/* Relevance Filter */}
              <select
                className="select-field"
                style={{ height: 32, fontSize: 12 }}
                value={relevanceFilter}
                onChange={(e) => setRelevanceFilter(e.target.value)}
              >
                <option value="all">All Relevance</option>
                <option value="High">High Relevance</option>
                <option value="Medium">Medium Relevance</option>
                <option value="Low">Low Relevance</option>
                <option value="Unknown">Unknown</option>
              </select>

              {/* Classification Filter */}
              <select
                className="select-field"
                style={{ height: 32, fontSize: 12 }}
                value={classFilter}
                onChange={(e) => setClassFilter(e.target.value)}
              >
                <option value="all">All Classifications</option>
                <option value="Business">Business</option>
                <option value="Individual">Individual</option>
                <option value="Unclassified">Unclassified</option>
              </select>
            </div>

            <button
              className="btn btn-sm"
              onClick={() => { fetchStats(); fetchLeads(); }}
              title="Refresh table"
            >
              <RefreshCw size={12} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Intelligence Table */}
      <div className="table-container">
        <table className="ops-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Contact & Role</th>
              <th>Classification</th>
              <th>Buyer Relevance</th>
              <th>Website</th>
              <th>Country</th>
              <th>AI Confidence</th>
              <th>Enrichment</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>
                  Loading prospect intelligence records...
                </td>
              </tr>
            ) : leads.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '40px 16px' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                    No leads found matching current intelligence filters.
                  </div>
                </td>
              </tr>
            ) : (
              leads.map((lead) => {
                const enr = lead.enrichment || {};
                const cont = enr.public_contact || {};
                const contactDisplay = cont.name || lead.buyer_name || '-';
                const roleDisplay = cont.role && cont.role !== 'Unknown' ? cont.role : null;
                const confPercent = Math.round((lead.ai_confidence || 0) * 100);

                return (
                  <tr
                    key={lead.lead_id}
                    onClick={() => openLeadDrawer(lead)}
                    style={{ cursor: 'pointer' }}
                    className="table-row-hover"
                  >
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {lead.company_name || 'Sound & Wellness Prospect'}
                      </div>
                      {lead.email && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                          {lead.email}
                        </div>
                      )}
                    </td>

                    <td>
                      <div>{contactDisplay}</div>
                      {roleDisplay && <StatusBadge type="role" value={roleDisplay} />}
                    </td>

                    <td>
                      <StatusBadge type="classification" value={lead.classification} />
                    </td>

                    <td>
                      <StatusBadge type="relevance" value={lead.buyer_relevance || 'Unknown'} />
                    </td>

                    <td>
                      {lead.website ? (
                        <a
                          href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--accent-primary)', fontSize: 11.5 }}
                        >
                          <Globe size={11} />
                          <span>{lead.website.replace(/^https?:\/\/(www\.)?/, '').slice(0, 24)}</span>
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>No site</span>
                      )}
                    </td>

                    <td>
                      <span style={{ fontSize: 11.5 }}>{lead.country || 'International'}</span>
                    </td>

                    <td>
                      {confPercent > 0 ? (
                        <span style={{ fontSize: 11.5, fontWeight: 600, color: confPercent >= 75 ? '#065F46' : 'var(--text-secondary)' }}>
                          {confPercent}%
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>-</span>
                      )}
                    </td>

                    <td>
                      <StatusBadge type="enrichment" value={lead.enrichment_status || 'needs_enrichment'} />
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-sm"
                        style={{ padding: '2px 8px', fontSize: 11 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          openLeadDrawer(lead);
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Slide-out Intelligence Detail Drawer */}
      {selectedLead && (
        <div className="drawer-overlay" onClick={() => setSelectedLead(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 580 }}>
            {/* Drawer Header */}
            <div className="drawer-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Compass size={18} style={{ color: 'var(--accent-primary)' }} />
                <div>
                  <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                    {selectedLead.company_name || 'Prospect Intelligence'}
                  </h3>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    ID: {selectedLead.lead_id} • {selectedLead.is_demo === 'true' ? 'Demo Record' : 'Real Lead'}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={handleEnrichSingle}
                  disabled={enrichingSingle}
                  title="Run real-time website crawl and AI enrichment"
                >
                  <RefreshCw size={12} className={enrichingSingle ? 'spin' : ''} />
                  <span>{enrichingSingle ? 'Enriching...' : 'Enrich Now'}</span>
                </button>
                <button className="btn btn-sm" onClick={() => setSelectedLead(null)}>
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Drawer Content */}
            <div className="drawer-content" style={{ padding: 18 }}>
              {/* Relevance & Classification Status Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div className="intel-card">
                  <div className="intel-card-header">
                    <span className="intel-label">Buyer Relevance</span>
                    {buyerRelevance.confidence && (
                      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-primary)' }}>
                        {Math.round(buyerRelevance.confidence * 100)}% conf
                      </span>
                    )}
                  </div>
                  <div className="intel-value-row">
                    <StatusBadge type="relevance" value={buyerRelevance.relevance || selectedLead.buyer_relevance || 'Unknown'} />
                  </div>
                  {buyerRelevance.reason && (
                    <div className="intel-reason">{buyerRelevance.reason}</div>
                  )}
                </div>

                <div className="intel-card">
                  <div className="intel-card-header">
                    <span className="intel-label">Classification</span>
                    {classificationObj.confidence && (
                      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-primary)' }}>
                        {Math.round(classificationObj.confidence * 100)}% conf
                      </span>
                    )}
                  </div>
                  <div className="intel-value-row">
                    <StatusBadge type="classification" value={selectedLead.classification || 'Unclassified'} />
                  </div>
                  {classificationObj.reason && (
                    <div className="intel-reason">{classificationObj.reason}</div>
                  )}
                </div>
              </div>

              {/* Business Capabilities */}
              <div className="intel-card">
                <div className="intel-card-header">
                  <span className="intel-label">Factual Business Profile</span>
                  <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>Verified Public Data</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12, marginBottom: 8 }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: 10.5 }}>Business Type</span>
                    <strong style={{ color: 'var(--text-primary)' }}>{businessDetails.business_type || 'Unknown / General'}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: 10.5 }}>Industry Sector</span>
                    <strong style={{ color: 'var(--text-primary)' }}>{businessDetails.industry || 'Sound Therapy / Wellness'}</strong>
                  </div>
                </div>

                {businessDetails.company_description && (
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.45, marginTop: 6 }}>
                    {businessDetails.company_description}
                  </div>
                )}
              </div>

              {/* Public Contact Information */}
              <div className="intel-card">
                <div className="intel-card-header">
                  <span className="intel-label">Public Business Contact</span>
                  {publicContact.role && publicContact.role !== 'Unknown' && (
                    <StatusBadge type="role" value={publicContact.role} />
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <User size={13} style={{ color: 'var(--text-muted)' }} />
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {publicContact.name || selectedLead.buyer_name || 'No named contact published'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Mail size={13} style={{ color: 'var(--text-muted)' }} />
                      <span style={{ fontFamily: 'monospace', fontSize: 11.5 }}>
                        {publicContact.email || selectedLead.email || 'No email published'}
                      </span>
                    </div>
                    {(publicContact.email || selectedLead.email) && (
                      <button
                        className="btn btn-sm"
                        style={{ padding: '1px 6px', fontSize: 10.5 }}
                        onClick={() => copyEmail(publicContact.email || selectedLead.email)}
                      >
                        {copiedEmail ? <Check size={11} /> : <Copy size={11} />}
                        <span>{copiedEmail ? 'Copied' : 'Copy'}</span>
                      </button>
                    )}
                  </div>

                  {publicContact.phone && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Phone size={13} style={{ color: 'var(--text-muted)' }} />
                      <span>{publicContact.phone}</span>
                    </div>
                  )}

                  {selectedLead.website && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Globe size={13} style={{ color: 'var(--text-muted)' }} />
                      <a
                        href={selectedLead.website.startsWith('http') ? selectedLead.website : `https://${selectedLead.website}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}
                      >
                        {selectedLead.website}
                      </a>
                    </div>
                  )}
                </div>
              </div>

              {/* Verified Source Evidence */}
              {evidenceList.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span className="intel-label">Ground-Truth Evidence Snippets</span>
                    <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>{evidenceList.length} verified quotes</span>
                  </div>

                  <div className="evidence-list">
                    {evidenceList.map((ev, idx) => (
                      <div key={idx} className="evidence-item">
                        <div className="evidence-quote">"{ev.evidence}"</div>
                        <div className="evidence-meta">
                          <span>Field: <strong>{ev.field}</strong></span>
                          {ev.url && (
                            <a
                              href={ev.url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ color: 'var(--accent-primary)', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                            >
                              <span>Inspect Source</span>
                              <ExternalLink size={10} />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Crawled Pages */}
              {pagesCrawled.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <span className="intel-label" style={{ display: 'block', marginBottom: 4 }}>Pages Inspected</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {pagesCrawled.map((url, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          fontSize: 10.5,
                          background: '#FFFFFF',
                          border: '1px solid var(--border-default)',
                          padding: '2px 6px',
                          borderRadius: 'var(--radius-sm)',
                          color: 'var(--text-secondary)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 3
                        }}
                      >
                        <span>{url.replace(/^https?:\/\//, '').slice(0, 32)}</span>
                        <ExternalLink size={9} />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Operator Notes & Status Overrides */}
              <div className="intel-card">
                <div className="intel-card-header">
                  <span className="intel-label">Operator Classification Override & Notes</span>
                </div>

                <div style={{ marginBottom: 8 }}>
                  <select
                    className="select-field"
                    style={{ width: '100%', height: 32, fontSize: 12, marginBottom: 8 }}
                    value={drawerClassification}
                    onChange={(e) => setDrawerClassification(e.target.value)}
                  >
                    <option value="Business">Business (Wholesale / Studio)</option>
                    <option value="Individual">Individual (Retail Collector)</option>
                    <option value="Unclassified">Unclassified</option>
                  </select>

                  <textarea
                    className="input-field"
                    style={{ width: '100%', height: 60, fontSize: 12, resize: 'vertical' }}
                    placeholder="Record notes on buyer discussions, specific frequencies needed, order sizes..."
                    value={drawerNotes}
                    onChange={(e) => setDrawerNotes(e.target.value)}
                  />
                </div>

                <button
                  className="btn btn-sm btn-primary"
                  onClick={handleSaveDrawerNotes}
                  disabled={savingNotes}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  <Save size={12} />
                  <span>{savingNotes ? 'Saving...' : 'Save Notes & Override'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
