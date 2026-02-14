"""Base protocol for data source clients."""

from typing import Optional, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataSourceClient(Protocol):
    """
    Protocol defining the interface for all data source clients.

    All clients must implement get_series_data() and return a standardized
    DataFrame format: [observation_date, value, series_id]
    """

    def get_series_data(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch data for a specific series.

        Args:
            series_id: The series identifier (format varies by source)
            start_date: Optional 'YYYY-MM-DD' string for start date
            end_date: Optional 'YYYY-MM-DD' string for end date

        Returns:
            pd.DataFrame: DataFrame with columns:
                - observation_date (datetime): Date of the observation
                - value (float): The data value
                - series_id (str): The series identifier

        Raises:
            Exception: If the data fetch fails
        """
        ...
