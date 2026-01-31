import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ispService } from '../services/api';
import Navbar from '../components/Navbar';

function Settings() {
  const [isp, setIsp] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await ispService.getMe();
      setIsp(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const handleRegenerateApiKey = async () => {
    if (window.confirm('Are you sure you want to regenerate the API key? This will invalidate the current key.')) {
      try {
        const response = await ispService.regenerateApiKey();
        alert('API key regenerated successfully');
        loadSettings();
      } catch (error) {
        console.error('Error regenerating API key:', error);
        alert('Error regenerating API key');
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
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
        <h1>Settings</h1>

        <div className="card">
          <h2 className="card-title">ISP Information</h2>
          <div style={{ marginBottom: '1rem' }}>
            <strong>Name:</strong> {isp.name}
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <strong>Email:</strong> {isp.email}
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <strong>Subscription Status:</strong>{' '}
            <span className={`badge ${isp.subscription_status === 'active' ? 'badge-active' : 'badge-medium'}`}>
              {isp.subscription_status}
            </span>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <strong>Plan:</strong> {isp.subscription_plan.toUpperCase()}
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">API Configuration</h2>
          <div style={{ marginBottom: '1rem' }}>
            <strong>API Key:</strong>
            <div style={{
              background: '#f8f9fa',
              padding: '1rem',
              borderRadius: '6px',
              marginTop: '0.5rem',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              wordBreak: 'break-all'
            }}>
              {isp.api_key}
            </div>
          </div>
          <button className="btn btn-danger" onClick={handleRegenerateApiKey}>
            Regenerate API Key
          </button>
          <p style={{ marginTop: '0.5rem', color: '#666', fontSize: '0.875rem' }}>
            Warning: Regenerating the API key will invalidate all existing integrations using the current key.
          </p>
        </div>

        <div className="card">
          <h2 className="card-title">Detection Thresholds</h2>
          <div className="form-group">
            <label>SYN Flood Threshold (packets/sec)</label>
            <input type="number" defaultValue="10000" />
          </div>
          <div className="form-group">
            <label>UDP Flood Threshold (packets/sec)</label>
            <input type="number" defaultValue="50000" />
          </div>
          <div className="form-group">
            <label>Auto-Mitigation</label>
            <select defaultValue="enabled">
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
          <button className="btn btn-primary">Save Settings</button>
        </div>

        <div className="card">
          <h2 className="card-title">Notification Settings</h2>
          <div className="form-group">
            <label>Alert Email</label>
            <input type="email" placeholder="admin@example.com" />
          </div>
          <div className="form-group">
            <label>Telegram Bot Token</label>
            <input type="text" placeholder="Your bot token" />
          </div>
          <div className="form-group">
            <label>Telegram Chat ID</label>
            <input type="text" placeholder="Chat ID" />
          </div>
          <button className="btn btn-primary">Save Notifications</button>
        </div>
      </div>
    </>
  );
}

export default Settings;
