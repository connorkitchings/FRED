# U.S. Treasury Fiscal Data API

## Overview

The FRED-Macro-Dashboard integrates with the [U.S. Treasury Fiscal Data API](https://fiscaldata.treasury.gov/api-documentation/) to provide direct access to Treasury market data including average interest rates and auction results.

**Key Features:**
- **No Authentication Required**: Public API with no API key needed
- **Direct Treasury Data**: Official data from the U.S. Department of the Treasury
- **Historical Coverage**: Access to historical average rates and auction data

## API Details

- **Base URL**: `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/`
- **Authentication**: None required
- **Rate Limiting**: Conservative 0.3s delay between requests (unofficial limit)
- **Data Format**: JSON
- **Documentation**: https://fiscaldata.treasury.gov/api-documentation/

## Available Series

The FRED-Macro-Dashboard currently supports 8 Treasury series across two categories:

### Average Interest Rates

Monthly data on average interest rates for outstanding Treasury securities:

| Series ID | Title | Description |
|-----------|-------|-------------|
| `TREAS_AVG_BILLS` | Average Interest Rate - Treasury Bills | Short-term government borrowing costs (< 1 year maturity) |
| `TREAS_AVG_NOTES` | Average Interest Rate - Treasury Notes | Medium-term government borrowing costs (2-10 year maturity) |
| `TREAS_AVG_BONDS` | Average Interest Rate - Treasury Bonds | Long-term government borrowing costs (> 10 year maturity) |
| `TREAS_AVG_TIPS` | Average Interest Rate - TIPS | Real yield on Treasury Inflation-Protected Securities |

**Data Source**: [Average Interest Rates API](https://fiscaldata.treasury.gov/datasets/average-interest-rates-treasury-securities/average-interest-rates-on-u-s-treasury-securities)

**Update Frequency**: Monthly (typically published within 5 business days of month-end)

**Historical Coverage**: January 2001 - Present

### Auction Data

Irregular data reflecting individual Treasury auction results:

| Series ID | Title | Description |
|-----------|-------|-------------|
| `TREAS_AUCTION_10Y` | 10-Year Note Auction High Rate | Market-clearing yield for benchmark 10-year Note auctions |
| `TREAS_AUCTION_2Y` | 2-Year Note Auction High Rate | Market-clearing yield for 2-year Note auctions |
| `TREAS_AUCTION_30Y` | 30-Year Bond Auction High Rate | Market-clearing yield for 30-year Bond auctions |
| `TREAS_BID_COVER_10Y` | 10-Year Note Bid-to-Cover Ratio | Demand indicator (higher = stronger demand) |

**Data Source**: [Securities Auctions API](https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions/)

**Update Frequency**: Irregular (as auctions occur, typically monthly for 10Y, quarterly for 30Y)

**Historical Coverage**: 2003 - Present (varies by security)

## Data Quality Considerations

### Expected Irregularities

1. **Auction Data Gaps**: Auction series have irregular frequencies and may show gaps:
   - 10-Year Notes: ~monthly auctions
   - 2-Year Notes: ~monthly auctions
   - 30-Year Bonds: ~quarterly auctions
   - These gaps are **not data quality issues** but reflect actual auction schedules

2. **Monthly Reporting Delays**: Average interest rate data typically publishes 3-5 business days after month-end

### Data Quality Rules

The dashboard applies the following validations to Treasury data:

- **Stale Data Warning**: If most recent observation is > 60 days old (for monthly series)
- **Missing Data**: Series with zero observations trigger warnings
- **Value Range**: Interest rates validated to be non-negative and < 100%

## Usage Examples

### CLI Ingestion

Ingest all Treasury series:

```bash
uv run python -m src.fred_macro.cli ingest --mode incremental
```

Seed Treasury series metadata:

```bash
uv run python -m src.fred_macro.cli seed-catalog
```

### Python API

```python
from src.fred_macro.clients import ClientFactory

# Get Treasury client
client = ClientFactory.get_client("TREASURY")

# Fetch 10-year auction data
df = client.get_series_data(
    series_id="TREAS_AUCTION_10Y",
    start_date="2020-01-01",
    end_date="2024-12-31"
)

# Result: DataFrame with columns [observation_date, value, series_id]
print(df.head())
```

## Implementation Details

### Client Architecture

The `TreasuryClient` implements the `DataSourceClient` protocol:

```python
from src.fred_macro.clients import TreasuryClient

client = TreasuryClient()  # No API key needed
```

**Key Methods:**
- `get_series_data(series_id, start_date=None, end_date=None)` → pd.DataFrame

### Series Mapping

The client maps internal series IDs to Treasury API endpoints:

- **Average Rates**: `v2/accounting/od/avg_interest_rates` (uses `record_date` field)
- **Auctions**: `v1/accounting/od/auctions_query` (uses `auction_date` field)

Filters are applied dynamically based on security type and date range.

### Rate Limiting

Conservative approach with 0.3s delay between requests to avoid rate limit issues:

```python
# Automatically enforced by client
client._rate_limit_delay = 0.3  # seconds
```

### Pagination

The client automatically handles paginated responses (max 10,000 records per page).

## Data Dictionary

See [Data Dictionary](../dictionary.md) for detailed field definitions and units.

## References

- [Treasury Fiscal Data Home](https://fiscaldata.treasury.gov/)
- [API Documentation](https://fiscaldata.treasury.gov/api-documentation/)
- [Data Dictionary](https://fiscaldata.treasury.gov/data-dictionary/)
- [Auction Schedule](https://www.treasurydirect.gov/auctions/upcoming/)

## Support

For API issues or data discrepancies, contact the Treasury Fiscal Service:

- **Email**: fiscalservice@fiscal.treasury.gov
- **API Status**: Check [API Documentation](https://fiscaldata.treasury.gov/api-documentation/) for outages

---

**Last Updated**: 2026-02-15
