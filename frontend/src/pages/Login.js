import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await authService.login(username, password);
      localStorage.setItem('token', response.data.access_token);
      navigate('/');
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 400) {
        setError('Invalid username or password.');
      } else if (err.request) {
        setError('Unable to connect to server. Please try again.');
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          {/* Logo / Brand */}
          <div className="login-logo">
            <div className="login-logo-icon">🛡️</div>
            <span className="login-title">DDoS Shield</span>
          </div>
          <p className="login-subtitle">Enterprise DDoS Protection Platform</p>

          {error && (
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                disabled={loading}
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                disabled={loading}
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading}
              style={{ marginTop: '0.5rem' }}
            >
              {loading ? (
                <>
                  <span
                    style={{
                      display: 'inline-block',
                      width: '14px',
                      height: '14px',
                      border: '2px solid rgba(255,255,255,0.4)',
                      borderTopColor: '#fff',
                      borderRadius: '50%',
                      animation: 'spin 0.7s linear infinite',
                    }}
                  />
                  Signing in…
                </>
              ) : (
                'Sign In →'
              )}
            </button>
          </form>

          <p style={{
            marginTop: '1.5rem',
            fontSize: '0.75rem',
            color: 'rgba(255,255,255,0.3)',
            textAlign: 'center',
            lineHeight: 1.5,
          }}>
            Protected by enterprise-grade security.<br />
            Unauthorized access is prohibited.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;

