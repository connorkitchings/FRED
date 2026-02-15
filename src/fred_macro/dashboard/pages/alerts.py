"""Alert History page for the Streamlit dashboard."""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from src.fred_macro.db import get_connection
from src.fred_macro.logging_config import get_logger

logger = get_logger(__name__)


def load_alert_history(days: int = 30) -> pd.DataFrame:
    """Load alert history from database."""
    try:
        conn = get_connection()

        # Check if table exists
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alert_history'"
        ).fetchall()

        if not tables:
            # Table doesn't exist yet
            return pd.DataFrame()

        query = """
            SELECT 
                alert_id,
                rule_name,
                severity,
                description,
                timestamp,
                details,
                metadata,
                acknowledged
            FROM alert_history
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        df = conn.execute(query, (cutoff_date,)).fetchdf()
        conn.close()

        return df
    except Exception as e:
        logger.error(f"Error loading alert history: {e}")
        return pd.DataFrame()


def get_alert_summary(days: int = 7) -> dict:
    """Get summary statistics for alerts."""
    try:
        conn = get_connection()

        # Check if table exists
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alert_history'"
        ).fetchall()

        if not tables:
            return {
                "total": 0,
                "critical": 0,
                "warning": 0,
                "info": 0,
                "acknowledged": 0,
                "unacknowledged": 0,
            }

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        summary = conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN severity = 'warning' THEN 1 ELSE 0 END) as warning,
                SUM(CASE WHEN severity = 'info' THEN 1 ELSE 0 END) as info,
                SUM(CASE WHEN acknowledged = TRUE THEN 1 ELSE 0 END) as acknowledged,
                SUM(CASE WHEN acknowledged = FALSE THEN 1 ELSE 0 END) as unacknowledged
            FROM alert_history
            WHERE timestamp >= ?
        """,
            (cutoff_date,),
        ).fetchone()

        conn.close()

        return {
            "total": summary[0] or 0,
            "critical": summary[1] or 0,
            "warning": summary[2] or 0,
            "info": summary[3] or 0,
            "acknowledged": summary[4] or 0,
            "unacknowledged": summary[5] or 0,
        }
    except Exception as e:
        logger.error(f"Error getting alert summary: {e}")
        return {
            "total": 0,
            "critical": 0,
            "warning": 0,
            "info": 0,
            "acknowledged": 0,
            "unacknowledged": 0,
        }


def acknowledge_alert(alert_id: str):
    """Mark an alert as acknowledged."""
    try:
        conn = get_connection()
        conn.execute(
            "UPDATE alert_history SET acknowledged = TRUE WHERE alert_id = ?",
            (alert_id,),
        )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return False


def render_alert_history():
    """Render the alert history page."""
    st.title("🚨 Alert History")
    st.markdown("View and manage system alerts and notifications")

    # Sidebar filters
    st.sidebar.header("Filters")

    days = st.sidebar.selectbox(
        "Time Range",
        options=[7, 14, 30, 90],
        index=2,
        format_func=lambda x: f"Last {x} days",
    )

    severity_filter = st.sidebar.multiselect(
        "Severity",
        options=["critical", "warning", "info"],
        default=["critical", "warning", "info"],
    )

    show_acknowledged = st.sidebar.checkbox("Show Acknowledged", value=True)
    show_unacknowledged = st.sidebar.checkbox("Show Unacknowledged", value=True)

    # Summary metrics
    st.header("Alert Summary (Last 7 Days)")
    summary = get_alert_summary(days=7)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Alerts", summary["total"])
    with col2:
        st.metric("🔴 Critical", summary["critical"])
    with col3:
        st.metric("🟡 Warnings", summary["warning"])
    with col4:
        st.metric("🔵 Info", summary["info"])

    # Acknowledgment status
    col5, col6 = st.columns(2)
    with col5:
        st.metric("✅ Acknowledged", summary["acknowledged"])
    with col6:
        st.metric("⏳ Unacknowledged", summary["unacknowledged"])

    st.divider()

    # Load alert data
    alerts_df = load_alert_history(days=days)

    if alerts_df.empty:
        st.info("No alerts found in the selected time range")
        return

    # Apply filters
    if severity_filter:
        alerts_df = alerts_df[alerts_df["severity"].isin(severity_filter)]

    if not show_acknowledged and not show_unacknowledged:
        st.warning("Please select at least one acknowledgment status")
        return
    elif not show_acknowledged:
        alerts_df = alerts_df[alerts_df["acknowledged"] == False]
    elif not show_unacknowledged:
        alerts_df = alerts_df[alerts_df["acknowledged"] == True]

    if alerts_df.empty:
        st.info("No alerts match the selected filters")
        return

    # Display alerts
    st.header(f"Alert Details ({len(alerts_df)} alerts)")

    for _, alert in alerts_df.iterrows():
        # Determine color based on severity
        severity_colors = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
        icon = severity_colors.get(alert["severity"], "⚪")

        # Format timestamp
        try:
            timestamp = pd.to_datetime(alert["timestamp"]).strftime("%Y-%m-%d %H:%M")
        except:
            timestamp = str(alert["timestamp"])

        # Acknowledgment status
        ack_status = "✅ Acknowledged" if alert["acknowledged"] else "⏳ Unacknowledged"

        with st.expander(
            f"{icon} [{alert['severity'].upper()}] {alert['rule_name']} - {timestamp}"
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**Description:** {alert['description']}")
                st.markdown(f"**Details:** {alert['details']}")
                st.markdown(f"**Status:** {ack_status}")

            with col2:
                if not alert["acknowledged"]:
                    if st.button("Acknowledge", key=f"ack_{alert['alert_id']}"):
                        if acknowledge_alert(alert["alert_id"]):
                            st.success("Acknowledged!")
                            st.rerun()
                        else:
                            st.error("Failed to acknowledge")

    # Download option
    st.divider()
    if st.button("📥 Download Alert History"):
        csv = alerts_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"alert_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
