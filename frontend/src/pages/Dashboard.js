import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { trafficService, alertsService } from '../services/api';
import Navbar from '../components/Navbar';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

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
    const interval = setInterval(loadDashboardData, 10000); // Refresh every 10 seconds
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
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <>
        <Navbar onLogout={handleLogout} />
        <div className="container">
          <div className="spinner"></div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <h1 style={{ marginBottom: '2rem' }}>Dashboard</h1>

        {/* Stats Overview */}
        <div className="grid">
          <div className="stat-card">
            <h3>Total Packets (5 min)</h3>
            <p>{stats.total_packets.toLocaleString()}</p>
          </div>
          <div className="stat-card">
            <h3>Total Traffic (5 min)</h3>
            <p>{formatBytes(stats.total_bytes)}</p>
          </div>
          <div className="stat-card">
            <h3>Active Flows</h3>
            <p>{stats.total_flows.toLocaleString()}</p>
          </div>
          <div className={`stat-card ${alertSummary.by_status?.active > 0 ? 'critical' : 'success'}`}>
            <h3>Active Alerts</h3>
            <p>{alertSummary.by_status?.active || 0}</p>
          </div>
        </div>

        {/* Alert Summary */}
        <div className="grid-2">
          <div className="card">
            <h2 className="card-title">Alert Status</h2>
            <table className="table">
              <tbody>
                <tr>
                  <td>Active</td>
                  <td><strong>{alertSummary.by_status?.active || 0}</strong></td>
                </tr>
                <tr>
                  <td>Mitigated</td>
                  <td>{alertSummary.by_status?.mitigated || 0}</td>
                </tr>
                <tr>
                  <td>Resolved</td>
                  <td>{alertSummary.by_status?.resolved || 0}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="card">
            <h2 className="card-title">Alert Severity</h2>
            <table className="table">
              <tbody>
                <tr>
                  <td>Critical</td>
                  <td><span className="badge badge-critical">{alertSummary.by_severity?.critical || 0}</span></td>
                </tr>
                <tr>
                  <td>High</td>
                  <td><span className="badge badge-high">{alertSummary.by_severity?.high || 0}</span></td>
                </tr>
                <tr>
                  <td>Medium</td>
                  <td><span className="badge badge-medium">{alertSummary.by_severity?.medium || 0}</span></td>
                </tr>
                <tr>
                  <td>Low</td>
                  <td><span className="badge badge-low">{alertSummary.by_severity?.low || 0}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h2 className="card-title">Quick Actions</h2>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <Link to="/alerts">
              <button className="btn btn-primary">View Alerts</button>
            </Link>
            <Link to="/rules">
              <button className="btn btn-primary">Manage Rules</button>
            </Link>
            <Link to="/traffic">
              <button className="btn btn-primary">Traffic Monitor</button>
            </Link>
            <Link to="/reports">
              <button className="btn btn-primary">Generate Report</button>
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
