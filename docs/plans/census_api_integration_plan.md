# Census Bureau API Integration Plan

## Context

**Problem**: The FRED-Macro-Dashboard currently lacks direct access to international trade and inventory data, which are critical leading indicators for economic cycles.

**Solution**: Integrate the U.S. Census Bureau API as a fourth data source, focusing on trade statistics and business inventories where Census is the primary/authoritative source.

**Outcome**: Expand coverage to ~103+ series (88 current + 15 Census) with direct trade and inventory data.

---

## Scope

### In Scope
- Create `CensusClient` implementing `DataSourceClient` protocol
- Register in `ClientFactory` with source key "CENSUS"
- Add 15 Census series to catalog (8 trade + 7 inventory)
- Unit tests following existing patterns
- API documentation
- API key configuration (required for Census API)

### Out of Scope
- Microdata/survey responses (ACS, CPS)
- Decennial census data
- Geographic detail below national level (for MVP)
- Non-timeseries datasets

---

## Implementation Plan

### Phase 1: Create CensusClient

**File**: `src/fred_macro/clients/census_client.py`

Key implementation details:
- **Base URL**: `https://api.census.gov/data/timeseries/`
- **Authentication**: API key required (env var `CENSUS_API_KEY`)
- **Rate Limiting**: 500 requests/day (documented limit), 0.5s delay
- **Series Mapping**: Internal mapping from series_id to dataset + variable codes

```python
SERIES_MAPPING = {
    # International Trade (Monthly)
    "CENSUS_EXP_GOODS": {
        "dataset": "intltrade/exports/hs",
        "variables": {"MONTH": "time", "GEN_VAL_MO": "value"},
        "filters": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL"}
    },
    "CENSUS_IMP_GOODS": {
        "dataset": "intltrade/imports/hs",
        "variables": {"MONTH": "time", "GEN_VAL_MO": "value"},
        "filters": {"COMM_LVL": "HS2", "DISTRICT": "TOTAL"}
    },
    # ... additional trade series

    # Business Inventories (Monthly)
    "CENSUS_INV_MFG": {
        "dataset": "eits/mwts",
        "variables": {"per": "time", "val": "value"},
        "filters": {"seasonally_adj": "yes", "category_code": "MTSI"}
    },
    # ... additional inventory series
}
```

### Phase 2: Update ClientFactory

**File**: `src/fred_macro/clients/__init__.py`

- Import `CensusClient`
- Add to registry: `"CENSUS": CensusClient`
- Update `__all__` exports

### Phase 3: Update CatalogService

**File**: `src/fred_macro/services/catalog.py`

- Add "CENSUS" to allowed sources in `validate_source`

### Phase 4: Add Census Series to Catalog

**File**: `config/series_catalog.yaml`

Add 15 series (Tier 2):

#### International Trade (8 series)

| Series ID | Title | Frequency |
|-----------|-------|-----------|
| `CENSUS_EXP_GOODS` | U.S. Exports of Goods | Monthly |
| `CENSUS_IMP_GOODS` | U.S. Imports of Goods | Monthly |
| `CENSUS_TRADE_BAL` | U.S. Trade Balance (Goods) | Monthly |
| `CENSUS_EXP_CHINA` | U.S. Exports to China | Monthly |
| `CENSUS_IMP_CHINA` | U.S. Imports from China | Monthly |
| `CENSUS_EXP_CANADA` | U.S. Exports to Canada | Monthly |
| `CENSUS_IMP_CANADA` | U.S. Imports from Canada | Monthly |
| `CENSUS_EXP_MEXICO` | U.S. Exports to Mexico | Monthly |

#### Business Inventories (7 series)

| Series ID | Title | Frequency |
|-----------|-------|-----------|
| `CENSUS_INV_MFG` | Manufacturing Inventories | Monthly |
| `CENSUS_INV_WHOLESALE` | Wholesale Trade Inventories | Monthly |
| `CENSUS_INV_RETAIL` | Retail Trade Inventories | Monthly |
| `CENSUS_INV_SALES_RATIO` | Total Business Inventory/Sales Ratio | Monthly |
| `CENSUS_INV_MFG_RATIO` | Manufacturing Inventory/Sales Ratio | Monthly |
| `CENSUS_SHIP_MFG` | Manufacturing Shipments | Monthly |
| `CENSUS_ORDERS_MFG` | Manufacturing New Orders | Monthly |

