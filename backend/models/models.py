from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class ISP(Base):
    __tablename__ = "isps"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    subscription_status = Column(String(50), default="trial")  # trial, active, suspended, cancelled
    subscription_plan = Column(String(50), default="basic")  # basic, professional, enterprise
    api_key = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    users = relationship("User", back_populates="isp")
    rules = relationship("Rule", back_populates="isp")
    alerts = relationship("Alert", back_populates="isp")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    role = Column(String(50), default="viewer")  # admin, operator, viewer
    isp_id = Column(Integer, ForeignKey("isps.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    isp = relationship("ISP", back_populates="users")

class Rule(Base):
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, index=True)
    isp_id = Column(Integer, ForeignKey("isps.id"))
    name = Column(String(255))
    rule_type = Column(String(50))  # rate_limit, ip_block, protocol_filter, geo_block
    condition = Column(JSON)  # Store conditions as JSON
    action = Column(String(50))  # block, rate_limit, redirect, alert
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    isp = relationship("ISP", back_populates="rules")

class TrafficLog(Base):
    __tablename__ = "traffic_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    isp_id = Column(Integer, ForeignKey("isps.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    source_ip = Column(String(45))
    dest_ip = Column(String(45))
    protocol = Column(String(20))
    packets = Column(Integer)
    bytes = Column(Integer)
    flags = Column(String(50))
    is_anomaly = Column(Boolean, default=False)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    isp_id = Column(Integer, ForeignKey("isps.id"))
    alert_type = Column(String(50))  # syn_flood, udp_flood, dns_amplification
    severity = Column(String(20))  # low, medium, high, critical
    source_ip = Column(String(45))
    target_ip = Column(String(45))
    description = Column(Text)
    status = Column(String(50), default="active")  # active, mitigated, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    
    isp = relationship("ISP", back_populates="alerts")

class MitigationAction(Base):
    __tablename__ = "mitigation_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"))
    action_type = Column(String(50))  # firewall, bgp_blackhole, flowspec, rate_limit
    details = Column(JSON)
    status = Column(String(50), default="pending")  # pending, active, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    isp_id = Column(Integer, ForeignKey("isps.id"))
    report_type = Column(String(50))  # monthly, weekly, incident
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    file_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
