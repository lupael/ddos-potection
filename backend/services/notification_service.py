"""
Multi-channel notification service for alerts
Supports Email, SMS (Twilio), and Telegram notifications
"""
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict
from datetime import datetime

import httpx
from config import settings


class NotificationService:
    """Multi-channel notification dispatcher"""
    
    def __init__(self):
        self.smtp_enabled = bool(settings.SMTP_HOST and settings.SMTP_USER)
        self.telegram_enabled = bool(settings.TELEGRAM_BOT_TOKEN)
        self.sms_enabled = False  # Will be enabled if Twilio credentials are provided
        self.slack_enabled = bool(getattr(settings, 'SLACK_WEBHOOK_URL', ''))
        self.teams_enabled = bool(getattr(settings, 'TEAMS_WEBHOOK_URL', ''))
        self.pagerduty_enabled = bool(
            getattr(settings, 'PAGERDUTY_ENABLED', False)
            and getattr(settings, 'PAGERDUTY_INTEGRATION_KEY', '')
        )

        # Check for Twilio credentials
        if hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
            self.sms_enabled = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
    
    async def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email notification (runs in thread pool to avoid blocking)"""
        if not self.smtp_enabled:
            print("Email notifications not configured")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.SMTP_USER
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Attach HTML version if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email in a background thread to avoid blocking the event loop
            def _send_email_sync() -> None:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            
            await asyncio.to_thread(_send_email_sync)
            
            print(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    async def send_telegram(self, chat_id: str, message: str, parse_mode: str = 'HTML') -> bool:
        """Send Telegram notification"""
        if not self.telegram_enabled:
            print("Telegram notifications not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                response.raise_for_status()
            
            print(f"Telegram message sent to {chat_id}")
            return True
            
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    async def send_sms(self, to_number: str, message: str) -> bool:
        """Send SMS notification via Twilio (runs in thread pool to avoid blocking)"""
        if not self.sms_enabled:
            print("SMS notifications not configured")
            return False
        
        try:
            # Import Twilio client only if needed
            from twilio.rest import Client
            
            # Send SMS in a background thread to avoid blocking the event loop
            def _send_sms_sync() -> str:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                msg = client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to_number
                )
                return msg.sid
            
            message_sid = await asyncio.to_thread(_send_sms_sync)
            
            print(f"SMS sent to {to_number}: {message_sid}")
            return True
            
        except ImportError:
            print("Twilio library not installed. Install with: pip install twilio")
            return False
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False
    
    async def send_slack(self, message: str, webhook_url: str = None) -> bool:
        """Send notification to a Slack channel via Incoming Webhook."""
        url = webhook_url or getattr(settings, 'SLACK_WEBHOOK_URL', '')
        if not url:
            print("Slack notifications not configured")
            return False

        try:
            payload = {"text": message}
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                response.raise_for_status()
            print("Slack message sent")
            return True
        except Exception as e:
            print(f"Error sending Slack message: {e}")
            return False

    async def send_teams(self, message: str, webhook_url: str = None) -> bool:
        """Send notification to a Microsoft Teams channel via Incoming Webhook."""
        url = webhook_url or getattr(settings, 'TEAMS_WEBHOOK_URL', '')
        if not url:
            print("Microsoft Teams notifications not configured")
            return False

        try:
            # Teams uses a simple Adaptive Card / legacy MessageCard format
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "text": message,
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                response.raise_for_status()
            print("Teams message sent")
            return True
        except Exception as e:
            print(f"Error sending Teams message: {e}")
            return False

    async def send_pagerduty(
        self,
        summary: str,
        severity: str,
        source: str,
        custom_details: dict = None,
        dedup_key: str = None,
    ) -> bool:
        """Send PagerDuty Events API v2 alert (trigger)."""
        if not self.pagerduty_enabled:
            print("PagerDuty notifications not configured")
            return False

        import uuid
        payload = {
            "routing_key": settings.PAGERDUTY_INTEGRATION_KEY,
            "event_action": "trigger",
            "dedup_key": dedup_key or str(uuid.uuid4()),
            "payload": {
                "summary": summary,
                "severity": severity,
                "source": source,
                "custom_details": custom_details or {},
            },
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
            print(f"PagerDuty alert sent: {summary}")
            return True
        except Exception as exc:
            print(f"Error sending PagerDuty alert: {exc}")
            return False

    async def send_pagerduty_resolve(self, dedup_key: str) -> bool:
        """Send PagerDuty resolve event to close an open incident."""
        if not self.pagerduty_enabled:
            print("PagerDuty notifications not configured")
            return False

        payload = {
            "routing_key": settings.PAGERDUTY_INTEGRATION_KEY,
            "event_action": "resolve",
            "dedup_key": dedup_key,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
            print(f"PagerDuty incident resolved: {dedup_key}")
            return True
        except Exception as exc:
            print(f"Error resolving PagerDuty incident: {exc}")
            return False

    def format_alert_slack(self, alert: Dict) -> str:
        """Format alert data for Slack notification."""
        severity_emoji = {
            'critical': ':red_circle:',
            'high': ':large_orange_circle:',
            'medium': ':large_yellow_circle:',
            'low': ':large_blue_circle:'
        }
        emoji = severity_emoji.get(alert['severity'], ':white_circle:')
        return (
            f"{emoji} *DDoS Alert: {alert['alert_type']}* [{alert['severity'].upper()}]\n"
            f"*Target:* `{alert['target_ip']}` | *Source:* `{alert.get('source_ip', 'unknown')}`\n"
            f"*Time:* {alert.get('timestamp', datetime.utcnow().isoformat())}\n"
            f"{alert['description']}"
        )

    def format_alert_teams(self, alert: Dict) -> str:
        """Format alert data for Microsoft Teams notification."""
        return (
            f"🚨 **DDoS Alert: {alert['alert_type']}** [{alert['severity'].upper()}]\n\n"
            f"**Target IP:** {alert['target_ip']}  |  "
            f"**Source IP:** {alert.get('source_ip', 'unknown')}\n\n"
            f"**Time:** {alert.get('timestamp', datetime.utcnow().isoformat())}\n\n"
            f"{alert['description']}"
        )

    def format_alert_email(self, alert: Dict) -> tuple[str, str, str]:
        """Format alert data for email notification"""
        subject = f"🚨 DDoS Alert: {alert['alert_type']} [{alert['severity'].upper()}]"
        
        # Plain text version
        body = f"""
