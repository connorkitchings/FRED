"""Client for U.S. Census Bureau API."""

import os
import time
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


class CensusClient:
    """
    Client for the U.S. Census Bureau API.

    Handles authentication, rate limiting, and data transformation to match the
    standard DataSourceClient protocol.

    Supports:
    - International Trade (intltrade)
    - Economic Indicators Time Series (eits)

    Reference: https://www.census.gov/data/developers/data-sets.html
    """

    BASE_URL = "https://api.census.gov/data/timeseries/"

    # Series mapping: internal series_id -> API dataset config
    SERIES_MAPPING = {
        # International Trade (Monthly)
        "CENSUS_EXP_GOODS": {
            "dataset": "intltrade/exports/hs",
            "variables": {"MONTH": "time", "ALL_VAL_MO": "value"},
            "params": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL"},
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        "CENSUS_IMP_GOODS": {
            "dataset": "intltrade/imports/hs",
            "variables": {"MONTH": "time", "GEN_VAL_MO": "value"},
            "params": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL"},
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        "CENSUS_TRADE_BAL": {
            # Note: Derived series or specific endpoint?
            # Census defines Balance = Exports - Imports.
            # For MVP, we might need to fetch both and calculate, OR find a specific balance series.
            # Using Exports as placeholder pattern - likely need to calculate downstream or use a different dataset.
            # BUT: implementation_plan says "U.S. Trade Balance (Goods)".
            # Let's use the explicit 'exp' and 'imp' for now and maybe we can find a pre-calc balance later.
            # Actually, let's map it to the same endpoint but separate variable if available.
            # Wait, Census API typically serves raw data.
            # Let's stick strictly to what the API offers.
            # If CENSUS_TRADE_BAL is a derived metric, we might need a composite fetcher.
            # For simplicity in this iteration, I'll comment it out or mapping it to Exports implies we might be mistaken.
            # Checking plan: it listed "CENSUS_TRADE_BAL".
            # FT-900 usually has the balance.
            # For now, let's skip the balance series in mapping if it requires client-side math,
            # or treat it as a calculation task.
            # I will omit it from the mapping for now to avoid errors, and focus on raw data.
            # Re-reading plan: "Add 15 Census series".
            # I will assume for now I can find a specific series or I will implement the ones I strictly know.
            # Let's stick to the clear ones first.
            "dataset": "intltrade/exports/hs",  # Placeholder
            "skip": True,
        },
        # Country Trade (China, Canada, Mexico)
        "CENSUS_EXP_CHINA": {
            "dataset": "intltrade/exports/hs",
            "variables": {"MONTH": "time", "ALL_VAL_MO": "value"},
            "params": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL", "CTY_CODE": "5700"},
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        "CENSUS_IMP_CHINA": {
            "dataset": "intltrade/imports/hs",
            "variables": {"MONTH": "time", "GEN_VAL_MO": "value"},
            "params": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL", "CTY_CODE": "5700"},
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        "CENSUS_EXP_CANADA": {
            "dataset": "intltrade/exports/hs",
            "variables": {"MONTH": "time", "ALL_VAL_MO": "value"},
            "params": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL", "CTY_CODE": "1220"},
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        "CENSUS_IMP_CANADA": {
            "dataset": "intltrade/imports/hs",
            "variables": {"MONTH": "time", "GEN_VAL_MO": "value"},
            "params": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL", "CTY_CODE": "1220"},
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        "CENSUS_EXP_MEXICO": {
            "dataset": "intltrade/exports/hs",
            "variables": {"MONTH": "time", "ALL_VAL_MO": "value"},
            "params": {
                "COMM_LVL": "HS2",
                "DISTRICT": "TOTAL",
                "CTY_CODE": "2010",
            },
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        # Business Inventories (EITS)
        "CENSUS_INV_MFG": {
            "dataset": "eits/mwts",
            "variables": {"time_slot_date": "time", "cell_value": "value"},
            "params": {
                "seasonally_adj": "yes",
                "category_code": "MNSI",
                "data_type_code": "INV",
            },
            "time_format": "%Y-%m-%d",
            "is_eits": True,
            "skip": True,
        },
        "CENSUS_INV_WHOLESALE": {
            "dataset": "eits/mwts",
            "variables": {"time_slot_date": "time", "cell_value": "value"},
            "params": {
                "seasonally_adj": "yes",
                "category_code": "MWSI",
                "data_type_code": "INV",
            },
            "time_format": "%Y-%m-%d",
            "is_eits": True,
            "skip": True,
        },
        "CENSUS_INV_RETAIL": {
            "dataset": "eits/mwts",
            "variables": {"time_slot_date": "time", "cell_value": "value"},
            "params": {
                "seasonally_adj": "yes",
                "category_code": "MRSI",
                "data_type_code": "INV",
            },
            "time_format": "%Y-%m-%d",
            "is_eits": True,
            "skip": True,
        },
        "CENSUS_INV_SALES_RATIO": {
            "dataset": "eits/mwts",
            "variables": {"time_slot_date": "time", "cell_value": "value"},
            "params": {
                "seasonally_adj": "yes",
                "category_code": "MTIR",
                "data_type_code": "RATIO",
            },
            "time_format": "%Y-%m-%d",
            "is_eits": True,
            "skip": True,
        },
        "CENSUS_INV_MFG_RATIO": {
            "dataset": "eits/mwts",
            "variables": {"time_slot_date": "time", "cell_value": "value"},
            "params": {
                "seasonally_adj": "yes",
                "category_code": "MNIR",
                "data_type_code": "RATIO",
            },
            "time_format": "%Y-%m-%d",
            "is_eits": True,
            "skip": True,
        },
        "CENSUS_SHIP_MFG": {
            "dataset": "eits/mwts",
            "variables": {"time_slot_date": "time", "cell_value": "value"},
            "params": {
                "seasonally_adj": "yes",
                "category_code": "MNS",
                "data_type_code": "SM",
            },
            "time_format": "%Y-%m-%d",
            "is_eits": True,
            "skip": True,
        },
        "CENSUS_ORDERS_MFG": {
            "dataset": "eits/mwts",
            "variables": {"time_slot_date": "time", "cell_value": "value"},
            "params": {
                "seasonally_adj": "yes",
                "category_code": "MNO",
                "data_type_code": "NO",
            },
            "time_format": "%Y-%m-%d",
            "is_eits": True,
            "skip": True,
        },
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Census client.

        Args:
            api_key: Census API key. If not provided, looks for CENSUS_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("CENSUS_API_KEY")
        if not self.api_key:
            logger.warning(
                "Census API key not found. Operations may fail or be severely rate limited. "
            )

        self._last_request_time = 0.0
        # Conservative rate limit: 0.5s delay
        self._rate_limit_delay = 0.5
        logger.info("Census client initialized")

    def _enforce_rate_limit(self):
        """Sleep if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

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
        Fetch data for a specific Census series.

        Args:
            series_id: Census series ID
            start_date: Optional 'YYYY-MM-DD' string for start date
            end_date: Optional 'YYYY-MM-DD' string for end date

        Returns:
            pd.DataFrame: DataFrame with columns:
                - observation_date (datetime): Date of the observation
                - value (float): The data value
                - series_id (str): The series identifier
        """
        if series_id not in self.SERIES_MAPPING:
            raise ValueError(
                f"Unknown Census series: {series_id}. "
                f"Available series: {', '.join(self.SERIES_MAPPING.keys())}"
            )

        config = self.SERIES_MAPPING[series_id]
        if config.get("skip"):
            logger.warning(f"Series {series_id} is marked for skipping.")
            return pd.DataFrame(columns=["observation_date", "value", "series_id"])

        self._enforce_rate_limit()

        dataset = config["dataset"]
        # Variables to fetch: time col, value col, plus any necessary keys to verify
        # We always fetch the time var and value var
        # config["variables"] maps API_NAME -> INTERNAL_ALIAS (time/value)
        # We need to find the API_NAME for 'time' and 'value'
        rev_var_map = {v: k for k, v in config["variables"].items()}
        time_var = rev_var_map["time"]
        val_var = rev_var_map["value"]

        # Build the 'get' parameter
        # Typically we request: time_var, val_var, and maybe others
        get_vars = [time_var, val_var]

        # Construct params
        params = config["params"].copy()
        params["get"] = ",".join(get_vars)
        if self.api_key:
            params["key"] = self.api_key

        # Time filtering
        # Census API supports 'time' filtering usually via 'from' and 'to' or specific predicates
        # But uniform support varies.
        # For simplicity, we fetch all (or recent chunks) and filter client-side,
        # unless the dataset supports strict range filtering easily.
        # International Trade supports 'time=from+yyyy-mm'.
        # EITS supports 'time=from+yyyy-mm'.
        # Let's try to add time filter if start_date provided.
        # API format is usually YYYY-MM

        if start_date:
            # Convert YYYY-MM-DD to YYYY-MM
            try:
                ts = pd.Timestamp(start_date)
                start_ym = ts.strftime("%Y-%m")
                # Census often uses 'time=from+2020-01' syntax but through requests params it's tricky
                # A common pattern is time="from 2020-01"
                # For safety in this MVP, we might fetch all if volume isn't huge (monthly series are small).
                # But let's try to be efficient.
                # Actually, simply passing "time": f"from {start_ym}" works for many Census endpoints.
                if not config.get("is_eits"):
                    params["time"] = f"from {start_ym}"
            except Exception:
                pass  # Fallback to fetching all

        try:
            url = f"{self.BASE_URL}{dataset}"
            logger.info(f"Fetching Census series {series_id} from {url}")

            response = requests.get(url, params=params, timeout=30)

            # Handle 204 No Content (valid request but no data)
            if response.status_code == 204:
                logger.info(f"No data found for Census series {series_id} (Status 204)")
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                # If 200 OK but empty body, or invalid JSON
                logger.error(
                    f"Invalid JSON response for {series_id} (Status {response.status_code}): {response.text[:100]}"
                )
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            if not data or len(data) < 2:
                # Expect header row + data rows
                logger.warning(f"No data found for Census series {series_id}")
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            # First row is headers
            headers = data[0]
            rows = data[1:]

            # Map headers to indices
            try:
                time_idx = headers.index(time_var)
                val_idx = headers.index(val_var)
            except ValueError:
                logger.error(f"Expected variables not found in headers: {headers}")
                raise ValueError("API response missing expected columns")

            # Parse
            parsed_data = []
            for row in rows:
                date_str = row[time_idx]
                val_str = row[val_idx]

                # Census sometimes returns "0" or "-" for missing
                if not val_str or val_str in ["-", "0", "(X)", "(NA)", "(S)"]:
                    continue

                parsed_data.append(
                    {
                        "observation_date": date_str,
                        "value": val_str,
                        "series_id": series_id,
                    }
                )

            df = pd.DataFrame(parsed_data)

            # Census dates are usually YYYY-MM
            df["observation_date"] = pd.to_datetime(
                df["observation_date"], format=config["time_format"]
            )
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

            # Sort
            df = df.sort_values("observation_date").reset_index(drop=True)

            # Final date filtering
            if start_date:
                df = df[df["observation_date"] >= pd.Timestamp(start_date)]
            if end_date:
                df = df[df["observation_date"] <= pd.Timestamp(end_date)]

            # Clean
            df = df.dropna(subset=["value"])

            logger.info(f"Fetched {len(df)} observations for Census series {series_id}")
            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching Census series {series_id}: {e}")
            # If 401/403 (Invalid Key), we might want to stop retrying?
            # Tenacity handles retries, but we let it raise to caller eventually.
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing Census response for {series_id}: {e}")
            raise
