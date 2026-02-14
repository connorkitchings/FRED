import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from src.fred_macro.clients import ClientFactory
from src.fred_macro.db import get_connection
from src.fred_macro.logging_config import get_logger, setup_logging
from src.fred_macro.validation import (
    ValidationFinding,
    count_findings_by_severity,
    run_data_quality_checks,
    summarize_findings,
)

from src.fred_macro.services.catalog import CatalogService

logger = get_logger(__name__)


class IngestionEngine:
    def __init__(
        self, config_path: str = "config/series_catalog.yaml", alert_manager=None
    ):
        self.config_path = config_path
        self.catalog_service = CatalogService(config_path)
        self.current_run_id = None
        self.alert_manager = alert_manager
        self.writer = None  # Initialize writer attribute to avoid AttributeError

    def _get_series_list(self) -> List[Dict[str, Any]]:
        """Retrieve list of series from config as dictionaries."""
        # Convert Pydantic models back to dicts for compatibility with existing logic
        return [s.model_dump() for s in self.catalog_service.get_all_series()]

    def _group_series_by_source(
        self, series_list: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group configured series by data source."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in series_list:
            source = str(item.get("source", "FRED")).strip().upper()
            grouped.setdefault(source, []).append(item)
        return grouped

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
                VALUES (source.series_id, source.observation_date, source.value,
                        CURRENT_TIMESTAMP);
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

    def _log_dq_findings(
        self,
        run_id: str,
        findings: List[ValidationFinding],
    ) -> bool:
        """Persist structured data-quality findings for a run."""
        try:
            self.writer.repo.insert_dq_findings(run_id, findings)
            return True
        except Exception as e:
            logger.error("Failed to persist DQ findings for run %s: %s", run_id, e)
            return False

    def _update_logged_run_status(
        self,
        run_id: str,
        status: str,
        error_message: str | None,
    ) -> bool:
        """Patch ingestion_log row after write, if needed."""
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
            return True
        except Exception as e:
            logger.error("Failed to update run status for %s: %s", run_id, e)
            return False
        finally:
            conn.close()

    @staticmethod
    def _append_error(existing: str | None, message: str) -> str:
        if existing:
            return f"{existing}; {message}"
        return message

    def run(self, mode: str = "incremental") -> str:
        """
        Execute the ingestion pipeline.

        Args:
            mode: 'backfill' or 'incremental'
        Returns:
            str: The run_id
        """
        self.current_run_id = str(uuid.uuid4())
        start_time = time.time()
        logger.info(f"Starting ingestion run {self.current_run_id} in {mode} mode")

        series_list = self._get_series_list()
        series_ingested = []
        total_fetched = 0
        total_processed = 0
        status = "success"
        error_msg = None
        run_series_stats: Dict[str, Dict[str, int]] = {}
        dq_findings: List[ValidationFinding] = []

        start_date = self._determine_start_date(mode)

        try:
            for item in series_list:
                series_id = item["series_id"]
                run_series_stats[series_id] = {
                    "rows_fetched": 0,
                    "rows_processed": 0,
                }

            for source, source_items in self._group_series_by_source(
                series_list
            ).items():
                try:
                    client = ClientFactory.get_client(source)
                except Exception as e:
                    logger.error(
                        f"Failed to initialize client for source {source}: {e}"
                    )
                    status = "partial"
                    error_msg = self._append_error(error_msg, f"{source}: {e}")
                    continue

                for item in source_items:
                    series_id = item["series_id"]
                    try:
                        df = client.get_series_data(series_id, start_date=start_date)
                        run_series_stats[series_id]["rows_fetched"] = len(df)

                        if not df.empty:
                            count = self._upsert_data(df)
                            run_series_stats[series_id]["rows_processed"] = count
                            total_fetched += len(df)
                            total_processed += count
                            logger.info(
                                f"Processed {series_id} ({source}): {len(df)} rows"
                            )
                        else:
                            logger.warning(f"No data found for {series_id} ({source})")

                        series_ingested.append(series_id)

                    except Exception as e:
                        logger.error(f"Failed to process {series_id} ({source}): {e}")
                        status = "partial"  # Continue processing others
                        error_msg = self._append_error(error_msg, f"{series_id}: {e}")

            dq_findings = run_data_quality_checks(
                mode=mode,
                configured_series=series_list,
                run_series_stats=run_series_stats,
            )
            dq_counts = count_findings_by_severity(dq_findings)

            logger.info(
                "Data-quality summary: critical=%s warning=%s info=%s",
                dq_counts["critical"],
                dq_counts["warning"],
                dq_counts["info"],
            )

            if dq_counts["warning"] > 0:
                logger.warning(
                    "Data-quality warnings: %s",
                    summarize_findings(
                        [f for f in dq_findings if f.severity == "warning"],
                    ),
                )

            if dq_counts["critical"] > 0:
                critical_summary = summarize_findings(
                    [f for f in dq_findings if f.severity == "critical"],
                )
                status = "failed"
                error_msg = self._append_error(
                    error_msg,
                    f"dq_critical={critical_summary}",
                )

        except Exception as e:
            logger.critical(f"Critical failure in ingestion run: {e}")
            status = "failed"
            error_msg = str(e)

        finally:
            duration = time.time() - start_time
            self._log_run(
                self.current_run_id,
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
            dq_logged = self._log_dq_findings(self.current_run_id, dq_findings)
            if not dq_logged:
                patched_status = "failed" if status == "failed" else "partial"
                patched_error = self._append_error(
                    error_msg,
                    "dq_report_logging_failed",
                )
                self._update_logged_run_status(
                    run_id=self.current_run_id,
                    status=patched_status,
                    error_message=patched_error,
                )

            # Evaluate alerting rules
            if self.alert_manager:
                alert_context = {
                    "run_id": self.current_run_id,
                    "run_status": status,
                    "dq_findings": [f.model_dump() for f in dq_findings],
                    "total_series": len(series_list),
                    "failed_series": len(series_list) - len(series_ingested),
                    "series_ingested": series_ingested,
                }
                self.alert_manager.check_and_alert(alert_context)

        return self.current_run_id


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "incremental"
    setup_logging()
    engine = IngestionEngine()
    engine.run(mode=mode)
