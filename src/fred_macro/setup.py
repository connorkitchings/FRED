import logging

from src.fred_macro.db import get_connection

logger = logging.getLogger(__name__)


def create_schema():
    """Create the database schema if it does not exist."""
    conn = get_connection()
    try:
        logger.info("Creating schema...")

        # 1. series_catalog
        logger.info("Creating table: series_catalog")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS series_catalog (
                series_id VARCHAR NOT NULL PRIMARY KEY,
                title VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                frequency VARCHAR NOT NULL,
                units VARCHAR NOT NULL,
                seasonal_adjustment VARCHAR,
                tier INTEGER NOT NULL,
                source VARCHAR,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indexes for series_catalog
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_series_tier ON series_catalog(tier);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_series_category ON "
            "series_catalog(category);"
        )

        # 2. observations
        logger.info("Creating table: observations")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                series_id VARCHAR NOT NULL,
                observation_date DATE NOT NULL,
                value DOUBLE,
                load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (series_id, observation_date),
                FOREIGN KEY (series_id) REFERENCES series_catalog(series_id)
            );
        """)

        # 3. ingestion_log
        logger.info("Creating table: ingestion_log")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                run_id VARCHAR NOT NULL PRIMARY KEY,
                run_timestamp TIMESTAMP NOT NULL,
                mode VARCHAR NOT NULL,
                series_ingested JSON NOT NULL,
                total_rows_fetched INTEGER NOT NULL,
                total_rows_inserted INTEGER NOT NULL,
                total_rows_updated INTEGER NOT NULL,
                duration_seconds DOUBLE NOT NULL,
                status VARCHAR NOT NULL,
                error_message TEXT
            );
        """)

        # Index for ingestion_log
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingest_time ON "
            "ingestion_log(run_timestamp);"
        )

        logger.info("Schema creation complete.")

    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_schema()
