import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { hostgroupService } from '../services/api';
import Navbar from '../components/Navbar';

function Hostgroups() {
  const [hostgroups, setHostgroups] = useState([]);
  const [defaults, setDefaults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showCheckIp, setShowCheckIp] = useState(false);
  const [checkIpResult, setCheckIpResult] = useState(null);
  const navigate = useNavigate();
  
  // Form state
  const [hostgroupForm, setHostgroupForm] = useState({
    name: '',
    subnet: '',
    packets_per_second: 10000,
    bytes_per_second: 100000000,
    flows_per_second: 1000,
    block_script: '',
    notify_script: ''
  });
  
  const [checkIpForm, setCheckIpForm] = useState({
    ip: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [groupsRes, defaultsRes] = await Promise.all([
        hostgroupService.list(),
        hostgroupService.getDefaults()
      ]);
      setHostgroups(groupsRes.data.hostgroups || []);
      setDefaults(defaultsRes.data.default_thresholds || {});
      setLoading(false);
    } catch (err) {
      console.error('Error loading hostgroups:', err);
      setError(err.response?.data?.detail || 'Failed to load hostgroups');
      setLoading(false);
    }
  };

  const handleCreateHostgroup = async (e) => {
    e.preventDefault();
    setError(null);
    
    // Basic client-side validation for numeric thresholds
    const packetsPerSecond = parseInt(hostgroupForm.packets_per_second, 10);
    const bytesPerSecond = parseInt(hostgroupForm.bytes_per_second, 10);
    const flowsPerSecond = parseInt(hostgroupForm.flows_per_second, 10);

    if (
      Number.isNaN(packetsPerSecond) ||
      Number.isNaN(bytesPerSecond) ||
      Number.isNaN(flowsPerSecond)
    ) {
      setError('Please enter valid numeric values for all threshold fields.');
      return;
    }
    
    try {
      const payload = {
        name: hostgroupForm.name,
        subnet: hostgroupForm.subnet,
        thresholds: {
          packets_per_second: packetsPerSecond,
          bytes_per_second: bytesPerSecond,
          flows_per_second: flowsPerSecond
        },
        scripts: {}
      };
      
      if (hostgroupForm.block_script) {
        payload.scripts.block = hostgroupForm.block_script;
      }
      if (hostgroupForm.notify_script) {
        payload.scripts.notify = hostgroupForm.notify_script;
      }
      
      await hostgroupService.create(payload);
      alert(`Hostgroup "${hostgroupForm.name}" created successfully`);
      setShowCreateForm(false);
      setHostgroupForm({
        name: '',
        subnet: '',
        packets_per_second: 10000,
        bytes_per_second: 100000000,
        flows_per_second: 1000,
        block_script: '',
        notify_script: ''
      });
      loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create hostgroup');
    }
  };

  const handleDeleteHostgroup = async (name) => {
    if (!window.confirm(`Delete hostgroup "${name}"?`)) return;
    
    try {
      await hostgroupService.delete(name);
      alert('Hostgroup deleted');
      loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete hostgroup');
    }
  };

  const handleCheckIp = async (e) => {
    e.preventDefault();
    setError(null);
    
    try {
      const response = await hostgroupService.checkIp(checkIpForm.ip);
      setCheckIpResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to check IP');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const formatNumber = (num) => {
    return num.toLocaleString();
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="page">
      <Navbar onLogout={handleLogout} />
      <div className="content">
        <div className="header">
          <h2>🎯 Hostgroups & Thresholds</h2>
          <div>
            <button 
              onClick={() => setShowCheckIp(!showCheckIp)}
              className="btn btn-secondary"
              style={{ marginRight: '10px' }}
            >
              {showCheckIp ? 'Hide' : '🔍 Check IP'}
            </button>
            <button 
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="btn btn-primary"
            >
              {showCreateForm ? 'Cancel' : '➕ Create Hostgroup'}
            </button>
          </div>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {showCheckIp && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3>Check IP Thresholds</h3>
            <form onSubmit={handleCheckIp}>
              <div className="form-group">
                <label>IP Address:</label>
                <input
                  type="text"
                  value={checkIpForm.ip}
                  onChange={(e) => setCheckIpForm({ip: e.target.value})}
                  placeholder="192.168.1.50"
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">
                Check Thresholds
              </button>
            </form>
            
            {checkIpResult && (
              <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                <h4>Result for {checkIpResult.ip}</h4>
                {checkIpResult.hostgroup ? (
                  <div>
                    <p><strong>Hostgroup:</strong> {checkIpResult.hostgroup.name}</p>
                    <p><strong>Subnet:</strong> {checkIpResult.hostgroup.subnet}</p>
                  </div>
                ) : (
                  <p><strong>Hostgroup:</strong> Default (no specific match)</p>
                )}
                <h5 style={{ marginTop: '15px' }}>Applied Thresholds:</h5>
                <ul>
                  <li>Packets/sec: {formatNumber(checkIpResult.thresholds.packets_per_second)}</li>
                  <li>Bytes/sec: {formatBytes(checkIpResult.thresholds.bytes_per_second)}/s</li>
                  <li>Flows/sec: {formatNumber(checkIpResult.thresholds.flows_per_second)}</li>
                </ul>
              </div>
            )}
          </div>
        )}

        {showCreateForm && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3>Create New Hostgroup</h3>
            <form onSubmit={handleCreateHostgroup}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Name:</label>
                  <input
                    type="text"
                    value={hostgroupForm.name}
                    onChange={(e) => setHostgroupForm({...hostgroupForm, name: e.target.value})}
                    placeholder="customer_network_1"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Subnet (CIDR):</label>
                  <input
                    type="text"
                    value={hostgroupForm.subnet}
                    onChange={(e) => setHostgroupForm({...hostgroupForm, subnet: e.target.value})}
                    placeholder="192.168.1.0/24"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Packets/Second Threshold:</label>
                  <input
                    type="number"
                    value={hostgroupForm.packets_per_second}
                    onChange={(e) => setHostgroupForm({...hostgroupForm, packets_per_second: e.target.value})}
                    min="100"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Bytes/Second Threshold:</label>
                  <input
                    type="number"
                    value={hostgroupForm.bytes_per_second}
                    onChange={(e) => setHostgroupForm({...hostgroupForm, bytes_per_second: e.target.value})}
                    min="1000"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Flows/Second Threshold:</label>
                  <input
                    type="number"
                    value={hostgroupForm.flows_per_second}
                    onChange={(e) => setHostgroupForm({...hostgroupForm, flows_per_second: e.target.value})}
                    min="10"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Block Script (optional):</label>
                  <input
                    type="text"
                    value={hostgroupForm.block_script}
                    onChange={(e) => setHostgroupForm({...hostgroupForm, block_script: e.target.value})}
                    placeholder="/etc/ddos-protection/scripts/block.sh"
                  />
                </div>
                
                <div className="form-group">
                  <label>Notify Script (optional):</label>
                  <input
                    type="text"
                    value={hostgroupForm.notify_script}
                    onChange={(e) => setHostgroupForm({...hostgroupForm, notify_script: e.target.value})}
                    placeholder="/etc/ddos-protection/scripts/notify.sh"
                  />
                </div>
              </div>
              
              <button type="submit" className="btn btn-primary">
                Create Hostgroup
              </button>
            </form>
          </div>
        )}

        {loading ? (
          <div className="loading">Loading hostgroups...</div>
        ) : (
          <>
            <div className="card" style={{ marginBottom: '20px' }}>
              <h3>Default Thresholds</h3>
              <p style={{ color: '#666', marginBottom: '15px' }}>
                Applied to IPs that don't match any hostgroup
              </p>
              {defaults && (
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-value">{formatNumber(defaults.packets_per_second)}</div>
                    <div className="stat-label">Packets/Second</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{formatBytes(defaults.bytes_per_second)}/s</div>
                    <div className="stat-label">Bytes/Second</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{formatNumber(defaults.flows_per_second)}</div>
                    <div className="stat-label">Flows/Second</div>
                  </div>
                </div>
              )}
            </div>

            <div className="card">
              <h3>Configured Hostgroups ({hostgroups.length})</h3>
              
              {hostgroups.length === 0 ? (
                <p style={{ textAlign: 'center', color: '#666', padding: '20px' }}>
                  No hostgroups configured. Create a hostgroup to set custom thresholds for specific subnets.
                </p>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Subnet</th>
                        <th>Packets/sec</th>
                        <th>Bytes/sec</th>
                        <th>Flows/sec</th>
                        <th>Scripts</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {hostgroups.map((group) => (
                        <tr key={group.name}>
                          <td><strong>{group.name}</strong></td>
                          <td><code>{group.subnet}</code></td>
                          <td>{formatNumber(group.thresholds.packets_per_second)}</td>
                          <td>{formatBytes(group.thresholds.bytes_per_second)}/s</td>
                          <td>{formatNumber(group.thresholds.flows_per_second)}</td>
                          <td>
                            {group.scripts && (Object.keys(group.scripts).length > 0) ? (
                              <span>
                                {group.scripts.block && '🚫 Block '}
                                {group.scripts.notify && '📧 Notify'}
                              </span>
                            ) : (
                              <span style={{ color: '#999' }}>None</span>
                            )}
                          </td>
                          <td>
                            <button
                              onClick={() => handleDeleteHostgroup(group.name)}
                              className="btn btn-small btn-danger"
                            >
                              🗑️ Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        <div className="info-card" style={{ marginTop: '20px' }}>
          <h4>ℹ️ About Hostgroups</h4>
          <ul>
            <li><strong>Per-Subnet Thresholds:</strong> Configure different rate limits for different networks</li>
            <li><strong>Longest Prefix Match:</strong> Most specific subnet takes precedence</li>
            <li><strong>Script Execution:</strong> Custom block/notify scripts triggered on threshold violations</li>
            <li><strong>Default Fallback:</strong> IPs without specific hostgroups use system defaults</li>
            <li><strong>Redis Persistence:</strong> Configuration survives service restarts</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Hostgroups;
