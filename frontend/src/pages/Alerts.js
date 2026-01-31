import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { alertsService, mitigationService } from '../services/api';
import Navbar from '../components/Navbar';

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      const response = await alertsService.list();
      setAlerts(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading alerts:', error);
    }
  };

  const handleResolve = async (alertId) => {
    try {
      await alertsService.resolve(alertId);
      loadAlerts();
    } catch (error) {
      console.error('Error resolving alert:', error);
    }
  };

  const handleMitigate = async (alertId) => {
    try {
      await mitigationService.create({
        alert_id: alertId,
        action_type: 'firewall',
        details: { auto: true }
      });
      alert('Mitigation action created');
      loadAlerts();
    } catch (error) {
      console.error('Error creating mitigation:', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const getSeverityBadge = (severity) => {
    const badges = {
      critical: 'badge-critical',
      high: 'badge-high',
      medium: 'badge-medium',
      low: 'badge-low',
    };
    return badges[severity] || 'badge-low';
  };

  const getStatusBadge = (status) => {
    return status === 'active' ? 'badge-critical' : 'badge-active';
  };

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <h1>Alerts</h1>

        <div className="card">
          {loading ? (
            <div className="spinner"></div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Source IP</th>
                  <th>Target IP</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => (
                  <tr key={alert.id}>
                    <td>{new Date(alert.created_at).toLocaleString()}</td>
                    <td><strong>{alert.alert_type.replace('_', ' ').toUpperCase()}</strong></td>
                    <td>
                      <span className={`badge ${getSeverityBadge(alert.severity)}`}>
                        {alert.severity}
                      </span>
                    </td>
                    <td>{alert.source_ip}</td>
                    <td>{alert.target_ip}</td>
                    <td>{alert.description}</td>
                    <td>
                      <span className={`badge ${getStatusBadge(alert.status)}`}>
                        {alert.status}
                      </span>
                    </td>
                    <td>
                      {alert.status === 'active' && (
                        <>
                          <button
                            className="btn btn-primary"
                            style={{ marginRight: '0.5rem', padding: '0.5rem 1rem' }}
                            onClick={() => handleMitigate(alert.id)}
                          >
                            Mitigate
                          </button>
                          <button
                            className="btn btn-success"
                            style={{ padding: '0.5rem 1rem' }}
                            onClick={() => handleResolve(alert.id)}
                          >
                            Resolve
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!loading && alerts.length === 0 && (
            <p style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No alerts found
            </p>
          )}
        </div>
      </div>
    </>
  );
}

export default Alerts;
