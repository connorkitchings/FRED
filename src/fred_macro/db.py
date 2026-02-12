import logging
import os
from typing import Optional

import duckdb
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_connection(db_path: str = "md:") -> duckdb.DuckDBPyConnection:
    """
    Establishes a connection to MotherDuck (preferred) or local DuckDB.

    Args:
        db_path: Connection string or path. Defaults to "md:" for MotherDuck.
                 If MOTHERDUCK_TOKEN is not set, falls back to local 'fred.db'.

    Returns:
        duckdb.DuckDBPyConnection: Active database connection.
    """
    token = os.getenv("MOTHERDUCK_TOKEN")

    if token:
        logger.info("Connecting to MotherDuck...")
        try:
            # Connect to MotherDuck with the token
            # Note: duckdb usually picks up the token from environment variable if set
            # but we can explicitly pass it or let the md: syntax handle it
            # if env var is set
            conn = duckdb.connect(f"{db_path}?motherduck_token={token}")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to MotherDuck: {e}")
            raise
    else:
        logger.warning("MOTHERDUCK_TOKEN not found in environment variables.")
        logger.warning("Falling back to local DuckDB file: 'fred.db'")
        return duckdb.connect("fred.db")


def execute_query(query: str, params: Optional[tuple] = None) -> Optional[list]:
    """Execute a query and return results."""
    conn = get_connection()
    try:
        if params:
            return conn.execute(query, params).fetchall()
        else:
            return conn.execute(query).fetchall()
    finally:
        conn.close()
