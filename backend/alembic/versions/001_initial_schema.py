"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "isps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("subscription_status", sa.String(50), nullable=True, server_default="trial"),
        sa.Column("subscription_plan", sa.String(50), nullable=True, server_default="basic"),
        sa.Column("api_key", sa.String(255), nullable=True, unique=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("paypal_customer_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_isps_id", "isps", ["id"])
    op.create_index("ix_isps_name", "isps", ["name"])
    op.create_index("ix_isps_email", "isps", ["email"])
    op.create_index("ix_isps_api_key", "isps", ["api_key"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=True, server_default="viewer"),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("rule_type", sa.String(50), nullable=True),
        sa.Column("condition", sa.JSON(), nullable=True),
        sa.Column("action", sa.String(50), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rules_id", "rules", ["id"])

    op.create_table(
        "traffic_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("dest_ip", sa.String(45), nullable=True),
        sa.Column("protocol", sa.String(20), nullable=True),
        sa.Column("packets", sa.Integer(), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("flags", sa.String(50), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=True, server_default=sa.false()),
    )
    op.create_index("ix_traffic_logs_id", "traffic_logs", ["id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("alert_type", sa.String(50), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("target_ip", sa.String(45), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alerts_id", "alerts", ["id"])

    op.create_table(
        "mitigation_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mitigation_actions_id", "mitigation_actions", ["id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("report_type", sa.String(50), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_format", sa.String(10), nullable=True, server_default="txt"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reports_id", "reports", ["id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("plan_name", sa.String(50), nullable=True),
        sa.Column("plan_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("billing_cycle", sa.String(20), nullable=True, server_default="monthly"),
        sa.Column("status", sa.String(50), nullable=True, server_default="active"),
        sa.Column("start_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_subscriptions_id", "subscriptions", ["id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True, server_default="USD"),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("payment_gateway_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="pending"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payment_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_payments_id", "payments", ["id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("invoice_number", sa.String(100), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True, server_default="USD"),
        sa.Column("status", sa.String(50), nullable=True, server_default="unpaid"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoices_id", "invoices", ["id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])

    op.create_table(
        "sla_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=False),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=False),
        sa.Column("attack_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("mitigated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ttd_seconds", sa.Integer(), nullable=True),
        sa.Column("ttm_seconds", sa.Integer(), nullable=True),
        sa.Column("sla_met", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sla_records_id", "sla_records", ["id"])
    op.create_index("ix_sla_records_isp_id", "sla_records", ["isp_id"])
    op.create_index("ix_sla_records_alert_id", "sla_records", ["alert_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("client_ip", sa.String(45), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_isp_id", "audit_logs", ["isp_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("isp_id", sa.Integer(), sa.ForeignKey("isps.id"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhooks_id", "webhooks", ["id"])
    op.create_index("ix_webhooks_isp_id", "webhooks", ["isp_id"])


def downgrade() -> None:
    op.drop_table("webhooks")
    op.drop_table("audit_logs")
    op.drop_table("sla_records")
    op.drop_table("invoices")
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("reports")
    op.drop_table("mitigation_actions")
    op.drop_table("alerts")
    op.drop_table("traffic_logs")
    op.drop_table("rules")
    op.drop_table("users")
    op.drop_table("isps")
