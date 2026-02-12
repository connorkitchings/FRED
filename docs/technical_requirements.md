# Technical Requirements

> **Detailed technical specifications for the FRED-Macro-Dashboard system.**

---

## System Requirements

### Software Prerequisites

- **Python**: 3.10 or higher
  - Required for modern type hints and pattern matching
  - Tested on: Python 3.10, 3.11, 3.12
- **Package Manager**: uv (0.4.x or higher)
  - Fast Python package management and dependency resolution
  - Install: https://github.com/astral-sh/uv
- **Git**: For version control
- **Internet Connection**: Required for FRED API and MotherDuck

### External Services

- **MotherDuck Account**: Free tier sufficient
  - Storage limit: 10GB (expected usage: <100MB)
  - Compute limit: 10GB (more than adequate)
  - Sign up: https://motherduck.com/
- **FRED API Key**: Free registration required
  - Rate limit: 120 requests/minute
  - No daily limit
  - Register: https://fred.stlouisfed.org/docs/api/api_key.html

### Environment Variables

```bash
# Required
MOTHERDUCK_TOKEN="your_motherduck_token_here"
FRED_API_KEY="your_fred_api_key_here"

# Optional
LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

---

## Data Requirements

### Volume Estimates

#### MVP (Tier 1 - Big Four)

| Metric | Estimate | Notes |
|--------|----------|-------|
| Number of series | 4 | FEDFUNDS, UNRATE, CPIAUCSL, GDPC1 |
| Time period | 10 years | 2016-01-01 to present |
| Total observations | ~400 | 120 monthly + 120 monthly + 120 monthly + 40 quarterly |
| Storage size | ~20KB | Minimal storage footprint |

#### Tier 2 (Extended)

| Metric | Estimate | Notes |
|--------|----------|-------|
| Number of series | ~30 | Additional housing, consumption, manufacturing indicators |
| Total observations | ~3,500 | Mix of daily, monthly, quarterly |
| Storage size | ~200KB | Still very small |

#### Tier 3 (Deep Dive)

| Metric | Estimate | Notes |
|--------|----------|-------|
| Number of series | ~50 | Sector-specific, financial markets |
| Total observations | ~100,000 | Many daily financial series |
| Storage size | ~5MB | Daily data for 10 years |

#### Full Suite

| Metric | Estimate | Notes |
|--------|----------|-------|
| Number of series | 80-100 | All three tiers |
| Total observations | ~100,000 | Primarily daily financial data |
| Storage size | <10MB | Well within MotherDuck free tier |
| Growth rate | ~50 rows/day | Daily series updates |

---

### Data Freshness

#### Update Schedules (FRED Release Times)

| Indicator Type | Release Schedule | FRED Update Time | Notes |
|---------------|------------------|------------------|-------|
| Daily Financial | Daily | Next business day, ~10 AM ET | e.g., FEDFUNDS, Treasury rates |
| Weekly | Weekly | Thursday, ~4:30 PM ET | e.g., Initial claims |
| Monthly | Monthly | ~8:30 AM ET on release day | e.g., CPI, Employment |
| Quarterly | Quarterly | ~8:30 AM ET on release day | e.g., GDP (advance, revised, final) |

> **Learning Note**: FRED aggregates data from multiple sources. Update times reflect when FRED ingests the data, not the original source release.

#### Ingestion Strategy

- **Backfill Mode**: Run once to load 10 years of history
- **Incremental Mode**: Run daily to fetch last 60 days
  - 60-day window ensures we catch any late revisions
  - For quarterly data (GDP), this captures latest release plus revisions

---

### Data Quality Requirements

#### Handling Missing Values

- **Expected**: Some series have gaps (e.g., monthly series may skip a month)
- **Strategy**: Store as NULL/NaN in database
- **Validation**: Log warnings but don't fail ingestion

#### Handling Data Revisions

- **Expected**: GDP and other indicators frequently revised
- **Strategy**: Upsert (MERGE INTO) on composite key (series_id, observation_date)
- **Result**: Latest value always reflects most recent FRED data

> **Learning Note**: GDP has three releases for each quarter:
> - Advance (first estimate, ~1 month after quarter end)
> - Revised (second estimate, ~2 months after quarter end)
> - Final (third estimate, ~3 months after quarter end)
>
> Our upsert strategy handles all three automatically.

#### Data Validation Rules

For MVP, validation is minimal:
- Value is numeric (or NULL)
- Observation date is valid date
- Series ID matches catalog

Post-MVP validation (future):
- Range checks (e.g., unemployment rate 0-100%)
- Anomaly detection (sudden spikes)
- Freshness checks (alert if data is stale)

---

### Ingestion Logging

Every ingestion run must record:

| Field | Type | Description |
|-------|------|-------------|
| run_id | VARCHAR | Unique identifier (UUID) |
| run_timestamp | TIMESTAMP | When ingestion started |
| mode | VARCHAR | 'backfill' or 'incremental' |
| series_ingested | JSON | List of series_id values processed |
| total_rows_fetched | INTEGER | Total observations from FRED |
| total_rows_inserted | INTEGER | New observations added |
| total_rows_updated | INTEGER | Existing observations revised |
| duration_seconds | DOUBLE | Total runtime |
| status | VARCHAR | 'success', 'partial', 'failed' |
| error_message | TEXT | Error details if status != 'success' |

---

## API Requirements

### FRED API

#### Authentication

```python
from fredapi import Fred
fred = Fred(api_key=os.getenv('FRED_API_KEY'))
```

#### Rate Limits

- **Limit**: 120 requests per minute
- **Strategy**: Throttle to 1 request per second (conservative)
- **Handling**: Exponential backoff on 429 errors

#### Key Endpoints

| Endpoint | Purpose | Rate |
|----------|---------|------|
| `series/observations` | Get time series data | 1 call per series |
| `series` | Get series metadata | Optional (can use catalog) |

#### Error Handling

| Error Code | Meaning | Handling |
|------------|---------|----------|
| 400 | Bad request (invalid series_id) | Log warning, skip series |
| 429 | Rate limit exceeded | Exponential backoff, retry |
| 500 | Server error | Retry with backoff, fail after 3 attempts |

#### Request Parameters

```python
observations = fred.get_series(
    series_id='UNRATE',
    observation_start='2016-01-01',  # Backfill mode
    observation_end='2026-02-12'      # Today
)
```

---

### MotherDuck API

#### Authentication

```python
import duckdb
conn = duckdb.connect(f'md:?motherduck_token={MOTHERDUCK_TOKEN}')
```

#### Connection String Format

```
md:fred_macro?motherduck_token={token}
```

- `md:` — MotherDuck protocol
- `fred_macro` — Database name (created if not exists)
- `motherduck_token` — Authentication token

#### Query Language

- **Dialect**: DuckDB SQL
- **Notable features**:
  - Native MERGE INTO for upsert
  - Strong type system
  - JSON support for complex fields

#### Performance Considerations

- **Batch inserts**: Use prepared statements for bulk inserts
- **Indexes**: Not needed for small data volume (<100K rows)
- **Partitioning**: Not needed for MVP

---

## Functional Requirements

### FR-1: Database Connection

**Requirement**: System must connect to MotherDuck using token authentication.

**Acceptance**:
- Connection succeeds with valid token
- Connection fails gracefully with invalid token
- Connection retries on transient failures (up to 3 attempts)

---

### FR-2: Schema Initialization

**Requirement**: System must create database schema if it doesn't exist.

**Acceptance**:
- Tables created: `series_catalog`, `observations`, `ingestion_log`
- Idempotent: Re-running setup doesn't error if tables exist
- Correct data types and constraints applied

---

### FR-3: Series Configuration

**Requirement**: System must read series catalog from YAML configuration.

**Acceptance**:
- Config file at `config/series_catalog.yaml`
- Supports all required fields (series_id, title, category, frequency, tier)
- Validation: Missing required fields cause clear error

---

### FR-4: Data Fetching

**Requirement**: System must fetch time series data from FRED API.

**Acceptance**:
- Fetches observations for specified date range
- Handles API rate limits gracefully
- Returns data as pandas DataFrame with (date, value) columns

---

### FR-5: Data Upsert

**Requirement**: System must insert new observations and update existing ones.

**Acceptance**:
- No duplicate (series_id, observation_date) rows
- Existing observations are updated with latest value
- New observations are inserted
- Composite key enforced

---

### FR-6: Backfill Mode

**Requirement**: System must support loading 10 years of historical data.

**Acceptance**:
- Fetches data from 2016-01-01 to present
- Works for first-time setup (empty database)
- Completes in <5 minutes for Tier 1 indicators

---

### FR-7: Incremental Mode

**Requirement**: System must support incremental updates (last 60 days).

**Acceptance**:
- Fetches data from today - 60 days to present
- Efficiently updates only recent data
- Completes in <1 minute for Tier 1 indicators

---

### FR-8: Ingestion Logging

**Requirement**: System must log every ingestion run with details.

**Acceptance**:
- Unique run_id for each execution
- Captures row counts (fetched, inserted, updated)
- Records duration and status
- Logs stored in `ingestion_log` table

---

### FR-9: Error Handling

**Requirement**: System must handle errors gracefully without data corruption.

**Acceptance**:
- API errors don't crash the process
- Partial failures logged but don't prevent other series
- Database transactions rolled back on error
- Clear error messages for debugging

---

### FR-10: Idempotency

**Requirement**: Re-running ingestion must be safe (no duplicates or corruption).

**Acceptance**:
- Running backfill twice produces same result
- Running incremental multiple times produces same result
- Upsert correctly handles existing data

---

## Non-Functional Requirements

### NFR-1: Performance

**Requirement**: Ingestion must complete within acceptable time limits.

| Mode | Target Time | Max Time | Tier |
|------|-------------|----------|------|
| Backfill (Tier 1) | 1 minute | 5 minutes | 4 series |
| Incremental (Tier 1) | 15 seconds | 1 minute | 4 series |
| Backfill (Tier 2) | 5 minutes | 15 minutes | 30 series |
| Incremental (Tier 2) | 30 seconds | 2 minutes | 30 series |

---

### NFR-2: Reliability

**Requirement**: System must be robust to transient failures.

- **API Failures**: Retry with exponential backoff (up to 3 attempts)
- **Network Issues**: Timeout after 30 seconds, retry
- **Database Errors**: Log error, continue with other series

**Target**: 99% success rate for ingestion runs

---

### NFR-3: Observability

**Requirement**: System behavior must be transparent and debuggable.

- **Logging**: All operations logged at appropriate level (DEBUG, INFO, WARNING, ERROR)
- **Metrics**: Row counts, API call counts, duration tracked
- **Audit Trail**: Every ingestion run recorded in database

---

### NFR-4: Idempotency

**Requirement**: Re-running operations must be safe.

- **Database**: Upsert logic prevents duplicates
- **API**: Fetching same date range multiple times is safe
- **Logs**: Multiple runs create separate log entries (don't overwrite)

**Validation**: Run ingestion twice, verify row counts don't double

---

### NFR-5: Extensibility

**Requirement**: Adding new series must not require code changes.

- **Configuration-Driven**: All series defined in YAML
- **Dynamic Loading**: Ingestion reads config at runtime
- **Validation**: Config schema validation on startup

**Target**: Add new series by editing config file only

---

### NFR-6: Maintainability

**Requirement**: Code must be understandable and modifiable.

- **Documentation**: README, docstrings, inline comments (where needed)
- **Testing**: Unit tests for core functions
- **Standards**: Follow PEP 8, use type hints
- **Structure**: Clear separation of concerns (API client, database, config)

---

### NFR-7: Security

**Requirement**: Sensitive credentials must be protected.

- **Environment Variables**: Tokens and API keys in env vars, never hardcoded
- **Git**: `.gitignore` excludes `.env` files
- **Logging**: Don't log tokens or API keys

---

## Testing Requirements

### Unit Tests

**Coverage Target**: ≥80% for core modules

- `test_config.py` — Configuration loading and validation
- `test_fred_client.py` — FRED API client (mocked API)
- `test_database.py` — Database connection and queries (mocked DB)
- `test_ingestion.py` — Ingestion logic (mocked API and DB)

### Integration Tests

**Requirements**:
- Test with real MotherDuck connection (test database)
- Test with real FRED API (use single series to minimize calls)
- Validate end-to-end flow

### Manual Acceptance Tests

See [`docs/mvp_definition.md`](mvp_definition.md) for acceptance test scenarios.

---

## Deployment Requirements

### Environment Setup

```bash
# Clone repository
git clone https://github.com/connorkitchings/FRED.git
cd FRED

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your tokens

