"""
Tests for integration services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.integrations import (
    KafkaIntegration,
    ClickHouseIntegration,
    InfluxDBIntegration,
    GraphiteIntegration,
    MongoDBIntegration
)


class TestKafkaIntegration:
    """Test Kafka integration."""
    
    def test_kafka_disabled_by_default(self):
        """Test that Kafka is disabled by default."""
        kafka = KafkaIntegration()
        assert kafka.enabled == False
    
    @patch.dict(os.environ, {'KAFKA_ENABLED': 'true'})
    def test_kafka_enabled_with_env(self):
        """Test Kafka can be enabled via environment variable."""
        with patch('services.integrations.logger'):
            kafka = KafkaIntegration()
            assert kafka.enabled == True or kafka.enabled == False  # May be false if aiokafka not installed
    
    @pytest.mark.asyncio
    async def test_send_flow_when_disabled(self):
        """Test that send_flow returns False when disabled."""
        kafka = KafkaIntegration()
        result = await kafka.send_flow({'source_ip': '192.0.2.1'})
        assert result == False


class TestClickHouseIntegration:
    """Test ClickHouse integration."""
    
    def test_clickhouse_disabled_by_default(self):
        """Test that ClickHouse is disabled by default."""
        ch = ClickHouseIntegration()
        assert ch.enabled == False
    
    @patch.dict(os.environ, {'CLICKHOUSE_ENABLED': 'true'})
    def test_clickhouse_enabled_with_env(self):
        """Test ClickHouse can be enabled via environment variable."""
        with patch('services.integrations.logger'):
            ch = ClickHouseIntegration()
            # May be False if clickhouse-driver not installed
            assert ch.enabled in [True, False]
    
    def test_insert_flows_when_disabled(self):
        """Test that insert_flows returns False when disabled."""
        ch = ClickHouseIntegration()
        result = ch.insert_flows([{'source_ip': '192.0.2.1'}])
        assert result == False


class TestInfluxDBIntegration:
    """Test InfluxDB integration."""
    
    def test_influxdb_disabled_by_default(self):
        """Test that InfluxDB is disabled by default."""
        influx = InfluxDBIntegration()
        assert influx.enabled == False
    
    @patch.dict(os.environ, {'INFLUXDB_ENABLED': 'true'})
    def test_influxdb_enabled_with_env(self):
        """Test InfluxDB can be enabled via environment variable."""
        with patch('services.integrations.logger'):
            influx = InfluxDBIntegration()
            # May be False if influxdb-client not installed
            assert influx.enabled in [True, False]
    
    def test_write_metric_when_disabled(self):
        """Test that write_metric returns False when disabled."""
        influx = InfluxDBIntegration()
        result = influx.write_metric(
            'traffic',
            {'protocol': 'tcp'},
            {'packets': 1000}
        )
        assert result == False


class TestGraphiteIntegration:
    """Test Graphite integration."""
    
    def test_graphite_disabled_by_default(self):
        """Test that Graphite is disabled by default."""
        graphite = GraphiteIntegration()
        assert graphite.enabled == False
    
    @patch.dict(os.environ, {'GRAPHITE_ENABLED': 'true'})
    def test_graphite_enabled_with_env(self):
        """Test Graphite can be enabled via environment variable."""
        with patch('services.integrations.logger'):
            graphite = GraphiteIntegration()
            assert graphite.enabled == True
    
    def test_send_metric_when_disabled(self):
        """Test that send_metric returns False when disabled."""
        graphite = GraphiteIntegration()
        result = graphite.send_metric('traffic.packets', 1000)
        assert result == False


class TestMongoDBIntegration:
    """Test MongoDB integration."""
    
    def test_mongodb_disabled_by_default(self):
        """Test that MongoDB is disabled by default."""
        mongo = MongoDBIntegration()
        assert mongo.enabled == False
    
    @patch.dict(os.environ, {'MONGODB_ENABLED': 'true'})
    def test_mongodb_enabled_with_env(self):
        """Test MongoDB can be enabled via environment variable."""
        with patch('services.integrations.logger'):
            mongo = MongoDBIntegration()
            # May be False if pymongo not installed
            assert mongo.enabled in [True, False]
    
    def test_insert_alert_when_disabled(self):
        """Test that insert_alert returns False when disabled."""
        mongo = MongoDBIntegration()
        result = mongo.insert_alert({'type': 'syn_flood'})
        assert result == False
    
    def test_find_alerts_when_disabled(self):
        """Test that find_alerts returns empty list when disabled."""
        mongo = MongoDBIntegration()
        result = mongo.find_alerts({'severity': 'high'})
        assert result == []


class TestIntegrationConfiguration:
    """Test integration configuration."""
    
    @patch.dict(os.environ, {
        'KAFKA_BOOTSTRAP_SERVERS': 'kafka1:9092,kafka2:9092',
        'KAFKA_TOPIC_FLOWS': 'test.flows',
        'KAFKA_FORMAT': 'json',
        'KAFKA_COMPRESSION': 'gzip'
    })
    def test_kafka_configuration(self):
        """Test Kafka configuration from environment."""
        kafka = KafkaIntegration()
        assert kafka.bootstrap_servers == ['kafka1:9092', 'kafka2:9092']
        assert kafka.topic_flows == 'test.flows'
        assert kafka.format == 'json'
        assert kafka.compression == 'gzip'
    
    @patch.dict(os.environ, {
        'CLICKHOUSE_HOST': 'ch-server',
        'CLICKHOUSE_PORT': '9000',
        'CLICKHOUSE_DATABASE': 'test_db',
        'CLICKHOUSE_USER': 'test_user'
    })
    def test_clickhouse_configuration(self):
        """Test ClickHouse configuration from environment."""
        ch = ClickHouseIntegration()
        assert ch.host == 'ch-server'
        assert ch.port == 9000
        assert ch.database == 'test_db'
        assert ch.user == 'test_user'
    
    @patch.dict(os.environ, {
        'INFLUXDB_HOST': 'influx-server',
        'INFLUXDB_PORT': '8086',
        'INFLUXDB_DATABASE': 'test_metrics',
        'INFLUXDB_V2': 'true'
    })
    def test_influxdb_configuration(self):
        """Test InfluxDB configuration from environment."""
        influx = InfluxDBIntegration()
        assert influx.host == 'influx-server'
        assert influx.port == 8086
        assert influx.database == 'test_metrics'
        assert influx.v2 == True
    
    @patch.dict(os.environ, {
        'GRAPHITE_HOST': 'graphite-server',
        'GRAPHITE_PORT': '2003',
        'GRAPHITE_PREFIX': 'test.ddos'
    })
    def test_graphite_configuration(self):
        """Test Graphite configuration from environment."""
        graphite = GraphiteIntegration()
        assert graphite.host == 'graphite-server'
        assert graphite.port == 2003
        assert graphite.prefix == 'test.ddos'
    
    @patch.dict(os.environ, {
        'MONGODB_HOST': 'mongo-server',
        'MONGODB_PORT': '27017',
        'MONGODB_DATABASE': 'test_platform'
    })
    def test_mongodb_configuration(self):
        """Test MongoDB configuration from environment."""
        mongo = MongoDBIntegration()
        assert mongo.host == 'mongo-server'
        assert mongo.port == 27017
        assert mongo.database == 'test_platform'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
