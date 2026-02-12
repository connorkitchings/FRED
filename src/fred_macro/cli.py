import json
from typing import Optional

import typer

from src.fred_macro.db import get_connection
from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.logging_config import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)

app = typer.Typer(help="FRED Macro Dashboard CLI")


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


import yaml

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

        from src.fred_macro.fred_client import FredClient

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

    conn = get_connection()
    try:
        target_run_id = run_id
        if target_run_id is None:
            latest = conn.execute(
                """
                SELECT run_id
                FROM ingestion_log
                ORDER BY run_timestamp DESC
                LIMIT 1
                """
            ).fetchone()
            if latest is None:
                typer.echo("No ingestion runs found.")
                raise typer.Exit(code=1)
            target_run_id = latest[0]

        run_row = conn.execute(
            """
            SELECT
                run_id, run_timestamp, mode, status,
                total_rows_fetched, total_rows_inserted, total_rows_updated,
                duration_seconds, error_message
            FROM ingestion_log
            WHERE run_id = ?
            """,
            (target_run_id,),
        ).fetchone()

        if run_row is None:
            typer.echo(f"Run not found: {target_run_id}")
            raise typer.Exit(code=1)

        counts = conn.execute(
            """
            SELECT severity, COUNT(*) AS count
            FROM dq_report
            WHERE run_id = ?
            GROUP BY severity
            ORDER BY severity
            """,
            (target_run_id,),
        ).fetchall()
        count_map = {"info": 0, "warning": 0, "critical": 0}
        for sev, count in counts:
            count_map[sev] = count

        findings_query = """
            SELECT severity, code, series_id, message, metadata
            FROM dq_report
            WHERE run_id = ?
        """
        params = [target_run_id]
        if severity != "all":
            findings_query += " AND severity = ?"
            params.append(severity)
        findings_query += " ORDER BY finding_timestamp DESC LIMIT ?"
        params.append(limit)

        findings = conn.execute(findings_query, params).fetchall()

        typer.echo(
            "Run Summary: "
            f"run_id={run_row[0]} mode={run_row[2]} status={run_row[3]} "
            f"rows_fetched={run_row[4]} duration={run_row[7]:.2f}s"
        )
        typer.echo(
            "DQ Counts: "
            f"critical={count_map['critical']} "
            f"warning={count_map['warning']} "
            f"info={count_map['info']}"
        )

        if run_row[8]:
            typer.echo(f"Run Error: {run_row[8]}")

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
    finally:
        conn.close()


if __name__ == "__main__":
    app()
