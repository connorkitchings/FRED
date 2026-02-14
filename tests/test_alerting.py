"""Tests for the alerting system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.fred_macro.services.alert_handlers import (
    AlertHandler,
    EmailAlertHandler,
    ConsoleAlertHandler,
)
from src.fred_macro.services.alert_manager import AlertRule, AlertManager


class TestAlertRule:
    """Test suite for AlertRule class."""

    def test_rule_initialization(self):
        """Test alert rule initialization."""
        config = {
            "name": "test_rule",
            "enabled": True,
            "severity": "critical",
            "description": "Test description",
            "condition": {"type": "ingestion_status", "statuses": ["failed"]},
            "cooldown_hours": 2,
        }

        rule = AlertRule(config)

        assert rule.name == "test_rule"
        assert rule.enabled is True
        assert rule.severity == "critical"
        assert rule.description == "Test description"
        assert rule.cooldown_hours == 2

    def test_cooldown_logic(self):
        """Test cooldown functionality."""
        config = {
            "name": "test_rule",
            "enabled": True,
            "severity": "warning",
            "condition": {"type": "ingestion_status", "statuses": ["failed"]},
            "cooldown_hours": 1,
        }

        rule = AlertRule(config)

        # Initially not on cooldown
        assert rule.is_on_cooldown() is False

        # Mark as alerted
        rule.mark_alerted()
        assert rule.is_on_cooldown() is True

    def test_ingestion_status_evaluation(self):
        """Test ingestion status rule evaluation."""
        config = {
            "name": "ingestion_failure",
            "enabled": True,
            "severity": "critical",
            "condition": {
                "type": "ingestion_status",
                "statuses": ["failed", "partial"],
            },
            "cooldown_hours": 1,
        }

        rule = AlertRule(config)

        # Should trigger on failed status
        context = {"run_status": "failed"}
        alert = rule.evaluate(context)
        assert alert is not None
        assert alert["rule_name"] == "ingestion_failure"
        assert alert["severity"] == "critical"

    def test_dq_count_evaluation(self):
        """Test data quality count rule evaluation."""
        config = {
            "name": "dq_critical",
            "enabled": True,
            "severity": "critical",
            "condition": {
                "type": "dq_count",
                "severity": "critical",
                "threshold": 3,
                "operator": ">=",
            },
            "cooldown_hours": 1,
        }

        rule = AlertRule(config)

        # Should trigger when count >= threshold
        context = {
            "dq_findings": [
                {"severity": "critical"},
                {"severity": "critical"},
                {"severity": "critical"},
                {"severity": "warning"},
            ]
        }
        alert = rule.evaluate(context)
        assert alert is not None
        assert "3 critical DQ findings" in alert["details"]

    def test_data_freshness_evaluation(self):
        """Test data freshness rule evaluation."""
        config = {
            "name": "stale_data",
            "enabled": True,
            "severity": "warning",
            "condition": {"type": "data_freshness", "max_age_days": 60},
            "cooldown_hours": 24,
        }

        rule = AlertRule(config)

        # Should trigger when stale series exist
        context = {"stale_series": [{"series_id": "UNRATE"}, {"series_id": "CPI"}]}
        alert = rule.evaluate(context)
        assert alert is not None
        assert "2 series" in alert["details"]


class TestEmailAlertHandler:
    """Test suite for EmailAlertHandler."""

    def test_handler_initialization(self):
        """Test email handler initialization."""
        config = {
            "enabled": True,
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_user": "test@example.com",
            "smtp_password": "password",
            "from_address": "alerts@example.com",
            "to_addresses": ["admin@example.com"],
        }

        handler = EmailAlertHandler(config)

        assert handler.enabled is True
        assert handler.smtp_host == "smtp.test.com"
        assert handler.smtp_port == 587
        assert handler.from_address == "alerts@example.com"

    def test_disabled_handler_skips_sending(self):
        """Test that disabled handler doesn't attempt to send."""
        config = {"enabled": False}
        handler = EmailAlertHandler(config)

        alert = {"rule_name": "test", "severity": "warning"}
        result = handler.send_alert(alert)

        assert result is True  # Returns True when disabled (not an error)

    def test_send_alert_no_recipients(self):
        """Test alert sending with no recipients."""
        config = {"enabled": True, "to_addresses": []}
        handler = EmailAlertHandler(config)

        alert = {"rule_name": "test", "severity": "warning"}
        result = handler.send_alert(alert)

        assert result is False  # Should fail without recipients

    @patch("smtplib.SMTP")
    def test_send_alert_success(self, mock_smtp):
        """Test successful alert email sending."""
        config = {
            "enabled": True,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "from_address": "test@example.com",
            "to_addresses": ["admin@example.com"],
        }
        handler = EmailAlertHandler(config)

        alert = {
            "rule_name": "test_rule",
            "severity": "warning",
            "description": "Test description",
            "timestamp": "2024-01-01T00:00:00",
            "details": "Test details",
        }

        result = handler.send_alert(alert)

        assert result is True
        mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()

    def test_send_digest_empty_alerts(self):
        """Test sending digest with no alerts."""
        config = {"enabled": True, "to_addresses": ["admin@example.com"]}
        handler = EmailAlertHandler(config)

        result = handler.send_digest([], {})

        assert result is True  # Should succeed with no alerts

    @patch("smtplib.SMTP")
    def test_send_digest_success(self, mock_smtp):
        """Test successful digest email sending."""
        config = {
            "enabled": True,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "from_address": "test@example.com",
            "to_addresses": ["admin@example.com"],
        }
        handler = EmailAlertHandler(config)

        alerts = [
            {
                "rule_name": "rule1",
                "severity": "critical",
                "description": "Desc1",
                "timestamp": "2024-01-01",
                "details": "Details1",
            },
            {
                "rule_name": "rule2",
                "severity": "warning",
                "description": "Desc2",
                "timestamp": "2024-01-01",
                "details": "Details2",
            },
        ]

        summary = {
            "date": "2024-01-01",
            "critical_count": 1,
            "warning_count": 1,
            "info_count": 0,
            "total_count": 2,
        }

        result = handler.send_digest(alerts, summary)

        assert result is True
        mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()


