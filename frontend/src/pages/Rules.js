import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { rulesService } from '../services/api';
import Navbar from '../components/Navbar';

function Rules() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    rule_type: 'ip_block',
    condition: {},
    action: 'block',
    priority: 100,
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    try {
      const response = await rulesService.list();
      setRules(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading rules:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await rulesService.create(formData);
      setShowForm(false);
      setFormData({
        name: '',
        rule_type: 'ip_block',
        condition: {},
        action: 'block',
        priority: 100,
      });
      loadRules();
    } catch (error) {
      console.error('Error creating rule:', error);
      alert('Error creating rule');
    }
  };

  const handleDelete = async (ruleId) => {
    if (window.confirm('Are you sure you want to delete this rule?')) {
      try {
        await rulesService.delete(ruleId);
        loadRules();
      } catch (error) {
        console.error('Error deleting rule:', error);
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <>
      <Navbar onLogout={handleLogout} />
      <div className="container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h1>Firewall Rules</h1>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : 'Add Rule'}
          </button>
        </div>

        {showForm && (
          <div className="card">
            <h2 className="card-title">Create New Rule</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Rule Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Rule Type</label>
                <select
                  value={formData.rule_type}
                  onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                >
                  <option value="ip_block">IP Block</option>
                  <option value="rate_limit">Rate Limit</option>
                  <option value="protocol_filter">Protocol Filter</option>
                  <option value="geo_block">Geo Block</option>
                </select>
              </div>
              <div className="form-group">
                <label>Action</label>
                <select
                  value={formData.action}
                  onChange={(e) => setFormData({ ...formData, action: e.target.value })}
                >
                  <option value="block">Block</option>
                  <option value="rate_limit">Rate Limit</option>
                  <option value="alert">Alert Only</option>
                </select>
              </div>
              <div className="form-group">
                <label>Priority (lower = higher priority)</label>
                <input
                  type="number"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label>Condition (JSON)</label>
                <textarea
                  rows="4"
                  value={JSON.stringify(formData.condition)}
                  onChange={(e) => {
                    try {
                      setFormData({ ...formData, condition: JSON.parse(e.target.value) });
                    } catch {}
                  }}
                  placeholder='{"ip": "1.2.3.4", "port": 80}'
                />
              </div>
              <button type="submit" className="btn btn-primary">Create Rule</button>
            </form>
          </div>
        )}

        <div className="card">
          <h2 className="card-title">Active Rules</h2>
          {loading ? (
            <div className="spinner"></div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Action</th>
                  <th>Priority</th>
                  <th>Condition</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td><strong>{rule.name}</strong></td>
                    <td>{rule.rule_type.replace('_', ' ')}</td>
                    <td>{rule.action}</td>
                    <td>{rule.priority}</td>
                    <td><code>{JSON.stringify(rule.condition)}</code></td>
                    <td>
                      <span className={`badge ${rule.is_active ? 'badge-active' : 'badge-inactive'}`}>
                        {rule.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-danger"
                        style={{ padding: '0.5rem 1rem' }}
                        onClick={() => handleDelete(rule.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!loading && rules.length === 0 && (
            <p style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No rules configured
            </p>
          )}
        </div>
      </div>
    </>
  );
}

export default Rules;
