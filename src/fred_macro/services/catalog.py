from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, field_validator


class SeriesConfig(BaseModel):
    series_id: str
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    tier: int
    source: str = "FRED"
    description: str = ""

    @field_validator("source")
    def validate_source(cls, v):  # noqa: N805
        allowed = {"FRED", "BLS", "TREASURY"}
        if v.upper() not in allowed:
            raise ValueError(f"Source must be one of {allowed}")
        return v.upper()


class CatalogService:
    """
    Centralized service for accessing the series catalog.
    Handles loading, validation, and filtering.
    """

    def __init__(self, config_path: str = "config/series_catalog.yaml"):
        self.config_path = Path(config_path)
        self._series: List[SeriesConfig] = []
        self.load()

    def load(self):
        """Reload the catalog from disk."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Catalog not found at {self.config_path}")

        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f)

        raw_list = data.get("series", [])
        self._series = [SeriesConfig(**item) for item in raw_list]

    def get_all_series(self) -> List[SeriesConfig]:
        """Return all configured series."""
        return self._series

    def get_active_series(self) -> List[SeriesConfig]:
        """
        Return active series.
        (Future-proofing: can add 'active: bool' to schema later)
        Currently returns all series.
        """
        return self._series

    def filter_by_source(self, source: str) -> List[SeriesConfig]:
        """Filter series by source (FRED/BLS/TREASURY)."""
        return [s for s in self._series if s.source == source.upper()]

    def filter_by_tier(self, tier: int) -> List[SeriesConfig]:
        """Filter series by tier."""
        return [s for s in self._series if s.tier == tier]

    def get_series_by_id(self, series_id: str) -> Optional[SeriesConfig]:
        """Find a specific series config."""
        for s in self._series:
            if s.series_id == series_id:
                return s
        return None
