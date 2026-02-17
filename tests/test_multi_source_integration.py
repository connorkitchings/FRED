"""Integration tests for multi-source data ingestion (FRED + BLS)."""

from unittest.mock import Mock

import pandas as pd
import pytest

from src.fred_macro.clients import ClientFactory, FredClient
from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.services.catalog import SeriesConfig
from src.fred_macro.services.fetcher import DataFetcher
from src.fred_macro.validation import ValidationFinding


class TestMultiSourceIngestion:
    """Integration tests for mixed FRED+BLS ingestion scenarios."""

    def test_fetcher_routes_to_correct_client_by_source(self, monkeypatch):
        """Test DataFetcher routes series to correct client based on source."""
        fred_calls = []
        bls_calls = []

        def mock_get_client(source):
            mock_client = Mock()
            if source == "FRED":

                def fred_fetch(series_id, start_date):
                    fred_calls.append(series_id)
                    return pd.DataFrame(
                        {
                            "series_id": [series_id],
                            "observation_date": ["2025-01-01"],
                            "value": [100.0],
                        }
                    )

                mock_client.get_series_data = fred_fetch
            elif source == "BLS":

                def bls_fetch(series_id, start_date):
                    bls_calls.append(series_id)
                    return pd.DataFrame(
                        {
                            "series_id": [series_id],
                            "observation_date": ["2025-01-01"],
                            "value": [200.0],
                        }
                    )

                mock_client.get_series_data = bls_fetch
            return mock_client

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        fetcher = DataFetcher()

        # Fetch FRED series
        fred_series = SeriesConfig(
            series_id="FEDFUNDS",
            source="FRED",
            title="Fed Funds Rate",
            units="Percent",
            frequency="Monthly",
            seasonal_adjustment="SA",
            tier=1,
        )
        df_fred = fetcher.fetch_series(fred_series, mode="incremental")

        # Fetch BLS series
        bls_series = SeriesConfig(
            series_id="LNS14000000",
            source="BLS",
            title="Unemployment Rate",
            units="Percent",
            frequency="Monthly",
            seasonal_adjustment="SA",
            tier=1,
        )
        df_bls = fetcher.fetch_series(bls_series, mode="incremental")

        assert len(fred_calls) == 1
        assert fred_calls[0] == "FEDFUNDS"
        assert len(bls_calls) == 1
        assert bls_calls[0] == "LNS14000000"
        assert not df_fred.empty
        assert not df_bls.empty
        assert df_fred["value"].iloc[0] == 100.0
        assert df_bls["value"].iloc[0] == 200.0

    def test_ingestion_engine_processes_mixed_catalog(self, monkeypatch):
        """Test IngestionEngine correctly processes mixed FRED+BLS catalog."""
        processed_series = []

        def mock_get_client(source):
            mock_client = Mock()

            def mock_fetch(series_id, start_date):
                processed_series.append((series_id, source))
                return pd.DataFrame(
                    {
                        "series_id": [series_id],
                        "observation_date": ["2025-01-01"],
                        "value": [1.0],
                    }
                )

            mock_client.get_series_data = mock_fetch
            return mock_client

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        # Build engine with mixed catalog
        engine = IngestionEngine.__new__(IngestionEngine)
        engine.config_path = "config/series_catalog.yaml"
        engine.current_run_id = "test-run-id"

        mock_catalog = Mock()
        mock_catalog.get_all_series.return_value = [
            SeriesConfig(
                series_id="FEDFUNDS",
                source="FRED",
                title="Fed Funds",
                units="Percent",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=1,
            ),
            SeriesConfig(
                series_id="UNRATE",
                source="FRED",
                title="Unemployment",
                units="Percent",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=1,
            ),
            SeriesConfig(
                series_id="LNS14000000",
                source="BLS",
                title="BLS Unemployment",
                units="Percent",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=2,
            ),
        ]
        engine.catalog_service = mock_catalog

        # Mock database operations
        monkeypatch.setattr(
            engine, "_upsert_data", lambda df: len(df) if not df.empty else 0
        )

        captured = {}

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
                    "series_ingested": series_ingested,
                    "rows_fetched": rows_fetched,
                    "status": status,
                }
            )

        monkeypatch.setattr(engine, "_log_run", capture_log_run)
        monkeypatch.setattr(
            engine,
            "_update_logged_run_status",
            lambda run_id, status, error_message: True,
        )
        monkeypatch.setattr(
            "src.fred_macro.ingest.run_data_quality_checks",
            lambda **kwargs: [],
        )

        engine.run(mode="incremental")

        # Verify all series were processed
        assert len(processed_series) == 3
        assert ("FEDFUNDS", "FRED") in processed_series
        assert ("UNRATE", "FRED") in processed_series
        assert ("LNS14000000", "BLS") in processed_series

        # Verify ingestion logged correctly
        assert captured["status"] == "success"
        assert captured["rows_fetched"] == 3
        assert set(captured["series_ingested"]) == {"FEDFUNDS", "UNRATE", "LNS14000000"}

    def test_fetcher_uses_source_series_id_for_bls_alias(self, monkeypatch):
        """Fetcher should request source_series_id and persist internal series_id."""
        requested_ids = []

        def mock_get_client(source):
            mock_client = Mock()

            def mock_fetch(series_id, start_date):
                requested_ids.append(series_id)
                return pd.DataFrame(
                    {
                        "series_id": [series_id],
                        "observation_date": ["2025-01-01"],
                        "value": [2.5],
                    }
                )

            mock_client.get_series_data = mock_fetch
            return mock_client

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        fetcher = DataFetcher()
        alias_series = SeriesConfig(
            series_id="ECIALLCIV_BLS",
            source_series_id="ECIALLCIV",
            source="BLS",
            title="ECI Total Comp (BLS Alias)",
            units="Index",
            frequency="Quarterly",
            seasonal_adjustment="SA",
            tier=2,
        )

        df = fetcher.fetch_series(alias_series, mode="incremental")

        assert requested_ids == ["ECIALLCIV"]
        assert not df.empty
        assert (df["series_id"] == "ECIALLCIV_BLS").all()

    def test_ingestion_engine_uses_source_series_id_for_bls_alias(self, monkeypatch):
        """IngestionEngine should fetch alias by source_series_id and store alias id."""
        requested_series = []

        def mock_get_client(source):
            mock_client = Mock()

            def mock_fetch(series_id, start_date):
                requested_series.append((source, series_id))
                return pd.DataFrame(
                    {
                        "series_id": [series_id],
                        "observation_date": ["2025-01-01"],
                        "value": [4.0],
                    }
                )

            mock_client.get_series_data = mock_fetch
            return mock_client

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        engine = IngestionEngine.__new__(IngestionEngine)
        engine.config_path = "config/series_catalog.yaml"
        engine.current_run_id = "test-run-id"
        engine.alert_manager = None

        mock_catalog = Mock()
        mock_catalog.get_all_series.return_value = [
            SeriesConfig(
                series_id="ECIALLCIV_BLS",
                source_series_id="ECIALLCIV",
                source="BLS",
                title="ECI Alias",
                units="Index",
                frequency="Quarterly",
                seasonal_adjustment="SA",
                tier=2,
            ),
        ]
        engine.catalog_service = mock_catalog

        upsert_payload = {}

        def capture_upsert(df):
            upsert_payload["series_ids"] = set(df["series_id"].tolist())
            return len(df)

        monkeypatch.setattr(engine, "_upsert_data", capture_upsert)
        monkeypatch.setattr(
            engine,
            "_log_run",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            engine,
            "_update_logged_run_status",
            lambda run_id, status, error_message: True,
        )
        monkeypatch.setattr(
            "src.fred_macro.ingest.run_data_quality_checks",
            lambda **kwargs: [],
        )

        engine.run(mode="incremental")

        assert requested_series == [("BLS", "ECIALLCIV")]
        assert upsert_payload["series_ids"] == {"ECIALLCIV_BLS"}

    def test_ingestion_falls_back_to_fred_when_bls_quota_reached(self, monkeypatch):
        """If BLS daily quota is reached, ingestion should fallback to FRED."""
        bls_calls = []
        fred_calls = []

        def mock_get_client(source):
            mock_client = Mock()

            if source == "BLS":

                def bls_fetch(series_id, start_date):
                    bls_calls.append(series_id)
                    raise Exception(
                        "BLS API request failed: Request could not be serviced, "
                        "as the daily threshold for total number of requests "
                        "allocated to the user with registration key has been reached."
                    )

                mock_client.get_series_data = bls_fetch
                return mock_client

            if source == "FRED":

                def fred_fetch(series_id, start_date):
                    fred_calls.append(series_id)
                    return pd.DataFrame(
                        {
                            "series_id": [series_id],
                            "observation_date": ["2025-01-01"],
                            "value": [3.0],
                        }
                    )

                mock_client.get_series_data = fred_fetch
                return mock_client

            raise ValueError(f"Unexpected source in test: {source}")

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        engine = IngestionEngine.__new__(IngestionEngine)
        engine.config_path = "config/series_catalog.yaml"
        engine.current_run_id = "test-run-id"
        engine.alert_manager = None

        mock_catalog = Mock()
        mock_catalog.get_all_series.return_value = [
            SeriesConfig(
                series_id="BLS_SERIES_1",
                source="BLS",
                title="BLS 1",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=2,
            ),
            SeriesConfig(
                series_id="BLS_SERIES_2",
                source="BLS",
                title="BLS 2",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=2,
            ),
        ]
        engine.catalog_service = mock_catalog

        monkeypatch.setattr(
            engine, "_upsert_data", lambda df: len(df) if not df.empty else 0
        )
        monkeypatch.setattr(
            engine,
            "_log_run",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            engine,
            "_update_logged_run_status",
            lambda run_id, status, error_message: True,
        )
        monkeypatch.setattr(
            "src.fred_macro.ingest.run_data_quality_checks",
            lambda **kwargs: [],
        )

        engine.run(mode="incremental")

        # BLS client is tried once, then run switches to FRED fallback.
        assert bls_calls == ["BLS_SERIES_1"]
        assert fred_calls == ["BLS_SERIES_1", "BLS_SERIES_2"]

    def test_ingestion_degrades_gracefully_when_fred_fallback_missing(
        self, monkeypatch
    ):
        """BLS quota + missing FRED fallback series should not force partial status."""
        bls_calls = []
        fred_calls = []
        captured = {}

        def mock_get_client(source):
            mock_client = Mock()

            if source == "BLS":

                def bls_fetch(series_id, start_date):
                    bls_calls.append(series_id)
                    raise Exception(
                        "BLS API request failed: Request could not be serviced, "
                        "as the daily threshold for total number of requests "
                        "allocated to the user with registration key has been reached."
                    )

                mock_client.get_series_data = bls_fetch
                return mock_client

            if source == "FRED":

                def fred_fetch(series_id, start_date):
                    fred_calls.append(series_id)
                    raise Exception("Bad Request.  The series does not exist.")

                mock_client.get_series_data = fred_fetch
                return mock_client

            raise ValueError(f"Unexpected source in test: {source}")

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        engine = IngestionEngine.__new__(IngestionEngine)
        engine.config_path = "config/series_catalog.yaml"
        engine.current_run_id = "test-run-id"
        engine.alert_manager = None

        mock_catalog = Mock()
        mock_catalog.get_all_series.return_value = [
            SeriesConfig(
                series_id="BLS_ONLY_1",
                source="BLS",
                title="BLS Only 1",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=2,
            ),
            SeriesConfig(
                series_id="BLS_ONLY_2",
                source="BLS",
                title="BLS Only 2",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=2,
            ),
        ]
        engine.catalog_service = mock_catalog

        monkeypatch.setattr(
            engine, "_upsert_data", lambda df: len(df) if not df.empty else 0
        )
        monkeypatch.setattr(
            engine,
            "_update_logged_run_status",
            lambda run_id, status, error_message: True,
        )
        monkeypatch.setattr(
            "src.fred_macro.ingest.run_data_quality_checks",
            lambda **kwargs: [],
        )

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
                    "status": status,
                    "error_message": error_message,
                    "series_ingested": series_ingested,
                }
            )

        monkeypatch.setattr(engine, "_log_run", capture_log_run)

        engine.run(mode="incremental")

        assert bls_calls == ["BLS_ONLY_1"]
        assert fred_calls == ["BLS_ONLY_1", "BLS_ONLY_2"]
        assert captured["status"] == "success"
        assert captured["error_message"] is None
        assert set(captured["series_ingested"]) == {"BLS_ONLY_1", "BLS_ONLY_2"}

    def test_client_factory_unknown_source_raises_error(self):
        """Test ClientFactory raises ValueError for unknown source."""
        with pytest.raises(ValueError) as exc_info:
            ClientFactory.get_client("UNKNOWN_SOURCE")

        assert "Unknown data source" in str(exc_info.value)
        assert "UNKNOWN_SOURCE" in str(exc_info.value)

    def test_ingestion_continues_on_single_series_failure(self, monkeypatch):
        """Test ingestion continues when one series fails."""

        def mock_get_client(source):
            mock_client = Mock()

            def mock_fetch(series_id, start_date):
                if series_id == "FAIL_SERIES":
                    raise Exception("Simulated API failure")
                return pd.DataFrame(
                    {
                        "series_id": [series_id],
                        "observation_date": ["2025-01-01"],
                        "value": [1.0],
                    }
                )

            mock_client.get_series_data = mock_fetch
            return mock_client

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        engine = IngestionEngine.__new__(IngestionEngine)
        engine.config_path = "config/series_catalog.yaml"
        engine.current_run_id = "test-run-id"

        mock_catalog = Mock()
        mock_catalog.get_all_series.return_value = [
            SeriesConfig(
                series_id="GOOD_SERIES_1",
                source="FRED",
                title="Good 1",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=1,
            ),
            SeriesConfig(
                series_id="FAIL_SERIES",
                source="FRED",
                title="Fails",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=1,
            ),
            SeriesConfig(
                series_id="GOOD_SERIES_2",
                source="BLS",
                title="Good 2",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=2,
            ),
        ]
        engine.catalog_service = mock_catalog

        monkeypatch.setattr(
            engine, "_upsert_data", lambda df: len(df) if not df.empty else 0
        )

        captured = {}

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
                    "series_ingested": series_ingested,
                    "status": status,
                    "error_message": error_message,
                }
            )

        monkeypatch.setattr(engine, "_log_run", capture_log_run)
        monkeypatch.setattr(
            engine,
            "_update_logged_run_status",
            lambda run_id, status, error_message: True,
        )
        monkeypatch.setattr(
            "src.fred_macro.ingest.run_data_quality_checks",
            lambda **kwargs: [],
        )

        engine.run(mode="incremental")

        # Should be partial due to failure
        assert captured["status"] == "partial"
        assert "FAIL_SERIES" in captured["error_message"]
        # But other series should still be processed
        assert "GOOD_SERIES_1" in captured["series_ingested"]
        assert "GOOD_SERIES_2" in captured["series_ingested"]

    def test_empty_dataframe_from_client_handled_gracefully(self, monkeypatch):
        """Test empty DataFrame from client is handled correctly."""

        def mock_get_client(source):
            mock_client = Mock()
            mock_client.get_series_data.return_value = pd.DataFrame()
            return mock_client

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        fetcher = DataFetcher()
        series = SeriesConfig(
            series_id="EMPTY_SERIES",
            source="FRED",
            title="Empty",
            units="Index",
            frequency="Monthly",
            seasonal_adjustment="SA",
            tier=1,
        )

        df = fetcher.fetch_series(series, mode="incremental")

        assert df.empty

    def test_mixed_sources_with_dq_findings(self, monkeypatch):
        """Test DQ findings from mixed sources are aggregated correctly."""

        def mock_get_client(source):
            mock_client = Mock()
            mock_client.get_series_data.return_value = pd.DataFrame(
                {
                    "series_id": ["TEST"],
                    "observation_date": ["2025-01-01"],
                    "value": [1.0],
                }
            )
            return mock_client

        monkeypatch.setattr(ClientFactory, "get_client", mock_get_client)

        engine = IngestionEngine.__new__(IngestionEngine)
        engine.config_path = "config/series_catalog.yaml"
        engine.current_run_id = "test-run-id"

        mock_catalog = Mock()
        mock_catalog.get_all_series.return_value = [
            SeriesConfig(
                series_id="FRED_SERIES",
                source="FRED",
                title="FRED",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=1,
            ),
            SeriesConfig(
                series_id="BLS_SERIES",
                source="BLS",
                title="BLS",
                units="Index",
                frequency="Monthly",
                seasonal_adjustment="SA",
                tier=2,
            ),
        ]
        engine.catalog_service = mock_catalog

        monkeypatch.setattr(
            engine, "_upsert_data", lambda df: len(df) if not df.empty else 0
        )

        captured = {}

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
                    "status": status,
                    "error_message": error_message,
                }
            )

        monkeypatch.setattr(engine, "_log_run", capture_log_run)
        monkeypatch.setattr(
            engine,
            "_update_logged_run_status",
            lambda run_id, status, error_message: True,
        )

        # Return DQ findings
        monkeypatch.setattr(
            "src.fred_macro.ingest.run_data_quality_checks",
            lambda **kwargs: [
                ValidationFinding(
                    severity="warning",
                    code="stale_series_data",
                    message="FRED series is stale",
                    series_id="FRED_SERIES",
                ),
                ValidationFinding(
                    severity="critical",
                    code="missing_series_data",
                    message="BLS series missing",
                    series_id="BLS_SERIES",
                ),
            ],
        )

        engine.run(mode="incremental")

        assert captured["status"] == "failed"
        assert "dq_critical" in captured["error_message"]


