import unittest
from unittest.mock import patch

import pandas as pd

from src.fred_macro.fred_client import FredClient


class TestFredClient(unittest.TestCase):
    @patch("src.fred_macro.fred_client.Fred")
    def test_init_success(self, mock_fred):
        """Test successful initialization with API key."""
        client = FredClient(api_key="test_key")
        mock_fred.assert_called_with(api_key="test_key")
        self.assertEqual(client.api_key, "test_key")

    @patch.dict("os.environ", {}, clear=True)
    def test_init_no_key(self):
        """Test initialization fails without API key."""
        with self.assertRaises(ValueError):
            FredClient()

    @patch("src.fred_macro.fred_client.Fred")
    @patch("src.fred_macro.fred_client.time.sleep")
    def test_get_series_data_success(self, mock_sleep, mock_fred):
        """Test successful data fetch."""
        # Setup mock return
        mock_series = pd.Series(
            data=[100.0, 101.0],
            index=pd.to_datetime(["2023-01-01", "2023-02-01"]),
            name="GDP",
        )
        mock_fred_instance = mock_fred.return_value
        mock_fred_instance.get_series.return_value = mock_series

        client = FredClient(api_key="test_key")
        df = client.get_series_data("GDP")

        # Verify call
        mock_fred_instance.get_series.assert_called_with(
            "GDP", observation_start=None, observation_end=None
        )

        # Verify DataFrame structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertListEqual(
            list(df.columns), ["observation_date", "value", "series_id"]
        )
        self.assertEqual(df.iloc[0]["series_id"], "GDP")
        self.assertEqual(df.iloc[0]["value"], 100.0)

    @patch("src.fred_macro.fred_client.Fred")
    @patch("src.fred_macro.fred_client.time.sleep")
    def test_rate_limiting(self, mock_sleep, mock_fred):
        """Test that rate limiting triggers sleep."""
        client = FredClient(api_key="test_key")
        client._last_request_time = 1000.0

        with patch("src.fred_macro.fred_client.time.time", return_value=1000.5):
            client._enforce_rate_limit()
            mock_sleep.assert_called()  # Should sleep because only 0.5s passed

    @patch("src.fred_macro.fred_client.Fred")
    def test_get_series_data_failure(self, mock_fred):
        """Test error propagation."""
        mock_fred_instance = mock_fred.return_value
        mock_fred_instance.get_series.side_effect = Exception("API Error")

        client = FredClient(api_key="test_key")
        with self.assertRaises(Exception):
            client.get_series_data("GDP")
