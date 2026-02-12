# ADR-0003: Use MERGE INTO for Upsert Strategy

**Status**: Accepted

**Date**: 2026-02-12

**Deciders**: Connor Kitchings

**Context**: System must handle data revisions from FRED API without creating duplicate observations.

---

## Context and Problem Statement

Economic indicators frequently get revised as more complete data becomes available. For example:

- **GDP (GDPC1)**: Released three times per quarter (advance, revised, final)
- **Employment (PAYEMS)**: Prior two months revised with each release
- **Other indicators**: Occasional revisions for data corrections

The system needs a strategy to:

1. Insert new observations when they first appear
2. Update existing observations when values are revised
3. Prevent duplicate rows for the same (series_id, observation_date)
4. Be idempotent (safe to re-run ingestion)

### Options Considered

1. **INSERT with ON CONFLICT (SQLite/Postgres style)**
2. **MERGE INTO (SQL standard upsert)**
3. **DELETE + INSERT**
4. **Application-level logic** (check existence, then INSERT or UPDATE)

---

## Decision

**Chosen Option**: Use SQL `MERGE INTO` statement with composite key matching.

```sql
MERGE INTO observations AS target
USING (SELECT ? AS series_id, ? AS observation_date, ? AS value) AS source
ON target.series_id = source.series_id
   AND target.observation_date = source.observation_date
WHEN MATCHED THEN
    UPDATE SET value = source.value, load_timestamp = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (series_id, observation_date, value, load_timestamp)
    VALUES (source.series_id, source.observation_date, source.value, CURRENT_TIMESTAMP);
```

---

## Decision Drivers

### ✅ Positive Factors

1. **SQL Standard**
   - Part of SQL:2003 standard
   - Widely supported (DuckDB, PostgreSQL, SQL Server, Oracle)
   - Declarative and clear semantics

2. **Atomic Operation**
   - Single SQL statement
   - Database handles matching logic
   - Reduces race conditions

3. **Handles Both Cases**
   - Inserts new observations
   - Updates existing observations
   - Explicit logic for each case

4. **Performance**
   - Database-optimized matching
   - Better than separate SELECT + INSERT/UPDATE
   - Bulk operations supported

5. **Idempotency**
   - Re-running produces same result
   - No duplicate rows created
   - Safe for retries and re-runs

### ⚠️ Trade-offs

1. **Slightly Complex SQL**
   - More verbose than simple INSERT
   - Requires understanding of MERGE syntax
   - Mitigation: Well-documented and testable

2. **DuckDB-Specific Syntax**
   - Syntax varies slightly between databases
   - Mitigation: We're committed to DuckDB/MotherDuck

---

## Comparison with Alternatives

### Option 1: INSERT with ON CONFLICT (SQLite/Postgres)

**Syntax**:
```sql
INSERT INTO observations (series_id, observation_date, value, load_timestamp)
VALUES (?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT (series_id, observation_date)
DO UPDATE SET value = EXCLUDED.value, load_timestamp = CURRENT_TIMESTAMP;
```

**Pros**:
- Concise syntax
- Common in SQLite and PostgreSQL

**Cons**:
- ❌ Not standard SQL (Postgres/SQLite-specific)
- ❌ Not supported in DuckDB (as of 0.10)

**Verdict**: Rejected — not supported in DuckDB

---

### Option 2: MERGE INTO (Chosen)

**Syntax**: See decision above

**Pros**:
- ✅ SQL standard
- ✅ Supported in DuckDB
- ✅ Explicit and clear
- ✅ Atomic operation

**Cons**:
- ⚠️ Slightly verbose

**Verdict**: Chosen — best fit for DuckDB

---

### Option 3: DELETE + INSERT

**Approach**:
```sql
DELETE FROM observations WHERE series_id = ? AND observation_date = ?;
INSERT INTO observations VALUES (?, ?, ?, CURRENT_TIMESTAMP);
```

**Pros**:
- Simple logic
- Works in any database

**Cons**:
- ❌ Not atomic (two statements)
- ❌ Deletes even if no update needed
- ❌ Inefficient for large batches
- ❌ Vulnerable to race conditions

