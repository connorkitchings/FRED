# ADR-0004: Three-Tier Indicator Organization

**Status**: Accepted

**Date**: 2026-02-12

**Deciders**: Connor Kitchings

**Context**: System needs extensible organization of economic indicators without overwhelming initial implementation.

---

## Context and Problem Statement

FRED provides access to 800,000+ economic time series. For a personal macro tracking dashboard, we need to:

1. **Start focused**: Build MVP with essential indicators
2. **Enable expansion**: Add more indicators over time without restructuring
3. **Maintain clarity**: Organize indicators logically as the catalog grows
4. **Avoid complexity**: Don't over-engineer for hypothetical future needs

### Options Considered

1. **Flat list** (no organization)
2. **Two tiers** (Core and Extended)
3. **Three tiers** (Core, Extended, Deep Dive)
4. **Category-based only** (group by economic category)
5. **Priority levels** (P0, P1, P2, P3)

---

## Decision

**Chosen Option**: Three-tier organization (Tier 1, Tier 2, Tier 3) combined with category tags.

### Tier Definitions

**Tier 1: Core Indicators**
- The "Big Four" essential macro indicators
- Always tracked, always displayed
- MVP scope
- Count: 4 series

**Tier 2: Extended Indicators**
- Commonly referenced indicators for broader coverage
- Post-MVP expansion
- Count: 20-30 series

**Tier 3: Deep Dive Indicators**
- Specialized, sector-specific, or less common indicators
- Future exploration and research
- Count: 40+ series

---

## Decision Drivers

### ✅ Positive Factors

1. **Clear MVP Scope**
   - Tier 1 defines exactly what MVP includes
   - "Build Tier 1 first" is unambiguous
   - Avoids scope creep during initial development

2. **Natural Expansion Path**
   - After MVP: Add Tier 2
   - Later: Add Tier 3 as needed
   - No restructuring required

3. **Config-Driven**
   - Tier is just a field in YAML config
   - Easy to promote/demote indicators between tiers
   - No code changes needed

4. **User-Friendly**
   - "Core indicators" is intuitive
   - Three levels are easy to remember
   - Not too few (flat) or too many (overwhelming)

5. **Filtering Support**
   - Can query "show me Tier 1 only"
   - Can ingest "Tier 1 and 2 only"
   - Enables progressive feature rollout

### ⚠️ Trade-offs

1. **Subjective Boundaries**
   - What's "core" vs. "extended" is somewhat arbitrary
   - Mitigation: Document tier criteria clearly

2. **Maintenance Overhead**
   - Need to assign tier to each series
   - Mitigation: Only ~50-100 series total, manageable

---

## Comparison with Alternatives

### Option 1: Flat List (No Organization)

**Approach**: All indicators in single list, no tiers

**Pros**:
- Simplest implementation
- No tier assignment needed

**Cons**:
- ❌ No clear MVP scope
- ❌ Hard to prioritize
- ❌ Catalog becomes overwhelming as it grows

**Verdict**: Rejected — lacks structure for expansion

---

### Option 2: Two Tiers (Core and Extended)

**Approach**: Tier 1 (essential) and Tier 2 (everything else)

**Pros**:
- Simple binary classification
- Clear MVP (Tier 1)

**Cons**:
- ❌ "Extended" becomes a catch-all
- ❌ No distinction between "commonly useful" and "niche"
- ❌ Hard to prioritize post-MVP expansion

**Verdict**: Rejected — not enough granularity

---

### Option 3: Three Tiers (Chosen)

**Approach**: Tier 1 (Core), Tier 2 (Extended), Tier 3 (Deep Dive)

**Pros**:
- ✅ Clear MVP scope (Tier 1)
- ✅ Natural post-MVP expansion (Tier 2)
- ✅ Room for future growth (Tier 3)
- ✅ Not too many levels

**Cons**:
- ⚠️ Need to define tier boundaries

**Verdict**: Chosen — best balance of structure and simplicity

---

### Option 4: Category-Based Only

**Approach**: Organize by economic category (labor, housing, etc.), no tiers

**Pros**:
- Thematic organization
- Natural grouping

**Cons**:
- ❌ Doesn't define MVP scope
- ❌ All categories equally important (not true)
- ❌ Hard to prioritize implementation

