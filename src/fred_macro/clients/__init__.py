"""
Data source client factory and abstractions.

This module provides a factory pattern for obtaining data source clients
(FRED, BLS, etc.) and ensures they implement a common interface.
"""

from typing import Dict, Type

from src.fred_macro.clients.base import DataSourceClient
from src.fred_macro.clients.bls_client import BLSClient
from src.fred_macro.clients.fred_client import FredClient
from src.fred_macro.clients.treasury_client import TreasuryClient


class ClientFactory:
    """
    Factory for creating and managing data source client instances.

    Implements singleton pattern per source to maintain rate limit state.
    """

    _registry: Dict[str, Type[DataSourceClient]] = {
        "FRED": FredClient,
        "BLS": BLSClient,
        "TREASURY": TreasuryClient,
    }
    _instances: Dict[str, DataSourceClient] = {}

    @classmethod
    def get_client(cls, source: str) -> DataSourceClient:
        """
        Get a client instance for the specified data source.

        Args:
            source: Data source name (case-insensitive). Currently supports:
                - "FRED": Federal Reserve Economic Data
                - "BLS": Bureau of Labor Statistics
                - "TREASURY": U.S. Treasury Fiscal Data

        Returns:
            DataSourceClient: A client instance implementing the
                DataSourceClient protocol

        Raises:
            ValueError: If the source is not registered

        Examples:
            >>> client = ClientFactory.get_client("FRED")
            >>> df = client.get_series_data("GDP")
        """
        source_upper = source.upper()

        if source_upper not in cls._registry:
            raise ValueError(
                f"Unknown data source: {source}. "
                f"Available sources: {', '.join(cls._registry.keys())}"
            )

        # Singleton pattern: reuse existing instance to maintain rate limit state
        if source_upper not in cls._instances:
            cls._instances[source_upper] = cls._registry[source_upper]()

        return cls._instances[source_upper]


__all__ = [
    "DataSourceClient",
    "FredClient",
    "BLSClient",
    "TreasuryClient",
    "ClientFactory",
]
