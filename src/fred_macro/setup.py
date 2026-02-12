from src.fred_macro.db import get_connection
from src.fred_macro.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


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

        # 4. dq_report
        logger.info("Creating table: dq_report")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dq_report (
                report_id VARCHAR NOT NULL PRIMARY KEY,
                run_id VARCHAR NOT NULL,
                finding_timestamp TIMESTAMP NOT NULL,
                severity VARCHAR NOT NULL,
                code VARCHAR NOT NULL,
                series_id VARCHAR,
                message TEXT NOT NULL,
                metadata JSON,
                FOREIGN KEY (run_id) REFERENCES ingestion_log(run_id)
            );
        """)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dq_report_run_id ON dq_report(run_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dq_report_severity ON dq_report(severity);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dq_report_time ON "
            "dq_report(finding_timestamp);"
        )

        # 5. dq_report_latest_runs view
        logger.info("Creating view: dq_report_latest_runs")
        conn.execute("""
            CREATE OR REPLACE VIEW dq_report_latest_runs AS
            SELECT
                il.run_id,
                il.run_timestamp,
                il.mode,
                il.status AS run_status,
                il.total_rows_fetched,
                il.total_rows_inserted,
                il.duration_seconds,
                dr.report_id,
                dr.finding_timestamp,
                dr.severity,
                dr.code,
                dr.series_id,
                dr.message,
                dr.metadata
            FROM ingestion_log il
            LEFT JOIN dq_report dr
                ON il.run_id = dr.run_id
            ORDER BY il.run_timestamp DESC, dr.finding_timestamp DESC;
        """)

        # 6. dq_report_summary_by_run view
        logger.info("Creating view: dq_report_summary_by_run")
        conn.execute("""
            CREATE OR REPLACE VIEW dq_report_summary_by_run AS
            SELECT
                il.run_id,
                il.run_timestamp,
                il.mode,
                il.status,
                COUNT(dr.report_id) AS total_findings,
                SUM(CASE WHEN dr.severity = 'critical' THEN 1 ELSE 0 END)
                    AS critical_count,
                SUM(CASE WHEN dr.severity = 'warning' THEN 1 ELSE 0 END)
                    AS warning_count,
                SUM(CASE WHEN dr.severity = 'info' THEN 1 ELSE 0 END)
                    AS info_count
            FROM ingestion_log il
            LEFT JOIN dq_report dr ON il.run_id = dr.run_id
            GROUP BY il.run_id, il.run_timestamp, il.mode, il.status
            ORDER BY il.run_timestamp DESC;
        """)

        # 7. dq_report_trend_by_series view
        logger.info("Creating view: dq_report_trend_by_series")
        conn.execute("""
            CREATE OR REPLACE VIEW dq_report_trend_by_series AS
            SELECT
                dr.series_id,
                dr.code,
                dr.severity,
                COUNT(*) AS occurrence_count,
                MAX(dr.finding_timestamp) AS last_seen,
                MIN(dr.finding_timestamp) AS first_seen
            FROM dq_report dr
            WHERE dr.finding_timestamp >= CURRENT_DATE - INTERVAL '30 days'
              AND dr.series_id IS NOT NULL
            GROUP BY dr.series_id, dr.code, dr.severity
            ORDER BY occurrence_count DESC;
        """)

        logger.info("Schema creation complete.")

    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    setup_logging()
    create_schema()
