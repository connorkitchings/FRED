"""
Compatibility shim for FredClient import.

DEPRECATED: Import FredClient from src.fred_macro.clients instead.

This module will be removed in a future version.
"""

import warnings

from src.fred_macro.clients.fred_client import FredClient

warnings.warn(
    "Importing FredClient from src.fred_macro.fred_client is deprecated. "
    "Use 'from src.fred_macro.clients import FredClient' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["FredClient"]
