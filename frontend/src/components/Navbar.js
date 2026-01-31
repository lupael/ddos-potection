import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

function Navbar({ onLogout }) {
  return (
    <div className="navbar">
      <h1>🛡️ DDoS Protection Platform</h1>
      <nav>
        <Link to="/">Dashboard</Link>
        <Link to="/traffic">Traffic</Link>
        <Link to="/alerts">Alerts</Link>
        <Link to="/rules">Rules</Link>
        <Link to="/reports">Reports</Link>
        <Link to="/settings">Settings</Link>
        <button 
          onClick={onLogout} 
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: 'none',
            color: 'white',
            padding: '0.5rem 1rem',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Logout
        </button>
      </nav>
    </div>
  );
}

export default Navbar;
