import json

import duckdb
from typer.testing import CliRunner

from src.fred_macro.cli import app


def _init_report_db(db_path):
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE ingestion_log (
            run_id VARCHAR NOT NULL PRIMARY KEY,
            run_timestamp TIMESTAMP NOT NULL,
            mode VARCHAR NOT NULL,
            series_ingested JSON NOT NULL,
            total_rows_fetched INTEGER NOT NULL,
            total_rows_inserted INTEGER NOT NULL,
            total_rows_updated INTEGER NOT NULL,
            duration_seconds DOUBLE NOT NULL,
            status VARCHAR NOT NULL,
            error_message TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE dq_report (
            report_id VARCHAR NOT NULL PRIMARY KEY,
            run_id VARCHAR NOT NULL,
            finding_timestamp TIMESTAMP NOT NULL,
            severity VARCHAR NOT NULL,
            code VARCHAR NOT NULL,
            series_id VARCHAR,
            message TEXT NOT NULL,
            metadata JSON
        );
    """)
    conn.close()


def test_run_health_latest_summary_and_json_output(tmp_path, monkeypatch):
    db_path = tmp_path / "run_health.duckdb"
    output_path = tmp_path / "artifacts" / "run-health.json"
    _init_report_db(db_path)

    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        INSERT INTO ingestion_log (
            run_id, run_timestamp, mode, series_ingested,
            total_rows_fetched, total_rows_inserted, total_rows_updated,
            duration_seconds, status, error_message
        ) VALUES
        (
            'run-old', NOW() - INTERVAL '1 day', 'incremental', '[]',
            10, 10, 0, 2.1, 'success', NULL
        ),
        (
            'run-latest', NOW(), 'incremental', '[]',
            20, 18, 2, 3.4, 'success', NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO dq_report (
            report_id, run_id, finding_timestamp, severity,
            code, series_id, message, metadata
        ) VALUES
        ('h1', 'run-latest', NOW(), 'warning', 'stale_series_data',
         'UNRATE', 'Series is stale.', '{"age_days": 120}')
        """
    )
    conn.close()

    import src.fred_macro.repositories.read_repo as read_repo

    monkeypatch.setattr(
        read_repo,
        "get_connection",
        lambda: duckdb.connect(str(db_path)),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run-health", "--run-id", "latest", "--output-json", str(output_path)],
    )

    assert result.exit_code == 0
    assert "Run Health: run_id=run-latest status=success" in result.stdout
    assert "DQ Counts: critical=0 warning=1 info=0" in result.stdout
    assert output_path.exists()

    payload = json.loads(output_path.read_text())
    assert payload["run_id"] == "run-latest"
    assert payload["status"] == "success"
    assert payload["dq_counts"]["warning"] == 1


def test_run_health_fail_on_status(tmp_path, monkeypatch):
    db_path = tmp_path / "run_health_fail_status.duckdb"
    _init_report_db(db_path)

    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        INSERT INTO ingestion_log (
            run_id, run_timestamp, mode, series_ingested,
            total_rows_fetched, total_rows_inserted, total_rows_updated,
            duration_seconds, status, error_message
        ) VALUES
        (
            'run-partial', NOW(), 'incremental', '[]',
            20, 18, 2, 3.4, 'partial', 'one series failed'
        )
        """
    )
    conn.close()

    import src.fred_macro.repositories.read_repo as read_repo

    monkeypatch.setattr(
        read_repo,
        "get_connection",
        lambda: duckdb.connect(str(db_path)),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["run-health", "--fail-on-status"])

    assert result.exit_code == 1
    assert "Health check failed: status=partial" in result.stdout


def test_run_health_fail_on_critical(tmp_path, monkeypatch):
    db_path = tmp_path / "run_health_fail_critical.duckdb"
    _init_report_db(db_path)

    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        INSERT INTO ingestion_log (
            run_id, run_timestamp, mode, series_ingested,
            total_rows_fetched, total_rows_inserted, total_rows_updated,
            duration_seconds, status, error_message
        ) VALUES
        (
            'run-critical', NOW(), 'backfill', '[]',
            20, 18, 2, 3.4, 'success', NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO dq_report (
            report_id, run_id, finding_timestamp, severity,
            code, series_id, message, metadata
        ) VALUES
        ('c1', 'run-critical', NOW(), 'critical', 'duplicate_observations',
         'CPIAUCSL', 'Duplicate rows detected.', '{"duplicate_count": 2}')
        """
    )
    conn.close()

    import src.fred_macro.repositories.read_repo as read_repo

    monkeypatch.setattr(
        read_repo,
        "get_connection",
        lambda: duckdb.connect(str(db_path)),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["run-health", "--fail-on-critical"])

    assert result.exit_code == 1
    assert "Health check failed: critical_findings=1" in result.stdout
