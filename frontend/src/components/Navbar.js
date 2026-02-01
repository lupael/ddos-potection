import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';

function Navbar({ onLogout }) {
  const [showTrafficMenu, setShowTrafficMenu] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowTrafficMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      setShowTrafficMenu(!showTrafficMenu);
    } else if (event.key === ' ') {
      event.preventDefault();
      setShowTrafficMenu(!showTrafficMenu);
    } else if (event.key === 'Escape') {
      setShowTrafficMenu(false);
    }
  };

  return (
    <div className="navbar">
      <h1>🛡️ DDoS Protection Platform</h1>
      <nav>
        <Link to="/">Dashboard</Link>
        <Link to="/traffic">Traffic</Link>
        
        {/* Traffic Collection & Detection Dropdown */}
        <div 
          className="dropdown"
          ref={dropdownRef}
          onMouseEnter={() => setShowTrafficMenu(true)}
          onMouseLeave={() => setShowTrafficMenu(false)}
        >
          <button
            className="dropdown-trigger"
            onClick={() => setShowTrafficMenu(!showTrafficMenu)}
            onKeyDown={handleKeyDown}
            aria-haspopup="true"
            aria-expanded={showTrafficMenu}
          >
            Collection & Detection ▼
          </button>
          {showTrafficMenu && (
            <div className="dropdown-menu" role="menu">
              <Link to="/traffic-collection" role="menuitem">
                Traffic Collection
              </Link>
              <Link to="/anomaly-detection" role="menuitem">
                Anomaly Detection
              </Link>
              <Link to="/entropy-analysis" role="menuitem">
                Entropy Analysis
              </Link>
            </div>
          )}
        </div>
        
        <Link to="/alerts">Alerts</Link>
        <Link to="/rules">Rules</Link>
        <Link to="/capture">Capture</Link>
        <Link to="/hostgroups">Hostgroups</Link>
        <Link to="/bgp-blackholing">BGP/RTBH</Link>
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
