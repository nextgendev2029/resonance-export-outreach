import React, { useState, useEffect } from 'react';
import { api } from '../api';
import {
  Save,
  CheckCircle2,
  AlertCircle,
  Key,
  Mail,
  Sliders,
  FileText,
  ShieldCheck,
  RefreshCw,
  ShieldAlert,
  Plus,
  Trash2,
  Download,
  Info,
  Search,
  Globe,
  ExternalLink,
  Cpu,
  Layers,
  HelpCircle
} from 'lucide-react';

export default function SettingsPage({ onRefreshStats }) {
  const [formData, setFormData] = useState({
    gmail_email: '',
    gmail_app_password: '',
    monitoring_cc_email: '',
    search_keyword: 'Singing Bowls',
    daily_send_limit: 100,
    send_delay_seconds: 5,
    presentation_path: 'assets/company_presentation.pdf',
    gemini_api_key: '',
    gemini_model: 'gemini-3-flash-preview',
    classification_batch_size: 20,
    default_subject: '',
    default_body: '',
    // Phase 6 Discovery API Credentials
    google_api_key: '',
    google_cse_id: '',
    facebook_access_token: '',
    linkedin_access_token: '',
    // Phase 5 Controlled Dispatch Settings
    dry_run: true,
    max_emails_per_day: 100,
    max_emails_per_campaign: 50,
    max_emails_per_run: 25,
    min_delay_seconds: 3,
    max_delay_seconds: 8,
    max_retries: 2,
    test_recipient_email: '',
  });

  const [maskedPassword, setMaskedPassword] = useState('');
  const [maskedApiKey, setMaskedApiKey] = useState('');
  const [maskedGoogleApiKey, setMaskedGoogleApiKey] = useState('');
  const [maskedGoogleCseId, setMaskedGoogleCseId] = useState('');
  const [maskedFbToken, setMaskedFbToken] = useState('');
  const [maskedLiToken, setMaskedLiToken] = useState('');
  const [configStatus, setConfigStatus] = useState(null);
  const [presentationExists, setPresentationExists] = useState(false);
  const [safetyProtections, setSafetyProtections] = useState([]);
  const [suppressions, setSuppressions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // New suppression form state
  const [newSuppEmail, setNewSuppEmail] = useState('');
  const [newSuppReason, setNewSuppReason] = useState('manual_suppression');
  const [newSuppNote, setNewSuppNote] = useState('');
  const [suppAdding, setSuppAdding] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const [data, suppList, cfgStatus] = await Promise.all([
        api.getSettings(),
        api.getSuppressions(),
        api.getDiscoveryConfigStatus().catch(() => null)
      ]);
      setFormData({
        gmail_email: data.gmail_email || '',
        gmail_app_password: '', // Never populate raw password
        monitoring_cc_email: data.monitoring_cc_email || '',
        search_keyword: data.search_keyword || 'Singing Bowls',
        daily_send_limit: data.daily_send_limit || 100,
        send_delay_seconds: data.send_delay_seconds || 5,
        presentation_path: data.presentation_path || 'assets/company_presentation.pdf',
        gemini_api_key: '', // Never populate raw key
        gemini_model: data.gemini_model || 'gemini-3-flash-preview',
        classification_batch_size: data.classification_batch_size || 20,
        default_subject: data.default_subject || '',
        default_body: data.default_body || '',
        google_api_key: '',
        google_cse_id: '',
        facebook_access_token: '',
        linkedin_access_token: '',
        dry_run: data.dry_run !== undefined ? data.dry_run : true,
        max_emails_per_day: data.max_emails_per_day || 100,
        max_emails_per_campaign: data.max_emails_per_campaign || 50,
        max_emails_per_run: data.max_emails_per_run || 25,
        min_delay_seconds: data.min_delay_seconds || 3,
        max_delay_seconds: data.max_delay_seconds || 8,
        max_retries: data.max_retries || 2,
        test_recipient_email: data.test_recipient_email || '',
      });
      setMaskedPassword(data.gmail_app_password_masked || '');
      setMaskedApiKey(data.gemini_api_key_masked || '');
      setMaskedGoogleApiKey(data.google_api_key_masked || '');
      setMaskedGoogleCseId(data.google_cse_id_masked || '');
      setMaskedFbToken(data.facebook_access_token_masked || '');
      setMaskedLiToken(data.linkedin_access_token_masked || '');
      setConfigStatus(cfgStatus);
      setPresentationExists(data.presentation_exists || false);
      setSafetyProtections(data.safety_protections || []);
      setSuppressions(suppList || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    try {
      await api.updateSettings(formData);
      setSaveSuccess(true);
      fetchSettings();
      if (onRefreshStats) onRefreshStats();
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err) {
      alert('Save failed: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAddSuppression = async (e) => {
    e.preventDefault();
    if (!newSuppEmail || !newSuppEmail.includes('@')) {
      alert('Please enter a valid email address.');
    }
    setSuppAdding(true);
    try {
      await api.addSuppression({
        email: newSuppEmail,
        reason: newSuppReason,
        operator_note: newSuppNote
      });
      setNewSuppEmail('');
      setNewSuppNote('');
      const updated = await api.getSuppressions();
      setSuppressions(updated);
    } catch (err) {
      alert('Failed to suppress: ' + err.message);
    } finally {
      setSuppAdding(false);
    }
  };

  const handleRemoveSuppression = async (email) => {
    if (!window.confirm(`Remove '${email}' from the suppression list?`)) return;
    try {
      await api.removeSuppression(email);
      const updated = await api.getSuppressions();
      setSuppressions(updated);
    } catch (err) {
      alert('Failed to remove: ' + err.message);
    }
  };

  return (
    <div>
      <form onSubmit={handleSave}>
        {/* Dry Run Banner */}
        {formData.dry_run && (
          <div style={{ background: '#FEF3C7', border: '1px solid #F59E0B', color: '#92400E', padding: '12px 16px', borderRadius: 6, marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600 }}>
              <ShieldAlert size={18} />
              <span>DRY RUN - No emails will be sent. Full pipeline simulation active.</span>
            </div>
            <span style={{ fontSize: 12, background: '#FDE68A', padding: '2px 8px', borderRadius: 4, fontWeight: 500 }}>
              Zero-Risk Mode
            </span>
          </div>
        )}

        {/* Save Bar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            background: 'var(--surface-color)',
            padding: '14px 20px',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
          }}
        >
          <div>
            <h2 style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-primary)' }}>
              Operational Configuration & Credentials
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Configure Buyer Discovery APIs, Gemini AI intelligence, Gmail SMTP dispatch, and safety policies.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {saveSuccess && (
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  color: 'var(--color-success)',
                  fontSize: '13px',
                  fontWeight: '500',
                }}
              >
                <CheckCircle2 size={15} /> Saved successfully
              </span>
            )}
            <button type="submit" className="btn btn-primary" disabled={saving || loading}>
              <Save size={14} />
              <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </div>
        </div>

        {/* Section: Live Integration Status Matrix */}
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Service & API Integration Status</h3>
              <p className="panel-description">
                Real-time configuration matrix across AI intelligence, buyer discovery sources, and outbound dispatch
              </p>
            </div>
            <Layers size={16} color="var(--brand-forest)" />
          </div>
          <div className="panel-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              {/* AI Group */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6, padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 10 }}>
                  <Cpu size={13} />
                  <span>AI Intelligence</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>Google Gemini AI</span>
                  <span className={`badge ${configStatus?.gemini_api?.configured ? 'badge-valid' : 'badge-neutral'}`} style={{ fontSize: 10 }}>
                    {configStatus?.gemini_api?.status || (configStatus?.gemini_api?.configured ? 'Ready' : 'Not Configured')}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, marginTop: 6 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Model:</span>
                  <span style={{ fontWeight: 600, color: 'var(--brand-forest)' }}>
                    {configStatus?.gemini_api?.model_display || 'Gemini 3 Flash'}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#64748B', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                  {configStatus?.gemini_api?.model || 'gemini-3-flash-preview'}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
                  Powers AI classification, evidence auditing, and personalized drafting.
                </div>
              </div>

              {/* Discovery Group */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6, padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 10 }}>
                  <Search size={13} />
                  <span>Discovery Sources</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <span style={{ fontSize: 12 }}>Google Search API</span>
                  <span className={`badge ${configStatus?.google_search?.configured ? 'badge-valid' : 'badge-neutral'}`} style={{ fontSize: 10 }}>
                    {configStatus?.google_search?.configured ? 'Configured' : 'Not Configured'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <span style={{ fontSize: 12 }}>US B2B Trade Directory</span>
                  <span className="badge badge-valid" style={{ fontSize: 10 }}>
                    Configured (Built-in)
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <span style={{ fontSize: 12 }}>Company Website Crawler</span>
                  <span className="badge badge-valid" style={{ fontSize: 10 }}>
                    Configured (Built-in)
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <span style={{ fontSize: 12 }}>Meta Graph API</span>
                  <span className={`badge ${configStatus?.facebook_api?.configured ? 'badge-valid' : 'badge-neutral'}`} style={{ fontSize: 10 }}>
                    {configStatus?.facebook_api?.configured ? 'Configured' : 'Not Configured'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                  <span style={{ fontSize: 12 }}>LinkedIn Org API</span>
                  <span className={`badge ${configStatus?.linkedin_api?.configured ? 'badge-valid' : 'badge-neutral'}`} style={{ fontSize: 10 }}>
                    {configStatus?.linkedin_api?.configured ? 'Configured' : 'Not Configured'}
                  </span>
                </div>
              </div>

              {/* Outreach Group */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6, padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 10 }}>
                  <Mail size={13} />
                  <span>Outreach Dispatch</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #E2E8F0' }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>Gmail SMTP</span>
                  <span className={`badge ${configStatus?.gmail_smtp?.configured ? 'badge-valid' : 'badge-neutral'}`} style={{ fontSize: 10 }}>
                    {configStatus?.gmail_smtp?.configured ? 'Configured' : 'Not Configured'}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 8 }}>
                  Controlled outbound email delivery via authenticated Google App Passwords.
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Section 1: Buyer Discovery API Integrations (Phase 6) */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Buyer Discovery API Integrations</h3>
                <p className="panel-description">
                  Official search and platform credentials for finding verified US home decor commercial buyers
                </p>
              </div>
              <Search size={16} color="var(--brand-forest)" />
            </div>
            <div className="panel-body">
              {/* Google Custom Search Credentials */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: 16 }}>
                <div className="form-group">
                  <label className="form-label">Google Custom Search API Key (GOOGLE_API_KEY)</label>
                  <input
                    type="password"
                    name="google_api_key"
                    className="input"
                    value={formData.google_api_key}
                    onChange={handleChange}
                    placeholder={maskedGoogleApiKey ? `Current: ${maskedGoogleApiKey} (Leave blank to keep)` : 'AIzaSy...'}
                  />
                  <div className="form-hint">Obtained from Google Cloud Console → APIs & Services → Credentials.</div>
                </div>

                <div className="form-group">
                  <label className="form-label">Google Search Engine ID (GOOGLE_CSE_ID)</label>
                  <input
                    type="text"
                    name="google_cse_id"
                    className="input"
                    value={formData.google_cse_id}
                    onChange={handleChange}
                    placeholder={maskedGoogleCseId ? `Current: ${maskedGoogleCseId} (Leave blank to keep)` : 'e.g. 017576662512468239146:omuauf_lfve'}
                  />
                  <div className="form-hint">From Google Programmable Search Engine with Region set to United States.</div>
                </div>
              </div>

              {/* Instructions Callout */}
              <div style={{ background: '#F0FDFA', border: '1px solid #CCFBF1', borderRadius: 6, padding: '12px 14px', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: 12, color: '#0F766E', marginBottom: 4 }}>
                  <HelpCircle size={14} />
                  <span>How Google Search Discovery Works</span>
                </div>
                <div style={{ fontSize: 12, color: '#134E4A', lineHeight: 1.5 }}>
                  Resonance queries the Google Custom Search REST API with US geographic targeting (<code>gl=us, cr=countryUS</code>).
                  When unconfigured, the engine seamlessly uses built-in US B2B Trade Directories and Website Crawlers, ensuring zero interruption to operator discovery workflows.
                </div>
              </div>

              {/* Optional Meta & LinkedIn tokens */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Meta Graph API Token (FACEBOOK_ACCESS_TOKEN - Optional)</label>
                  <input
                    type="password"
                    name="facebook_access_token"
                    className="input"
                    value={formData.facebook_access_token}
                    onChange={handleChange}
                    placeholder={maskedFbToken ? `Current: ${maskedFbToken} (Leave blank to keep)` : 'EAAB... (Requires Pages Search API approval)'}
                  />
                  <div className="form-hint">Only required if using official Meta Graph API developer endpoints.</div>
                </div>

                <div className="form-group">
                  <label className="form-label">LinkedIn Organization Token (LINKEDIN_ACCESS_TOKEN - Optional)</label>
                  <input
                    type="password"
                    name="linkedin_access_token"
                    className="input"
                    value={formData.linkedin_access_token}
                    onChange={handleChange}
                    placeholder={maskedLiToken ? `Current: ${maskedLiToken} (Leave blank to keep)` : 'AQV... (Requires LinkedIn Developer approval)'}
                  />
                  <div className="form-hint">Only required if using official LinkedIn Organization Search API.</div>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Gmail Authentication */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Gmail Outreach Credentials</h3>
                <p className="panel-description">
                  Authenticated sender identity using standard Google App Passwords
                </p>
              </div>
              <Mail size={16} color="#64748B" />
            </div>
            <div className="panel-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Gmail Sender Address</label>
                  <input
                    type="email"
                    name="gmail_email"
                    className="input"
                    value={formData.gmail_email}
                    onChange={handleChange}
                    placeholder="e.g. export@yourbusiness.com"
                  />
                  <div className="form-hint">Address used as 'From' in outbound outreach messages.</div>
                </div>

                <div className="form-group">
                  <label className="form-label">Gmail App Password</label>
                  <input
                    type="password"
                    name="gmail_app_password"
                    className="input"
                    value={formData.gmail_app_password}
                    onChange={handleChange}
                    placeholder={maskedPassword ? `Current: ${maskedPassword} (Leave blank to keep)` : '16-character app password'}
                  />
                  <div className="form-hint">
                    Never shared or logged. Created via Google Account → Security → App Passwords.
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Monitoring CC Address (Optional)</label>
                <input
                  type="email"
                  name="monitoring_cc_email"
                  className="input"
                  value={formData.monitoring_cc_email}
                  onChange={handleChange}
                  placeholder="e.g. audit@yourcompany.com"
                />
                <div className="form-hint">Copies all sent messages to an internal monitoring inbox.</div>
              </div>
            </div>
          </div>

          {/* Section 3: Phase 5 Controlled Dispatch Engine Settings */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Controlled Dispatch Engine & Limits</h3>
                <p className="panel-description">
                  Operational rate bounds, polite pacing delays, and test dispatch target
                </p>
              </div>
              <Sliders size={16} color="#64748B" />
            </div>
            <div className="panel-body">
              {/* Dry Run Toggle */}
              <div style={{ padding: '12px 16px', background: formData.dry_run ? '#FEF3C7' : '#F8FAFC', border: `1px solid ${formData.dry_run ? '#F59E0B' : '#E2E8F0'}`, borderRadius: 6, marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, color: formData.dry_run ? '#92400E' : 'inherit' }}>
                    Dry Run Mode (Zero-Risk Simulation)
                  </div>
                  <div style={{ fontSize: 12, color: formData.dry_run ? '#B45309' : 'var(--text-secondary)' }}>
                    When enabled, the entire dispatch engine operates identically but does not connect to Gmail SMTP.
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    name="dry_run"
                    checked={formData.dry_run}
                    onChange={handleChange}
                    style={{ width: 18, height: 18, cursor: 'pointer' }}
                  />
                  <span style={{ fontWeight: 600, fontSize: 13 }}>Enabled</span>
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: 16 }}>
                <div className="form-group">
                  <label className="form-label">Max Emails Per Day</label>
                  <input
                    type="number"
                    name="max_emails_per_day"
                    className="input"
                    value={formData.max_emails_per_day}
                    onChange={handleChange}
                    min={1}
                    max={500}
                  />
                  <div className="form-hint">Daily system quota.</div>
                </div>

                <div className="form-group">
                  <label className="form-label">Max Emails Per Campaign</label>
                  <input
                    type="number"
                    name="max_emails_per_campaign"
                    className="input"
                    value={formData.max_emails_per_campaign}
                    onChange={handleChange}
                    min={1}
                    max={200}
                  />
                  <div className="form-hint">Campaign ceiling.</div>
                </div>

                <div className="form-group">
                  <label className="form-label">Max Batch Per Run</label>
                  <input
                    type="number"
                    name="max_emails_per_run"
                    className="input"
                    value={formData.max_emails_per_run}
                    onChange={handleChange}
                    min={1}
                    max={100}
                  />
                  <div className="form-hint">Batch limit per confirmation.</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: 16 }}>
                <div className="form-group">
                  <label className="form-label">Min Delay (Seconds)</label>
                  <input
                    type="number"
                    name="min_delay_seconds"
                    className="input"
                    value={formData.min_delay_seconds}
                    onChange={handleChange}
                    min={1}
                    max={30}
                  />
                  <div className="form-hint">Minimum bounded delay.</div>
                </div>

                <div className="form-group">
                  <label className="form-label">Max Delay (Seconds)</label>
                  <input
                    type="number"
                    name="max_delay_seconds"
                    className="input"
                    value={formData.max_delay_seconds}
                    onChange={handleChange}
                    min={1}
                    max={60}
                  />
                  <div className="form-hint">Maximum randomized delay.</div>
                </div>

                <div className="form-group">
                  <label className="form-label">Max Retries</label>
                  <input
                    type="number"
                    name="max_retries"
                    className="input"
                    value={formData.max_retries}
                    onChange={handleChange}
                    min={0}
                    max={5}
                  />
                  <div className="form-hint">For transient errors only.</div>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Designated Test Recipient Email</label>
                <input
                  type="email"
                  name="test_recipient_email"
                  className="input"
                  value={formData.test_recipient_email}
                  onChange={handleChange}
                  placeholder="e.g. operator@resonance.org"
                />
                <div className="form-hint">Pre-filled destination when performing controlled test sends.</div>
              </div>
            </div>
          </div>

          {/* Section 4: Operational Safety Checklist (Non-bypassable protections) */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Active Operational Safety Guardrails</h3>
                <p className="panel-description">
                  Individual hard boundaries preventing accidental or non-compliant email transmission
                </p>
              </div>
              <ShieldCheck size={16} color="var(--brand-forest)" />
            </div>
            <div className="panel-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
                {safetyProtections.map((p, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6 }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.description}</div>
                    </div>
                    <span className="status-badge valid">{p.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Section 5: AI Configuration */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Gemini AI Lead Intelligence</h3>
                <p className="panel-description">
                  Model parameters for AI enrichment, intent classification, and evidence extraction
                </p>
              </div>
              <Key size={16} color="#64748B" />
            </div>
            <div className="panel-body">
              <div className="form-group">
                <label className="form-label">Gemini API Key (GEMINI_API_KEY)</label>
                <input
                  type="password"
                  name="gemini_api_key"
                  className="input"
                  value={formData.gemini_api_key}
                  onChange={handleChange}
                  placeholder={maskedApiKey ? `Current: ${maskedApiKey} (Leave blank to keep)` : 'AIzaSy...'}
                />
                <div className="form-hint">
                  If left unset, the system uses the deterministic domain & business role heuristic classifier.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <label className="form-label" style={{ margin: 0 }}>Gemini Model</label>
                    <span style={{ fontSize: 11, color: 'var(--brand-forest)', fontWeight: 600 }}>
                      Gemini 3 Flash
                    </span>
                  </div>
                  <select
                    name="gemini_model"
                    className="select"
                    value={formData.gemini_model}
                    onChange={handleChange}
                  >
                    <option value="gemini-3-flash-preview">Gemini 3 Flash (gemini-3-flash-preview) - Intended Active</option>
                  </select>
                  <div className="form-hint" style={{ marginTop: 4 }}>
                    Technical API Model ID: <code>gemini-3-flash-preview</code>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Classification Batch Size</label>
                  <input
                    type="number"
                    name="classification_batch_size"
                    className="input"
                    value={formData.classification_batch_size}
                    onChange={handleChange}
                    min={5}
                    max={100}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 6: Company Presentation Asset Verification */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Resonance Export Catalog Presentation (PDF)</h3>
                <p className="panel-description">
                  Verified PDF export brochure and specifications attached to B2B outbound campaigns
                </p>
              </div>
              <FileText size={16} color="#64748B" />
            </div>
            <div className="panel-body">
              <div className="form-group">
                <label className="form-label">Presentation File Path</label>
                <input
                  type="text"
                  name="presentation_path"
                  className="input"
                  value={formData.presentation_path}
                  onChange={handleChange}
                />
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {presentationExists ? (
                    <span className="badge badge-valid">
                      <CheckCircle2 size={12} style={{ marginRight: '4px' }} /> Verified PDF File Available
                    </span>
                  ) : (
                    <span className="badge badge-error">
                      <AlertCircle size={12} style={{ marginRight: '4px' }} /> File Not Found at Path
                    </span>
                  )}
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    Export campaigns cannot dispatch without a verified PDF presentation.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </form>

      {/* Section 7: Persistent Suppression List Management */}
      <div className="panel" style={{ marginTop: 24 }}>
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="panel-title">Contact Suppression List</h3>
            <p className="panel-description">
              Recipients on this list are permanently excluded from all outbound campaigns.
            </p>
          </div>
          <a href="/download-suppression-list" className="btn btn-sm btn-secondary">
            <Download size={13} />
            <span>Export CSV</span>
          </a>
        </div>
        <div className="panel-body">
          {/* Add Suppression Form */}
          <form onSubmit={handleAddSuppression} style={{ display: 'flex', gap: 10, alignItems: 'flex-end', marginBottom: 20, flexWrap: 'wrap' }}>
            <div style={{ flex: 2, minWidth: 200 }}>
              <label className="drawer-label" style={{ fontSize: 11 }}>Email Address</label>
              <input
                type="email"
                className="input input-sm"
                placeholder="contact@company.com"
                value={newSuppEmail}
                onChange={(e) => setNewSuppEmail(e.target.value)}
                required
              />
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <label className="drawer-label" style={{ fontSize: 11 }}>Reason</label>
              <select
                className="select select-sm"
                value={newSuppReason}
                onChange={(e) => setNewSuppReason(e.target.value)}
              >
                <option value="unsubscribe">unsubscribe</option>
                <option value="manual_suppression">manual_suppression</option>
                <option value="bounce">bounce</option>
                <option value="complaint">complaint</option>
                <option value="invalid_contact">invalid_contact</option>
                <option value="operator_block">operator_block</option>
              </select>
            </div>
            <div style={{ flex: 2, minWidth: 180 }}>
              <label className="drawer-label" style={{ fontSize: 11 }}>Operator Note</label>
              <input
                type="text"
                className="input input-sm"
                placeholder="e.g. Opted out via website"
                value={newSuppNote}
                onChange={(e) => setNewSuppNote(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-sm btn-primary" disabled={suppAdding}>
              <Plus size={13} />
              <span>{suppAdding ? 'Adding...' : 'Suppress Contact'}</span>
            </button>
          </form>

          {/* Suppression Records Table */}
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Reason</th>
                  <th>Notes</th>
                  <th>Suppressed Date</th>
                  <th style={{ width: 80 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {suppressions.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '24px 16px', color: 'var(--text-secondary)' }}>
                      No suppressed contacts recorded.
                    </td>
                  </tr>
                ) : (
                  suppressions.map((s, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 500 }}>{s.email}</td>
                      <td>
                        <span className="badge" style={{ fontSize: 11, textTransform: 'capitalize' }}>
                          {s.reason}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        {s.operator_note || s.notes || '-'}
                      </td>
                      <td style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td>
                        <button
                          className="btn btn-xs btn-outline-danger"
                          onClick={() => handleRemoveSuppression(s.email)}
                          title="Remove from suppression list"
                        >
                          <Trash2 size={11} />
                          <span>Remove</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
