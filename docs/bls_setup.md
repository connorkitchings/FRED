# BLS API Setup Guide

## Overview

The FRED-Macro-Dashboard now supports direct BLS API integration for 25 economic series, providing same-day data access with higher rate limits than FRED-mediated sources.

## Why Use Direct BLS API?

1. **Data Freshness**: Same-day availability vs next-day on FRED
2. **Rate Limits**: 50 queries/10 seconds (registered) vs 10 queries/10 seconds (unregistered)
3. **Cost**: Free API access
4. **Coverage**: Access to BLS-exclusive series

## Quick Start

### 1. Register for BLS API Key (Recommended)

Visit https://data.bls.gov/registrationEngine/

Registration provides:
- Higher rate limits (50 vs 10 queries per 10 seconds)
- Access to calculations and annual averages
- Series descriptions and metadata

### 2. Configure Environment Variable

```bash
# macOS/Linux - add to ~/.bashrc or ~/.zshrc
export BLS_API_KEY="your-api-key-here"

# Windows PowerShell
$env:BLS_API_KEY="your-api-key-here"
```

### 3. Verify Configuration

```bash
uv run fred-cli verify
```

## BLS Series Added

### Phase 1: Core Indicators (8 series)
- CES0000000001: Total Nonfarm Employment
- CES0500000003: Average Hourly Earnings
- LNS11300000: Labor Force Participation Rate
- CUUS0000SA0: Core CPI (ex Food and Energy)
- WPUFD4: PPI - Finished Goods
- CUUR0000SETB01: CPI - Gasoline
- PRS85006112: Nonfarm Business Productivity
- ECIALLCIV: Employment Cost Index

### Phase 2: Extended Employment (6 series)
- LNS12000000: Employment-Population Ratio
- LNS13000000: Long-term Unemployed (15+ weeks)
- LNS14027662: Youth Unemployment (16-19)
- CES3000000001: Manufacturing Employment
- CES4200000001: Trade/Transport/Utilities Employment
- CES5051000001: Financial Activities Employment

### Phase 3: Price Detail (6 series)
- CUSR0000SAF11: CPI - Food at Home
- CUSR0000SAS: CPI - Services
- CUSR0000SAC: CPI - Commodities
- WPUSOP3000: PPI - Crude Materials
- PRS85006152: Unit Labor Costs
- PRS85006092: Real Hourly Compensation

### Phase 4: Regional and Demographics (3 series)
- LASST060000000000003: California Unemployment Rate
- LASST360000000000003: New York Unemployment Rate
- LNS14027660: Unemployment Rate - Bachelor's Degree+

Plus 2 existing BLS series (LNS14000000 and CUUR0000SA0) for a total of 25 direct BLS series.

## Current Status

- **Total Series**: 80 (55 FRED + 25 BLS direct)
- **Test Coverage**: All 68 tests passing
- **Catalog Validation**: All series have unique IDs
