import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { trafficService } from '../services/api';
import Navbar from '../components/Navbar';

function TrafficMonitor() {
  const [protocols, setProtocols] = useState([]);
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadTrafficData();
    const interval = setInterval(loadTrafficData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadTrafficData = async () => {
    try {
      const [protocolRes, statsRes] = await Promise.all([
        trafficService.getProtocols(),
        trafficService.getStats(50),
      ]);
      setProtocols(protocolRes.data.protocols);
      setStats(statsRes.data.logs);
      setLoading(false);
    } catch (error) {
      console.error('Error loading traffic data:', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <h1>Traffic Monitor</h1>

        <div className="card">
          <h2 className="card-title">Protocol Distribution</h2>
          {loading ? (
            <div className="spinner"></div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Protocol</th>
                  <th>Flow Count</th>
                  <th>Total Bytes</th>
                </tr>
              </thead>
              <tbody>
                {protocols.map((p, idx) => (
                  <tr key={idx}>
                    <td><strong>{p.protocol}</strong></td>
                    <td>{p.count.toLocaleString()}</td>
                    <td>{formatBytes(p.bytes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h2 className="card-title">Recent Traffic Logs</h2>
          {loading ? (
            <div className="spinner"></div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Source IP</th>
                  <th>Destination IP</th>
                  <th>Protocol</th>
                  <th>Packets</th>
                  <th>Bytes</th>
                  <th>Anomaly</th>
                </tr>
              </thead>
              <tbody>
                {stats.map((log, idx) => (
                  <tr key={idx}>
                    <td>{new Date(log.timestamp).toLocaleTimeString()}</td>
                    <td>{log.source_ip}</td>
                    <td>{log.dest_ip}</td>
                    <td>{log.protocol}</td>
                    <td>{log.packets.toLocaleString()}</td>
                    <td>{formatBytes(log.bytes)}</td>
                    <td>
                      {log.is_anomaly ? (
                        <span className="badge badge-critical">Yes</span>
                      ) : (
                        <span className="badge badge-low">No</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

export default TrafficMonitor;
