import pytest

from src.fred_macro.services.catalog import CatalogService, SeriesConfig


def test_catalog_load():
    """Test loading the real config file."""
    service = CatalogService("config/series_catalog.yaml")
    series = service.get_all_series()
    assert len(series) > 0
    assert isinstance(series[0], SeriesConfig)


def test_filtering():
    """Test filtering logic."""
    service = CatalogService("config/series_catalog.yaml")

    # Tier 1 check
    t1 = service.filter_by_tier(1)
    assert len(t1) > 0
    assert all(s.tier == 1 for s in t1)

    # Source check (FRED)
    fred_series = service.filter_by_source("FRED")
    assert len(fred_series) > 0
    assert all(s.source == "FRED" for s in fred_series)


def test_validation():
    """Test pydantic validation."""
    with pytest.raises(ValueError):
        SeriesConfig(
            series_id="TEST",
            title="Test",
            units="Index",
            frequency="Monthly",
            seasonal_adjustment="SA",
            tier=1,
            source="INVALID_SOURCE",
        )
