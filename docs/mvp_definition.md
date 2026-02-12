# MVP Definition

> **Clear success criteria for the minimum viable product.**

---

## Goal

Build a working data pipeline that fetches the "Big Four" macroeconomic indicators from the FRED API and stores them in MotherDuck with proper upsert logic to handle data revisions.

---

## Success Criteria

### Must Work

The MVP is considered complete when all of these work reliably:

- [ ] **Database Connection**: Connect to MotherDuck from CLI using token authentication
- [ ] **Schema Initialization**: Create `fred_macro` database and tables if they don't exist
- [ ] **Data Fetching**: Successfully fetch data for all four core indicators from FRED API
  - FEDFUNDS (Federal Funds Rate)
  - UNRATE (Unemployment Rate)
  - CPIAUCSL (Consumer Price Index)
  - GDPC1 (Real GDP)
- [ ] **Upsert Logic**: Insert new data and update existing records without creating duplicates
- [ ] **Backfill Mode**: Fetch 10 years of historical data for all series
- [ ] **Incremental Mode**: Fetch only recent data (last 60 days) for updates
- [ ] **Ingestion Logging**: Record every ingestion run with timestamp, series, and row counts
- [ ] **Error Handling**: Gracefully handle API failures and rate limits

---

## Data Validation

After successful ingestion, the database should contain approximately these row counts for 10 years of data:

| Series ID | Expected Rows | Frequency | First Date | Latest Date |
|-----------|---------------|-----------|------------|-------------|
| FEDFUNDS | ~120 | Monthly | 2016-02 | 2026-02 |
| UNRATE | ~120 | Monthly | 2016-01 | 2026-01 |
| CPIAUCSL | ~120 | Monthly | 2016-01 | 2026-01 |
| GDPC1 | ~40 | Quarterly | 2016-Q1 | 2025-Q4 |

**Total Expected**: ~400 observations

### Validation Queries

```sql
-- Count observations by series
SELECT series_id, COUNT(*) as row_count
FROM observations
GROUP BY series_id
ORDER BY series_id;

-- Check date range by series
SELECT
    series_id,
    MIN(observation_date) as first_date,
    MAX(observation_date) as last_date,
    COUNT(*) as row_count
FROM observations
GROUP BY series_id;

-- Verify no duplicates
SELECT series_id, observation_date, COUNT(*) as duplicate_count
FROM observations
GROUP BY series_id, observation_date
HAVING COUNT(*) > 1;
```

---

## Acceptance Tests

### Test 1: Fresh Database (Backfill)

**Setup**: Empty MotherDuck database

**Steps**:
1. Run schema initialization
2. Run backfill mode for Big Four indicators
3. Query database for row counts

**Expected Result**: ~400 total observations, no duplicates

---

### Test 2: Re-Run Test (Idempotency)

**Setup**: Database already populated from Test 1

**Steps**:
1. Re-run backfill mode for same indicators
2. Query database for row counts

**Expected Result**: Same row counts as Test 1, no duplicates created

---

### Test 3: Incremental Update

**Setup**: Database populated with historical data

**Steps**:
1. Run incremental mode (last 60 days)
2. Verify only recent data is fetched
3. Check ingestion logs

**Expected Result**:
- Only ~2 new monthly observations per series (or 0 if no new releases)
- ~1 quarterly observation for GDPC1 (or 0 if no new release)
- Ingestion log shows reduced API calls

---

### Test 4: Data Revision Handling

**Setup**: Database with existing GDP value

**Steps**:
1. Manually update a GDPC1 value in database
2. Re-run incremental mode
3. Verify the value gets updated (upserted)

**Expected Result**: Modified value is overwritten with latest FRED data

---

## Out of Scope for MVP

These features are explicitly **NOT** required for MVP and will be added later:

- ❌ Tier 2 and Tier 3 indicator expansion
- ❌ Data quality checks and validation rules
- ❌ Query views for common analysis patterns
- ❌ Automated scheduling (cron, Prefect flows)
- ❌ Web dashboard or UI
- ❌ Alert notifications for indicator changes
- ❌ Historical vintages tracking (point-in-time data)
- ❌ Data export to other formats (CSV, Excel)
- ❌ Multi-user access control
- ❌ Performance optimization for large queries

---

## Technical Requirements

### Environment Variables

```bash
MOTHERDUCK_TOKEN="your_motherduck_token"
FRED_API_KEY="your_fred_api_key"
```

### Dependencies

- Python 3.10+
- duckdb >= 0.10.0
- fredapi
- pyyaml
- python-dotenv

### Commands

```bash
# Schema setup
uv run python -m src.fred_macro.setup

# Backfill (10 years)
uv run python -m src.fred_macro.ingest --mode backfill

# Incremental (60 days)
uv run python -m src.fred_macro.ingest --mode incremental

# Validate data
uv run python -m src.fred_macro.validate
```

---

## Definition of Done

The MVP is **DONE** when:

1. ✅ All "Must Work" criteria are met
2. ✅ All four acceptance tests pass
3. ✅ Data validation queries show expected row counts
4. ✅ No duplicate observations exist in database
5. ✅ Ingestion logs are created for every run
6. ✅ Documentation is complete and accurate
7. ✅ Code is tested with unit tests for core functions
8. ✅ README has working quick start instructions

---

## Measuring Success

### Quantitative Metrics

- **API Success Rate**: ≥95% of API requests succeed
- **Data Completeness**: ≥95% of expected observations present
- **Duplicate Rate**: 0% (no duplicates allowed)
- **Backfill Time**: <2 minutes for Big Four indicators
- **Incremental Time**: <30 seconds for Big Four indicators

### Qualitative Goals

- **Usability**: A developer can run backfill with a single command
- **Reliability**: Re-running ingestion is safe (idempotent)
- **Extensibility**: Adding new series requires only config changes

---

## Timeline

**Estimated Duration**: 2-3 weeks

**Phase Breakdown**:
1. **Week 1**: Foundation (database, schema, FRED client)
2. **Week 2**: Core pipeline (ingestion, upsert, logging)
3. **Week 3**: Testing, validation, documentation

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FRED API rate limits hit | Medium | Medium | Implement exponential backoff and request throttling |
| MotherDuck free tier limits | Low | High | Monitor storage usage; optimize schema if needed |
| Data revisions more complex than expected | Medium | Medium | Start with simple upsert; refine if issues found |
| Missing observations in FRED | Low | Low | Log warnings; don't fail entire run |

---

## Post-MVP Priorities

After MVP completion, the next priorities are:

1. **Tier 2 Indicators**: Expand to 20-30 additional series
2. **Query Views**: Create common analysis views (YoY change, trend analysis)
3. **Data Quality Checks**: Add validation rules and anomaly detection
4. **Scheduling**: Set up automated daily/weekly ingestion

See [`docs/implementation_schedule.md`](implementation_schedule.md) for full roadmap.

---

**Last Updated**: 2026-02-12
**Status**: Draft — MVP not yet started
