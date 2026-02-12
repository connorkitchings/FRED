# Data Dictionary

> **Comprehensive reference for all data elements, database schema, and indicator catalog.**

---

## Table of Contents

- [Database Schema](#database-schema)
  - [series_catalog](#series_catalog)
  - [observations](#observations)
  - [ingestion_log](#ingestion_log)
- [Indicator Categories](#indicator-categories)
- [Tier 1 Indicators (Core)](#tier-1-indicators-core)
- [Tier 2 Indicators (Extended)](#tier-2-indicators-extended)
- [Tier 3 Indicators (Deep Dive)](#tier-3-indicators-deep-dive)

---

## Database Schema

### series_catalog

**Purpose**: Metadata about each time series tracked in the system.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `series_id` | VARCHAR | NOT NULL | FRED series identifier (e.g., 'UNRATE'). Primary key. |
| `title` | VARCHAR | NOT NULL | Human-readable indicator name |
| `category` | VARCHAR | NOT NULL | Indicator category (see categories below) |
| `frequency` | VARCHAR | NOT NULL | Data frequency: 'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly), 'A' (annual) |
| `units` | VARCHAR | NOT NULL | Measurement units (e.g., 'Percent', 'Index', 'Billions of Dollars') |
| `seasonal_adjustment` | VARCHAR | NULL | 'SA' (seasonally adjusted), 'NSA' (not seasonally adjusted), NULL |
| `tier` | INTEGER | NOT NULL | Indicator tier: 1 (core), 2 (extended), 3 (deep dive) |
| `source` | VARCHAR | NULL | Original data source (e.g., 'Bureau of Labor Statistics') |
| `notes` | TEXT | NULL | Additional context or interpretation guidance |
| `created_at` | TIMESTAMP | NOT NULL | When series was added to catalog |

**Indexes**:
- Primary key on `series_id`
- Index on `tier` for filtering
- Index on `category` for grouping

**Example Row**:
```sql
INSERT INTO series_catalog VALUES (
    'UNRATE',
    'Unemployment Rate',
    'labor_market',
    'M',
    'Percent',
    'SA',
    1,
    'Bureau of Labor Statistics',
    'U-3 unemployment rate, most widely cited measure',
    '2026-02-12 10:00:00'
);
```

---

### observations

**Purpose**: Time series data points for all tracked indicators.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `series_id` | VARCHAR | NOT NULL | Foreign key to series_catalog.series_id |
| `observation_date` | DATE | NOT NULL | Date of the observation |
| `value` | DOUBLE | NULL | Numeric value (NULL for missing data) |
| `load_timestamp` | TIMESTAMP | NOT NULL | When this observation was last loaded/updated |

**Composite Primary Key**: (`series_id`, `observation_date`)

**Indexes**:
- Composite primary key on (`series_id`, `observation_date`)
- Foreign key to `series_catalog(series_id)`

**Example Rows**:
```sql
INSERT INTO observations VALUES
    ('UNRATE', '2026-01-01', 3.7, '2026-02-12 14:23:00'),
    ('UNRATE', '2025-12-01', 3.8, '2026-02-12 14:23:00'),
    ('GDPC1', '2025-Q4', 22500.5, '2026-02-12 14:23:05');
```

> **Learning Note**: The composite primary key ensures no duplicate observations for the same series and date. This is critical for our upsert strategy.

---

### ingestion_log

**Purpose**: Audit trail of all ingestion runs for observability and debugging.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `run_id` | VARCHAR | NOT NULL | Unique run identifier (UUID). Primary key. |
| `run_timestamp` | TIMESTAMP | NOT NULL | When ingestion started |
| `mode` | VARCHAR | NOT NULL | 'backfill' or 'incremental' |
| `series_ingested` | JSON | NOT NULL | Array of series_id values processed |
| `total_rows_fetched` | INTEGER | NOT NULL | Total observations retrieved from FRED |
| `total_rows_inserted` | INTEGER | NOT NULL | New observations added to database |
| `total_rows_updated` | INTEGER | NOT NULL | Existing observations updated (revisions) |
| `duration_seconds` | DOUBLE | NOT NULL | Total runtime in seconds |
| `status` | VARCHAR | NOT NULL | 'success', 'partial', 'failed' |
| `error_message` | TEXT | NULL | Error details if status != 'success' |

**Indexes**:
- Primary key on `run_id`
- Index on `run_timestamp` for time-based queries

**Example Row**:
```sql
INSERT INTO ingestion_log VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '2026-02-12 14:23:00',
    'incremental',
    '["FEDFUNDS", "UNRATE", "CPIAUCSL", "GDPC1"]',
    8,
    2,
    6,
    45.2,
    'success',
    NULL
);
```

---

## Indicator Categories

Indicators are organized into thematic categories for easier navigation and understanding.

| Category | Description | Example Series |
|----------|-------------|----------------|
| `output_income` | Measures of economic output and income | GDP, GDI, GNP |
| `labor_market` | Employment, unemployment, wages | UNRATE, PAYEMS, AHETPI |
| `prices_inflation` | Price levels and inflation measures | CPI, PPI, PCE |
| `financial_markets` | Interest rates, yields, asset prices | FEDFUNDS, DGS10, SP500 |
| `housing` | Housing market indicators | HOUST, PERMIT, CSUSHPISA |
| `consumption_retail` | Consumer spending and retail sales | RSXFS, PCE, PCEC96 |
| `money_credit` | Money supply and credit measures | M2SL, TOTCI, CONSUMER |
| `trade_international` | Trade balance, exports, imports | NETEXP, EXPGS, IMPGS |
| `manufacturing` | Industrial production, capacity | INDPRO, TCU, CAPUTLG2211A1S |
| `confidence_sentiment` | Consumer and business confidence | UMCSENT, BSCICP02USM665S |

---

## Tier 1 Indicators (Core)

**Purpose**: The "Big Four" essential macroeconomic indicators for MVP.

| Series ID | Title | Frequency | Category | Units | Seasonal Adj | Source |
|-----------|-------|-----------|----------|-------|--------------|--------|
| **FEDFUNDS** | Federal Funds Effective Rate | Monthly | financial_markets | Percent | NSA | Federal Reserve |
| **UNRATE** | Unemployment Rate | Monthly | labor_market | Percent | SA | Bureau of Labor Statistics |
| **CPIAUCSL** | Consumer Price Index for All Urban Consumers: All Items | Monthly | prices_inflation | Index (1982-84=100) | SA | Bureau of Labor Statistics |
| **GDPC1** | Real Gross Domestic Product | Quarterly | output_income | Billions of Chained 2017 Dollars | SA | Bureau of Economic Analysis |

### FEDFUNDS — Federal Funds Rate

**Description**: The interest rate at which depository institutions lend reserve balances to other depository institutions overnight. The primary tool of U.S. monetary policy.

**Interpretation**:
- **Higher rates**: Fed is tightening to control inflation
- **Lower rates**: Fed is easing to stimulate economy
- **Target range**: Set by Federal Open Market Committee (FOMC)

**Typical Range**: 0% to 6% (historically)

**Release**: Monthly average, published ~1 week after month end

---

### UNRATE — Unemployment Rate

**Description**: The percentage of the labor force that is unemployed and actively seeking employment (U-3 measure).

**Interpretation**:
- **Rising**: Economic weakness, labor market deterioration
- **Falling**: Economic strength, job growth
- **Natural rate**: ~4-5% (NAIRU concept)

**Typical Range**: 3% to 10% (normal conditions)

**Release**: Monthly, first Friday after month end (~8:30 AM ET)

> **Learning Note**: This is the U-3 unemployment rate, the most commonly cited measure. Other measures (U-1 through U-6) provide alternative views of labor underutilization.

---

### CPIAUCSL — Consumer Price Index

**Description**: Measures the average change in prices paid by urban consumers for a basket of goods and services. Primary inflation gauge.

**Interpretation**:
- **YoY % change**: Inflation rate (e.g., 3.2% = prices up 3.2% from a year ago)
- **Fed target**: 2% annual inflation
- **High inflation**: Erosion of purchasing power

**Typical Range**: -2% to +10% (YoY change)

**Release**: Monthly, ~mid-month for prior month (~8:30 AM ET)

---

### GDPC1 — Real GDP

**Description**: The total market value of all finished goods and services produced in the U.S., adjusted for inflation (real dollars).

**Interpretation**:
- **Positive growth**: Economic expansion
- **Negative growth**: Economic contraction (recession if 2+ consecutive quarters)
- **Strong growth**: >3% annualized
- **Weak growth**: <1% annualized

**Typical Range**: -5% to +5% (quarterly change, annualized)

**Release**: Quarterly, three estimates:
1. Advance (~1 month after quarter end)
2. Revised (~2 months after quarter end)
3. Final (~3 months after quarter end)

> **Learning Note**: GDP is subject to significant revisions. Our upsert strategy automatically captures the latest estimate.

---

## Tier 2 Indicators (Extended)

**Purpose**: Additional indicators for broader economic coverage (Post-MVP).

**Status**: Placeholder — To be populated when Tier 2 implementation begins.

### Labor Market (Extended)

| Series ID | Title | Frequency | Description |
|-----------|-------|-----------|-------------|
| PAYEMS | All Employees: Total Nonfarm | Monthly | Total nonfarm payroll employment (jobs report) |
| AHETPI | Average Hourly Earnings | Monthly | Wage growth indicator |
| CIVPART | Labor Force Participation Rate | Monthly | % of population in labor force |
| U6RATE | U-6 Unemployment Rate | Monthly | Broader unemployment measure (includes underemployed) |

### Housing

| Series ID | Title | Frequency | Description |
|-----------|-------|-----------|-------------|
| HOUST | Housing Starts | Monthly | New residential construction starts |
| PERMIT | Building Permits | Monthly | New residential building permits |
| CSUSHPISA | Case-Shiller Home Price Index | Monthly | National home price index |

### Consumption & Retail

| Series ID | Title | Frequency | Description |
|-----------|-------|-----------|-------------|
| RSXFS | Retail Sales | Monthly | Total retail and food services sales |
| PCE | Personal Consumption Expenditures | Monthly | Consumer spending |
| UMCSENT | University of Michigan Consumer Sentiment | Monthly | Consumer confidence index |

### Financial Markets

| Series ID | Title | Frequency | Description |
|-----------|-------|-----------|-------------|
| DGS10 | 10-Year Treasury Yield | Daily | Benchmark interest rate |
| SP500 | S&P 500 Index | Daily | Stock market performance |
| DEXUSEU | USD/EUR Exchange Rate | Daily | Dollar strength |

### Manufacturing & Trade

| Series ID | Title | Frequency | Description |
|-----------|-------|-----------|-------------|
| INDPRO | Industrial Production Index | Monthly | Manufacturing output |
| TCU | Total Capacity Utilization | Monthly | Factory capacity usage |
| NETEXP | Net Exports | Quarterly | Trade balance |

**Estimated Total**: 25-30 series
**Estimated Observations**: ~3,000-4,000 for 10 years

---

## Tier 3 Indicators (Deep Dive)

**Purpose**: Specialized sector-specific indicators for detailed analysis (Future).

**Status**: Placeholder — To be defined based on future research needs.

### Potential Categories

- **Sector-Specific Labor**: Construction, Manufacturing, Service sector employment
- **Detailed Inflation**: Core CPI, PPI by industry, PCE components
- **Credit Markets**: Corporate bond spreads, mortgage rates, consumer credit
- **International**: Country-specific trade, foreign reserves, commodity prices
- **Regional**: State-level unemployment, regional GDP, metro area data

**Estimated Total**: 40-50 series
**Estimated Observations**: ~10,000-100,000 (many daily financial series)

---

## Data Source Notes

### FRED API Characteristics

- **Update Frequency**: Varies by series (see individual indicator documentation)
- **Revisions**: Common for GDP, employment, and some other series
- **Missing Data**: Some series have gaps (economic disruptions, data collection issues)
- **Vintage Data**: FRED tracks historical revisions (not implemented in MVP)

### Data Quality

- **Reliability**: FRED is the authoritative source for U.S. economic data
- **Timeliness**: Data typically available within hours of official release
- **Completeness**: Generally complete, but some series have known gaps

---

## Query Examples

### Count observations by series

```sql
SELECT series_id, COUNT(*) as row_count
FROM observations
GROUP BY series_id
ORDER BY row_count DESC;
```

### Latest value for each series

```sql
SELECT
    s.series_id,
    s.title,
    o.observation_date,
    o.value,
    s.units
FROM observations o
JOIN series_catalog s ON o.series_id = s.series_id
WHERE o.observation_date IN (
    SELECT MAX(observation_date)
    FROM observations o2
    WHERE o2.series_id = o.series_id
)
ORDER BY s.series_id;
```

### Year-over-year change

```sql
WITH current AS (
    SELECT series_id, observation_date, value
    FROM observations
    WHERE series_id = 'CPIAUCSL'
    AND observation_date >= CURRENT_DATE - INTERVAL '12 months'
),
prior AS (
    SELECT series_id, observation_date, value
    FROM observations
    WHERE series_id = 'CPIAUCSL'
    AND observation_date >= CURRENT_DATE - INTERVAL '24 months'
    AND observation_date < CURRENT_DATE - INTERVAL '12 months'
)
SELECT
    c.observation_date,
    c.value as current_value,
    p.value as prior_value,
    ((c.value - p.value) / p.value * 100) as yoy_change_pct
FROM current c
JOIN prior p ON c.observation_date = p.observation_date + INTERVAL '12 months'
ORDER BY c.observation_date;
```

---

## Configuration File Format

Series catalog is defined in `config/series_catalog.yaml`:

```yaml
series:
  - series_id: FEDFUNDS
    title: Federal Funds Effective Rate
    category: financial_markets
    frequency: M
    units: Percent
    seasonal_adjustment: NSA
    tier: 1
    source: Federal Reserve
    notes: "Primary monetary policy tool"

  - series_id: UNRATE
    title: Unemployment Rate
    category: labor_market
    frequency: M
    units: Percent
    seasonal_adjustment: SA
    tier: 1
    source: Bureau of Labor Statistics
    notes: "U-3 unemployment rate"

  # Additional series...
```

---

**Last Updated**: 2026-02-12
**Status**: Tier 1 complete, Tier 2/3 placeholders