# Initialize database
uv run python -m src.fred_macro.setup
```

### Running Ingestion

```bash
# Backfill (first run)
uv run python -m src.fred_macro.ingest --mode backfill

# Incremental (daily updates)
uv run python -m src.fred_macro.ingest --mode incremental
```

### Scheduling (Post-MVP)

Future: Use cron or Prefect for automated scheduling

```bash
# Example cron (daily at 2 PM ET, after most releases)
0 14 * * * cd /path/to/FRED && uv run python -m src.fred_macro.ingest --mode incremental
```

---

## Dependencies

### Python Packages

See `pyproject.toml` for full dependency list.

**Core**:
- `duckdb >= 0.10.0` — Database engine
- `fredapi` — FRED API client
- `pyyaml` — Config file parsing
- `pandas` — Data manipulation
- `python-dotenv` — Environment variable loading

**Development**:
- `ruff` — Linting and formatting
- `pytest` — Testing framework
- `pytest-cov` — Code coverage
- `mypy` — Type checking

---

## Constraints

### Technical Constraints

- **Python Version**: Must be 3.10+ (no 3.9 support)
- **Database**: Must use DuckDB/MotherDuck (no Postgres, MySQL, etc.)
- **API**: Must use FRED (no alternative data sources)

### Resource Constraints

- **MotherDuck**: Free tier only (10GB storage, 10GB compute)
- **FRED API**: Free tier only (120 req/min)
- **Time**: MVP must complete in 2-3 weeks

### Business Constraints

- **Personal Use**: No multi-user support required
- **No SLA**: Best-effort reliability (not mission-critical)

---

**Last Updated**: 2026-02-12
**Status**: Specification Complete — Ready for Implementation
