import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from src.fred_macro.db import get_connection
from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.logging_config import get_logger, setup_logging
from src.fred_macro.repositories.read_repo import ReadRepository

# Initialize logging
setup_logging()
logger = get_logger(__name__)

app = typer.Typer(help="FRED Macro Dashboard CLI")
repo = ReadRepository()


def _resolve_target_run_id(requested_run_id: Optional[str]) -> str:
    if requested_run_id is None or requested_run_id.lower() == "latest":
        latest_id = repo.get_latest_run_id()
        if latest_id is None:
            raise ValueError("No ingestion runs found.")
        return latest_id
    return requested_run_id


@app.command()
def ingest(
    mode: str = typer.Option(
        "incremental",
        help="Ingestion mode: 'incremental' (last 60 days) or 'backfill' (history)",
    ),
):
    """
    Run data ingestion pipeline.
    """
    if mode not in ["incremental", "backfill"]:
        typer.echo(f"Invalid mode: {mode}. Must be 'incremental' or 'backfill'.")
        raise typer.Exit(code=1)

    typer.echo(f"Starting ingestion in {mode} mode...")

    try:
        engine = IngestionEngine()
        engine.run(mode=mode)
        typer.echo("Ingestion run complete.")
    except Exception as e:
        typer.echo(f"Ingestion failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def verify():
    """
    Verify connections and dependencies.
    """
    typer.echo("Verifying connections...")
    # Add verification logic here (DB check, API check)
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        typer.echo("Database connection: OK")
        conn.close()

        from src.fred_macro.clients import FredClient

        client = FredClient()  # This will fail if no API Key
        typer.echo(f"FRED API Key found: {client.api_key[:4]}...")

        # Verify Catalog
        with open("config/series_catalog.yaml", "r") as f:
            catalog = yaml.safe_load(f)
            series_count = len(catalog.get("series", []))
            typer.echo(f"Catalog loaded: {series_count} series configured.")

    except Exception as e:
        typer.echo(f"Verification failed: {e}")
        raise typer.Exit(code=1)


@app.command("dq-report")
def dq_report(
    run_id: Optional[str] = typer.Option(
        None,
        help="Run ID to inspect. Defaults to the latest run.",
    ),
    limit: int = typer.Option(
        50,
        min=1,
        max=500,
        help="Maximum number of findings to show.",
    ),
    severity: str = typer.Option(
        "all",
        help="Filter by severity: all, info, warning, critical.",
    ),
):
    """Show operational DQ report for a run."""
    valid_severities = {"all", "info", "warning", "critical"}
    if severity not in valid_severities:
        typer.echo(
            f"Invalid severity: {severity}. Use one of {sorted(valid_severities)}."
        )
        raise typer.Exit(code=1)

    try:
        try:
            target_run_id = _resolve_target_run_id(run_id)
        except ValueError as e:
            typer.echo(str(e))
            raise typer.Exit(code=1)

        run_row = repo.get_run_by_id(target_run_id)

        if run_row is None:
            typer.echo(f"Run not found: {target_run_id}")
            raise typer.Exit(code=1)

        count_map = repo.get_dq_counts(target_run_id)
        findings = repo.get_dq_findings(target_run_id, severity, limit)

        typer.echo(
            "Run Summary: "
            f"run_id={run_row['run_id']} mode={run_row['mode']} status={run_row['status']} "
            f"rows_fetched={run_row['rows_fetched']} duration={run_row['duration']:.2f}s"
        )
        typer.echo(
            "DQ Counts: "
            f"critical={count_map['critical']} "
            f"warning={count_map['warning']} "
            f"info={count_map['info']}"
        )

        if run_row["error"]:
            typer.echo(f"Run Error: {run_row['error']}")

        if not findings:
            typer.echo("No DQ findings for this selection.")
            return

        typer.echo("Findings:")
        for sev, code, series_id, message, metadata in findings:
            series_label = series_id if series_id else "-"
            line = f"- [{sev}] {code} series={series_label}: {message}"
            if metadata:
                metadata_text = (
                    metadata if isinstance(metadata, str) else json.dumps(metadata)
                )
                line += f" | metadata={metadata_text}"
            typer.echo(line)
    except Exception as e:
        typer.echo(f"Error fetching report: {e}")
        raise typer.Exit(code=1)


@app.command("run-health")
def run_health(
    run_id: Optional[str] = typer.Option(
        None,
        help="Run ID to inspect. Use 'latest' or omit for the newest run.",
    ),
    output_json: Optional[str] = typer.Option(
        None,
        help="Optional path to write a JSON health summary.",
    ),
    fail_on_status: bool = typer.Option(
        False,
        help="Exit non-zero if run status is not success.",
    ),
    fail_on_critical: bool = typer.Option(
        False,
        help="Exit non-zero if critical DQ findings exist.",
    ),
    fail_on_warning: bool = typer.Option(
        False,
        help="Exit non-zero if warning DQ findings exist.",
    ),
):
    """Show ingestion run health summary (for automation and triage)."""
    try:
        try:
            target_run_id = _resolve_target_run_id(run_id)
        except ValueError as e:
            typer.echo(str(e))
            raise typer.Exit(code=1)

        run_row = repo.get_run_by_id(target_run_id)
        if run_row is None:
            typer.echo(f"Run not found: {target_run_id}")
            raise typer.Exit(code=1)

        count_map = repo.get_dq_counts(target_run_id)

        run_timestamp = run_row["run_timestamp"]
        run_timestamp_text = (
            run_timestamp.isoformat()
            if hasattr(run_timestamp, "isoformat")
            else str(run_timestamp)
        )

        summary = {
            "run_id": run_row["run_id"],
            "run_timestamp": run_timestamp_text,
            "mode": run_row["mode"],
            "status": run_row["status"],
            "rows_fetched": run_row["rows_fetched"],
            "rows_inserted": run_row["rows_inserted"],
            "duration_seconds": run_row["duration"],
            "error_message": run_row["error"],
            "dq_counts": count_map,
            "dq_total": (
                count_map["critical"] + count_map["warning"] + count_map["info"]
            ),
        }

        typer.echo(
            "Run Health: "
            f"run_id={summary['run_id']} "
            f"status={summary['status']} "
            f"mode={summary['mode']} "
            f"rows_fetched={summary['rows_fetched']} "
            f"duration={summary['duration_seconds']:.2f}s"
        )
        typer.echo(
            "DQ Counts: "
            f"critical={count_map['critical']} "
            f"warning={count_map['warning']} "
            f"info={count_map['info']}"
        )

        if summary["error_message"]:
            typer.echo(f"Run Error: {summary['error_message']}")

        if output_json:
            output_path = Path(output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(summary, indent=2))
            typer.echo(f"Wrote health summary JSON: {output_path}")

        failures = []
        if fail_on_status and summary["status"] != "success":
            failures.append(f"status={summary['status']}")
        if fail_on_critical and count_map["critical"] > 0:
            failures.append(f"critical_findings={count_map['critical']}")
        if fail_on_warning and count_map["warning"] > 0:
            failures.append(f"warning_findings={count_map['warning']}")

        if failures:
            typer.echo(f"Health check failed: {', '.join(failures)}")
            raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error fetching health: {e}")
        raise typer.Exit(code=1)


@app.command()
def send_digest(
    config_path: str = typer.Option("config/alerts.yaml", help="Path to alerts config"),
):
    """Send daily alert digest manually."""
    from src.fred_macro.services.alert_manager import AlertManager

    try:
        alert_manager = AlertManager(config_path)
        alert_manager.send_digest()
        typer.echo("Digest sent successfully")
    except Exception as e:
        typer.echo(f"Error sending digest: {e}")
        raise typer.Exit(code=1)


@app.command()
def test_alert(
    rule_name: str = typer.Argument(..., help="Name of alert rule to test"),
    config_path: str = typer.Option("config/alerts.yaml", help="Path to alerts config"),
):
    """Test an alert rule by triggering it manually."""
    from src.fred_macro.services.alert_manager import AlertManager

    try:
        alert_manager = AlertManager(config_path)

        # Create a test alert
        test_alert_data = {
            "rule_name": rule_name,
            "severity": "warning",
            "description": f"Test alert for rule: {rule_name}",
            "timestamp": "2024-01-01T00:00:00",
            "details": "This is a test alert to verify the alerting system is working",
            "metadata": {"test": True},
        }

        alert_manager.send_alert(test_alert_data)
        typer.echo(f"Test alert sent for rule: {rule_name}")
    except Exception as e:
        typer.echo(f"Error sending test alert: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
