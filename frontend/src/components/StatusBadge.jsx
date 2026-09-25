import React from 'react';

export default function StatusBadge({ type, value }) {
  if (value === undefined || value === null) return null;

  const valStr = String(value).trim();
  const valLower = valStr.toLowerCase();

  let badgeClass = 'badge';

  if (type === 'validation') {
    if (valLower === 'valid') badgeClass += ' badge-valid';
    else if (valLower === 'review' || valLower === 'questionable') badgeClass += ' badge-warn';
    else if (valLower === 'missing') badgeClass += ' badge-missing';
    else badgeClass += ' badge-error';
  } else if (type === 'classification') {
    if (valLower === 'business') badgeClass += ' badge-business';
    else if (valLower === 'individual') badgeClass += ' badge-individual';
    else badgeClass += ' badge-unclassified';
  } else if (type === 'outreach') {
    if (valLower === 'sent' || valLower === 'delivered') badgeClass += ' badge-valid';
    else if (valLower === 'failed') badgeClass += ' badge-error';
    else if (valLower === 'skipped' || valLower === 'queued') badgeClass += ' badge-warn';
    else badgeClass += ' badge-unclassified';
  } else if (type === 'datatype') {
    if (valLower === 'true' || valLower === 'demo') {
      return <span className="badge badge-demo">Demo Data</span>;
    } else {
      return <span className="badge badge-real">Real Lead</span>;
    }
  } else if (type === 'relevance') {
    if (valLower === 'high') badgeClass += ' badge-high';
    else if (valLower === 'medium') badgeClass += ' badge-medium';
    else if (valLower === 'low') badgeClass += ' badge-low';
    else badgeClass += ' badge-unknown';
  } else if (type === 'enrichment') {
    if (valLower === 'enriched') badgeClass += ' badge-valid';
    else if (valLower === 'needs_enrichment') badgeClass += ' badge-warn';
    else if (valLower === 'blocked') badgeClass += ' badge-error';
    else if (valLower === 'failed') badgeClass += ' badge-error';
    else badgeClass += ' badge-unclassified';
  } else if (type === 'role') {
    badgeClass += ' badge-role';
  } else if (type === 'draft_status') {
    if (valLower === 'approved') badgeClass += ' badge-valid';
    else if (valLower === 'edited') badgeClass += ' badge-business';
    else if (valLower === 'needs review' || valLower === 'needs_review') badgeClass += ' badge-warn';
    else if (valLower === 'rejected') badgeClass += ' badge-error';
    else if (valLower === 'archived') badgeClass += ' badge-missing';
    else badgeClass += ' badge-unclassified';
  } else if (type === 'campaign_status') {
    if (valLower === 'approved') badgeClass += ' badge-valid';
    else if (valLower === 'partially approved' || valLower === 'partially_approved') badgeClass += ' badge-business';
    else if (valLower === 'review' || valLower === 'generating drafts' || valLower === 'generating_drafts') badgeClass += ' badge-warn';
    else if (valLower === 'archived') badgeClass += ' badge-missing';
    else badgeClass += ' badge-unclassified';
  }

  return <span className={badgeClass}>{valStr}</span>;
}
