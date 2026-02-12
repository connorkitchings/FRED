# ADR-0002: Use MotherDuck Instead of Local DuckDB

**Status**: Accepted

**Date**: 2026-02-12

**Deciders**: Connor Kitchings

**Context**: System requires persistent storage for macroeconomic time series data.

---

## Context and Problem Statement

The FRED-Macro-Dashboard needs a database to store time series observations, series metadata, and ingestion logs. The system must support:

1. **Persistence**: Data survives across sessions
2. **Accessibility**: Query data from multiple machines (laptop, desktop, cloud notebooks)
3. **SQL Interface**: Standard SQL for querying and analysis
4. **Analytics Performance**: Fast queries over time series data
5. **Cost**: Ideally free or low-cost for personal use

### Options Considered

1. **Local DuckDB file** (`fred_macro.db`)
2. **MotherDuck** (cloud-hosted DuckDB)
3. **PostgreSQL** (self-hosted or cloud)
4. **SQLite** (embedded file-based)

---

## Decision

**Chosen Option**: MotherDuck (cloud-hosted DuckDB)

We will use MotherDuck as the primary data store, connecting via token authentication.

---

## Decision Drivers

### ✅ Positive Factors

1. **Cloud Accessibility**
   - Access data from laptop, desktop, or cloud notebooks
   - No need to sync database files across machines
   - Can query from anywhere with internet

2. **DuckDB Benefits**
   - Columnar storage optimized for analytics
   - Fast aggregations and time series queries
   - Native SQL with rich analytical functions
   - Excellent Python integration

3. **Free Tier Adequate**
   - 10GB storage (need <10MB)
   - 10GB compute (more than sufficient)
   - No credit card required
   - Personal use is supported

4. **Simplicity**
   - Same SQL dialect as local DuckDB
   - Single connection string
   - No server management
   - Automatic backups

5. **Learning Value**
   - Experience with cloud data warehouses
   - Understand DuckDB in production
   - Modern data infrastructure patterns

### ⚠️ Trade-offs

1. **Internet Dependency**
   - Requires internet connection for all operations
   - Cannot work offline
   - Mitigation: Stable internet is generally available

2. **Authentication Required**
   - Must manage MotherDuck token
   - Token rotation needed periodically
   - Mitigation: Token stored in environment variable

3. **Cloud Vendor Lock-in (Mild)**
   - Data stored in MotherDuck's infrastructure
   - Mitigation: Can export to local DuckDB file if needed

4. **Latency**
   - Network round-trip adds ~50-200ms per query
   - Mitigation: Not significant for batch ingestion or analysis

---

## Comparison with Alternatives

### Option 1: Local DuckDB File

**Pros**:
- No internet required
- No authentication needed
- Zero cost
- Fast (no network latency)

**Cons**:
- ❌ Not accessible across machines
- ❌ Need to sync file manually (Dropbox, Git LFS, etc.)
- ❌ File corruption risk if synced incorrectly
- ❌ No collaborative access

**Verdict**: Rejected due to multi-machine access requirement

---

### Option 2: MotherDuck (Chosen)

**Pros**:
- ✅ Cloud-accessible from anywhere
- ✅ Same SQL dialect as local DuckDB
- ✅ Free tier sufficient
- ✅ Automatic backups
- ✅ No server management

**Cons**:
- ⚠️ Requires internet
- ⚠️ Token management
- ⚠️ Mild vendor lock-in

**Verdict**: Chosen — best balance of simplicity and accessibility

---

### Option 3: PostgreSQL

**Pros**:
- Industry-standard RDBMS
- Rich ecosystem
- Cloud options (RDS, Supabase, Neon)

**Cons**:
- ❌ Not optimized for analytics (row-based storage)
- ❌ Slower for time series aggregations
- ❌ More complex setup
- ❌ Free tiers more limited
- ❌ Overkill for this use case

**Verdict**: Rejected — unnecessary complexity

---

### Option 4: SQLite

**Pros**:
- Simple embedded database
- No server needed
- Widely supported

**Cons**:
- ❌ Not optimized for analytics
- ❌ Limited analytical SQL functions
- ❌ Same multi-machine sync issues as local DuckDB
- ❌ Inferior performance for time series

**Verdict**: Rejected — not analytics-optimized

---

## Technical Details

### Connection String

```python
import duckdb
import os

token = os.getenv('MOTHERDUCK_TOKEN')
conn = duckdb.connect(f'md:fred_macro?motherduck_token={token}')
```

### Configuration

Environment variable in `.env` file:
```bash
MOTHERDUCK_TOKEN="your_token_here"
```

### Fallback Strategy

If MotherDuck is unavailable or slow, fallback to local DuckDB:

```python
# Local fallback
conn = duckdb.connect('fred_macro.db')
```

SQL is identical; only connection string changes.

---

## Consequences

### Positive Consequences

1. **Multi-Machine Workflow**
   - Can ingest data on desktop, query on laptop
   - Share database with notebooks in cloud (Google Colab, Hex)
   - No file syncing complexity

2. **Data Safety**
   - Automatic backups by MotherDuck
   - No risk of local file corruption
   - Can re-download data if local issues

3. **Scalability**
   - Free tier supports 10GB (10,000x current need)
   - Can upgrade if needed (unlikely)
   - No infrastructure management

4. **Learning Opportunity**
   - Hands-on experience with cloud data warehouse
   - Modern data infrastructure patterns
   - Token-based authentication

### Negative Consequences

1. **Internet Dependency**
   - Cannot run ingestion or queries offline
   - Network issues block all operations
   - Acceptable for personal project with stable internet

2. **Token Management**
   - Must secure token in environment variable
   - Need to rotate token periodically
   - Risk of accidental exposure (mitigated by gitignore)

3. **Latency Overhead**
   - ~50-200ms added to each query
   - Not noticeable for batch ingestion
   - Acceptable for analysis workloads

4. **Vendor Dependency**
   - Data stored in MotherDuck infrastructure
   - Service reliability depends on MotherDuck uptime
   - Low risk: Can export to local file if needed

---

## Implementation Notes

### Schema Creation

Same SQL works for both local and MotherDuck:

```sql
CREATE TABLE IF NOT EXISTS observations (
    series_id VARCHAR NOT NULL,
    observation_date DATE NOT NULL,
    value DOUBLE,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (series_id, observation_date)
);
```

### Migration Path

If MotherDuck becomes unsuitable:

1. Export data: `COPY (SELECT * FROM observations) TO 'observations.csv'`
2. Switch connection to local: `conn = duckdb.connect('fred_macro.db')`
3. Import data: `COPY observations FROM 'observations.csv'`

---

## Monitoring

Track MotherDuck usage:

- Storage: Monitor total database size
- Queries: Log query count and duration
- Errors: Alert on authentication failures

Check usage: MotherDuck dashboard at https://app.motherduck.com/

---

## Related Decisions

- [ADR-0003: Upsert Strategy](adr-0003-upsert-strategy.md) — How we handle data updates
- [Technical Requirements](../../technical_requirements.md) — Database requirements

---

## References

- **MotherDuck Documentation**: https://motherduck.com/docs/
- **DuckDB Documentation**: https://duckdb.org/docs/
- **DuckDB Python API**: https://duckdb.org/docs/api/python/overview

---

**Last Updated**: 2026-02-12
**Review Date**: After MVP completion (reassess if issues arise)
