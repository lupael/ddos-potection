import axios, { AxiosInstance, AxiosResponse } from 'axios';
import type {
  IAlert,
  ITrafficData,
  IMitigation,
  IISP,
  IUser,
  IRule,
  ISubscription,
  IAttackCampaign,
  ISLARecord,
  IWebhook,
  IThreatScore,
  ILoginResponse,
  ITrafficStats,
  IAlertSummary,
  IMitigationAnalytics,
} from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Auth
export const login = (
  username: string,
  password: string,
): Promise<AxiosResponse<ILoginResponse>> => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  return apiClient.post<ILoginResponse>('/auth/token', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
};

export const register = (data: {
  username: string;
  email: string;
  password: string;
  isp_name?: string;
}): Promise<AxiosResponse<IUser>> =>
  apiClient.post<IUser>('/auth/register', data, {
    headers: { 'Content-Type': 'application/json' },
  });

export const getCurrentUser = (): Promise<AxiosResponse<IUser>> =>
  apiClient.get<IUser>('/auth/me');

// Alerts
export const getAlerts = (status?: string): Promise<AxiosResponse<IAlert[]>> =>
  apiClient.get<IAlert[]>(`/alerts/${status ? `?status=${status}` : ''}`);

export const getAlert = (id: number): Promise<AxiosResponse<IAlert>> =>
  apiClient.get<IAlert>(`/alerts/${id}`);

export const resolveAlert = (id: number): Promise<AxiosResponse<IAlert>> =>
  apiClient.post<IAlert>(`/alerts/${id}/resolve`);

export const getAlertSummary = (): Promise<AxiosResponse<IAlertSummary>> =>
  apiClient.get<IAlertSummary>('/alerts/stats/summary');

// Traffic
export const getTrafficData = (limit = 100): Promise<AxiosResponse<ITrafficStats[]>> =>
  apiClient.get<ITrafficStats[]>(`/traffic/stats?limit=${limit}`);

export const getRealtimeTraffic = (): Promise<AxiosResponse<ITrafficStats>> =>
  apiClient.get<ITrafficStats>('/traffic/realtime');

export const getProtocols = (): Promise<AxiosResponse<Record<string, number>>> =>
  apiClient.get<Record<string, number>>('/traffic/protocols');

// Mitigations
export const getMitigations = (): Promise<AxiosResponse<IMitigation[]>> =>
  apiClient.get<IMitigation[]>('/mitigation/');

export const createMitigation = (
  data: Partial<IMitigation>,
): Promise<AxiosResponse<IMitigation>> =>
  apiClient.post<IMitigation>('/mitigation/', data);

export const executeMitigation = (id: number): Promise<AxiosResponse<IMitigation>> =>
  apiClient.post<IMitigation>(`/mitigation/${id}/execute`);

export const stopMitigation = (id: number): Promise<AxiosResponse<IMitigation>> =>
  apiClient.post<IMitigation>(`/mitigation/${id}/stop`);

export const getMitigationActiveStatus = (): Promise<
  AxiosResponse<{ total: number; mitigations: IMitigation[] }>
> => apiClient.get('/mitigation/status/active');

export const getMitigationHistory = (
  hours = 24,
): Promise<AxiosResponse<{ period_hours: number; total_mitigations: number; history: IMitigation[] }>> =>
  apiClient.get(`/mitigation/status/history?hours=${hours}`);

export const getMitigationAnalytics = (): Promise<AxiosResponse<IMitigationAnalytics>> =>
  apiClient.get<IMitigationAnalytics>('/mitigation/status/analytics');

// Rules
export const getRules = (): Promise<AxiosResponse<IRule[]>> =>
  apiClient.get<IRule[]>('/rules/');

export const getRule = (id: number): Promise<AxiosResponse<IRule>> =>
  apiClient.get<IRule>(`/rules/${id}`);

export const createRule = (rule: Partial<IRule>): Promise<AxiosResponse<IRule>> =>
  apiClient.post<IRule>('/rules/', rule);

export const updateRule = (id: number, rule: Partial<IRule>): Promise<AxiosResponse<IRule>> =>
  apiClient.put<IRule>(`/rules/${id}`, rule);

export const deleteRule = (id: number): Promise<AxiosResponse<void>> =>
  apiClient.delete<void>(`/rules/${id}`);

// ISPs
export const getISPs = (): Promise<AxiosResponse<IISP[]>> =>
  apiClient.get<IISP[]>('/isp/me');

export const getMyISP = (): Promise<AxiosResponse<IISP>> =>
  apiClient.get<IISP>('/isp/me');

export const createISP = (data: Partial<IISP>): Promise<AxiosResponse<IISP>> =>
  apiClient.post<IISP>('/isp/', data);

export const updateISP = (data: Partial<IISP>): Promise<AxiosResponse<IISP>> =>
  apiClient.put<IISP>('/isp/me', data);

export const regenerateApiKey = (): Promise<AxiosResponse<{ api_key: string }>> =>
  apiClient.post<{ api_key: string }>('/isp/regenerate-api-key');

export const listISPUsers = (): Promise<AxiosResponse<IUser[]>> =>
  apiClient.get<IUser[]>('/isp/users');

// Subscriptions
export const getSubscription = (): Promise<AxiosResponse<ISubscription>> =>
  apiClient.get<ISubscription>('/subscription/');

// Attack Campaigns
export const getAttackCampaigns = (): Promise<AxiosResponse<IAttackCampaign[]>> =>
  apiClient.get<IAttackCampaign[]>('/campaigns/');

// SLA
export const getSLARecords = (): Promise<AxiosResponse<ISLARecord[]>> =>
  apiClient.get<ISLARecord[]>('/sla/');

// Webhooks
export const getWebhooks = (): Promise<AxiosResponse<IWebhook[]>> =>
  apiClient.get<IWebhook[]>('/webhooks/');

export const createWebhook = (data: Partial<IWebhook>): Promise<AxiosResponse<IWebhook>> =>
  apiClient.post<IWebhook>('/webhooks/', data);

export const deleteWebhook = (id: number): Promise<AxiosResponse<void>> =>
  apiClient.delete<void>(`/webhooks/${id}`);

// Threat Intelligence
export const getThreatScore = (ip: string): Promise<AxiosResponse<IThreatScore>> =>
  apiClient.get<IThreatScore>(`/threat-intel/score/${ip}`);

// Reports
export const getReports = (): Promise<AxiosResponse<unknown[]>> =>
  apiClient.get('/reports/');

export const generateReport = (reportType: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/reports/generate?report_type=${reportType}`);

export const downloadReport = (id: number): Promise<AxiosResponse<Blob>> =>
  apiClient.get<Blob>(`/reports/${id}/download`, { responseType: 'blob' });

// Packet Capture
export const startCapture = (captureData: Record<string, unknown>): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/capture/start', captureData);

export const stopCapture = (captureId: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/capture/stop/${captureId}`);

export const getCaptureStatus = (captureId: string): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/capture/status/${captureId}`);

export const listCaptures = (): Promise<AxiosResponse<unknown[]>> =>
  apiClient.get('/capture/list');

export const downloadCapture = (filename: string): Promise<AxiosResponse<Blob>> =>
  apiClient.get<Blob>(`/capture/download/${filename}`, { responseType: 'blob' });

export default apiClient;
