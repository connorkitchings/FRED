"""Alert management service for the FRED Macro Dashboard."""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.fred_macro.db import get_connection
from src.fred_macro.logging_config import get_logger
from src.fred_macro.services.alert_handlers import (
    AlertHandler,
    ConsoleAlertHandler,
    EmailAlertHandler,
)

logger = get_logger(__name__)


class AlertRule:
    """Represents a single alert rule with evaluation logic."""

    def __init__(self, config: Dict[str, Any]):
        self.name = config["name"]
        self.enabled = config.get("enabled", True)
        self.severity = config.get("severity", "info")
        self.description = config.get("description", "")
        self.condition = config.get("condition", {})
        self.cooldown_hours = config.get("cooldown_hours", 24)
        self._last_alert_time: Optional[datetime] = None

    def is_on_cooldown(self) -> bool:
        """Check if rule is currently on cooldown."""
        if self._last_alert_time is None:
            return False
        cooldown_end = self._last_alert_time + timedelta(hours=self.cooldown_hours)
        return datetime.now() < cooldown_end

    def mark_alerted(self):
        """Mark that an alert was just triggered."""
        self._last_alert_time = datetime.now()

    def evaluate(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate the rule against current context. Returns alert dict if triggered."""
        if not self.enabled or self.is_on_cooldown():
            return None

        condition_type = self.condition.get("type")

        if condition_type == "ingestion_status":
            return self._evaluate_ingestion_status(context)
        elif condition_type == "dq_count":
            return self._evaluate_dq_count(context)
        elif condition_type == "data_freshness":
            return self._evaluate_data_freshness(context)
        elif condition_type == "missing_data":
            return self._evaluate_missing_data(context)
        elif condition_type == "error_rate":
            return self._evaluate_error_rate(context)

        return None

    def _evaluate_ingestion_status(
        self, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate ingestion status condition."""
        run_status = context.get("run_status", "")
        target_statuses = self.condition.get("statuses", [])

        if run_status in target_statuses:
            return self._create_alert(
                f"Ingestion run completed with status: {run_status}",
                {"run_id": context.get("run_id"), "status": run_status},
            )
        return None

    def _evaluate_dq_count(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate data quality count condition."""
        severity = self.condition.get("severity", "critical")
        threshold = self.condition.get("threshold", 1)
        operator = self.condition.get("operator", ">=")

        dq_findings = context.get("dq_findings", [])
        count = sum(1 for f in dq_findings if f.get("severity") == severity)

        triggered = False
        if operator == ">=" and count >= threshold:
            triggered = True
        elif operator == ">" and count > threshold:
            triggered = True
        elif operator == "=" and count == threshold:
            triggered = True

        if triggered:
            return self._create_alert(
                f"{count} {severity} DQ findings detected (threshold: {threshold})",
                {"count": count, "severity": severity, "threshold": threshold},
            )
        return None

    def _evaluate_data_freshness(
        self, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate data freshness condition."""
        max_age_days = self.condition.get("max_age_days", 60)
        stale_series = context.get("stale_series", [])

        if stale_series:
            series_list = ", ".join(
                [s.get("series_id", "unknown") for s in stale_series[:5]]
            )
            if len(stale_series) > 5:
                series_list += f" and {len(stale_series) - 5} more"

            return self._create_alert(
                f"{len(stale_series)} series haven't been updated in {max_age_days} days",
                {
                    "stale_count": len(stale_series),
                    "max_age_days": max_age_days,
                    "series": series_list,
                },
            )
        return None

    def _evaluate_missing_data(
        self, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate missing data condition."""
        days = self.condition.get("days", 30)
        missing_series = context.get("missing_series", [])

        if missing_series:
            series_list = ", ".join(
                [s.get("series_id", "unknown") for s in missing_series[:5]]
            )
            if len(missing_series) > 5:
                series_list += f" and {len(missing_series) - 5} more"

            return self._create_alert(
                f"{len(missing_series)} series have no data in the last {days} days",
                {
                    "missing_count": len(missing_series),
                    "days": days,
                    "series": series_list,
                },
            )
        return None

    def _evaluate_error_rate(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate error rate condition."""
        threshold = self.condition.get("threshold", 0.20)
        operator = self.condition.get("operator", ">=")

        total = context.get("total_series", 0)
        failed = context.get("failed_series", 0)

        if total == 0:
            return None

        error_rate = failed / total

        triggered = False
        if operator == ">=" and error_rate >= threshold:
            triggered = True
        elif operator == ">" and error_rate > threshold:
            triggered = True

        if triggered:
            return self._create_alert(
                f"High API error rate: {error_rate:.1%} ({failed}/{total} series failed)",
                {"error_rate": error_rate, "failed": failed, "total": total},
            )
        return None

    def _create_alert(self, details: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create an alert dictionary."""
        return {
            "rule_name": self.name,
            "severity": self.severity,
            "description": self.description,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "metadata": metadata,
        }


class AlertManager:
    """Manages alert rules, evaluation, and notification dispatch."""

    def __init__(self, config_path: str = "config/alerts.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.rules: List[AlertRule] = []
        self.handlers: List[AlertHandler] = []
        self._alerts_buffer: List[Dict[str, Any]] = []
        self._init_rules()
        self._init_handlers()

    def _load_config(self) -> Dict[str, Any]:
        """Load alert configuration from YAML."""
        if not self.config_path.exists():
            logger.warning(f"Alert config not found at {self.config_path}")
            return {}

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f) or {}

    def _init_rules(self):
        """Initialize alert rules from configuration."""
        rules_config = self.config.get("rules", [])
        for rule_config in rules_config:
            try:
                rule = AlertRule(rule_config)
                self.rules.append(rule)
                logger.debug(f"Initialized alert rule: {rule.name}")
            except Exception as e:
                logger.error(f"Failed to initialize rule: {e}")

    def _init_handlers(self):
        """Initialize notification handlers."""
        # Email handler
        email_config = self.config.get("email", {})
        # Substitute environment variables
        email_config = self._substitute_env_vars(email_config)
        self.handlers.append(EmailAlertHandler(email_config))

        # Console handler (for development)
        console_config = {"enabled": True}
        self.handlers.append(ConsoleAlertHandler(console_config))

    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in config values."""
        result = {}
        for key, value in config.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                # Extract var name and default
                var_expr = value[2:-1]  # Remove ${ and }
                if ":-" in var_expr:
                    var_name, default = var_expr.split(":-", 1)
                    result[key] = os.getenv(var_name, default)
                else:
                    result[key] = os.getenv(var_expr, "")
            elif isinstance(value, list):
                result[key] = [
                    self._substitute_env_vars_in_string(item)
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _substitute_env_vars_in_string(self, value: str) -> str:
        """Substitute environment variables in a string."""
        if value.startswith("${") and value.endswith("}"):
            var_expr = value[2:-1]
            if ":-" in var_expr:
                var_name, default = var_expr.split(":-", 1)
                return os.getenv(var_name, default)
            return os.getenv(var_expr, "")
        return value

    def evaluate_all_rules(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all rules and return triggered alerts."""
        triggered_alerts = []

        for rule in self.rules:
            try:
                alert = rule.evaluate(context)
                if alert:
                    triggered_alerts.append(alert)
                    rule.mark_alerted()
                    logger.info(f"Alert triggered: {rule.name} ({rule.severity})")
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")

        return triggered_alerts

    def send_alert(self, alert: Dict[str, Any]):
        """Send an alert through all enabled handlers."""
        global_config = self.config.get("global", {})
        digest_mode = global_config.get("digest_mode", True)

        if digest_mode:
            # Buffer for digest
            self._alerts_buffer.append(alert)
            logger.debug(f"Alert buffered for digest: {alert['rule_name']}")
        else:
            # Send immediately
            for handler in self.handlers:
                try:
                    handler.send_alert(alert)
                except Exception as e:
                    logger.error(f"Handler failed to send alert: {e}")

    def send_digest(self):
        """Send daily digest of all buffered alerts."""
        if not self._alerts_buffer:
            logger.debug("No alerts to send in digest")
            return

        # Calculate summary
        critical_count = sum(
            1 for a in self._alerts_buffer if a.get("severity") == "critical"
        )
        warning_count = sum(
            1 for a in self._alerts_buffer if a.get("severity") == "warning"
        )
        info_count = sum(1 for a in self._alerts_buffer if a.get("severity") == "info")

        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "total_count": len(self._alerts_buffer),
        }

        # Send through all handlers
        for handler in self.handlers:
            try:
                handler.send_digest(self._alerts_buffer, summary)
            except Exception as e:
                logger.error(f"Handler failed to send digest: {e}")

        # Clear buffer
        logger.info(f"Digest sent with {len(self._alerts_buffer)} alerts")
        self._alerts_buffer = []

    def check_and_alert(self, context: Dict[str, Any]):
        """Evaluate rules and send alerts for any triggered rules."""
        alerts = self.evaluate_all_rules(context)
        for alert in alerts:
            self.send_alert(alert)

    def get_buffered_alerts(self) -> List[Dict[str, Any]]:
        """Get current buffered alerts (for testing/debugging)."""
        return self._alerts_buffer.copy()

    def clear_buffer(self):
        """Clear the alerts buffer."""
        self._alerts_buffer = []

    def persist_alert(self, alert: Dict[str, Any]):
        """Persist alert to database for history tracking."""
        try:
            conn = get_connection()
            conn.execute(
                """
                INSERT INTO alert_history 
                (alert_id, rule_name, severity, description, timestamp, details, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.get("alert_id", str(time.time())),
                    alert["rule_name"],
                    alert["severity"],
                    alert["description"],
                    alert["timestamp"],
                    alert["details"],
                    str(alert.get("metadata", {})),
                ),
            )
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist alert: {e}")


def create_alert_history_table():
    """Create alert history table if it doesn't exist."""
    try:
        conn = get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                alert_id VARCHAR PRIMARY KEY,
                rule_name VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                description TEXT,
                timestamp TIMESTAMP NOT NULL,
                details TEXT,
                metadata TEXT,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        """)
        conn.close()
        logger.info("Alert history table created/verified")
    except Exception as e:
        logger.error(f"Failed to create alert history table: {e}")
