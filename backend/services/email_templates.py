"""
Branded HTML email template renderer.

All templates are rendered using plain f-strings — no third-party template
libraries are required.
"""
from datetime import datetime, timezone
from typing import Any


class BrandedEmailRenderer:
    """Renders ISP-branded transactional HTML emails."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe(value: Any, fallback: str = "") -> str:
        """Return *value* as a string, or *fallback* if falsy."""
        return str(value) if value else fallback

    def _header(self, branding: dict) -> str:
        primary = self._safe(branding.get("brand_primary_color"), "#1a73e8")
        logo_url = self._safe(branding.get("brand_logo_url"), "")
        company = self._safe(branding.get("brand_company_name"), "DDoS Protection Platform")
        logo_html = (
            f'<img src="{logo_url}" alt="{company}" '
            'style="max-height:50px;max-width:200px;vertical-align:middle;">'
            if logo_url
            else f'<span style="font-size:20px;font-weight:bold;">{company}</span>'
        )
        return f"""
<div style="background:{primary};padding:20px 30px;border-radius:6px 6px 0 0;">
  <a href="#" style="text-decoration:none;color:#ffffff;">{logo_html}</a>
</div>"""

    def _footer(self, branding: dict) -> str:
        company = self._safe(branding.get("brand_company_name"), "DDoS Protection Platform")
        support = self._safe(branding.get("brand_support_email"), "")
        support_line = (
            f'<a href="mailto:{support}" style="color:#555;">{support}</a>'
            if support
            else ""
        )
        return f"""
<div style="background:#f0f0f0;padding:16px 30px;border-radius:0 0 6px 6px;
            font-size:12px;color:#777;text-align:center;">
  &copy; {datetime.now(timezone.utc).year} {company}. All rights reserved.
  {"&nbsp;|&nbsp;" + support_line if support_line else ""}
</div>"""

    def _wrap(self, body: str, branding: dict) -> str:
        """Wrap *body* HTML with standard header/footer layout."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:20px;background:#f8f9fa;
             font-family:Arial,Helvetica,sans-serif;color:#333;">
<div style="max-width:620px;margin:0 auto;background:#fff;
            border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
  {self._header(branding)}
  <div style="padding:28px 30px;">
    {body}
  </div>
  {self._footer(branding)}
</div>
</body>
</html>"""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_alert_email(self, alert: dict, branding: dict) -> str:
        """Render an HTML DDoS alert notification email.

        Args:
            alert: Alert data dict (keys: alert_type, severity, target_ip,
                source_ip, description, timestamp).
            branding: ISP branding dict (brand_primary_color, brand_logo_url,
                brand_company_name, brand_support_email).

        Returns:
            Complete HTML email string with inline CSS.
        """
        primary = self._safe(branding.get("brand_primary_color"), "#1a73e8")
        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#17a2b8",
        }
        sev = self._safe(alert.get("severity"), "medium").lower()
        sev_color = severity_colors.get(sev, "#6c757d")
        ts = self._safe(alert.get("timestamp"), datetime.now(timezone.utc).isoformat())

        body = f"""
<h2 style="margin-top:0;color:{primary};">&#128680; DDoS Attack Alert</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
  <tr>
    <td style="padding:8px;font-weight:bold;width:140px;">Alert Type:</td>
    <td style="padding:8px;">{self._safe(alert.get("alert_type"))}</td>
  </tr>
  <tr style="background:#f8f9fa;">
    <td style="padding:8px;font-weight:bold;">Severity:</td>
    <td style="padding:8px;">
      <span style="background:{sev_color};color:#fff;padding:3px 10px;
                   border-radius:3px;font-weight:bold;">{sev.upper()}</span>
    </td>
  </tr>
  <tr>
    <td style="padding:8px;font-weight:bold;">Target IP:</td>
    <td style="padding:8px;font-family:monospace;">{self._safe(alert.get("target_ip"))}</td>
  </tr>
  <tr style="background:#f8f9fa;">
    <td style="padding:8px;font-weight:bold;">Source IP:</td>
    <td style="padding:8px;font-family:monospace;">{self._safe(alert.get("source_ip"), "unknown")}</td>
  </tr>
  <tr>
    <td style="padding:8px;font-weight:bold;">Time:</td>
    <td style="padding:8px;">{ts}</td>
  </tr>
