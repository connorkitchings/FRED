# FRED API Data Source

> **Federal Reserve Economic Data (FRED) API documentation and usage guide.**

---

## Overview

**FRED** (Federal Reserve Economic Data) is a comprehensive database of economic time series maintained by the Federal Reserve Bank of St. Louis. It provides free access to over 800,000 economic data series from 100+ sources.

### Key Features

- **Coverage**: U.S. economic indicators plus international data
- **Sources**: Federal Reserve, Bureau of Labor Statistics, Bureau of Economic Analysis, Census Bureau, and many more
- **Historical Data**: Most series go back decades (some to the 1940s)
- **Free Access**: No cost for API usage
- **Reliability**: Authoritative source for U.S. economic data
- **Timeliness**: Data updated within hours of official releases

---

## Access & Authentication

### Getting Started

1. **Create Account**: Visit [https://fred.stlouisfed.org](https://fred.stlouisfed.org)
2. **Request API Key**: [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
3. **Save Key**: Store in environment variable `FRED_API_KEY`

### API Key Usage

```bash
# Set environment variable
export FRED_API_KEY="your_api_key_here"
```

```python
# Use in Python
import os
from fredapi import Fred

fred = Fred(api_key=os.getenv('FRED_API_KEY'))
```

> **Security Note**: Never hardcode API keys in source code. Always use environment variables.

---

## Rate Limits

### API Quotas

| Limit Type | Quota | Notes |
|------------|-------|-------|
| **Requests per minute** | 120 | Hard limit enforced by FRED |
| **Requests per day** | Unlimited | No daily cap |
| **Concurrent requests** | Not specified | Recommend sequential for simplicity |

### Recommended Strategy

For this project (50-100 series):
- **Throttling**: 1 request per second (conservative)
- **Backfill**: ~100 requests = 100 seconds (<2 minutes)
- **Incremental**: ~50 requests = 50 seconds (<1 minute)

### Handling Rate Limits

If you exceed the rate limit (HTTP 429), implement exponential backoff:

```python
import time
from requests.exceptions import HTTPError

def fetch_with_backoff(series_id, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            return fred.get_series(series_id)
        except HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** retries  # 1s, 2s, 4s
                time.sleep(wait_time)
                retries += 1
            else:
                raise
    raise Exception(f"Max retries exceeded for {series_id}")
```

---

## Key Endpoints

### 1. series/observations (Primary)

**Purpose**: Retrieve time series data points.

**URL**: `https://api.stlouisfed.org/fred/series/observations`

**Parameters**:
- `series_id` (required): FRED series identifier (e.g., 'UNRATE')
- `api_key` (required): Your API key
- `observation_start` (optional): Start date (YYYY-MM-DD)
- `observation_end` (optional): End date (YYYY-MM-DD)
- `file_type` (optional): 'json' (default) or 'xml'

**Example Request**:
```
GET https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key=YOUR_KEY&observation_start=2020-01-01
```

**Response Format**:
```json
{
  "realtime_start": "2026-02-12",
  "realtime_end": "2026-02-12",
  "observation_start": "2020-01-01",
  "observation_end": "9999-12-31",
  "units": "lin",
  "output_type": 1,
  "file_type": "json",
  "order_by": "observation_date",
  "sort_order": "asc",
  "count": 73,
  "offset": 0,
  "limit": 100000,
  "observations": [
    {
      "realtime_start": "2026-02-12",
      "realtime_end": "2026-02-12",
      "date": "2020-01-01",
      "value": "3.6"
    },
    {
      "realtime_start": "2026-02-12",
      "realtime_end": "2026-02-12",
      "date": "2020-02-01",
      "value": "3.5"
    }
    // ... more observations
  ]
}
```

---

### 2. series (Metadata)

**Purpose**: Retrieve metadata about a time series.

**URL**: `https://api.stlouisfed.org/fred/series`

**Parameters**:
- `series_id` (required): FRED series identifier
- `api_key` (required): Your API key

**Example Request**:
```
GET https://api.stlouisfed.org/fred/series?series_id=UNRATE&api_key=YOUR_KEY
```

**Response Format**:
```json
{
  "seriess": [
    {
      "id": "UNRATE",
      "realtime_start": "2026-02-12",
      "realtime_end": "2026-02-12",
      "title": "Unemployment Rate",
      "observation_start": "1948-01-01",
      "observation_end": "2026-01-01",
      "frequency": "Monthly",
      "frequency_short": "M",
      "units": "Percent",
      "units_short": "Percent",
      "seasonal_adjustment": "Seasonally Adjusted",
      "seasonal_adjustment_short": "SA",
      "last_updated": "2026-02-07 07:44:03-06",
      "popularity": 93,
      "notes": "The unemployment rate represents the number of unemployed..."
    }
  ]
}
```

> **Note**: For this project, we use a static series catalog (YAML config) instead of fetching metadata, reducing API calls.

---

## Using fredapi Library

### Installation

```bash
uv add fredapi
```

### Basic Usage

```python
from fredapi import Fred
import os

# Initialize client
fred = Fred(api_key=os.getenv('FRED_API_KEY'))

# Fetch series data
data = fred.get_series('UNRATE')
print(data)  # Returns pandas Series

# Fetch with date range
data = fred.get_series(
    'UNRATE',
    observation_start='2020-01-01',
    observation_end='2026-02-12'
)

# Get metadata
info = fred.get_series_info('UNRATE')
print(info['title'])  # "Unemployment Rate"
print(info['units'])  # "Percent"
```

### Batch Fetching

```python
series_list = ['FEDFUNDS', 'UNRATE', 'CPIAUCSL', 'GDPC1']

for series_id in series_list:
    print(f"Fetching {series_id}...")
    data = fred.get_series(series_id, observation_start='2016-01-01')
    print(f"  Rows: {len(data)}")
    time.sleep(1)  # Throttle to avoid rate limits
```

---

## Data Characteristics

### Update Frequency by Series Type

| Indicator Type | Release Schedule | Example Series |
|---------------|------------------|----------------|
| **Daily** | Every business day | FEDFUNDS, DGS10, DEXUSEU |
| **Weekly** | Every Thursday | ICSA (Initial Claims) |
| **Monthly** | 10-15 days after month end | UNRATE, CPIAUCSL, HOUST |
| **Quarterly** | 30-90 days after quarter end | GDPC1 (3 releases per quarter) |
| **Annual** | Varies | Less common in our catalog |

### Data Revisions

Many economic indicators are subject to revisions:

**GDP (GDPC1)**: Three releases per quarter
1. **Advance** (~30 days after quarter end): First estimate
2. **Revised** (~60 days): Incorporates more complete data
3. **Final** (~90 days): Most complete picture

**Employment (PAYEMS)**: Revised for prior two months with each release

**Other**: CPI, PCE, and many others occasionally revised

> **Learning Note**: Our upsert strategy (MERGE INTO) automatically handles revisions by updating existing observations with the latest value.

---

### Missing Data

Some series have missing values, represented as `"."` in the API response:

```json
{
  "date": "2020-03-01",
  "value": "."
}
```

**Handling Strategy**:
- Store as NULL in database
- Log warning but don't fail ingestion
- Document known gaps in series notes

---

### Special Cases

#### Non-Standard Frequencies

Some series have irregular frequencies:
- **NBER Recession Indicators**: Binary indicators (0 or 1) that change state
- **Quarterly series**: Dates shown as first day of quarter (e.g., 2025-10-01 for Q4)

#### Transformed Data

FRED offers data transformations (not used in this project):
- Percent change
- Percent change from year ago
- Compounded annual rate of change
- Natural log

We store **original (level) data** and perform transformations in queries.

---

## API Error Handling

### Common Error Codes

| Status Code | Meaning | Handling |
|------------|---------|----------|
| **400** | Bad Request (invalid series_id) | Log warning, skip series, continue |
| **401** | Unauthorized (invalid API key) | Fail immediately with clear error |
| **404** | Series not found | Log warning, skip series |
| **429** | Rate limit exceeded | Exponential backoff, retry |
| **500** | Server error | Retry with backoff, fail after 3 attempts |
| **503** | Service unavailable | Retry with backoff, fail after 3 attempts |

### Recommended Error Handling

```python
import time
import logging
from requests.exceptions import HTTPError, RequestException

def fetch_series_with_error_handling(series_id):
    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            data = fred.get_series(series_id, observation_start='2016-01-01')
            return data

        except HTTPError as e:
            if e.response.status_code == 400:
                logging.warning(f"Invalid series: {series_id}")
                return None
            elif e.response.status_code == 429:
                wait = retry_delay * (2 ** attempt)
                logging.warning(f"Rate limit hit, waiting {wait}s")
                time.sleep(wait)
            elif e.response.status_code in [500, 503]:
                wait = retry_delay * (2 ** attempt)
                logging.warning(f"Server error, retrying in {wait}s")
                time.sleep(wait)
            else:
                logging.error(f"HTTP error {e.response.status_code}: {series_id}")
                raise

        except RequestException as e:
            logging.error(f"Network error: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

    logging.error(f"Max retries exceeded for {series_id}")
    return None
```

---

## Performance Considerations

### Optimization Strategies

1. **Batch Processing**: Group series by frequency to minimize total API calls
2. **Incremental Updates**: Fetch only recent data (last 60 days) for updates
3. **Caching**: Store fetched data in database; don't re-fetch historical data
4. **Parallel Requests**: Use threading for independent series (respect rate limits)

### Typical Fetch Times

| Mode | Series Count | Expected Time | Notes |
|------|--------------|---------------|-------|
| Backfill (Tier 1) | 4 | ~10 seconds | 4 API calls at 1/sec |
| Backfill (Tier 2) | 30 | ~60 seconds | 30 API calls at 1/sec |
| Incremental (Tier 1) | 4 | ~10 seconds | Same as backfill for now |
| Incremental (Tier 2) | 30 | ~60 seconds | Future optimization: check freshness first |

---

## Example Workflows

### 1. Backfill Historical Data

```python
import pandas as pd
from fredapi import Fred
import time

fred = Fred(api_key=os.getenv('FRED_API_KEY'))
series_list = ['FEDFUNDS', 'UNRATE', 'CPIAUCSL', 'GDPC1']

start_date = '2016-01-01'
results = {}

for series_id in series_list:
    print(f"Fetching {series_id}...")
    data = fred.get_series(series_id, observation_start=start_date)
    results[series_id] = data
    print(f"  Retrieved {len(data)} observations")
    time.sleep(1)  # Rate limit throttle

# Convert to DataFrame
df = pd.DataFrame(results)
print(df.head())
```

---

### 2. Incremental Update (Last 60 Days)

```python
from datetime import datetime, timedelta

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

for series_id in series_list:
    print(f"Updating {series_id} from {start_date} to {end_date}...")
    data = fred.get_series(
        series_id,
        observation_start=start_date,
        observation_end=end_date
    )
    print(f"  Retrieved {len(data)} observations")
    time.sleep(1)
```

---

### 3. Check Data Freshness

```python
def check_freshness(series_id):
    """Check when a series was last updated."""
    info = fred.get_series_info(series_id)
    last_updated = info['last_updated']
    observation_end = info['observation_end']

    print(f"{series_id}:")
    print(f"  Last updated: {last_updated}")
    print(f"  Latest data: {observation_end}")
    return observation_end

for series_id in series_list:
    check_freshness(series_id)
    time.sleep(0.5)
```

---

## API Documentation Links

### Official Resources

- **FRED Website**: [https://fred.stlouisfed.org](https://fred.stlouisfed.org)
- **API Documentation**: [https://fred.stlouisfed.org/docs/api/fred/](https://fred.stlouisfed.org/docs/api/fred/)
- **API Key Request**: [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
- **fredapi Library**: [https://github.com/mortada/fredapi](https://github.com/mortada/fredapi)

### Useful Pages

- **Search FRED Series**: [https://fred.stlouisfed.org/search](https://fred.stlouisfed.org/search)
- **Release Calendars**: [https://fred.stlouisfed.org/releases/calendar](https://fred.stlouisfed.org/releases/calendar)
- **Tags**: [https://fred.stlouisfed.org/tags](https://fred.stlouisfed.org/tags)

---

## Troubleshooting

### Common Issues

**Problem**: `APIKeyNotFound` error

**Solution**: Set environment variable `FRED_API_KEY`

```bash
export FRED_API_KEY="your_key_here"
```

---

**Problem**: Rate limit exceeded (HTTP 429)

**Solution**: Add throttling between requests

```python
import time
time.sleep(1)  # Wait 1 second between requests
```

---

**Problem**: Series returns no data

**Possible causes**:
- Series ID is misspelled (check FRED website)
- Date range is outside series availability
- Series has been discontinued

**Solution**: Verify series exists and check date range

---

**Problem**: Data doesn't match FRED website

**Possible causes**:
- Data has been revised since last fetch
- Using transformed units (percent change vs. level)
- Vintage data mismatch

**Solution**: Re-run incremental update to fetch latest revisions

---

**Last Updated**: 2026-02-12
**API Version**: FRED API v2
