import logging
import os
import time
from typing import Optional
from urllib.error import HTTPError

import pandas as pd
from fredapi import Fred
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class FredClient:
    """
    Wrapper around fredapi.Fred to handle rate limiting, error handling,
    and data transformation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FRED_API_KEY must be provided or set in environment variables."
            )

        self.client = Fred(api_key=self.api_key)
        self._last_request_time = 0.0
        self._rate_limit_delay = 1.0  # Seconds between requests to stay safe

    def _enforce_rate_limit(self):
        """Sleep if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((HTTPError, ConnectionError, TimeoutError)),
    )
    def get_series_data(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch data for a specific series.

        Args:
            series_id: The FRED series ID (e.g., 'GDP')
            start_date: 'YYYY-MM-DD' string
            end_date: 'YYYY-MM-DD' string

        Returns:
            pd.DataFrame: DataFrame with 'date' and 'value' columns.
        """
        self._enforce_rate_limit()
        try:
            logger.info(f"Fetching series {series_id}...")
            # fredapi returns a Series with datetime index
            series_data = self.client.get_series(
                series_id, observation_start=start_date, observation_end=end_date
            )

            # Convert to DataFrame
            df = series_data.to_frame(name="value")
            df.index.name = "observation_date"
            df.reset_index(inplace=True)

            # Add series_id column for database schema alignment
            df = df.assign(series_id=series_id)

            # Ensure proper types
            df["observation_date"] = pd.to_datetime(df["observation_date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

            return df

        except Exception as e:
            logger.error(f"Error fetching {series_id}: {e}")
            raise
