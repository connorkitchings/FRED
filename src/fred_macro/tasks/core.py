from prefect import task
from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.seed_catalog import seed_catalog
import pandas as pd

@task(name="Seed Catalog", retries=2)
def task_seed_catalog():
    """Seed the series catalog to ensure new series exist in DB."""
    seed_catalog()

@task(name="Ingest Batch", retries=3, retry_delay_seconds=30)
def task_ingest_batch(mode: str = "incremental") -> str:
    """
    Run the ingestion engine for a batch.
    Returns the run_id.
    """
    engine = IngestionEngine()
    # The engine handles its own internal batching/routing.
    # We are wrapping the top-level execution here.
    engine.run(mode=mode)
    return engine.current_run_id

@task(name="Validate Run Health")
def task_validate_run(run_id: str) -> dict:
    """
    Check the health of a completed run.
    Returns a dictionary summary.
    """
    from src.fred_macro.db import get_connection
    
    conn = get_connection()
    try:
        # Get run status
        run_row = conn.execute(
            "SELECT status, error_message FROM ingestion_log WHERE run_id = ?", 
            (run_id,)
        ).fetchone()
        
        status, error = run_row if run_row else ("unknown", "Run not found")
        
        # Get DQ counts
        dq_counts = conn.execute(
            """
            SELECT severity, COUNT(*) 
            FROM dq_report 
            WHERE run_id = ? 
            GROUP BY severity
            """, 
            (run_id,)
        ).fetchall()
        
        dq_map = {row[0]: row[1] for row in dq_counts}
        
        return {
            "run_id": run_id,
            "status": status,
            "error": error,
            "dq_critical": dq_map.get("critical", 0),
            "dq_warning": dq_map.get("warning", 0)
        }
    finally:
        conn.close()
