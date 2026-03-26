import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../../components/Navbar';

/**
 * Customer self-service portal — My Protection
 * Read-only view scoped to the customer's own IP prefixes.
 * Uses the /api/v1/customer/ endpoints.
 */
function MyProtection() {
  const [prefixes, setPrefixes] = useState([]);
  const [mitigations, setMitigations] = useState([]);
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

      const [prefixRes, mitigationRes] = await Promise.all([
        fetch('/api/v1/customer/prefixes', { headers }),
        fetch('/api/v1/customer/mitigations', { headers }),
      ]);

      if (prefixRes.status === 401 || mitigationRes.status === 401) {
        navigate('/login');
        return;
      }

      const prefixData = prefixRes.ok ? await prefixRes.json() : [];
      const mitigationData = mitigationRes.ok ? await mitigationRes.json() : [];

      setPrefixes(Array.isArray(prefixData) ? prefixData : []);
      setMitigations(Array.isArray(mitigationData) ? mitigationData : []);
    } catch (err) {
      setError('Failed to load protection data.');
      console.error('MyProtection load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status) => {
    const colours = {
      active: '#28a745',
      resolved: '#6c757d',
      mitigating: '#ffc107',
      escalating: '#dc3545',
    };
    return (
      <span
        style={{
          background: colours[status] || '#6c757d',
          color: '#fff',
          padding: '2px 8px',
          borderRadius: '12px',
          fontSize: '0.75rem',
          textTransform: 'capitalize',
        }}
      >
        {status || 'unknown'}
      </span>
    );
  };

  if (loading) {
    return (
      <div>
        <Navbar />
        <div style={{ padding: '20px' }}>Loading protection data…</div>
      </div>
    );
  }

  return (
    <div>
      <Navbar />
      <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <h1>My Protection</h1>
        <p style={{ color: '#6c757d' }}>
          Read-only view of your protected IP prefixes and active mitigations.
        </p>

        {error && (
          <div style={{ background: '#f8d7da', color: '#721c24', padding: '10px', borderRadius: '4px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {/* Protected Prefixes */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ borderBottom: '2px solid #007bff', paddingBottom: '8px' }}>
            Protected Prefixes ({prefixes.length})
          </h2>
          {prefixes.length === 0 ? (
            <p style={{ color: '#6c757d' }}>No protected prefixes registered. Contact your ISP to add prefixes.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={thStyle}>Prefix</th>
                  <th style={thStyle}>Description</th>
                  <th style={thStyle}>Protection Level</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Added</th>
                </tr>
              </thead>
              <tbody>
                {prefixes.map((p, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={tdStyle}>
                      <code>{p.prefix || p.network || '-'}</code>
                    </td>
                    <td style={tdStyle}>{p.description || '-'}</td>
                    <td style={tdStyle}>{p.protection_level || 'Standard'}</td>
                    <td style={tdStyle}>{statusBadge(p.status || 'active')}</td>
                    <td style={tdStyle}>{p.created_at ? new Date(p.created_at).toLocaleDateString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* Active / Recent Mitigations */}
        <section>
          <h2 style={{ borderBottom: '2px solid #28a745', paddingBottom: '8px' }}>
            Active Mitigations ({mitigations.length})
          </h2>
          {mitigations.length === 0 ? (
            <p style={{ color: '#6c757d' }}>No active mitigations. Your traffic is flowing normally.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={thStyle}>Target IP</th>
                  <th style={thStyle}>Attack Type</th>
                  <th style={thStyle}>Action</th>
                  <th style={thStyle}>State</th>
                  <th style={thStyle}>Started</th>
                </tr>
              </thead>
              <tbody>
                {mitigations.map((m, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={tdStyle}><code>{m.target_ip || '-'}</code></td>
                    <td style={tdStyle}>{m.attack_type || m.action_type || '-'}</td>
                    <td style={tdStyle}>{m.action_type || '-'}</td>
                    <td style={tdStyle}>{statusBadge(m.state || m.status || 'active')}</td>
                    <td style={tdStyle}>{m.created_at ? new Date(m.created_at).toLocaleString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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

export default MyProtection;
