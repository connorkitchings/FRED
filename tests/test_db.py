import os
import unittest
from unittest.mock import patch, MagicMock
from src.fred_macro.db import get_connection, execute_query


class TestDB(unittest.TestCase):
    @patch("src.fred_macro.db.duckdb.connect")
    @patch.dict(os.environ, {"MOTHERDUCK_TOKEN": "test_token"}, clear=True)
    def test_get_connection_motherduck(self, mock_connect):
        """Test connection to MotherDuck when token is present."""
        conn = get_connection()
        mock_connect.assert_called_with("md:?motherduck_token=test_token")
        self.assertIsNotNone(conn)

    @patch("src.fred_macro.db.duckdb.connect")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_connection_local(self, mock_connect):
        """Test fallback to local DB when token is missing."""
        conn = get_connection()
        mock_connect.assert_called_with("fred.db")
        self.assertIsNotNone(conn)

    @patch("src.fred_macro.db.get_connection")
    def test_execute_query(self, mock_get_conn):
        """Test execute_query wrapper."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [("result",)]

        result = execute_query("SELECT 1")
        
        mock_get_conn.assert_called_once()
        mock_conn.execute.assert_called_with("SELECT 1")
        self.assertEqual(result, [("result",)])
        mock_conn.close.assert_called_once()

    @patch("src.fred_macro.db.get_connection")
    def test_execute_query_with_params(self, mock_get_conn):
        """Test execute_query with parameters."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        execute_query("SELECT ?", ("param",))
        
        mock_conn.execute.assert_called_with("SELECT ?", ("param",))
