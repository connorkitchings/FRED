"""Tests for ClientFactory and client abstraction layer."""

import unittest
from unittest.mock import patch

from src.fred_macro.clients import (
    ClientFactory,
    DataSourceClient,
    FredClient,
    TreasuryClient,
    CensusClient,
)


class TestClientFactory(unittest.TestCase):
    """Test suite for ClientFactory."""

    def setUp(self):
        """Clear singleton instances before each test."""
        ClientFactory._instances = {}

    @patch.dict("os.environ", {"FRED_API_KEY": "test_key"})
    def test_get_client_fred(self):
        """Test getting FRED client from factory."""
        client = ClientFactory.get_client("FRED")
        self.assertIsInstance(client, FredClient)

    @patch.dict("os.environ", {"FRED_API_KEY": "test_key"})
    def test_get_client_case_insensitive(self):
        """Test that source name is case-insensitive."""
        client_upper = ClientFactory.get_client("FRED")
        client_lower = ClientFactory.get_client("fred")
        client_mixed = ClientFactory.get_client("Fred")

        self.assertIsInstance(client_upper, FredClient)
        self.assertIsInstance(client_lower, FredClient)
        self.assertIsInstance(client_mixed, FredClient)

    @patch.dict("os.environ", {"FRED_API_KEY": "test_key"})
    def test_get_client_singleton(self):
        """Test that factory returns same instance (singleton pattern)."""
        client1 = ClientFactory.get_client("FRED")
        client2 = ClientFactory.get_client("FRED")

        self.assertIs(client1, client2)

    def test_get_client_unknown_source(self):
        """Test that unknown source raises ValueError."""
        with self.assertRaises(ValueError) as context:
            ClientFactory.get_client("UNKNOWN_SOURCE")

        self.assertIn("Unknown data source", str(context.exception))
        self.assertIn("UNKNOWN_SOURCE", str(context.exception))

    @patch.dict("os.environ", {"FRED_API_KEY": "test_key"})
    def test_get_client_implements_protocol(self):
        """Test that returned client implements DataSourceClient protocol."""
        client = ClientFactory.get_client("FRED")
        self.assertIsInstance(client, DataSourceClient)

    @patch.dict("os.environ", {"FRED_API_KEY": "test_key"})
    def test_client_has_required_method(self):
        """Test that client has get_series_data method."""
        client = ClientFactory.get_client("FRED")
        self.assertTrue(hasattr(client, "get_series_data"))
        self.assertTrue(callable(getattr(client, "get_series_data")))

    def test_get_client_treasury(self):
        """Test getting Treasury client from factory."""
        client = ClientFactory.get_client("TREASURY")
        self.assertIsInstance(client, TreasuryClient)

    def test_get_client_treasury_singleton(self):
        """Test that factory returns same Treasury instance (singleton pattern)."""
        client1 = ClientFactory.get_client("TREASURY")
        client2 = ClientFactory.get_client("TREASURY")
        self.assertIs(client1, client2)

    def test_treasury_implements_protocol(self):
        """Test that Treasury client implements DataSourceClient protocol."""
        client = ClientFactory.get_client("TREASURY")
        self.assertIsInstance(client, DataSourceClient)
        self.assertTrue(hasattr(client, "get_series_data"))
        self.assertTrue(callable(getattr(client, "get_series_data")))

    def test_get_client_census(self):
        """Test getting Census client from factory."""
        client = ClientFactory.get_client("CENSUS")
        self.assertIsInstance(client, CensusClient)

    def test_get_client_census_singleton(self):
        """Test that factory returns same Census instance (singleton pattern)."""
        client1 = ClientFactory.get_client("CENSUS")
        client2 = ClientFactory.get_client("CENSUS")
        self.assertIs(client1, client2)

    def test_census_implements_protocol(self):
        """Test that Census client implements DataSourceClient protocol."""
        client = ClientFactory.get_client("CENSUS")
        self.assertIsInstance(client, DataSourceClient)
        self.assertTrue(hasattr(client, "get_series_data"))
        self.assertTrue(callable(getattr(client, "get_series_data")))


if __name__ == "__main__":
    unittest.main()
