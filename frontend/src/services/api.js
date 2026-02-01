import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authService = {
  login: (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
  register: (data) => api.post('/auth/register', data, {
    headers: {
      'Content-Type': 'application/json',
    },
  }),
  getCurrentUser: () => api.get('/auth/me'),
};

// Traffic endpoints
export const trafficService = {
  getStats: (limit = 100) => api.get(`/traffic/stats?limit=${limit}`),
  getRealtime: () => api.get('/traffic/realtime'),
  getProtocols: () => api.get('/traffic/protocols'),
};

// Rules endpoints
export const rulesService = {
  list: () => api.get('/rules/'),
  create: (rule) => api.post('/rules/', rule),
  get: (id) => api.get(`/rules/${id}`),
  update: (id, rule) => api.put(`/rules/${id}`, rule),
  delete: (id) => api.delete(`/rules/${id}`),
};

// Alerts endpoints
export const alertsService = {
  list: (status = null) => api.get(`/alerts/${status ? `?status=${status}` : ''}`),
  get: (id) => api.get(`/alerts/${id}`),
  resolve: (id) => api.post(`/alerts/${id}/resolve`),
  getSummary: () => api.get('/alerts/stats/summary'),
};

// Mitigation endpoints
export const mitigationService = {
  list: () => api.get('/mitigation/'),
  create: (mitigation) => api.post('/mitigation/', mitigation),
  execute: (id) => api.post(`/mitigation/${id}/execute`),
  stop: (id) => api.post(`/mitigation/${id}/stop`),
  /**
   * Get active mitigation status
   * @returns {Promise} Response with { total, mitigations: Array }
   *   Each mitigation contains { id, alert_id, action_type, status, details, 
   *   created_at, duration_seconds, alert: { type, severity, target_ip, source_ip } }
   *   NOTE: The nested alert object uses 'type' (not 'alert_type') as the property name.
   *   This is different from the /alerts/ endpoint which uses 'alert_type'.
   */
  getActiveStatus: () => api.get('/mitigation/status/active'),
  /**
   * Get mitigation history
   * @param {number} hours - Number of hours to look back (default: 24)
   * @returns {Promise} Response with { period_hours, total_mitigations, history: Array, statistics }
   *   Each history item contains { id, action_type, status, created_at, completed_at,
   *   duration_seconds, alert: { id, type, severity, target_ip } }
   *   NOTE: The nested alert object uses 'type' (not 'alert_type') as the property name.
   *   This is different from the /alerts/ endpoint which uses 'alert_type'.
   */
  getHistory: (hours = 24) => api.get(`/mitigation/status/history?hours=${hours}`),
  /**
   * Get mitigation analytics
   * @returns {Promise} Response with { period, total_mitigations, active_mitigations, 
   *   success_rate_percent, most_used_types }
   */
  getAnalytics: () => api.get('/mitigation/status/analytics'),
};

// ISP endpoints
export const ispService = {
  getMe: () => api.get('/isp/me'),
  update: (data) => api.put('/isp/me', data),
  regenerateApiKey: () => api.post('/isp/regenerate-api-key'),
  listUsers: () => api.get('/isp/users'),
};

// Reports endpoints
export const reportsService = {
  list: () => api.get('/reports/'),
  generate: (reportType) => api.post(`/reports/generate?report_type=${reportType}`),
  download: (id) => api.get(`/reports/${id}/download`, { responseType: 'blob' }),
};

// Packet Capture endpoints
export const captureService = {
  start: (captureData) => api.post('/capture/start', captureData),
  stop: (captureId) => api.post(`/capture/stop/${captureId}`),
  status: (captureId) => api.get(`/capture/status/${captureId}`),
  list: () => api.get('/capture/list'),
  download: (filename) => api.get(`/capture/download/${filename}`, { responseType: 'blob' }),
  cleanup: (maxAgeDays = 7) => api.delete(`/capture/cleanup?max_age_days=${maxAgeDays}`),
};

// Hostgroup endpoints
export const hostgroupService = {
  list: () => api.get('/hostgroups/'),
  create: (hostgroup) => api.post('/hostgroups/', hostgroup),
  get: (name) => api.get(`/hostgroups/${name}`),
  delete: (name) => api.delete(`/hostgroups/${name}`),
  checkIp: (ip) => api.post('/hostgroups/check-ip', { ip }),
  getDefaults: () => api.get('/hostgroups/defaults/thresholds'),
};

export default api;
