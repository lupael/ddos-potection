import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import api from '../services/api';

function EntropyAnalysis() {
  const [entropy, setEntropy] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadEntropy();
    const interval = setInterval(loadEntropy, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadEntropy = async () => {
    try {
      const response = await api.get('/traffic-collection/entropy');
      setEntropy(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading entropy data:', error);
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

  const getEntropyLevel = (value) => {
    if (value < 2) return { level: 'Very Low', color: '#dc3545' };
    if (value < 4) return { level: 'Low', color: '#ffc107' };
    if (value < 6) return { level: 'Medium', color: '#17a2b8' };
    if (value < 8) return { level: 'High', color: '#28a745' };
    return { level: 'Very High', color: '#007bff' };
  };

  const getAttackPatternInfo = (pattern) => {
    const patterns = {
      normal: {
        name: 'Normal Traffic',
        description: 'Traffic patterns appear normal with good distribution',
        severity: 'none',
        color: '#28a745',
        icon: '✅'
      },
      distributed_ddos: {
        name: 'Distributed DDoS',
        description: 'Low source entropy + Low destination entropy indicates few sources attacking single target',
        severity: 'critical',
        color: '#dc3545',
        icon: '🚨'
      },
      volumetric_attack: {
        name: 'Volumetric Attack',
        description: 'High source entropy + Low destination entropy indicates many sources attacking few targets',
        severity: 'high',
        color: '#fd7e14',
        icon: '⚠️'
      },
      scanning: {
        name: 'Scanning Activity',
        description: 'High entropy across dimensions suggests reconnaissance or port scanning',
        severity: 'medium',
        color: '#ffc107',
        icon: '🔍'
      }
    };
    return patterns[pattern] || patterns.normal;
  };

  const EntropyMeter = ({ value, label, threshold }) => {
    const level = getEntropyLevel(value);
    const percentage = Math.min((value / 10) * 100, 100);
    
    return (
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontWeight: 'bold' }}>{label}</span>
          <span style={{ color: level.color, fontWeight: 'bold' }}>
            {value.toFixed(2)} ({level.level})
          </span>
        </div>
        <div style={{ 
          width: '100%', 
          height: '24px', 
          background: '#e9ecef', 
          borderRadius: '12px',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div style={{ 
            width: `${percentage}%`, 
            height: '100%', 
            background: level.color,
            transition: 'width 0.3s ease',
            borderRadius: '12px'
          }}></div>
          {threshold && (
            <div style={{
              position: 'absolute',
              left: `${(threshold / 10) * 100}%`,
              top: 0,
              bottom: 0,
              width: '2px',
              background: '#000',
              opacity: 0.5
            }}>
              <div style={{
                position: 'absolute',
                top: '-20px',
                left: '-20px',
                fontSize: '0.7rem',
                whiteSpace: 'nowrap'
              }}>
                Threshold
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <h1>Entropy Analysis</h1>

        {loading ? (
          <div className="spinner"></div>
        ) : entropy ? (
          <>
            {/* Attack Pattern Detection */}
            {entropy.attack_pattern && (
              <div className="card">
                <h2 className="card-title">Current Traffic Pattern</h2>
                {(() => {
                  const pattern = getAttackPatternInfo(entropy.attack_pattern);
                  return (
                    <div style={{ 
                      padding: '1.5rem', 
                      background: pattern.severity === 'none' ? '#d4edda' : 
                                 pattern.severity === 'critical' ? '#f8d7da' :
                                 pattern.severity === 'high' ? '#fff3cd' : '#d1ecf1',
                      borderRadius: '8px',
                      border: `2px solid ${pattern.color}`
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ fontSize: '3rem' }}>{pattern.icon}</div>
                        <div style={{ flex: 1 }}>
                          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.5rem', color: pattern.color }}>
                            {pattern.name}
                          </h3>
                          <p style={{ margin: 0, fontSize: '1rem' }}>
                            {pattern.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Multi-dimensional Entropy */}
            <div className="card">
              <h2 className="card-title">Multi-dimensional Entropy Analysis</h2>
              <div style={{ padding: '1rem' }}>
                <EntropyMeter 
                  value={entropy.source_entropy} 
                  label="Source IP Entropy"
                  threshold={entropy.threshold}
                />
                <EntropyMeter 
                  value={entropy.destination_entropy} 
                  label="Destination IP Entropy"
                  threshold={entropy.threshold}
                />
                <EntropyMeter 
                  value={entropy.protocol_entropy} 
                  label="Protocol Entropy"
                />
                
                <div style={{ 
                  marginTop: '1.5rem', 
                  padding: '1rem', 
                  background: '#f8f9fa', 
                  borderRadius: '8px',
                  fontSize: '0.9rem'
                }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div>
                      <strong>Sample Size:</strong> {entropy.sample_size.toLocaleString()} flows
                    </div>
                    <div>
                      <strong>Detection Threshold:</strong> {entropy.threshold}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Entropy Explanation */}
            <div className="card">
              <h2 className="card-title">Understanding Shannon Entropy</h2>
              <div style={{ fontSize: '0.95rem', lineHeight: '1.6' }}>
                <p>
                  Shannon entropy measures the randomness or distribution in data. In network traffic analysis:
                </p>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', margin: '1rem 0' }}>
                  <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <h4 style={{ margin: '0 0 0.5rem', color: '#dc3545' }}>Low Entropy (&lt; 2)</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>
                      Concentrated traffic from few sources or to few destinations. Typical in targeted attacks.
                    </p>
                  </div>
                  
                  <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <h4 style={{ margin: '0 0 0.5rem', color: '#17a2b8' }}>Medium Entropy (2-6)</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>
                      Moderate distribution. Could be normal traffic or early-stage attack.
                    </p>
                  </div>
                  
                  <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                    <h4 style={{ margin: '0 0 0.5rem', color: '#28a745' }}>High Entropy (&gt; 6)</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>
                      Well-distributed traffic across many IPs. Can indicate normal traffic or botnet activity.
                    </p>
                  </div>
                </div>

                <h3 style={{ fontSize: '1.1rem', marginTop: '1.5rem' }}>Attack Pattern Recognition</h3>
                <table className="table" style={{ marginTop: '1rem' }}>
                  <thead>
                    <tr>
                      <th>Pattern</th>
                      <th>Source Entropy</th>
                      <th>Destination Entropy</th>
                      <th>Indication</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>Distributed DDoS</strong></td>
                      <td>Low (&lt; 3.5)</td>
                      <td>Very Low (&lt; 1.0)</td>
                      <td>Few sources attacking single target</td>
                    </tr>
                    <tr>
                      <td><strong>Volumetric Attack</strong></td>
                      <td>High (&gt; 5.0)</td>
                      <td>Low (&lt; 2.0)</td>
                      <td>Many sources attacking few targets (botnet)</td>
                    </tr>
                    <tr>
                      <td><strong>Scanning</strong></td>
                      <td>High (&gt; 4.0)</td>
                      <td>High (&gt; 4.0)</td>
                      <td>Reconnaissance, port scanning activity</td>
                    </tr>
                    <tr>
                      <td><strong>Normal Traffic</strong></td>
                      <td>Medium (3-6)</td>
                      <td>Medium (3-6)</td>
                      <td>Typical enterprise network patterns</td>
                    </tr>
                  </tbody>
                </table>

                <div style={{ 
                  marginTop: '1.5rem', 
                  padding: '1rem', 
                  background: '#e7f3ff', 
                  borderRadius: '8px',
                  borderLeft: '4px solid #007bff'
                }}>
                  <strong>Note:</strong> Entropy analysis is performed on traffic from the last 5 minutes, 
                  analyzing up to 5,000 flow records. Thresholds are configurable based on your network characteristics.
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="card">
            <p style={{ textAlign: 'center', color: '#666', padding: '2rem' }}>
              No entropy data available. Waiting for traffic...
            </p>
          </div>
        )}
      </div>
    </>
  );
}

export default EntropyAnalysis;