DDoS Protection Platform Alert

Alert Type: {alert['alert_type']}
Severity: {alert['severity'].upper()}
Target IP: {alert['target_ip']}
Source IP: {alert.get('source_ip', 'unknown')}
Description: {alert['description']}
Time: {alert.get('timestamp', datetime.utcnow().isoformat())}

This is an automated alert from your DDoS Protection Platform.
Please review and take appropriate action if necessary.
"""
        
        # HTML version
        severity_colors = {
            'critical': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#17a2b8'
        }
        color = severity_colors.get(alert['severity'], '#6c757d')
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 5px;">
        <h2 style="color: {color}; border-bottom: 2px solid {color}; padding-bottom: 10px;">
            🚨 DDoS Protection Alert
        </h2>
        
        <div style="background: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; font-weight: bold; width: 150px;">Alert Type:</td>
                    <td style="padding: 10px;">{alert['alert_type']}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; font-weight: bold;">Severity:</td>
                    <td style="padding: 10px;">
                        <span style="background-color: {color}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">
                            {alert['severity'].upper()}
                        </span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-weight: bold;">Target IP:</td>
                    <td style="padding: 10px; font-family: monospace;">{alert['target_ip']}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; font-weight: bold;">Source IP:</td>
                    <td style="padding: 10px; font-family: monospace;">{alert.get('source_ip', 'unknown')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-weight: bold;">Time:</td>
                    <td style="padding: 10px;">{alert.get('timestamp', datetime.utcnow().isoformat())}</td>
                </tr>
            </table>
            
            <div style="margin-top: 20px; padding: 15px; background-color: #e7f3ff; border-left: 4px solid #0066cc; border-radius: 3px;">
                <p style="margin: 0; font-weight: bold;">Description:</p>
                <p style="margin: 5px 0 0 0;">{alert['description']}</p>
            </div>
        </div>
        
        <p style="color: #666; font-size: 12px; margin-top: 20px;">
            This is an automated alert from your DDoS Protection Platform.
            Please review and take appropriate action if necessary.
        </p>
    </div>
</body>
</html>
"""
        
        return subject, body, html_body
    
    def format_alert_telegram(self, alert: Dict) -> str:
        """Format alert data for Telegram notification"""
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🔵'
        }
        emoji = severity_emoji.get(alert['severity'], '⚪')
        
        message = f"""
{emoji} <b>DDoS Alert: {alert['alert_type']}</b>

<b>Severity:</b> {alert['severity'].upper()}
<b>Target IP:</b> <code>{alert['target_ip']}</code>
<b>Source IP:</b> <code>{alert.get('source_ip', 'unknown')}</code>
<b>Time:</b> {alert.get('timestamp', datetime.utcnow().isoformat())}

<b>Description:</b>
{alert['description']}

⚡ <i>Automated alert from DDoS Protection Platform</i>
"""
        return message
    
    def format_alert_sms(self, alert: Dict) -> str:
        """Format alert data for SMS notification (must be concise)"""
        SMS_DESCRIPTION_MAX_LENGTH = 80  # SMS has limited character space
        SMS_MESSAGE_MAX_LENGTH = 160  # Standard SMS length limit
        
        description = alert['description'][:SMS_DESCRIPTION_MAX_LENGTH]
        message = f"DDoS Alert [{alert['severity'].upper()}]: {alert['alert_type']} targeting {alert['target_ip']}. {description}"
        return message[:SMS_MESSAGE_MAX_LENGTH]  # SMS limit
    
    async def send_alert_notification(self, alert: Dict, channels: List[str], recipients: Dict[str, str]) -> Dict[str, bool]:
        """
        Send alert notification through multiple channels
        
        Args:
            alert: Alert data dictionary
            channels: List of channels to send notification (email, telegram, sms, slack, teams)
            recipients: Dictionary mapping channel to recipient (e.g., {'email': 'admin@example.com', 'telegram': '123456789'})
        
        Returns:
            Dictionary with success status for each channel
        """
        results = {}
        
        # Send email
        if 'email' in channels and 'email' in recipients:
            subject, body, html_body = self.format_alert_email(alert)
            results['email'] = await self.send_email(recipients['email'], subject, body, html_body)
        
        # Send Telegram
        if 'telegram' in channels and 'telegram' in recipients:
            message = self.format_alert_telegram(alert)
            results['telegram'] = await self.send_telegram(recipients['telegram'], message)
        
        # Send SMS
        if 'sms' in channels and 'sms' in recipients:
            message = self.format_alert_sms(alert)
            results['sms'] = await self.send_sms(recipients['sms'], message)
        
        # Send Slack
        if 'slack' in channels:
            message = self.format_alert_slack(alert)
            webhook_url = recipients.get('slack') or getattr(settings, 'SLACK_WEBHOOK_URL', '')
            results['slack'] = await self.send_slack(message, webhook_url)
        
        # Send Microsoft Teams
        if 'teams' in channels:
            message = self.format_alert_teams(alert)
            webhook_url = recipients.get('teams') or getattr(settings, 'TEAMS_WEBHOOK_URL', '')
            results['teams'] = await self.send_teams(message, webhook_url)
        
        return results
    
    async def send_mitigation_notification(self, mitigation: Dict, channels: List[str], recipients: Dict[str, str]) -> Dict[str, bool]:
        """Send notification about mitigation action"""
        # Convert mitigation to alert-like format
        alert_data = {
            'alert_type': f"mitigation_{mitigation['action_type']}",
            'severity': 'high',
            'target_ip': mitigation.get('target_ip', 'N/A'),
            'source_ip': mitigation.get('source_ip', 'N/A'),
            'description': f"Mitigation action applied: {mitigation['action_type']}. Status: {mitigation['status']}",
            'timestamp': mitigation.get('created_at', datetime.utcnow().isoformat())
        }
        
        return await self.send_alert_notification(alert_data, channels, recipients)


