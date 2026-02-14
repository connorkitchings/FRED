"""Tests for BLSClient."""

import unittest
from unittest.mock import Mock, patch

import pandas as pd

from src.fred_macro.clients import BLSClient


class TestBLSClient(unittest.TestCase):
    """Test suite for BLSClient."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = BLSClient(api_key="test_key")
        self.assertEqual(client.api_key, "test_key")

    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_api_key(self):
        """Test initialization without API key (should succeed but warn)."""
        client = BLSClient()
        self.assertIsNone(client.api_key)

    @patch.dict("os.environ", {"BLS_API_KEY": "env_key"})
    def test_init_from_env(self):
        """Test initialization from environment variable."""
        client = BLSClient()
        self.assertEqual(client.api_key, "env_key")

    def test_parse_period_monthly(self):
        """Test parsing monthly period codes."""
        client = BLSClient(api_key="test_key")

        self.assertEqual(client._parse_period_to_date("2024", "M01"), "2024-01-01")
        self.assertEqual(client._parse_period_to_date("2024", "M06"), "2024-06-01")
        self.assertEqual(client._parse_period_to_date("2024", "M12"), "2024-12-01")

    def test_parse_period_quarterly(self):
        """Test parsing quarterly period codes."""
        client = BLSClient(api_key="test_key")

        self.assertEqual(client._parse_period_to_date("2024", "Q01"), "2024-01-01")
        self.assertEqual(client._parse_period_to_date("2024", "Q02"), "2024-04-01")
        self.assertEqual(client._parse_period_to_date("2024", "Q03"), "2024-07-01")
        self.assertEqual(client._parse_period_to_date("2024", "Q04"), "2024-10-01")

    def test_parse_period_annual(self):
        """Test parsing annual period code."""
        client = BLSClient(api_key="test_key")

        self.assertEqual(client._parse_period_to_date("2024", "A01"), "2024-01-01")

    def test_parse_period_invalid(self):
        """Test parsing invalid period code raises error."""
        client = BLSClient(api_key="test_key")

        with self.assertRaises(ValueError):
            client._parse_period_to_date("2024", "X99")

    @patch("src.fred_macro.clients.bls_client.requests.post")
    @patch("src.fred_macro.clients.bls_client.time.sleep")
    def test_get_series_data_success(self, mock_sleep, mock_post):
        """Test successful data fetch."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [
                    {
                        "seriesID": "LNS14000000",
                        "data": [
                            {"year": "2024", "period": "M02", "value": "3.7"},
                            {"year": "2024", "period": "M01", "value": "3.8"},
                        ],
                    }
                ]
            },
        }
        mock_post.return_value = mock_response

        client = BLSClient(api_key="test_key")
        df = client.get_series_data("LNS14000000")

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], client.BASE_URL)
        payload = call_args[1]["json"]
        self.assertEqual(payload["seriesid"], ["LNS14000000"])
        self.assertEqual(payload["registrationkey"], "test_key")

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
        self.assertEqual(df.iloc[0]["value"], 3.8)
        self.assertEqual(df.iloc[1]["value"], 3.7)

        # Verify series_id
        self.assertTrue((df["series_id"] == "LNS14000000").all())

    @patch("src.fred_macro.clients.bls_client.requests.post")
    @patch("src.fred_macro.clients.bls_client.time.sleep")
    def test_get_series_data_with_dates(self, mock_sleep, mock_post):
        """Test data fetch with date range."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {"series": [{"seriesID": "TEST", "data": []}]},
        }
        mock_post.return_value = mock_response

        client = BLSClient(api_key="test_key")
        client.get_series_data("TEST", start_date="2020-01-01", end_date="2024-12-31")

        # Verify years are extracted correctly
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["startyear"], "2020")
        self.assertEqual(payload["endyear"], "2024")

    @patch("src.fred_macro.clients.bls_client.requests.post")
    @patch("src.fred_macro.clients.bls_client.time.sleep")
    def test_get_series_data_no_data(self, mock_sleep, mock_post):
        """Test handling of empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {"series": []},
        }
        mock_post.return_value = mock_response

        client = BLSClient(api_key="test_key")
        df = client.get_series_data("NOSERIES")

        # Should return empty DataFrame with correct columns
        self.assertTrue(df.empty)
        self.assertListEqual(
            list(df.columns), ["observation_date", "value", "series_id"]
        )

    @patch("src.fred_macro.clients.bls_client.requests.post")
    @patch("src.fred_macro.clients.bls_client.time.sleep")
    def test_get_series_data_api_error(self, mock_sleep, mock_post):
        """Test handling of API error response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_FAILED",
            "message": ["Invalid series ID"],
        }
        mock_post.return_value = mock_response

        client = BLSClient(api_key="test_key")

        with self.assertRaises(ValueError) as context:
            client.get_series_data("INVALID")

        self.assertIn("BLS API request failed", str(context.exception))

    @patch("src.fred_macro.clients.bls_client.requests.post")
    @patch("src.fred_macro.clients.bls_client.time.sleep")
    def test_get_series_data_network_error(self, mock_sleep, mock_post):
        """Test handling of network error."""
        mock_post.side_effect = ConnectionError("Network failure")

        client = BLSClient(api_key="test_key")

        with self.assertRaises(ConnectionError):
            client.get_series_data("TEST")

    @patch("src.fred_macro.clients.bls_client.requests.post")
    @patch("src.fred_macro.clients.bls_client.time.sleep")
    def test_rate_limiting(self, mock_sleep, mock_post):
        """Test that rate limiting triggers sleep."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {"series": [{"seriesID": "TEST", "data": []}]},
        }
        mock_post.return_value = mock_response

        client = BLSClient(api_key="test_key")
        client._last_request_time = 1000.0

        with patch("src.fred_macro.clients.bls_client.time.time", return_value=1000.2):
            client._enforce_rate_limit()
            # Should sleep because only 0.2s passed (< 0.5s delay)
            mock_sleep.assert_called()

    @patch("src.fred_macro.clients.bls_client.requests.post")
    @patch("src.fred_macro.clients.bls_client.time.sleep")
    def test_get_series_data_skip_invalid_periods(self, mock_sleep, mock_post):
        """Test that observations with invalid periods are skipped."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [
                    {
                        "seriesID": "TEST",
                        "data": [
                            {"year": "2024", "period": "M01", "value": "100"},
                            # Invalid period - should be skipped:
                            {"year": "2024", "period": "X99", "value": "200"},
                            {"year": "2024", "period": "M02", "value": "300"},
                        ],
                    }
                ]
            },
        }
        mock_post.return_value = mock_response

        client = BLSClient(api_key="test_key")
        df = client.get_series_data("TEST")

        # Should only have 2 valid observations
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["value"], 100.0)
        self.assertEqual(df.iloc[1]["value"], 300.0)


if __name__ == "__main__":
    unittest.main()
