# Operational Runbook

This runbook documents how to operate, monitor, and troubleshoot the **FRED Macro Dashboard**.

## Table of Contents

- [Monitoring Data Ingestion](#monitoring-data-ingestion)
  - [Check Ingestion Status](#check-ingestion-status)
  - [Operational Data Quality (DQ) Reporting](#operational-data-quality-dq-reporting)
- [Troubleshooting](#troubleshooting)
  - [Common Errors](#common-errors)
  - [Database Issues](#database-issues)
- [Maintenance](#maintenance)
  - [Adding New Indicators](#adding-new-indicators)
  - [Updating DQ Rules](#updating-dq-rules)
- [Automation & Scheduling](#automation--scheduling)
  - [GitHub Actions](#github-actions)
  - [Secrets Configuration](#secrets-configuration)
- [Contact & Escalation](#contact--escalation)

---

## Monitoring Data Ingestion

### Check Ingestion Status

The primary way to verify ingestion health is via the `ingestion_log` table.

**Query: Latest 10 Runs**
```sql
SELECT run_id, run_timestamp, mode, status, duration_seconds, error_message
FROM ingestion_log
ORDER BY run_timestamp DESC
LIMIT 10;
```

**Status Codes**:
- `success`: All series processed successfully.
- `partial`: Some series succeeded, others failed (or DQ persistence failed).
- `failed`: The entire run crashed (e.g., connection lost).

### Operational Data Quality (DQ) Reporting

We use a "Run & Report" model. Every ingestion run generates a structured report in the `dq_report` table.

#### 1. CLI Inspection (Quick Triage)

Use the CLI to inspect findings for the latest run:

```bash
# Show findings for the latest run (default)
uv run python -m src.fred_macro.cli dq-report

# Filter by severity
uv run python -m src.fred_macro.cli dq-report --severity critical
uv run python -m src.fred_macro.cli dq-report --severity warning

# Inspect a specific run
uv run python -m src.fred_macro.cli dq-report --run-id <UUID>
```

#### 2. SQL Views (Trend Analysis)

Three views are available for operational dashboards or ad-hoc analysis:

**`dq_report_summary_by_run`**
*High-level health check.*
- **Use for**: Checking if critical errors are spiking over time.
- **Columns**: `run_id`, `critical_count`, `warning_count`, `info_count`.

**`dq_report_trend_by_series`**
*Problem child identification.*
- **Use for**: Finding series that consistently fail checks (e.g., `stale_series_data`).
- **Scope**: Last 30 days.
- **Columns**: `series_id`, `code`, `occurrence_count`, `last_seen`.

**`dq_report_latest_runs`**
*Detailed join.*
- **Use for**: Deep diving into specific errors alongside run context.

---

## Troubleshooting

### Common Errors

| Error Code | Symptom | Severity | Resolution |
|------------|---------|----------|------------|
| `missing_series_data` | "No rows fetched during backfill" | **Critical** | Check if series ID is valid on FRED website. Check API key permissions. |
| `stale_series_data` | "Latest observation is X days old" | Warning | Check FRED release schedule. If series is discontinued, deprecate in catalog. |
| `rapid_change_detected` | "Large latest-period change detected" | Warning | Verify value on FRED. If real, it's a valid signal. If artifact, tune threshold in `validation.py`. |
| `duplicate_observations` | "Found duplicate observations" | **Critical** | Upsert logic failure. Check composite primary key and `ingest.py` logic. |

### Database Issues

**Connection Failed**:
- Check `MOTHERDUCK_TOKEN` environment variable.
- Verify internet connectivity.
- Fallback: Unset token to use local `fred.db` (dev only).

**Foreign Key Violations**:
- Symptom: "Violates foreign key constraint... series_id X does not exist"
- Cause: `config/series_catalog.yaml` has a new series that hasn't been seeded to the DB.
- Fix: Run `uv run python -m src.fred_macro.seed_catalog`.


---

## Automation & Scheduling

The project is configured to run daily data ingestion via **GitHub Actions**.

### GitHub Actions
- **Workflow File**: `.github/workflows/daily_ingest.yml`
- **Schedule**: Daily at 10:00 UTC (6:00 AM ET).
- **Triggers**: Scheduled cron, or manual `workflow_dispatch`.
- **Health Gate**: `run-health` runs after ingestion and fails the workflow when:
  - ingestion status is not `success`
  - critical DQ findings are present
- **Warnings**: warning-level findings are surfaced in output/artifacts but do not fail the workflow.
- **Artifacts**:
  - `artifacts/run-id.txt` for deterministic run targeting in CI
  - `artifacts/run-health.json` for triage context
- **Catalog Sync**: Workflow seeds `series_catalog` from `config/series_catalog.yaml` before ingestion to prevent FK drift.

#### Local Reproduction of Automation Health Check

```bash
# Health summary for latest run
uv run python -m src.fred_macro.cli run-health --run-id latest

# Health summary for a specific run id captured by automation
uv run python -m src.fred_macro.cli run-health --run-id "$(cat artifacts/run-id.txt)"

# Fail locally if run status is not success or critical findings exist
uv run python -m src.fred_macro.cli run-health \
  --run-id latest \
  --fail-on-status \
  --fail-on-critical \
  --output-json artifacts/run-health.json
```

### Secrets Configuration
For the workflow to succeed, the following **Repository Secrets** must be configured in GitHub:

1. Go to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret**.
3. Add the following:

| Secret Name | Value | Purpose |
|-------------|-------|---------|
| `MOTHERDUCK_TOKEN` | (Your Token) | Authentication for MotherDuck database |
| `FRED_API_KEY` | (Your Key) | Authentication for Federal Reserve API |
| `BLS_API_KEY` | (Optional Key) | Higher-throughput access for direct BLS ingestion |
| `CENSUS_API_KEY` | (Your Key) | Authentication for Census Bureau API ingestion |

**Note**: If these secrets are missing or invalid, the `daily_ingest` job will fail.

---

## Maintenance

### Adding New Indicators
1. Edit `config/series_catalog.yaml`.
2. For source-coexistence aliases (for example, `*_BLS`), set:
   - `series_id` to the internal unique alias ID.
   - `source_series_id` to the provider-native API ID used for fetch.
3. Run `uv run python -m src.fred_macro.seed_catalog` to update the DB.
4. Run `uv run python -m src.fred_macro.cli ingest --mode backfill` (upsert is safe).

### Updating DQ Rules
- Edit `src/fred_macro/validation.py`.
- Thresholds are defined in `_check_freshness` (days) and `_check_recent_anomalies` (percent).

---

## Contact & Escalation

- **Owner**: Connor Kitchings
- **Repository**: [FRED-Macro-Dashboard](https://github.com/connorkitchings/FRED)
- **Escalation**: Create a GitHub Issue for persistent failures.
