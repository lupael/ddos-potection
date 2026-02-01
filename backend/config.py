from pydantic_settings import BaseSettings
from typing import List

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
    
    class Config:
        env_file = ".env"

settings = Settings()
