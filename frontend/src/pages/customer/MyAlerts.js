import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../../components/Navbar';

/**
 * Customer self-service portal — My Alerts
 * Read-only feed of DDoS alerts affecting the customer's own prefixes.
 */
function MyAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all' | 'open' | 'resolved'
  const navigate = useNavigate();

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/v1/customer/alerts', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        navigate('/login');
        return;
      }
      const data = res.ok ? await res.json() : [];
      setAlerts(Array.isArray(data) ? data : []);
    } catch (err) {
      setError('Failed to load alerts.');
      console.error('MyAlerts load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const severityColour = (severity) => {
    const map = { critical: '#dc3545', high: '#fd7e14', medium: '#ffc107', low: '#28a745' };
    return map[severity?.toLowerCase()] || '#6c757d';
  };

  const filtered = alerts.filter((a) => {
    if (filter === 'open') return !a.resolved;
    if (filter === 'resolved') return a.resolved;
    return true;
  });

  if (loading) {
    return (
      <div>
        <Navbar />
        <div style={{ padding: '20px' }}>Loading alerts…</div>
      </div>
    );
  }

  return (
    <div>
      <Navbar />
      <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <h1>My Alerts</h1>
        <p style={{ color: '#6c757d' }}>
          DDoS alerts affecting your protected IP prefixes (read-only).
        </p>

        {error && (
          <div style={{ background: '#f8d7da', color: '#721c24', padding: '10px', borderRadius: '4px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {/* Filter bar */}
        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
          {['all', 'open', 'resolved'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 16px',
                borderRadius: '4px',
                border: '1px solid #dee2e6',
                background: filter === f ? '#007bff' : '#fff',
                color: filter === f ? '#fff' : '#333',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {f}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', alignSelf: 'center', color: '#6c757d' }}>
            {filtered.length} alert{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>

        {filtered.length === 0 ? (
          <p style={{ color: '#6c757d' }}>No alerts to display.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f8f9fa' }}>
                <th style={thStyle}>Severity</th>
                <th style={thStyle}>Attack Type</th>
                <th style={thStyle}>Target IP</th>
                <th style={thStyle}>Packets/s</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Detected At</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #dee2e6' }}>
                  <td style={tdStyle}>
                    <span
                      style={{
                        background: severityColour(a.severity),
                        color: '#fff',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        textTransform: 'capitalize',
                      }}
                    >
                      {a.severity || 'info'}
                    </span>
                  </td>
                  <td style={tdStyle}>{a.attack_type || '-'}</td>
                  <td style={tdStyle}><code>{a.target_ip || a.source_ip || '-'}</code></td>
                  <td style={tdStyle}>{a.packets_per_second ? a.packets_per_second.toLocaleString() : '-'}</td>
                  <td style={tdStyle}>
                    {a.resolved ? (
                      <span style={{ color: '#28a745' }}>✓ Resolved</span>
                    ) : (
                      <span style={{ color: '#dc3545' }}>● Open</span>
                    )}
                  </td>
                  <td style={tdStyle}>
                    {a.created_at ? new Date(a.created_at).toLocaleString() : '-'}
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

export default MyAlerts;
