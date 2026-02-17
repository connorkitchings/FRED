from datetime import datetime, timedelta

import pandas as pd

from src.fred_macro.clients import ClientFactory
from src.fred_macro.logging_config import get_logger
from src.fred_macro.services.catalog import SeriesConfig

logger = get_logger(__name__)


class DataFetcher:
    """
    Component responsible for fetching data from external APIs.
    """

    def __init__(self):
        self.clients = {}

    def _get_client(self, source: str):
        source = source.upper()
        if source not in self.clients:
            self.clients[source] = ClientFactory.get_client(source)
        return self.clients[source]

    def _determine_start_date(self, mode: str) -> str:
        today = datetime.now()
        if mode == "backfill":
            start_date = today - timedelta(days=365 * 10)
        else:
            start_date = today - timedelta(days=60)
        return start_date.strftime("%Y-%m-%d")

    def fetch_series(
        self, series: SeriesConfig, mode: str = "incremental"
    ) -> pd.DataFrame:
        """
        Fetch data for a single series.
        Returns empty DataFrame on failure/no data.
        """
        try:
            client = self._get_client(series.source)
            start_date = self._determine_start_date(mode)
            request_series_id = series.source_series_id or series.series_id

            df = client.get_series_data(request_series_id, start_date=start_date)

            if df.empty:
                logger.warning(
                    f"No data found for {series.series_id} ({series.source})"
                )
                return df

            # Keep storage keyed by internal catalog id while allowing
            # source-specific fetch ids.
            df["series_id"] = series.series_id

            logger.info(
                f"Fetched {len(df)} rows for {series.series_id} "
                f"(request={request_series_id}, source={series.source})"
            )
            return df

        except Exception as e:
            logger.error(f"Failed to fetch {series.series_id} ({series.source}): {e}")
            return pd.DataFrame()
