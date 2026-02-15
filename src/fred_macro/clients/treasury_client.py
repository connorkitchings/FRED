"""Client for U.S. Treasury Fiscal Data API."""

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


class TreasuryClient:
    """
    Client for the U.S. Treasury Fiscal Data API.

    Handles rate limiting and data transformation to match the standard
    DataSourceClient protocol.

    Reference: https://fiscaldata.treasury.gov/api-documentation/
    """

    BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"

    # Series mapping: internal series_id -> API endpoint and filters
    SERIES_MAPPING = {
        "TREAS_AVG_BILLS": {
            "endpoint": "v2/accounting/od/avg_interest_rates",
            "filter": "security_type_desc:eq:Treasury Bills",
            "value_field": "avg_interest_rate_amt",
        },
        "TREAS_AVG_NOTES": {
            "endpoint": "v2/accounting/od/avg_interest_rates",
            "filter": "security_type_desc:eq:Treasury Notes",
            "value_field": "avg_interest_rate_amt",
        },
        "TREAS_AVG_BONDS": {
            "endpoint": "v2/accounting/od/avg_interest_rates",
            "filter": "security_type_desc:eq:Treasury Bonds",
            "value_field": "avg_interest_rate_amt",
        },
        "TREAS_AVG_TIPS": {
            "endpoint": "v2/accounting/od/avg_interest_rates",
            "filter": "security_type_desc:eq:Treasury Inflation-Protected Securities (TIPS)",
            "value_field": "avg_interest_rate_amt",
        },
        "TREAS_AUCTION_10Y": {
            "endpoint": "v1/accounting/od/auctions_query",
            "filter": "security_term:eq:10-Year",
            "value_field": "high_investment_rate",
        },
        "TREAS_AUCTION_2Y": {
            "endpoint": "v1/accounting/od/auctions_query",
            "filter": "security_term:eq:2-Year",
            "value_field": "high_investment_rate",
        },
        "TREAS_AUCTION_30Y": {
            "endpoint": "v1/accounting/od/auctions_query",
            "filter": "security_term:eq:30-Year",
            "value_field": "high_investment_rate",
        },
        "TREAS_BID_COVER_10Y": {
            "endpoint": "v1/accounting/od/auctions_query",
            "filter": "security_term:eq:10-Year",
            "value_field": "bid_to_cover_ratio",
        },
    }

    def __init__(self):
        """
        Initialize Treasury client.

        No API key required - the Treasury Fiscal Data API is public.
        """
        self._last_request_time = 0.0
        # Conservative rate limit: 0.3s delay between requests
        self._rate_limit_delay = 0.3
        logger.info("Treasury client initialized (public API, no authentication)")

    def _enforce_rate_limit(self):
        """Sleep if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _build_filters(
        self,
        base_filter: str,
        endpoint: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        Build filter string for API request.

        Args:
            base_filter: Base filter from SERIES_MAPPING (e.g., security type)
            endpoint: API endpoint being called
            start_date: Optional YYYY-MM-DD start date
            end_date: Optional YYYY-MM-DD end date

        Returns:
            Complete filter string for API request
        """
        filters = [base_filter]

        # Determine date field based on endpoint
        # Average interest rates use 'record_date'
        # Auction data uses 'auction_date'
        date_field = (
            "record_date"
            if "avg_interest_rates" in endpoint
            else "auction_date"
        )

        if start_date:
            filters.append(f"{date_field}:gte:{start_date}")
        if end_date:
            filters.append(f"{date_field}:lte:{end_date}")

        return ",".join(filters)

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
        Fetch data for a specific Treasury series.

        Args:
            series_id: Treasury series ID (e.g., 'TREAS_AVG_BILLS')
            start_date: Optional 'YYYY-MM-DD' string for start date
            end_date: Optional 'YYYY-MM-DD' string for end date

        Returns:
            pd.DataFrame: DataFrame with columns:
                - observation_date (datetime): Date of the observation
                - value (float): The data value
                - series_id (str): The series identifier

        Raises:
            ValueError: If series_id is not recognized
            requests.RequestException: If the API request fails
        """
        if series_id not in self.SERIES_MAPPING:
            raise ValueError(
                f"Unknown Treasury series: {series_id}. "
                f"Available series: {', '.join(self.SERIES_MAPPING.keys())}"
            )

        self._enforce_rate_limit()

        series_config = self.SERIES_MAPPING[series_id]
        endpoint = series_config["endpoint"]
        base_filter = series_config["filter"]
        value_field = series_config["value_field"]

        # Build complete filter string
        filter_str = self._build_filters(base_filter, endpoint, start_date, end_date)

        # Determine date field for parsing
        date_field = (
            "record_date"
            if "avg_interest_rates" in endpoint
            else "auction_date"
        )

        try:
            logger.info(f"Fetching Treasury series {series_id}...")

            # Build request with pagination support
            all_data = []
            page = 1
            page_size = 10000  # Max page size

            while True:
                params = {
                    "filter": filter_str,
                    "page[size]": page_size,
                    "page[number]": page,
                    "sort": f"-{date_field}",  # Newest first
                }

                response = requests.get(
                    f"{self.BASE_URL}{endpoint}",
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()

                data = response.json()

                # Extract records
                records = data.get("data", [])
                if not records:
                    break

                all_data.extend(records)

                # Check if there are more pages
                meta = data.get("meta", {})
                total_pages = meta.get("total-pages", 1)
                if page >= total_pages:
                    break

                page += 1

            if not all_data:
                logger.warning(f"No data found for Treasury series {series_id}")
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            # Parse records into DataFrame
            rows = []
            for record in all_data:
                obs_date = record.get(date_field)
                value = record.get(value_field)

                if obs_date and value:
                    rows.append(
                        {
                            "observation_date": obs_date,
                            "value": value,
                            "series_id": series_id,
                        }
                    )

            # Create DataFrame
            df = pd.DataFrame(rows)

            # Ensure proper types
            df.loc[:, "observation_date"] = pd.to_datetime(df["observation_date"])
            df.loc[:, "value"] = pd.to_numeric(df["value"], errors="coerce")

            # Sort by date (oldest first)
            df = df.sort_values("observation_date").reset_index(drop=True)

            # Additional date filtering (API filters may not be exact)
            if start_date:
                df = df[df["observation_date"] >= pd.Timestamp(start_date)]
            if end_date:
                df = df[df["observation_date"] <= pd.Timestamp(end_date)]

            logger.info(f"Fetched {len(df)} observations for Treasury series {series_id}")

            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching Treasury series {series_id}: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Treasury response for {series_id}: {e}")
            raise
