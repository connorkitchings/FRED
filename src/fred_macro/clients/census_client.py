"""Client for U.S. Census Bureau API."""

import os
import time
from typing import Any, Optional

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
            "variables": {
                "MONTH": "time",
                "ALL_VAL_MO": "value",
            },
            "params": {
                "COMM_LVL": "HS2",
                "DISTRICT": "TOTAL",
                "CTY_CODE": "2010",
            },
            "time_format": "%Y-%m",
            "is_eits": False,
        },
        "CENSUS_IMP_MEXICO": {
            "dataset": "intltrade/imports/hs",
            "variables": {
                "MONTH": "time",
                "GEN_VAL_MO": "value",
            },
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
        },
    }

    _MISSING_VALUE_TOKENS = {"-", "(X)", "(NA)", "(S)", ""}

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Census client.

        Args:
            api_key: Census API key. If not provided, looks for CENSUS_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("CENSUS_API_KEY")
        if not self.api_key:
            logger.warning(
                "Census API key not found. Operations may fail or be severely "
                "rate limited."
            )

        self._last_request_time = 0.0
        # Conservative rate limit: 0.5s delay
        self._rate_limit_delay = 0.5
        self._eits_time_slot_cache: dict[tuple[str, str, str, str], str] = {}
        logger.info("Census client initialized")

    def _enforce_rate_limit(self):
        """Sleep if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _normalize_month_start(self, date_value: Optional[str]) -> Optional[str]:
        if not date_value:
            return None
        try:
            return pd.Timestamp(date_value).strftime("%Y-%m")
        except Exception:
            return None

    def _build_url(self, dataset: str) -> str:
        return f"{self.BASE_URL}{dataset}"

    def _request_json(
        self, url: str, params: dict[str, Any]
    ) -> Optional[list[list[str]]]:
        """Perform a Census API request and return parsed JSON rows or None if empty."""
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 204:
            return None

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            logger.error(
                "Invalid JSON response from Census endpoint %s (Status %s)",
                url,
                response.status_code,
            )
            return None

        if not data or len(data) < 2:
            return None

        return data

    def _count_valid_rows(
        self,
        rows: list[list[str]],
        headers: list[str],
        time_slot_id: str,
        start_ym: Optional[str],
        end_ym: Optional[str],
    ) -> int:
        """Count rows with a usable value within requested date bounds for a slot."""
        try:
            slot_idx = headers.index("time_slot_id")
            date_idx = headers.index("time_slot_date")
            value_idx = headers.index("cell_value")
        except ValueError:
            return 0

        valid = 0
        for row in rows:
            if len(row) <= max(slot_idx, date_idx, value_idx):
                continue
            if row[slot_idx] != time_slot_id:
                continue

            date_key = row[date_idx][:7]
            if start_ym and date_key < start_ym:
                continue
            if end_ym and date_key > end_ym:
                continue

            value_str = str(row[value_idx]).strip()
            if value_str in self._MISSING_VALUE_TOKENS:
                continue

            numeric = pd.to_numeric([value_str], errors="coerce")[0]
            if pd.isna(numeric):
                continue
            valid += 1

        return valid

    def _resolve_eits_time_slot_id(
        self,
        config: dict[str, Any],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Optional[str]:
        """Resolve and cache EITS time_slot_id for a series configuration."""
        params = config["params"]
        cache_key = (
            str(config["dataset"]),
            str(params.get("category_code", "")),
            str(params.get("data_type_code", "")),
            str(params.get("seasonally_adj", "")),
        )
        cached = self._eits_time_slot_cache.get(cache_key)
        if cached:
            return cached

        start_ym = self._normalize_month_start(start_date)
        end_ym = self._normalize_month_start(end_date)

        discovery_params = {
            "get": "time_slot_id,time_slot_date,cell_value",
            **params,
        }
        # Use broad windows to get enough data for deterministic ranking.
        if start_ym:
            discovery_params["time"] = f"from {start_ym}"
        if self.api_key:
            discovery_params["key"] = self.api_key

        url = self._build_url(str(config["dataset"]))
        data = self._request_json(url, discovery_params)
        if not data:
            logger.warning("No EITS discovery data returned for %s", cache_key)
            return None

        headers = data[0]
        rows = data[1:]
        if "time_slot_id" not in headers:
            logger.warning(
                "EITS discovery missing time_slot_id column for %s", cache_key
            )
            return None

        slot_idx = headers.index("time_slot_id")
        unique_slots = sorted({row[slot_idx] for row in rows if len(row) > slot_idx})
        if not unique_slots:
            logger.warning("No EITS time_slot_id values discovered for %s", cache_key)
            return None

        ranked_slots = []
        for slot in unique_slots:
            valid_rows = self._count_valid_rows(rows, headers, slot, start_ym, end_ym)
            ranked_slots.append((valid_rows, slot))

        ranked_slots.sort(key=lambda item: (-item[0], item[1]))
        best_count, best_slot = ranked_slots[0]
        if best_count == 0:
            logger.warning(
                "EITS discovery found slots but no valid rows for %s (candidate=%s)",
                cache_key,
                best_slot,
            )
            return None

        self._eits_time_slot_cache[cache_key] = best_slot
        return best_slot

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
        self._enforce_rate_limit()

        dataset = config["dataset"]
        rev_var_map = {v: k for k, v in config["variables"].items()}
        time_var = rev_var_map["time"]
        val_var = rev_var_map["value"]

        params = config["params"].copy()
        params["get"] = ",".join([time_var, val_var])
        if self.api_key:
            params["key"] = self.api_key

        if config.get("is_eits"):
            resolved_slot_id = self._resolve_eits_time_slot_id(
                config=config,
                start_date=start_date,
                end_date=end_date,
            )
            if not resolved_slot_id:
                logger.warning(
                    "Unable to resolve EITS time_slot_id for %s. Returning empty "
                    "result.",
                    series_id,
                )
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])
            params["time_slot_id"] = resolved_slot_id
            if start_date:
                start_ym = self._normalize_month_start(start_date)
                if start_ym:
                    params["time"] = f"from {start_ym}"
        elif start_date:
            start_ym = self._normalize_month_start(start_date)
            if start_ym:
                params["time"] = f"from {start_ym}"

        try:
            url = self._build_url(str(dataset))
            logger.info("Fetching Census series %s from %s", series_id, url)

            data = self._request_json(url, params)
            if not data:
                logger.warning("No data found for Census series %s", series_id)
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            headers = data[0]
            rows = data[1:]

            try:
                time_idx = headers.index(time_var)
                val_idx = headers.index(val_var)
            except ValueError:
                logger.error("Expected variables not found in headers: %s", headers)
                raise ValueError("API response missing expected columns")

            parsed_data = []
            for row in rows:
                if len(row) <= max(time_idx, val_idx):
                    continue
                date_str = row[time_idx]
                val_str = str(row[val_idx]).strip()

                if val_str in self._MISSING_VALUE_TOKENS:
                    continue

                parsed_data.append(
                    {
                        "observation_date": date_str,
                        "value": val_str,
                        "series_id": series_id,
                    }
                )

            if not parsed_data:
                return pd.DataFrame(columns=["observation_date", "value", "series_id"])

            df = pd.DataFrame(parsed_data)

            df["observation_date"] = pd.to_datetime(
                df["observation_date"], format=config["time_format"]
            )
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

            df = df.dropna(subset=["value"])
            df = df.sort_values("observation_date").reset_index(drop=True)

            if start_date:
                df = df[df["observation_date"] >= pd.Timestamp(start_date)]
            if end_date:
                df = df[df["observation_date"] <= pd.Timestamp(end_date)]

            logger.info(
                "Fetched %s observations for Census series %s", len(df), series_id
            )
            return df

        except requests.RequestException as e:
            logger.error("Error fetching Census series %s: %s", series_id, e)
            raise
        except (ValueError, KeyError) as e:
            logger.error("Error parsing Census response for %s: %s", series_id, e)
            raise
