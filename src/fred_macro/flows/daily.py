from prefect import flow, get_run_logger
from prefect.artifacts import create_markdown_artifact
from src.fred_macro.tasks.core import task_seed_catalog, task_ingest_batch, task_validate_run
import json
from pathlib import Path

@flow(name="Daily Ingest Pipeline")
def daily_ingest_flow(mode: str = "incremental"):
    """
    Orchestrates the daily data pipeline:
    1. Seeds catalog (schema updates)
    2. Runs ingestion (fetch + upsert)
    3. Validates health
    """
    logger = get_run_logger()
    logger.info(f"Starting Daily Ingest Flow in {mode} mode")

    # 1. Seed Catalog
    task_seed_catalog()

    # 2. Ingest
    run_id = task_ingest_batch(mode=mode)
    
    # 3. Validate
    health = task_validate_run(run_id)
    
    # 4. Persist Artifacts (Local JSON for CI)
    # Ensure artifacts dir exists
    Path("artifacts").mkdir(exist_ok=True)
    health_file = Path("artifacts/run-health.json")
    health_file.write_text(json.dumps(health, indent=2))
    logger.info(f"Wrote health summary to {health_file}")

    # 5. Reporting (Prefect UI)
    status_emoji = "✅" if health["status"] == "success" else "❌"
    if health["dq_critical"] > 0:
        status_emoji = "⚠️"
        
    report = f"""
# {status_emoji} Ingestion Report

**Run ID**: `{run_id}`
**Status**: {health['status']}
**Mode**: {mode}

## Data Quality
- **Critical Issues**: {health['dq_critical']}
- **Warnings**: {health['dq_warning']}

## Errors
{health['error'] if health['error'] else "None"}
    """
    
    create_markdown_artifact(
        key="ingestion-report",
        markdown=report,
        description=f"Report for run {run_id}"
    )
    
    if health["status"] != "success" or health["dq_critical"] > 0:
        raise RuntimeError(f"Pipeline failed health check: {health}")

if __name__ == "__main__":
    daily_ingest_flow()
