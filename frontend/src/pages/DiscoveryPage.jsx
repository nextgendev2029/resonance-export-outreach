import React, { useState, useEffect } from 'react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';
import {
  Search,
  Play,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sliders,
  History,
  ExternalLink,
  Layers,
  Plus,
  Compass,
  Building2,
  MapPin,
  Mail,
  Phone,
  ShieldCheck,
  Check,
  X,
  Info,
  Globe,
  Tag,
  ArrowRight
} from 'lucide-react';

const ALL_BUYER_TYPES = [
  'Importer',
  'Distributor',
  'Wholesaler',
  'Retailer',
  'Home Decor Store',
  'Gift Shop',
  'Wellness Store',
  'Interior Decor Business',
  'Lifestyle Store',
  'Boutique Store',
  'B2B Buyer',
  'Specialty Store'
];

const US_STATES_LIST = [
  'All 50 US States',
  'California', 'Texas', 'Florida', 'New York', 'Illinois',
  'Pennsylvania', 'Ohio', 'Georgia', 'North Carolina', 'Michigan',
  'New Jersey', 'Virginia', 'Washington', 'Arizona', 'Massachusetts',
  'Tennessee', 'Indiana', 'Missouri', 'Maryland', 'Wisconsin',
  'Colorado', 'Minnesota', 'South Carolina', 'Alabama', 'Louisiana',
  'Kentucky', 'Oregon', 'Oklahoma', 'Connecticut', 'Utah'
];