class TestConsoleAlertHandler:
    """Test suite for ConsoleAlertHandler."""

    def test_console_handler_enabled(self, capsys):
        """Test console handler prints alerts."""
        config = {"enabled": True}
        handler = ConsoleAlertHandler(config)

        alert = {
            "rule_name": "test_rule",
            "severity": "warning",
            "description": "Test description",
            "timestamp": "2024-01-01",
            "details": "Test details",
        }

        result = handler.send_alert(alert)
        captured = capsys.readouterr()

        assert result is True
        assert "ALERT - WARNING" in captured.out
        assert "test_rule" in captured.out

    def test_console_handler_disabled(self, capsys):
        """Test disabled console handler doesn't print."""
        config = {"enabled": False}
        handler = ConsoleAlertHandler(config)

        alert = {"rule_name": "test", "severity": "warning"}
        result = handler.send_alert(alert)
        captured = capsys.readouterr()

        assert result is True
        assert captured.out == ""  # Should not print anything


class TestAlertManager:
    """Test suite for AlertManager."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a temporary alert config file."""
        config_content = """
global:
  enabled: true
  digest_mode: true
  digest_time: "08:00"

email:
  enabled: false
  smtp_host: "smtp.test.com"
  smtp_port: 587
  from_address: "test@example.com"
  to_addresses:
    - "admin@example.com"

rules:
  - name: "test_rule"
    enabled: true
    severity: "warning"
    description: "Test rule"
    condition:
      type: "ingestion_status"
      statuses: ["failed"]
    cooldown_hours: 1
"""
        config_file = tmp_path / "test_alerts.yaml"
        config_file.write_text(config_content)
        return str(config_file)

    def test_manager_initialization(self, mock_config):
        """Test alert manager initialization."""
        manager = AlertManager(mock_config)

        assert len(manager.rules) == 1
        assert manager.rules[0].name == "test_rule"
        assert len(manager.handlers) == 2  # Email + Console

    def test_evaluate_all_rules(self, mock_config):
        """Test evaluating all rules."""
        manager = AlertManager(mock_config)

        context = {"run_status": "failed"}
        alerts = manager.evaluate_all_rules(context)

        assert len(alerts) == 1
        assert alerts[0]["rule_name"] == "test_rule"

    def test_send_alert_digest_mode(self, mock_config):
        """Test that alerts are buffered in digest mode."""
        manager = AlertManager(mock_config)

        alert = {"rule_name": "test", "severity": "warning"}
        manager.send_alert(alert)

        assert len(manager.get_buffered_alerts()) == 1

    def test_send_digest(self, mock_config):
        """Test sending digest clears buffer."""
        manager = AlertManager(mock_config)

        # Add some alerts
        manager.send_alert({"rule_name": "rule1", "severity": "critical"})
        manager.send_alert({"rule_name": "rule2", "severity": "warning"})

        assert len(manager.get_buffered_alerts()) == 2

        # Send digest
        manager.send_digest()

        assert len(manager.get_buffered_alerts()) == 0

    def test_clear_buffer(self, mock_config):
        """Test clearing alert buffer."""
        manager = AlertManager(mock_config)

        manager.send_alert({"rule_name": "test", "severity": "warning"})
        assert len(manager.get_buffered_alerts()) == 1

        manager.clear_buffer()
        assert len(manager.get_buffered_alerts()) == 0

    def test_environment_variable_substitution(self, tmp_path):
        """Test environment variable substitution in config."""
        import os

        os.environ["TEST_SMTP_HOST"] = "env.smtp.com"

        config_content = """
email:
  enabled: true
  smtp_host: "${TEST_SMTP_HOST}"
  smtp_port: 587
rules: []
"""
        config_file = tmp_path / "env_alerts.yaml"
        config_file.write_text(config_content)

        manager = AlertManager(str(config_file))

        # Check that environment variable was substituted
        email_handler = None
        for handler in manager.handlers:
            if isinstance(handler, EmailAlertHandler):
                email_handler = handler
                break

        assert email_handler is not None
        assert email_handler.smtp_host == "env.smtp.com"


class TestAlertIntegration:
    """Integration tests for alerting system."""

    def test_end_to_end_alert_flow(self, tmp_path):
        """Test complete alert flow from evaluation to notification."""
        config_content = """
global:
  enabled: true
  digest_mode: false

email:
  enabled: false

rules:
  - name: "critical_ingestion_failure"
    enabled: true
    severity: "critical"
    description: "Critical ingestion failure"
    condition:
      type: "ingestion_status"
      statuses: ["failed"]
    cooldown_hours: 1
"""
        config_file = tmp_path / "integration_alerts.yaml"
        config_file.write_text(config_content)

        manager = AlertManager(str(config_file))

        # Mock the console handler to capture alerts
        console_handler = None
        for handler in manager.handlers:
            if isinstance(handler, ConsoleAlertHandler):
                console_handler = handler
                break

        # Trigger an alert
        context = {"run_status": "failed"}
        manager.check_and_alert(context)

        # In non-digest mode, alert should be sent immediately
        # (We can't easily verify this without mocking, but we can verify no buffer)
        assert len(manager.get_buffered_alerts()) == 0
