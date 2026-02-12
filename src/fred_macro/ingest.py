import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import yaml

from src.fred_macro.db import get_connection
from src.fred_macro.fred_client import FredClient

logger = logging.getLogger(__name__)


class IngestionEngine:
    def __init__(self, config_path: str = "config/series_catalog.yaml"):
        self.config_path = config_path
        self.client = FredClient()
        with open(config_path, "r") as f:
            self.catalog = yaml.safe_load(f)

    def _get_series_list(self) -> List[Dict[str, Any]]:
        """Retrieve list of series from config."""
        return self.catalog.get("series", [])

    def _determine_start_date(self, mode: str) -> str:
        """
        Determine start date based on mode.
        Backfill: 10 years ago (or more)
        Incremental: 60 days ago (to catch revisions)
        """
        today = datetime.now()
        if mode == "backfill":
            # MVP requirement: 10 years of history
            start_date = today - timedelta(days=365 * 10)
        else:
            # MVP requirement: Last 60 days for incremental
            start_date = today - timedelta(days=60)

        return start_date.strftime("%Y-%m-%d")

    def _upsert_data(self, df: pd.DataFrame) -> int:
        """
        Upsert data into observations table using MERGE INTO.
        Returns number of rows inserted/updated.
        """
        if df.empty:
            return 0

        conn = get_connection()
        try:
            # Create a temporary table for the batch
            conn.register("batch_data", df)

            # MERGE INTO observations
            # Match on (series_id, observation_date)
            # Update value and load_timestamp if matched
            # Insert if not matched
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
                VALUES (source.series_id, source.observation_date, source.value, CURRENT_TIMESTAMP);
            """

            # Execute merge
            conn.execute(query)

            # Get count of affected rows (not strictly returned by MERGE in all DBs,
            # but we can approximate or just return row count of dataframe)
            # DuckDB's MERGE doesn't easily return counts, so we'll assume success
            # means all rows were processed.
            count = len(df)

            return count
        except Exception as e:
            logger.error(f"Error upserting data: {e}")
            raise
        finally:
            conn.close()

    def _log_run(
        self,
        run_id: str,
        mode: str,
        series_ingested: List[str],
        rows_fetched: int,
        rows_processed: int,
        duration: float,
        status: str,
        error_message: str = None,
    ):
        """Log the ingestion run to ingestion_log table."""
        conn = get_connection()
        try:
            query = """
            INSERT INTO ingestion_log (
                run_id, run_timestamp, mode, series_ingested,
                total_rows_fetched, total_rows_inserted, total_rows_updated,
                duration_seconds, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # For simplicity in MVP, we treat rows_processed as total ops.
            # We don't distinguish inserted vs updated perfectly yet.
            # Using 0 for the other to allow schema compliance.

            params = (
                run_id,
                datetime.now(),
                mode,
                json.dumps(series_ingested),
                rows_fetched,
                rows_processed,  # inserted (approx)
                0,  # updated (approx - todo improve metrics)
                duration,
                status,
                error_message,
            )

            conn.execute(query, params)
        except Exception as e:
            logger.error(f"Failed to log run: {e}")
        finally:
            conn.close()

    def run(self, mode: str = "incremental"):
        """
        Execute the ingestion pipeline.

        Args:
            mode: 'backfill' or 'incremental'
        """
        run_id = str(uuid.uuid4())
        start_time = time.time()
        logger.info(f"Starting ingestion run {run_id} in {mode} mode")

        series_list = self._get_series_list()
        series_ingested = []
        total_fetched = 0
        total_processed = 0
        status = "success"
        error_msg = None

        start_date = self._determine_start_date(mode)

        try:
            for item in series_list:
                series_id = item["series_id"]
                try:
                    df = self.client.get_series_data(series_id, start_date=start_date)

                    if not df.empty:
                        count = self._upsert_data(df)
                        total_fetched += len(df)
                        total_processed += count
                        logger.info(f"Processed {series_id}: {len(df)} rows")
                    else:
                        logger.warning(f"No data found for {series_id}")

                    series_ingested.append(series_id)

                except Exception as e:
                    logger.error(f"Failed to process {series_id}: {e}")
                    status = "partial"  # Continue processing others
                    error_msg = str(e)  # Store last error

        except Exception as e:
            logger.critical(f"Critical failure in ingestion run: {e}")
            status = "failed"
            error_msg = str(e)

        finally:
            duration = time.time() - start_time
            self._log_run(
                run_id,
                mode,
                series_ingested,
                total_fetched,
                total_processed,
                duration,
                status,
                error_msg,
            )
            logger.info(
                f"Ingestion run complete. Status: {status}. "
                f"Series: {len(series_ingested)}"
            )


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "incremental"
    logging.basicConfig(level=logging.INFO)
    engine = IngestionEngine()
    engine.run(mode=mode)
