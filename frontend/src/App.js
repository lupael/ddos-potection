import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './styles/App.css';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import TrafficMonitor from './pages/TrafficMonitor';
import Rules from './pages/Rules';
import Alerts from './pages/Alerts';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import PacketCapture from './pages/PacketCapture';
import Hostgroups from './pages/Hostgroups';
import TrafficCollection from './pages/TrafficCollection';
import AnomalyDetection from './pages/AnomalyDetection';
import EntropyAnalysis from './pages/EntropyAnalysis';

function App() {
  const isAuthenticated = () => {
    return localStorage.getItem('token') !== null;
  };

  const PrivateRoute = ({ children }) => {
    return isAuthenticated() ? children : <Navigate to="/login" />;
  };

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/traffic"
            element={
              <PrivateRoute>
                <TrafficMonitor />
              </PrivateRoute>
            }
          />
          <Route
            path="/rules"
            element={
              <PrivateRoute>
                <Rules />
              </PrivateRoute>
            }
          />
          <Route
            path="/alerts"
            element={
              <PrivateRoute>
                <Alerts />
              </PrivateRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <PrivateRoute>
                <Reports />
              </PrivateRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <PrivateRoute>
                <Settings />
              </PrivateRoute>
            }
          />
          <Route
            path="/capture"
            element={
              <PrivateRoute>
                <PacketCapture />
              </PrivateRoute>
            }
          />
          <Route
            path="/hostgroups"
            element={
              <PrivateRoute>
                <Hostgroups />
              </PrivateRoute>
            }
          />
          <Route
            path="/traffic-collection"
            element={
              <PrivateRoute>
                <TrafficCollection />
              </PrivateRoute>
            }
          />
          <Route
            path="/anomaly-detection"
            element={
              <PrivateRoute>
                <AnomalyDetection />
              </PrivateRoute>
            }
          />
          <Route
            path="/entropy-analysis"
            element={
              <PrivateRoute>
                <EntropyAnalysis />
              </PrivateRoute>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
