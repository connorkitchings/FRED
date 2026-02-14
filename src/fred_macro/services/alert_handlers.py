"""Alert notification handlers for the FRED Macro Dashboard."""

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from src.fred_macro.logging_config import get_logger

logger = get_logger(__name__)


class AlertHandler(ABC):
    """Abstract base class for alert notification handlers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)

    @abstractmethod
    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send a single alert notification."""
        pass

    @abstractmethod
    def send_digest(
        self, alerts: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> bool:
        """Send a digest of multiple alerts."""
        pass


class EmailAlertHandler(AlertHandler):
    """Email-based alert handler with digest support."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_user = config.get("smtp_user", "")
        self.smtp_password = config.get("smtp_password", "")
        self.smtp_tls = config.get("smtp_tls", True)
        self.from_address = config.get("from_address", "fred-alerts@example.com")
        self.to_addresses = config.get("to_addresses", [])

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection."""
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        server.starttls() if self.smtp_tls else None
        if self.smtp_user and self.smtp_password:
            server.login(self.smtp_user, self.smtp_password)
        return server

    def _format_alert_html(self, alert: Dict[str, Any]) -> str:
        """Format a single alert as HTML."""
        severity = alert.get("severity", "info")
        severity_colors = {
            "critical": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
        }
        color = severity_colors.get(severity, "#6c757d")

        return f"""
        <div style="margin: 10px 0; padding: 15px; border-left: 4px solid {color}; background-color: #f8f9fa;">
            <h3 style="margin: 0 0 10px 0; color: {color};">
                [{severity.upper()}] {alert.get("rule_name", "Unknown")}
            </h3>
            <p style="margin: 5px 0;"><strong>Description:</strong> {alert.get("description", "N/A")}</p>
            <p style="margin: 5px 0;"><strong>Timestamp:</strong> {alert.get("timestamp", "N/A")}</p>
            <p style="margin: 5px 0;"><strong>Details:</strong> {alert.get("details", "N/A")}</p>
        </div>
        """

    def _format_digest_html(
        self, alerts: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        """Format daily digest as HTML email."""
        critical_count = summary.get("critical_count", 0)
        warning_count = summary.get("warning_count", 0)
        info_count = summary.get("info_count", 0)
        total_alerts = len(alerts)

        # Group alerts by severity
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        warning_alerts = [a for a in alerts if a.get("severity") == "warning"]
        info_alerts = [a for a in alerts if a.get("severity") == "info"]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .summary {{ background-color: #ecf0f1; padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .summary-item {{ display: inline-block; margin: 0 20px; text-align: center; }}
                .summary-number {{ font-size: 32px; font-weight: bold; }}
                .critical {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
                .info {{ color: #17a2b8; }}
                .alert-section {{ margin: 30px 0; }}
                .alert-section h2 {{ border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>FRED Macro Dashboard - Daily Alert Digest</h1>
                <p>{summary.get("date", "Unknown Date")}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <div class="summary-item">
                    <div class="summary-number critical">{critical_count}</div>
                    <div>Critical</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number warning">{warning_count}</div>
                    <div>Warning</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number info">{info_count}</div>
                    <div>Info</div>
                </div>
                <div class="summary-item">
                    <div class="summary-number">{total_alerts}</div>
                    <div>Total</div>
                </div>
            </div>
        """

        # Add critical alerts section
        if critical_alerts:
            html += """
            <div class="alert-section">
                <h2 class="critical">Critical Alerts</h2>
            """
            for alert in critical_alerts[:10]:  # Limit to 10
                html += self._format_alert_html(alert)
            if len(critical_alerts) > 10:
                html += f"<p><em>... and {len(critical_alerts) - 10} more critical alerts</em></p>"
            html += "</div>"

        # Add warning alerts section
        if warning_alerts:
            html += """
            <div class="alert-section">
                <h2 class="warning">Warning Alerts</h2>
            """
            for alert in warning_alerts[:10]:
                html += self._format_alert_html(alert)
            if len(warning_alerts) > 10:
                html += f"<p><em>... and {len(warning_alerts) - 10} more warning alerts</em></p>"
            html += "</div>"

        # Add info alerts section
        if info_alerts:
            html += """
            <div class="alert-section">
                <h2 class="info">Info Alerts</h2>
            """
            for alert in info_alerts[:5]:
                html += self._format_alert_html(alert)
            if len(info_alerts) > 5:
                html += (
                    f"<p><em>... and {len(info_alerts) - 5} more info alerts</em></p>"
                )
            html += "</div>"

        html += """
            <div style="margin-top: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 5px;">
                <p><strong>FRED Macro Dashboard</strong></p>
                <p>This is an automated alert digest. To configure alerts, edit config/alerts.yaml</p>
            </div>
        </body>
        </html>
        """

        return html

    def _format_digest_plain(
        self, alerts: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        """Format daily digest as plain text."""
        lines = [
            "FRED Macro Dashboard - Daily Alert Digest",
            f"Date: {summary.get('date', 'Unknown')}",
            "",
            "Summary:",
            f"  Critical: {summary.get('critical_count', 0)}",
            f"  Warning: {summary.get('warning_count', 0)}",
            f"  Info: {summary.get('info_count', 0)}",
            f"  Total: {len(alerts)}",
            "",
            "=" * 60,
            "",
        ]

        for alert in alerts:
            lines.extend(
                [
                    f"[{alert.get('severity', 'INFO').upper()}] {alert.get('rule_name', 'Unknown')}",
                    f"  Description: {alert.get('description', 'N/A')}",
                    f"  Timestamp: {alert.get('timestamp', 'N/A')}",
                    f"  Details: {alert.get('details', 'N/A')}",
                    "",
                ]
            )

        lines.extend(["=" * 60, "FRED Macro Dashboard - Automated Alert System"])

        return "\n".join(lines)

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send a single alert via email."""
        if not self.enabled:
            logger.debug("Email handler disabled, skipping alert")
            return True

        if not self.to_addresses:
            logger.warning("No email recipients configured")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = (
                f"[FRED Alert] [{alert.get('severity', 'INFO').upper()}] {alert.get('rule_name', 'Unknown')}"
            )
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)

            # Plain text version
            text_body = f"""
Alert: {alert.get("rule_name", "Unknown")}
Severity: {alert.get("severity", "info")}
Description: {alert.get("description", "N/A")}
Timestamp: {alert.get("timestamp", "N/A")}
Details: {alert.get("details", "N/A")}
            """
            msg.attach(MIMEText(text_body, "plain"))

            # HTML version
            html_body = self._format_alert_html(alert)
            msg.attach(MIMEText(html_body, "html"))

            with self._create_smtp_connection() as server:
                server.send_message(msg)

            logger.info(f"Alert email sent: {alert.get('rule_name')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False

    def send_digest(
        self, alerts: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> bool:
        """Send a daily digest of alerts via email."""
        if not self.enabled:
            logger.debug("Email handler disabled, skipping digest")
            return True

        if not self.to_addresses:
            logger.warning("No email recipients configured")
            return False

        if not alerts:
            logger.debug("No alerts to send in digest")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = (
                f"[FRED Daily Digest] {summary.get('date', 'Today')} - {len(alerts)} Alerts"
            )
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)

            # Plain text version
            text_body = self._format_digest_plain(alerts, summary)
            msg.attach(MIMEText(text_body, "plain"))

            # HTML version
            html_body = self._format_digest_html(alerts, summary)
            msg.attach(MIMEText(html_body, "html"))

            with self._create_smtp_connection() as server:
                server.send_message(msg)

            logger.info(f"Daily digest sent with {len(alerts)} alerts")
            return True

        except Exception as e:
            logger.error(f"Failed to send digest email: {e}")
            return False


class ConsoleAlertHandler(AlertHandler):
    """Console-based alert handler for development/testing."""

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Print alert to console."""
        if not self.enabled:
            return True

        severity = alert.get("severity", "info").upper()
        print(f"\n[ALERT - {severity}] {alert.get('rule_name', 'Unknown')}")
        print(f"  Description: {alert.get('description', 'N/A')}")
        print(f"  Timestamp: {alert.get('timestamp', 'N/A')}")
        print(f"  Details: {alert.get('details', 'N/A')}")
        return True

    def send_digest(
        self, alerts: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> bool:
        """Print digest to console."""
        if not self.enabled:
            return True

        print(f"\n{'=' * 60}")
        print(f"DAILY DIGEST - {summary.get('date', 'Today')}")
        print(f"{'=' * 60}")
        print(f"Critical: {summary.get('critical_count', 0)}")
        print(f"Warning: {summary.get('warning_count', 0)}")
        print(f"Info: {summary.get('info_count', 0)}")
        print(f"Total: {len(alerts)}")
        print(f"{'=' * 60}")

        for alert in alerts:
            self.send_alert(alert)

        return True