**Verdict**: Rejected — not atomic or efficient

---

### Option 4: Application-Level Logic

**Approach**:
```python
if exists(series_id, observation_date):
    update_observation(series_id, observation_date, value)
else:
    insert_observation(series_id, observation_date, value)
```

**Pros**:
- Full control in Python
- Database-agnostic

**Cons**:
- ❌ Multiple round-trips to database
- ❌ Race condition risk
- ❌ Slower for batch operations
- ❌ More complex code

**Verdict**: Rejected — inefficient and error-prone

---

## Technical Details

### Composite Primary Key

The `observations` table has a composite primary key:

```sql
CREATE TABLE observations (
    series_id VARCHAR NOT NULL,
    observation_date DATE NOT NULL,
    value DOUBLE,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (series_id, observation_date)
);
```

This ensures:
- No duplicate (series_id, observation_date) rows
- Fast lookups for matching
- Database-enforced constraint

---

### MERGE INTO Implementation

#### Single Observation

```python
def upsert_observation(conn, series_id, observation_date, value):
    """Upsert a single observation."""
    sql = """
    MERGE INTO observations AS target
    USING (SELECT ? AS series_id, ? AS observation_date, ? AS value) AS source
    ON target.series_id = source.series_id
       AND target.observation_date = source.observation_date
    WHEN MATCHED THEN
        UPDATE SET
            value = source.value,
            load_timestamp = CURRENT_TIMESTAMP
    WHEN NOT MATCHED THEN
        INSERT (series_id, observation_date, value, load_timestamp)
        VALUES (source.series_id, source.observation_date, source.value, CURRENT_TIMESTAMP);
    """
    conn.execute(sql, [series_id, observation_date, value])
```

#### Batch Observations

```python
def upsert_batch(conn, df: pd.DataFrame):
    """Upsert a batch of observations from DataFrame.

    Args:
        df: DataFrame with columns [series_id, observation_date, value]
    """
    sql = """
    MERGE INTO observations AS target
    USING (SELECT * FROM df) AS source
    ON target.series_id = source.series_id
       AND target.observation_date = source.observation_date
    WHEN MATCHED THEN
        UPDATE SET
            value = source.value,
            load_timestamp = CURRENT_TIMESTAMP
    WHEN NOT MATCHED THEN
        INSERT (series_id, observation_date, value, load_timestamp)
        VALUES (source.series_id, source.observation_date, source.value, CURRENT_TIMESTAMP);
    """
    conn.execute(sql)
```

---

### Handling Data Revisions

#### GDP Example

GDP is revised three times per quarter:

```
2025-Q4 Advance:  22,500.0  (released 2026-01-30)
2025-Q4 Revised:  22,520.5  (released 2026-02-27) ← revised up
2025-Q4 Final:    22,510.2  (released 2026-03-28) ← revised down
```

**Behavior**:

1. **First ingestion (Advance)**:
   - `WHEN NOT MATCHED THEN INSERT` → Row inserted with value 22,500.0

2. **Second ingestion (Revised)**:
   - `WHEN MATCHED THEN UPDATE` → Value updated to 22,520.5

3. **Third ingestion (Final)**:
   - `WHEN MATCHED THEN UPDATE` → Value updated to 22,510.2

**Result**: Always reflects latest FRED value

---

## Consequences

### Positive Consequences

1. **Automatic Revision Handling**
   - No special logic needed for revisions
   - Latest value always in database
   - Transparent to downstream queries

2. **Idempotency**
   - Re-running ingestion produces same result
   - Safe to re-run on failures
   - Enables reliable automation

3. **No Duplicates**
   - Composite primary key enforced
   - MERGE logic prevents duplicates
   - Data integrity guaranteed

4. **Performance**
   - Single SQL statement per batch
   - Database-optimized matching
   - Bulk operations supported

5. **Observability**
   - Can track inserts vs. updates in logs
   - `load_timestamp` shows when data last updated
   - Audit trail for revisions

### Negative Consequences

