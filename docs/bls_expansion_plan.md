# BLS API Expansion Plan

## Executive Summary

This phase expands the FRED-Macro-Dashboard from 58 series (all FRED) to **100+ series** by adding **25 direct BLS API series**. This provides access to primary BLS data sources with higher frequency updates than FRED-mediated data.

## Current State
- **Total Series**: 58 (all FRED-sourced)
- **BLS Series**: 0 direct (2 were tested but not in production catalog)
- **Architecture**: Multi-source ready with ClientFactory

## Target State
- **Total Series**: 100+
- **Direct BLS Series**: 25
- **Source Distribution**: 75 FRED, 25 BLS direct

## BLS Series Selection Criteria

1. **Tier 1 Priority**: High-frequency, closely-watched indicators
2. **FRED Gaps**: Series with delays or limited history on FRED
3. **BLS Exclusives**: Data available only via BLS API
4. **Economic Significance**: Components of major indicators

## Proposed BLS Series (25 total)

### Employment & Unemployment (10 series)
| Series ID | Title | Frequency | Survey | Why BLS Direct |
|-----------|-------|-----------|---------|----------------|
| LNS14000000 | Unemployment Rate (CPS) | Monthly | Current Population Survey | Primary source, real-time |
| CES0000000001 | Total Nonfarm Employment | Monthly | Current Employment Statistics | Principal economic indicator |
| CES0500000003 | Avg Hourly Earnings - Total Private | Monthly | CES | Wage inflation tracker |
| LNS11300000 | Labor Force Participation | Monthly | CPS | Labor supply metric |
| LNS12000000 | Employment-Population Ratio | Monthly | CPS | Employment health |
| LNS13000000 | Persons Unemployed 15+ Weeks | Monthly | CPS | Structural unemployment |
| LNS14027662 | Youth Unemployment (16-19) | Monthly | CPS | Vulnerable worker segment |
| CES3000000001 | Manufacturing Employment | Monthly | CES | Industrial health |
| CES4200000001 | Trade/Transport/Utilities Employment | Monthly | CES | Service sector proxy |
| CES5051000001 | Financial Activities Employment | Monthly | CES | Financial sector health |

### Inflation & Prices (8 series)
| Series ID | Title | Frequency | Survey | Why BLS Direct |
|-----------|-------|-----------|---------|----------------|
| CUUR0000SA0 | CPI-All Items (NSA) | Monthly | Consumer Price Index | Primary inflation measure |
| CUUS0000SA0 | CPI-Core (All Items Less Food & Energy) | Monthly | CPI | Core inflation trend |
| CUSR0000SAF11 | CPI-Food at Home | Monthly | CPI | Food price inflation |
| CUSR0000SAS | CPI-Services | Monthly | CPI | Service inflation |
| CUSR0000SAC | CPI-Commodities | Monthly | CPI | Goods inflation |
| WPUFD4 | PPI-Finished Goods | Monthly | Producer Price Index | Wholesale inflation |
| WPUSOP3000 | PPI-Crude Materials | Monthly | PPI | Input cost pressures |
| CUUR0000SETB01 | CPI-Gasoline (All Types) | Monthly | CPI | Energy price shock indicator |

### Productivity & Costs (4 series)
| Series ID | Title | Frequency | Survey | Why BLS Direct |
|-----------|-------|-----------|---------|----------------|
| PRS85006112 | Nonfarm Business Sector Productivity | Quarterly | Productivity | Efficiency measure |
| PRS85006152 | Unit Labor Costs | Quarterly | Productivity | Inflation pressure |
| PRS85006092 | Real Hourly Compensation | Quarterly | Productivity | Worker welfare |
| ECIALLCIV | Employment Cost Index | Quarterly | National Compensation Survey | Labor cost trends |

### Regional & Demographics (3 series)
| Series ID | Title | Frequency | Survey | Why BLS Direct |
|-----------|-------|-----------|---------|----------------|
| LASST060000000000003 | CA Unemployment Rate | Monthly | LAUS | Regional indicator |
| LASST360000000000003 | NY Unemployment Rate | Monthly | LAUS | Regional indicator |
| LNS14027660 | Unemployment - Bachelor's Degree+ | Monthly | CPS | Educational attainment gap |

## Implementation Phases

### Phase 1: Core BLS Series (10 series)
Focus on high-frequency employment and inflation indicators
- LNS14000000, CES0000000001, CES0500000003, LNS11300000
- CUUR0000SA0, CUUS0000SA0, WPUFD4, CUUR0000SETB01
- PRS85006112, ECIALLCIV

### Phase 2: Extended Employment (6 series)
Labor market depth indicators
- LNS12000000, LNS13000000, LNS14027662
- CES3000000001, CES4200000001, CES5051000001

### Phase 3: Price Detail (6 series)
Inflation components and producer prices
- CUSR0000SAF11, CUSR0000SAS, CUSR0000SAC
- WPUSOP3000, PRS85006152, PRS85006092

### Phase 4: Regional & Demographics (3 series)
Geographic and educational breakdowns
- LASST060000000000003, LASST360000000000003, LNS14027660

## Technical Implementation

### 1. Catalog Updates
Add `source: BLS` field to new series entries
```yaml
- series_id: "LNS14000000"
  title: "Unemployment Rate (CPS)"
  units: "Percent"
  frequency: "Monthly"
  seasonal_adjustment: "Seasonally Adjusted"
  tier: 2
  source: "BLS"
  description: "Primary unemployment rate from Current Population Survey"
```

### 2. BLS API Key Management
- Document BLS registration process
- Add `BLS_API_KEY` to environment variables
- Implement rate limit optimization (50 req/10s with key vs 10 req/10s without)

### 3. Source Fallback System (Future Enhancement)
```python
# Priority: BLS direct → FRED → skip
source_priority = ["BLS", "FRED"]
```

### 4. Testing Requirements
- Unit tests for each BLS series ID format
- Integration tests for BLS client with real API
- Error handling tests (rate limits, invalid series)
- Data validation tests (format, date ranges)

## Benefits

1. **Data Freshness**: BLS data often available same-day vs FRED next-day
2. **Rate Limits**: 50 queries/10s with API key vs FRED's 120/hour
3. **Cost**: BLS API is free
4. **Coverage**: Access to series not on FRED or with limited history
5. **Resilience**: Dual-source architecture reduces single-point-of-failure

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| BLS API changes | Monitor BLS developer announcements |
| Rate limiting | Implement exponential backoff (already in place) |
| Data format differences | Standardize in BLSClient transformation layer |
| Maintenance overhead | Automated testing and health checks |

## Success Criteria

- [ ] 25 BLS series added to catalog
- [ ] All 25 series ingesting successfully
- [ ] BLS API key registered and configured
- [ ] Test coverage for BLS client ≥ 80%
- [ ] Documentation updated with BLS setup instructions
- [ ] Total series count ≥ 100

## Timeline Estimate

- **Phase 1**: 1 week (10 core series)
- **Phase 2**: 3-4 days (6 employment series)
- **Phase 3**: 3-4 days (6 price series)
- **Phase 4**: 2-3 days (3 regional series)
- **Testing & Documentation**: 2-3 days

**Total: 2.5-3 weeks**
