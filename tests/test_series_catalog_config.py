from pathlib import Path

import yaml

CATALOG_PATH = Path("config/series_catalog.yaml")

REQUIRED_FIELDS = {
    "series_id",
    "title",
    "units",
    "frequency",
    "seasonal_adjustment",
    "tier",
    "description",
}

TIER1_BIG_FOUR = {"FEDFUNDS", "UNRATE", "CPIAUCSL", "GDPC1"}
TIER2_KICKOFF = {"HOUST", "PERMIT", "CSUSHPISA", "RSXFS", "INDPRO"}
TIER2_BATCH3 = {"AHETPI", "U6RATE", "CPILFESL", "SP500", "DEXUSEU", "BUSLOANS"}
TIER2_BATCH4 = {"T5YIE", "DCOILWTICO", "DTWEXBGS", "NFCI", "WALCL", "SOFR"}
TIER2_BATCH5 = {
    "JTSQUR",
    "JTSHIR",
    "JTSLDR",  # JOLTS Flow Data
    "MANEMP",
    "USCONS",
    "USGOVT",  # Sectoral Employment
    "ECIWAG",
    "ECIALLCIV",
    "ULCNFB",  # Wage/Compensation
    "UEMPMEAN",
    "EMRATIO",  # Unemployment Detail
    "PPIACO",
    "WPSFD49207",  # Producer Prices
    "CUSR0000SAH1",
    "CPIENGSL",  # CPI Components
}


def _load_series() -> list[dict]:
    with CATALOG_PATH.open("r") as f:
        data = yaml.safe_load(f)
    return data["series"]


def test_series_catalog_entries_have_required_fields():
    series_list = _load_series()
    assert series_list, "series_catalog.yaml must include at least one series."
    for item in series_list:
        missing = REQUIRED_FIELDS - set(item.keys())
        assert not missing, (
            f"Missing required fields for {item.get('series_id')}: {missing}"
        )


def test_series_catalog_has_unique_series_ids():
    series_list = _load_series()
    series_ids = [item["series_id"] for item in series_list]
    assert len(series_ids) == len(set(series_ids)), "Duplicate series_id values found."


def test_tier1_big_four_present():
    series_list = _load_series()
    tier1 = {item["series_id"] for item in series_list if item["tier"] == 1}
    assert TIER1_BIG_FOUR.issubset(tier1)


def test_tier2_kickoff_bundle_present():
    series_list = _load_series()
    tier2 = {item["series_id"] for item in series_list if item["tier"] == 2}
    assert TIER2_KICKOFF.issubset(tier2)


def test_tier2_batch3_present():
    series_list = _load_series()
    tier2 = {item["series_id"] for item in series_list if item["tier"] == 2}
    assert TIER2_BATCH3.issubset(tier2)


def test_tier2_batch4_present():
    series_list = _load_series()
    tier2 = {item["series_id"] for item in series_list if item["tier"] == 2}
    assert TIER2_BATCH4.issubset(tier2)


def test_tier2_batch5_present():
    series_list = _load_series()
    tier2 = {item["series_id"] for item in series_list if item["tier"] == 2}
    assert TIER2_BATCH5.issubset(tier2)