</table>
<div style="background:#e7f3ff;border-left:4px solid {primary};
            padding:14px;border-radius:3px;">
  <strong>Description:</strong><br>
  {self._safe(alert.get("description"))}
</div>
<p style="margin-top:20px;color:#555;font-size:13px;">
  Please review and take appropriate action in your DDoS Protection Dashboard.
</p>"""
        return self._wrap(body, branding)

    def render_monthly_report_email(self, report: dict, branding: dict) -> str:
        """Render an HTML monthly attack-summary report email.

        Args:
            report: Report data dict (keys: period, total_attacks, peak_gbps,
                mitigated, top_attack_types).
            branding: ISP branding dict.

        Returns:
            Complete HTML email string with inline CSS.
        """
        primary = self._safe(branding.get("brand_primary_color"), "#1a73e8")
        period = self._safe(report.get("period"), "Last 30 days")
        total = report.get("total_attacks", 0)
        peak = report.get("peak_gbps", 0)
        mitigated = report.get("mitigated", 0)
        top_types: list = report.get("top_attack_types", [])

        top_rows = "".join(
            f"<tr><td style='padding:6px 8px;'>{t}</td></tr>"
            for t in top_types
        ) or "<tr><td style='padding:6px 8px;color:#777;'>None</td></tr>"

        body = f"""
<h2 style="margin-top:0;color:{primary};">Monthly Security Report</h2>
<p style="color:#555;">Period: <strong>{period}</strong></p>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
  <tr style="background:{primary};color:#fff;">
    <th style="padding:10px;">Total Attacks</th>
    <th style="padding:10px;">Mitigated</th>
    <th style="padding:10px;">Peak (Gbps)</th>
  </tr>
  <tr style="text-align:center;">
    <td style="padding:12px;font-size:24px;font-weight:bold;">{total}</td>
    <td style="padding:12px;font-size:24px;font-weight:bold;color:#28a745;">{mitigated}</td>
    <td style="padding:12px;font-size:24px;font-weight:bold;color:#dc3545;">{peak}</td>
  </tr>
</table>
<h3 style="color:{primary};">Top Attack Types</h3>
<table style="width:100%;border-collapse:collapse;">
  {top_rows}
</table>
<p style="margin-top:20px;color:#555;font-size:13px;">
  Log in to your portal for the full report and detailed analytics.
</p>"""
        return self._wrap(body, branding)

    def render_welcome_email(self, user: dict, branding: dict) -> str:
        """Render an HTML welcome email for newly registered users.

        Args:
            user: User data dict (keys: username, email, role).
            branding: ISP branding dict.

        Returns:
            Complete HTML email string with inline CSS.
        """
        primary = self._safe(branding.get("brand_primary_color"), "#1a73e8")
        company = self._safe(branding.get("brand_company_name"), "DDoS Protection Platform")
        domain = self._safe(branding.get("brand_portal_domain"), "")
        portal_link = f"https://{domain}" if domain else "#"
        username = self._safe(user.get("username"), "User")
        role = self._safe(user.get("role"), "viewer")

        body = f"""
<h2 style="margin-top:0;color:{primary};">Welcome to {company}!</h2>
<p>Hi <strong>{username}</strong>,</p>
<p>Your account has been successfully created. Here are your details:</p>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
  <tr style="background:#f8f9fa;">
    <td style="padding:8px;font-weight:bold;width:120px;">Username:</td>
    <td style="padding:8px;">{username}</td>
  </tr>
  <tr>
    <td style="padding:8px;font-weight:bold;">Email:</td>
    <td style="padding:8px;">{self._safe(user.get("email"))}</td>
  </tr>
  <tr style="background:#f8f9fa;">
    <td style="padding:8px;font-weight:bold;">Role:</td>
    <td style="padding:8px;">{role.capitalize()}</td>
  </tr>
</table>
<p style="text-align:center;">
  <a href="{portal_link}"
     style="background:{primary};color:#fff;padding:12px 28px;
            border-radius:4px;text-decoration:none;font-weight:bold;">
    Access Your Dashboard
  </a>
</p>
<p style="margin-top:20px;color:#555;font-size:13px;">
  If you did not request this account, please contact your administrator immediately.
</p>"""
        return self._wrap(body, branding)