**Verdict**: Rejected — use categories AND tiers

---

### Option 5: Priority Levels (P0, P1, P2, P3)

**Approach**: Software engineering style priority levels

**Pros**:
- Familiar to engineers
- Fine-grained prioritization

**Cons**:
- ❌ Too technical for user-facing documentation
- ❌ Four levels may be too many
- ❌ P0/P1/P2/P3 not intuitive

**Verdict**: Rejected — tiers are more user-friendly

---

## Technical Details

### Tier Field in Series Catalog

```yaml
# config/series_catalog.yaml
series:
  - series_id: FEDFUNDS
    title: Federal Funds Effective Rate
    category: financial_markets
    tier: 1  # ← Tier assignment

  - series_id: HOUST
    title: Housing Starts
    category: housing
    tier: 2

  - series_id: PERMIT1MSA
    title: Building Permits in Metro Area X
    category: housing
    tier: 3
```

### Database Schema

```sql
CREATE TABLE series_catalog (
    series_id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    tier INTEGER NOT NULL,  -- 1, 2, or 3
    ...
);
```

---

## Tier Criteria

### Tier 1: Core Indicators (The "Big Four")

**Criteria**:
- ✅ Universally recognized macro indicator
- ✅ Frequently cited in economic news
- ✅ Covers a distinct aspect of the economy (output, labor, prices, policy)
- ✅ High-quality data with regular releases

**Indicators**:
1. **FEDFUNDS** — Federal Funds Rate (monetary policy)
2. **UNRATE** — Unemployment Rate (labor market)
3. **CPIAUCSL** — Consumer Price Index (inflation)
4. **GDPC1** — Real GDP (economic output)

**Philosophy**: These are the first indicators you'd check to understand the economy's state.

---

### Tier 2: Extended Indicators

**Criteria**:
- ✅ Commonly referenced in economic analysis
- ✅ Complements Tier 1 with additional detail
- ✅ Helps answer specific questions (housing, consumption, manufacturing)
- ✅ Regularly updated and reliable

**Examples**:

**Labor Market**:
- PAYEMS (Nonfarm Payrolls)
- AHETPI (Average Hourly Earnings)
- CIVPART (Labor Force Participation)

**Housing**:
- HOUST (Housing Starts)
- PERMIT (Building Permits)
- CSUSHPISA (Case-Shiller Home Price Index)

**Financial Markets**:
- DGS10 (10-Year Treasury Yield)
- SP500 (S&P 500 Index)
- DEXUSEU (USD/EUR Exchange Rate)

**Consumption**:
- RSXFS (Retail Sales)
- PCE (Personal Consumption Expenditures)
- UMCSENT (Consumer Sentiment)

**Manufacturing**:
- INDPRO (Industrial Production)
- TCU (Capacity Utilization)

**Philosophy**: These indicators provide broader coverage and answer "what about X?" questions.

---

### Tier 3: Deep Dive Indicators

**Criteria**:
- ✅ Specialized or sector-specific
- ✅ Less commonly referenced but valuable for research
- ✅ May be regional, niche, or experimental

**Examples** (to be defined):
- Regional unemployment rates (state-level)
- Detailed CPI components (food, energy subindices)
- Sector-specific capacity utilization (manufacturing subsectors)
- Alternative inflation measures (Trimmed Mean PCE)
- Financial market microstructure (bid-ask spreads)

**Philosophy**: These indicators support deep research or specific hypotheses.

---

## Consequences

### Positive Consequences

1. **Clear MVP Scope**
   - Tier 1 = MVP (4 series)
   - Unambiguous starting point
   - Fast iteration to working system

2. **Guided Expansion**
   - Post-MVP: Add Tier 2 (~25 series)
   - Future: Add Tier 3 as needed
   - No rework required

3. **User Experience**
   - Can filter UI/dashboard by tier
   - "Show me core indicators" is intuitive
   - Progressive disclosure for complexity

4. **Config-Driven**
   - Tiers defined in YAML
   - No code changes to add series
   - Easy to rebalance tiers

5. **Ingestion Optimization**
   - Can ingest Tier 1 only (MVP)
   - Can ingest Tier 1+2 (Post-MVP)
   - Incremental expansion of API usage

