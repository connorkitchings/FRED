import duckdb

from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.services.writer import DataWriter
from src.fred_macro.validation import ValidationFinding


def _init_dq_schema(db_path):
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
            metadata JSON,
            FOREIGN KEY (run_id) REFERENCES ingestion_log(run_id)
        );
    """)
    conn.close()


def test_log_dq_findings_persists_rows(tmp_path, monkeypatch):
    """Integration test: verify DQ findings are actually persisted to database."""
    db_path = tmp_path / "dq_report.duckdb"
    _init_dq_schema(db_path)

    # Seed the ingestion_log (required for FK constraint)
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        INSERT INTO ingestion_log (
            run_id, run_timestamp, mode, series_ingested,
            total_rows_fetched, total_rows_inserted, total_rows_updated,
            duration_seconds, status, error_message
        ) VALUES (?, NOW(), 'backfill', '[]', 0, 0, 0, 0.0, 'success', NULL)
        """,
        ("run-123",),
    )
    conn.close()

    # Monkeypatch get_connection at the repository level to use test DB
    def test_connection():
        return duckdb.connect(str(db_path))

    monkeypatch.setattr(
        "src.fred_macro.repositories.write_repo.get_connection",
        test_connection,
    )

    # Use real DataWriter with real WriteRepository
    engine = IngestionEngine.__new__(IngestionEngine)
    engine.writer = DataWriter()

    findings = [
        ValidationFinding(
            severity="warning",
            code="stale_series_data",
            message="Series is stale.",
            series_id="UNRATE",
            metadata={"age_days": 120, "threshold_days": 90},
        ),
        ValidationFinding(
            severity="critical",
            code="duplicate_observations",
            message="Duplicate rows detected.",
            series_id="CPIAUCSL",
            metadata={"duplicate_count": 2},
        ),
    ]

    ok = engine._log_dq_findings("run-123", findings)
    assert ok is True

    # Verify data was actually persisted in the database
    conn = duckdb.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT severity, code, series_id
        FROM dq_report
        WHERE run_id = 'run-123'
        ORDER BY severity
        """
    ).fetchall()
    metadata = conn.execute(
        """
        SELECT metadata
        FROM dq_report
        WHERE run_id = 'run-123' AND code = 'stale_series_data'
        LIMIT 1
        """
    ).fetchone()
    conn.close()

    assert len(rows) == 2
    assert ("critical", "duplicate_observations", "CPIAUCSL") in rows
    assert ("warning", "stale_series_data", "UNRATE") in rows
    assert metadata is not None
