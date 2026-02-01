# Monitoring and Alerting Guide

This guide covers the comprehensive monitoring, visualization, and alerting features of the DDoS Protection Platform.

## Table of Contents

- [Prometheus Metrics](#prometheus-metrics)
- [Grafana Dashboards](#grafana-dashboards)
- [Multi-channel Alerts](#multi-channel-alerts)
- [Live Attack Maps](#live-attack-maps)
- [Mitigation Status Tracking](#mitigation-status-tracking)

## Prometheus Metrics

The platform exposes comprehensive metrics at the `/metrics` endpoint for Prometheus scraping.

### Available Metrics

#### Traffic Metrics
- `ddos_traffic_packets_total` - Total packets processed (counter)
- `ddos_traffic_bytes_total` - Total bytes processed (counter)
- `ddos_traffic_flows_total` - Total flows processed (counter)

#### Alert Metrics
- `ddos_alerts_total` - Total alerts generated (counter)
- `ddos_alerts_active` - Number of active alerts (gauge)
- `ddos_alerts_resolved_total` - Total alerts resolved (counter)

#### Mitigation Metrics
- `ddos_mitigations_total` - Total mitigations applied (counter)
- `ddos_mitigations_active` - Number of active mitigations (gauge)
- `ddos_mitigation_duration_seconds` - Duration of mitigations (histogram)

#### Attack Detection Metrics
- `ddos_attacks_detected_total` - Total attacks detected (counter)
- `ddos_attack_volume_packets` - Current attack volume in packets/sec (gauge)
- `ddos_attack_volume_bytes` - Current attack volume in bytes/sec (gauge)

#### System Health Metrics
- `ddos_system_health` - System health status (gauge, 1=healthy, 0=unhealthy)
- `ddos_api_requests_total` - Total API requests (counter)
- `ddos_api_request_duration_seconds` - API request duration (histogram)

### Accessing Metrics

```bash
# View metrics directly
curl http://localhost:8000/metrics

# Prometheus is configured to scrape this endpoint automatically
# Access Prometheus UI at http://localhost:9090
```

### Example Prometheus Queries

```promql
# Active alerts by severity
sum by(severity) (ddos_alerts_active)

# Attack detection rate (5-minute window)
rate(ddos_attacks_detected_total[5m])

# Top attacked targets
topk(10, ddos_attack_volume_packets)

# Mitigation rate (last hour)
sum(increase(ddos_mitigations_total[1h]))

# System health status
ddos_system_health
```

## Grafana Dashboards

The platform includes three pre-configured Grafana dashboards:

### 1. DDoS Protection - Overview
**Location:** `docker/grafana/dashboards/ddos-overview.json`

Main operational dashboard showing:
- Active alerts count
- Active mitigations count
- Traffic rate (packets/sec)
- Active alerts by severity (time series)
- Traffic rate by protocol
- Attacks detected (5m rate)
- Active mitigations by type
- System health indicators (Database, Redis, API)

**Refresh rate:** 5 seconds  
**Access:** http://localhost:3001/d/ddos-overview

### 2. DDoS Protection - Attack Analysis
**Location:** `docker/grafana/dashboards/attack-analysis.json`

Detailed attack analysis showing:
- Attack types distribution (pie chart)
- Alert severity distribution (pie chart)
- Top 10 attack targets by packet volume
- Top 10 attack targets by bandwidth
- Attack statistics table

**Refresh rate:** 10 seconds  
**Access:** http://localhost:3001/d/ddos-attack-analysis

### 3. DDoS Protection - Mitigation Status
**Location:** `docker/grafana/dashboards/mitigation-status.json`

Mitigation tracking dashboard showing:
- Active firewall rules count
- Active BGP blackholes count
- Active rate limits count
- Total mitigations (24h)
- Active mitigations by type over time
- Mitigation actions applied (5m rate)
- Mitigation duration percentiles (p50, p95)
- Mitigation types distribution (24h)
- Current active mitigations table

**Refresh rate:** 10 seconds  
**Access:** http://localhost:3001/d/ddos-mitigation-status

### Accessing Grafana

1. Navigate to http://localhost:3001
2. Login with default credentials:
   - Username: `admin`
   - Password: `admin`
3. Dashboards are automatically provisioned and available in the sidebar

### Customizing Dashboards

Dashboards are provisioned from JSON files in `docker/grafana/dashboards/`. To customize:

1. Edit the dashboard in Grafana UI
2. Export the dashboard JSON
3. Save to `docker/grafana/dashboards/`
4. Restart Grafana container

## Multi-channel Alerts

The platform supports notifications through multiple channels:

### Supported Channels

1. **Email** - SMTP-based email notifications
2. **SMS** - Twilio-based SMS notifications
3. **Telegram** - Telegram bot notifications

### Configuration

Add the following to your `.env` file:

```bash
# Email Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=admin@example.com

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# SMS Notifications (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

### Email Setup

For Gmail:
1. Enable 2-factor authentication
2. Generate an app password at https://myaccount.google.com/apppasswords
3. Use the app password in `SMTP_PASSWORD`

### Telegram Setup

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Get your bot token
3. Start a chat with your bot
4. Get your chat ID by visiting: `https://api.telegram.org/bot<TOKEN>/getUpdates`

### SMS Setup (Twilio)

1. Sign up at https://www.twilio.com/
2. Get your Account SID and Auth Token from the console
3. Get a Twilio phone number
4. Add credentials to `.env`

### Notification Format

Alerts include:
- Alert type and severity
- Target and source IP addresses
- Timestamp
- Detailed description
- Color-coded severity (email/Telegram)

### Testing Notifications

You can test notifications programmatically:

```python
from services.notification_service import notification_service

# Test email
await notification_service.send_email(
    to_email="admin@example.com",
    subject="Test Alert",
    body="This is a test notification"
)

# Test Telegram
await notification_service.send_telegram(
    chat_id="your-chat-id",
    message="🚨 Test Alert: System is operational"
)

# Test SMS
await notification_service.send_sms(
    to_number="+1234567890",
    message="DDoS Alert: Test notification"
)
```

## Live Attack Maps

Real-time attack visualization with geographic data.

### API Endpoints

#### Get Live Attacks
```bash
GET /api/v1/attack-map/live-attacks

# Response
{
  "total": 5,
  "attacks": [
    {
      "id": 123,
      "type": "syn_flood",
      "severity": "critical",
      "source_ip": "1.2.3.4",
      "target_ip": "10.0.0.1",
      "description": "SYN flood detected",
      "timestamp": "2024-01-15T10:30:00Z",
      "source_location": {
        "lat": 40.7128,
        "lon": -74.0060,
        "country": "US",
        "city": "New York"
      },
      "target_location": {
        "lat": 51.5074,
        "lon": -0.1278,
        "country": "UK",
        "city": "London"
      }
    }
  ],
  "last_updated": "2024-01-15T10:35:00Z"
}
```

#### Get Attack Heatmap
```bash
GET /api/v1/attack-map/attack-heatmap?hours=24

# Returns aggregated attack data for heatmap visualization
```

#### Get Attack Statistics
```bash
GET /api/v1/attack-map/attack-statistics

# Returns summary statistics for dashboard widgets
```

#### WebSocket Real-time Updates
```javascript
// Connect to WebSocket for real-time attack updates
const ws = new WebSocket('ws://localhost:8000/api/v1/attack-map/ws/live-attacks');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'new_attack') {
    console.log('New attack detected:', data.data);
    // Update map visualization
  }
};
```

### Geographic Data

The platform uses IP geolocation to map attack sources and targets. In production:

1. Integrate with a GeoIP service (e.g., MaxMind GeoLite2)
2. Install the GeoIP database
3. Update the `get_ip_location()` function in `attack_map_router.py`

Example with MaxMind:
```python
import geoip2.database

reader = geoip2.database.Reader('/path/to/GeoLite2-City.mmdb')
response = reader.city(ip_address)
location = {
    'lat': response.location.latitude,
    'lon': response.location.longitude,
    'country': response.country.name,
    'city': response.city.name
}
```

## Mitigation Status Tracking

Comprehensive tracking of mitigation actions and their effectiveness.

### API Endpoints

#### Get Active Mitigations
```bash
GET /api/v1/mitigation/status/active

# Returns all currently active mitigations with details
{
  "total": 3,
  "mitigations": [
    {
      "id": 45,
      "alert_id": 123,
      "action_type": "firewall",
      "status": "active",
      "details": {"ip": "1.2.3.4", "protocol": "tcp"},
      "created_at": "2024-01-15T10:30:00Z",
      "duration_seconds": 300,
      "alert": {
        "type": "syn_flood",
        "severity": "critical",
        "target_ip": "10.0.0.1",
        "source_ip": "1.2.3.4"
      }
    }
  ]
}
```

#### Get Mitigation History
```bash
GET /api/v1/mitigation/status/history?hours=24

# Returns historical mitigations with statistics
{
  "period_hours": 24,
  "total_mitigations": 15,
  "history": [...],
  "statistics": {
    "by_type_and_status": {
      "firewall": {"active": 2, "completed": 8, "failed": 1},
      "bgp_blackhole": {"completed": 3, "failed": 1}
    },
    "average_duration_seconds": {
      "firewall": 450,
      "bgp_blackhole": 600
    }
  }
}
```

#### Get Mitigation Analytics
```bash
GET /api/v1/mitigation/status/analytics

# Returns comprehensive analytics
{
  "period": "24h",
  "total_mitigations": 15,
  "active_mitigations": 3,
  "success_rate_percent": 93.33,
  "most_used_types": [
    {"type": "firewall", "count": 10},
    {"type": "bgp_blackhole", "count": 5}
  ]
}
```

### Mitigation Lifecycle

1. **Pending** - Mitigation created but not yet executed
2. **Active** - Mitigation is currently in effect
3. **Completed** - Mitigation successfully completed
4. **Failed** - Mitigation execution or removal failed

### Monitoring Best Practices

1. **Set up alerts** in Grafana for critical thresholds
2. **Review mitigation success rates** regularly
3. **Monitor system health** indicators
4. **Check notification delivery** periodically
5. **Analyze attack patterns** using the Attack Analysis dashboard
6. **Track mitigation effectiveness** using duration and success rate metrics

## Troubleshooting

### Prometheus Not Scraping Metrics

1. Check Prometheus configuration: `docker/prometheus.yml`
2. Verify backend is exposing metrics: `curl http://localhost:8000/metrics`
3. Check Prometheus targets: http://localhost:9090/targets

### Grafana Dashboards Not Loading

1. Check volume mounts in `docker-compose.yml`
2. Verify dashboard JSON files exist in `docker/grafana/dashboards/`
3. Check Grafana logs: `docker logs ddos-grafana`

### Notifications Not Sending

1. Verify credentials in `.env` file
2. Check backend logs for error messages
3. Test credentials independently (e.g., send test email via SMTP)
4. Ensure notification service is properly initialized

### WebSocket Connection Issues

1. Check CORS configuration in `backend/config.py`
2. Verify WebSocket is supported by your reverse proxy (if using one)
3. Check browser console for connection errors

## Performance Considerations

- Metrics are collected every 15 seconds (configurable in `prometheus.yml`)
- Dashboards auto-refresh every 5-10 seconds
- WebSocket updates are real-time with minimal latency
- Historical data retention is configurable in Prometheus
- Consider using Prometheus recording rules for frequently queried metrics

## Security Notes

- Grafana admin password should be changed from default
- Prometheus metrics endpoint could expose sensitive information - consider authentication
- Notification credentials should be stored securely (use environment variables, not config files)
- WebSocket connections should be authenticated in production
- Consider using TLS for all communications in production
