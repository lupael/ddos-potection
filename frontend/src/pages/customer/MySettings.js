import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../../components/Navbar';

/**
 * Customer self-service portal — My Settings
 * Manage notification preferences and whitelisted IPs for the customer's account.
 */
function MySettings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const navigate = useNavigate();

  // Local state for editable fields
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [telegramEnabled, setTelegramEnabled] = useState(false);
  const [slackEnabled, setSlackEnabled] = useState(false);
  const [notifyEmail, setNotifyEmail] = useState('');
  const [whitelistIPs, setWhitelistIPs] = useState('');
  const [alertThreshold, setAlertThreshold] = useState('medium');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/v1/customer/settings', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        navigate('/login');
        return;
      }
      const data = res.ok ? await res.json() : {};
      setSettings(data);

      // Populate form fields from fetched settings
      setEmailEnabled(data.email_notifications !== false);
      setSmsEnabled(!!data.sms_notifications);
      setTelegramEnabled(!!data.telegram_notifications);
      setSlackEnabled(!!data.slack_notifications);
      setNotifyEmail(data.notification_email || '');
      setWhitelistIPs(
        Array.isArray(data.whitelisted_ips) ? data.whitelisted_ips.join('\n') : (data.whitelisted_ips || '')
      );
      setAlertThreshold(data.alert_threshold || 'medium');
    } catch (err) {
      setError('Failed to load settings.');
      console.error('MySettings load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    const ips = whitelistIPs
      .split(/[\n,]+/)
      .map((ip) => ip.trim())
      .filter(Boolean);

    // Basic client-side validation: each entry must be a valid IPv4/IPv6 address or CIDR
    const ipCidrPattern =
      /^((\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?|([\da-fA-F:]+)(\/\d{1,3})?)$/;
    const invalid = ips.filter((ip) => !ipCidrPattern.test(ip));
    if (invalid.length > 0) {
      setError(`Invalid IP/CIDR entries: ${invalid.join(', ')}`);
      setSaving(false);
      return;
    }

    const payload = {
      email_notifications: emailEnabled,
      sms_notifications: smsEnabled,
      telegram_notifications: telegramEnabled,
      slack_notifications: slackEnabled,
      notification_email: notifyEmail,
      whitelisted_ips: ips,
      alert_threshold: alertThreshold,
    };

    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/v1/customer/settings', {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      if (res.status === 401) {
        navigate('/login');
        return;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Save failed');
      }
      setSuccessMsg('Settings saved successfully.');
    } catch (err) {
      setError(err.message || 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div>
        <Navbar />
        <div style={{ padding: '20px' }}>Loading settings…</div>
      </div>
    );
  }

  return (
    <div>
      <Navbar />
      <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        <h1>My Settings</h1>
        <p style={{ color: '#6c757d' }}>
          Manage your notification preferences and IP whitelist.
        </p>

        {error && (
          <div style={{ background: '#f8d7da', color: '#721c24', padding: '10px', borderRadius: '4px', marginBottom: '16px' }}>
            {error}
          </div>
        )}
        {successMsg && (
          <div style={{ background: '#d4edda', color: '#155724', padding: '10px', borderRadius: '4px', marginBottom: '16px' }}>
            {successMsg}
          </div>
        )}

        <form onSubmit={handleSave}>
          {/* Notification channels */}
          <section style={sectionStyle}>
            <h2 style={sectionHeaderStyle}>Notification Channels</h2>

            <div style={rowStyle}>
              <label style={labelStyle}>
                <input
                  type="checkbox"
                  checked={emailEnabled}
                  onChange={(e) => setEmailEnabled(e.target.checked)}
                  style={{ marginRight: '8px' }}
                />
                Email notifications
              </label>
            </div>
            {emailEnabled && (
              <div style={{ marginLeft: '24px', marginBottom: '12px' }}>
                <label style={{ display: 'block', marginBottom: '4px', color: '#6c757d', fontSize: '0.9rem' }}>
                  Notification email address
                </label>
                <input
                  type="email"
                  value={notifyEmail}
                  onChange={(e) => setNotifyEmail(e.target.value)}
                  placeholder="alerts@example.com"
                  style={inputStyle}
                />
              </div>
            )}

            <div style={rowStyle}>
              <label style={labelStyle}>
                <input
                  type="checkbox"
                  checked={smsEnabled}
                  onChange={(e) => setSmsEnabled(e.target.checked)}
                  style={{ marginRight: '8px' }}
                />
                SMS notifications (Twilio)
              </label>
            </div>

            <div style={rowStyle}>
              <label style={labelStyle}>
                <input
                  type="checkbox"
                  checked={telegramEnabled}
                  onChange={(e) => setTelegramEnabled(e.target.checked)}
                  style={{ marginRight: '8px' }}
                />
                Telegram notifications
              </label>
            </div>

            <div style={rowStyle}>
              <label style={labelStyle}>
                <input
                  type="checkbox"
                  checked={slackEnabled}
                  onChange={(e) => setSlackEnabled(e.target.checked)}
                  style={{ marginRight: '8px' }}
                />
                Slack notifications
              </label>
            </div>
          </section>

          {/* Alert threshold */}
          <section style={sectionStyle}>
            <h2 style={sectionHeaderStyle}>Alert Threshold</h2>
            <p style={{ color: '#6c757d', fontSize: '0.9rem', marginBottom: '8px' }}>
              Only send notifications for alerts at or above this severity level.
            </p>
            <select
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(e.target.value)}
              style={{ ...inputStyle, width: '200px' }}
            >
              <option value="low">Low (all alerts)</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical only</option>
            </select>
          </section>

          {/* IP Whitelist */}
          <section style={sectionStyle}>
            <h2 style={sectionHeaderStyle}>IP Whitelist</h2>
            <p style={{ color: '#6c757d', fontSize: '0.9rem', marginBottom: '8px' }}>
              Traffic from these IPs/CIDRs will never trigger alerts for your prefixes.
              Enter one IP or CIDR per line.
            </p>
            <textarea
              value={whitelistIPs}
              onChange={(e) => setWhitelistIPs(e.target.value)}
              placeholder={'192.168.1.1\n10.0.0.0/8'}
              rows={6}
              style={{ ...inputStyle, fontFamily: 'monospace', resize: 'vertical' }}
            />
          </section>

          <button
            type="submit"
            disabled={saving}
            style={{
              padding: '10px 24px',
              background: '#007bff',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
        </form>
      </div>
    </div>
  );
}

const sectionStyle = {
  marginBottom: '28px',
  padding: '16px',
  border: '1px solid #dee2e6',
  borderRadius: '8px',
};

const sectionHeaderStyle = {
  marginTop: 0,
  marginBottom: '12px',
  fontSize: '1.1rem',
  borderBottom: '1px solid #dee2e6',
  paddingBottom: '8px',
};

const rowStyle = {
  marginBottom: '10px',
};

const labelStyle = {
  display: 'flex',
  alignItems: 'center',
  cursor: 'pointer',
};

const inputStyle = {
  width: '100%',
  padding: '8px 10px',
  border: '1px solid #ced4da',
  borderRadius: '4px',
  fontSize: '0.95rem',
  boxSizing: 'border-box',
};

export default MySettings;