### Phase 5: Create Tests

**File**: `tests/test_census_client.py`

Test coverage:
- Initialization with API key (required)
- Initialization without API key (should fail gracefully)
- Series mapping validation
- get_series_data success (mocked)
- Date filtering
- Empty response handling
- API key error (401)
- Network error retry
- Rate limiting
- Complex filter building

**File**: `tests/test_clients_factory.py`

- Add `test_get_client_census`
- Add `test_census_implements_protocol`

### Phase 6: Configuration

**File**: `.env.example` or documentation

Add Census API key configuration:
```bash
# Census Bureau API Key (required)
# Register at: https://api.census.gov/data/key_signup.html
CENSUS_API_KEY=your_census_api_key_here
```

### Phase 7: Documentation

**File**: `docs/data/sources/census_api.md`

- API overview
- Authentication (API key required)
- Available series (trade + inventory)
- Data update schedule
- Usage examples
- API key registration process

---

## Files to Modify/Create

| File | Change |
|------|--------|
| `src/fred_macro/clients/census_client.py` | **CREATE** - New client |
| `src/fred_macro/clients/__init__.py` | Add import + registry entry |
| `src/fred_macro/services/catalog.py` | Add "CENSUS" to allowed sources |
| `config/series_catalog.yaml` | Add 15 Census series |
| `tests/test_census_client.py` | **CREATE** - Unit tests |
| `tests/test_clients_factory.py` | Add Census tests |
| `tests/test_series_catalog_config.py` | Add "CENSUS" to valid sources |
| `docs/data/sources/census_api.md` | **CREATE** - API docs |
| `docs/data/dictionary.md` | Add Census series descriptions |
| `.env.example` | Add CENSUS_API_KEY |

---

## Census API Details

### International Trade API

**Endpoint**: `https://api.census.gov/data/timeseries/intltrade/`

**Datasets**:
- `exports/hs` - Harmonized System exports by country
- `imports/hs` - Harmonized System imports by country

**Key Variables**:
- `MONTH` - YYYY-MM format
- `GEN_VAL_MO` - General value (monthly)
- `CTY_CODE` - Country code (ISO)
- `COMM_LVL` - Commodity level (HS2, HS4, etc.)

**Filters**:
- `COMM_LVL=HS2` - Top-level aggregation (all commodities)
- `DISTRICT=TOTAL` - All customs districts (national total)
- `CTY_CODE=5700` - China
- `CTY_CODE=1220` - Canada
- `CTY_CODE=2010` - Mexico

### Economic Indicators Time Series (EITS)

**Endpoint**: `https://api.census.gov/data/timeseries/eits/`

**Datasets**:
- `mwts` - Manufacturing and Trade: Inventories and Sales

**Key Variables**:
- `per` - Period (YYYY-MM)
- `val` - Value
- `seasonally_adj` - Seasonal adjustment flag
- `category_code` - Series identifier

**Series Codes**:
- `MTSI` - Total Business Inventories
- `MNSI` - Manufacturing Inventories
- `MWSI` - Wholesale Trade Inventories
- `MRSI` - Retail Trade Inventories
- `MTIR` - Total Business Inventory/Sales Ratio
- `MNIR` - Manufacturing Inventory/Sales Ratio

---

## Reusable Patterns

Follow existing patterns from:
- `src/fred_macro/clients/treasury_client.py` - Rate limiting, retry logic, DataFrame transformation
- `tests/test_treasury_client.py` - Test structure with mocked responses
- `tests/test_clients_factory.py` - Factory integration tests

---

## API Key Registration

Census API requires a free API key:

**Registration URL**: https://api.census.gov/data/key_signup.html

**Process**:
1. Visit registration page
2. Provide name, email, organization
3. Receive API key via email (instant)
4. Add to `.env` file as `CENSUS_API_KEY`

