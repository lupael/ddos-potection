import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { captureService } from '../services/api';
import Navbar from '../components/Navbar';

function PacketCapture() {
  const [captures, setCaptures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showStartForm, setShowStartForm] = useState(false);
  const navigate = useNavigate();
  
  // Form state
  const [captureForm, setCaptureForm] = useState({
    interface: 'eth0',
    capture_mode: 'af_packet',
    duration: 60,
    filter_bpf: '',
    target_ip: ''
  });

  useEffect(() => {
    loadCaptures();
    const interval = setInterval(loadCaptures, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadCaptures = async () => {
    try {
      const response = await captureService.list();
      setCaptures(response.data.captures || []);
      setLoading(false);
    } catch (err) {
      console.error('Error loading captures:', err);
      setError(err.response?.data?.detail || 'Failed to load captures');
      setLoading(false);
    }
  };

  const handleStartCapture = async (e) => {
    e.preventDefault();
    setError(null);
    
    try {
      const response = await captureService.start(captureForm);
      alert(`Capture started: ${response.data.capture_id}`);
      setShowStartForm(false);
      loadCaptures();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start capture');
    }
  };

  const handleDownload = async (filename) => {
    try {
      const response = await captureService.download(filename);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to download PCAP');
    }
  };

  const handleCleanup = async () => {
    if (!window.confirm('Delete old PCAP files (older than 7 days)?')) return;
    
    try {
      const response = await captureService.cleanup(7);
      alert(`Deleted ${response.data.deleted} old files`);
      loadCaptures();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to cleanup');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="page">
      <Navbar onLogout={handleLogout} />
      <div className="content">
        <div className="header">
          <h2>📦 Packet Capture</h2>
          <div>
            <button 
              onClick={() => setShowStartForm(!showStartForm)}
              className="btn btn-primary"
              style={{ marginRight: '10px' }}
            >
              {showStartForm ? 'Cancel' : '▶️ Start Capture'}
            </button>
            <button 
              onClick={handleCleanup}
              className="btn btn-secondary"
            >
              🗑️ Cleanup Old Files
            </button>
          </div>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {showStartForm && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3>Start New Capture</h3>
            <form onSubmit={handleStartCapture}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Interface:</label>
                  <input
                    type="text"
                    value={captureForm.interface}
                    onChange={(e) => setCaptureForm({...captureForm, interface: e.target.value})}
                    placeholder="eth0"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Capture Mode:</label>
                  <select
                    value={captureForm.capture_mode}
                    onChange={(e) => setCaptureForm({...captureForm, capture_mode: e.target.value})}
                  >
                    <option value="pcap">PCAP (Standard)</option>
                    <option value="af_packet">AF_PACKET (High Performance)</option>
                    <option value="af_xdp">AF_XDP (Ultra Performance)</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Duration (seconds):</label>
                  <input
                    type="number"
                    value={captureForm.duration}
                    onChange={(e) => {
                      const rawValue = e.target.value;
                      const parsed = parseInt(rawValue, 10);
                      if (Number.isNaN(parsed)) {
                        // Ignore non-numeric input to avoid storing NaN in state
                        return;
                      }
                      const clamped = Math.min(3600, Math.max(10, parsed));
                      setCaptureForm({ ...captureForm, duration: clamped });
                    }}
                    min="10"
                    max="3600"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>BPF Filter (optional):</label>
                  <input
                    type="text"
                    value={captureForm.filter_bpf}
                    onChange={(e) => setCaptureForm({...captureForm, filter_bpf: e.target.value})}
                    placeholder="tcp and port 80"
                  />
                </div>
                
                <div className="form-group">
                  <label>Target IP (optional):</label>
                  <input
                    type="text"
                    value={captureForm.target_ip}
                    onChange={(e) => setCaptureForm({...captureForm, target_ip: e.target.value})}
                    placeholder="192.168.1.100"
                  />
                </div>
              </div>
              
              <button type="submit" className="btn btn-primary">
                Start Capture
              </button>
            </form>
          </div>
        )}

        {loading ? (
          <div className="loading">Loading captures...</div>
        ) : (
          <div className="card">
            <h3>PCAP Files ({captures.length})</h3>
            
            {captures.length === 0 ? (
              <p style={{ textAlign: 'center', color: '#666', padding: '20px' }}>
                No captures found. Start a new capture to begin recording traffic.
              </p>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Filename</th>
                      <th>Size</th>
                      <th>Created</th>
                      <th>Modified</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {captures.map((capture) => (
                      <tr key={capture.filename}>
                        <td>
                          <code style={{ fontSize: '0.9em' }}>{capture.filename}</code>
                        </td>
                        <td>{formatBytes(capture.size_bytes)}</td>
                        <td>{formatDate(capture.created)}</td>
                        <td>{formatDate(capture.modified)}</td>
                        <td>
                          <button
                            onClick={() => handleDownload(capture.filename)}
                            className="btn btn-small btn-primary"
                            style={{ marginRight: '5px' }}
                          >
                            ⬇️ Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div className="info-card" style={{ marginTop: '20px' }}>
          <h4>ℹ️ About Packet Capture</h4>
          <ul>
            <li><strong>PCAP:</strong> Standard capture with BPF filtering (works everywhere)</li>
            <li><strong>AF_PACKET:</strong> High-performance raw socket capture (Linux only)</li>
            <li><strong>AF_XDP:</strong> Ultra-high-performance with XDP (requires Linux 4.18+)</li>
            <li><strong>VLAN Untagging:</strong> Automatically removes 802.1Q and 802.1ad tags</li>
            <li><strong>Attack Fingerprints:</strong> Automatically captured during detected attacks</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default PacketCapture;
