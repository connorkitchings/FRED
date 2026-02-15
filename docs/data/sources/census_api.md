# Census Bureau Data Integration

This document details the integration of U.S. Census Bureau data into the FRED Macro Dashboard.

## Overview

The `CensusClient` provides access to economic indicators from the Census Bureau API, specifically focusing on:
1.  **International Trade**: U.S. exports and imports of goods (total and by country).
2.  **Economic Indicators (EITS)**: Business inventories, shipments, and new orders.

## Configuration

### API Key
A Census Bureau API key is required.
- **Get a key**: [Request a Key](https://api.census.gov/data/key_signup.html)
- **Environment Variable**: `CENSUS_API_KEY`

### Rate Limits
- The client enforces a conservative rate limit of **0.5 seconds** between requests to ensure reliability.
- The Census API terms allow up to 500 requests per day without a key, but a key is strongly recommended for production use.

## Implemented Series

### International Trade (Monthly)
Data source: `intltrade/exports/hs`, `intltrade/imports/hs`

| ID | Title | Census Dataset | Params |
|----|-------|----------------|--------|
| `CENSUS_EXP_GOODS` | U.S. Exports of Goods | Exports | `COMM_LVL=HS2`, `DISTRICT=TOTAL` |
| `CENSUS_IMP_GOODS` | U.S. Imports of Goods | Imports | `COMM_LVL=HS2`, `DISTRICT=TOTAL` |
| `CENSUS_EXP_CHINA` | Exports to China | Exports | `CTY_CODE=5700` |
| `CENSUS_IMP_CHINA` | Imports from China | Imports | `CTY_CODE=5700` |
| `CENSUS_EXP_CANADA`| Exports to Canada | Exports | `CTY_CODE=1220` |
| `CENSUS_IMP_CANADA`| Imports from Canada | Imports | `CTY_CODE=1220` |
| `CENSUS_EXP_MEXICO`| Exports to Mexico | Exports | `CTY_CODE=2010` |
| `CENSUS_IMP_MEXICO`| Imports from Mexico | Imports | `CTY_CODE=2010` |

### Business Inventories & Orders (Monthly)
Data source: `eits/mwts` (Manufacturing and Trade Inventories and Sales)

| ID | Title | Category Code | Data Type | Seasonal Adj |
|----|-------|---------------|-----------|--------------|
| `CENSUS_INV_MFG` | Manufacturing Inventories | `MNSI` | `INV` | Yes |
| `CENSUS_INV_WHOLESALE`| Wholesale Inventories | `MWSI` | `INV` | Yes |
| `CENSUS_INV_RETAIL` | Retail Inventories | `MRSI` | `INV` | Yes |
| `CENSUS_INV_SALES_RATIO`| Total Business Inv/Sales Ratio | `MTIR` | `RATIO` | Yes |
| `CENSUS_INV_MFG_RATIO` | Mfg Inv/Shipments Ratio | `MNIR` | `RATIO` | Yes |
| `CENSUS_SHIP_MFG` | Manufacturing Shipments | `MNS` | `SM` | Yes |
| `CENSUS_ORDERS_MFG` | Manufacturing New Orders | `MNO` | `NO` | Yes |

## Usage Example

```python
from src.fred_macro.clients import ClientFactory

# Get client instance
client = ClientFactory.get_client("CENSUS")

# Fetch data
df = client.get_series_data("CENSUS_EXP_GOODS", start_date="2023-01-01")

print(df.head())
#   observation_date      value         series_id
# 0       2023-01-01  170425.0  CENSUS_EXP_GOODS
# 1       2023-02-01  168500.0  CENSUS_EXP_GOODS
```

## Implementation Details

### `CensusClient`
- **Location**: `src/fred_macro/clients/census_client.py`
- **Protocol**: Implements `DataSourceClient`.
- **Logic**:
    - Maps internal series IDs to API endpoints and parameters.
    - Handles pagination (though mostly not needed for time series).
    - Transforms API JSON response (list of lists) into a pandas DataFrame.
    - Standardizes date format to `YYYY-MM-DD`.
    - Handles missing values or suppression codes (e.g., `(X)`, `-`).

### Testing
- Unit tests cover initialization, series mapping, and data fetching (mocked).
- Run tests: `uv run pytest tests/test_census_client.py`

## Troubleshooting

- **Missing Data**: Ensure `start_date` is within available range. Census data availability varies by series.
- **Connection Errors**: Check internet connection and `CENSUS_API_KEY`.
- **Column Errors**: If "API response missing expected columns", valid variable names might have changed on the Census side. Check `SERIES_MAPPING`.
