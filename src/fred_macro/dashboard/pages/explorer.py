import streamlit as st
import plotly.express as px
from src.fred_macro.dashboard.data import get_series_catalog, get_history
import pandas as pd

def show_data_explorer():
    st.header("🔎 Data Explorer")
    st.caption("Deep dive into individual series with interactive charts and raw data.")

    # Load Catalog
    catalog = get_series_catalog()
    
    # --- Sidebar Controls ---
    with st.sidebar:
        st.subheader("Filter Series")
        
        # Source Filter
        sources = ["All"] + sorted(catalog["source"].dropna().unique().tolist())
        sel_source = st.selectbox("Source", sources)
        
        # Tier Filter
        tiers = ["All"] + sorted(catalog["tier"].dropna().unique().tolist())
        sel_tier = st.selectbox("Tier", tiers)
        
        # Filter Logic
        filtered_catalog = catalog.copy()
        if sel_source != "All":
            filtered_catalog = filtered_catalog[filtered_catalog["source"] == sel_source]
        if sel_tier != "All":
            filtered_catalog = filtered_catalog[filtered_catalog["tier"] == sel_tier]
            
        # Series Selection
        # Create a label map for the selectbox: "ID - Title"
        filtered_catalog["label"] = filtered_catalog["series_id"] + " - " + filtered_catalog["title"]
        series_options = filtered_catalog["label"].tolist()
        
        if not series_options:
            st.warning("No series match filters.")
            return

        sel_label = st.selectbox("Select Series", series_options)
        
        # Extract ID from label
        series_id = sel_label.split(" - ")[0]
        series_meta = filtered_catalog[filtered_catalog["series_id"] == series_id].iloc[0]

        # Date Range
        st.subheader("Time Range")
        years_back = st.slider("Lookback (Years)", 1, 30, 10)

    # --- Main Content ---
    
    # 1. Fetch Data
    df = get_history([series_id], years=years_back)
    
    if df.empty:
        st.warning(f"No data found for {series_id} in the last {years_back} years.")
        return

    # 2. Hero Chart
    st.subheader(f"{series_meta['title']}")
    
    # Metadata Badge Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ID", series_id)
    m2.metric("Source", series_meta["source"])
    m3.metric("Frequency", series_meta["frequency"])
    m4.metric("Units", series_meta["units"])
    
    # Plotly Chart
    fig = px.line(
        df, 
        x="observation_date", 
        y="value", 
        title=None,
        labels={"value": series_meta["units"], "observation_date": "Date"}
    )
    
    fig.update_traces(line=dict(width=2.5, color="#0068C9"))
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=0, r=0, t=20, b=0),
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 3. Description
    with st.expander("ℹ️ Series Description", expanded=True):
        st.markdown(series_meta["description"])
        st.markdown(f"**Seasonal Adjustment:** {series_meta['seasonal_adjustment']}")

    # 4. Raw Data Tab
    st.divider()
    tab1, tab2 = st.tabs(["📄 Raw Data", "📊 Statistics"])
    
    with tab1:
        st.dataframe(
            df.sort_values("observation_date", ascending=False),
            use_container_width=True
        )
        
    with tab2:
        desc = df["value"].describe()
        st.table(desc)

if __name__ == "__main__":
    # For testing isolation
    st.set_page_config(layout="wide")
    show_data_explorer()
