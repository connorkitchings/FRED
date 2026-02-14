import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.fred_macro.dashboard.data import (
    get_series_catalog,
    get_latest_values,
    get_history,
)
import pandas as pd

# Import Pages
from src.fred_macro.dashboard.pages.explorer import show_data_explorer
from src.fred_macro.dashboard.pages.health import show_health_monitor

# Page Config
st.set_page_config(
    page_title="FRED Macro Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS Styling ---
st.markdown(
    """
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to", ["Executive Summary", "Data Explorer", "Health Monitor"]
)

# --- Page Logic ---

if page == "Data Explorer":
    show_data_explorer()

elif page == "Health Monitor":
    show_health_monitor()

elif page == "Executive Summary":
    # --- Header ---
    st.title("🏛️ Macroeconomic Dashboard")
    st.markdown(
        "Monitoring key indicators of the US Economy. Data sourced from FRED & BLS."
    )
    st.divider()

    # --- Section 1: The Big Four (Tier 1 Metrics) ---
    st.subheader("🇺🇸 The Big Four: Core Economic Health")

    # Load Tier 1 Data
    latest_t1 = get_latest_values(tier=1)
    if not latest_t1.empty:
        cols = st.columns(4)

        # Map series IDs to friendly names/emojis if needed
        series_map = {
            "FEDFUNDS": "💸 Fed Funds Rate",
            "UNRATE": "👷 Unemployment",
            "CPIAUCSL": "🏷️ CPI (Index)",
            "GDPC1": "🏭 Real GDP",
        }

        # Iterate and display metrics
        # We want specific order: Growth, Inflation, Jobs, Policy
        display_order = ["GDPC1", "CPIAUCSL", "UNRATE", "FEDFUNDS"]

        for i, series_id in enumerate(display_order):
            row = latest_t1[latest_t1["series_id"] == series_id]
            if not row.empty:
                row = row.iloc[0]
                title = series_map.get(series_id, row["title"])
                val = row["value"]
                delta = row["delta"]

                # Formatting
                if series_id == "GDPC1":
                    fmt_val = f"${val:,.0f}B"
                    fmt_delta = f"{delta:,.0f}B"
                else:
                    fmt_val = (
                        f"{val:.2f}%" if "Percent" in row["units"] else f"{val:.1f}"
                    )
                    fmt_delta = f"{delta:.2f}"

                with cols[i]:
                    st.metric(
                        label=title,
                        value=fmt_val,
                        delta=fmt_delta,
                        help=f"Last updated: {row['observation_date']}",
                    )
    else:
        st.warning("No Tier 1 data found. Run ingestion first.")

    st.divider()

    # --- Section 2: Narrative Visualizations ---

    col_main, col_side = st.columns([2, 1])

    with col_main:
        st.subheader("🔥 Inflation vs. Policy Response")
        st.caption(
            "How the Federal Reserve adjusts rates in response to price levels (CPI)."
        )

        # Dual Axis Chart: CPI (Left) vs FEDFUNDS (Right)
        hist_df = get_history(["CPIAUCSL", "FEDFUNDS", "UNRATE", "GDPC1"], years=10)

        if not hist_df.empty:
            # Calculate YoY for CPI to make it comparable to Rates
            # Need to pivot first
            pivot_df = hist_df.pivot(
                index="observation_date", columns="series_id", values="value"
            )

            # Calculate YoY Change for CPI
            pivot_df["CPI_YoY"] = pivot_df["CPIAUCSL"].pct_change(12) * 100

            fig = go.Figure()

            # Trace 1: CPI YoY (Area/Line)
            fig.add_trace(
                go.Scatter(
                    x=pivot_df.index,
                    y=pivot_df["CPI_YoY"],
                    name="CPI (YoY %)",
                    line=dict(color="#FF6B6B", width=2),
                    fill="tozeroy",
                )
            )

            # Trace 2: Fed Funds (Line)
            fig.add_trace(
                go.Scatter(
                    x=pivot_df.index,
                    y=pivot_df["FEDFUNDS"],
                    name="Fed Funds Rate",
                    line=dict(color="#4ECDC4", width=3),
                )
            )

            fig.update_layout(
                height=450,
                legend=dict(orientation="h", y=1.1),
                margin=dict(l=20, r=20, t=20, b=20),
                hovermode="x unified",
                xaxis_title=None,
                yaxis_title="Percent (%)",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_side:
        st.subheader("📉 The Phillips Curve?")
        st.caption("Unemployment trend over the last decade.")

        fig_un = px.line(
            hist_df[hist_df["series_id"] == "UNRATE"],
            x="observation_date",
            y="value",
            color_discrete_sequence=["#FFE66D"],
        )
        fig_un.update_traces(line=dict(width=3))
        fig_un.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title=None,
            yaxis_title="Unemployment (%)",
            showlegend=False,
        )
        st.plotly_chart(fig_un, use_container_width=True)

        st.subheader("🏭 Real Growth")
        st.caption("Real GDP (Billions 2017 $)")

        fig_gdp = px.bar(
            hist_df[hist_df["series_id"] == "GDPC1"],
            x="observation_date",
            y="value",
            color_discrete_sequence=["#1A535C"],
        )
        fig_gdp.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title=None,
            yaxis_title="GDP ($B)",
            showlegend=False,
        )
        st.plotly_chart(fig_gdp, use_container_width=True)

    # --- Section 3: Data Explorer Preview ---
    st.divider()
    st.subheader("📂 Catalog Preview")
    with st.expander("View Active Series Catalog"):
        catalog = get_series_catalog()
        st.dataframe(
            catalog[["series_id", "title", "frequency", "source", "tier"]],
            use_container_width=True,
            hide_index=True,
        )
