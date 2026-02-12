from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Literal, Optional

from src.fred_macro.db import get_connection

Severity = Literal["info", "warning", "critical"]


@dataclass(frozen=True)
class ValidationFinding:
    severity: Severity
    code: str
    message: str
    series_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def run_data_quality_checks(
    mode: str,
    configured_series: List[Dict],
    run_series_stats: Dict[str, Dict[str, int]],
) -> List[ValidationFinding]:
    findings: List[ValidationFinding] = []
    expected_series_ids = [item["series_id"] for item in configured_series]

    findings.extend(
        _check_missing_required_series(mode, expected_series_ids, run_series_stats)
    )
    findings.extend(_check_duplicate_observations())
    findings.extend(_check_freshness(expected_series_ids))
    findings.extend(_check_recent_anomalies(expected_series_ids))

    return findings


def count_findings_by_severity(findings: Iterable[ValidationFinding]) -> Dict[str, int]:
    counts = {"info": 0, "warning": 0, "critical": 0}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def summarize_findings(findings: List[ValidationFinding], max_items: int = 5) -> str:
    if not findings:
        return "No findings."

    rendered = []
    for finding in findings[:max_items]:
        if finding.series_id:
            rendered.append(f"{finding.code}({finding.series_id})")
        else:
            rendered.append(finding.code)

    summary = ", ".join(rendered)
    if len(findings) > max_items:
        summary += f", +{len(findings) - max_items} more"
    return summary


def _check_missing_required_series(
    mode: str,
    expected_series_ids: List[str],
    run_series_stats: Dict[str, Dict[str, int]],
) -> List[ValidationFinding]:
    findings: List[ValidationFinding] = []

    if mode == "backfill":
        for series_id in expected_series_ids:
            rows_fetched = run_series_stats.get(series_id, {}).get("rows_fetched", 0)
            if rows_fetched == 0:
                findings.append(
                    ValidationFinding(
                        severity="critical",
                        code="missing_series_data",
                        message="No rows fetched during backfill for required series.",
                        series_id=series_id,
                        metadata={"mode": mode, "rows_fetched": rows_fetched},
                    )
                )
        return findings

    total_fetched = sum(
        run_series_stats.get(series_id, {}).get("rows_fetched", 0)
        for series_id in expected_series_ids
    )
    if total_fetched == 0:
        findings.append(
            ValidationFinding(
                severity="warning",
                code="incremental_no_new_rows",
                message="Incremental run fetched no rows for all configured series.",
                metadata={"mode": mode, "total_fetched": total_fetched},
            )
        )
    return findings


def _check_duplicate_observations() -> List[ValidationFinding]:
    conn = get_connection()
    try:
        duplicates = conn.execute("""
            SELECT series_id, observation_date, COUNT(*) AS duplicate_count
            FROM observations
            GROUP BY series_id, observation_date
            HAVING COUNT(*) > 1
            LIMIT 5
        """).fetchall()
    finally:
        conn.close()

    findings: List[ValidationFinding] = []
    for series_id, _, duplicate_count in duplicates:
        findings.append(
            ValidationFinding(
                severity="critical",
                code="duplicate_observations",
                message=f"Found duplicate observations (count={duplicate_count}).",
                series_id=series_id,
                metadata={"duplicate_count": duplicate_count},
            )
        )
    return findings


def _check_freshness(expected_series_ids: List[str]) -> List[ValidationFinding]:
    if not expected_series_ids:
        return []

    placeholders = ", ".join(["?"] * len(expected_series_ids))
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            WITH latest AS (
                SELECT series_id, MAX(observation_date) AS max_date
                FROM observations
                GROUP BY series_id
            )
            SELECT
                sc.series_id,
                sc.frequency,
                latest.max_date
            FROM series_catalog sc
            LEFT JOIN latest ON latest.series_id = sc.series_id
            WHERE sc.series_id IN ({placeholders})
            ORDER BY sc.series_id
            """,
            expected_series_ids,
        ).fetchall()
    finally:
        conn.close()

    findings: List[ValidationFinding] = []
    today = date.today()

    for series_id, frequency, max_date in rows:
        if max_date is None:
            findings.append(
                ValidationFinding(
                    severity="warning",
                    code="series_has_no_observations",
                    message="Series has no observations in the database.",
                    series_id=series_id,
                    metadata={"frequency": frequency},
                )
            )
            continue

        age_days = (today - max_date).days
        threshold = _freshness_threshold_days(frequency)
        if age_days > threshold:
            findings.append(
                ValidationFinding(
                    severity="warning",
                    code="stale_series_data",
                    message=(
                        f"Latest observation is {age_days} days old "
                        f"(threshold {threshold})."
                    ),
                    series_id=series_id,
                    metadata={
                        "age_days": age_days,
                        "threshold_days": threshold,
                        "frequency": frequency,
                    },
                )
            )

    return findings


def _check_recent_anomalies(expected_series_ids: List[str]) -> List[ValidationFinding]:
    if not expected_series_ids:
        return []

    placeholders = ", ".join(["?"] * len(expected_series_ids))
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            WITH ranked AS (
                SELECT
                    series_id,
                    observation_date,
                    value,
                    ROW_NUMBER() OVER (
                        PARTITION BY series_id
                        ORDER BY observation_date DESC
                    ) AS rn
                FROM observations
                WHERE series_id IN ({placeholders})
            ),
            latest_two AS (
                SELECT
                    series_id,
                    MAX(CASE WHEN rn = 1 THEN value END) AS latest_value,
                    MAX(CASE WHEN rn = 2 THEN value END) AS previous_value
                FROM ranked
                WHERE rn <= 2
                GROUP BY series_id
            )
            SELECT series_id, latest_value, previous_value
            FROM latest_two
            ORDER BY series_id
            """,
            expected_series_ids,
        ).fetchall()
    finally:
        conn.close()

    findings: List[ValidationFinding] = []
    for series_id, latest_value, previous_value in rows:
        if latest_value is None or previous_value in (None, 0):
            continue

        # Skip check for small-base numbers to avoid noise (e.g. 0.1 -> 0.2 is 100% but small impact)
        if abs(previous_value) < 0.1:
            continue

        pct_change = abs((latest_value - previous_value) / abs(previous_value)) * 100.0
        if pct_change > 100.0:
            findings.append(
                ValidationFinding(
                    severity="warning",
                    code="rapid_change_detected",
                    message=f"Large latest-period change detected ({pct_change:.2f}%).",
                    series_id=series_id,
                    metadata={"pct_change": round(pct_change, 4)},
                )
            )

    return findings


def _freshness_threshold_days(frequency: str) -> int:
    normalized = (frequency or "").strip().lower()

    if normalized.startswith("d"):
        return 10
    if normalized.startswith("w"):
        return 28
    if normalized.startswith("m"):
        return 90
    if normalized.startswith("q"):
        return 200
    if normalized.startswith("a"):
        return 550

    return 180
