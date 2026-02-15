import json
import uuid
from datetime import datetime
from typing import Any, List, Optional

import pandas as pd

from src.fred_macro.db import get_connection
from src.fred_macro.logging_config import get_logger

logger = get_logger(__name__)


class WriteRepository:
    def upsert_observations(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        conn = get_connection()
        try:
            conn.register("batch_data", df)
            query = """
            MERGE INTO observations AS target
            USING batch_data AS source
            ON target.series_id = source.series_id
               AND target.observation_date = source.observation_date
            WHEN MATCHED THEN
                UPDATE SET value = source.value,
                           load_timestamp = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (series_id, observation_date, value, load_timestamp)
                VALUES (source.series_id, source.observation_date, source.value,
                        CURRENT_TIMESTAMP);
            """
            conn.execute(query)
            return len(df)
        finally:
            conn.close()

    def create_run_log(
        self,
        run_id: str,
        mode: str,
        series_ingested: List[str],
        rows_fetched: int,
        rows_processed: int,
        duration: float,
        status: str,
        error_message: Optional[str],
    ):
        conn = get_connection()
        try:
            query = """
            INSERT INTO ingestion_log (
                run_id, run_timestamp, mode, series_ingested,
                total_rows_fetched, total_rows_inserted, total_rows_updated,
                duration_seconds, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                run_id,
                datetime.now(),
                mode,
                json.dumps(series_ingested),
                rows_fetched,
                rows_processed,
                0,
                duration,
                status,
                error_message,
            )
            conn.execute(query, params)
        finally:
            conn.close()

    def update_run_status(self, run_id: str, status: str, error_message: Optional[str]):
        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE ingestion_log
                SET status = ?, error_message = ?
                WHERE run_id = ?
                """,
                (status, error_message, run_id),
            )
        finally:
            conn.close()

    def insert_dq_findings(self, run_id: str, findings: List[Any]):
        """
        Findings is list of objects with severity, code, series_id, message, metadata.
        """
        if not findings:
            return
        conn = get_connection()
        try:
            query = """
            INSERT INTO dq_report (
                report_id, run_id, finding_timestamp, severity, code,
                series_id, message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            for f in findings:
                conn.execute(
                    query,
                    (
                        str(uuid.uuid4()),
                        run_id,
                        datetime.now(),
                        f.severity,
                        f.code,
                        f.series_id,
                        f.message,
                        json.dumps(f.metadata) if f.metadata else None,
                    ),
                )
        finally:
            conn.close()