class TestClientFactoryEdgeCases:
    """Edge case tests for ClientFactory."""

    def test_client_factory_is_singleton(self, monkeypatch):
        """Test that ClientFactory returns same client instance."""
        # Clear any existing instances
        ClientFactory._instances = {}

        mock_client = Mock()
        mock_client.get_series_data.return_value = pd.DataFrame()

        call_count = 0

        def mock_init(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return None

        def mock_new(cls, *args, **kwargs):
            return mock_client

        monkeypatch.setattr(FredClient, "__init__", mock_init)
        monkeypatch.setattr(FredClient, "__new__", mock_new)

        # Temporarily register mock
        original_registry = ClientFactory._registry.copy()
        ClientFactory._registry = {"FRED": FredClient}

        try:
            client1 = ClientFactory.get_client("FRED")
            client2 = ClientFactory.get_client("FRED")

            # Should be same instance (singleton)
            assert client1 is client2
        finally:
            ClientFactory._registry = original_registry
            ClientFactory._instances = {}

    def test_client_factory_case_insensitive(self, monkeypatch):
        """Test source lookup is case insensitive."""
        ClientFactory._instances = {}

        # Create a mock client class
        mock_client_class = Mock()
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance

        # Temporarily register mock
        original_registry = ClientFactory._registry.copy()
        ClientFactory._registry = {"FRED": mock_client_class}

        try:
            # All case variations should return the same client
            client1 = ClientFactory.get_client("fred")
            ClientFactory._instances = {}  # Clear to get new instance
            client2 = ClientFactory.get_client("Fred")
            ClientFactory._instances = {}  # Clear to get new instance
            client3 = ClientFactory.get_client("FRED")

            # All should be valid (no ValueError raised)
            assert client1 is not None
            assert client2 is not None
            assert client3 is not None
        finally:
            ClientFactory._registry = original_registry
            ClientFactory._instances = {}
