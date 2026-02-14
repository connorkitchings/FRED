"""Client for Bureau of Labor Statistics (BLS) API."""

import os
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.fred_macro.logging_config import get_logger

logger = get_logger(__name__)


class BLSClient:
    """
    Client for the Bureau of Labor Statistics (BLS) Public Data API v2.

    Handles authentication, rate limiting, and data transformation to match
    the standard DataSourceClient protocol.

    Reference: https://www.bls.gov/developers/api_signature_v2.htm
    """

    BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize BLS client.

        Args:
            api_key: Optional BLS API key. If not provided, reads from BLS_API_KEY
                     environment variable. API key is optional but recommended for
                     higher rate limits (50 queries/10s vs 10 queries/10s).
        """
        self.api_key = api_key or os.getenv("BLS_API_KEY")
        self._last_request_time = 0.0

        # Rate limits:
        # - Registered (with API key): 50 queries / 10 seconds
        # - Unregistered: 10 queries / 10 seconds
        # Use 0.5s delay to stay safe (allows ~20 queries/10s)
        self._rate_limit_delay = 0.5

        if self.api_key:
            logger.info("BLS client initialized with API key (registered rate limits)")
        else:
            logger.warning(
                "BLS client initialized without API key (unregistered rate limits). "
                "Consider registering at https://data.bls.gov/registrationEngine/"
            )

    def _enforce_rate_limit(self):
        """Sleep if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _parse_period_to_date(self, year: str, period: str) -> str:
        """
        Convert BLS period format to YYYY-MM-DD date string.

        Args:
            year: Year as string (e.g., "2024")
            period: BLS period code. Common formats:
                    - M01-M12: Monthly data (January-December)
                    - Q01-Q04: Quarterly data
                    - A01: Annual data

        Returns:
            Date string in YYYY-MM-DD format

        Raises:
            ValueError: If period format is not recognized
        """
        # Monthly periods: M01-M12
        if period.startswith("M"):
            month = int(period[1:])
            if 1 <= month <= 12:
                # Use first day of the month
                return f"{year}-{month:02d}-01"

        # Quarterly periods: Q01-Q04
        if period.startswith("Q"):
            quarter = int(period[1:])
            if 1 <= quarter <= 4:
                # Use first month of the quarter
                month = (quarter - 1) * 3 + 1
                return f"{year}-{month:02d}-01"

        # Annual periods: A01
        if period == "A01":
            return f"{year}-01-01"

        raise ValueError(f"Unsupported BLS period format: {period}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
    )
    def get_series_data(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch data for a specific BLS series.

        Args:
            series_id: BLS series ID (e.g., 'LNS14000000' for unemployment rate)
            start_date: Optional 'YYYY-MM-DD' string for start date
            end_date: Optional 'YYYY-MM-DD' string for end date

        Returns:
            pd.DataFrame: DataFrame with columns:
                - observation_date (datetime): Date of the observation
                - value (float): The data value
                - series_id (str): The series identifier

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response format is invalid
        """
        self._enforce_rate_limit()

        # Convert dates to years for BLS API
        start_year = None
        end_year = None
        if start_date:
            start_year = datetime.strptime(start_date, "%Y-%m-%d").year
        if end_date:
            end_year = datetime.strptime(end_date, "%Y-%m-%d").year

        # Build request payload
        payload = {"seriesid": [series_id]}

        if start_year and end_year:
            payload["startyear"] = str(start_year)
            payload["endyear"] = str(end_year)

        if self.api_key:
            payload["registrationkey"] = self.api_key

        try:
            logger.info(f"Fetching BLS series {series_id}...")

            response = requests.post(
                self.BASE_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Check API response status
            if data.get("status") != "REQUEST_SUCCEEDED":
                error_msg = data.get("message", ["Unknown error"])[0]
                raise ValueError(f"BLS API request failed: {error_msg}")

            # Extract series data
            results = data.get("Results", {})
            series_list = results.get("series", [])

            if not series_list:
                logger.warning(f"No data found for BLS series {series_id}")
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            series_data = series_list[0]
            observations = series_data.get("data", [])

            if not observations:
                logger.warning(f"No observations found for BLS series {series_id}")
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            # Parse observations into DataFrame
            rows = []
            for obs in observations:
                year = obs["year"]
                period = obs["period"]
                value = obs["value"]

                try:
                    obs_date = self._parse_period_to_date(year, period)
                    rows.append(
                        {
                            "observation_date": obs_date,
                            "value": value,
                            "series_id": series_id,
                        }
                    )
                except ValueError as e:
                    logger.warning(
                        f"Skipping observation with invalid period: {e} "
                        f"(year={year}, period={period})"
                    )
                    continue

            # Create DataFrame
            df = pd.DataFrame(rows)

            # Ensure proper types (use .loc to avoid chained assignment warnings)
            df.loc[:, "observation_date"] = pd.to_datetime(df["observation_date"])
            df.loc[:, "value"] = pd.to_numeric(df["value"], errors="coerce")

            # Sort by date (BLS returns newest first)
            df = df.sort_values("observation_date").reset_index(drop=True)

            # Filter by date range if specified
            if start_date:
                df = df[df["observation_date"] >= start_date]
            if end_date:
                df = df[df["observation_date"] <= end_date]

            logger.info(f"Fetched {len(df)} observations for BLS series {series_id}")

            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching BLS series {series_id}: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing BLS response for {series_id}: {e}")
            raise
