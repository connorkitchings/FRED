import typer

from src.fred_macro.ingest import IngestionEngine
from src.fred_macro.logging_config import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)

app = typer.Typer(help="FRED Macro Dashboard CLI")


@app.command()
def ingest(
    mode: str = typer.Option(
        "incremental",
        help="Ingestion mode: 'incremental' (last 60 days) or 'backfill' (history)",
    ),
):
    """
    Run data ingestion pipeline.
    """
    if mode not in ["incremental", "backfill"]:
        typer.echo(f"Invalid mode: {mode}. Must be 'incremental' or 'backfill'.")
        raise typer.Exit(code=1)

    typer.echo(f"Starting ingestion in {mode} mode...")

    try:
        engine = IngestionEngine()
        engine.run(mode=mode)
        typer.echo("Ingestion run complete.")
    except Exception as e:
        typer.echo(f"Ingestion failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def verify():
    """
    Verify connections and dependencies.
    """
    typer.echo("Verifying connections...")
    # Add verification logic here (DB check, API check)
    try:
        from src.fred_macro.db import get_connection

        conn = get_connection()
        conn.execute("SELECT 1")
        typer.echo("Database connection: OK")

        from src.fred_macro.fred_client import FredClient

        client = FredClient()  # This will fail if no API Key
        typer.echo(f"FRED API Key found: {client.api_key[:4]}...")

    except Exception as e:
        typer.echo(f"Verification failed: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
