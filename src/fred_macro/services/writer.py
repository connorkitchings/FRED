import pandas as pd
from typing import List, Optional
from src.fred_macro.repositories.write_repo import WriteRepository
from src.fred_macro.logging_config import get_logger

logger = get_logger(__name__)


class DataWriter:
    """
    Service responsible for writing data, delegating to WriteRepository.
    """

    def __init__(self):
        self.repo = WriteRepository()

    def upsert_data(self, df: pd.DataFrame) -> int:
        try:
            return self.repo.upsert_observations(df)
        except Exception as e:
            logger.error(f"Error upserting data: {e}")
            raise

    def log_run(
        self,
        run_id: str,
        mode: str,
        series_ingested: list[str],
        rows_fetched: int,
        rows_processed: int,
        duration: float,
        status: str,
        error_message: str | None,
    ):
        try:
            self.repo.create_run_log(
                run_id,
                mode,
                series_ingested,
                rows_fetched,
                rows_processed,
                duration,
                status,
                error_message,
            )
        except Exception as e:
            logger.error(f"Failed to log run: {e}")

    def update_run_status(
        self, run_id: str, status: str, error_message: str | None
    ) -> bool:
        try:
            self.repo.update_run_status(run_id, status, error_message)
            return True
        except Exception as e:
            logger.error(f"Failed to update run status for {run_id}: {e}")
            return False