# Global notification service instance
notification_service = NotificationService()


async def notify_alert(alert: Dict, isp_preferences: Dict = None):
    """
    Convenience function to send alert notifications based on ISP preferences
    
    Args:
        alert: Alert data dictionary
        isp_preferences: ISP notification preferences (channels, recipients)
    """
    if not isp_preferences:
        # Default to email only if no preferences provided
        isp_preferences = {
            'channels': ['email'],
            'recipients': {
                'email': settings.ALERT_EMAIL
            }
        }
    
    channels = isp_preferences.get('channels', ['email'])
    recipients = isp_preferences.get('recipients', {})
    
    # Add default Telegram chat ID if configured and not in recipients
    if 'telegram' in channels and 'telegram' not in recipients and settings.TELEGRAM_CHAT_ID:
        recipients['telegram'] = settings.TELEGRAM_CHAT_ID
    
    # Add Slack webhook URL if configured and not in recipients
    slack_url = getattr(settings, 'SLACK_WEBHOOK_URL', '')
    if 'slack' in channels and 'slack' not in recipients and slack_url:
        recipients['slack'] = slack_url

    # Add Teams webhook URL if configured and not in recipients
    teams_url = getattr(settings, 'TEAMS_WEBHOOK_URL', '')
    if 'teams' in channels and 'teams' not in recipients and teams_url:
        recipients['teams'] = teams_url
    
    results = await notification_service.send_alert_notification(alert, channels, recipients)
    
    print(f"Alert notification sent: {results}")
    return results
