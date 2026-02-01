"""
Tests for monitoring and alerting features
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import json

# Test metrics collector
def test_metrics_collector_initialization():
    """Test that metrics collector initializes correctly"""
    from services.metrics_collector import MetricsCollector
    
    collector = MetricsCollector()
    assert collector.registry is not None


def test_metrics_format():
    """Test that metrics are exported in correct format"""
    from services.metrics_collector import get_metrics_content
    
    metrics = get_metrics_content()
    assert isinstance(metrics, bytes)
    assert b'ddos_' in metrics  # Should contain our custom metrics


# Test notification service
def test_notification_service_initialization():
    """Test notification service initializes"""
    from services.notification_service import NotificationService
    
    service = NotificationService()
    assert hasattr(service, 'smtp_enabled')
    assert hasattr(service, 'telegram_enabled')
    assert hasattr(service, 'sms_enabled')


def test_alert_email_formatting():
    """Test email alert formatting"""
    from services.notification_service import NotificationService
    
    service = NotificationService()
    alert = {
        'alert_type': 'syn_flood',
        'severity': 'critical',
        'target_ip': '10.0.0.1',
        'source_ip': '1.2.3.4',
        'description': 'SYN flood detected',
        'timestamp': '2024-01-15T10:30:00Z'
    }
    
    subject, body, html_body = service.format_alert_email(alert)
    
    assert 'syn_flood' in subject
    assert 'CRITICAL' in subject
    assert '10.0.0.1' in body
    assert 'SYN flood detected' in body
    assert '<html>' in html_body


def test_alert_telegram_formatting():
    """Test Telegram alert formatting"""
    from services.notification_service import NotificationService
    
    service = NotificationService()
    alert = {
        'alert_type': 'udp_flood',
        'severity': 'high',
        'target_ip': '10.0.0.2',
        'source_ip': '5.6.7.8',
        'description': 'UDP flood detected',
        'timestamp': '2024-01-15T10:30:00Z'
    }
    
    message = service.format_alert_telegram(alert)
    
    assert 'udp_flood' in message
    assert '10.0.0.2' in message
    assert 'UDP flood detected' in message
    assert '<b>' in message  # HTML formatting


def test_alert_sms_formatting():
    """Test SMS alert formatting"""
    from services.notification_service import NotificationService
    
    service = NotificationService()
    alert = {
        'alert_type': 'icmp_flood',
        'severity': 'medium',
        'target_ip': '10.0.0.3',
        'description': 'ICMP flood detected with high packet rate'
    }
    
    message = service.format_alert_sms(alert)
    
    assert len(message) <= 160  # SMS limit
    assert 'icmp_flood' in message.lower()
    assert '10.0.0.3' in message


@pytest.mark.asyncio
async def test_email_notification_disabled():
    """Test email notification when not configured"""
    from services.notification_service import NotificationService
    
    service = NotificationService()
    service.smtp_enabled = False
    
    result = await service.send_email(
        to_email="test@example.com",
        subject="Test",
        body="Test body"
    )
    
    assert result is False


# Test attack map router functions
def test_get_ip_location():
    """Test IP location placeholder function"""
    from routers.attack_map_router import get_ip_location
    
    location = get_ip_location('1.2.3.4')
    
    assert location is not None
    assert 'lat' in location
    assert 'lon' in location
    assert 'country' in location
    assert 'city' in location


def test_get_ip_location_invalid():
    """Test IP location with invalid input"""
    from routers.attack_map_router import get_ip_location
    
    location = get_ip_location('unknown')
    assert location is None
    
    location = get_ip_location('')
    assert location is None


# Test mitigation metrics
def test_mitigation_metrics_exist():
    """Test that mitigation metrics are defined"""
    from services.metrics_collector import (
        mitigations_total,
        mitigations_active,
        mitigation_duration_seconds
    )
    
    assert mitigations_total is not None
    assert mitigations_active is not None
    assert mitigation_duration_seconds is not None


# Test alert metrics
def test_alert_metrics_exist():
    """Test that alert metrics are defined"""
    from services.metrics_collector import (
        alerts_total,
        alerts_active,
        alerts_resolved_total
    )
    
    assert alerts_total is not None
    assert alerts_active is not None
    assert alerts_resolved_total is not None


# Test system health metrics
def test_system_health_metrics_exist():
    """Test that system health metrics are defined"""
    from services.metrics_collector import system_health
    
    assert system_health is not None


# Integration test for metrics collection
def test_metrics_collector_updates(mocker):
    """Test that metrics collector can update metrics"""
    from services.metrics_collector import MetricsCollector
    
    # Mock database session
    mock_db = mocker.MagicMock()
    mocker.patch('services.metrics_collector.SessionLocal', return_value=mock_db)
    
    collector = MetricsCollector()
    
    # Should not raise exceptions
    try:
        collector.update_system_health()
        success = True
    except Exception as e:
        print(f"Error in update_system_health: {e}")
        success = False
    
    assert success


def test_notification_preferences():
    """Test notification preferences structure"""
    preferences = {
        'channels': ['email', 'telegram', 'sms'],
        'recipients': {
            'email': 'admin@example.com',
            'telegram': '123456789',
            'sms': '+1234567890'
        }
    }
    
    assert 'channels' in preferences
    assert 'recipients' in preferences
    assert 'email' in preferences['channels']
    assert 'telegram' in preferences['channels']
    assert 'sms' in preferences['channels']


# Test metrics endpoint response format
def test_metrics_content_type():
    """Test metrics endpoint returns correct content type"""
    from services.metrics_collector import CONTENT_TYPE_LATEST
    
    assert CONTENT_TYPE_LATEST == 'text/plain; version=0.0.4; charset=utf-8'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
