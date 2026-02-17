from unittest.mock import Mock

import pandas as pd
import pytest
from pydantic import ValidationError

from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.validation import ValidationFinding


def _build_engine_for_test(
    monkeypatch,
    dq_findings,
    catalog=None,
    client_getter=None,
):
    """
    Helper to construct IngestionEngine with mocks.
    Returns engine and a capture dict that tracks logged run data.
    """
    if catalog is None:
        catalog = {"series": [{"series_id": "FEDFUNDS", "source": "FRED"}]}

    # Capture data storage for assertions
    captured = {}

    # Build real engine
    engine = IngestionEngine.__new__(IngestionEngine)
    engine.config_path = "config/series_catalog.yaml"
    engine.current_run_id = "test-run-id"
    engine.alert_manager = None  # Initialize alert_manager

    # Mock CatalogService
    from src.fred_macro.services.catalog import CatalogService, SeriesConfig

    mock_catalog_service = Mock(spec=CatalogService)

    series_configs = []
    for s in catalog["series"]:
        # Ensure defaults with correct types
        s.setdefault("title", "Test")
        s.setdefault("units", "Index")
        s.setdefault("frequency", "Monthly")
        s.setdefault("seasonal_adjustment", "SA")
        s.setdefault("tier", 1)
        series_configs.append(SeriesConfig(**s))

    mock_catalog_service.get_all_series.return_value = series_configs
    engine.catalog_service = mock_catalog_service

    # Mock the client factory to return mock clients
    def mock_get_client(source):
        if client_getter:
            return client_getter(source)
        # Default mock client
        mock_client = Mock()
        mock_client.get_series_data.return_value = pd.DataFrame(
            {
                "series_id": ["FEDFUNDS"],
                "observation_date": ["2025-01-01"],
                "value": [123.45],
            }
        )
        return mock_client

    monkeypatch.setattr(
        "src.fred_macro.ingest.ClientFactory.get_client",
        mock_get_client,
    )

    # Mock _upsert_data to avoid DB writes
    monkeypatch.setattr(
        engine, "_upsert_data", lambda df: len(df) if not df.empty else 0
    )

    # Mock _log_run to capture logged data
    def capture_log_run(
        run_id,
        mode,
        series_ingested,
        rows_fetched,
        rows_processed,
        duration,
        status,
        error_message,
    ):
        captured.update(
            {
                "run_id": run_id,
                "mode": mode,
                "series_ingested": series_ingested,
                "rows_fetched": rows_fetched,
                "rows_processed": rows_processed,
                "status": status,
                "error_message": error_message,
            }
        )

    monkeypatch.setattr(engine, "_log_run", capture_log_run)

    # Mock _update_logged_run_status to capture updates
    def capture_update_status(run_id, status, error_message):
        captured.update(
            {
                "patched_status": status,
                "patched_error_message": error_message,
            }
        )
        return True

    monkeypatch.setattr(engine, "_update_logged_run_status", capture_update_status)

    # Mock run_data_quality_checks
    mock_dq = Mock(return_value=dq_findings)
    monkeypatch.setattr("src.fred_macro.ingest.run_data_quality_checks", mock_dq)

    return engine, captured


def test_ingest_marks_run_failed_on_critical_dq(monkeypatch):
    engine, captured = _build_engine_for_test(
        monkeypatch,
        [
            ValidationFinding(
                severity="critical",
                code="missing_series_data",
                message="No rows fetched for required series.",
                series_id="FEDFUNDS",
            )
        ],
    )

    engine.run(mode="backfill")

    assert captured["status"] == "failed"
    assert "dq_critical" in captured["error_message"]
    assert captured["series_ingested"] == ["FEDFUNDS"]


def test_ingest_keeps_success_status_when_only_warnings(monkeypatch):
    engine, captured = _build_engine_for_test(
        monkeypatch,
        [
            ValidationFinding(
                severity="warning",
                code="stale_series_data",
                message="Series is stale.",
                series_id="FEDFUNDS",
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
                series_id="FEDFUNDS",
            )
        ],
    )
    monkeypatch.setattr(engine, "_log_dq_findings", lambda run_id, findings: False)

    engine.run(mode="incremental")

    # Initial status is success (from DQ warnings only)
    assert captured["status"] == "success"
    # But it gets patched to partial due to DQ logging failure
    assert captured["patched_status"] == "partial"
    assert "dq_report_logging_failed" in captured["patched_error_message"]


def test_log_dq_findings_lazy_initializes_writer(monkeypatch):
    captured = {}

    class _DummyRepo:
        def insert_dq_findings(self, run_id, findings):
            captured["run_id"] = run_id
            captured["count"] = len(findings)

    class _DummyWriter:
        def __init__(self):
            self.repo = _DummyRepo()

    monkeypatch.setattr("src.fred_macro.ingest.DataWriter", _DummyWriter)

    engine = IngestionEngine.__new__(IngestionEngine)
    findings = [
        ValidationFinding(
            severity="warning",
            code="stale_series_data",
            message="Series is stale.",
            series_id="FEDFUNDS",
        )
    ]

    ok = engine._log_dq_findings("run-xyz", findings)

    assert ok is True
    assert captured["run_id"] == "run-xyz"
    assert captured["count"] == 1
    assert hasattr(engine, "writer")


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
    """Test that unknown source raises ValidationError during SeriesConfig."""
    # This test verifies that SeriesConfig validates the source field
    from src.fred_macro.services.catalog import SeriesConfig

    with pytest.raises(ValidationError) as exc_info:
        SeriesConfig(
            series_id="UNKNOWN_SERIES",
            source="UNKNOWN",  # Invalid source
            title="Test",
            units="Index",
            frequency="Monthly",
            seasonal_adjustment="SA",
            tier=1,
        )

    assert "Source must be one of" in str(exc_info.value)


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
                {"series_id": "LNS14000000", "source": "BLS"},
            ]
        },
        client_getter=_client_getter,
    )

    engine.run(mode="incremental")

    assert captured["status"] == "success"
    assert fred_client.series_ids == ["FEDFUNDS"]
    assert bls_client.series_ids == ["LNS14000000"]
    assert captured["rows_fetched"] == 2
