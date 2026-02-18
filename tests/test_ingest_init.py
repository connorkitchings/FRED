import pytest
from unittest.mock import Mock, patch
from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.services.writer import DataWriter


def test_ingestion_engine_init_initializes_writer():
    """Verify that IngestionEngine.__init__ correctly initializes DataWriter."""
    with patch("src.fred_macro.ingest.CatalogService"):
        engine = IngestionEngine()
        assert hasattr(engine, "writer")
        assert isinstance(engine.writer, DataWriter)
