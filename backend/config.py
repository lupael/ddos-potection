from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import List, Optional


# ---------------------------------------------------------------------------
# Sub-models (plain BaseModel – not loaded from env directly)
# ---------------------------------------------------------------------------

class DatabaseSettings(BaseModel):
    DATABASE_URL: str = "postgresql://ddos_user:ddos_pass@localhost:5432/ddos_platform"


class RedisSettings(BaseModel):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0


class DetectionSettings(BaseModel):
    SYN_FLOOD_THRESHOLD: int = 10000
    UDP_FLOOD_THRESHOLD: int = 50000
    ICMP_FLOOD_THRESHOLD: int = 10000
    DNS_AMPLIFICATION_THRESHOLD: int = 500
    NTP_AMPLIFICATION_THRESHOLD: int = 468
    MEMCACHED_AMPLIFICATION_THRESHOLD: int = 1400
    SSDP_AMPLIFICATION_THRESHOLD: int = 400
    TCP_RST_FLOOD_THRESHOLD: int = 5000
    TCP_ACK_FLOOD_THRESHOLD: int = 10000
    ENTROPY_THRESHOLD: float = 3.5
    VOLUMETRIC_SRC_ENTROPY_THRESHOLD: float = 5.0
    VOLUMETRIC_DST_ENTROPY_THRESHOLD: float = 2.0
    SCANNING_SRC_ENTROPY_THRESHOLD: float = 4.0
    SCANNING_DST_ENTROPY_THRESHOLD: float = 4.0


class NotificationSettings(BaseModel):
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL: str = "admin@example.com"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SLACK_WEBHOOK_URL: str = ""
    TEAMS_WEBHOOK_URL: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""


class BGPSettings(BaseModel):
    BGP_ENABLED: bool = False
    BGP_DAEMON: str = "exabgp"
    BGP_BLACKHOLE_NEXTHOP: str = "192.0.2.1"
    BGP_BLACKHOLE_COMMUNITY: str = "65535:666"
    EXABGP_CMD_PIPE: str = "/var/run/exabgp.cmd"
    FRR_VTYSH_CMD: str = "/usr/bin/vtysh"
    BIRD_CMD: str = "birdc"
    BIRD_CONTROL_SOCKET: str = "/var/run/bird/bird.ctl"


class CaptureSettings(BaseModel):
    PCAP_ENABLED: bool = True
    PCAP_DIR: str = "/var/lib/ddos-protection/pcaps"
    PCAP_MAX_PACKETS: int = 10000
    VLAN_UNTAGGING_ENABLED: bool = True
    AF_PACKET_ENABLED: bool = True
    AF_XDP_ENABLED: bool = False


