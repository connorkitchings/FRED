"""Tests for TreasuryClient."""

import unittest
from unittest.mock import Mock, patch

import pandas as pd
from tenacity import RetryError

from src.fred_macro.clients import TreasuryClient


class TestTreasuryClient(unittest.TestCase):
    """Test suite for TreasuryClient."""

    def test_init(self):
        """Test initialization (no API key needed)."""
        client = TreasuryClient()
        self.assertEqual(client._rate_limit_delay, 0.3)
        self.assertEqual(client._last_request_time, 0.0)

    def test_series_mapping_coverage(self):
        """Test that all expected series are in the mapping."""
        client = TreasuryClient()
        expected_series = [
            "TREAS_AVG_BILLS",
            "TREAS_AVG_NOTES",
            "TREAS_AVG_BONDS",
            "TREAS_AVG_TIPS",
            "TREAS_AUCTION_10Y",
            "TREAS_AUCTION_2Y",
            "TREAS_AUCTION_30Y",
            "TREAS_BID_COVER_10Y",
        ]
        for series_id in expected_series:
            self.assertIn(series_id, client.SERIES_MAPPING)

    def test_series_mapping_structure(self):
        """Test that series mapping has required fields."""
        client = TreasuryClient()
        for series_id, config in client.SERIES_MAPPING.items():
            self.assertIn("endpoint", config, f"{series_id} missing endpoint")
            self.assertIn("filter", config, f"{series_id} missing filter")
            self.assertIn("value_field", config, f"{series_id} missing value_field")

    def test_build_filters_base_only(self):
        """Test filter building with only base filter."""
        client = TreasuryClient()
        result = client._build_filters(
            "security_type_desc:eq:Treasury Bills",
            "v2/accounting/od/avg_interest_rates"
        )
        self.assertEqual(result, "security_type_desc:eq:Treasury Bills")

    def test_build_filters_with_start_date(self):
        """Test filter building with start date for avg interest rates."""
        client = TreasuryClient()
        result = client._build_filters(
            "security_type_desc:eq:Treasury Bills",
            "v2/accounting/od/avg_interest_rates",
            start_date="2020-01-01"
        )
        # Should use record_date for avg_interest_rates endpoint
        self.assertIn("record_date:gte:2020-01-01", result)
        self.assertIn("security_type_desc:eq:Treasury Bills", result)

    def test_build_filters_with_date_range(self):
        """Test filter building with date range for avg interest rates."""
        client = TreasuryClient()
        result = client._build_filters(
            "security_type_desc:eq:Treasury Bills",
            "v2/accounting/od/avg_interest_rates",
            start_date="2020-01-01",
            end_date="2023-12-31"
        )
        self.assertIn("record_date:gte:2020-01-01", result)
        self.assertIn("record_date:lte:2023-12-31", result)

    def test_build_filters_auction_endpoint(self):
        """Test filter building for auction endpoint uses auction_date."""
        client = TreasuryClient()
        result = client._build_filters(
            "security_term:eq:10-Year",
            "v1/accounting/od/auctions_query",
            start_date="2020-01-01"
        )
        # Should use auction_date for auctions_query endpoint
        self.assertIn("auction_date:gte:2020-01-01", result)
        self.assertIn("security_term:eq:10-Year", result)

    def test_get_series_data_unknown_series(self):
        """Test that unknown series raises ValueError."""
        client = TreasuryClient()
        with self.assertRaises(ValueError) as context:
            client.get_series_data("UNKNOWN_SERIES")
        self.assertIn("Unknown Treasury series", str(context.exception))

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_get_series_data_success(self, mock_sleep, mock_get):
        """Test successful data fetch."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "record_date": "2024-02-01",
                    "avg_interest_rate_amt": "4.25",
                    "security_type_desc": "Treasury Bills",
                },
                {
                    "record_date": "2024-01-01",
                    "avg_interest_rate_amt": "4.10",
                    "security_type_desc": "Treasury Bills",
                },
            ],
            "meta": {"total-pages": 1},
        }
        mock_get.return_value = mock_response

        client = TreasuryClient()
        df = client.get_series_data("TREAS_AVG_BILLS")

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("avg_interest_rates", call_args[0][0])

        # Verify DataFrame structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertListEqual(
            list(df.columns), ["observation_date", "value", "series_id"]
        )
        self.assertEqual(len(df), 2)

        # Verify data is sorted by date (oldest first)
        self.assertEqual(df.iloc[0]["observation_date"], pd.Timestamp("2024-01-01"))
        self.assertEqual(df.iloc[1]["observation_date"], pd.Timestamp("2024-02-01"))

        # Verify values
        self.assertEqual(df.iloc[0]["value"], 4.10)
        self.assertEqual(df.iloc[1]["value"], 4.25)

        # Verify series_id
        self.assertTrue((df["series_id"] == "TREAS_AVG_BILLS").all())

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_get_series_data_auction_series(self, mock_sleep, mock_get):
        """Test successful data fetch for auction series."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "auction_date": "2024-02-15",
                    "high_investment_rate": "4.35",
                    "security_term": "10-Year",
                },
                {
                    "auction_date": "2024-01-15",
                    "high_investment_rate": "4.25",
                    "security_term": "10-Year",
                },
            ],
            "meta": {"total-pages": 1},
        }
        mock_get.return_value = mock_response

        client = TreasuryClient()
        df = client.get_series_data("TREAS_AUCTION_10Y")

        # Verify DataFrame structure
        self.assertEqual(len(df), 2)
        self.assertTrue((df["series_id"] == "TREAS_AUCTION_10Y").all())

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_get_series_data_with_date_filtering(self, mock_sleep, mock_get):
        """Test data fetch with date range filtering."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"record_date": "2020-01-01", "avg_interest_rate_amt": "2.0"},
                {"record_date": "2020-02-01", "avg_interest_rate_amt": "2.5"},
                {"record_date": "2020-03-01", "avg_interest_rate_amt": "3.0"},
            ],
            "meta": {"total-pages": 1},
        }
        mock_get.return_value = mock_response

        client = TreasuryClient()
        df = client.get_series_data(
            "TREAS_AVG_BILLS",
            start_date="2020-02-01",
            end_date="2020-03-01",
        )

        # Verify date filtering was applied in API call
        call_params = mock_get.call_args[1]["params"]
        self.assertIn("record_date:gte:2020-02-01", call_params["filter"])
        self.assertIn("record_date:lte:2020-03-01", call_params["filter"])

        # Verify additional filtering in DataFrame
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["observation_date"], pd.Timestamp("2020-02-01"))
        self.assertEqual(df.iloc[1]["observation_date"], pd.Timestamp("2020-03-01"))

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_get_series_data_empty_response(self, mock_sleep, mock_get):
        """Test handling of empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [],
            "meta": {"total-pages": 0},
        }
        mock_get.return_value = mock_response

        client = TreasuryClient()
        df = client.get_series_data("TREAS_AVG_BILLS")

        # Should return empty DataFrame with correct columns
        self.assertTrue(df.empty)
        self.assertListEqual(
            list(df.columns), ["observation_date", "value", "series_id"]
        )

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_get_series_data_pagination(self, mock_sleep, mock_get):
        """Test handling of paginated responses."""
        # Mock two pages of data
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "data": [
                {"record_date": "2024-02-01", "avg_interest_rate_amt": "4.0"},
            ],
            "meta": {"total-pages": 2},
        }

        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = {
            "data": [
                {"record_date": "2024-01-01", "avg_interest_rate_amt": "3.5"},
            ],
            "meta": {"total-pages": 2},
        }

        mock_get.side_effect = [mock_response_page1, mock_response_page2]

        client = TreasuryClient()
        df = client.get_series_data("TREAS_AVG_BILLS")

        # Verify both API calls were made
        self.assertEqual(mock_get.call_count, 2)

        # Verify combined data
        self.assertEqual(len(df), 2)

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_get_series_data_network_error(self, mock_sleep, mock_get):
        """Test handling of network error with retry."""
        mock_get.side_effect = ConnectionError("Network failure")

        client = TreasuryClient()

        with self.assertRaises(RetryError) as context:
            client.get_series_data("TREAS_AVG_BILLS")

        self.assertIsInstance(
            context.exception.last_attempt.exception(), ConnectionError
        )

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_rate_limiting(self, mock_sleep, mock_get):
        """Test that rate limiting triggers sleep."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [],
            "meta": {"total-pages": 0},
        }
        mock_get.return_value = mock_response

        client = TreasuryClient()
        client._last_request_time = 1000.0

        with patch("src.fred_macro.clients.treasury_client.time.time", return_value=1000.1):
            client._enforce_rate_limit()
            # Should sleep because only 0.1s passed (< 0.3s delay)
            mock_sleep.assert_called()

    @patch("src.fred_macro.clients.treasury_client.requests.get")
    @patch("src.fred_macro.clients.treasury_client.time.sleep")
    def test_get_series_data_missing_fields(self, mock_sleep, mock_get):
        """Test handling of records with missing fields."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"record_date": "2024-02-01", "avg_interest_rate_amt": "4.0"},
                {"record_date": "2024-01-01"},  # Missing value
                {"avg_interest_rate_amt": "3.5"},  # Missing date
            ],
            "meta": {"total-pages": 1},
        }
        mock_get.return_value = mock_response

        client = TreasuryClient()
        df = client.get_series_data("TREAS_AVG_BILLS")

        # Should only include the complete record
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["value"], 4.0)


if __name__ == "__main__":
    unittest.main()
