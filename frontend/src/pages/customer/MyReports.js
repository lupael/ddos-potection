import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../../components/Navbar';

/** Maximum number of SLA records to display in the table. */
const MAX_DISPLAYED_SLA_RECORDS = 20;

/**
 * Customer self-service portal — My Reports
 * Read-only view of reports generated for the customer's account.
 */
function MyReports() {
  const [reports, setReports] = useState([]);
  const [slaRecords, setSlaRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [reportRes, slaRes] = await Promise.all([
        fetch('/api/v1/customer/reports', { headers }),
        fetch('/api/v1/customer/sla', { headers }),
      ]);

      if (reportRes.status === 401) {
        navigate('/login');
        return;
      }

      const reportData = reportRes.ok ? await reportRes.json() : [];
      const slaData = slaRes.ok ? await slaRes.json() : [];

      setReports(Array.isArray(reportData) ? reportData : []);
      setSlaRecords(Array.isArray(slaData) ? slaData : []);
    } catch (err) {
      setError('Failed to load reports.');
      console.error('MyReports load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (reportId, fmt) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`/api/v1/reports/${reportId}/download?format=${fmt}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      alert('Download failed.');
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${reportId}.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatDuration = (seconds) => {
    if (seconds == null) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  if (loading) {
    return (
      <div>
        <Navbar />
        <div style={{ padding: '20px' }}>Loading reports…</div>
      </div>
    );
  }

  return (
    <div>
      <Navbar />
      <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <h1>My Reports</h1>
        <p style={{ color: '#6c757d' }}>
          Download historical attack reports and review SLA performance metrics.
        </p>

        {error && (
          <div style={{ background: '#f8d7da', color: '#721c24', padding: '10px', borderRadius: '4px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {/* Reports table */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ borderBottom: '2px solid #007bff', paddingBottom: '8px' }}>
            Attack Reports ({reports.length})
          </h2>
          {reports.length === 0 ? (
            <p style={{ color: '#6c757d' }}>No reports available yet.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={thStyle}>Title</th>
                  <th style={thStyle}>Period</th>
                  <th style={thStyle}>Generated</th>
                  <th style={thStyle}>Download</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={tdStyle}>{r.title || r.report_type || `Report #${r.id}`}</td>
                    <td style={tdStyle}>
                      {r.start_date && r.end_date
                        ? `${new Date(r.start_date).toLocaleDateString()} – ${new Date(r.end_date).toLocaleDateString()}`
                        : '-'}
                    </td>
                    <td style={tdStyle}>
                      {r.created_at ? new Date(r.created_at).toLocaleString() : '-'}
                    </td>
                    <td style={tdStyle}>
                      {['pdf', 'csv'].map((fmt) => (
                        <button
                          key={fmt}
                          onClick={() => handleDownload(r.id, fmt)}
                          style={{
                            marginRight: '4px',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            border: '1px solid #dee2e6',
                            background: '#fff',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            textTransform: 'uppercase',
                          }}
                        >
                          {fmt}
                        </button>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* SLA Performance */}
        <section>
          <h2 style={{ borderBottom: '2px solid #28a745', paddingBottom: '8px' }}>
            SLA Performance ({slaRecords.length} incidents)
          </h2>
          {slaRecords.length === 0 ? (
            <p style={{ color: '#6c757d' }}>No SLA records found.</p>
          ) : (
            <>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
                {[
                  {
                    label: 'Avg. Time-to-Detect',
                    value: formatDuration(
                      slaRecords.reduce((s, r) => s + (r.time_to_detect || 0), 0) / slaRecords.length
                    ),
                    colour: '#007bff',
                  },
                  {
                    label: 'Avg. Time-to-Mitigate',
                    value: formatDuration(
                      slaRecords.reduce((s, r) => s + (r.time_to_mitigate || 0), 0) / slaRecords.length
                    ),
                    colour: '#28a745',
                  },
                  {
                    label: 'SLA Breaches',
                    value: slaRecords.filter((r) => r.sla_breached).length,
                    colour: '#dc3545',
                  },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    style={{
                      flex: '1',
                      minWidth: '160px',
                      padding: '16px',
                      borderRadius: '8px',
                      border: `2px solid ${stat.colour}`,
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ fontSize: '1.6rem', fontWeight: '700', color: stat.colour }}>
                      {stat.value}
                    </div>
                    <div style={{ color: '#6c757d', fontSize: '0.85rem' }}>{stat.label}</div>
                  </div>
                ))}
              </div>

              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8f9fa' }}>
                    <th style={thStyle}>Alert ID</th>
                    <th style={thStyle}>TTD</th>
                    <th style={thStyle}>TTM</th>
                    <th style={thStyle}>SLA Tier</th>
                    <th style={thStyle}>Breached</th>
                    <th style={thStyle}>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {slaRecords.slice(0, MAX_DISPLAYED_SLA_RECORDS).map((r, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={tdStyle}>{r.alert_id || '-'}</td>
                      <td style={tdStyle}>{formatDuration(r.time_to_detect)}</td>
                      <td style={tdStyle}>{formatDuration(r.time_to_mitigate)}</td>
                      <td style={tdStyle}>{r.sla_tier || 'Standard'}</td>
                      <td style={tdStyle}>
                        {r.sla_breached ? (
                          <span style={{ color: '#dc3545' }}>✗ Yes</span>
                        ) : (
                          <span style={{ color: '#28a745' }}>✓ No</span>
                        )}
                      </td>
                      <td style={tdStyle}>
                        {r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {slaRecords.length > MAX_DISPLAYED_SLA_RECORDS && (
                <p style={{ color: '#6c757d', marginTop: '8px', fontSize: '0.85rem' }}>
                  Showing {MAX_DISPLAYED_SLA_RECORDS} of {slaRecords.length} records.
                </p>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

const thStyle = {
  padding: '10px 12px',
  textAlign: 'left',
  fontWeight: '600',
  borderBottom: '2px solid #dee2e6',
};

const tdStyle = {
  padding: '10px 12px',
  verticalAlign: 'middle',
};

export default MyReports;
