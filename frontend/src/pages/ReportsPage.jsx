import React from 'react';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import {
  Download,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Percent,
  Calendar,
  ShieldCheck
} from 'lucide-react';

export default function ReportsPage({ stats, reports }) {
  const logs = reports?.recent_activity || [];

  return (
    <div>
      {/* Action / Export Banner */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '6px',
          padding: '14px 18px',
          marginBottom: '20px',
        }}
      >
        <div>
          <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#0F172A' }}>
            Operational Export Audit & Campaign Reports
          </h2>
          <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
            Comprehensive delivery tracking, de-duplication logs, and full dataset export
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <a href="/download-dispatch-log" className="btn btn-secondary">
            <Download size={13} />
            <span>Dispatch Log CSV</span>
          </a>
          <a href="/download-suppression-list" className="btn btn-secondary">
            <Download size={13} />
            <span>Suppression List CSV</span>
          </a>
          <a href="/download-report" className="btn btn-primary">
            <Download size={13} />
            <span>Master Leads Report</span>
          </a>
        </div>
      </div>


      {/* Metrics Row */}
      <div className="metrics-grid">
        <MetricCard
          label="Total Deliveries"
          value={stats?.successful_deliveries || 0}
          subtext="Confirmed SMTP 250 OK"
          icon={CheckCircle2}
        />
        <MetricCard
          label="Failed Attempts"
          value={stats?.failed_sends || 0}
          subtext="Connection or syntax failure"
          icon={XCircle}
        />
        <MetricCard
          label="Duplicates Blocked"
          value={stats?.duplicates_skipped || 0}
          subtext="De-duplication safety"
          icon={RotateCcw}
        />
        <MetricCard
          label="Overall Delivery Rate"
          value={`${stats?.success_rate || 0}%`}
          subtext="Deliveries / total attempts"
          icon={Percent}
        />
      </div>

      {/* Full Audit Log Table */}
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Outreach Delivery Audit Trail (data/sent_log.csv)</h2>
            <p className="panel-description">
              Exact timestamped record of every outbound communication attempt
            </p>
          </div>
          <span style={{ fontSize: '11px', color: '#64748B' }}>
            {logs.length} Recent Log Entries
          </span>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          {logs.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: '#64748B' }}>
              No delivery records found in sent_log.csv.
            </div>
          ) : (
            <div className="table-container" style={{ border: 'none' }}>
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Recipient Email</th>
                    <th>Status</th>
                    <th>Subject Line</th>
                    <th>Error Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, idx) => (
                    <tr key={idx}>
                      <td className="mono-cell" style={{ color: '#64748B', whiteSpace: 'nowrap' }}>
                        {log.timestamp || '-'}
                      </td>
                      <td className="mono-cell" style={{ fontWeight: 500 }}>
                        {log.email}
                      </td>
                      <td>
                        <StatusBadge type="outreach" value={log.status} />
                      </td>
                      <td style={{ color: '#475569', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.campaign_subject || '-'}
                      </td>
                      <td style={{ color: '#DC2626', fontSize: '11.5px' }}>
                        {log.error_message || '-'}
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
