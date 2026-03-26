import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

function Navbar({ onLogout }) {
  const [showCollectionMenu, setShowCollectionMenu] = useState(false);
  const dropdownRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowCollectionMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setShowCollectionMenu(!showCollectionMenu);
    } else if (event.key === 'Escape') {
      setShowCollectionMenu(false);
    }
  };

  const isActive = (path) => location.pathname === path ? 'active' : '';

  const collectionPaths = ['/traffic-collection', '/anomaly-detection', '/entropy-analysis'];
  const collectionActive = collectionPaths.includes(location.pathname);

  return (
    <header className="navbar" role="banner">
      {/* Brand */}
      <Link to="/" className="navbar-brand">
        <div className="navbar-brand-icon" aria-hidden="true">🛡️</div>
        <h1>DDoS Shield</h1>
      </Link>

      {/* Navigation links */}
      <nav aria-label="Main navigation">
        <Link to="/" className={isActive('/')}>
          📊 Dashboard
        </Link>
        <Link to="/traffic" className={isActive('/traffic')}>
          📡 Traffic
        </Link>

        {/* Collection & Detection dropdown */}
        <div
          className="dropdown"
          ref={dropdownRef}
          data-open={showCollectionMenu}
          onMouseEnter={() => setShowCollectionMenu(true)}
          onMouseLeave={() => setShowCollectionMenu(false)}
        >
          <button
            className={`dropdown-trigger${collectionActive ? ' active' : ''}`}
            onClick={() => setShowCollectionMenu(!showCollectionMenu)}
            onKeyDown={handleKeyDown}
            aria-haspopup="true"
            aria-expanded={showCollectionMenu}
          >
            🔍 Detection
            <span className="dropdown-chevron">▼</span>
          </button>

          {showCollectionMenu && (
            <div className="dropdown-menu" role="menu">
              <div className="dropdown-menu-header">Collection &amp; Analysis</div>
              <Link to="/traffic-collection" role="menuitem" onClick={() => setShowCollectionMenu(false)}>
                <span className="dropdown-menu-icon">📥</span> Traffic Collection
              </Link>
              <Link to="/anomaly-detection" role="menuitem" onClick={() => setShowCollectionMenu(false)}>
                <span className="dropdown-menu-icon">⚠️</span> Anomaly Detection
              </Link>
              <Link to="/entropy-analysis" role="menuitem" onClick={() => setShowCollectionMenu(false)}>
                <span className="dropdown-menu-icon">📈</span> Entropy Analysis
              </Link>
            </div>
          )}
        </div>

        <Link to="/alerts" className={isActive('/alerts')}>
          🚨 Alerts
        </Link>
        <Link to="/rules" className={isActive('/rules')}>
          📋 Rules
        </Link>
        <Link to="/bgp-blackholing" className={isActive('/bgp-blackholing')}>
          🌐 BGP/RTBH
        </Link>
        <Link to="/capture" className={isActive('/capture')}>
          🔬 Capture
        </Link>
        <Link to="/hostgroups" className={isActive('/hostgroups')}>
          🖥️ Hosts
        </Link>
        <Link to="/reports" className={isActive('/reports')}>
          📄 Reports
        </Link>
        <Link to="/settings" className={isActive('/settings')}>
          ⚙️ Settings
        </Link>

        <div className="navbar-divider" role="separator" aria-hidden="true" />

        <button className="navbar-logout" onClick={onLogout} aria-label="Log out">
          🚪 Logout
        </button>
      </nav>
    </header>
  );
}

export default Navbar;
