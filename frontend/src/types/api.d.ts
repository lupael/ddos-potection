// TypeScript type definitions for the DDoS Protection Platform API

export interface IAlert {
  id: number;
  isp_id: number;
  alert_type: string;
  severity: string;
  source_ip: string | null;
  dest_ip: string | null;
  target_ip: string | null;
  status: string;
  details: Record<string, unknown> | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ITrafficData {
  id: number;
  isp_id: number;
  timestamp: string;
  source_ip: string;
  dest_ip: string;
  protocol: string;
  packets: number;
  bytes: number;
  port: number | null;
}

export interface IMitigation {
  id: number;
  alert_id: number;
  isp_id: number;
  action_type: string;
  status: string;
  details: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  alert?: {
    type: string;
    severity: string;
    target_ip: string;
    source_ip: string | null;
  };
}

export interface IISP {
  id: number;
  name: string;
  email: string;
  api_key: string | null;
  subscription_tier: string;
  is_active: boolean;
  created_at: string;
}

export interface IUser {
  id: number;
  username: string;
  email: string;
  role: string;
  isp_id: number;
  is_active: boolean;
  created_at: string;
}

export interface IRule {
  id: number;
  isp_id: number;
  name: string;
  description: string | null;
  rule_type: string;
  threshold: number | null;
  action: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ISubscription {
  id: number;
  isp_id: number;
  tier: string;
  status: string;
  start_date: string;
  end_date: string | null;
  price_monthly: number;
  features: Record<string, unknown>;
}

export interface IAttackCampaign {
  id: number;
  isp_id: number;
  name: string;
  attack_type: string;
  start_time: string;
  end_time: string | null;
  status: string;
  total_packets: number;
  peak_pps: number;
  source_ips: string[];
}

export interface ISLARecord {
  id: number;
  isp_id: number;
  period_start: string;
  period_end: string;
  uptime_percent: number;
  mttr_minutes: number;
  incidents: number;
  sla_met: boolean;
}

export interface IWebhook {
  id: number;
  isp_id: number;
  url: string;
  events: string[];
  is_active: boolean;
  secret: string | null;
  created_at: string;
  last_triggered: string | null;
}

export interface IThreatScore {
  ip: string;
  score: number;
  categories: string[];
  last_seen: string | null;
  confidence: number;
}

export interface ILoginResponse {
  access_token: string;
  token_type: string;
}

export interface ITrafficStats {
  timestamp: string;
  total_packets: number;
  total_bytes: number;
  protocol_breakdown: Record<string, number>;
  top_sources: Array<{ ip: string; packets: number }>;
}

export interface IAlertSummary {
  total: number;
  open: number;
  resolved: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
}

export interface IMitigationAnalytics {
  period: string;
  total_mitigations: number;
  active_mitigations: number;
  success_rate_percent: number;
  most_used_types: Array<{ type: string; count: number }>;
}
