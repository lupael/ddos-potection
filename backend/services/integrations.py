"""
Integration services for external systems.

This module provides integrations with various external systems including:
- Kafka (for data export)
- ClickHouse (for analytics)
- InfluxDB (for time-series metrics)
- Graphite (for metrics)
- MongoDB/FerretDB (for flexible schema)

All integrations are optional and can be enabled via environment variables.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class KafkaIntegration:
    """Kafka integration for exporting flows and alerts."""
    
    def __init__(self):
        self.enabled = os.getenv('KAFKA_ENABLED', 'false').lower() == 'true'
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
        self.topic_flows = os.getenv('KAFKA_TOPIC_FLOWS', 'ddos.flows')
        self.topic_alerts = os.getenv('KAFKA_TOPIC_ALERTS', 'ddos.alerts')
        self.topic_mitigations = os.getenv('KAFKA_TOPIC_MITIGATIONS', 'ddos.mitigations')
        self.format = os.getenv('KAFKA_FORMAT', 'json')
        self.compression = os.getenv('KAFKA_COMPRESSION', 'gzip')
        self.producer = None
        
        if self.enabled:
            self._init_producer()
    
    def _init_producer(self):
        """Initialize Kafka producer."""
        try:
            from aiokafka import AIOKafkaProducer
            # Producer will be initialized asynchronously when needed
            logger.info(f"Kafka integration enabled: {self.bootstrap_servers}")
        except ImportError:
            logger.warning("aiokafka not installed. Install with: pip install aiokafka")
            self.enabled = False
    
    async def send_flow(self, flow_data: Dict[str, Any]) -> bool:
        """
        Send flow data to Kafka.
        
        Args:
            flow_data: Flow record dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            from aiokafka import AIOKafkaProducer
            
            if not self.producer:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    compression_type=self.compression,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await self.producer.start()
            
            # Convert to JSON format
            message = {
                'timestamp': flow_data.get('timestamp', datetime.utcnow().isoformat()),
                'isp_id': flow_data.get('isp_id'),
                'source_ip': flow_data.get('source_ip'),
                'dest_ip': flow_data.get('dest_ip'),
                'source_port': flow_data.get('source_port'),
                'dest_port': flow_data.get('dest_port'),
                'protocol': flow_data.get('protocol'),
                'packets': flow_data.get('packets'),
                'bytes': flow_data.get('bytes'),
                'tcp_flags': flow_data.get('tcp_flags', []),
                'router_ip': flow_data.get('router_ip')
            }
            
            await self.producer.send_and_wait(self.topic_flows, message)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send flow to Kafka: {e}")
            return False
    
    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send alert to Kafka."""
        if not self.enabled:
            return False
        
        try:
            from aiokafka import AIOKafkaProducer
            
            if not self.producer:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    compression_type=self.compression,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await self.producer.start()
            
            await self.producer.send_and_wait(self.topic_alerts, alert_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert to Kafka: {e}")
            return False
    
    async def close(self):
        """Close Kafka producer."""
        if self.producer:
            await self.producer.stop()


class ClickHouseIntegration:
    """ClickHouse integration for analytics."""
    
    def __init__(self):
        self.enabled = os.getenv('CLICKHOUSE_ENABLED', 'false').lower() == 'true'
        self.host = os.getenv('CLICKHOUSE_HOST', 'localhost')
        self.port = int(os.getenv('CLICKHOUSE_PORT', '9000'))
        self.database = os.getenv('CLICKHOUSE_DATABASE', 'ddos_analytics')
        self.user = os.getenv('CLICKHOUSE_USER', 'default')
        self.password = os.getenv('CLICKHOUSE_PASSWORD', '')
        self.client = None
        
        if self.enabled:
            self._init_client()
    
    def _init_client(self):
        """Initialize ClickHouse client."""
        try:
            from clickhouse_driver import Client
            self.client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info(f"ClickHouse integration enabled: {self.host}:{self.port}")
        except ImportError:
            logger.warning("clickhouse-driver not installed. Install with: pip install clickhouse-driver")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            self.enabled = False
    
    def insert_flows(self, flows: List[Dict[str, Any]]) -> bool:
        """Insert flow records into ClickHouse."""
        if not self.enabled or not self.client:
            return False
        
        try:
            # Prepare data for bulk insert
            data = [
                (
                    flow.get('timestamp'),
                    flow.get('isp_id'),
                    flow.get('source_ip'),
                    flow.get('dest_ip'),
                    flow.get('source_port'),
                    flow.get('dest_port'),
                    flow.get('protocol'),
                    flow.get('packets'),
                    flow.get('bytes'),
                    flow.get('tcp_flags'),
                    flow.get('router_ip')
                )
                for flow in flows
            ]
            
            self.client.execute(
                'INSERT INTO traffic_flows VALUES',
                data
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert flows to ClickHouse: {e}")
            return False
    
    def query(self, sql: str) -> List[tuple]:
        """Execute query on ClickHouse."""
        if not self.enabled or not self.client:
            return []
        
        try:
            return self.client.execute(sql)
        except Exception as e:
            logger.error(f"Failed to query ClickHouse: {e}")
            return []


class InfluxDBIntegration:
    """InfluxDB integration for time-series metrics."""
    
    def __init__(self):
        self.enabled = os.getenv('INFLUXDB_ENABLED', 'false').lower() == 'true'
        self.host = os.getenv('INFLUXDB_HOST', 'localhost')
        self.port = int(os.getenv('INFLUXDB_PORT', '8086'))
        self.database = os.getenv('INFLUXDB_DATABASE', 'ddos_metrics')
        self.user = os.getenv('INFLUXDB_USER', 'ddos')
        self.password = os.getenv('INFLUXDB_PASSWORD', '')
        self.v2 = os.getenv('INFLUXDB_V2', 'false').lower() == 'true'
        self.client = None
        
        if self.enabled:
            self._init_client()
    
    def _init_client(self):
        """Initialize InfluxDB client."""
        try:
            if self.v2:
                from influxdb_client import InfluxDBClient
                org = os.getenv('INFLUXDB_ORG', 'my-org')
                token = os.getenv('INFLUXDB_TOKEN', '')
                bucket = os.getenv('INFLUXDB_BUCKET', 'ddos-metrics')
                
                self.client = InfluxDBClient(
                    url=f"http://{self.host}:{self.port}",
                    token=token,
                    org=org
                )
                self.write_api = self.client.write_api()
                logger.info(f"InfluxDB 2.x integration enabled: {self.host}:{self.port}")
            else:
                from influxdb import InfluxDBClient as InfluxDBClientV1
                self.client = InfluxDBClientV1(
                    host=self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    database=self.database
                )
                logger.info(f"InfluxDB 1.x integration enabled: {self.host}:{self.port}")
        except ImportError:
            logger.warning("influxdb-client not installed. Install with: pip install influxdb-client")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            self.enabled = False
    
    def write_metric(self, measurement: str, tags: Dict[str, str], 
                     fields: Dict[str, Any], timestamp: Optional[datetime] = None) -> bool:
        """Write metric to InfluxDB."""
        if not self.enabled or not self.client:
            return False
        
        try:
            if self.v2:
                from influxdb_client import Point
                point = Point(measurement)
                for key, value in tags.items():
                    point = point.tag(key, value)
                for key, value in fields.items():
                    point = point.field(key, value)
                if timestamp:
                    point = point.time(timestamp)
                
                bucket = os.getenv('INFLUXDB_BUCKET', 'ddos-metrics')
                self.write_api.write(bucket=bucket, record=point)
            else:
                json_body = [{
                    'measurement': measurement,
                    'tags': tags,
                    'fields': fields,
                    'time': timestamp.isoformat() if timestamp else datetime.utcnow().isoformat()
                }]
                self.client.write_points(json_body)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write metric to InfluxDB: {e}")
            return False


class GraphiteIntegration:
    """Graphite integration for metrics."""
    
    def __init__(self):
        self.enabled = os.getenv('GRAPHITE_ENABLED', 'false').lower() == 'true'
        self.host = os.getenv('GRAPHITE_HOST', 'localhost')
        self.port = int(os.getenv('GRAPHITE_PORT', '2003'))
        self.prefix = os.getenv('GRAPHITE_PREFIX', 'ddos.protection')
        self.socket = None
        
        if self.enabled:
            logger.info(f"Graphite integration enabled: {self.host}:{self.port}")
    
    def send_metric(self, metric_name: str, value: float, timestamp: Optional[int] = None) -> bool:
        """Send metric to Graphite."""
        if not self.enabled:
            return False
        
        try:
            import socket
            
            if timestamp is None:
                timestamp = int(datetime.utcnow().timestamp())
            
            message = f"{self.prefix}.{metric_name} {value} {timestamp}\n"
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            sock.sendall(message.encode('utf-8'))
            sock.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send metric to Graphite: {e}")
            return False


class MongoDBIntegration:
    """MongoDB/FerretDB integration for flexible schema storage."""
    
    def __init__(self):
        self.enabled = os.getenv('MONGODB_ENABLED', 'false').lower() == 'true'
        self.host = os.getenv('MONGODB_HOST', 'localhost')
        self.port = int(os.getenv('MONGODB_PORT', '27017'))
        self.database = os.getenv('MONGODB_DATABASE', 'ddos_platform')
        self.client = None
        self.db = None
        
        if self.enabled:
            self._init_client()
    
    def _init_client(self):
        """Initialize MongoDB/FerretDB client."""
        try:
            from pymongo import MongoClient
            
            connection_string = f"mongodb://{self.host}:{self.port}/"
            self.client = MongoClient(connection_string)
            self.db = self.client[self.database]
            
            # Test connection
            self.client.server_info()
            logger.info(f"MongoDB integration enabled: {self.host}:{self.port}")
            
        except ImportError:
            logger.warning("pymongo not installed. Install with: pip install pymongo")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.enabled = False
    
    def insert_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Insert alert document into MongoDB."""
        if not self.enabled or not self.db:
            return False
        
        try:
            self.db.alerts.insert_one(alert_data)
            return True
        except Exception as e:
            logger.error(f"Failed to insert alert to MongoDB: {e}")
            return False
    
    def insert_flow(self, flow_data: Dict[str, Any]) -> bool:
        """Insert flow document into MongoDB."""
        if not self.enabled or not self.db:
            return False
        
        try:
            self.db.flows.insert_one(flow_data)
            return True
        except Exception as e:
            logger.error(f"Failed to insert flow to MongoDB: {e}")
            return False
    
    def find_alerts(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query alerts from MongoDB."""
        if not self.enabled or not self.db:
            return []
        
        try:
            return list(self.db.alerts.find(query))
        except Exception as e:
            logger.error(f"Failed to query alerts from MongoDB: {e}")
            return []


# Global integration instances
kafka_integration = KafkaIntegration()
clickhouse_integration = ClickHouseIntegration()
influxdb_integration = InfluxDBIntegration()
graphite_integration = GraphiteIntegration()
mongodb_integration = MongoDBIntegration()


async def export_flow_to_all(flow_data: Dict[str, Any]):
    """Export flow data to all enabled integrations."""
    # Kafka
    if kafka_integration.enabled:
        await kafka_integration.send_flow(flow_data)
    
    # ClickHouse (batch insert in production)
    if clickhouse_integration.enabled:
        clickhouse_integration.insert_flows([flow_data])
    
    # MongoDB
    if mongodb_integration.enabled:
        mongodb_integration.insert_flow(flow_data)


def export_metrics_to_all(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Export metrics to all enabled integrations."""
    tags = tags or {}
    
    # InfluxDB
    if influxdb_integration.enabled:
        influxdb_integration.write_metric(
            'traffic',
            tags,
            {metric_name: value}
        )
    
    # Graphite
    if graphite_integration.enabled:
        metric_path = '.'.join([tags.get(k, '') for k in tags.keys()] + [metric_name])
        graphite_integration.send_metric(metric_path, value)
