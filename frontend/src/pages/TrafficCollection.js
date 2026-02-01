import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import api from '../services/api';

function TrafficCollection() {
  const [status, setStatus] = useState(null);
  const [routers, setRouters] = useState([]);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [statusRes, routersRes, configRes] = await Promise.all([
        api.get('/traffic-collection/status'),
        api.get('/traffic-collection/routers'),
        api.get('/traffic-collection/config')
      ]);
      
      setStatus(statusRes.data);
      setRouters(routersRes.data.routers || []);
      setConfig(configRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading traffic collection data:', error);
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
      }
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Never';
    return new Date(timestamp).toLocaleString();
  };

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <h1>Traffic Collection & Detection</h1>
        
        {loading ? (
          <div className="spinner"></div>
        ) : (
          <>
            {/* Collection Status */}
            <div className="card">
              <h2 className="card-title">Collection Status</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
                {status && (
                  <>
                    <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>NetFlow</h3>
                      <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        <div>Status: <span className="badge badge-low">Active</span></div>
                        <div>Port: {status.netflow.port}</div>
                        <div>Versions: {status.netflow.version.join(', ')}</div>
                      </div>
                    </div>
                    
                    <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>sFlow</h3>
                      <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        <div>Status: <span className="badge badge-low">Active</span></div>
                        <div>Port: {status.sflow.port}</div>
                        <div>Version: {status.sflow.version}</div>
                      </div>
                    </div>
                    
                    <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>IPFIX</h3>
                      <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        <div>Status: <span className="badge badge-low">Active</span></div>
                        <div>Port: {status.ipfix.port}</div>
                        <div>RFC: {status.ipfix.rfc}</div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Detection Configuration */}
            {config && (
              <div className="card">
                <h2 className="card-title">Detection Thresholds</h2>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Detection Type</th>
                      <th>Threshold</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>SYN Flood</strong></td>
                      <td>{config.syn_flood_threshold.toLocaleString()} pps</td>
                      <td>Packets per second to single destination</td>
                    </tr>
                    <tr>
                      <td><strong>UDP Flood</strong></td>
                      <td>{config.udp_flood_threshold.toLocaleString()} ppm</td>
                      <td>Packets per minute to single destination</td>
                    </tr>
                    <tr>
                      <td><strong>ICMP Flood</strong></td>
                      <td>{config.icmp_flood_threshold.toLocaleString()} ppm</td>
                      <td>ICMP packets per minute</td>
                    </tr>
                    <tr>
                      <td><strong>DNS Amplification</strong></td>
                      <td>{config.dns_amplification_threshold} bytes/packet</td>
                      <td>Byte-to-packet ratio threshold</td>
                    </tr>
                    <tr>
                      <td><strong>Entropy Analysis</strong></td>
                      <td>{config.entropy_threshold}</td>
                      <td>Shannon entropy threshold</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}

            {/* Router Detection */}
            <div className="card">
              <h2 className="card-title">Detected Routers ({routers.length})</h2>
              {routers.length === 0 ? (
                <p style={{ textAlign: 'center', color: '#666', padding: '2rem' }}>
                  No routers detected yet. Configure your routers to send NetFlow/sFlow/IPFIX data.
                </p>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Router IP</th>
                      <th>Vendor</th>
                      <th>Flow Count</th>
                      <th>Last Seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {routers.map((router, idx) => (
                      <tr key={idx}>
                        <td><strong>{router.ip}</strong></td>
                        <td>{router.vendor}</td>
                        <td>{router.flow_count.toLocaleString()}</td>
                        <td>{formatTimestamp(router.last_seen)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Configuration Instructions */}
            <div className="card">
              <h2 className="card-title">Router Configuration Examples</h2>
              <div style={{ fontSize: '0.9rem' }}>
                <h3 style={{ fontSize: '1rem', marginTop: '1rem' }}>MikroTik (NetFlow v9)</h3>
                <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px', overflow: 'auto' }}>
{`/ip traffic-flow
set enabled=yes interfaces=all
/ip traffic-flow target
add address=<collector-ip>:2055 version=9`}
                </pre>

                <h3 style={{ fontSize: '1rem', marginTop: '1rem' }}>Cisco (NetFlow v9)</h3>
                <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px', overflow: 'auto' }}>
{`flow exporter DDOS-COLLECTOR
  destination <collector-ip>
  transport udp 2055
  
flow monitor DDOS-MONITOR
  record netflow ipv4 original-input
  exporter DDOS-COLLECTOR`}
                </pre>

                <h3 style={{ fontSize: '1rem', marginTop: '1rem' }}>Juniper (sFlow)</h3>
                <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px', overflow: 'auto' }}>
{`protocols {
    sflow {
        collector <collector-ip> udp-port 6343;
        interfaces all;
        sample-rate 1000;
    }
}`}
                </pre>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default TrafficCollection;