# ---------------------------------------------------------------------------
# Root settings class – all flat fields are kept for backward compatibility.
# Sub-model instances are populated automatically via model_validator.
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    # API Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "postgresql://ddos_user:ddos_pass@localhost:5432/ddos_platform"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000"
    ]
    
    # NetFlow/sFlow
    NETFLOW_PORT: int = 2055
    SFLOW_PORT: int = 6343
    IPFIX_PORT: int = 4739
    
    # Detection Thresholds
    SYN_FLOOD_THRESHOLD: int = 10000  # packets per second
    UDP_FLOOD_THRESHOLD: int = 50000  # packets per second
    ICMP_FLOOD_THRESHOLD: int = 10000  # packets per minute
    DNS_AMPLIFICATION_THRESHOLD: int = 500  # bytes per packet
    NTP_AMPLIFICATION_THRESHOLD: int = 468   # bytes per packet (NTP monlist response size)
    MEMCACHED_AMPLIFICATION_THRESHOLD: int = 1400  # bytes per packet
    SSDP_AMPLIFICATION_THRESHOLD: int = 400  # bytes per packet
    TCP_RST_FLOOD_THRESHOLD: int = 5000   # RST packets per minute
    TCP_ACK_FLOOD_THRESHOLD: int = 10000  # ACK packets per minute
    ENTROPY_THRESHOLD: float = 3.5
    VOLUMETRIC_SRC_ENTROPY_THRESHOLD: float = 5.0
    VOLUMETRIC_DST_ENTROPY_THRESHOLD: float = 2.0
    SCANNING_SRC_ENTROPY_THRESHOLD: float = 4.0
    SCANNING_DST_ENTROPY_THRESHOLD: float = 4.0
    
    # Mitigation
    AUTO_MITIGATION: bool = True
    MITIGATION_DURATION: int = 300  # seconds
    
    # Alerts
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL: str = "admin@example.com"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SLACK_WEBHOOK_URL: str = ""       # Slack Incoming Webhook URL
    TEAMS_WEBHOOK_URL: str = ""       # Microsoft Teams Incoming Webhook URL
    
    # SMS/Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # Payment
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Monitoring
    PROMETHEUS_PORT: int = 9090
    
    # BGP Blackholing (RTBH) Configuration
    BGP_ENABLED: bool = False  # Set to True to enable BGP blackholing
    BGP_DAEMON: str = "exabgp"  # Options: exabgp, frr, bird
    BGP_BLACKHOLE_NEXTHOP: str = "192.0.2.1"  # Standard blackhole next-hop
    BGP_BLACKHOLE_COMMUNITY: str = "65535:666"  # RFC 7999 blackhole community
    
    # ExaBGP Configuration
    EXABGP_CMD_PIPE: str = "/var/run/exabgp.cmd"  # Named pipe for ExaBGP commands
    
    # FRR Configuration
    FRR_VTYSH_CMD: str = "/usr/bin/vtysh"  # Path to vtysh command
    
    # BIRD Configuration
    BIRD_CMD: str = "birdc"  # Path to birdc command
    BIRD_CONTROL_SOCKET: str = "/var/run/bird/bird.ctl"  # BIRD control socket
    
    # GeoIP Configuration (for geo-blocking)
    GEOIP_DATABASE_PATH: str = "/usr/share/GeoIP/GeoLite2-Country.mmdb"
    GEOIP_CITY_DB_PATH: str = "/usr/share/GeoIP/GeoLite2-City.mmdb"

    # Threat Intelligence
    THREAT_INTEL_ENABLED: bool = True
    THREAT_INTEL_REFRESH_INTERVAL: int = 3600  # seconds

    # PagerDuty
    PAGERDUTY_INTEGRATION_KEY: str = ""
    PAGERDUTY_ENABLED: bool = False

    # SIEM Export
    SIEM_ENABLED: bool = False
    SIEM_HOST: str = ""
    SIEM_PORT: int = 514
    SIEM_FORMAT: str = "cef"  # "cef" or "syslog"
    SIEM_FACILITY: int = 16   # local0

    # NetBox IPAM
    NETBOX_URL: str = ""
    NETBOX_TOKEN: str = ""
    NETBOX_ENABLED: bool = False

    # SNMP Traps
    SNMP_ENABLED: bool = False
    SNMP_MANAGER_HOST: str = ""
    SNMP_MANAGER_PORT: int = 162
    SNMP_COMMUNITY: str = "public"
    SNMP_ENTERPRISE_OID: str = "1.3.6.1.4.1.99999"

    # Kafka Flow Pipeline
    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_FLOW_TOPIC: str = "ddos-flows"
    KAFKA_CONSUMER_GROUP: str = "ddos-detector"
    
    # Packet Capture Configuration
    PCAP_ENABLED: bool = True  # Enable PCAP capture features
    PCAP_DIR: str = "/var/lib/ddos-protection/pcaps"  # Directory for PCAP files
    PCAP_MAX_PACKETS: int = 10000  # Maximum packets per PCAP file
    VLAN_UNTAGGING_ENABLED: bool = True  # Remove VLAN tags from captured packets
    AF_PACKET_ENABLED: bool = True  # Enable AF_PACKET capture (Linux only)
    AF_XDP_ENABLED: bool = False  # Enable AF_XDP capture (requires libxdp)
    
    # Threshold Configuration
    DEFAULT_PPS_THRESHOLD: int = 10000  # Default packets per second threshold
    DEFAULT_BPS_THRESHOLD: int = 100000000  # Default bytes per second (100 Mbps)
    DEFAULT_FPS_THRESHOLD: int = 1000  # Default flows per second threshold
    THRESHOLD_CHECK_INTERVAL: int = 1  # Seconds between threshold checks
    
    # Script Execution
    SCRIPTS_ENABLED: bool = True  # Enable script execution for block/notify
    SCRIPTS_DIR: str = "/etc/ddos-protection/scripts"  # Directory for scripts
    SCRIPT_TIMEOUT: int = 30  # Maximum script execution time in seconds

    # Webhook Delivery
    WEBHOOK_MAX_RETRIES: int = 5          # Maximum delivery retries (exponential back-off)
    WEBHOOK_RETRY_BACKOFF: float = 2.0    # Multiplier for retry delay
    WEBHOOK_TIMEOUT: int = 10             # HTTP request timeout in seconds

    # HTTP Flood / Slowloris Detection
    HTTP_FLOOD_THRESHOLD: int = 10000     # requests per minute
    SLOWLORIS_THRESHOLD: int = 500        # half-open connections

    # DNS Water-Torture Detection
    DNS_NXDOMAIN_THRESHOLD: int = 1000    # NXDOMAIN responses per minute

    # ML Adaptive Baselines
    BASELINE_WINDOW_SIZE: int = 1000      # rolling buffer size per prefix
    BASELINE_MIN_SAMPLES: int = 100       # minimum samples before ML kicks in

    # Anomaly Detector Poll Interval (fallback when no Redis event received)
    DETECTOR_POLL_INTERVAL: int = 30      # seconds

    # Redis Sentinel HA
    REDIS_SENTINEL_ENABLED: bool = False
    REDIS_SENTINEL_HOSTS: str = "localhost:26379"

    # Traffic Forecasting
    FORECAST_HISTORY_WEEKS: int = 4

    # RPKI Validation
    RPKI_VALIDATION_ENABLED: bool = True
    RPKI_API_URL: str = "https://rpki.cloudflare.com/api/v1/validity"

    # Shadow Mode – ML detectors emit tagged alerts but skip mitigation
    SHADOW_MODE: bool = False

    # TLS-wrapped NetFlow receiver
    TLS_FLOW_ENABLED: bool = False
    TLS_FLOW_PORT: int = 2056
    TLS_FLOW_CERTFILE: Optional[str] = None
    TLS_FLOW_KEYFILE: Optional[str] = None

    # ---------------------------------------------------------------------------
    # Sub-model instances – populated after all flat fields are validated.
    # External code may use settings.database.DATABASE_URL etc. as an alternative
    # to the flat settings.DATABASE_URL attribute.
    # ---------------------------------------------------------------------------
    database: Optional[DatabaseSettings] = None
    redis: Optional[RedisSettings] = None
    detection: Optional[DetectionSettings] = None
    notification: Optional[NotificationSettings] = None
    bgp: Optional[BGPSettings] = None
    capture: Optional[CaptureSettings] = None

    def model_post_init(self, __context: object) -> None:
        """Populate sub-model instances from the already-validated flat fields."""
        object.__setattr__(self, "database", DatabaseSettings(
            DATABASE_URL=self.DATABASE_URL,
        ))
        object.__setattr__(self, "redis", RedisSettings(
            REDIS_HOST=self.REDIS_HOST,
            REDIS_PORT=self.REDIS_PORT,
            REDIS_DB=self.REDIS_DB,
        ))
        object.__setattr__(self, "detection", DetectionSettings(
            SYN_FLOOD_THRESHOLD=self.SYN_FLOOD_THRESHOLD,
            UDP_FLOOD_THRESHOLD=self.UDP_FLOOD_THRESHOLD,
            ICMP_FLOOD_THRESHOLD=self.ICMP_FLOOD_THRESHOLD,
            DNS_AMPLIFICATION_THRESHOLD=self.DNS_AMPLIFICATION_THRESHOLD,
            NTP_AMPLIFICATION_THRESHOLD=self.NTP_AMPLIFICATION_THRESHOLD,
            MEMCACHED_AMPLIFICATION_THRESHOLD=self.MEMCACHED_AMPLIFICATION_THRESHOLD,
            SSDP_AMPLIFICATION_THRESHOLD=self.SSDP_AMPLIFICATION_THRESHOLD,
            TCP_RST_FLOOD_THRESHOLD=self.TCP_RST_FLOOD_THRESHOLD,
            TCP_ACK_FLOOD_THRESHOLD=self.TCP_ACK_FLOOD_THRESHOLD,
            ENTROPY_THRESHOLD=self.ENTROPY_THRESHOLD,
            VOLUMETRIC_SRC_ENTROPY_THRESHOLD=self.VOLUMETRIC_SRC_ENTROPY_THRESHOLD,
            VOLUMETRIC_DST_ENTROPY_THRESHOLD=self.VOLUMETRIC_DST_ENTROPY_THRESHOLD,
            SCANNING_SRC_ENTROPY_THRESHOLD=self.SCANNING_SRC_ENTROPY_THRESHOLD,
            SCANNING_DST_ENTROPY_THRESHOLD=self.SCANNING_DST_ENTROPY_THRESHOLD,
        ))
        object.__setattr__(self, "notification", NotificationSettings(
            SMTP_HOST=self.SMTP_HOST,
            SMTP_PORT=self.SMTP_PORT,
            SMTP_USER=self.SMTP_USER,
            SMTP_PASSWORD=self.SMTP_PASSWORD,
            ALERT_EMAIL=self.ALERT_EMAIL,
            TELEGRAM_BOT_TOKEN=self.TELEGRAM_BOT_TOKEN,
            TELEGRAM_CHAT_ID=self.TELEGRAM_CHAT_ID,
            SLACK_WEBHOOK_URL=self.SLACK_WEBHOOK_URL,
            TEAMS_WEBHOOK_URL=self.TEAMS_WEBHOOK_URL,
            TWILIO_ACCOUNT_SID=self.TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN=self.TWILIO_AUTH_TOKEN,
            TWILIO_PHONE_NUMBER=self.TWILIO_PHONE_NUMBER,
        ))
        object.__setattr__(self, "bgp", BGPSettings(
            BGP_ENABLED=self.BGP_ENABLED,
            BGP_DAEMON=self.BGP_DAEMON,
            BGP_BLACKHOLE_NEXTHOP=self.BGP_BLACKHOLE_NEXTHOP,
            BGP_BLACKHOLE_COMMUNITY=self.BGP_BLACKHOLE_COMMUNITY,
            EXABGP_CMD_PIPE=self.EXABGP_CMD_PIPE,
            FRR_VTYSH_CMD=self.FRR_VTYSH_CMD,
            BIRD_CMD=self.BIRD_CMD,
            BIRD_CONTROL_SOCKET=self.BIRD_CONTROL_SOCKET,
        ))
        object.__setattr__(self, "capture", CaptureSettings(
            PCAP_ENABLED=self.PCAP_ENABLED,
            PCAP_DIR=self.PCAP_DIR,
            PCAP_MAX_PACKETS=self.PCAP_MAX_PACKETS,
            VLAN_UNTAGGING_ENABLED=self.VLAN_UNTAGGING_ENABLED,
            AF_PACKET_ENABLED=self.AF_PACKET_ENABLED,
            AF_XDP_ENABLED=self.AF_XDP_ENABLED,
        ))

    class Config:
        env_file = ".env"

settings = Settings()
