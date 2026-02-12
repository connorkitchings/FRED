import logging

import yaml

from src.fred_macro.db import get_connection

logger = logging.getLogger(__name__)


def seed_catalog(config_path: str = "config/series_catalog.yaml"):
    """
    Read series configuration and populate/update series_catalog table.
    """
    conn = get_connection()
    try:
        with open(config_path, "r") as f:
            catalog = yaml.safe_load(f)

        series_list = catalog.get("series", [])
        logger.info(f"Seeding {len(series_list)} series into catalog...")

        for item in series_list:
            # Upsert logic for series_catalog
            # DuckDB supports INSERT OR REPLACE or ON CONFLICT
            query = """
            INSERT INTO series_catalog (
                series_id, title, category, frequency, units,
                seasonal_adjustment, tier, source, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (series_id) DO UPDATE SET
                title = EXCLUDED.title,
                category = 'macro', -- defaulting category
                frequency = EXCLUDED.frequency,
                units = EXCLUDED.units,
                seasonal_adjustment = EXCLUDED.seasonal_adjustment,
                tier = EXCLUDED.tier,
                source = 'FRED',
                notes = EXCLUDED.notes
            """

            # Load config
            # yaml has: series_id, title, units, frequency, seasonal_adjustment, tier, description

            # Let's inspect the yaml structure I created earlier.
            # Step 50:
            # - series_id: "FEDFUNDS"
            #   tier: 1
            #   description: ...

            # Default category to 'Tier X' for now since it's missing in YAML

            params = (
                item["series_id"],
                item["title"],
                "Tier " + str(item["tier"]),  # simplistic category for now
                item["frequency"],
                item["units"],
                item["seasonal_adjustment"],
                item["tier"],
                "FRED",
                item.get("description", ""),
            )

            conn.execute(query, params)

        logger.info("Catalog seeding complete.")

    except Exception as e:
        logger.error(f"Error seeding catalog: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_catalog()
