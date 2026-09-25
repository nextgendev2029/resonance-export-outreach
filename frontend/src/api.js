/**
 * API Client for Resonance - Export Outreach & Lead Operations
 */

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL)
  ? import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '')
  : '';

async function handleResponse(res) {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const err = await res.json();
      errorDetail = err.detail || err.message || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Stats & Telemetry
  getStats: () => fetch(`${API_BASE}/api/stats`).then(handleResponse),

  // Leads Management
  getLeads: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.set('search', params.search);
    if (params.status && params.status !== 'all') query.set('status', params.status);
    if (params.classification && params.classification !== 'all') query.set('classification', params.classification);
    if (params.source && params.source !== 'all') query.set('source', params.source);
    if (params.data_type && params.data_type !== 'all') query.set('data_type', params.data_type);
    return fetch(`${API_BASE}/api/leads?${query.toString()}`).then(handleResponse);
  },

  getLeadDetail: (identifier) =>
    fetch(`${API_BASE}/api/leads/${encodeURIComponent(identifier)}`).then(handleResponse),

  updateLead: (identifier, payload) =>
    fetch(`${API_BASE}/api/leads/${encodeURIComponent(identifier)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  uploadLeads: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/api/leads/upload`, {
      method: 'POST',
      body: formData,
    }).then(handleResponse);
  },

  deleteLead: (identifier) =>
    fetch(`${API_BASE}/api/leads/${encodeURIComponent(identifier)}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Discovery Engine (Phase 6 US Home Decor & API Integrations)
  getDiscoveryConfig: () =>
    fetch(`${API_BASE}/api/discovery/config`).then(handleResponse),

  getDiscoveryProviders: () =>
    fetch(`${API_BASE}/api/discovery/providers`).then(handleResponse),

  getProviderHealth: (providerId) =>
    fetch(`${API_BASE}/api/discovery/providers/${encodeURIComponent(providerId)}/health`).then(handleResponse),

  searchBuyers: (payload) =>
    fetch(`${API_BASE}/api/discovery/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  getDiscoveryStats: () =>
    fetch(`${API_BASE}/api/discovery/stats`).then(handleResponse),

  getDiscoveryConfigStatus: () =>
    fetch(`${API_BASE}/api/discovery/config/status`).then(handleResponse),

  startDiscovery: (payload) =>
    fetch(`${API_BASE}/api/discovery/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  getDiscoveryStatus: () =>
    fetch(`${API_BASE}/api/discovery/status`).then(handleResponse),

  getDiscoveryRuns: () =>
    fetch(`${API_BASE}/api/discovery/runs`).then(handleResponse),

  getDiscoveryRunDetail: (runId) =>
    fetch(`${API_BASE}/api/discovery/runs/${encodeURIComponent(runId)}`).then(handleResponse),

  // Classification
  startClassification: (payload) =>
    fetch(`${API_BASE}/api/classify/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  getClassifyStatus: () =>
    fetch(`${API_BASE}/api/classify/status`).then(handleResponse),

  // Campaigns / Send
  sendCampaign: (payload) =>
    fetch(`${API_BASE}/api/campaign/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  getCampaignStatus: () =>
    fetch(`${API_BASE}/api/campaign/status`).then(handleResponse),

  // Reports
  getReports: () =>
    fetch(`${API_BASE}/api/reports`).then(handleResponse),

  // Settings
  getSettings: () =>
    fetch(`${API_BASE}/api/settings`).then(handleResponse),

  updateSettings: (payload) =>
    fetch(`${API_BASE}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  // Lead Intelligence & Enrichment (Phase 3)
  getIntelligenceStats: () =>
    fetch(`${API_BASE}/api/intelligence/stats`).then(handleResponse),

  getIntelligenceLeads: (params = {}) => {
    const query = new URLSearchParams();
    if (params.dataset && params.dataset !== 'all') query.set('dataset', params.dataset);
    if (params.status && params.status !== 'all') query.set('status', params.status);
    if (params.classification && params.classification !== 'all') query.set('classification', params.classification);
    if (params.relevance && params.relevance !== 'all') query.set('relevance', params.relevance);
    if (params.search) query.set('search', params.search);
    return fetch(`${API_BASE}/api/intelligence/leads?${query.toString()}`).then(handleResponse);
  },

  getIntelligenceLeadDetail: (leadId) =>
    fetch(`${API_BASE}/api/intelligence/leads/${encodeURIComponent(leadId)}`).then(handleResponse),

  enrichSingleLead: (leadId) =>
    fetch(`${API_BASE}/api/intelligence/leads/${encodeURIComponent(leadId)}/enrich`, {
      method: 'POST',
    }).then(handleResponse),

  startIntelligenceRun: (payload = {}) =>
    fetch(`${API_BASE}/api/intelligence/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  getIntelligenceStatus: () =>
    fetch(`${API_BASE}/api/intelligence/status`).then(handleResponse),

  getIntelligenceRuns: () =>
    fetch(`${API_BASE}/api/intelligence/runs`).then(handleResponse),

  getIntelligenceRunDetail: (runId) =>
    fetch(`${API_BASE}/api/intelligence/runs/${encodeURIComponent(runId)}`).then(handleResponse),

  classifyLeads: (payload = {}) =>
    fetch(`${API_BASE}/api/intelligence/classify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  // Campaigns & Outreach Queue (Phase 4)
  getCampaigns: () => fetch(`${API_BASE}/api/campaigns`).then(handleResponse),

  createCampaign: (payload) =>
    fetch(`${API_BASE}/api/campaigns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  getCampaignDetail: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}`).then(handleResponse),

  updateCampaign: (campaignId, payload) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  deleteCampaign: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}`, {
      method: 'DELETE',
    }).then(handleResponse),

  getAttachmentInfo: () =>
    fetch(`${API_BASE}/api/campaigns/attachment-info`).then(handleResponse),

  previewAudience: (payload) =>
    fetch(`${API_BASE}/api/campaigns/preview-audience`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  previewCampaignAudience: (campaignId, payload = null) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/audience/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload ? JSON.stringify(payload) : undefined,
    }).then(handleResponse),

  generateCampaignDrafts: (campaignId, payload = {}) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  getCampaignGenerationStatus: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/status`).then(handleResponse),

  getCampaignDrafts: (campaignId, params = {}) => {
    const query = new URLSearchParams();
    if (params.status && params.status !== 'all') query.set('status', params.status);
    if (params.search) query.set('search', params.search);
    return fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts?${query.toString()}`).then(handleResponse);
  },

  getCampaignDraftDetail: (campaignId, draftId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/${encodeURIComponent(draftId)}`).then(handleResponse),

  updateCampaignDraft: (campaignId, draftId, payload) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/${encodeURIComponent(draftId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  approveCampaignDraft: (campaignId, draftId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/${encodeURIComponent(draftId)}/approve`, {
      method: 'POST',
    }).then(handleResponse),

  rejectCampaignDraft: (campaignId, draftId, reason) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/${encodeURIComponent(draftId)}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    }).then(handleResponse),

  regenerateCampaignDraft: (campaignId, draftId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/${encodeURIComponent(draftId)}/regenerate`, {
      method: 'POST',
    }).then(handleResponse),

  bulkApproveDrafts: (campaignId, draftIds) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/bulk-approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_ids: draftIds }),
    }).then(handleResponse),

  bulkRejectDrafts: (campaignId, draftIds, reason) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/bulk-reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_ids: draftIds, reason }),
    }).then(handleResponse),

  bulkArchiveDrafts: (campaignId, draftIds) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/drafts/bulk-archive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_ids: draftIds }),
    }).then(handleResponse),

  // -------------------------------------------------------------
  // Controlled Dispatch Operations (Phase 5)
  // -------------------------------------------------------------
  getCampaignPreflight: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/dispatch/preflight`).then(handleResponse),

  prepareCampaignQueue: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/dispatch/queue`, {
      method: 'POST',
    }).then(handleResponse),

  getCampaignDispatchStatus: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/dispatch/status`).then(handleResponse),

  confirmCampaignDispatch: (campaignId, payload = { confirmed: true, operator_notes: '' }) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/dispatch/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  pauseCampaignDispatch: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/dispatch/pause`, {
      method: 'POST',
    }).then(handleResponse),

  cancelCampaignDispatch: (campaignId) =>
    fetch(`${API_BASE}/api/campaigns/${encodeURIComponent(campaignId)}/dispatch/cancel`, {
      method: 'POST',
    }).then(handleResponse),

  getDispatchItem: (dispatchId) =>
    fetch(`${API_BASE}/api/dispatch/${encodeURIComponent(dispatchId)}`).then(handleResponse),

  dispatchTestSend: (payload) =>
    fetch(`${API_BASE}/api/dispatch/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  // Suppression
  getSuppressions: () =>
    fetch(`${API_BASE}/api/suppression`).then(handleResponse),

  addSuppression: (payload) =>
    fetch(`${API_BASE}/api/suppression`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handleResponse),

  removeSuppression: (email) =>
    fetch(`${API_BASE}/api/suppression/${encodeURIComponent(email)}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Analytics
  getAnalyticsOverview: () =>
    fetch(`${API_BASE}/api/analytics/overview`).then(handleResponse),

  getAnalyticsCampaigns: () =>
    fetch(`${API_BASE}/api/analytics/campaigns`).then(handleResponse),

  getAnalyticsCampaignDetail: (campaignId) =>
    fetch(`${API_BASE}/api/analytics/campaigns/${encodeURIComponent(campaignId)}`).then(handleResponse),

  getAnalyticsRecentActivity: (limit = 50) =>
    fetch(`${API_BASE}/api/analytics/recent-activity?limit=${limit}`).then(handleResponse),
};

