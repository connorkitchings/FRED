import duckdb
import pandas as pd
import streamlit as st
from src.fred_macro.db import get_connection

@st.cache_data(ttl=3600)
def get_series_catalog() -> pd.DataFrame:
    """Load the full series catalog."""
    conn = get_connection()
    try:
        df = conn.execute("SELECT * FROM series_catalog").fetchdf()
        return df
    finally:
        conn.close()

@st.cache_data(ttl=3600)
def get_latest_values(tier: int = None) -> pd.DataFrame:
    """
    Get the most recent observation for series.
    Returns: series_id, title, observation_date, value, units, frequency
    """
    conn = get_connection()
    query = """
        WITH RankedObs AS (
            SELECT 
                o.series_id,
                o.observation_date,
                o.value,
                s.title,
                s.units,
                s.frequency,
                s.tier,
                ROW_NUMBER() OVER (PARTITION BY o.series_id ORDER BY o.observation_date DESC) as rn,
                LEAD(o.value) OVER (PARTITION BY o.series_id ORDER BY o.observation_date DESC) as prev_value
            FROM observations o
            JOIN series_catalog s ON o.series_id = s.series_id
            WHERE 1=1
    """
    params = []
    if tier:
        query += " AND s.tier = ?"
        params.append(tier)
        
    query += """
        )
        SELECT 
            series_id, title, observation_date, value, prev_value, units, frequency, tier,
            (value - prev_value) as delta
        FROM RankedObs
        WHERE rn = 1
        ORDER BY tier ASC, series_id ASC
    """
    try:
        return conn.execute(query, params).fetchdf()
    finally:
        conn.close()

@st.cache_data(ttl=3600)
def get_history(series_ids: list[str], years: int = 5) -> pd.DataFrame:
    """
    Get historical data for a list of series.
    Pivot table: date index, columns = series_ids.
    """
    if not series_ids:
        return pd.DataFrame()
        
    conn = get_connection()
    # DuckDB list parameter handling
    placeholders = ",".join(["?"] * len(series_ids))
    
    query = f"""
        SELECT 
            o.observation_date,
            o.series_id,
            o.value
        FROM observations o
        WHERE o.series_id IN ({placeholders})
          AND o.observation_date >= CURRENT_DATE - INTERVAL '{years} years'
        ORDER BY o.observation_date ASC
    """
    try:
        df = conn.execute(query, series_ids).fetchdf()
        # Pivot for easier plotting
        return df
    finally:
        conn.close()
