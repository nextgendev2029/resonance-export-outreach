import React, { useState, useEffect } from 'react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';
import {
  Search,
  Trash2,
  Filter,
  Download,
  ExternalLink,
  Copy,
  Check,
  X,
  FileText,
  Save,
  Globe,
  Building2,
  Mail,
  User,
  MapPin,
  Calendar,
  Layers,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';

export default function LeadsPage({ onRefreshStats }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [classFilter, setClassFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [dataTypeFilter, setDataTypeFilter] = useState('all'); // 'all', 'real', 'demo'

  // Lead Detail Drawer State
  const [selectedLead, setSelectedLead] = useState(null);
  const [drawerNotes, setDrawerNotes] = useState('');
  const [drawerStatus, setDrawerStatus] = useState('');
  const [drawerClassification, setDrawerClassification] = useState('');
  const [savingLead, setSavingLead] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const data = await api.getLeads({
        search: searchTerm,
        status: statusFilter,
        classification: classFilter,
        source: sourceFilter,
        data_type: dataTypeFilter,
      });
      setLeads(data);
    } catch (err) {
      console.error('Failed to load leads:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchLeads();
    }, 180);
    return () => clearTimeout(timer);
  }, [searchTerm, statusFilter, classFilter, sourceFilter, dataTypeFilter]);

  const openLeadDrawer = (lead) => {
    setSelectedLead(lead);
    setDrawerNotes(lead.notes || '');
    setDrawerStatus(lead.validation_status || 'Valid');
    setDrawerClassification(lead.classification || 'Unclassified');
  };

  const closeLeadDrawer = () => {
    setSelectedLead(null);
  };

  const handleCopyEmail = (email) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  const handleSaveDrawerLead = async () => {
    if (!selectedLead) return;
    setSavingLead(true);
    try {
      const idOrEmail = selectedLead.email || selectedLead.lead_id;
      const res = await api.updateLead(idOrEmail, {
        notes: drawerNotes,
        validation_status: drawerStatus,
        classification: drawerClassification,
      });
      // Update local state
      setSelectedLead({
        ...selectedLead,
        notes: drawerNotes,
        validation_status: drawerStatus,
        classification: drawerClassification,
      });
      fetchLeads();
      onRefreshStats();
      alert('Lead details updated successfully.');
    } catch (err) {
      alert('Update failed: ' + err.message);
    } finally {
      setSavingLead(false);
    }
  };

  const handleDelete = async (lead) => {
    const idOrEmail = lead.email || lead.lead_id;
    const name = lead.company_name || lead.email;
    if (!window.confirm(`Remove buyer lead '${name}' from database?`)) return;
    try {
      await api.deleteLead(idOrEmail);
      if (selectedLead && (selectedLead.email === lead.email || selectedLead.lead_id === lead.lead_id)) {
        closeLeadDrawer();
      }
      fetchLeads();
      onRefreshStats();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  return (
    <div>
      {/* Top Controls Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A' }}>
            {leads.length} Records In View
          </span>
          <span style={{ fontSize: '12px', color: '#64748B', marginLeft: '8px' }}>
            (Persistent Lead Store: data/buyers.csv)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <a href="/discovery" className="btn btn-sm btn-primary">
            <Search size={13} />
            <span>Find Buyers (API)</span>
          </a>
          <a href="/download-report" className="btn btn-sm">
            <Download size={13} />
            <span>Export CSV</span>
          </a>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        {/* Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: '1', minWidth: '220px' }}>
          <Search size={14} color="#64748B" />
          <input
            type="text"
            className="input"
            style={{ padding: '5px 8px', fontSize: '12px' }}
            placeholder="Search by company, buyer name, email, country, or notes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Data Type Filter (Real vs Demo) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: '#64748B' }}>Dataset:</span>
          <select
            className="select"
            style={{ padding: '4px 6px', fontSize: '12px', width: 'auto' }}
            value={dataTypeFilter}
            onChange={(e) => setDataTypeFilter(e.target.value)}
          >
            <option value="all">All Records</option>
            <option value="real">Real Discovered Only</option>
            <option value="demo">Demo / Sample Data</option>
          </select>
        </div>

        {/* Validation Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: '#64748B' }}>Validation:</span>
          <select
            className="select"
            style={{ padding: '4px 6px', fontSize: '12px', width: 'auto' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="valid">Valid Syntax</option>
            <option value="review">Review Needed</option>
            <option value="missing">Missing Email</option>
            <option value="invalid">Invalid Syntax</option>
          </select>
        </div>

        {/* Classification Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: '#64748B' }}>Segment:</span>
          <select
            className="select"
            style={{ padding: '4px 6px', fontSize: '12px', width: 'auto' }}
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value)}
          >
            <option value="all">All Segments</option>
            <option value="business">Business (B2B)</option>
            <option value="individual">Individual</option>
            <option value="unclassified">Unclassified</option>
          </select>
        </div>

        {/* Source Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: '#64748B' }}>Source:</span>
          <select
            className="select"
            style={{ padding: '4px 6px', fontSize: '12px', width: 'auto' }}
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="all">All Sources</option>
            <option value="Google Search">Google Search</option>
            <option value="US B2B Trade Directory">US B2B Trade Directory</option>
            <option value="Direct Website Contact Crawler">Website Contact Crawler</option>
            <option value="Facebook">Facebook</option>
            <option value="LinkedIn">LinkedIn</option>
          </select>
        </div>
      </div>

      {/* Main Table */}
      <div className="table-container">
        {loading ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#64748B' }}>
            Loading buyer leads...
          </div>
        ) : leads.length === 0 ? (
          <div className="empty-state-box">
            <div className="empty-state-title">No buyer leads found matching filter</div>
            <div className="empty-state-desc">
              Try adjusting your search terms, changing the segment filter, or run a buyer discovery pass.
            </div>
          </div>
        ) : (
          <table className="ops-table">
            <thead>
              <tr>
                <th>Company Name</th>
                <th>Contact Name</th>
                <th>Email Address</th>
                <th>Country</th>
                <th>Source</th>
                <th>Validation</th>
                <th>AI Segment</th>
                <th>Outreach</th>
                <th>Dataset</th>
                <th style={{ width: '40px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((b) => (
                <tr
                  key={b.lead_id || b.email}
                  className="clickable"
                  onClick={() => openLeadDrawer(b)}
                  title="Click to view and edit lead details"
                >
                  <td>
                    <div style={{ fontWeight: 600, color: '#0F172A' }}>
                      {b.company_name || 'Wholesale Buyer'}
                    </div>
                    {b.website && (
                      <div style={{ fontSize: '11px', color: '#0F766E' }}>
                        {b.website.replace('https://', '').replace('http://', '').split('/')[0]}
                      </div>
                    )}
                  </td>
                  <td>
                    <span style={{ fontSize: '12px', color: '#334155' }}>
                      {b.buyer_name || <span style={{ color: '#94A3B8' }}>-</span>}
                    </span>
                  </td>
                  <td className="mono-cell">
                    {b.email ? (
                      b.email
                    ) : (
                      <span style={{ color: '#C2410C', fontSize: '11px' }}>
                        [Missing - Review URL]
                      </span>
                    )}
                  </td>
                  <td>
                    <span style={{ fontSize: '12px', color: '#334155' }}>
                      {b.country || 'International'}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', color: '#64748B' }}>
                      {b.source_platform}
                    </span>
                  </td>
                  <td>
                    <StatusBadge type="validation" value={b.validation_status} />
                  </td>
                  <td>
                    <StatusBadge type="classification" value={b.classification} />
                  </td>
                  <td>
                    <StatusBadge type="outreach" value={b.outreach_status} />
                  </td>
                  <td>
                    <StatusBadge type="datatype" value={b.is_demo} />
                  </td>
                  <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDelete(b)}
                      title="Delete lead record"
                    >
                      <Trash2 size={11} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Slide-out Lead Detail Drawer */}
      {selectedLead && (
        <div className="drawer-overlay" onClick={closeLeadDrawer}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <StatusBadge type="datatype" value={selectedLead.is_demo} />
                  <StatusBadge type="validation" value={selectedLead.validation_status} />
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A', lineHeight: '1.2' }}>
                  {selectedLead.company_name || 'Wholesale Buyer'}
                </h3>
                <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                  Lead ID: <span className="mono-cell">{selectedLead.lead_id}</span>
                </div>
              </div>
              <button
                className="btn btn-sm"
                onClick={closeLeadDrawer}
                style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '16px' }}
              >
                ✕
              </button>
            </div>

            <div className="drawer-body">
              {/* Email Address with Copy Button */}
              <div className="drawer-field-group">
                <span className="drawer-field-label">Email Address</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="mono-cell drawer-field-value" style={{ fontWeight: 600 }}>
                    {selectedLead.email || <span style={{ color: '#C2410C' }}>No direct email extracted</span>}
                  </span>
                  {selectedLead.email && (
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => handleCopyEmail(selectedLead.email)}
                      style={{ padding: '2px 6px', fontSize: '11px' }}
                      title="Copy email"
                    >
                      {copiedEmail ? <Check size={11} color="#059669" /> : <Copy size={11} />}
                      <span>{copiedEmail ? 'Copied' : 'Copy'}</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Contact Name & Country */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="drawer-field-group">
                  <span className="drawer-field-label">Contact Name</span>
                  <span className="drawer-field-value">{selectedLead.buyer_name || 'Not specified'}</span>
                </div>
                <div className="drawer-field-group">
                  <span className="drawer-field-label">Country</span>
                  <span className="drawer-field-value">{selectedLead.country || 'International'}</span>
                </div>
              </div>

              {/* Website & Source Platform */}
              <div className="drawer-field-group">
                <span className="drawer-field-label">Company Website</span>
                {selectedLead.website ? (
                  <a
                    href={selectedLead.website.startsWith('http') ? selectedLead.website : `https://${selectedLead.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#0F766E', display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12.5px' }}
                  >
                    <span>{selectedLead.website}</span>
                    <ExternalLink size={12} />
                  </a>
                ) : (
                  <span style={{ color: '#94A3B8', fontSize: '12px' }}>No website recorded</span>
                )}
              </div>

              {/* Source URL with View Source Link */}
              <div className="drawer-field-group">
                <span className="drawer-field-label">Originating Source URL</span>
                {selectedLead.source_url ? (
                  <a
                    href={selectedLead.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#0F766E', display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12.5px', wordBreak: 'break-all' }}
                  >
                    <span>{selectedLead.source_url}</span>
                    <ExternalLink size={12} />
                  </a>
                ) : (
                  <span style={{ color: '#94A3B8', fontSize: '12px' }}>Original source URL unavailable</span>
                )}
              </div>

              {/* Source Channel & Run */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="drawer-field-group">
                  <span className="drawer-field-label">Discovery Channel</span>
                  <span className="drawer-field-value">{selectedLead.source_platform}</span>
                </div>
                <div className="drawer-field-group">
                  <span className="drawer-field-label">Discovery Run</span>
                  <span className="mono-cell drawer-field-value" style={{ fontSize: '11px' }}>
                    {selectedLead.discovery_run_id || 'manual'}
                  </span>
                </div>
              </div>

              {/* Intelligence Summary if available */}
              {selectedLead.enrichment && selectedLead.enrichment.enrichment_status === 'enriched' && (
                <div className="intel-card" style={{ marginTop: 12 }}>
                  <div className="intel-card-header">
                    <span className="intel-label">AI Lead Intelligence</span>
                    <StatusBadge type="relevance" value={selectedLead.buyer_relevance || 'Unknown'} />
                  </div>
                  {selectedLead.enrichment.buyer_relevance?.reason && (
                    <div className="intel-reason">{selectedLead.enrichment.buyer_relevance.reason}</div>
                  )}
                  {selectedLead.enrichment.public_contact?.phone && (
                    <div style={{ fontSize: 11.5, color: '#334155', marginTop: 4 }}>
                      Phone: <strong>{selectedLead.enrichment.public_contact.phone}</strong>
                    </div>
                  )}
                </div>
              )}

              {/* Operational Status Overrides */}
              <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '14px' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#475569', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Operator Review & Status Overrides
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Validation Status</label>
                    <select
                      className="select"
                      value={drawerStatus}
                      onChange={(e) => setDrawerStatus(e.target.value)}
                    >
                      <option value="Valid">Valid</option>
                      <option value="Review">Review Needed</option>
                      <option value="Missing">Missing Email</option>
                      <option value="Invalid">Invalid Syntax</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">AI Classification</label>
                    <select
                      className="select"
                      value={drawerClassification}
                      onChange={(e) => setDrawerClassification(e.target.value)}
                    >
                      <option value="Business">Business (B2B)</option>
                      <option value="Individual">Individual</option>
                      <option value="Unclassified">Unclassified</option>
                    </select>
                  </div>
                </div>

                {/* Operator Notes Field */}
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Operator Notes & Procurement Insights</label>
                  <textarea
                    className="textarea"
                    rows={4}
                    value={drawerNotes}
                    onChange={(e) => setDrawerNotes(e.target.value)}
                    placeholder="Add notes e.g., Wholesale sound studio interested in 7-metal 432Hz bowls; contact form submitted on 23rd..."
                  />
                </div>
              </div>
            </div>

            <div className="drawer-footer">
              <button
                type="button"
                className="btn btn-sm btn-danger"
                onClick={() => handleDelete(selectedLead)}
              >
                <Trash2 size={12} /> Delete Lead
              </button>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="button" className="btn btn-sm" onClick={closeLeadDrawer}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={handleSaveDrawerLead}
                  disabled={savingLead}
                >
                  <Save size={12} />
                  <span>{savingLead ? 'Saving...' : 'Save Updates'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
