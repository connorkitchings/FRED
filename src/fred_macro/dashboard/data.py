import pandas as pd
import streamlit as st
from src.fred_macro.services.catalog import CatalogService
from src.fred_macro.repositories.read_repo import ReadRepository

# Initialize repo (it's stateless)
repo = ReadRepository()


@st.cache_data(ttl=3600)
def get_series_catalog() -> pd.DataFrame:
    """Load the full series catalog via service."""
    service = CatalogService()
    series_list = [s.model_dump() for s in service.get_all_series()]
    return pd.DataFrame(series_list)


@st.cache_data(ttl=3600)
def get_latest_values(tier: int = None) -> pd.DataFrame:
    """Get the most recent observation for series."""
    return repo.get_latest_values_df(tier=tier)


@st.cache_data(ttl=3600)
def get_history(series_ids: list[str], years: int = 5) -> pd.DataFrame:
    """Get historical data for a list of series."""
    return repo.get_history_df(series_ids, years)