**Rate Limits**:
- 500 requests per IP per day (documented)
- No per-second limit documented (use conservative 0.5s delay)

---

## Verification Plan

1. **Unit Tests**: `uv run pytest tests/test_census_client.py -v`
2. **Factory Tests**: `uv run pytest tests/test_clients_factory.py -v`
3. **Full Suite**: `uv run pytest`
4. **CLI Verify**: `uv run python -m src.fred_macro.cli verify`
5. **Test Real API**:
   ```python
   from src.fred_macro.clients import ClientFactory
   client = ClientFactory.get_client("CENSUS")
   df = client.get_series_data("CENSUS_EXP_GOODS",
                                start_date="2024-01-01",
                                end_date="2024-12-31")
   ```
6. **Mixed Ingestion**: `uv run python -m src.fred_macro.cli ingest --mode incremental`

Success criteria:
- All tests pass (target: 120+ tests)
- Census API key validated
- Census series populated with historical data
- No critical DQ findings

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API key not configured | Graceful error with registration URL |
| Rate limit exceeded | Conservative 0.5s delay; log 429s |
| Dataset structure changes | Version-specific endpoints where available |
| Country code changes | Document ISO codes; handle deprecations |
| Missing API key | Clear error message directing to registration |
| Daily rate limit hit | Log warning, skip remaining series, resume next day |

---

## Data Quality Considerations

### Expected Patterns

1. **Trade Data Revisions**: Census revises trade data for 1-2 months after initial release
   - Initial release: ~6 weeks after month-end
   - Revised data: Following months
   - **Not a DQ issue** - document revision schedule

2. **Seasonal Patterns**: Strong seasonality in trade (holiday imports) and inventories
   - Use seasonally adjusted series where available
   - Document seasonal vs NSA in catalog

3. **Country-Level Volatility**: Individual country trade flows more volatile than totals
   - Expected behavior, not a data issue

### Data Quality Rules

Apply standard validations:
- **Stale Data Warning**: If most recent observation is > 90 days old (monthly series)
- **Missing Data**: Series with zero observations trigger warnings
- **Value Range**: Trade/inventory values should be non-negative

---

## Branch Strategy

Before implementation:
```bash
git checkout main
git pull origin main
git checkout -b feat/census-api-integration
```

Commits:
1. `feat(clients): add CensusClient implementation`
2. `feat(catalog): add Census series to catalog`
3. `test(census): add CensusClient unit tests`
4. `docs: add Census API documentation`
5. `config: add Census API key configuration`

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| CensusClient implementation | 45 min |
| ClientFactory + Catalog updates | 10 min |
| Unit tests | 40 min |
| API key configuration | 10 min |
| Integration testing | 20 min |
| Documentation | 20 min |
| **Total** | ~2.5 hours |

---

## Post-Implementation

### Total Dashboard Coverage

After Census integration:
- **Total Series**: ~103 (88 current + 15 Census)
- **Data Sources**: 4 (FRED, BLS, TREASURY, CENSUS)
- **Categories**:
  - Monetary Policy (FRED)
  - Labor Markets (FRED, BLS)
  - Inflation (FRED, BLS)
  - Treasury Markets (TREASURY)
  - International Trade (CENSUS) ← NEW
  - Business Inventories (CENSUS) ← NEW

### Coverage Gaps Addressed

✅ **Trade Data**: Direct access to exports/imports (previously only FRED derivatives)
✅ **Inventory Data**: Leading indicators for production cycles
✅ **Country-Level Trade**: China, Canada, Mexico bilateral flows
✅ **Inventory/Sales Ratios**: Supply chain health indicators

---

## References

- [Census API Documentation](https://www.census.gov/data/developers/data-sets.html)
- [International Trade API](https://www.census.gov/data/developers/data-sets/international-trade.html)
- [Economic Indicators Time Series](https://www.census.gov/data/developers/data-sets/economic-indicators.html)
- [API Key Registration](https://api.census.gov/data/key_signup.html)

---

**Status**: READY FOR IMPLEMENTATION
**Priority**: Medium (complements existing sources)
**Dependencies**: Census API key registration
**Estimated Timeline**: 1 session (~2.5 hours)
