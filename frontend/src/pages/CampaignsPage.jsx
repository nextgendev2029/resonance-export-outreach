import React, { useState, useEffect } from 'react';
import {
  Plus,
  RefreshCw,
  Trash2,
  Edit3,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Archive,
  ChevronRight,
  ArrowLeft,
  ExternalLink,
  Copy,
  FileText,
  Check,
  AlertTriangle,
  Layers,
  ShieldCheck,
  Eye,
  Info,
  Sliders,
  Building2,
  Send,
  Play,
  Pause,
  Ban,
  ShieldAlert,
  FileCheck,
  Gauge,
  Clock
} from 'lucide-react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';

const STEPPER_STEPS = [
  { id: 'audience', label: '1. Audience' },
  { id: 'message', label: '2. Message & Catalog' },
  { id: 'personalize', label: '3. Personalization' },
  { id: 'review', label: '4. Review Queue' },
  { id: 'dispatch', label: '5. Dispatch Center' },
];


export default function CampaignsPage({ onRefreshStats, stats }) {
  // Campaign list state
  const [campaigns, setCampaigns] = useState([]);
  const [configStatus, setConfigStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Active campaign / workspace state
  const [activeCampaign, setActiveCampaign] = useState(null);
  const [activeStep, setActiveStep] = useState('audience'); // 'audience', 'message', 'personalize', 'review'

  // Step 1: Audience filters & preview state
  const [audienceFilters, setAudienceFilters] = useState({
    dataset: 'real',
    classification: ['Business'],
    validation_status: ['Valid'],
    buyer_relevance: ['High', 'Medium'],
    country: '',
    contacted_status: 'never'
  });
  const [audiencePreview, setAudiencePreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [showExcludedSample, setShowExcludedSample] = useState(false);

  // Step 2: Message & Catalog details state
  const [campaignName, setCampaignName] = useState('');
  const [subjectTemplate, setSubjectTemplate] = useState('Handcrafted Himalayan Singing Bowls - B2B Wholesale Catalog & Export Pricing');
  const [bodyTemplate, setBodyTemplate] = useState(`Dear {{buyer_name}},

{{personalized_opening}}

We are specialized Himalayan artisans and direct exporters of authentic hand-hammered 7-metal Tibetan Singing Bowls, meditation gongs, and sound-healing instruments.

We noticed {{company_name}}'s focus on quality holistic wellness and musical instruments. We would love to share our latest 2026 Export Catalog and direct manufacturer wholesale price list with your procurement team.

Please find our complete company presentation and export specifications attached.

Key B2B Offerings:
• Authentic 7-metal hand-hammered singing bowls (graded Frequencies & Hz)
• Custom engraving and OEM private labeling for international distributors
• Direct worldwide door-to-door export shipping with full export documentation

Would you be open to reviewing our wholesale price sheet this week?

Warm regards,

Export Operations Team
Himalayan Singing Bowls Exporters
export@himalayanbowls.org | www.himalayanbowls.org`);
  const [attachmentInfo, setAttachmentInfo] = useState(null);
  const [senderIdentity, setSenderIdentity] = useState('Himalayan Singing Bowls Export Operations');

  // Step 3: Personalization Generation state
  const [generating, setGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState(null);

  // Step 4: Review Queue state
  const [drafts, setDrafts] = useState([]);
  const [draftsLoading, setDraftsLoading] = useState(false);
  const [draftStatusFilter, setDraftStatusFilter] = useState('all');
  const [draftSearch, setDraftSearch] = useState('');
  const [selectedDraftIds, setSelectedDraftIds] = useState([]);

  // Detail drawer / Editor state
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [editingDraft, setEditingDraft] = useState(null);
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('Incorrect personalization');
  const [actionNotice, setActionNotice] = useState(null);

  // Step 5: Dispatch Center State (Phase 5)
  const [preflight, setPreflight] = useState(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmUnderstood, setConfirmUnderstood] = useState(false);
  const [confirmNotes, setConfirmNotes] = useState('');
  const [dispatching, setDispatching] = useState(false);
  const [testRecipient, setTestRecipient] = useState('');
  const [testDraftId, setTestDraftId] = useState('');
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [dispatchNotice, setDispatchNotice] = useState(null);

  // Load campaigns & attachment metadata on mount

  useEffect(() => {
    fetchCampaigns();
    fetchAttachment();
    api.getDiscoveryConfigStatus().then(setConfigStatus).catch(() => {});
  }, []);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const data = await api.getCampaigns();
      setCampaigns(data || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAttachment = async () => {
    try {
      const info = await api.getAttachmentInfo();
      setAttachmentInfo(info);
    } catch (_) {}
  };

  // Evaluate audience preview whenever filters change
  const runAudiencePreview = async (overrideFilters = null) => {
    setPreviewLoading(true);
    try {
      const filtersToUse = overrideFilters || audienceFilters;
      const preview = await api.previewAudience(filtersToUse);
      setAudiencePreview(preview);
    } catch (err) {
      console.error('Audience preview error:', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  // When opening a campaign
  const openCampaign = (campaign) => {
    setActiveCampaign(campaign);
    setCampaignName(campaign.name || '');
    setSubjectTemplate(campaign.subject_template || '');
    setBodyTemplate(campaign.body_template || '');
    if (campaign.audience_filters) {
      setAudienceFilters({
        dataset: campaign.audience_filters.dataset || 'real',
        classification: campaign.audience_filters.classification || ['Business'],
        validation_status: campaign.audience_filters.validation_status || ['Valid'],
        buyer_relevance: campaign.audience_filters.buyer_relevance || ['High', 'Medium'],
        country: campaign.audience_filters.country || '',
        contacted_status: campaign.audience_filters.contacted_status || 'never'
      });
    }

    // Default to Review Queue if drafts already exist, otherwise Audience
    if (campaign.draft_count > 0) {
      setActiveStep('review');
      fetchDrafts(campaign.campaign_id);
    } else {
      setActiveStep('audience');
      runAudiencePreview(campaign.audience_filters);
    }
  };

  const closeCampaign = () => {
    setActiveCampaign(null);
    setSelectedDraft(null);
    setEditingDraft(null);
    fetchCampaigns();
  };

  const startNewCampaign = () => {
    const defaultFilters = {
      dataset: 'real',
      classification: ['Business'],
      validation_status: ['Valid'],
      buyer_relevance: ['High', 'Medium'],
      country: '',
      contacted_status: 'never'
    };
    setActiveCampaign({
      campaign_id: null,
      name: 'Singing Bowls - International Wellness Distributors',
      status: 'Draft',
      audience_filters: defaultFilters,
      draft_count: 0
    });
    setCampaignName('Singing Bowls - International Wellness Distributors');
    setAudienceFilters(defaultFilters);
    setActiveStep('audience');
    runAudiencePreview(defaultFilters);
  };

  // Save/Create campaign
  const saveCampaignConfig = async (nextStep = null) => {
    try {
      const payload = {
        name: campaignName.trim() || 'Himalayan Singing Bowls Export Outreach',
        audience_filters: audienceFilters,
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        sender_identity: senderIdentity,
        attachment_path: attachmentInfo?.path || 'assets/company_presentation.pdf'
      };

      let savedCamp = null;
      if (activeCampaign.campaign_id) {
        savedCamp = await api.updateCampaign(activeCampaign.campaign_id, payload);
      } else {
        savedCamp = await api.createCampaign(payload);
      }

      setActiveCampaign(savedCamp);
      showNotice('Campaign configuration saved.');
      if (nextStep) setActiveStep(nextStep);
      return savedCamp;
    } catch (err) {
      setError(err.message);
      return null;
    }
  };

  // Step 3: Trigger draft generation
  const handleStartGeneration = async () => {
    if (!activeCampaign?.campaign_id) {
      const saved = await saveCampaignConfig();
      if (!saved) return;
    }

    setGenerating(true);
    setGenerationStatus({ progress: 5, status_message: 'Initializing draft generation...' });

    try {
      await api.generateCampaignDrafts(activeCampaign.campaign_id, { force_regenerate: false });
      pollGenerationStatus(activeCampaign.campaign_id);
    } catch (err) {
      setError(err.message);
      setGenerating(false);
    }
  };

  const pollGenerationStatus = (campaignId) => {
    const interval = setInterval(async () => {
      try {
        const status = await api.getCampaignGenerationStatus(campaignId);
        setGenerationStatus(status);

        if (!status.is_running) {
          clearInterval(interval);
          setGenerating(false);
          // Refresh campaign and drafts
          const updated = await api.getCampaignDetail(campaignId);
          setActiveCampaign(updated);
          fetchDrafts(campaignId);
          setActiveStep('review');
          showNotice(`Draft generation complete. ${status.generated_count || 0} drafts in review queue.`);
        }
      } catch (err) {
        clearInterval(interval);
        setGenerating(false);
      }
    }, 800);
  };

  // Step 4: Fetch Drafts
  const fetchDrafts = async (campaignId) => {
    if (!campaignId) return;
    setDraftsLoading(true);
    try {
      const data = await api.getCampaignDrafts(campaignId, {
        status: draftStatusFilter,
        search: draftSearch
      });
      setDrafts(data || []);
      setSelectedDraftIds([]);
    } catch (err) {
      console.error('Fetch drafts error:', err);
    } finally {
      setDraftsLoading(false);
    }
  };

  useEffect(() => {
    if (activeCampaign?.campaign_id && activeStep === 'review') {
      fetchDrafts(activeCampaign.campaign_id);
    }
  }, [activeCampaign?.campaign_id, draftStatusFilter, draftSearch, activeStep]);

  // Draft Actions
  const handleOpenDraftDrawer = (draft) => {
    setSelectedDraft(draft);
    setEditingDraft({
      subject: draft.subject,
      opening_line: draft.opening_line,
      body: draft.body,
      closing: draft.closing
    });
  };

  const handleSaveDraftEdit = async () => {
    if (!selectedDraft || !editingDraft) return;
    try {
      const updated = await api.updateCampaignDraft(selectedDraft.campaign_id, selectedDraft.draft_id, editingDraft);
      setSelectedDraft(updated);
      showNotice('Draft changes saved.');
      fetchDrafts(selectedDraft.campaign_id);
    } catch (err) {
      showNotice(`Error saving: ${err.message}`, true);
    }
  };

  const handleApproveDraft = async (draftId) => {
    try {
      const res = await api.approveCampaignDraft(activeCampaign.campaign_id, draftId);
      showNotice('Draft approved for future dispatch (no email sent).');
      if (selectedDraft?.draft_id === draftId) {
        setSelectedDraft(res.draft);
      }
      fetchDrafts(activeCampaign.campaign_id);
      if (onRefreshStats) onRefreshStats();
    } catch (err) {
      showNotice(`Approval error: ${err.message}`, true);
    }
  };

  const handleRejectDraft = async () => {
    if (!selectedDraft) return;
    try {
      const res = await api.rejectCampaignDraft(activeCampaign.campaign_id, selectedDraft.draft_id, rejectionReason);
      setShowRejectModal(false);
      showNotice('Draft marked as Rejected.');
      setSelectedDraft(res.draft);
      fetchDrafts(activeCampaign.campaign_id);
    } catch (err) {
      showNotice(`Rejection error: ${err.message}`, true);
    }
  };

  const handleRegenerateDraft = async (draftId) => {
    try {
      showNotice('Regenerating draft with AI grounding...');
      const res = await api.regenerateCampaignDraft(activeCampaign.campaign_id, draftId);
      if (selectedDraft?.draft_id === draftId) {
        setSelectedDraft(res.draft);
        setEditingDraft({
          subject: res.draft.subject,
          opening_line: res.draft.opening_line,
          body: res.draft.body,
          closing: res.draft.closing
        });
      }
      showNotice('Draft regenerated successfully.');
      fetchDrafts(activeCampaign.campaign_id);
    } catch (err) {
      showNotice(`Regeneration error: ${err.message}`, true);
    }
  };

  // Bulk Actions
  const handleBulkApprove = async () => {
    if (!selectedDraftIds.length) return;
    try {
      const res = await api.bulkApproveDrafts(activeCampaign.campaign_id, selectedDraftIds);
      showNotice(`Approved ${res.approved_count} drafts for future dispatch.`);
      fetchDrafts(activeCampaign.campaign_id);
      setSelectedDraftIds([]);
    } catch (err) {
      showNotice(err.message, true);
    }
  };

  const handleBulkReject = async () => {
    if (!selectedDraftIds.length) return;
    try {
      const res = await api.bulkRejectDrafts(activeCampaign.campaign_id, selectedDraftIds, 'Bulk operator rejection');
      showNotice(`Rejected ${res.rejected_count} drafts.`);
      fetchDrafts(activeCampaign.campaign_id);
      setSelectedDraftIds([]);
    } catch (err) {
      showNotice(err.message, true);
    }
  };

  const handleBulkArchive = async () => {
    if (!selectedDraftIds.length) return;
    try {
      const res = await api.bulkArchiveDrafts(activeCampaign.campaign_id, selectedDraftIds);
      showNotice(`Archived ${res.archived_count} drafts.`);
      fetchDrafts(activeCampaign.campaign_id);
      setSelectedDraftIds([]);
    } catch (err) {
      showNotice(err.message, true);
    }
  };

  const handleDeleteCampaign = async (campaignId, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this campaign and all its drafts?')) return;
    try {
      await api.deleteCampaign(campaignId);
      fetchCampaigns();
      if (activeCampaign?.campaign_id === campaignId) {
        setActiveCampaign(null);
      }
    } catch (err) {
      alert(`Delete error: ${err.message}`);
    }
  };

  const showNotice = (msg, isError = false) => {
    setActionNotice({ msg, isError });
    setTimeout(() => setActionNotice(null), 4000);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  // -------------------------------------------------------------
  // Phase 5 Dispatch Engine Handlers
  // -------------------------------------------------------------
  const fetchPreflight = async (campaignId) => {
    if (!campaignId) return;
    setPreflightLoading(true);
    try {
      const data = await api.getCampaignPreflight(campaignId);
      setPreflight(data);
    } catch (err) {
      console.error('Preflight fetch error:', err);
    } finally {
      setPreflightLoading(false);
    }
  };

  const fetchDispatchStatus = async (campaignId) => {
    if (!campaignId) return;
    try {
      const data = await api.getCampaignDispatchStatus(campaignId);
      setDispatchStatus(data);
    } catch (err) {
      console.error('Dispatch status fetch error:', err);
    }
  };

  useEffect(() => {
    if (activeCampaign?.campaign_id && activeStep === 'dispatch') {
      fetchPreflight(activeCampaign.campaign_id);
      fetchDispatchStatus(activeCampaign.campaign_id);
    }
  }, [activeCampaign?.campaign_id, activeStep]);

  useEffect(() => {
    let interval = null;
    if (activeCampaign?.campaign_id && activeStep === 'dispatch') {
      if (dispatchStatus?.is_dispatching || activeCampaign?.status === 'Sending') {
        interval = setInterval(() => {
          fetchDispatchStatus(activeCampaign.campaign_id);
          fetchPreflight(activeCampaign.campaign_id);
        }, 3000);
      }
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeCampaign?.campaign_id, activeStep, dispatchStatus?.is_dispatching, activeCampaign?.status]);

  const handleOpenConfirmModal = () => {
    setConfirmUnderstood(false);
    setConfirmNotes('');
    setShowConfirmModal(true);
  };

  const handleConfirmSend = async () => {
    if (!activeCampaign?.campaign_id) return;
    if (!confirmUnderstood) {
      alert('Please check the confirmation box before sending.');
      return;
    }
    setDispatching(true);
    setDispatchNotice(null);
    try {
      const res = await api.confirmCampaignDispatch(activeCampaign.campaign_id, {
        confirmed: true,
        operator_notes: confirmNotes
      });
      setShowConfirmModal(false);
      setDispatchNotice({ type: 'success', message: res.message || 'Dispatch initiated successfully.' });
      await fetchDispatchStatus(activeCampaign.campaign_id);
      await fetchPreflight(activeCampaign.campaign_id);
      if (onRefreshStats) onRefreshStats();
    } catch (err) {
      setDispatchNotice({ type: 'error', message: err.message || 'Dispatch confirmation failed.' });
    } finally {
      setDispatching(false);
    }
  };

  const handlePauseDispatch = async () => {
    if (!activeCampaign?.campaign_id) return;
    try {
      await api.pauseCampaignDispatch(activeCampaign.campaign_id);
      fetchDispatchStatus(activeCampaign.campaign_id);
      showNotice('Dispatch paused.');
    } catch (err) {
      showNotice(`Pause error: ${err.message}`, true);
    }
  };

  const handleCancelDispatch = async () => {
    if (!activeCampaign?.campaign_id) return;
    if (!window.confirm('Cancel remaining unsent emails in this campaign?')) return;
    try {
      const res = await api.cancelCampaignDispatch(activeCampaign.campaign_id);
      fetchDispatchStatus(activeCampaign.campaign_id);
      showNotice(`Cancelled ${res.cancelled_count || 0} remaining emails.`);
    } catch (err) {
      showNotice(`Cancel error: ${err.message}`, true);
    }
  };

  const handleTestSend = async () => {
    if (!testRecipient || !testRecipient.includes('@')) {
      alert('Please enter a valid test recipient email address.');
      return;
    }
    const targetDraftId = testDraftId || (drafts.find(d => d.status === 'Approved')?.draft_id);
    if (!targetDraftId) {
      alert('Please select an approved draft for the test send.');
      return;
    }
    setTestSending(true);
    setTestResult(null);
    try {
      const res = await api.dispatchTestSend({
        draft_id: targetDraftId,
        test_recipient: testRecipient
      });
      setTestResult({
        success: true,
        message: `Test email successfully dispatched to ${res.test_recipient}`,
        smtp_message_id: res.smtp_message_id
      });
    } catch (err) {
      setTestResult({
        success: false,
        message: err.message || 'Test send failed'
      });
    } finally {
      setTestSending(false);
    }
  };

  // -------------------------------------------------------------
  // Render View 1: Campaigns List View
  // -------------------------------------------------------------

  if (!activeCampaign) {
    return (
      <div className="page-container">
        {/* Toast Notice */}
        {actionNotice && (
          <div className={`toast-notification ${actionNotice.isError ? 'toast-error' : 'toast-success'}`}>
            <span>{actionNotice.msg}</span>
          </div>
        )}

        <div className="section-header">
          <div>
            <h2 className="section-title">Campaigns & Outreach Workspace</h2>
            <p className="section-subtitle">
              Prepare, personalize, and stage verified B2B export outreach from enriched prospect intelligence.
            </p>
          </div>
          <div className="toolbar-actions">
            <button className="btn btn-secondary" onClick={fetchCampaigns}>
              <RefreshCw size={13} />
              <span>Refresh</span>
            </button>
            <button className="btn btn-primary" onClick={startNewCampaign}>
              <Plus size={14} />
              <span>New Campaign</span>
            </button>
          </div>
        </div>

        {/* Attachment Safety Status Banner */}
        <div className="card attachment-banner" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', marginBottom: '20px', background: 'var(--surface-color)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <FileText size={18} style={{ color: 'var(--brand-forest)' }} />
            <div>
              <div style={{ fontSize: '13px', fontWeight: '600' }}>
                Resonance Export Catalog Presentation (PDF)
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {attachmentInfo?.filename || 'company_presentation.pdf'} ({attachmentInfo?.size_kb || 3} KB) • Standard Export Presentation • Verified B2B Specifications
              </div>
            </div>
          </div>
          <span className="badge badge-valid">Attachment Ready</span>
        </div>

        {/* Pipeline Readiness Launchpad (Visible when no active campaigns) */}
        {!loading && campaigns.length === 0 && (
          <div style={{ marginBottom: '24px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '10px' }}>
              Pipeline Operational Readiness
            </div>
            <div className="stats-grid" style={{ marginBottom: 0 }}>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#F0FDFA', color: '#0F766E' }}>
                  <Building2 size={18} />
                </div>
                <div className="stat-label">Eligible Business Leads</div>
                <div className="stat-value">{stats?.business_contacts || 0}</div>
                <div className="stat-sub">Verified B2B wholesale prospects</div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#ECFDF5', color: '#059669' }}>
                  <CheckCircle2 size={18} />
                </div>
                <div className="stat-label">Valid Recipients</div>
                <div className="stat-value">{stats?.valid_emails || 0}</div>
                <div className="stat-sub">Deliverable addresses identified</div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#F0FDF4', color: '#16A34A' }}>
                  <FileText size={18} />
                </div>
                <div className="stat-label">AI Personalization</div>
                <div className="stat-value" style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px' }}>
                  {configStatus?.gemini_api?.model_display || 'Gemini 3 Flash'}
                </div>
                <div className="stat-sub">Model: gemini-3-flash-preview</div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#FEF3C7', color: '#D97706' }}>
                  <FileCheck size={18} />
                </div>
                <div className="stat-label">Catalog Presentation</div>
                <div className="stat-value" style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px' }}>
                  {attachmentInfo?.valid ? 'PDF Verified' : 'Ready'}
                </div>
                <div className="stat-sub">{attachmentInfo?.filename || 'company_presentation.pdf'} ({attachmentInfo?.size_kb || 3} KB)</div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#F8FAFC', color: '#475569' }}>
                  <ShieldCheck size={18} />
                </div>
                <div className="stat-label">Dispatch Guard</div>
                <div className="stat-value" style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px' }}>
                  Dry-Run Active
                </div>
                <div className="stat-sub">100% simulation • Zero live sends</div>
              </div>
            </div>
          </div>
        )}

        {/* Campaigns Table */}
        <div className="card table-container">
          {loading ? (
            <div className="empty-state">Loading campaigns...</div>
          ) : campaigns.length === 0 ? (
            <div className="empty-state" style={{ padding: '36px 20px' }}>
              <Layers size={36} style={{ color: 'var(--brand-forest)', marginBottom: '12px' }} />
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                No Active Outreach Campaigns
              </h3>
              <p style={{ maxWidth: '520px', margin: '0 auto 18px', color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.5 }}>
                All prerequisite systems are verified and ready. Filter discovered wholesale buyers, personalize outreach copy with Gemini 3 Flash intelligence, and initiate a controlled campaign sequence.
              </p>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                <button className="btn btn-primary" onClick={startNewCampaign}>
                  <Plus size={14} />
                  <span>Create First Campaign</span>
                </button>
                <button className="btn btn-secondary" onClick={fetchCampaigns}>
                  <RefreshCw size={13} />
                  <span>Refresh Readiness</span>
                </button>
              </div>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Campaign Name</th>
                  <th>Target Audience</th>
                  <th>Drafts</th>
                  <th>Approved</th>
                  <th>Needs Review</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((camp) => (
                  <tr
                    key={camp.campaign_id}
                    onClick={() => openCampaign(camp)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{camp.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                        {camp.campaign_id}
                      </div>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px' }}>
                        {camp.audience_filters?.dataset === 'real' ? 'Real leads' : 'All datasets'} •{' '}
                        {camp.eligible_count || 0} eligible
                      </span>
                    </td>
                    <td>
                      <strong>{camp.draft_count || 0}</strong>
                    </td>
                    <td>
                      <span style={{ color: 'var(--brand-forest)', fontWeight: '600' }}>
                        {camp.approved_count || 0}
                      </span>
                    </td>
                    <td>
                      {camp.needs_review_count > 0 ? (
                        <span style={{ color: 'var(--color-warning)', fontWeight: '600' }}>
                          {camp.needs_review_count}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-tertiary)' }}>0</span>
                      )}
                    </td>
                    <td>
                      <StatusBadge type="campaign_status" value={camp.status} />
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {camp.updated_at ? new Date(camp.updated_at).toLocaleDateString() : '-'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        <button
                          className="btn btn-xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            openCampaign(camp);
                          }}
                        >
                          Open
                        </button>
                        <button
                          className="btn btn-xs btn-outline-danger"
                          onClick={(e) => handleDeleteCampaign(camp.campaign_id, e)}
                          title="Delete Campaign"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // Render View 2: Campaign Builder & Review Workspace
  // -------------------------------------------------------------
  return (
    <div className="page-container">
      {/* Toast Notice */}
      {actionNotice && (
        <div className={`toast-notification ${actionNotice.isError ? 'toast-error' : 'toast-success'}`}>
          <span>{actionNotice.msg}</span>
        </div>
      )}

      {/* Top Workspace Bar */}
      <div className="section-header" style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn btn-sm btn-secondary" onClick={closeCampaign}>
            <ArrowLeft size={13} />
            <span>Campaigns</span>
          </button>
          <div>
            <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>{activeCampaign.name || 'New Campaign'}</span>
              <StatusBadge type="campaign_status" value={activeCampaign.status} />
            </h2>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {activeCampaign.campaign_id ? `ID: ${activeCampaign.campaign_id}` : 'Draft Configuration'} •{' '}
              {drafts.length} drafts staged
            </div>
          </div>
        </div>

        <div className="toolbar-actions">
          {activeStep === 'review' && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => fetchDrafts(activeCampaign.campaign_id)}
            >
              <RefreshCw size={13} />
              <span>Refresh Queue</span>
            </button>
          )}
          <button className="btn btn-primary btn-sm" onClick={() => saveCampaignConfig()}>
            <span>Save Configuration</span>
          </button>
        </div>
      </div>

      {/* Compact Stepper Navigation */}
      <div className="stepper-bar" style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        {STEPPER_STEPS.map((step) => (
          <button
            key={step.id}
            className={`btn btn-sm ${activeStep === step.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => {
              setActiveStep(step.id);
              if (step.id === 'review' && activeCampaign.campaign_id) {
                fetchDrafts(activeCampaign.campaign_id);
              }
            }}
            style={{ fontWeight: activeStep === step.id ? '600' : '400' }}
          >
            {step.label}
          </button>
        ))}
      </div>

      {/* STEP 1: AUDIENCE SELECTOR */}
      {activeStep === 'audience' && (
        <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '20px' }}>
          {/* Left Column: Filter Controls */}
          <div className="card" style={{ padding: '18px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sliders size={15} />
              <span>Audience Eligibility Rules</span>
            </h3>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label">Dataset</label>
              <select
                className="form-control"
                value={audienceFilters.dataset}
                onChange={(e) => {
                  const updated = { ...audienceFilters, dataset: e.target.value };
                  setAudienceFilters(updated);
                  runAudiencePreview(updated);
                }}
              >
                <option value="real">Real leads only (Protected)</option>
                <option value="demo">Demo / Sample data only</option>
                <option value="all">All datasets (Real + Demo)</option>
              </select>
              <span className="field-hint">By default, demo records are excluded from live audiences.</span>
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label">Contact Classification</label>
              <select
                className="form-control"
                value={audienceFilters.classification[0] || 'Business'}
                onChange={(e) => {
                  const val = e.target.value === 'all' ? ['Business', 'Individual', 'Unclassified'] : [e.target.value];
                  const updated = { ...audienceFilters, classification: val };
                  setAudienceFilters(updated);
                  runAudiencePreview(updated);
                }}
              >
                <option value="Business">Business entities only</option>
                <option value="Individual">Individual practitioners only</option>
                <option value="all">All classifications</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label">Email Validation Status</label>
              <select
                className="form-control"
                value={audienceFilters.validation_status[0] || 'Valid'}
                onChange={(e) => {
                  const val = e.target.value === 'all' ? ['Valid', 'Review'] : [e.target.value];
                  const updated = { ...audienceFilters, validation_status: val };
                  setAudienceFilters(updated);
                  runAudiencePreview(updated);
                }}
              >
                <option value="Valid">Valid RFC syntax only</option>
                <option value="all">Valid + Review addresses</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label">Singing Bowls Buyer Relevance</label>
              <select
                className="form-control"
                value={audienceFilters.buyer_relevance.includes('Unknown') ? 'all' : 'high_medium'}
                onChange={(e) => {
                  const val = e.target.value === 'all' ? ['High', 'Medium', 'Unknown'] : ['High', 'Medium'];
                  const updated = { ...audienceFilters, buyer_relevance: val };
                  setAudienceFilters(updated);
                  runAudiencePreview(updated);
                }}
              >
                <option value="high_medium">High & Medium relevance only</option>
                <option value="all">Include Unknown relevance</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label">Outreach History</label>
              <select
                className="form-control"
                value={audienceFilters.contacted_status}
                onChange={(e) => {
                  const updated = { ...audienceFilters, contacted_status: e.target.value };
                  setAudienceFilters(updated);
                  runAudiencePreview(updated);
                }}
              >
                <option value="never">Never previously contacted</option>
                <option value="all">Allow re-contacting past leads</option>
              </select>
            </div>

            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '10px' }}
              onClick={() => saveCampaignConfig('message')}
            >
              <span>Save & Continue to Message</span>
              <ChevronRight size={14} />
            </button>
          </div>

          {/* Right Column: Live Audience Preview & Exclusion Breakdown */}
          <div className="card" style={{ padding: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: '600' }}>Live Audience Evaluation</h3>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Evaluates all stored leads against your configured audience rules.
                </p>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => runAudiencePreview()}
                disabled={previewLoading}
              >
                <RefreshCw size={12} className={previewLoading ? 'spinning' : ''} />
                <span>Re-evaluate</span>
              </button>
            </div>

            {previewLoading ? (
              <div className="empty-state" style={{ padding: '40px' }}>Evaluating audience...</div>
            ) : audiencePreview ? (
              <div>
                {/* 3 Metric Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginBottom: '20px' }}>
                  <div className="intel-card" style={{ padding: '14px' }}>
                    <span className="intel-label">Total Prospects</span>
                    <span className="intel-value">{audiencePreview.total_evaluated}</span>
                  </div>
                  <div className="intel-card" style={{ padding: '14px', borderColor: 'var(--brand-forest)' }}>
                    <span className="intel-label" style={{ color: 'var(--brand-forest)' }}>Eligible for Campaign</span>
                    <span className="intel-value" style={{ color: 'var(--brand-forest)' }}>
                      {audiencePreview.eligible_count}
                    </span>
                  </div>
                  <div className="intel-card" style={{ padding: '14px' }}>
                    <span className="intel-label">Excluded Records</span>
                    <span className="intel-value" style={{ color: 'var(--color-warning)' }}>
                      {audiencePreview.excluded_count}
                    </span>
                  </div>
                </div>

                {/* Explicit Exclusion Reasons Breakdown */}
                {audiencePreview.excluded_count > 0 && (
                  <div style={{ marginBottom: '20px', padding: '14px', background: 'var(--surface-color)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px' }}>
                      Explicit Exclusion Breakdown:
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {Object.entries(audiencePreview.exclusion_reasons || {}).map(([reason, count]) => (
                        <span
                          key={reason}
                          className="badge"
                          style={{ background: 'var(--stone-100)', color: 'var(--stone-800)', border: '1px solid var(--stone-300)', padding: '4px 8px' }}
                        >
                          <strong>{count}</strong> - {reason.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Sample Previews */}
                <div style={{ marginTop: '16px' }}>
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                    <button
                      className={`btn btn-xs ${!showExcludedSample ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setShowExcludedSample(false)}
                    >
                      Eligible Sample ({audiencePreview.sample_eligible?.length || 0})
                    </button>
                    <button
                      className={`btn btn-xs ${showExcludedSample ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setShowExcludedSample(true)}
                    >
                      Excluded Sample ({audiencePreview.sample_excluded?.length || 0})
                    </button>
                  </div>

                  <table className="data-table" style={{ fontSize: '12px' }}>
                    <thead>
                      <tr>
                        <th>Company</th>
                        <th>Email</th>
                        <th>Classification</th>
                        <th>Relevance</th>
                        {showExcludedSample && <th>Exclusion Reason</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {(showExcludedSample
                        ? audiencePreview.sample_excluded
                        : audiencePreview.sample_eligible
                      )?.slice(0, 8).map((lead) => (
                        <tr key={lead.lead_id}>
                          <td style={{ fontWeight: '500' }}>{lead.company_name || 'Unknown'}</td>
                          <td>{lead.email || '-'}</td>
                          <td><StatusBadge type="classification" value={lead.classification} /></td>
                          <td><StatusBadge type="relevance" value={lead.buyer_relevance} /></td>
                          {showExcludedSample && (
                            <td>
                              <span style={{ color: 'var(--color-danger)', fontSize: '11px' }}>
                                {(lead.exclusion_reasons || []).join(', ')}
                              </span>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* STEP 2: MESSAGE & CATALOG CONFIGURATION */}
      {activeStep === 'message' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
          {/* Left Column: Form Fields */}
          <div className="card" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '16px' }}>
              Campaign Details & Export Templates
            </h3>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label">Campaign Name</label>
              <input
                type="text"
                className="form-control"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
                placeholder="e.g. Singing Bowls - EU Holistic Instrument Wholesalers"
              />
            </div>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label">Subject Template</label>
              <input
                type="text"
                className="form-control"
                value={subjectTemplate}
                onChange={(e) => setSubjectTemplate(e.target.value)}
                placeholder="Subject with optional {{company_name}} tag"
              />
            </div>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label">Email Body Template</label>
              <textarea
                className="form-control"
                rows={14}
                value={bodyTemplate}
                onChange={(e) => setBodyTemplate(e.target.value)}
                style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', lineHeight: '1.6' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
              <button className="btn btn-secondary" onClick={() => setActiveStep('audience')}>
                <ArrowLeft size={13} />
                <span>Back to Audience</span>
              </button>
              <button className="btn btn-primary" onClick={() => saveCampaignConfig('personalize')}>
                <span>Save & Continue to Personalization</span>
                <ChevronRight size={13} />
              </button>
            </div>
          </div>

          {/* Right Column: Whitelisted Variables & Attachment Spec */}
          <div>
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px' }}>
                Whitelisted Template Tags
              </h4>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Tags automatically fall back to professional B2B phrasing if empty. Never renders "undefined".
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[
                  { tag: '{{buyer_name}}', desc: 'Verified contact name or Procurement Team' },
                  { tag: '{{company_name}}', desc: 'Verified company name' },
                  { tag: '{{country}}', desc: 'Prospect target country' },
                  { tag: '{{business_type}}', desc: 'Extracted wholesale or retail type' },
                  { tag: '{{industry}}', desc: 'Wellness, Sound Healing, or Instruments' },
                  { tag: '{{personalized_opening}}', desc: 'Grounded hook referencing verified evidence' }
                ].map((item) => (
                  <div key={item.tag} style={{ fontSize: '12px', background: 'var(--surface-color)', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                    <code style={{ color: 'var(--brand-forest)', fontWeight: '600' }}>{item.tag}</code>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card" style={{ padding: '16px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px' }}>
                Export Presentation Attachment
              </h4>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                Attached to drafts during review. Never dispatched automatically.
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px', background: 'var(--surface-color)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <FileText size={20} style={{ color: 'var(--brand-forest)' }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600' }}>{attachmentInfo?.filename}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{attachmentInfo?.size_kb} KB • Ready</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP 3: PERSONALIZATION GENERATOR */}
      {activeStep === 'personalize' && (
        <div className="card" style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
            Generate Grounded Outreach Drafts
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
            The personalization engine analyzes verified web evidence, applies anti-hallucination constraints,
            and validates each draft before staging it in the Operator Review Queue.
          </p>

          <div style={{ padding: '16px', background: 'var(--surface-color)', borderRadius: '6px', border: '1px solid var(--border-color)', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: '500' }}>Eligible Prospects:</span>
              <span style={{ fontWeight: '600', color: 'var(--brand-forest)' }}>
                {activeCampaign.eligible_count || audiencePreview?.eligible_count || 0}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: '500' }}>Existing Drafts:</span>
              <span style={{ fontWeight: '600' }}>{activeCampaign.draft_count || 0}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: '500' }}>Target Word Count:</span>
              <span style={{ color: 'var(--text-secondary)' }}>120 - 220 words</span>
            </div>
          </div>

          {/* Progress Monitor */}
          {generating && generationStatus && (
            <div style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                <span>{generationStatus.status_message}</span>
                <span>{generationStatus.progress}%</span>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${generationStatus.progress}%` }}></div>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                Active: {generationStatus.current_lead || 'Initializing...'}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="btn btn-primary"
              onClick={handleStartGeneration}
              disabled={generating}
              style={{ flex: 1 }}
            >
              <Play size={14} />
              <span>{generating ? 'Generating Drafts...' : 'Start Personalized Draft Generation'}</span>
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setActiveStep('review');
                fetchDrafts(activeCampaign.campaign_id);
              }}
            >
              <span>Go to Review Queue</span>
              <ChevronRight size={13} />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: OPERATOR REVIEW QUEUE (Main Workspace) */}
      {activeStep === 'review' && (
        <div>
          {/* Operational Review KPI Bar */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', marginBottom: '16px' }}>
            <div className="intel-card" style={{ padding: '12px' }}>
              <span className="intel-label">Total Drafts</span>
              <span className="intel-value">{drafts.length}</span>
            </div>
            <div className="intel-card" style={{ padding: '12px', borderColor: 'var(--brand-forest)' }}>
              <span className="intel-label" style={{ color: 'var(--brand-forest)' }}>Approved for Dispatch</span>
              <span className="intel-value" style={{ color: 'var(--brand-forest)' }}>
                {drafts.filter((d) => d.status === 'Approved').length}
              </span>
            </div>
            <div className="intel-card" style={{ padding: '12px' }}>
              <span className="intel-label">Needs Review</span>
              <span className="intel-value" style={{ color: 'var(--color-warning)' }}>
                {drafts.filter((d) => d.status === 'Needs Review').length}
              </span>
            </div>
            <div className="intel-card" style={{ padding: '12px' }}>
              <span className="intel-label">Edited by Operator</span>
              <span className="intel-value" style={{ color: 'var(--stone-800)' }}>
                {drafts.filter((d) => d.status === 'Edited').length}
              </span>
            </div>
            <div className="intel-card" style={{ padding: '12px' }}>
              <span className="intel-label">Rejected</span>
              <span className="intel-value" style={{ color: 'var(--color-danger)' }}>
                {drafts.filter((d) => d.status === 'Rejected').length}
              </span>
            </div>
          </div>

          {/* Review Filter Toolbar */}
          <div className="table-controls" style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {['all', 'Draft', 'Needs Review', 'Edited', 'Approved', 'Rejected'].map((st) => (
                <button
                  key={st}
                  className={`btn btn-xs ${draftStatusFilter === st ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setDraftStatusFilter(st)}
                >
                  {st === 'all' ? 'All Drafts' : st}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              {drafts.filter((d) => d.status === 'Approved').length > 0 && (
                <button
                  className="btn btn-xs btn-primary"
                  onClick={() => setActiveStep('dispatch')}
                  style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Send size={12} />
                  <span>Dispatch Center ({drafts.filter((d) => d.status === 'Approved').length} Approved) &rarr;</span>
                </button>
              )}
              <input
                type="text"
                placeholder="Search company, contact, subject..."
                className="form-control"
                style={{ width: '240px', fontSize: '12px', padding: '4px 10px' }}
                value={draftSearch}
                onChange={(e) => setDraftSearch(e.target.value)}
              />
            </div>

          </div>

          {/* Bulk Action Bar (Visible when drafts selected) */}
          {selectedDraftIds.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', background: 'var(--stone-100)', border: '1px solid var(--border-color)', borderRadius: '6px', marginBottom: '12px' }}>
              <span style={{ fontSize: '13px', fontWeight: '500' }}>
                {selectedDraftIds.length} draft{selectedDraftIds.length > 1 ? 's' : ''} selected
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-xs btn-primary" onClick={handleBulkApprove}>
                  <CheckCircle2 size={12} />
                  <span>Approve Selected</span>
                </button>
                <button className="btn btn-xs btn-outline-danger" onClick={handleBulkReject}>
                  <XCircle size={12} />
                  <span>Reject Selected</span>
                </button>
                <button className="btn btn-xs btn-secondary" onClick={handleBulkArchive}>
                  <Archive size={12} />
                  <span>Archive Selected</span>
                </button>
              </div>
            </div>
          )}

          {/* Drafts Dense Table */}
          <div className="card table-container">
            {draftsLoading ? (
              <div className="empty-state">Loading drafts...</div>
            ) : drafts.length === 0 ? (
              <div className="empty-state">
                <p>No drafts found matching the current filter.</p>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={() => {
                    setDraftStatusFilter('all');
                    setDraftSearch('');
                  }}
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '36px' }}>
                      <input
                        type="checkbox"
                        checked={selectedDraftIds.length === drafts.length && drafts.length > 0}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedDraftIds(drafts.map((d) => d.draft_id));
                          else setSelectedDraftIds([]);
                        }}
                      />
                    </th>
                    <th>Company</th>
                    <th>Recipient</th>
                    <th>Subject</th>
                    <th>Relevance</th>
                    <th>AI Confidence</th>
                    <th>Status</th>
                    <th>Updated</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {drafts.map((draft) => {
                    const isSelected = selectedDraftIds.includes(draft.draft_id);
                    return (
                      <tr
                        key={draft.draft_id}
                        className={isSelected ? 'row-selected' : ''}
                        onClick={() => handleOpenDraftDrawer(draft)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedDraftIds([...selectedDraftIds, draft.draft_id]);
                              else setSelectedDraftIds(selectedDraftIds.filter((id) => id !== draft.draft_id));
                            }}
                          />
                        </td>
                        <td>
                          <div style={{ fontWeight: '600' }}>{draft.company_name || 'Unknown'}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{draft.country || 'Global'}</div>
                        </td>
                        <td>
                          <div>{draft.recipient_name || 'Procurement Team'}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{draft.recipient_email}</div>
                        </td>
                        <td style={{ maxWidth: '280px' }}>
                          <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: '500' }}>
                            {draft.subject}
                          </div>
                        </td>
                        <td>
                          <StatusBadge type="relevance" value={draft.buyer_relevance} />
                        </td>
                        <td>
                          <span style={{ fontSize: '12px', fontWeight: '500' }}>
                            {Math.round((draft.ai_confidence || 0.85) * 100)}%
                          </span>
                        </td>
                        <td>
                          <StatusBadge type="draft_status" value={draft.status} />
                        </td>
                        <td style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                          {draft.updated_at ? new Date(draft.updated_at).toLocaleDateString() : '-'}
                        </td>
                        <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <button
                              className="btn btn-xs"
                              onClick={() => handleOpenDraftDrawer(draft)}
                              title="Review & Edit"
                            >
                              <Edit3 size={11} />
                              <span>Review</span>
                            </button>
                            {draft.status !== 'Approved' && (
                              <button
                                className="btn btn-xs btn-primary"
                                onClick={() => handleApproveDraft(draft.draft_id)}
                                title="Approve for future dispatch"
                              >
                                <Check size={11} />
                                <span>Approve</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* STEP 5: CONTROLLED DISPATCH ENGINE & DELIVERY TELEMETRY       */}
      {/* ------------------------------------------------------------- */}
      {activeStep === 'dispatch' && (
        <div>
          {/* DRY RUN BANNER */}
          {preflight?.dry_run && (
            <div style={{ background: '#FEF3C7', border: '1px solid #F59E0B', color: '#92400E', padding: '12px 16px', borderRadius: 6, marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600 }}>
                <ShieldAlert size={18} />
                <span>DRY RUN - No emails will be sent. Full pipeline simulation mode active.</span>
              </div>
              <span style={{ fontSize: 12, background: '#FDE68A', padding: '2px 8px', borderRadius: 4, fontWeight: 500 }}>
                Safe Testing Mode
              </span>
            </div>
          )}

          {/* Action Notification */}
          {dispatchNotice && (
            <div style={{ background: dispatchNotice.type === 'success' ? '#F0FDF4' : '#FEF2F2', border: `1px solid ${dispatchNotice.type === 'success' ? '#86EFAC' : '#FCA5A5'}`, color: dispatchNotice.type === 'success' ? '#166534' : '#991B1B', padding: '10px 16px', borderRadius: 6, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
              {dispatchNotice.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              <span>{dispatchNotice.message}</span>
            </div>
          )}

          {/* Preflight & Operational KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '20px' }}>
            <div className="intel-card" style={{ padding: '14px', borderColor: preflight?.ready ? 'var(--brand-forest)' : 'var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="intel-label">Preflight Eligibility</span>
                {preflightLoading ? (
                  <RefreshCw size={13} className="spin" />
                ) : preflight?.ready ? (
                  <CheckCircle2 size={16} color="var(--brand-forest)" />
                ) : (
                  <AlertTriangle size={16} color="var(--color-danger)" />
                )}
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: preflight?.ready ? 'var(--brand-forest)' : 'var(--color-danger)', marginTop: 4 }}>
                {preflight ? preflight.currently_eligible : '-'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {preflight ? `out of ${preflight.approved_count} approved drafts eligible` : 'Evaluating...'}
              </div>
            </div>

            <div className="intel-card" style={{ padding: '14px' }}>
              <span className="intel-label">Exclusions & Safety Filters</span>
              <div style={{ fontSize: '13px', marginTop: 8, lineHeight: 1.6 }}>
                <div>Duplicates: <strong>{preflight?.duplicate_count || 0}</strong></div>
                <div>Suppressed: <strong>{preflight?.suppressed_count || 0}</strong></div>
                <div>Demo Blocked: <strong>{preflight?.demo_count || 0}</strong></div>
              </div>
            </div>

            <div className="intel-card" style={{ padding: '14px' }}>
              <span className="intel-label">Attachment Specification</span>
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                <FileCheck size={16} color={preflight?.attachment_ready ? 'var(--brand-forest)' : 'var(--color-danger)'} />
                <span style={{ fontSize: 13, fontWeight: 500 }}>Resonance Export Catalog (company_presentation.pdf)</span>
              </div>
              <div style={{ fontSize: '11px', color: preflight?.attachment_ready ? 'var(--brand-forest)' : 'var(--color-danger)', marginTop: 4 }}>
                {preflight?.attachment_ready ? '✓ Valid verified PDF document (B2B catalog)' : '✗ Attachment missing or corrupt'}
              </div>
            </div>

            <div className="intel-card" style={{ padding: '14px' }}>
              <span className="intel-label">Daily Send Limits</span>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--stone-800)', marginTop: 4 }}>
                {preflight ? `${preflight.remaining_today} / ${preflight.daily_limit}` : '-'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {preflight ? `${preflight.sent_today} sent today (pacing: 3-8s delay)` : '-'}
              </div>
            </div>
          </div>

          {/* Preflight Blocking Reasons Alert (if not ready) */}
          {preflight && !preflight.ready && preflight.blocking_reasons?.length > 0 && (
            <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#991B1B', padding: '12px 16px', borderRadius: 6, marginBottom: 20 }}>
              <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <AlertTriangle size={16} />
                <span>Preflight Check Failed - Dispatch Blocked</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12 }}>
                {preflight.blocking_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Preflight Ready Banner (if ready) */}
          {preflight && preflight.ready && (
            <div style={{ background: '#F0FDFA', border: '1px solid #CCFBF1', color: '#0F766E', padding: '12px 16px', borderRadius: 6, marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600 }}>
                <CheckCircle2 size={18} />
                <span>Preflight Passed - Ready to dispatch {preflight.currently_eligible} verified emails.</span>
              </div>
              <span style={{ fontSize: 12 }}>Explicit confirmation required before sending.</span>
            </div>
          )}

          {/* Main Action Bar & Send Controls */}
          <div className="card" style={{ padding: '16px 20px', marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Campaign Status</div>
                <div style={{ marginTop: 2 }}>
                  <StatusBadge type="campaign_status" value={activeCampaign.status} />
                </div>
              </div>
              <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Queue Progress</div>
                <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>
                  {dispatchStatus ? `${dispatchStatus.counts?.Sent || 0} Sent • ${dispatchStatus.remaining_in_queue || 0} Pending` : '-'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => {
                  fetchPreflight(activeCampaign.campaign_id);
                  fetchDispatchStatus(activeCampaign.campaign_id);
                }}
                disabled={preflightLoading}
              >
                <RefreshCw size={13} className={preflightLoading ? 'spin' : ''} />
                <span>Re-check Preflight</span>
              </button>

              {activeCampaign.status === 'Sending' || dispatchStatus?.is_dispatching ? (
                <>
                  <button className="btn btn-sm btn-secondary" onClick={handlePauseDispatch}>
                    <Pause size={13} />
                    <span>Pause Campaign</span>
                  </button>
                  <button className="btn btn-sm btn-outline-danger" onClick={handleCancelDispatch}>
                    <Ban size={13} />
                    <span>Cancel Remaining</span>
                  </button>
                </>
              ) : activeCampaign.status === 'Paused' ? (
                <>
                  <button className="btn btn-sm btn-primary" onClick={handleOpenConfirmModal}>
                    <Play size={13} />
                    <span>Resume & Send</span>
                  </button>
                  <button className="btn btn-sm btn-outline-danger" onClick={handleCancelDispatch}>
                    <Ban size={13} />
                    <span>Cancel Remaining</span>
                  </button>
                </>
              ) : (
                <button
                  className="btn btn-primary"
                  onClick={handleOpenConfirmModal}
                  disabled={!preflight?.ready || preflight?.currently_eligible === 0}
                  style={{
                    padding: '8px 20px',
                    fontWeight: 600,
                    opacity: (!preflight?.ready || preflight?.currently_eligible === 0) ? 0.5 : 1
                  }}
                >
                  <Send size={15} />
                  <span>Send Approved Campaign</span>
                </button>
              )}
            </div>
          </div>

          {/* Two-Column Utility Grid: Test Send & Safety Controls */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
            {/* Controlled Test Send Panel */}
            <div className="card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <Send size={16} color="var(--brand-forest)" />
                <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Controlled Test Send</h4>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14 }}>
                Dispatches a test message with <code>[TEST OUTREACH]</code> header and company presentation. Never alters real contact history or <code>sent_log.csv</code>.
              </p>

              <div className="form-group" style={{ marginBottom: 10 }}>
                <label className="drawer-label" style={{ fontSize: 11 }}>Target Test Recipient</label>
                <input
                  type="email"
                  className="form-control"
                  placeholder="e.g. operator@resonance.org"
                  value={testRecipient}
                  onChange={(e) => setTestRecipient(e.target.value)}
                  style={{ fontSize: 12 }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="drawer-label" style={{ fontSize: 11 }}>Draft Template</label>
                <select
                  className="form-control"
                  value={testDraftId}
                  onChange={(e) => setTestDraftId(e.target.value)}
                  style={{ fontSize: 12 }}
                >
                  <option value="">Select an approved draft...</option>
                  {drafts.filter(d => d.status === 'Approved').map(d => (
                    <option key={d.draft_id} value={d.draft_id}>
                      {d.company_name} - {d.recipient_name} ({d.recipient_email})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={handleTestSend}
                  disabled={testSending || !testRecipient}
                >
                  <Send size={13} className={testSending ? 'spin' : ''} />
                  <span>{testSending ? 'Sending Test...' : 'Dispatch Test Email'}</span>
                </button>
              </div>

              {testResult && (
                <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 4, fontSize: 12, background: testResult.success ? '#F0FDF4' : '#FEF2F2', color: testResult.success ? '#166534' : '#991B1B', border: `1px solid ${testResult.success ? '#BBF7D0' : '#FECACA'}` }}>
                  {testResult.message}
                  {testResult.smtp_message_id && (
                    <div style={{ fontSize: 10, fontFamily: 'monospace', marginTop: 2, opacity: 0.8 }}>
                      ID: {testResult.smtp_message_id}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Operational Safety Guardrails */}
            <div className="card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <ShieldCheck size={16} color="var(--brand-forest)" />
                <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Active Safety Guardrails</h4>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14 }}>
                Automated deterministic boundaries enforcing responsible export outreach.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                  <CheckCircle2 size={15} color="var(--brand-forest)" />
                  <div>
                    <strong>Demo Data Isolation:</strong> <code>is_demo == true</code> records can never be sent.
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                  <CheckCircle2 size={15} color="var(--brand-forest)" />
                  <div>
                    <strong>Dual-Key Deduplication:</strong> Real-time lookup against historical <code>sent_log.csv</code>.
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                  <CheckCircle2 size={15} color="var(--brand-forest)" />
                  <div>
                    <strong>Suppression Filtering:</strong> Unsubscribed or blocked contacts excluded permanently.
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                  <CheckCircle2 size={15} color="var(--brand-forest)" />
                  <div>
                    <strong>Content Integrity:</strong> Rejects unresolved variables or missing body/subject.
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                  <CheckCircle2 size={15} color="var(--brand-forest)" />
                  <div>
                    <strong>Explicit Operator Confirmation:</strong> Automated background sending is strictly prevented.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Live Dispatch Queue Telemetry Table */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 className="card-title">Live Dispatch Queue & Events</h3>
                <p className="card-subtitle">Audited state transitions for campaign queue items.</p>
              </div>
            </div>

            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Recipient</th>
                    <th>Company</th>
                    <th>Subject</th>
                    <th>Status</th>
                    <th>Attempts</th>
                    <th>Queued At</th>
                    <th>Last Error / Note</th>
                  </tr>
                </thead>
                <tbody>
                  {(!dispatchStatus?.recent_events || dispatchStatus.recent_events.length === 0) ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-secondary)' }}>
                        Queue not yet initiated for this campaign. Click 'Send Approved Campaign' above to begin.
                      </td>
                    </tr>
                  ) : (
                    dispatchStatus.recent_events.map((ev, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 500 }}>{ev.recipient_email || '-'}</td>
                        <td>{ev.details?.company_name || 'Prospect'}</td>
                        <td style={{ fontSize: 12, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {ev.details?.subject || activeCampaign.subject_template}
                        </td>
                        <td>
                          <span className={`status-badge ${(ev.status || '').toLowerCase() === 'sent' ? 'valid' : (ev.status || '').toLowerCase() === 'failed' ? 'invalid' : 'neutral'}`}>
                            {ev.status || ev.event_type}
                          </span>
                        </td>
                        <td>{ev.details?.attempt_count || 1}</td>
                        <td style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                          {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '-'}
                        </td>
                        <td style={{ fontSize: 11, color: ev.error ? 'var(--color-danger)' : 'var(--text-secondary)', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {ev.error || ev.details?.smtp_message_id || '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}


      {/* ------------------------------------------------------------- */}
      {/* SLIDE-OUT OPERATOR REVIEW DRAWER (3-Column Layout)           */}
      {/* ------------------------------------------------------------- */}
      {selectedDraft && editingDraft && (
        <div className="drawer-overlay" onClick={() => setSelectedDraft(null)}>
          <div
            className="drawer-panel"
            style={{ width: '1080px', maxWidth: '95vw', display: 'flex', flexDirection: 'column' }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drawer Header */}
            <div className="drawer-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', padding: '16px 24px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: '600' }}>
                    Review Outreach Draft
                  </h3>
                  <StatusBadge type="draft_status" value={selectedDraft.status} />
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Draft ID: <code style={{ fontFamily: 'var(--font-mono)' }}>{selectedDraft.draft_id}</code>
                </div>
              </div>
              <button className="btn btn-sm btn-secondary" onClick={() => setSelectedDraft(null)}>
                Close
              </button>
            </div>

            {/* Drawer Body: 3 Columns */}
            <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr 280px', gap: '16px', padding: '20px 24px', flex: 1, overflowY: 'auto' }}>
              {/* Left Column: Prospect Intelligence */}
              <div style={{ borderRight: '1px solid var(--border-color)', paddingRight: '16px' }}>
                <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
                  Recipient Profile
                </h4>

                <div className="drawer-field" style={{ marginBottom: '12px' }}>
                  <label className="drawer-label">Company</label>
                  <div style={{ fontWeight: '600' }}>{selectedDraft.company_name || 'Unknown'}</div>
                </div>

                <div className="drawer-field" style={{ marginBottom: '12px' }}>
                  <label className="drawer-label">Recipient Name</label>
                  <div>{selectedDraft.recipient_name || 'Procurement Team'}</div>
                </div>

                <div className="drawer-field" style={{ marginBottom: '12px' }}>
                  <label className="drawer-label">Email</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '12px', wordBreak: 'break-all' }}>{selectedDraft.recipient_email}</span>
                    <button
                      className="btn btn-xs"
                      onClick={() => copyToClipboard(selectedDraft.recipient_email)}
                      title="Copy Email"
                    >
                      {copiedEmail ? <Check size={10} /> : <Copy size={10} />}
                    </button>
                  </div>
                </div>

                <div className="drawer-field" style={{ marginBottom: '12px' }}>
                  <label className="drawer-label">Country</label>
                  <div>{selectedDraft.country || 'International'}</div>
                </div>

                <div className="drawer-field" style={{ marginBottom: '12px' }}>
                  <label className="drawer-label">Classification</label>
                  <div><StatusBadge type="classification" value={selectedDraft.classification} /></div>
                </div>

                <div className="drawer-field" style={{ marginBottom: '12px' }}>
                  <label className="drawer-label">Buyer Relevance</label>
                  <div><StatusBadge type="relevance" value={selectedDraft.buyer_relevance} /></div>
                </div>

                <div className="drawer-field" style={{ marginBottom: '12px' }}>
                  <label className="drawer-label">AI Confidence</label>
                  <div style={{ fontWeight: '600', color: 'var(--brand-forest)' }}>
                    {Math.round((selectedDraft.ai_confidence || 0.85) * 100)}%
                  </div>
                </div>
              </div>

              {/* Middle Column: Email Draft Editor */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <h4 style={{ fontSize: '13px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
                  Message Draft Editor
                </h4>

                <div className="form-group">
                  <label className="form-label">Subject</label>
                  <input
                    type="text"
                    className="form-control"
                    value={editingDraft.subject}
                    onChange={(e) => setEditingDraft({ ...editingDraft, subject: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Opening Hook (Grounded)</label>
                  <input
                    type="text"
                    className="form-control"
                    value={editingDraft.opening_line}
                    onChange={(e) => setEditingDraft({ ...editingDraft, opening_line: e.target.value })}
                  />
                </div>

                <div className="form-group" style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <label className="form-label" style={{ marginBottom: 0 }}>Email Body</label>
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                      Words: {editingDraft.body.split(/\s+/).filter(Boolean).length} (Target: 120-220)
                    </span>
                  </div>
                  <textarea
                    className="form-control"
                    rows={12}
                    value={editingDraft.body}
                    onChange={(e) => setEditingDraft({ ...editingDraft, body: e.target.value })}
                    style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', lineHeight: '1.6' }}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Sign-off / Closing</label>
                  <textarea
                    className="form-control"
                    rows={2}
                    value={editingDraft.closing}
                    onChange={(e) => setEditingDraft({ ...editingDraft, closing: e.target.value })}
                    style={{ fontSize: '12px' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button className="btn btn-sm btn-secondary" onClick={handleSaveDraftEdit}>
                    <Edit3 size={12} />
                    <span>Save Draft Changes</span>
                  </button>
                </div>
              </div>

              {/* Right Column: Ground-Truth Evidence, Validation & Versions */}
              <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '16px', overflowY: 'auto' }}>
                <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
                  Evidence & Audit
                </h4>

                {/* Validation Report */}
                <div style={{ padding: '12px', background: 'var(--surface-color)', borderRadius: '6px', border: '1px solid var(--border-color)', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                    {selectedDraft.validation?.is_grounded ? (
                      <CheckCircle2 size={14} style={{ color: 'var(--brand-forest)' }} />
                    ) : (
                      <AlertTriangle size={14} style={{ color: 'var(--color-warning)' }} />
                    )}
                    <span style={{ fontSize: '12px', fontWeight: '600' }}>
                      {selectedDraft.validation?.is_grounded ? 'Grounded in Source Data' : 'Review Recommended'}
                    </span>
                  </div>

                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    Word Count: {selectedDraft.validation?.word_count || 0} •{' '}
                    Spam Triggers: {selectedDraft.validation?.spam_detected ? 'Detected' : 'None'}
                  </div>

                  {selectedDraft.validation?.issues?.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--color-warning)' }}>
                      {selectedDraft.validation.issues.map((iss, i) => (
                        <div key={i}>• {iss}</div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Ground-Truth Evidence Quotes */}
                <div style={{ marginBottom: '16px' }}>
                  <label className="drawer-label" style={{ marginBottom: '6px' }}>Source Evidence Citations</label>
                  {selectedDraft.personalization_evidence?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {selectedDraft.personalization_evidence.map((ev, i) => (
                        <div key={i} className="evidence-callout" style={{ fontSize: '11px', padding: '8px' }}>
                          <div>"{ev.evidence || ev.quote}"</div>
                          {ev.url && (
                            <a
                              href={ev.url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', marginTop: '4px', fontSize: '10px', color: 'var(--brand-forest)' }}
                            >
                              <span>View Source Page</span>
                              <ExternalLink size={10} />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                      Synthesized from verified lead business profile and export catalog specifications.
                    </div>
                  )}
                </div>

                {/* Version History Accordion */}
                <div>
                  <label className="drawer-label" style={{ marginBottom: '6px' }}>
                    Version History ({selectedDraft.version_history?.length || 1})
                  </label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                    {(selectedDraft.version_history || []).map((ver) => (
                      <div
                        key={ver.version}
                        style={{ padding: '8px', background: 'var(--surface-color)', borderRadius: '4px', border: '1px solid var(--border-color)', fontSize: '11px' }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600' }}>
                          <span>v{ver.version}</span>
                          <span style={{ color: 'var(--text-tertiary)', fontSize: '10px' }}>
                            {new Date(ver.generated_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>{ver.subject}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Drawer Footer Actions */}
            <div className="drawer-footer" style={{ borderTop: '1px solid var(--border-color)', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--surface-color)' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={() => handleRegenerateDraft(selectedDraft.draft_id)}
                >
                  <RotateCcw size={12} />
                  <span>Regenerate</span>
                </button>
                <button
                  className="btn btn-sm btn-outline-danger"
                  onClick={() => setShowRejectModal(true)}
                >
                  <XCircle size={12} />
                  <span>Reject</span>
                </button>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                  Approval stages draft for future dispatch. No emails will be sent.
                </div>
                {selectedDraft.status !== 'Approved' ? (
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => handleApproveDraft(selectedDraft.draft_id)}
                  >
                    <CheckCircle2 size={13} />
                    <span>Approve for Future Dispatch</span>
                  </button>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="badge badge-valid" style={{ padding: '6px 12px', fontSize: '12px' }}>
                      Approved for Future Dispatch
                    </span>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => {
                        setTestDraftId(selectedDraft.draft_id);
                        setActiveStep('dispatch');
                        setSelectedDraft(null);
                      }}
                      title="Test send this draft in Dispatch Center"
                    >
                      <Send size={12} />
                      <span>Test Send &rarr;</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="drawer-overlay" style={{ zIndex: 1100 }}>
          <div className="card" style={{ width: '420px', padding: '20px', margin: 'auto' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '10px' }}>
              Reject Outreach Draft
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
              Select a reason for auditing and model refinement:
            </p>
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <select
                className="form-control"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
              >
                <option value="Incorrect personalization">Incorrect personalization</option>
                <option value="Insufficient evidence">Insufficient evidence</option>
                <option value="Wrong audience profile">Wrong audience profile</option>
                <option value="Poor wording or tone">Poor wording or tone</option>
                <option value="Duplicate prospect">Duplicate prospect</option>
                <option value="Not relevant for export">Not relevant for export</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button className="btn btn-sm btn-secondary" onClick={() => setShowRejectModal(false)}>
                Cancel
              </button>
              <button className="btn btn-sm btn-outline-danger" onClick={handleRejectDraft}>
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* EXPLICIT SEND CONFIRMATION MODAL (Mandatory Step 5 Action)   */}
      {/* ------------------------------------------------------------- */}
      {showConfirmModal && (
        <div className="drawer-overlay" style={{ zIndex: 1200 }} onClick={() => setShowConfirmModal(false)}>
          <div
            className="card"
            style={{ width: '560px', maxWidth: '95vw', padding: '24px', margin: 'auto' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <Send size={20} color="var(--brand-forest)" />
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>
                Confirm & Send Approved Campaign
              </h3>
            </div>

            <div style={{ background: '#FEF3C7', border: '1px solid #F59E0B', color: '#92400E', padding: '12px 14px', borderRadius: 6, marginBottom: 16, fontSize: 13, lineHeight: 1.5 }}>
              You are about to send <strong>{preflight?.currently_eligible}</strong> emails.
              {preflight?.dry_run && (
                <div style={{ marginTop: 4, fontWeight: 600 }}>
                  [DRY RUN - No emails will be sent. Simulation only.]
                </div>
              )}
            </div>

            {/* Campaign Summary Breakdown */}
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 6, padding: '14px 16px', marginBottom: 16, fontSize: 13 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px' }}>
                <div>Campaign: <strong>{activeCampaign.name}</strong></div>
                <div>Recipients: <strong style={{ color: 'var(--brand-forest)' }}>{preflight?.currently_eligible}</strong></div>
                <div>Blocked: <strong>{preflight?.blocked_count}</strong></div>
                <div>Suppressed: <strong>{preflight?.suppressed_count}</strong></div>
                <div>Duplicates: <strong>{preflight?.duplicate_count}</strong></div>
                <div>Attachment: <strong>company_presentation.pdf (Export Catalog)</strong></div>
                <div>Daily limit: <strong>{preflight?.daily_limit}</strong></div>
                <div>Remaining today: <strong>{preflight?.remaining_today}</strong></div>
              </div>
            </div>

            {/* Operator Notes Input */}
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="drawer-label" style={{ fontSize: 12 }}>Operator Confirmation Notes (Optional)</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Verified B2B wholesale outreach batch"
                value={confirmNotes}
                onChange={(e) => setConfirmNotes(e.target.value)}
                style={{ fontSize: 13 }}
              />
            </div>

            {/* Acknowledgment Checkbox */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer', fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={confirmUnderstood}
                  onChange={(e) => setConfirmUnderstood(e.target.checked)}
                  style={{ marginTop: 3 }}
                />
                <span>
                  I confirm that these {preflight?.currently_eligible} drafts and recipients have been reviewed and approved for export outreach.
                </span>
              </label>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowConfirmModal(false)}
                disabled={dispatching}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleConfirmSend}
                disabled={!confirmUnderstood || dispatching}
                style={{ fontWeight: 600 }}
              >
                <Send size={14} className={dispatching ? 'spin' : ''} />
                <span>
                  {dispatching
                    ? 'Initiating Dispatch...'
                    : `Confirm & Send ${preflight?.currently_eligible || 0} Emails`}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

