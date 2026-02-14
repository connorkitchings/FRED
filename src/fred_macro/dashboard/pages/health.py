import streamlit as st
import pandas as pd
from src.fred_macro.db import get_connection

@st.cache_data(ttl=60)  # Short cache for health data
def get_recent_runs(limit: int = 10) -> pd.DataFrame:
    conn = get_connection()
    try:
        return conn.execute(f"""
            SELECT 
                run_id, run_timestamp, mode, status, 
                total_rows_fetched, total_rows_inserted, duration_seconds
            FROM ingestion_log
            ORDER BY run_timestamp DESC
            LIMIT {limit}
        """).fetchdf()
    finally:
        conn.close()

@st.cache_data(ttl=60)
def get_active_warnings(limit: int = 50) -> pd.DataFrame:
    """Get recent Warnings and Critical errors."""
    conn = get_connection()
    try:
        return conn.execute(f"""
            SELECT 
                finding_timestamp, severity, code, series_id, message
            FROM dq_report
            WHERE severity IN ('warning', 'critical')
            ORDER BY finding_timestamp DESC
            LIMIT {limit}
        """).fetchdf()
    finally:
        conn.close()

def show_health_monitor():
    st.header("🏥 Pipeline Health")
    st.caption("Operational status of the ingestion pipeline.")

    # Top Metrics
    runs = get_recent_runs(5)
    last_run = runs.iloc[0]
    
    c1, c2, c3 = st.columns(3)
    
    status_color = "normal" if last_run["status"] == "success" else "off"
    status_label = "✅ Online" if last_run["status"] == "success" else "❌ Issues"
    
    c1.metric("System Status", status_label, delta_color=status_color)
    c2.metric("Last Run", last_run["run_timestamp"].strftime("%H:%M:%S UTC"))
    c3.metric("Rows Ingested", f"{last_run['total_rows_inserted']:,}")

    # Recent Runs Table
    st.subheader("Recent Ingestion Runs")
    
    # Styled dataframe
    def color_status(val):
        color = '#d4edda' if val == 'success' else '#f8d7da'
        return f'background-color: {color}'

    st.dataframe(
        runs.style.applymap(color_status, subset=['status']),
        use_container_width=True
    )

    # DQ Issues
    st.subheader("⚠️ Active Data Quality Warnings")
    warnings = get_active_warnings()
    
    if warnings.empty:
        st.success("No active warnings! 🎉")
    else:
        # Severity Pills
        for _, row in warnings.iterrows():
            color = "red" if row["severity"] == "critical" else "orange"
            with st.container():
                c_sev, c_msg = st.columns([1, 6])
                c_sev.markdown(f":{color}[**{row['code']}**]")
                c_msg.markdown(f"**{row['series_id']}**: {row['message']}")
                st.divider()

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    show_health_monitor()
