import React, { useState, useEffect } from 'react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';
import {
  Send,
  Paperclip,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Building2,
  User,
  Users,
  Clock,
  ShieldAlert,
  ShieldCheck
} from 'lucide-react';

export default function SendCampaignPage({ onRefreshStats, stats }) {
  const [audience, setAudience] = useState('business');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [settings, setSettings] = useState(null);
  const [loadingSettings, setLoadingSettings] = useState(true);

  // Dispatch progress state
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Idle');
  const [campaignLogs, setCampaignLogs] = useState([]);
  const [sentCount, setSentCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [demoSuppressedCount, setDemoSuppressedCount] = useState(0);

  const fetchSettings = async () => {
    setLoadingSettings(true);
    try {
      const data = await api.getSettings();
      setSettings(data);
      if (!subject) setSubject(data.default_subject || '');
      if (!body) setBody(data.default_body || '');
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingSettings(false);
    }
  };

  const pollStatus = async () => {
    try {
      const res = await api.getCampaignStatus();
      setRunning(res.is_running);
      setProgress(res.progress);
      setStatusMessage(res.status_message);
      setSentCount(res.sent_count);
      setFailedCount(res.failed_count);
      setDemoSuppressedCount(res.demo_suppressed || 0);
      if (res.logs && res.logs.length > 0) {
        setCampaignLogs(res.logs);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSettings();
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
      onRefreshStats();
    }
    return () => clearInterval(interval);
  }, [running]);

  const insertVariable = (tag) => {
    setBody((prev) => prev + ` ${tag} `);
  };

  const handleLaunchCampaign = async () => {
    if (!settings?.gmail_email) {
      alert('Gmail is not configured yet. Please configure your Gmail email and App Password in the Settings tab before sending.');
      return;
    }

    const realEligible = stats?.real_leads_count || 0;
    if (realEligible === 0) {
      alert(
        'Notice: There are currently 0 real discovered leads in the database.\n\n' +
        'Existing sample contacts are flagged as Demo Data and strictly excluded from real email dispatch to protect your domain reputation. ' +
        'Please run an API Buyer Discovery pass first.'
      );
      return;
    }

    const confirmed = window.confirm(
      `Launch outreach campaign to the '${audience.toUpperCase()}' segment?\n\n` +
      `Safety Notice: Only real discovered contacts will be queued. Any demo contacts are automatically suppressed.`
    );
    if (!confirmed) return;

    setRunning(true);
    setProgress(5);
    setStatusMessage('Queuing verified recipients and authenticating SMTP session...');
    setCampaignLogs([]);

    try {
      await api.sendCampaign({
        audience,
        subject,
        body,
      });
      pollStatus();
    } catch (err) {
      alert('Campaign launch error: ' + err.message);
      setRunning(false);
    }
  };

  return (
    <div>
      {/* Demo Data Safety Banner */}
      <div className="notice-box" style={{ marginBottom: '16px' }}>
        <ShieldCheck size={16} color="#059669" />
        <div>
          <strong>Outreach Safety Guard Active:</strong> All {stats?.demo_leads_count || 0} sample/seeded records are strictly suppressed from live SMTP transmission. Only real discovered leads can receive campaign emails.
        </div>
      </div>

      {!settings?.gmail_email && (
        <div className="notice-box warning" style={{ marginBottom: '16px' }}>
          <ShieldAlert size={16} />
          <div>
            <strong>SMTP Credentials Unconfigured:</strong> Configure your Gmail App Password in the Settings tab to authorize live email dispatch.
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px' }}>
        {/* Left Column: Email Composer */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Outreach Message Composer</h2>
              <p className="panel-description">
                Personalized B2B export pitch with company presentation attachment
              </p>
            </div>
          </div>

          <div className="panel-body">
            {/* Target Audience Selector */}
            <div className="form-group">
              <label className="form-label">Target Audience Segment</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                <button
                  type="button"
                  className={`btn btn-sm ${audience === 'business' ? 'btn-primary' : ''}`}
                  onClick={() => setAudience('business')}
                  disabled={running}
                  style={{ justifyContent: 'center' }}
                >
                  <Building2 size={13} />
                  <span>Business ({stats?.business_contacts || 0})</span>
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${audience === 'individual' ? 'btn-primary' : ''}`}
                  onClick={() => setAudience('individual')}
                  disabled={running}
                  style={{ justifyContent: 'center' }}
                >
                  <User size={13} />
                  <span>Individual ({stats?.individual_contacts || 0})</span>
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${audience === 'all' ? 'btn-primary' : ''}`}
                  onClick={() => setAudience('all')}
                  disabled={running}
                  style={{ justifyContent: 'center' }}
                >
                  <Users size={13} />
                  <span>All Leads ({stats?.total_leads || 0})</span>
                </button>
              </div>
            </div>

            {/* Subject Line */}
            <div className="form-group">
              <label className="form-label">Email Subject Line</label>
              <input
                type="text"
                className="input"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                disabled={running}
              />
            </div>

            {/* Body */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                <label className="form-label" style={{ margin: 0 }}>Message Body</label>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => insertVariable('{{buyer_name}}')}
                    style={{ fontSize: '10.5px', padding: '2px 6px' }}
                    title="Insert buyer name"
                  >
                    + buyer_name
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => insertVariable('{{company_name}}')}
                    style={{ fontSize: '10.5px', padding: '2px 6px' }}
                    title="Insert company name"
                  >
                    + company_name
                  </button>
                </div>
              </div>
              <textarea
                className="textarea"
                rows={11}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                disabled={running}
                style={{ fontFamily: 'var(--font-sans)', fontSize: '12px', lineHeight: '1.6' }}
              />
            </div>

            {/* Presentation Attachment Card */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 12px',
                background: '#F8FAFC',
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                marginBottom: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Paperclip size={14} color="#0F766E" />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#0F172A' }}>
                    Resonance Export Catalog Presentation (PDF)
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748B' }}>
                    company_presentation.pdf • Standard Export Presentation • Verified B2B Specifications
                  </div>
                </div>
              </div>
              <span className="badge badge-valid">
                <CheckCircle2 size={11} style={{ marginRight: '3px' }} /> Attached
              </span>
            </div>

            {/* Dispatch Button */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', color: '#64748B' }}>
                Send delay: <strong>{settings?.send_delay_seconds || 5}s</strong> between emails
              </div>
              <button
                className="btn btn-primary"
                onClick={handleLaunchCampaign}
                disabled={running}
              >
                <Send size={13} />
                <span>{running ? 'Dispatching Campaign...' : 'Launch Campaign'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Live Campaign Status & Audit Feed */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Outreach Dispatch Monitor</h2>
              <p className="panel-description">
                Real-time delivery progress, SMTP retry passes, and deduplication
              </p>
            </div>
            {running && <span className="badge badge-valid">Live Run Active</span>}
          </div>

          <div className="panel-body">
            {/* Progress Bar & Current Status */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ fontWeight: 600, color: '#0F172A' }}>Delivery Queue:</span>
                <span style={{ color: '#0F766E', fontWeight: 600 }}>{progress}%</span>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>
                {statusMessage}
              </div>
            </div>

            {/* Quick Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '16px' }}>
              <div style={{ padding: '8px 10px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#64748B' }}>Delivered</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#166534' }}>{sentCount}</div>
              </div>
              <div style={{ padding: '8px 10px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#64748B' }}>Failed</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#991B1B' }}>{failedCount}</div>
              </div>
              <div style={{ padding: '8px 10px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#64748B' }}>Demo Excluded</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#0F766E' }}>
                  {demoSuppressedCount || stats?.demo_leads_count || 0}
                </div>
              </div>
            </div>

            {/* Real-time Log Stream */}
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
              DISPATCH EVENT LOG
            </div>
            <div
              style={{
                border: '1px solid #E2E8F0',
                borderRadius: '4px',
                background: '#F8FAFC',
                maxHeight: '260px',
                overflowY: 'auto',
                padding: '8px',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
              }}
            >
              {campaignLogs.length === 0 ? (
                <div style={{ color: '#94A3B8', textAlign: 'center', padding: '20px' }}>
                  No active send events in current session. Launch a campaign to see live SMTP events.
                </div>
              ) : (
                campaignLogs.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '4px 0',
                      borderBottom: '1px solid #EDF2F7',
                      color: item.status === 'sent' ? '#166534' : '#991B1B',
                    }}
                  >
                    <span>[{item.step}] {item.email}</span>
                    <span style={{ fontWeight: 600 }}>{item.status.toUpperCase()}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
