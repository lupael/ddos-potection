import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { reportsService } from '../services/api';
import Navbar from '../components/Navbar';

function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const response = await reportsService.list();
      setReports(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading reports:', error);
    }
  };

  const handleGenerate = async (reportType) => {
    setGenerating(true);
    try {
      await reportsService.generate(reportType);
      alert('Report generated successfully');
      loadReports();
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Error generating report');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (reportId) => {
    try {
      const response = await reportsService.download(reportId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${reportId}.txt`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading report:', error);
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
        <h1>Reports</h1>

        <div className="card">
          <h2 className="card-title">Generate New Report</h2>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <button
              className="btn btn-primary"
              onClick={() => handleGenerate('daily')}
              disabled={generating}
            >
              Daily Report
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleGenerate('weekly')}
              disabled={generating}
            >
              Weekly Report
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleGenerate('monthly')}
              disabled={generating}
            >
              Monthly Report
            </button>
          </div>
          {generating && <p style={{ marginTop: '1rem', color: '#667eea' }}>Generating report...</p>}
        </div>

        <div className="card">
          <h2 className="card-title">Report History</h2>
          {loading ? (
            <div className="spinner"></div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Report Type</th>
                  <th>Period Start</th>
                  <th>Period End</th>
                  <th>Generated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.id}>
                    <td><strong>{report.report_type.toUpperCase()}</strong></td>
                    <td>{new Date(report.period_start).toLocaleDateString()}</td>
                    <td>{new Date(report.period_end).toLocaleDateString()}</td>
                    <td>{new Date(report.created_at).toLocaleString()}</td>
                    <td>
                      <button
                        className="btn btn-primary"
                        style={{ padding: '0.5rem 1rem' }}
                        onClick={() => handleDownload(report.id)}
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!loading && reports.length === 0 && (
            <p style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No reports available
            </p>
          )}
        </div>
      </div>
    </>
  );
}

export default Reports;