### Negative Consequences

1. **Subjective Classification**
   - Some indicators could reasonably be Tier 2 or 3
   - Mitigation: Document rationale, accept imperfection

2. **Maintenance**
   - Need to assign tier when adding new series
   - Mitigation: Only ~50-100 series, not burdensome

3. **Tier Inflation Risk**
   - Temptation to add more Tier 1 indicators
   - Mitigation: Keep Tier 1 to 4-6 series max

---

## Usage Examples

### Querying by Tier

```sql
-- Get all Tier 1 (core) indicators
SELECT series_id, title
FROM series_catalog
WHERE tier = 1;

-- Get latest values for Tier 1 only
SELECT s.series_id, s.title, o.observation_date, o.value
FROM observations o
JOIN series_catalog s ON o.series_id = s.series_id
WHERE s.tier = 1
  AND o.observation_date = (
    SELECT MAX(observation_date)
    FROM observations o2
    WHERE o2.series_id = o.series_id
  );
```

---

### Ingestion by Tier

```python
def ingest_by_tier(tier: int, mode: str):
    """Ingest indicators for a specific tier."""
    # Load series catalog
    with open('config/series_catalog.yaml') as f:
        catalog = yaml.safe_load(f)

    # Filter by tier
    series_list = [
        s['series_id'] for s in catalog['series']
        if s['tier'] == tier
    ]

    # Ingest
    for series_id in series_list:
        if mode == 'backfill':
            fetch_and_upsert(series_id, start_date='2016-01-01')
        else:  # incremental
            fetch_and_upsert(series_id, start_date=get_date_60_days_ago())
```

---

### Dashboard Display

```python
def display_dashboard():
    """Display indicators organized by tier."""
    print("=== Core Indicators (Tier 1) ===")
    display_tier(tier=1)

    print("\n=== Extended Indicators (Tier 2) ===")
    display_tier(tier=2)

    print("\n=== Deep Dive Indicators (Tier 3) ===")
    display_tier(tier=3)
```

---

## Implementation Guidelines

### Adding New Indicators

When adding a new indicator, ask:

1. **Is this a universally recognized macro indicator?**
   - Yes → Consider Tier 1 (but keep Tier 1 small!)
   - No → Continue to question 2

2. **Would I reference this in broad economic analysis?**
   - Yes → Tier 2
   - No → Continue to question 3

3. **Is this specialized, niche, or exploratory?**
   - Yes → Tier 3

**Default**: When uncertain, start with Tier 3 and promote if it proves valuable.

---

### Promoting/Demoting Indicators

It's okay to change tiers over time:

```yaml
# Example: Promote housing starts from Tier 3 → Tier 2
- series_id: HOUST
  title: Housing Starts
  tier: 2  # Changed from 3 to 2 (more important than originally thought)
  notes: "Promoted to Tier 2 on 2026-03-15 after frequent use"
```

---

## Monitoring

Track tier distribution in series catalog:

```sql
SELECT tier, COUNT(*) as series_count
FROM series_catalog
GROUP BY tier
ORDER BY tier;
```

Expected distribution:
- Tier 1: 4-6 series (keep small!)
- Tier 2: 20-30 series
- Tier 3: 40+ series (open-ended)

---

## Future Considerations

### Tier 0: Critical Alerts?

If we later add alerting, consider Tier 0 for "critical watch indicators" that trigger notifications.

For now, Tier 1 serves this purpose.

---

### Combining with Categories

Tiers and categories are orthogonal:
- **Tiers**: Priority/importance
- **Categories**: Thematic grouping (labor, housing, prices, etc.)

Both are useful for different purposes:
- Tiers: "What should I build next?"
- Categories: "Show me all labor market indicators"

---

## Related Decisions

- [ADR-0002: MotherDuck](adr-0002-motherduck.md) — Database storage
- [Data Dictionary](../../data/dictionary.md) — Full indicator catalog

---

## References

- **FRED Website**: https://fred.stlouisfed.org
- **Indicator Categories**: https://fred.stlouisfed.org/categories

---

**Last Updated**: 2026-02-12
**Review Date**: After Tier 2 implementation (reassess tier boundaries)
