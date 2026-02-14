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
    catalog=None,
    client_getter=None,
):
    """
    Helper to construct IngestionEngine with mocks.
    """
    if catalog is None:
        catalog = {"series": [{"series_id": "TEST_SERIES", "source": "FRED"}]}

    # Mock CatalogService
    from unittest.mock import Mock
    mock_catalog_service = Mock()
    # Convert dict catalog to list of SeriesConfig objects
    from src.fred_macro.services.catalog import SeriesConfig
    
    series_configs = []
    for s in catalog["series"]:
        # Ensure defaults
        s.setdefault("title", "Test")
        s.setdefault("units", "Index")
        s.setdefault("frequency", "Monthly")
        s.setdefault("seasonal_adjustment", "SA")
        s.setdefault("tier", 1)
        series_configs.append(SeriesConfig(**s))
        
    mock_catalog_service.get_all_series.return_value = series_configs

    # Mock DataFetcher
    mock_fetcher = Mock()
    def _fetch_side_effect(series_config, mode):
        # Allow custom client behavior if client_getter provided
        if client_getter:
            client = client_getter(series_config.source)
            return client.get_series_data(series_config.series_id, "2020-01-01")
        # Default behavior: return empty or populated df based on test needs
        return pd.DataFrame() # Default empty
    
    mock_fetcher.fetch_series.side_effect = _fetch_side_effect

    # Mock DataWriter
    mock_writer = Mock()
    mock_writer.upsert_data.return_value = 10
    
    # Init Engine
    engine = IngestionEngine.__new__(IngestionEngine)
    engine.catalog_service = mock_catalog_service
    engine.fetcher = mock_fetcher
    engine.writer = mock_writer
    engine.current_run_id = "test-run-id"

    # Mock run_data_quality_checks
    mock_dq = Mock(return_value=dq_findings)
    monkeypatch.setattr("src.fred_macro.ingest.run_data_quality_checks", mock_dq)

    return engine, None


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
