import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { trafficService, alertsService } from '../services/api';
import Navbar from '../components/Navbar';

function Dashboard() {
  const [stats, setStats] = useState({
    total_packets: 0,
    total_bytes: 0,
    total_flows: 0,
  });
  const [alertSummary, setAlertSummary] = useState({
    by_status: {},
    by_severity: {},
  });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const [trafficRes, alertRes] = await Promise.all([
        trafficService.getRealtime(),
        alertsService.getSummary(),
      ]);
      setStats(trafficRes.data);
      setAlertSummary(alertRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
  };

  const activeAlerts  = alertSummary.by_status?.active    || 0;
  const criticalCount = alertSummary.by_severity?.critical || 0;

  if (loading) {
    return (
      <>
        <Navbar onLogout={handleLogout} />
        <div className="container">
          <div className="spinner" />
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">

        {/* Page header */}
        <div className="page-header">
          <div>
            <h1>Operations Dashboard</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Real-time network protection overview · auto-refreshes every 10 s
            </p>
          </div>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.375rem',
            background: 'var(--color-green-50)', color: 'var(--color-green-700)',
            border: '1px solid #a7f3d0', borderRadius: '999px',
            padding: '0.375rem 0.875rem', fontSize: '0.8125rem', fontWeight: 600,
          }}>
            <span className="status-dot green" /> Protection Active
          </span>
        </div>

        {/* ── KPI row ── */}
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))' }}>

          <div className="stat-card info">
            <div className="stat-card-header">
              <h3>Packets (5 min)</h3>
              <div className="stat-card-icon blue">📦</div>
            </div>
            <p>{stats.total_packets.toLocaleString()}</p>
            <div className="stat-card-trend">
              <span>📊</span> Last 5-minute window
            </div>
          </div>

          <div className="stat-card info">
            <div className="stat-card-header">
              <h3>Traffic Volume (5 min)</h3>
              <div className="stat-card-icon blue">📶</div>
            </div>
            <p>{formatBytes(stats.total_bytes)}</p>
            <div className="stat-card-trend">
              <span>📊</span> Bytes transferred
            </div>
          </div>

          <div className="stat-card success">
            <div className="stat-card-header">
              <h3>Active Flows</h3>
              <div className="stat-card-icon green">🔀</div>
            </div>
            <p>{stats.total_flows.toLocaleString()}</p>
            <div className="stat-card-trend">
              <span>✅</span> Tracked connections
            </div>
          </div>

          <div className={`stat-card ${activeAlerts > 0 ? 'critical' : 'success'}`}>
            <div className="stat-card-header">
              <h3>Active Alerts</h3>
              <div className={`stat-card-icon ${activeAlerts > 0 ? 'red' : 'green'}`}>
                {activeAlerts > 0 ? '🚨' : '✅'}
              </div>
            </div>
            <p>{activeAlerts}</p>
            <div className={`stat-card-trend ${activeAlerts > 0 ? 'down' : 'up'}`}>
              {activeAlerts > 0
                ? <><span>⚠️</span> Requires attention</>
                : <><span>✅</span> All clear</>}
            </div>
          </div>

          <div className={`stat-card ${criticalCount > 0 ? 'critical' : 'info'}`}>
            <div className="stat-card-header">
              <h3>Critical Threats</h3>
              <div className={`stat-card-icon ${criticalCount > 0 ? 'red' : 'purple'}`}>
                {criticalCount > 0 ? '🔥' : '🛡️'}
              </div>
            </div>
            <p>{criticalCount}</p>
            <div className={`stat-card-trend ${criticalCount > 0 ? 'down' : ''}`}>
              {criticalCount > 0
                ? <><span>🔥</span> Critical severity</>
                : <><span>🛡️</span> No critical alerts</>}
            </div>
          </div>

        </div>

        {/* ── Alert summary ── */}
        <div className="grid-2">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">🚦 Alert Status Breakdown</h2>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Count</th>
                  <th>Indicator</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <span className="status-dot red" style={{ marginRight: '0.5rem' }} />
                    Active
                  </td>
                  <td><strong>{alertSummary.by_status?.active || 0}</strong></td>
                  <td>
                    <span className="badge badge-critical">
                      {alertSummary.by_status?.active || 0}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <span className="status-dot blue" style={{ marginRight: '0.5rem' }} />
                    Mitigated
                  </td>
                  <td>{alertSummary.by_status?.mitigated || 0}</td>
                  <td>
                    <span className="badge badge-mitigated">
                      {alertSummary.by_status?.mitigated || 0}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <span className="status-dot green" style={{ marginRight: '0.5rem' }} />
                    Resolved
                  </td>
                  <td>{alertSummary.by_status?.resolved || 0}</td>
                  <td>
                    <span className="badge badge-resolved">
                      {alertSummary.by_status?.resolved || 0}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title">⚡ Alert Severity Distribution</h2>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Count</th>
                  <th>Badge</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { key: 'critical', label: '🔴 Critical', cls: 'badge-critical' },
                  { key: 'high',     label: '🟠 High',     cls: 'badge-high' },
                  { key: 'medium',   label: '🟡 Medium',   cls: 'badge-medium' },
                  { key: 'low',      label: '🟢 Low',      cls: 'badge-low' },
                ].map(({ key, label, cls }) => (
                  <tr key={key}>
                    <td>{label}</td>
                    <td>{alertSummary.by_severity?.[key] || 0}</td>
                    <td>
                      <span className={`badge ${cls}`}>
                        {alertSummary.by_severity?.[key] || 0}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Quick actions ── */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">⚡ Quick Actions</h2>
          </div>
          <div className="quick-actions">
            <Link to="/alerts">
              <button className="btn btn-primary">🚨 View Alerts</button>
            </Link>
            <Link to="/rules">
              <button className="btn btn-secondary">📋 Manage Rules</button>
            </Link>
            <Link to="/traffic">
              <button className="btn btn-secondary">📡 Traffic Monitor</button>
            </Link>
            <Link to="/bgp-blackholing">
              <button className="btn btn-secondary">🌐 BGP / RTBH</button>
            </Link>
            <Link to="/capture">
              <button className="btn btn-secondary">🔬 Packet Capture</button>
            </Link>
            <Link to="/reports">
              <button className="btn btn-outline">📄 Generate Report</button>
            </Link>
          </div>
        </div>

        {/* ── System status ── */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">🖥️ System Status</h2>
          </div>
          <div className="grid-3" style={{ marginBottom: 0 }}>
            {[
              { icon: '🛡️', label: 'Protection Engine',  status: 'Operational', color: 'green' },
              { icon: '📡', label: 'Flow Collector',      status: 'Operational', color: 'green' },
              { icon: '��', label: 'Anomaly Detector',    status: 'Operational', color: 'green' },
              { icon: '🌐', label: 'BGP Integration',     status: 'Operational', color: 'green' },
              { icon: '📊', label: 'Metrics Pipeline',    status: 'Operational', color: 'green' },
              { icon: '🔔', label: 'Alert Engine',        status: activeAlerts > 0 ? 'Active Alerts' : 'Operational', color: activeAlerts > 0 ? 'red' : 'green' },
            ].map((item) => (
              <div key={item.label} style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                padding: '0.875rem 1rem',
                background: 'var(--color-navy-50)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-default)',
              }}>
                <span style={{ fontSize: '1.25rem' }}>{item.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {item.label}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginTop: '0.2rem' }}>
                    <span className={`status-dot ${item.color}`} />
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{item.status}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </>
  );
}

export default Dashboard;