export default function DiscoveryPage({ onRefreshStats }) {
  // Step 1: Seller / Product Profile
  const [productName, setProductName] = useState('Singing Bowls');
  const [productCategory, setProductCategory] = useState('Home Decor');
  const [productDescription, setProductDescription] = useState(
    'Handcrafted singing bowls suitable for home decor, wellness spaces, meditation stores and lifestyle retailers.'
  );

  // Step 2: Target Market
  const [targetCountry, setTargetCountry] = useState('United States');
  const [targetState, setTargetState] = useState('');

  // Step 3: Buyer Types
  const [selectedBuyerTypes, setSelectedBuyerTypes] = useState([
    'Importer',
    'Distributor',
    'Wholesaler',
    'Retailer',
    'Home Decor Store',
    'Gift Shop',
    'Wellness Store'
  ]);
  const [customBuyerType, setCustomBuyerType] = useState('');

  // Step 4: Discovery Sources & Health
  const [providersHealth, setProvidersHealth] = useState([]);
  const [selectedSources, setSelectedSources] = useState({
    google: true,
    directory: true,
    website: true,
    facebook: false,
    linkedin: false,
  });
  const [maxPerSource, setMaxPerSource] = useState(5);

  // Operational State
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Ready to discover US Home Decor buyers.');
  const [currentSource, setCurrentSource] = useState('');
  const [discoveredLeads, setDiscoveredLeads] = useState([]);
  const [latestSummary, setLatestSummary] = useState(null);

  // Run History & Modals
  const [runs, setRuns] = useState([]);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [selectedRunDetail, setSelectedRunDetail] = useState(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configStatus, setConfigStatus] = useState(null);

  const fetchConfigAndProviders = async () => {
    try {
      const [cfg, providers, cStatus] = await Promise.all([
        api.getDiscoveryConfig(),
        api.getDiscoveryProviders(),
        api.getDiscoveryConfigStatus()
      ]);
      if (cfg.default_profile) {
        if (cfg.default_profile.product_name) setProductName(cfg.default_profile.product_name);
        if (cfg.default_profile.product_category) setProductCategory(cfg.default_profile.product_category);
        if (cfg.default_profile.product_description) setProductDescription(cfg.default_profile.product_description);
        if (cfg.default_profile.target_country) setTargetCountry(cfg.default_profile.target_country);
      }
      if (providers) setProvidersHealth(providers);
      if (cStatus) setConfigStatus(cStatus);
    } catch (err) {
      console.error('Failed to load discovery configuration:', err);
    }
  };

  const fetchRuns = async () => {
    setLoadingRuns(true);
    try {
      const data = await api.getDiscoveryRuns();
      setRuns(data);
    } catch (err) {
      console.error('Failed to fetch discovery runs:', err);
    } finally {
      setLoadingRuns(false);
    }
  };

  const pollStatus = async () => {
    try {
      const res = await api.getDiscoveryStatus();
      setRunning(res.is_running);
      setProgress(res.progress);
      setStatusMessage(res.status_message);
      if (res.current_source) setCurrentSource(res.current_source);
      if (res.discovered_leads && res.discovered_leads.length > 0) {
        setDiscoveredLeads(res.discovered_leads);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchConfigAndProviders();
    fetchRuns();
    pollStatus();
  }, []);

  useEffect(() => {
    let interval = null;
    if (running) {
      interval = setInterval(() => {
        pollStatus();
      }, 1500);
    } else if (interval) {
      clearInterval(interval);
      fetchRuns();
      onRefreshStats();
    }
    return () => clearInterval(interval);
  }, [running]);

  const toggleBuyerType = (type) => {
    if (selectedBuyerTypes.includes(type)) {
      if (selectedBuyerTypes.length === 1) {
        alert('Please keep at least one target buyer classification selected.');
        return;
      }
      setSelectedBuyerTypes(selectedBuyerTypes.filter((t) => t !== type));
    } else {
      setSelectedBuyerTypes([...selectedBuyerTypes, type]);
    }
  };

  const handleAddCustomType = (e) => {
    e.preventDefault();
    const clean = customBuyerType.trim();
    if (clean && !selectedBuyerTypes.includes(clean)) {
      setSelectedBuyerTypes([...selectedBuyerTypes, clean]);
      setCustomBuyerType('');
    }
  };

  const toggleSource = (sourceId) => {
    setSelectedSources((prev) => ({
      ...prev,
      [sourceId]: !prev[sourceId]
    }));
  };

  const handleStartDiscovery = async () => {
    const activeSources = Object.keys(selectedSources).filter((k) => selectedSources[k]);
    if (activeSources.length === 0) {
      alert('Please select at least one active discovery channel.');
      return;
    }

    setRunning(true);
    setProgress(5);
    setStatusMessage(`Initiating discovery for ${productName} in the United States...`);
    setDiscoveredLeads([]);
    setLatestSummary(null);

    const payload = {
      product_name: productName.trim() || 'Singing Bowls',
      product_category: productCategory.trim() || 'Home Decor',
      product_description: productDescription.trim(),
      target_country: 'United States',
      target_state: targetState === 'All 50 US States' ? '' : targetState,
      buyer_types: selectedBuyerTypes,
      sources: activeSources,
      max_per_source: parseInt(maxPerSource, 10),
    };

    try {
      const res = await api.searchBuyers(payload);
      setRunning(false);
      setProgress(100);
      setStatusMessage(
        `Discovery complete in ${res.summary.duration_seconds}s: ${res.summary.extracted_count} US buyers extracted (${res.summary.new_leads_added} new leads ingested).`
      );
      setDiscoveredLeads(res.results || []);
      setLatestSummary(res.summary);
      fetchRuns();
      onRefreshStats();
    } catch (err) {
      // Fall back to polling if running in background
      try {
        await api.startDiscovery({
          keyword: productName,
          product_name: productName,
          product_category: productCategory,
          product_description: productDescription,
          target_country: 'United States',
          target_state: targetState === 'All 50 US States' ? '' : targetState,
          buyer_types: selectedBuyerTypes,
          sources: activeSources,
          max_per_source: parseInt(maxPerSource, 10),
        });
        pollStatus();
      } catch (fallbackErr) {
        alert('Discovery error: ' + fallbackErr.message);
        setRunning(false);
      }
    }
  };

  return (
    <div>
      {/* Overview Banner */}
      <div className="notice-box" style={{ marginBottom: '18px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
          <Compass size={18} style={{ color: '#0F766E', marginTop: '2px', flexShrink: 0 }} />
          <div>
            <strong style={{ color: '#0F172A' }}>US Home Decor Buyer Discovery Engine:</strong> Configures seller export product specifications, enforces United States commercial market targeting, queries official and directory search APIs with independent fault-isolation, eliminates duplicates via cross-source dual-key matching, and validates buyer emails for subsequent outreach review.
          </div>
        </div>
      </div>

      {/* Source Health Strip */}
      <div style={{ marginBottom: '22px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            API & Search Integration Health
          </span>
          <button
            className="btn btn-sm"
            onClick={() => setShowConfigModal(true)}
            style={{ fontSize: '11px', padding: '3px 8px' }}
          >
            <Info size={12} />
            <span>API Requirements Guide</span>
          </button>
        </div>

        <div className="source-health-grid">
          {providersHealth.map((src) => {
            const isReady = src.status === 'READY';
            return (
              <div key={src.id} className={`source-health-card ${isReady ? 'ready' : 'requires_config'}`}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, fontSize: '12.5px', color: '#0F172A' }}>{src.name}</span>
                    <span className={`badge ${isReady ? 'badge-valid' : 'badge-warn'}`}>
                      {isReady ? 'READY' : 'NOT CONFIGURED'}
                    </span>
                  </div>
                  <div style={{ fontSize: '10.5px', color: '#0F766E', fontWeight: 500, marginBottom: '4px' }}>
                    {src.integration_type}
                  </div>
                  <p style={{ fontSize: '11px', color: '#64748B', lineHeight: '1.35', margin: 0 }}>
                    {src.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 5-Step Configuration Workspace */}
      <div className="panel" style={{ marginBottom: '22px' }}>
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Buyer Discovery Workspace</h2>
            <p className="panel-description">
              Follow the 5-step operational workflow to identify verified US buyers for Home Decor products.
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleStartDiscovery}
            disabled={running}
            style={{ minWidth: '150px' }}
          >
            {running ? <RefreshCw size={14} className="spin" /> : <Play size={14} />}
            <span>{running ? 'Finding Buyers...' : 'Find Buyers'}</span>
          </button>
        </div>

        <div className="panel-body">
          {/* STEP 1: Seller / Product */}
          <div style={{ paddingBottom: '16px', borderBottom: '1px solid #F1F5F9' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <span className="badge badge-valid" style={{ background: '#0F766E', color: '#FFFFFF', padding: '2px 8px', fontSize: '11px' }}>
                STEP 1
              </span>
              <strong style={{ fontSize: '13px', color: '#0F172A' }}>Seller & Product Specifications</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label">Product Name</label>
                <input
                  type="text"
                  className="input"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="e.g. Singing Bowls"
                  disabled={running}
                />
                <div className="form-hint">Generic export product (e.g. Singing Bowls, Brass Decor, Meditation Gongs).</div>
              </div>

              <div className="form-group">
                <label className="form-label">Product Category</label>
                <input
                  type="text"
                  className="input"
                  value={productCategory}
                  onChange={(e) => setProductCategory(e.target.value)}
                  placeholder="e.g. Home Decor"
                  disabled={running}
                />
                <div className="form-hint">Primary trade category: <strong>Home Decor</strong>.</div>
              </div>

              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">Product Commercial Positioning</label>
                <textarea
                  className="input"
                  rows={2}
                  value={productDescription}
                  onChange={(e) => setProductDescription(e.target.value)}
                  placeholder="Describe your artisan craftsmanship, acoustic quality, wholesale supply capabilities..."
                  disabled={running}
                  style={{ resize: 'vertical' }}
                />
              </div>
            </div>
          </div>

          {/* STEP 2: Target Market */}
          <div style={{ padding: '16px 0', borderBottom: '1px solid #F1F5F9' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <span className="badge badge-valid" style={{ background: '#0F766E', color: '#FFFFFF', padding: '2px 8px', fontSize: '11px' }}>
                STEP 2
              </span>
              <strong style={{ fontSize: '13px', color: '#0F172A' }}>Target Market & Location Targeting</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', alignItems: 'center' }}>
              <div className="form-group">
                <label className="form-label">Target Country (Fixed Requirement)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px' }}>
                  <span style={{ fontSize: '14px' }}>🇺🇸</span>
                  <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>United States</span>
                  <span className="badge badge-valid" style={{ marginLeft: 'auto', fontSize: '10.5px' }}>
                    Strict US Targeting Enforced
                  </span>
                </div>
                <div className="form-hint">All search queries enforce US location signals and post-verification.</div>
              </div>

              <div className="form-group">
                <label className="form-label">Target State (Optional)</label>
                <select
                  className="select"
                  value={targetState}
                  onChange={(e) => setTargetState(e.target.value)}
                  disabled={running}
                >
                  {US_STATES_LIST.map((st) => (
                    <option key={st} value={st === 'All 50 US States' ? '' : st}>
                      {st}
                    </option>
                  ))}
                </select>
                <div className="form-hint">Optionally restrict discovery to a commercial hub (e.g. California, New York, Texas).</div>
              </div>
            </div>
          </div>

          {/* STEP 3: Buyer Types */}
          <div style={{ padding: '16px 0', borderBottom: '1px solid #F1F5F9' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <span className="badge badge-valid" style={{ background: '#0F766E', color: '#FFFFFF', padding: '2px 8px', fontSize: '11px' }}>
                STEP 3
              </span>
              <strong style={{ fontSize: '13px', color: '#0F172A' }}>Commercial Buyer Classifications</strong>
              <span style={{ fontSize: '11px', color: '#64748B' }}>({selectedBuyerTypes.length} active)</span>
            </div>

            <div className="chips-wrapper" style={{ marginTop: '6px' }}>
              {ALL_BUYER_TYPES.map((type) => {
                const isSelected = selectedBuyerTypes.includes(type);
                return (
                  <button
                    key={type}
                    type="button"
                    className={`chip-tag ${isSelected ? 'active' : ''}`}
                    onClick={() => toggleBuyerType(type)}
                    disabled={running}
                  >
                    <span>{type}</span>
                    {isSelected ? '✓' : '+'}
                  </button>
                );
              })}
            </div>

            <form onSubmit={handleAddCustomType} style={{ display: 'flex', gap: '8px', marginTop: '10px', maxWidth: '300px' }}>
              <input
                type="text"
                className="input"
                style={{ padding: '4px 8px', fontSize: '11.5px' }}
                placeholder="Add custom buyer type..."
                value={customBuyerType}
                onChange={(e) => setCustomBuyerType(e.target.value)}
                disabled={running}
              />
              <button type="submit" className="btn btn-sm" disabled={!customBuyerType.trim() || running}>
                <Plus size={12} /> Add Tag
              </button>
            </form>
          </div>

          {/* STEP 4: Discovery Sources */}
          <div style={{ padding: '16px 0', borderBottom: '1px solid #F1F5F9' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <span className="badge badge-valid" style={{ background: '#0F766E', color: '#FFFFFF', padding: '2px 8px', fontSize: '11px' }}>
                STEP 4
              </span>
              <strong style={{ fontSize: '13px', color: '#0F172A' }}>Select Discovery Channels</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px', marginTop: '8px' }}>
              {[
                { id: 'google', label: 'Google Search API (US Geo-Targeted)', note: 'Custom Search Engine REST API' },
                { id: 'directory', label: 'US B2B Trade Directory', note: 'Wholesale registers & B2B indices' },
                { id: 'website', label: 'Direct Website Contact Crawler', note: 'Showroom & boutique contact pages' },
                { id: 'facebook', label: 'Facebook Business Pages (Meta Graph API)', note: 'Requires Meta token' },
                { id: 'linkedin', label: 'LinkedIn B2B Companies (Organization API)', note: 'Requires LinkedIn OAuth token' },
              ].map((s) => {
                const health = providersHealth.find((p) => p.id === s.id);
                const isConfigured = health ? health.is_configured : true;
                return (
                  <label
                    key={s.id}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px',
                      padding: '10px 12px',
                      background: selectedSources[s.id] ? '#F0FDFA' : '#FAFAFA',
                      border: `1px solid ${selectedSources[s.id] ? '#0F766E' : '#E2E8F0'}`,
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedSources[s.id]}
                      onChange={() => toggleSource(s.id)}
                      disabled={running}
                      style={{ marginTop: '2px' }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: '12px', color: '#0F172A' }}>{s.label}</span>
                        <span className={`badge ${isConfigured ? 'badge-valid' : 'badge-warn'}`} style={{ fontSize: '10px' }}>
                          {isConfigured ? 'READY' : 'NOT CONFIGURED'}
                        </span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>{s.note}</div>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* STEP 5: Execution Depth & Find Buyers */}
          <div style={{ paddingTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge badge-valid" style={{ background: '#0F766E', color: '#FFFFFF', padding: '2px 8px', fontSize: '11px' }}>
                  STEP 5
                </span>
                <span style={{ fontSize: '12.5px', fontWeight: 600, color: '#0F172A' }}>Results Depth:</span>
              </div>
              <select
                className="select"
                style={{ width: '180px', padding: '5px 8px', fontSize: '12px' }}
                value={maxPerSource}
                onChange={(e) => setMaxPerSource(e.target.value)}
                disabled={running}
              >
                <option value={3}>3 Results / Fast Pass</option>
                <option value={5}>5 Results / Standard Run</option>
                <option value={10}>10 Results / Deep Scan</option>
              </select>
            </div>

            <button
              className="btn btn-primary"
              onClick={handleStartDiscovery}
              disabled={running}
              style={{ minWidth: '160px', padding: '8px 16px', fontSize: '13px' }}
            >
              {running ? <RefreshCw size={14} className="spin" /> : <Play size={14} />}
              <span>{running ? 'Finding Buyers...' : 'Find Buyers'}</span>
            </button>
          </div>

          {/* Operational Progress Tracker */}
          {(running || progress > 0) && (
            <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #E2E8F0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ fontWeight: 600, color: '#0F172A' }}>
                  Execution Progress: {currentSource && <span style={{ color: '#0F766E' }}>[{currentSource}]</span>}
                </span>
                <span style={{ color: '#0F766E', fontWeight: 600 }}>{progress}%</span>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <div style={{ fontSize: '12px', color: '#475569', marginTop: '6px' }}>
                {statusMessage}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* STEP 6: Review Discovered Results (Telemetry Strip + Leads Table) */}
      {(latestSummary || discoveredLeads.length > 0) && (
        <div style={{ marginBottom: '22px' }}>
          {/* Telemetry KPI Strip */}
          {latestSummary && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginBottom: '14px' }}>
              <div className="card" style={{ padding: '12px 14px' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Raw Found</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                  {latestSummary.raw_count || 0}
                </div>
              </div>
              <div className="card" style={{ padding: '12px 14px', borderLeft: '3px solid #0F766E' }}>
                <div style={{ fontSize: '11px', color: '#0F766E', fontWeight: 600, textTransform: 'uppercase' }}>Unique Buyers</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#0F766E', marginTop: '2px' }}>
                  {latestSummary.extracted_count || 0}
                </div>
              </div>
              <div className="card" style={{ padding: '12px 14px' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>US Matches</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                  {latestSummary.us_match_count || 0}
                </div>
              </div>
              <div className="card" style={{ padding: '12px 14px' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Valid Emails</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                  {latestSummary.valid_email_count || 0}
                </div>
              </div>
              <div className="card" style={{ padding: '12px 14px' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Duplicates Skipped</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#64748B', marginTop: '2px' }}>
                  {latestSummary.duplicate_count || 0}
                </div>
              </div>
              <div className="card" style={{ padding: '12px 14px' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Ingested to DB</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#0F766E', marginTop: '2px' }}>
                  +{latestSummary.new_leads_added || 0}
                </div>
              </div>
            </div>
          )}

          {/* Results Table */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Step 6: Discovered US Buyers ({discoveredLeads.length})</h2>
                <p className="panel-description">
                  Normalized buyer records extracted via configured discovery APIs and persisted into data/buyers.csv
                </p>
              </div>
              <a href="/leads" className="btn btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <span>View In Master Leads</span>
                <ArrowRight size={13} />
              </a>
            </div>

            <div className="panel-body" style={{ padding: 0 }}>
              <div className="table-container" style={{ border: 'none' }}>
                <table className="ops-table">
                  <thead>
                    <tr>
                      <th>Company & Domain</th>
                      <th>Direct Email</th>
                      <th>US Location</th>
                      <th>Buyer Type</th>
                      <th>Relevance</th>
                      <th>Source Provenance</th>
                      <th>Link</th>
                    </tr>
                  </thead>
                  <tbody>
                    {discoveredLeads.map((item, idx) => (
                      <tr key={idx}>
                        <td>
                          <div style={{ fontWeight: 600, color: '#0F172A' }}>{item.company_name}</div>
                          {item.domain && (
                            <div style={{ fontSize: '11px', color: '#64748B' }}>{item.domain}</div>
                          )}
                        </td>
                        <td className="mono-cell">
                          {item.email ? (
                            <div>
                              <span>{item.email}</span>
                              <div style={{ marginTop: '2px' }}>
                                <StatusBadge type="validation" value={item.validation_status || item.email_status} />
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: '#C2410C', fontSize: '11px' }}>No direct email</span>
                          )}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span style={{ fontSize: '11.5px', fontWeight: 500 }}>
                              {item.state ? `${item.city ? `${item.city}, ` : ''}${item.state}` : item.country || 'United States'}
                            </span>
                            {item.country_match === 'true' && (
                              <span className="badge badge-valid" style={{ fontSize: '9px', padding: '1px 5px' }}>
                                US Verified
                              </span>
                            )}
                          </div>
                          {item.phone && (
                            <div style={{ fontSize: '10.5px', color: '#64748B' }}>{item.phone}</div>
                          )}
                        </td>
                        <td>
                          <span style={{ fontSize: '12px', fontWeight: 500, color: '#334155' }}>
                            {item.buyer_type || 'Wholesaler'}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              item.product_relevance === 'High'
                                ? 'badge-valid'
                                : item.product_relevance === 'Medium'
                                ? 'badge-warn'
                                : 'badge-neutral'
                            }`}
                          >
                            {item.product_relevance || 'High'}
                          </span>
                        </td>
                        <td>
                          <div style={{ fontSize: '11.5px', color: '#475569' }}>
                            {Array.isArray(item.provenance) && item.provenance.length > 0
                              ? item.provenance.join(', ')
                              : item.source_platform || item.source}
                          </div>
                        </td>
                        <td>
                          {item.source_url ? (
                            <a
                              href={item.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: '#0F766E', display: 'inline-flex', alignItems: 'center', gap: '3px', fontSize: '11px' }}
                            >
                              <span>View</span>
                              <ExternalLink size={10} />
                            </a>
                          ) : (
                            '-'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Discovery Run History */}
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Discovery Run History & Audit Trail</h2>
            <p className="panel-description">
              Audit log of previous buyer discovery passes persisted in data/discovery_runs.json
            </p>
          </div>
          <button className="btn btn-sm" onClick={fetchRuns} disabled={loadingRuns}>
            <RefreshCw size={12} className={loadingRuns ? 'spin' : ''} />
            <span>Refresh History</span>
          </button>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          {loadingRuns ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>Loading run history...</div>
          ) : runs.length === 0 ? (
            <div className="empty-state-box">
              <div className="empty-state-title">No Discovery Runs Recorded Yet</div>
              <div className="empty-state-desc">
                Launch your first buyer discovery above to start identifying verified US Home Decor prospects.
              </div>
              <button className="btn btn-sm btn-primary" onClick={handleStartDiscovery}>
                <Play size={12} /> Find Buyers
              </button>
            </div>
          ) : (
            <div className="table-container" style={{ border: 'none' }}>
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Run ID & Timestamp</th>
                    <th>Product & Category</th>
                    <th>Sources Used</th>
                    <th>Raw Results</th>
                    <th>Extracted Buyers</th>
                    <th>US Matches</th>
                    <th>Valid Emails</th>
                    <th>Duplicates</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.run_id}>
                      <td>
                        <div className="mono-cell" style={{ fontWeight: 600, color: '#0F172A' }}>
                          {r.run_id}
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>
                          {r.start_time || r.timestamp ? (r.start_time || r.timestamp).replace('T', ' ').split('.')[0] : '-'}
                        </div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 500 }}>
                          {r.profile ? `${r.profile.product_name} (${r.profile.product_category || 'Home Decor'})` : r.keyword}
                        </div>
                        <div style={{ fontSize: '10.5px', color: '#64748B' }}>
                          Target: {r.profile ? r.profile.target_country || 'United States' : 'United States'}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontSize: '11.5px', color: '#475569' }}>
                          {Array.isArray(r.sources_used) ? r.sources_used.join(', ') : 'Configured'}
                        </span>
                      </td>
                      <td>{r.raw_result_count || 0}</td>
                      <td>
                        <strong>{r.extracted_lead_count || 0}</strong>
                      </td>
                      <td>{r.us_match_count || (r.extracted_lead_count || 0)}</td>
                      <td>{r.valid_email_count || 0}</td>
                      <td>{r.duplicate_count || 0}</td>
                      <td>
                        <span className={`badge ${r.status === 'completed' ? 'badge-valid' : r.status === 'running' ? 'badge-warn' : 'badge-error'}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="mono-cell" style={{ fontSize: '11px', color: '#64748B' }}>
                        {r.duration_seconds ? `${r.duration_seconds}s` : '-'}
                      </td>
                      <td>
                        <button
                          className="btn btn-sm"
                          style={{ padding: '2px 6px', fontSize: '11px' }}
                          onClick={() => setSelectedRunDetail(r)}
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Run Detail Modal */}
      {selectedRunDetail && (
        <div className="modal-overlay" onClick={() => setSelectedRunDetail(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Discovery Run Details: {selectedRunDetail.run_id}</h2>
              <button
                className="btn btn-sm"
                onClick={() => setSelectedRunDetail(null)}
                style={{ border: 'none', background: 'none', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
                <div style={{ padding: '8px 12px', background: '#F8FAFC', borderRadius: '4px' }}>
                  <div style={{ fontSize: '11px', color: '#64748B' }}>Unique Buyers</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#0F766E' }}>{selectedRunDetail.extracted_lead_count || 0}</div>
                </div>
                <div style={{ padding: '8px 12px', background: '#F8FAFC', borderRadius: '4px' }}>
                  <div style={{ fontSize: '11px', color: '#64748B' }}>US Matches</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#0F172A' }}>{selectedRunDetail.us_match_count || (selectedRunDetail.extracted_lead_count || 0)}</div>
                </div>
                <div style={{ padding: '8px 12px', background: '#F8FAFC', borderRadius: '4px' }}>
                  <div style={{ fontSize: '11px', color: '#64748B' }}>Duration</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#0F172A' }}>{selectedRunDetail.duration_seconds ? `${selectedRunDetail.duration_seconds}s` : '-'}</div>
                </div>
              </div>

              {/* Executed Queries */}
              {selectedRunDetail.queries && selectedRunDetail.queries.length > 0 && (
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '11.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Executed Search Queries:
                  </div>
                  <div style={{ background: '#F8FAFC', padding: '8px 12px', borderRadius: '4px', fontSize: '11px', fontFamily: 'monospace' }}>
                    {selectedRunDetail.queries.map((q, idx) => (
                      <div key={idx} style={{ marginBottom: '4px' }}>• {q}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Source Breakdown */}
              {selectedRunDetail.sources_status && (
                <div>
                  <div style={{ fontSize: '11.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Provider Execution Breakdown:
                  </div>
                  <div style={{ border: '1px solid #E2E8F0', borderRadius: '4px', overflow: 'hidden' }}>
                    <table className="ops-table" style={{ margin: 0 }}>
                      <thead>
                        <tr>
                          <th>Provider</th>
                          <th>Status</th>
                          <th>Raw Count</th>
                          <th>Extracted</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(selectedRunDetail.sources_status).map(([srcKey, sData]) => (
                          <tr key={srcKey}>
                            <td style={{ fontWeight: 600 }}>{sData.source_name || srcKey}</td>
                            <td>
                              <span className={`badge ${sData.status === 'completed' ? 'badge-valid' : sData.status === 'requires_config' ? 'badge-warn' : 'badge-error'}`}>
                                {sData.status}
                              </span>
                            </td>
                            <td>{sData.raw_count || 0}</td>
                            <td>{sData.records_extracted || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-sm btn-primary" onClick={() => setSelectedRunDetail(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* API Requirements Modal */}
      {showConfigModal && (
        <div className="modal-overlay" onClick={() => setShowConfigModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Discovery API Configuration Guide</h2>
              <button
                className="btn btn-sm"
                onClick={() => setShowConfigModal(false)}
                style={{ border: 'none', background: 'none', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '12px', color: '#475569', marginBottom: '14px' }}>
                Resonance utilizes official APIs and public business trade directories. Sensitive credentials must be configured in <code>.env</code> or via the Settings page. Credentials are never exposed in UI or API responses.
              </p>

              {configStatus && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {Object.entries(configStatus).map(([key, item]) => (
                    <div key={key} style={{ padding: '10px 12px', border: '1px solid #E2E8F0', borderRadius: '4px', background: '#FAFAFA' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, fontSize: '12.5px', color: '#0F172A' }}>{item.name}</span>
                        <span className={`badge ${item.configured ? 'badge-valid' : 'badge-warn'}`}>
                          {item.status}
                        </span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>{item.description}</div>
                      {item.required_credentials && item.required_credentials.length > 0 && (
                        <div style={{ fontSize: '11px', color: '#0F766E', marginTop: '4px', fontFamily: 'monospace' }}>
                          Env variables: {item.required_credentials.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <a href="/settings" className="btn btn-sm" style={{ marginRight: 'auto' }}>
                Open Settings
              </a>
              <button className="btn btn-sm btn-primary" onClick={() => setShowConfigModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
