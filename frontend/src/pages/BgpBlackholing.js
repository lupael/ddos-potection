import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { mitigationService, alertsService } from '../services/api';
import Navbar from '../components/Navbar';

function BgpBlackholing() {
  const [activeMitigations, setActiveMitigations] = useState([]);
  const [mitigationHistory, setMitigationHistory] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    alert_id: '',
    prefix: '',
    nexthop: '',
    reason: '',
  });
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      const [activeMitigationsRes, historyRes, analyticsRes, alertsRes] = await Promise.all([
        mitigationService.getActiveStatus(),
        mitigationService.getHistory(24),
        mitigationService.getAnalytics(),
        alertsService.list('active'),
      ]);

      setActiveMitigations(activeMitigationsRes.data.mitigations || []);
      setMitigationHistory(historyRes.data.history || []);
      setAnalytics(analyticsRes.data);
      setAlerts(alertsRes.data || []);
      setLoading(false);
    } catch (error) {
      console.error('Error loading BGP data:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Refresh data every 30 seconds
    // Cleanup function properly stops the interval when component unmounts
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.alert_id || !formData.prefix) {
      alert('Please select an alert and enter a prefix');
      return;
    }

    try {
      // Create mitigation
      const createResponse = await mitigationService.create({
        alert_id: parseInt(formData.alert_id),
        action_type: 'bgp_blackhole',
        details: {
          prefix: formData.prefix,
          nexthop: formData.nexthop || undefined,
          reason: formData.reason || 'Manual BGP blackhole trigger',
        },
      });

      // Execute mitigation
      await mitigationService.execute(createResponse.data.id);

      alert('BGP blackhole announced successfully!');
      setShowForm(false);
      setFormData({
        alert_id: '',
        prefix: '',
        nexthop: '',
        reason: '',
      });
      loadData();
    } catch (error) {
      console.error('Error creating BGP blackhole:', error);
      alert(
        `Failed to announce BGP blackhole: ${
          error.response?.data?.detail || error.message
        }`
      );
    }
  };

  const handleWithdraw = async (mitigationId) => {
    if (
      !window.confirm(
        'Are you sure you want to withdraw this BGP blackhole? Traffic will resume to the target.'
      )
    ) {
      return;
    }

    try {
      await mitigationService.stop(mitigationId);
      alert('BGP blackhole withdrawn successfully!');
      loadData();
    } catch (error) {
      console.error('Error withdrawing BGP blackhole:', error);
      alert(
        `Failed to withdraw BGP blackhole: ${
          error.response?.data?.detail || error.message
        }`
      );
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return hours > 0
      ? `${hours}h ${minutes}m`
      : minutes > 0
      ? `${minutes}m ${secs}s`
      : `${secs}s`;
  };

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem',
          }}
        >
          <div>
            <h1>🛡️ BGP Blackholing (RTBH)</h1>
            <p style={{ color: '#666', marginTop: '0.5rem' }}>
              Remotely Triggered Black Hole - Drop attack traffic at ISP edge
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '➕ Announce Blackhole'}
          </button>
        </div>

        {/* Analytics Cards */}
        {analytics && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
              marginBottom: '2rem',
            }}
          >
            <div className="card">
              <h3
                style={{
                  fontSize: '0.9rem',
                  color: '#666',
                  marginBottom: '0.5rem',
                }}
              >
                Active Blackholes
              </h3>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e74c3c' }}>
                {analytics.active_mitigations}
              </div>
            </div>
            <div className="card">
              <h3
                style={{
                  fontSize: '0.9rem',
                  color: '#666',
                  marginBottom: '0.5rem',
                }}
              >
                Total (24h)
              </h3>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>
                {analytics.total_mitigations}
              </div>
            </div>
            <div className="card">
              <h3
                style={{
                  fontSize: '0.9rem',
                  color: '#666',
                  marginBottom: '0.5rem',
                }}
              >
                Success Rate
              </h3>
              <div
                style={{
                  fontSize: '2rem',
                  fontWeight: 'bold',
                  color:
                    analytics.success_rate_percent > 80 ? '#27ae60' : '#f39c12',
                }}
              >
                {analytics.success_rate_percent}%
              </div>
            </div>
          </div>
        )}

        {/* Announcement Form */}
        {showForm && (
          <div className="card" style={{ marginBottom: '2rem' }}>
            <h2 className="card-title">Announce BGP Blackhole (RTBH)</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>
                  Select Alert <span style={{ color: 'red' }}>*</span>
                </label>
                <select
                  value={formData.alert_id}
                  onChange={(e) =>
                    setFormData({ ...formData, alert_id: e.target.value })
                  }
                  required
                >
                  <option value="">-- Select Alert --</option>
                  {alerts.map((alert) => (
                    <option key={alert.id} value={alert.id}>
                      #{alert.id} - {alert.alert_type} - {alert.target_ip} (
                      {alert.severity})
                    </option>
                  ))}
                </select>
                <small style={{ color: '#666', display: 'block', marginTop: '0.25rem' }}>
                  Choose the alert/attack you want to mitigate
                </small>
              </div>

              <div className="form-group">
                <label>
                  Prefix (CIDR) <span style={{ color: 'red' }}>*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g., 203.0.113.50/32 or 2001:db8::1/128"
                  value={formData.prefix}
                  onChange={(e) =>
                    setFormData({ ...formData, prefix: e.target.value })
                  }
                  required
                />
                <small style={{ color: '#666', display: 'block', marginTop: '0.25rem' }}>
                  IP address or network in CIDR notation. Use /32 for single IPv4
                  or /128 for single IPv6
                </small>
              </div>

              <div className="form-group">
                <label>Next-hop (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g., 192.0.2.1 (leave empty for default)"
                  value={formData.nexthop}
                  onChange={(e) =>
                    setFormData({ ...formData, nexthop: e.target.value })
                  }
                />
                <small style={{ color: '#666', display: 'block', marginTop: '0.25rem' }}>
                  Blackhole next-hop IP (default: 192.0.2.1 from config)
                </small>
              </div>

              <div className="form-group">
                <label>Reason</label>
                <input
                  type="text"
                  placeholder="e.g., DDoS attack - SYN flood"
                  value={formData.reason}
                  onChange={(e) =>
                    setFormData({ ...formData, reason: e.target.value })
                  }
                />
              </div>

              <div
                style={{
                  background: '#fff3cd',
                  border: '1px solid #ffc107',
                  borderRadius: '4px',
                  padding: '1rem',
                  marginBottom: '1rem',
                }}
              >
                <strong>⚠️ Warning:</strong> Announcing a BGP blackhole will drop{' '}
                <strong>ALL</strong> traffic to the specified prefix at your ISP's
                edge. Use /32 for single IPs to minimize impact.
              </div>

              <button type="submit" className="btn btn-primary">
                🚨 Announce Blackhole
              </button>
            </form>
          </div>
        )}

        {/* Active Blackholes */}
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h2 className="card-title">🔴 Active BGP Blackholes</h2>
          {loading ? (
            <div className="spinner"></div>
          ) : activeMitigations.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Prefix</th>
                  <th>Alert Type</th>
                  <th>Severity</th>
                  <th>Target IP</th>
                  <th>Duration</th>
                  <th>Started</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeMitigations.map((mitigation) => (
                  <tr key={mitigation.id}>
                    <td>#{mitigation.id}</td>
                    <td>
                      <code style={{ background: '#f8f9fa', padding: '0.25rem 0.5rem' }}>
                        {mitigation.details?.prefix || 'N/A'}
                      </code>
                    </td>
                    <td>{mitigation.alert?.type || 'N/A'}</td>
                    <td>
                      <span
                        className={`badge badge-${
                          mitigation.alert?.severity || 'low'
                        }`}
                      >
                        {mitigation.alert?.severity || 'N/A'}
                      </span>
                    </td>
                    <td>{mitigation.alert?.target_ip || 'N/A'}</td>
                    <td>{formatDuration(mitigation.duration_seconds)}</td>
                    <td>
                      {new Date(mitigation.created_at).toLocaleString()}
                    </td>
                    <td>
                      <button
                        className="btn btn-success"
                        style={{ padding: '0.5rem 1rem' }}
                        onClick={() => handleWithdraw(mitigation.id)}
                      >
                        Withdraw
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p
              style={{ textAlign: 'center', padding: '2rem', color: '#666' }}
            >
              No active BGP blackholes. All routes are normal.
            </p>
          )}
        </div>

        {/* Mitigation History */}
        <div className="card">
          <h2 className="card-title">📊 BGP Blackhole History (Last 24h)</h2>
          {loading ? (
            <div className="spinner"></div>
          ) : mitigationHistory.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Alert Type</th>
                  <th>Target IP</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Started</th>
                  <th>Completed</th>
                </tr>
              </thead>
              <tbody>
                {mitigationHistory
                  .filter((m) => m.action_type === 'bgp_blackhole')
                  .map((mitigation) => (
                    <tr key={mitigation.id}>
                      <td>#{mitigation.id}</td>
                      <td>{mitigation.alert?.type || 'N/A'}</td>
                      <td>{mitigation.alert?.target_ip || 'N/A'}</td>
                      <td>
                        <span
                          className={`badge ${
                            mitigation.status === 'completed'
                              ? 'badge-active'
                              : mitigation.status === 'failed'
                              ? 'badge-critical'
                              : 'badge-medium'
                          }`}
                        >
                          {mitigation.status}
                        </span>
                      </td>
                      <td>
                        {mitigation.duration_seconds
                          ? formatDuration(mitigation.duration_seconds)
                          : 'N/A'}
                      </td>
                      <td>
                        {new Date(mitigation.created_at).toLocaleString()}
                      </td>
                      <td>
                        {mitigation.completed_at
                          ? new Date(mitigation.completed_at).toLocaleString()
                          : 'N/A'}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          ) : (
            <p
              style={{ textAlign: 'center', padding: '2rem', color: '#666' }}
            >
              No BGP blackhole history in the last 24 hours
            </p>
          )}
        </div>

        {/* Information Card */}
        <div
          className="card"
          style={{ marginTop: '2rem', background: '#e3f2fd' }}
        >
          <h3 style={{ marginBottom: '1rem' }}>ℹ️ About BGP Blackholing</h3>
          <p style={{ marginBottom: '0.5rem' }}>
            <strong>BGP Blackholing (RTBH)</strong> is a DDoS mitigation
            technique that drops traffic at your ISP's edge routers before it
            reaches your network.
          </p>
          <ul style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
            <li>
              <strong>Fast:</strong> Near-instant mitigation (1-5 seconds)
            </li>
            <li>
              <strong>Bandwidth-saving:</strong> Stops attack traffic upstream
            </li>
            <li>
              <strong>Standard:</strong> Uses RFC 7999 blackhole community
              (65535:666)
            </li>
            <li>
              <strong>Automated:</strong> Can be triggered by detection systems
            </li>
          </ul>
          <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#666' }}>
            📖 For detailed setup instructions, see the{' '}
            <a
              href="https://github.com/i4edubd/ddos-protection/blob/main/docs/BGP-RTBH.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              BGP-RTBH Documentation
            </a>
          </p>
        </div>
      </div>
    </>
  );
}

export default BgpBlackholing;
