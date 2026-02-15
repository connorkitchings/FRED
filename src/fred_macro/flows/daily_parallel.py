import json
import time
import uuid
from pathlib import Path

from prefect import flow, get_run_logger
from prefect.artifacts import create_markdown_artifact

from src.fred_macro.services.catalog import CatalogService
from src.fred_macro.services.writer import DataWriter
from src.fred_macro.tasks.core import (
    task_fetch_single_series,
    task_seed_catalog,
    task_validate_run,
    task_write_dataframe,
)


@flow(name="Daily Ingest Pipeline (Parallel)")
def daily_ingest_flow(mode: str = "incremental", source_filter: str = "FRED"):
    """
    Parallel orchestration:
    1. Seed Catalog
    2. Fan-out Fetch (Concurrent)
    3. Fan-in Write (Sequential)
    4. Log Run & Validate
    """
    logger = get_run_logger()
    run_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(
        f"Starting Parallel Ingest {run_id} | Mode: {mode} | Source: {source_filter}"
    )

    # 1. Seed
    task_seed_catalog()

    # 2. Get Workload
    catalog = CatalogService()
    if source_filter == "ALL":
        series_list = catalog.get_all_series()
    else:
        series_list = catalog.filter_by_source(source_filter)

    logger.info(f"Found {len(series_list)} series to process.")

    # 3. Fan-Out Fetch (Concurrent)
    # We pass dicts to avoid pickling issues with Pydantic objects if using distributed task runners
    series_dicts = [s.model_dump() for s in series_list]

    # .map() submits all tasks at once
    dfs = task_fetch_single_series.map(series_dicts, mode=mode)

    # 4. Fan-In Write (Sequential/Batched)
    # Wait for all fetches to complete, then write
    # Note: In a real distributed system, we might write as they complete,
    # but for DuckDB single-writer, collecting them is safer or using a lock.
    # Prefect futures need to be resolved.

    total_processed = 0
    series_ingested = []

    # Iterate over futures (this blocks until each is ready)
    for i, future in enumerate(dfs):
        try:
            df = future.result()
            if not df.empty:
                count = task_write_dataframe(df)
                total_processed += count
                series_ingested.append(series_list[i].series_id)
        except Exception as e:
            logger.error(f"Task failed for {series_list[i].series_id}: {e}")

    # 5. Log Run (Manually, since we aren't using IngestionEngine)
    writer = DataWriter()
    duration = time.time() - start_time

    writer.log_run(
        run_id=run_id,
        mode=mode,
        series_ingested=series_ingested,
        rows_fetched=total_processed,  # Approximation for now
        rows_processed=total_processed,
        duration=duration,
        status="success",  # Simplified
        error_message=None,
    )

    # 6. Validate
    health = task_validate_run(run_id)

    # 7. Artifacts
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/run-health.json").write_text(json.dumps(health, indent=2))

    status_emoji = "✅" if health["status"] == "success" else "❌"

    create_markdown_artifact(
        key="ingestion-report",
        markdown=f"# {status_emoji} Parallel Ingest\nRun ID: `{run_id}`\nProcessed: {total_processed}",
        description="Parallel Run Report",
    )


if __name__ == "__main__":
    daily_ingest_flow(source_filter="FRED")
