import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import api from '../services/api';

function AnomalyDetection() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const response = await api.get('/traffic-collection/detection/stats');
      setStats(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading detection stats:', error);
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

  const getDetectionInfo = (type) => {
    const info = {
      syn_flood: {
        name: 'SYN Flood Detection',
        description: 'Detects TCP SYN flood attacks by monitoring SYN packets per second to specific destinations',
        method: 'Redis-based real-time SYN packet counting with sliding window analysis',
        severity: 'Critical'
      },
      udp_flood: {
        name: 'UDP Flood Detection',
        description: 'Monitors UDP packet rate per destination over 60-second windows',
        method: 'Protocol-based traffic aggregation and per-destination packet rate monitoring',
        severity: 'High'
      },
      icmp_flood: {
        name: 'ICMP Flood Detection',
        description: 'Tracks ICMP protocol traffic and identifies excessive ping/echo requests',
        method: 'ICMP protocol monitoring with per-destination rate limiting',
        severity: 'Medium'
      },
      dns_amplification: {
        name: 'DNS Amplification Detection',
        description: 'Identifies DNS amplification attacks through byte-to-packet ratio analysis',
        method: 'Detects large DNS responses (>500 bytes/packet) indicating reflection attacks',
        severity: 'High'
      },
      distributed_ddos: {
        name: 'Distributed DDoS Detection',
        description: 'Uses entropy analysis to detect coordinated attacks from multiple sources',
        method: 'Multi-dimensional entropy: Low source + Low destination entropy',
        severity: 'Critical'
      },
      volumetric_attack: {
        name: 'Volumetric Attack Detection',
        description: 'Identifies large-scale attacks with high volume from many sources',
        method: 'Multi-dimensional entropy: High source + Low destination entropy',
        severity: 'High'
      }
    };
    return info[type] || { name: type, description: 'Unknown', method: 'Unknown', severity: 'Unknown' };
  };

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <h1>Anomaly Detection Engine</h1>

        {loading ? (
          <div className="spinner"></div>
        ) : (
          <>
            {/* Detection Overview */}
            <div className="card">
              <h2 className="card-title">Detection Statistics (Last 24 Hours)</h2>
              {stats && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                  <div style={{ textAlign: 'center', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#dc3545' }}>
                      {stats.detection_types.syn_flood}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>SYN Floods</div>
                  </div>
                  
                  <div style={{ textAlign: 'center', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#fd7e14' }}>
                      {stats.detection_types.udp_flood}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>UDP Floods</div>
                  </div>
                  
                  <div style={{ textAlign: 'center', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ffc107' }}>
                      {stats.detection_types.icmp_flood}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>ICMP Floods</div>
                  </div>
                  
                  <div style={{ textAlign: 'center', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#17a2b8' }}>
                      {stats.detection_types.dns_amplification}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>DNS Amplification</div>
                  </div>
                  
                  <div style={{ textAlign: 'center', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#dc3545' }}>
                      {stats.detection_types.distributed_ddos}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>Distributed DDoS</div>
                  </div>
                  
                  <div style={{ textAlign: 'center', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#fd7e14' }}>
                      {stats.detection_types.volumetric_attack}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>Volumetric Attacks</div>
                  </div>
                </div>
              )}
            </div>

            {/* Detection Methods */}
            <div className="card">
              <h2 className="card-title">Detection Methods</h2>
              <div style={{ display: 'grid', gap: '1rem' }}>
                {stats && Object.keys(stats.detection_types).map((type) => {
                  const info = getDetectionInfo(type);
                  const count = stats.detection_types[type];
                  
                  return (
                    <div 
                      key={type}
                      style={{ 
                        padding: '1rem', 
                        border: '1px solid #dee2e6', 
                        borderRadius: '8px',
                        background: count > 0 ? '#fff3cd' : 'white'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <div style={{ flex: 1 }}>
                          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem' }}>
                            {info.name}
                            <span 
                              className={`badge ${
                                info.severity === 'Critical' ? 'badge-critical' :
                                info.severity === 'High' ? 'badge-high' :
                                info.severity === 'Medium' ? 'badge-medium' : 'badge-low'
                              }`}
                              style={{ marginLeft: '0.5rem', fontSize: '0.8rem' }}
                            >
                              {info.severity}
                            </span>
                          </h3>
                          <p style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#666' }}>
                            {info.description}
                          </p>
                          <div style={{ fontSize: '0.85rem', color: '#999' }}>
                            <strong>Method:</strong> {info.method}
                          </div>
                        </div>
                        <div style={{ 
                          minWidth: '80px', 
                          textAlign: 'right',
                          fontSize: '1.5rem',
                          fontWeight: 'bold',
                          color: count > 0 ? '#dc3545' : '#28a745'
                        }}>
                          {count}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Real-time Monitoring */}
            <div className="card">
              <h2 className="card-title">Real-time Monitoring Features</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
                <div style={{ padding: '1rem', background: '#e7f3ff', borderRadius: '8px', borderLeft: '4px solid #007bff' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>🔄 Sliding Windows</h4>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                    10-second windows for SYN floods, 60-second windows for UDP/ICMP detection
                  </p>
                </div>
                
                <div style={{ padding: '1rem', background: '#e7f3ff', borderRadius: '8px', borderLeft: '4px solid #007bff' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>📊 Redis Streams</h4>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                    Real-time flow data streaming with automatic trimming (max 10,000 entries)
                  </p>
                </div>
                
                <div style={{ padding: '1rem', background: '#e7f3ff', borderRadius: '8px', borderLeft: '4px solid #007bff' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>🔔 Pub/Sub Alerts</h4>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                    Instant alert notifications through Redis pub/sub channels
                  </p>
                </div>
                
                <div style={{ padding: '1rem', background: '#e7f3ff', borderRadius: '8px', borderLeft: '4px solid #007bff' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>🎯 Deduplication</h4>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                    5-minute alert deduplication prevents alert flooding
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default AnomalyDetection;