1. **Loses Revision History**
   - Only current value stored
   - Cannot reconstruct historical revisions
   - Acceptable: Historical vintages out of scope for MVP

2. **Slightly Complex SQL**
   - More verbose than simple INSERT
   - Requires understanding MERGE semantics
   - Mitigation: Well-documented with examples

3. **DuckDB-Specific Syntax**
   - Cannot easily switch databases
   - Mitigation: Committed to DuckDB ecosystem

---

## Testing Strategy

### Test 1: Insert New Observation

```python
def test_upsert_new_observation(conn):
    """Test inserting a new observation."""
    upsert_observation(conn, 'UNRATE', '2026-01-01', 3.7)

    result = conn.execute(
        "SELECT value FROM observations WHERE series_id = 'UNRATE' AND observation_date = '2026-01-01'"
    ).fetchone()

    assert result[0] == 3.7
```

---

### Test 2: Update Existing Observation

```python
def test_upsert_update_observation(conn):
    """Test updating an existing observation."""
    # Insert initial value
    upsert_observation(conn, 'GDPC1', '2025-10-01', 22500.0)

    # Update with revision
    upsert_observation(conn, 'GDPC1', '2025-10-01', 22520.5)

    # Verify updated value
    result = conn.execute(
        "SELECT value FROM observations WHERE series_id = 'GDPC1' AND observation_date = '2025-10-01'"
    ).fetchone()

    assert result[0] == 22520.5

    # Verify only one row exists
    count = conn.execute(
        "SELECT COUNT(*) FROM observations WHERE series_id = 'GDPC1' AND observation_date = '2025-10-01'"
    ).fetchone()

    assert count[0] == 1  # No duplicates
```

---

### Test 3: Idempotency

```python
def test_upsert_idempotency(conn):
    """Test that re-running upsert produces same result."""
    # Run upsert twice
    upsert_observation(conn, 'CPIAUCSL', '2026-01-01', 308.5)
    upsert_observation(conn, 'CPIAUCSL', '2026-01-01', 308.5)

    # Verify only one row
    count = conn.execute(
        "SELECT COUNT(*) FROM observations WHERE series_id = 'CPIAUCSL' AND observation_date = '2026-01-01'"
    ).fetchone()

    assert count[0] == 1
```

---

### Test 4: Batch Upsert

```python
def test_batch_upsert(conn):
    """Test upserting a batch of observations."""
    df = pd.DataFrame({
        'series_id': ['FEDFUNDS', 'FEDFUNDS', 'UNRATE'],
        'observation_date': ['2026-01-01', '2026-02-01', '2026-01-01'],
        'value': [4.50, 4.50, 3.7]
    })

    upsert_batch(conn, df)

    count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()
    assert count[0] == 3
```

---

## Monitoring

Track upsert performance in ingestion logs:

```python
# Count inserts vs. updates
rows_before = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]

# Run upsert
upsert_batch(conn, df)

rows_after = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]

rows_inserted = rows_after - rows_before
rows_updated = len(df) - rows_inserted

# Log results
logger.info(f"Upsert complete: {rows_inserted} inserted, {rows_updated} updated")
```

---

## Future Considerations

### Historical Vintages (Out of Scope for MVP)

If we later need to track revision history:

1. Add `vintage_date` column to observations
2. Change primary key to (series_id, observation_date, vintage_date)
3. Store all revisions separately

This would enable "as-of" queries (e.g., "what did Q4 2025 GDP look like on Feb 1, 2026?")

For now, we only store the latest value.

---

## Related Decisions

- [ADR-0002: MotherDuck](adr-0002-motherduck.md) — Database choice
- [Technical Requirements](../../technical_requirements.md) — Upsert requirements

---

## References

- **SQL MERGE Syntax**: https://en.wikipedia.org/wiki/Merge_(SQL)
- **DuckDB MERGE**: https://duckdb.org/docs/sql/statements/insert (see MERGE section)
- **FRED Data Revisions**: https://fred.stlouisfed.org/docs/api/fred/

---

**Last Updated**: 2026-02-12
**Review Date**: After MVP completion (assess if revision tracking needed)
