"""Produce a privacy-preserving baseline audit of Event Tracker SQLite data.

This module intentionally reports only schema-level and aggregate information.
It never emits event names, notes, source event IDs, or individual timestamps.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sqlite3
from statistics import median
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"


def open_readonly_database(database_path: Path) -> sqlite3.Connection:
    """Open an existing SQLite database without write access."""

    resolved_path = database_path.expanduser().resolve()

    if not resolved_path.is_file():
        raise FileNotFoundError(f"Database not found: {resolved_path}")

    connection = sqlite3.connect(
        f"{resolved_path.as_uri()}?mode=ro",
        uri=True,
    )
    connection.execute("PRAGMA query_only = ON")
    connection.row_factory = sqlite3.Row
    return connection


def _one_row(
    connection: sqlite3.Connection,
    query: str,
) -> dict[str, Any]:
    row = connection.execute(query).fetchone()

    if row is None:
        raise RuntimeError("Expected one aggregate row, but query returned none.")

    return dict(row)


def _percentile(values: Sequence[float], proportion: float) -> float | None:
    if not values:
        return None

    position = (len(values) - 1) * proportion
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(values) - 1)
    fraction = position - lower_index

    return (
        values[lower_index] * (1 - fraction)
        + values[upper_index] * fraction
    )


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def build_baseline_report(database_path: Path) -> dict[str, Any]:
    """Return aggregate facts without exposing event content."""

    connection = open_readonly_database(database_path)

    try:
        integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
        integrity = [row[0] for row in integrity_rows]

        corpus = _one_row(
            connection,
            """
            SELECT
                COUNT(*) AS total_events,
                COUNT(source_event_id) AS synchronized_events,
                COUNT(*) - COUNT(source_event_id) AS legacy_events,
                COUNT(DISTINCT source_event_id) AS distinct_source_event_ids
            FROM events
            """,
        )

        event_type_counts = {
            row["event_type"]: row["event_count"]
            for row in connection.execute(
                """
                SELECT event_type, COUNT(*) AS event_count
                FROM events
                GROUP BY event_type
                ORDER BY event_count DESC, event_type
                """
            )
        }

        coverage = _one_row(
            connection,
            """
            SELECT
                COUNT(*) AS active_days,
                MIN(event_day) AS first_event_date,
                MAX(event_day) AS last_event_date,
                ROUND(AVG(events_per_day), 2) AS average_events_per_active_day,
                MIN(events_per_day) AS minimum_events_per_active_day,
                MAX(events_per_day) AS maximum_events_per_active_day
            FROM (
                SELECT date(occurred_at) AS event_day,
                       COUNT(*) AS events_per_day
                FROM events
                GROUP BY date(occurred_at)
            )
            """,
        )

        first_day = coverage["first_event_date"]
        last_day = coverage["last_event_date"]

        if first_day is not None and last_day is not None:
            span_days = (
                date.fromisoformat(last_day) - date.fromisoformat(first_day)
            ).days + 1
        else:
            span_days = 0

        coverage["calendar_span_days"] = span_days
        coverage["zero_event_days_within_span"] = (
            span_days - coverage["active_days"]
        )

        daily_counts = sorted(
            row[0]
            for row in connection.execute(
                """
                SELECT COUNT(*)
                FROM events
                GROUP BY date(occurred_at)
                """
            )
        )
        coverage["median_events_per_active_day"] = (
            round(median(daily_counts), 1) if daily_counts else None
        )
        coverage["p25_events_per_active_day"] = _rounded(
            _percentile(daily_counts, 0.25)
        )
        coverage["p75_events_per_active_day"] = _rounded(
            _percentile(daily_counts, 0.75)
        )

        fields = _one_row(
            connection,
            """
            SELECT
                SUM(CASE WHEN trim(exercise_type) = '' THEN 1 ELSE 0 END)
                    AS blank_event_names,
                SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END)
                    AS amount_null,
                SUM(CASE WHEN unit IS NULL OR trim(unit) = '' THEN 1 ELSE 0 END)
                    AS unit_blank_or_null,
                SUM(CASE WHEN note IS NULL OR trim(note) = '' THEN 1 ELSE 0 END)
                    AS details_blank_or_null,
                SUM(CASE WHEN (amount IS NULL) !=
                    (unit IS NULL OR trim(unit) = '') THEN 1 ELSE 0 END)
                    AS amount_unit_presence_mismatches,
                ROUND(AVG(CASE WHEN note IS NOT NULL THEN length(note) END), 1)
                    AS average_detail_characters,
                MAX(CASE WHEN note IS NOT NULL THEN length(note) END)
                    AS maximum_detail_characters,
                ROUND(AVG(length(exercise_type)), 1)
                    AS average_event_name_characters,
                MAX(length(exercise_type))
                    AS maximum_event_name_characters
            FROM events
            """,
        )

        timestamps = _one_row(
            connection,
            """
            SELECT
                SUM(CASE WHEN julianday(created_at) IS NULL THEN 1 ELSE 0 END)
                    AS invalid_created_at,
                SUM(CASE WHEN julianday(occurred_at) IS NULL THEN 1 ELSE 0 END)
                    AS invalid_occurred_at,
                SUM(CASE WHEN created_at GLOB '*[+-][0-9][0-9]:[0-9][0-9]'
                    OR created_at LIKE '%Z' THEN 0 ELSE 1 END)
                    AS created_at_without_explicit_offset,
                SUM(CASE WHEN occurred_at GLOB '*[+-][0-9][0-9]:[0-9][0-9]'
                    OR occurred_at LIKE '%Z' THEN 0 ELSE 1 END)
                    AS occurred_at_without_explicit_offset,
                SUM(CASE WHEN julianday(occurred_at) >
                    julianday(created_at) + (5.0 / 1440.0) THEN 1 ELSE 0 END)
                    AS occurred_more_than_five_minutes_after_creation,
                SUM(CASE WHEN julianday(created_at) - julianday(occurred_at)
                    >= (1.0 / 24.0) THEN 1 ELSE 0 END)
                    AS logged_at_least_one_hour_late,
                SUM(CASE WHEN julianday(created_at) - julianday(occurred_at)
                    >= 1.0 THEN 1 ELSE 0 END)
                    AS logged_at_least_one_day_late
            FROM events
            """,
        )

        capture_lags = sorted(
            row[0]
            for row in connection.execute(
                """
                SELECT (julianday(created_at) - julianday(occurred_at)) * 1440.0
                FROM events
                WHERE julianday(created_at) IS NOT NULL
                  AND julianday(occurred_at) IS NOT NULL
                """
            )
        )
        timestamps["capture_lag_minutes"] = {
            "p50": _rounded(_percentile(capture_lags, 0.50)),
            "p90": _rounded(_percentile(capture_lags, 0.90)),
            "p95": _rounded(_percentile(capture_lags, 0.95)),
            "p99": _rounded(_percentile(capture_lags, 0.99)),
            "minimum": _rounded(min(capture_lags) if capture_lags else None),
            "maximum": _rounded(max(capture_lags) if capture_lags else None),
        }

        density = _one_row(
            connection,
            """
            WITH ordered AS (
                SELECT
                    julianday(occurred_at) AS occurred,
                    lag(julianday(occurred_at)) OVER (
                        ORDER BY julianday(occurred_at), id
                    ) AS prior_occurred
                FROM events
            ),
            gaps AS (
                SELECT (occurred - prior_occurred) * 1440.0 AS gap_minutes
                FROM ordered
                WHERE prior_occurred IS NOT NULL
            )
            SELECT
                COUNT(*) AS adjacent_pairs,
                SUM(CASE WHEN gap_minutes <= 1.0 THEN 1 ELSE 0 END)
                    AS within_one_minute,
                SUM(CASE WHEN gap_minutes <= 5.0 THEN 1 ELSE 0 END)
                    AS within_five_minutes,
                SUM(CASE WHEN gap_minutes <= 15.0 THEN 1 ELSE 0 END)
                    AS within_fifteen_minutes
            FROM gaps
            """,
        )

        duplicates = _one_row(
            connection,
            """
            SELECT
                COUNT(*) AS exact_content_duplicate_groups,
                COALESCE(SUM(group_count - 1), 0)
                    AS excess_rows_in_exact_content_groups
            FROM (
                SELECT COUNT(*) AS group_count
                FROM events
                GROUP BY
                    created_at,
                    occurred_at,
                    event_type,
                    exercise_type,
                    amount,
                    unit,
                    note
                HAVING COUNT(*) > 1
            )
            """,
        )

        return {
            "report_version": 1,
            "privacy": {
                "contains_event_names": False,
                "contains_event_details": False,
                "contains_source_event_ids": False,
                "contains_individual_timestamps": False,
            },
            "database": {
                "integrity": integrity,
                "file_size_bytes": database_path.stat().st_size,
                "read_only": True,
            },
            "corpus": {
                **corpus,
                "event_type_counts": event_type_counts,
            },
            "coverage": coverage,
            "field_usage": fields,
            "timestamp_quality": timestamps,
            "event_density": density,
            "duplicate_candidates": duplicates,
            "derived_aliases": {
                "event_name": "events.exercise_type",
                "details": "events.note",
            },
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Event Tracker using aggregate, privacy-preserving, "
            "read-only queries."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="Path to event_tracker.db.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = build_baseline_report(args.database)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
