import pandas as pd
from typing import List, Dict, Any, Optional
from src.fred_macro.db import get_connection

class ReadRepository:
    def get_run_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    run_id, run_timestamp, mode, status,
                    total_rows_fetched, total_rows_inserted, total_rows_updated,
                    duration_seconds, error_message
                FROM ingestion_log
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "run_id": row[0],
                "run_timestamp": row[1],
                "mode": row[2],
                "status": row[3],
                "rows_fetched": row[4],
                "rows_inserted": row[5],
                "duration": row[7],
                "error": row[8]
            }
        finally:
            conn.close()

    def get_latest_run_id(self) -> Optional[str]:
        conn = get_connection()
        try:
            res = conn.execute("SELECT run_id FROM ingestion_log ORDER BY run_timestamp DESC LIMIT 1").fetchone()
            return res[0] if res else None
        finally:
            conn.close()

    def get_dq_findings(self, run_id: str, severity: str = "all", limit: int = 50) -> List[tuple]:
        conn = get_connection()
        try:
            query = """
                SELECT severity, code, series_id, message, metadata
                FROM dq_report
                WHERE run_id = ?
            """
            params = [run_id]
            if severity != "all":
                query += " AND severity = ?"
                params.append(severity)
            query += " ORDER BY finding_timestamp DESC LIMIT ?"
            params.append(limit)
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()

    def get_dq_counts(self, run_id: str) -> Dict[str, int]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT severity, COUNT(*) FROM dq_report WHERE run_id = ? GROUP BY severity",
                (run_id,)
            ).fetchall()
            counts = {"info": 0, "warning": 0, "critical": 0}
            for sev, cnt in rows:
                counts[sev] = cnt
            return counts
        finally:
            conn.close()

    def get_series_catalog_df(self) -> pd.DataFrame:
        conn = get_connection()
        try:
            return conn.execute("SELECT * FROM series_catalog").fetchdf()
        finally:
            conn.close()

    def get_latest_values_df(self, tier: int = None) -> pd.DataFrame:
        conn = get_connection()
        try:
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
            return conn.execute(query, params).fetchdf()
        finally:
            conn.close()

    def get_history_df(self, series_ids: List[str], years: int = 5) -> pd.DataFrame:
        if not series_ids:
            return pd.DataFrame()
        conn = get_connection()
        try:
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
            return conn.execute(query, series_ids).fetchdf()
        finally:
            conn.close()

    def get_recent_runs_df(self, limit: int = 10) -> pd.DataFrame:
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

    def get_active_warnings_df(self, limit: int = 50) -> pd.DataFrame:
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
