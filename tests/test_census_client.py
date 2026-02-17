"""Tests for CensusClient."""

import os
import unittest
from unittest.mock import Mock, patch

import pandas as pd

from src.fred_macro.clients import CensusClient


def _mock_response(status_code: int = 200, payload=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload if payload is not None else []
    response.raise_for_status = Mock()
    return response


class TestCensusClient(unittest.TestCase):
    """Test suite for CensusClient."""

    def test_init_with_env_var(self):
        """Test initialization with env var."""
        with patch.dict(os.environ, {"CENSUS_API_KEY": "test_key"}):
            client = CensusClient()
            self.assertEqual(client.api_key, "test_key")

    def test_init_with_arg(self):
        """Test initialization with argument."""
        client = CensusClient(api_key="arg_key")
        self.assertEqual(client.api_key, "arg_key")

    def test_init_no_key(self):
        """Test initialization without key (should warn but succeed)."""
        with patch.dict(os.environ, {}, clear=True):
            client = CensusClient()
            self.assertIsNone(client.api_key)

    def test_series_mapping_coverage(self):
        """Test that expected series are in the mapping."""
        client = CensusClient(api_key="test")
        expected_series = [
            "CENSUS_EXP_GOODS",
            "CENSUS_IMP_GOODS",
            "CENSUS_IMP_MEXICO",
            "CENSUS_INV_MFG",
            "CENSUS_ORDERS_MFG",
        ]
        for series_id in expected_series:
            self.assertIn(series_id, client.SERIES_MAPPING)
        self.assertNotIn("CENSUS_TRADE_BAL", client.SERIES_MAPPING)

    def test_get_series_data_unknown_series(self):
        """Test that unknown series raises ValueError."""
        client = CensusClient(api_key="test")
        with self.assertRaises(ValueError) as context:
            client.get_series_data("UNKNOWN_SERIES")
        self.assertIn("Unknown Census series", str(context.exception))

    @patch("src.fred_macro.clients.census_client.requests.get")
    @patch("src.fred_macro.clients.census_client.time.sleep")
    def test_get_series_data_success_intl_trade(self, mock_sleep, mock_get):
        """Test successful data fetch for international trade."""
        mock_get.return_value = _mock_response(
            200,
            [
                ["MONTH", "ALL_VAL_MO", "COMM_LVL", "DISTRICT"],
                ["2024-01", "1000000", "HS2", "TOTAL"],
                ["2024-02", "1100000", "HS2", "TOTAL"],
            ],
        )

        client = CensusClient(api_key="test")
        df = client.get_series_data("CENSUS_EXP_GOODS")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("intltrade/exports/hs", call_args[0][0])
        self.assertEqual(call_args[1]["params"]["key"], "test")

        self.assertEqual(len(df), 2)
        self.assertTrue((df["series_id"] == "CENSUS_EXP_GOODS").all())
        self.assertEqual(df.iloc[0]["value"], 1000000)
        self.assertEqual(df.iloc[0]["observation_date"], pd.Timestamp("2024-01-01"))

    @patch("src.fred_macro.clients.census_client.requests.get")
    @patch("src.fred_macro.clients.census_client.time.sleep")
    def test_get_series_data_start_date_filter(self, mock_sleep, mock_get):
        """Test start_date filtering for trade endpoint."""
        mock_get.return_value = _mock_response(
            200,
            [
                ["MONTH", "GEN_VAL_MO"],
                ["2023-12", "900"],
                ["2024-01", "1000"],
                ["2024-02", "1100"],
            ],
        )

        client = CensusClient(api_key="test")
        df = client.get_series_data("CENSUS_IMP_GOODS", start_date="2024-01-01")

        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["observation_date"], pd.Timestamp("2024-01-01"))

        call_params = mock_get.call_args[1]["params"]
        self.assertIn("time", call_params)
        self.assertIn("from 2024-01", call_params["time"])

    @patch("src.fred_macro.clients.census_client.requests.get")
    @patch("src.fred_macro.clients.census_client.time.sleep")
    def test_get_series_data_success_eits_with_slot_resolution(
        self, mock_sleep, mock_get
    ):
        """Test successful EITS fetch with discovered time_slot_id."""
        mock_get.side_effect = [
            _mock_response(
                200,
                [
                    ["time_slot_id", "time_slot_date", "cell_value"],
                    ["slot_b", "2024-01-01", "50"],
                    ["slot_b", "2024-02-01", "51"],
                    ["slot_a", "2024-01-01", "5"],
                ],
            ),
            _mock_response(
                200,
                [
                    ["time_slot_date", "cell_value"],
                    ["2024-01-01", "50"],
                    ["2024-02-01", "51"],
                ],
            ),
        ]

        client = CensusClient(api_key="test")
        df = client.get_series_data("CENSUS_INV_MFG", start_date="2024-01-01")

        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["value"], 50)
        self.assertEqual(mock_get.call_count, 2)

        discovery_params = mock_get.call_args_list[0][1]["params"]
        self.assertEqual(
            discovery_params["get"], "time_slot_id,time_slot_date,cell_value"
        )

        fetch_params = mock_get.call_args_list[1][1]["params"]
        self.assertEqual(fetch_params["time_slot_id"], "slot_b")
        self.assertEqual(fetch_params["get"], "time_slot_date,cell_value")
        self.assertEqual(fetch_params["time"], "from 2024-01")

    @patch("src.fred_macro.clients.census_client.requests.get")
    @patch("src.fred_macro.clients.census_client.time.sleep")
    def test_get_series_data_eits_slot_tie_breaks_to_smallest(
        self, mock_sleep, mock_get
    ):
        """Test deterministic tie-break for EITS slot_id selection."""
        mock_get.side_effect = [
            _mock_response(
                200,
                [
                    ["time_slot_id", "time_slot_date", "cell_value"],
                    ["slot_b", "2024-01-01", "10"],
                    ["slot_a", "2024-01-01", "20"],
                ],
            ),
            _mock_response(
                200,
                [
                    ["time_slot_date", "cell_value"],
                    ["2024-01-01", "20"],
                ],
            ),
        ]

        client = CensusClient(api_key="test")
        client.get_series_data("CENSUS_INV_MFG", start_date="2024-01-01")

        fetch_params = mock_get.call_args_list[1][1]["params"]
        self.assertEqual(fetch_params["time_slot_id"], "slot_a")

    @patch("src.fred_macro.clients.census_client.requests.get")
    @patch("src.fred_macro.clients.census_client.time.sleep")
    def test_get_series_data_eits_no_slot_found_returns_empty(
        self, mock_sleep, mock_get
    ):
        """Test EITS handling when no slot has valid rows."""
        mock_get.return_value = _mock_response(
            200,
            [
                ["time_slot_id", "time_slot_date", "cell_value"],
                ["slot_a", "2024-01-01", "-"],
                ["slot_b", "2024-01-01", "(NA)"],
            ],
        )

        client = CensusClient(api_key="test")
        df = client.get_series_data("CENSUS_INV_MFG", start_date="2024-01-01")

        self.assertTrue(df.empty)
        self.assertEqual(mock_get.call_count, 1)

    @patch("src.fred_macro.clients.census_client.requests.get")
    @patch("src.fred_macro.clients.census_client.time.sleep")
    def test_get_series_data_eits_204_returns_empty(self, mock_sleep, mock_get):
        """Test EITS final fetch 204 no content handling."""
        mock_get.side_effect = [
            _mock_response(
                200,
                [
                    ["time_slot_id", "time_slot_date", "cell_value"],
                    ["slot_a", "2024-01-01", "10"],
                ],
            ),
            _mock_response(204, None),
        ]

        client = CensusClient(api_key="test")
        df = client.get_series_data("CENSUS_INV_MFG", start_date="2024-01-01")

        self.assertTrue(df.empty)
        self.assertEqual(mock_get.call_count, 2)

    @patch("src.fred_macro.clients.census_client.requests.get")
    @patch("src.fred_macro.clients.census_client.time.sleep")
    def test_rate_limiting(self, mock_sleep, mock_get):
        """Test that rate limiting triggers sleep."""
        mock_get.return_value = _mock_response(200, [])

        client = CensusClient(api_key="test")
        client._last_request_time = 1000.0
        client._rate_limit_delay = 0.5

        with patch(
            "src.fred_macro.clients.census_client.time.time", return_value=1000.1
        ):
            client._enforce_rate_limit()
            mock_sleep.assert_called()


if __name__ == "__main__":
    unittest.main()
