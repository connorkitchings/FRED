from datetime import date, timedelta

import duckdb

from src.fred_macro.validation import run_data_quality_checks


def _init_test_db(db_path):
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE series_catalog (
            series_id VARCHAR,
            title VARCHAR,
            category VARCHAR,
            frequency VARCHAR,
            units VARCHAR,
            seasonal_adjustment VARCHAR,
            tier INTEGER,
            source VARCHAR,
            notes TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE observations (
            series_id VARCHAR,
            observation_date DATE,
            value DOUBLE,
            load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.close()


def _insert_series(conn, series_id: str, frequency: str = "Monthly", tier: int = 1):
    conn.execute(
        """
        INSERT INTO series_catalog (
            series_id, title, category, frequency, units,
            seasonal_adjustment, tier, source, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            series_id,
            series_id,
            "test",
            frequency,
            "units",
            "SA",
            tier,
            "FRED",
            "",
        ),
    )


def _insert_observation(conn, series_id: str, observation_date, value: float):
    conn.execute(
        """
        INSERT INTO observations (series_id, observation_date, value)
        VALUES (?, ?, ?)
        """,
        (series_id, observation_date, value),
    )


def _patch_connection(monkeypatch, db_path):
    import src.fred_macro.validation as validation

    def _connection():
        return duckdb.connect(str(db_path))

    monkeypatch.setattr(validation, "get_connection", _connection)


def test_backfill_missing_series_is_critical(tmp_path, monkeypatch):
    db_path = tmp_path / "validation_missing.duckdb"
    _init_test_db(db_path)
    conn = duckdb.connect(str(db_path))
    _insert_series(conn, "SERIES_A")
    _insert_series(conn, "SERIES_B")
    _insert_observation(conn, "SERIES_A", date.today(), 1.0)
    conn.close()

    _patch_connection(monkeypatch, db_path)

    configured = [{"series_id": "SERIES_A"}, {"series_id": "SERIES_B"}]
    run_stats = {
        "SERIES_A": {"rows_fetched": 10, "rows_processed": 10},
        "SERIES_B": {"rows_fetched": 0, "rows_processed": 0},
    }
    findings = run_data_quality_checks("backfill", configured, run_stats)

    assert any(
        finding.severity == "critical"
        and finding.code == "missing_series_data"
        and finding.series_id == "SERIES_B"
        for finding in findings
    )


def test_duplicate_observations_are_critical(tmp_path, monkeypatch):
    db_path = tmp_path / "validation_duplicates.duckdb"
    _init_test_db(db_path)
    conn = duckdb.connect(str(db_path))
    _insert_series(conn, "SERIES_A")
    _insert_observation(conn, "SERIES_A", date.today(), 1.0)
    _insert_observation(conn, "SERIES_A", date.today(), 1.1)
    conn.close()

    _patch_connection(monkeypatch, db_path)

    configured = [{"series_id": "SERIES_A"}]
    run_stats = {"SERIES_A": {"rows_fetched": 2, "rows_processed": 2}}
    findings = run_data_quality_checks("incremental", configured, run_stats)

    assert any(
        finding.severity == "critical" and finding.code == "duplicate_observations"
        for finding in findings
    )


def test_incremental_no_rows_is_warning(tmp_path, monkeypatch):
    db_path = tmp_path / "validation_incremental.duckdb"
    _init_test_db(db_path)
    conn = duckdb.connect(str(db_path))
    _insert_series(conn, "SERIES_A")
    conn.close()

    _patch_connection(monkeypatch, db_path)

    configured = [{"series_id": "SERIES_A"}]
    run_stats = {"SERIES_A": {"rows_fetched": 0, "rows_processed": 0}}
    findings = run_data_quality_checks("incremental", configured, run_stats)

    assert any(
        finding.severity == "warning" and finding.code == "incremental_no_new_rows"
        for finding in findings
    )
    assert not any(finding.severity == "critical" for finding in findings)


def test_stale_series_data_is_warning(tmp_path, monkeypatch):
    db_path = tmp_path / "validation_stale.duckdb"
    _init_test_db(db_path)
    conn = duckdb.connect(str(db_path))
    _insert_series(conn, "SERIES_A", frequency="Monthly")
    old_date = date.today() - timedelta(days=400)
    _insert_observation(conn, "SERIES_A", old_date, 10.0)
    conn.close()

    _patch_connection(monkeypatch, db_path)

    configured = [{"series_id": "SERIES_A"}]
    run_stats = {"SERIES_A": {"rows_fetched": 1, "rows_processed": 1}}
    findings = run_data_quality_checks("incremental", configured, run_stats)

    assert any(
        finding.severity == "warning"
        and finding.code == "stale_series_data"
        and finding.series_id == "SERIES_A"
        for finding in findings
    )
