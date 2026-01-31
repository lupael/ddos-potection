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

export default api;
