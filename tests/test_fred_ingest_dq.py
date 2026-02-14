import pandas as pd

from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.validation import ValidationFinding


class _FakeClient:
    def get_series_data(
        self,
        series_id: str,
        start_date: str,
        end_date: str | None = None,
    ):
        return pd.DataFrame(
            {
                "series_id": [series_id],
                "observation_date": ["2025-01-01"],
                "value": [123.45],
            }
        )


def _build_engine_for_test(
    monkeypatch,
    dq_findings,
    *,
    catalog=None,
    client_getter=None,
):
    engine = IngestionEngine.__new__(IngestionEngine)
    engine.catalog = catalog or {
        "series": [{"series_id": "TEST_SERIES", "source": "FRED"}]
    }

    monkeypatch.setattr(engine, "_determine_start_date", lambda mode: "2020-01-01")
    monkeypatch.setattr(engine, "_upsert_data", lambda df: len(df))
    if client_getter is None:
        client_getter = lambda source: _FakeClient()  # noqa: E731
    monkeypatch.setattr(
        "src.fred_macro.ingest.ClientFactory.get_client",
        client_getter,
    )

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


def test_group_series_by_source_defaults_to_fred():
    engine = IngestionEngine.__new__(IngestionEngine)
    grouped = engine._group_series_by_source(
        [
            {"series_id": "FEDFUNDS"},
            {"series_id": "UNRATE", "source": "fred"},
            {"series_id": "LNS14000000", "source": "bls"},
        ]
    )

    assert set(grouped.keys()) == {"FRED", "BLS"}
    assert len(grouped["FRED"]) == 2
    assert len(grouped["BLS"]) == 1


def test_ingest_marks_partial_on_unknown_source(monkeypatch):
    def _raise_unknown(source):
        raise ValueError(f"Unknown data source: {source}. Available sources: FRED, BLS")

    engine, captured = _build_engine_for_test(
        monkeypatch,
        dq_findings=[],
        catalog={"series": [{"series_id": "UNKNOWN_SERIES", "source": "UNKNOWN"}]},
        client_getter=_raise_unknown,
    )

    engine.run(mode="incremental")

    assert captured["status"] == "partial"
    assert "Unknown data source" in captured["error_message"]
    assert captured["series_ingested"] == []


def test_ingest_routes_series_to_client_by_source(monkeypatch):
    class _RecordingClient:
        def __init__(self):
            self.series_ids = []

        def get_series_data(self, series_id: str, start_date: str, end_date=None):
            self.series_ids.append(series_id)
            return pd.DataFrame(
                {
                    "series_id": [series_id],
                    "observation_date": ["2025-01-01"],
                    "value": [123.45],
                }
            )

    fred_client = _RecordingClient()
    bls_client = _RecordingClient()

    def _client_getter(source):
        return {"FRED": fred_client, "BLS": bls_client}[source]

    engine, captured = _build_engine_for_test(
        monkeypatch,
        dq_findings=[],
        catalog={
            "series": [
                {"series_id": "FEDFUNDS", "source": "FRED"},
                {"series_id": "LNS14000000", "source": "bls"},
            ]
        },
        client_getter=_client_getter,
    )

    engine.run(mode="incremental")

    assert captured["status"] == "success"
    assert fred_client.series_ids == ["FEDFUNDS"]
    assert bls_client.series_ids == ["LNS14000000"]
    assert captured["rows_fetched"] == 2
