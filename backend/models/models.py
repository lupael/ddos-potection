from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Numeric
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
    stripe_customer_id = Column(String(255), nullable=True)
    paypal_customer_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    users = relationship("User", back_populates="isp")
    rules = relationship("Rule", back_populates="isp")
    alerts = relationship("Alert", back_populates="isp")
    subscriptions = relationship("Subscription", back_populates="isp")
    payments = relationship("Payment", back_populates="isp")

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
    file_format = Column(String(10), default="txt")  # pdf, csv, txt
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    isp_id = Column(Integer, ForeignKey("isps.id"))
    plan_name = Column(String(50))  # basic, professional, enterprise
    plan_price = Column(Numeric(10, 2))  # Monthly price
    billing_cycle = Column(String(20), default="monthly")  # monthly, yearly
    status = Column(String(50), default="active")  # active, cancelled, expired, suspended
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True))
    auto_renew = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    isp = relationship("ISP", back_populates="subscriptions")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    isp_id = Column(Integer, ForeignKey("isps.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    amount = Column(Numeric(10, 2))
    currency = Column(String(10), default="USD")
    payment_method = Column(String(50))  # stripe, paypal, bkash
    payment_gateway_id = Column(String(255))  # Transaction ID from payment gateway
    status = Column(String(50), default="pending")  # pending, completed, failed, refunded
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)  # Store additional payment data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    isp = relationship("ISP", back_populates="payments")

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    isp_id = Column(Integer, ForeignKey("isps.id"))
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    invoice_number = Column(String(100), unique=True, index=True)
    amount = Column(Numeric(10, 2))
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="unpaid")  # unpaid, paid, overdue, cancelled
    due_date = Column(DateTime(timezone=True))
    paid_date = Column(DateTime(timezone=True), nullable=True)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
