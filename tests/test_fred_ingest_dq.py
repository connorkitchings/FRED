import pandas as pd

from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.validation import ValidationFinding


class _FakeClient:
    def get_series_data(self, series_id: str, start_date: str):
        return pd.DataFrame(
            {
                "series_id": [series_id],
                "observation_date": ["2025-01-01"],
                "value": [123.45],
            }
        )


def _build_engine_for_test(monkeypatch, dq_findings):
    engine = IngestionEngine.__new__(IngestionEngine)
    engine.catalog = {"series": [{"series_id": "TEST_SERIES"}]}
    engine.client = _FakeClient()

    monkeypatch.setattr(engine, "_determine_start_date", lambda mode: "2020-01-01")
    monkeypatch.setattr(engine, "_upsert_data", lambda df: len(df))

    captured = {}

    def _capture_log_run(
        run_id,
        mode,
        series_ingested,
        rows_fetched,
        rows_processed,
        duration,
        status,
        error_message,
    ):
        captured["status"] = status
        captured["error_message"] = error_message
        captured["series_ingested"] = series_ingested
        captured["rows_fetched"] = rows_fetched
        captured["rows_processed"] = rows_processed

    monkeypatch.setattr(engine, "_log_run", _capture_log_run)
    monkeypatch.setattr(
        "src.fred_macro.ingest.run_data_quality_checks",
        lambda mode, configured_series, run_series_stats: dq_findings,
    )
    monkeypatch.setattr(engine, "_log_dq_findings", lambda run_id, findings: True)
    monkeypatch.setattr(
        engine,
        "_update_logged_run_status",
        lambda run_id, status, error_message: captured.update(
            {
                "patched_run_id": run_id,
                "patched_status": status,
                "patched_error_message": error_message,
            }
        )
        or True,
    )
    return engine, captured


def test_ingest_marks_run_failed_on_critical_dq(monkeypatch):
    engine, captured = _build_engine_for_test(
        monkeypatch,
        [
            ValidationFinding(
                severity="critical",
                code="missing_series_data",
                message="No rows fetched for required series.",
                series_id="TEST_SERIES",
            )
        ],
    )

    engine.run(mode="backfill")

    assert captured["status"] == "failed"
    assert "dq_critical" in captured["error_message"]
    assert captured["series_ingested"] == ["TEST_SERIES"]


def test_ingest_keeps_success_status_when_only_warnings(monkeypatch):
    engine, captured = _build_engine_for_test(
        monkeypatch,
        [
            ValidationFinding(
                severity="warning",
                code="stale_series_data",
                message="Series is stale.",
                series_id="TEST_SERIES",
            )
        ],
    )

    engine.run(mode="incremental")

    assert captured["status"] == "success"
    assert captured["error_message"] is None


def test_ingest_marks_partial_if_dq_report_persistence_fails(monkeypatch):
    engine, captured = _build_engine_for_test(
        monkeypatch,
        [
            ValidationFinding(
                severity="warning",
                code="stale_series_data",
                message="Series is stale.",
                series_id="TEST_SERIES",
            )
        ],
    )
    monkeypatch.setattr(engine, "_log_dq_findings", lambda run_id, findings: False)

    engine.run(mode="incremental")

    assert captured["status"] == "success"
    assert captured["patched_status"] == "partial"
    assert "dq_report_logging_failed" in captured["patched_error_message"]
