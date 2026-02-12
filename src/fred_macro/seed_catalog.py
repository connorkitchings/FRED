import yaml

from src.fred_macro.db import get_connection
from src.fred_macro.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def _default_category_for_tier(tier: int) -> str:
    if tier == 1:
        return "core"
    if tier == 2:
        return "extended"
    return f"tier_{tier}"


def seed_catalog(config_path: str = "config/series_catalog.yaml"):
    """
    Read series configuration and populate missing rows in series_catalog.

    Existing rows are left unchanged to avoid DuckDB foreign-key update
    limitations when observations already reference a series_id.
    """
    conn = get_connection()
    try:
        with open(config_path, "r") as f:
            catalog = yaml.safe_load(f)

        series_list = catalog.get("series", [])
        logger.info(f"Seeding {len(series_list)} series into catalog...")
        inserted = 0
        skipped_existing = 0

        insert_query = """
        INSERT INTO series_catalog (
            series_id, title, category, frequency, units,
            seasonal_adjustment, tier, source, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        for item in series_list:
            series_id = item["series_id"]
            tier = item["tier"]
            category = item.get("category", _default_category_for_tier(tier))
            source = item.get("source", "FRED")
            notes = item.get("description", "")

            exists = conn.execute(
                "SELECT 1 FROM series_catalog WHERE series_id = ? LIMIT 1",
                (series_id,),
            ).fetchone()

            if exists:
                skipped_existing += 1
            else:
                conn.execute(
                    insert_query,
                    (
                        series_id,
                        item["title"],
                        category,
                        item["frequency"],
                        item["units"],
                        item["seasonal_adjustment"],
                        tier,
                        source,
                        notes,
                    ),
                )
                inserted += 1

        logger.info(
            "Catalog seeding complete. Inserted: %s, Skipped existing: %s",
            inserted,
            skipped_existing,
        )

    except Exception as e:
        logger.error(f"Error seeding catalog: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    setup_logging()
    seed_catalog()
