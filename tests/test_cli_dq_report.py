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


def test_dq_report_command_for_specific_run(tmp_path, monkeypatch):
    db_path = tmp_path / "dq_cli.duckdb"
    _init_report_db(db_path)
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        INSERT INTO ingestion_log (
            run_id, run_timestamp, mode, series_ingested,
            total_rows_fetched, total_rows_inserted, total_rows_updated,
            duration_seconds, status, error_message
        ) VALUES ('run-1', NOW(), 'backfill', '[]', 100, 100, 0, 2.5, 'success', NULL)
        """
    )
    conn.execute(
        """
        INSERT INTO dq_report (
            report_id, run_id, finding_timestamp, severity,
            code, series_id, message, metadata
        ) VALUES
        ('r1', 'run-1', NOW(), 'warning', 'stale_series_data',
         'UNRATE', 'Series is stale.', '{"age_days": 120}'),
        ('r2', 'run-1', NOW(), 'critical', 'duplicate_observations',
         'CPIAUCSL', 'Duplicate rows detected.', '{"duplicate_count": 2}')
        """
    )
    conn.close()

    # Monkeypatch get_connection at the repository level where ReadRepository uses it
    monkeypatch.setattr(
        "src.fred_macro.repositories.read_repo.get_connection",
        lambda: duckdb.connect(str(db_path)),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dq-report", "--run-id", "run-1"])

    assert result.exit_code == 0
    assert "Run Summary: run_id=run-1" in result.stdout
    assert "DQ Counts: critical=1 warning=1 info=0" in result.stdout
    assert "duplicate_observations" in result.stdout
    assert "stale_series_data" in result.stdout


def test_dq_report_command_uses_latest_run_by_default(tmp_path, monkeypatch):
    db_path = tmp_path / "dq_cli_latest.duckdb"
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
            'run-older', NOW() - INTERVAL '1 day', 'incremental', '[]',
            1, 1, 0, 1.0, 'success', NULL
        ),
        ('run-latest', NOW(), 'backfill', '[]', 2, 2, 0, 2.0, 'success', NULL)
        """
    )
    conn.execute(
        """
        INSERT INTO dq_report (
            report_id, run_id, finding_timestamp, severity,
            code, series_id, message, metadata
        ) VALUES
        ('r3', 'run-latest', NOW(), 'warning', 'series_has_no_observations',
         'HOUST', 'No observations.', '{"frequency": "Monthly"}')
        """
    )
    conn.close()

    # Monkeypatch get_connection at the repository level
    monkeypatch.setattr(
        "src.fred_macro.repositories.read_repo.get_connection",
        lambda: duckdb.connect(str(db_path)),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dq-report"])

    assert result.exit_code == 0
    assert "run_id=run-latest" in result.stdout


def test_dq_report_command_accepts_latest_alias(tmp_path, monkeypatch):
    db_path = tmp_path / "dq_cli_latest_alias.duckdb"
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
            'run-old', NOW() - INTERVAL '2 day', 'incremental', '[]',
            1, 1, 0, 1.0, 'success', NULL
        ),
        ('run-new', NOW(), 'incremental', '[]', 1, 1, 0, 1.0, 'success', NULL)
        """
    )
    conn.execute(
        """
        INSERT INTO dq_report (
            report_id, run_id, finding_timestamp, severity,
            code, series_id, message, metadata
        ) VALUES
        ('r-latest', 'run-new', NOW(), 'warning', 'stale_series_data',
         'UNRATE', 'Series is stale.', '{"age_days": 90}')
        """
    )
    conn.close()

    # Monkeypatch get_connection at the repository level
    monkeypatch.setattr(
        "src.fred_macro.repositories.read_repo.get_connection",
        lambda: duckdb.connect(str(db_path)),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dq-report", "--run-id", "latest"])

    assert result.exit_code == 0
    assert "run_id=run-new" in result.stdout


def test_dq_report_command_errors_for_missing_run(tmp_path, monkeypatch):
    db_path = tmp_path / "dq_cli_missing.duckdb"
    _init_report_db(db_path)

    # Monkeypatch get_connection at the repository level
    monkeypatch.setattr(
        "src.fred_macro.repositories.read_repo.get_connection",
        lambda: duckdb.connect(str(db_path)),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dq-report", "--run-id", "does-not-exist"])

    assert result.exit_code == 1
    assert "Run not found: does-not-exist" in result.stdout
