"""Build the aggregate-only Daily Context Explorer response."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sqlite3
from typing import Any


_BLANK_EVENT_NAME = "(blank)"
_MAXIMUM_RANGE_DAYS = 90
_READ_FAILURE_MESSAGE = "Daily Context data could not be read."


def _validate_preconditions(
    database_path: Path,
    start: date,
    end: date,
    selected_date: date,
) -> int:
    if not isinstance(database_path, Path):
        raise TypeError("database_path must be a Path.")

    for field_name, value in (
        ("start", start),
        ("end", end),
        ("selected_date", selected_date),
    ):
        if type(value) is not date:
            raise TypeError(f"{field_name} must be a date.")

    if start > end:
        raise ValueError("start must not be after end.")

    calendar_day_count = (end - start).days + 1

    if calendar_day_count > _MAXIMUM_RANGE_DAYS:
        raise ValueError("The inclusive range must contain 1 through 90 days.")

    if not start <= selected_date <= end:
        raise ValueError("selected_date must be inside the inclusive range.")

    return calendar_day_count


def _open_readonly_database(database_path: Path) -> sqlite3.Connection:
    try:
        resolved_path = database_path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise FileNotFoundError("Database file was not found.") from None

    if not resolved_path.is_file():
        raise FileNotFoundError("Database file was not found.")

    connection: sqlite3.Connection | None = None

    try:
        connection = sqlite3.connect(
            f"{resolved_path.as_uri()}?mode=ro",
            uri=True,
        )
        connection.execute("PRAGMA query_only = ON")
        connection.row_factory = sqlite3.Row
        return connection
    except (OSError, sqlite3.Error, ValueError):
        if connection is not None:
            connection.close()

        raise RuntimeError(_READ_FAILURE_MESSAGE) from None


def _parse_stored_local_date(value: object) -> date | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None

    normalized_value = (
        f"{value[:-1]}+00:00"
        if value.endswith("Z")
        else value
    )

    try:
        return datetime.fromisoformat(normalized_value).date()
    except ValueError:
        return None


def _event_name_label(value: object) -> tuple[str, bool]:
    if value is None:
        return _BLANK_EVENT_NAME, True

    if not isinstance(value, str):
        raise RuntimeError(_READ_FAILURE_MESSAGE)

    if not value or not value.strip():
        return _BLANK_EVENT_NAME, True

    return value, False


def _round_half_up(
    numerator: int,
    denominator: int,
    decimal_places: int,
) -> float:
    quantum = Decimal(1).scaleb(-decimal_places)
    value = Decimal(numerator) / Decimal(denominator)
    return float(value.quantize(quantum, rounding=ROUND_HALF_UP))


def _sorted_event_name_totals(
    counts: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "event_count": event_count,
        }
        for label, event_count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def _verify_contract_invariants(report: dict[str, Any]) -> None:
    try:
        days = report["days"]
        summary = report["summary"]
        selected_day = report["selected_day"]
        range_start = date.fromisoformat(report["range"]["start"])
        calendar_day_count = report["range"]["calendar_day_count"]

        event_count = summary["event_count"]
        daily_total = sum(day["event_count"] for day in days)
        day_dates = [day["date"] for day in days]
        expected_dates = [
            (range_start + timedelta(days=offset)).isoformat()
            for offset in range(calendar_day_count)
        ]
        calculated_days_with_logs = sum(
            day["event_count"] > 0
            for day in days
        )
        window_name_total = sum(
            item["event_count"]
            for item in report["event_name_totals"]
        )
        matching_days = [
            day
            for day in days
            if day["date"] == selected_day["date"]
        ]
        selected_name_total = sum(
            item["event_count"]
            for item in selected_day["event_name_totals"]
        )

        valid = (
            day_dates == expected_dates
            and summary["days_with_logged_events"]
            == calculated_days_with_logs
            and summary["days_with_logged_events"]
            + summary["days_without_logged_events"]
            == calendar_day_count
            and event_count == daily_total == window_name_total
            and all(
                item["event_count"] > 0
                for item in report["event_name_totals"]
            )
            and len(matching_days) == 1
            and selected_day["event_count"]
            == matching_days[0]["event_count"]
            == selected_name_total
            and all(
                item["event_count"] > 0
                for item in selected_day["event_name_totals"]
            )
        )
    except (KeyError, TypeError, ValueError):
        valid = False

    if not valid:
        raise RuntimeError("Daily Context aggregate invariants failed.")


def build_daily_context_report(
    database_path: Path,
    *,
    start: date,
    end: date,
    selected_date: date,
) -> dict[str, Any]:
    """Return the complete successful Daily Context v0.1 aggregate."""

    calendar_day_count = _validate_preconditions(
        database_path,
        start,
        end,
        selected_date,
    )
    day_counts = {
        start + timedelta(days=offset): 0
        for offset in range(calendar_day_count)
    }
    window_name_counts: dict[str, int] = {}
    selected_name_counts: dict[str, int] = {}
    invalid_occurred_at_count = 0
    blank_event_name_count = 0

    connection = _open_readonly_database(database_path)

    try:
        try:
            rows = connection.execute(
                """
                SELECT occurred_at, exercise_type
                FROM events
                """
            )

            for row in rows:
                occurred_date = _parse_stored_local_date(row["occurred_at"])

                if occurred_date is None:
                    invalid_occurred_at_count += 1
                    continue

                if occurred_date not in day_counts:
                    continue

                label, is_blank = _event_name_label(row["exercise_type"])
                day_counts[occurred_date] += 1
                window_name_counts[label] = (
                    window_name_counts.get(label, 0) + 1
                )

                if is_blank:
                    blank_event_name_count += 1

                if occurred_date == selected_date:
                    selected_name_counts[label] = (
                        selected_name_counts.get(label, 0) + 1
                    )
        except sqlite3.Error:
            raise RuntimeError(_READ_FAILURE_MESSAGE) from None
    finally:
        connection.close()

    days = [
        {
            "date": event_date.isoformat(),
            "event_count": event_count,
        }
        for event_date, event_count in day_counts.items()
    ]
    event_count = sum(day_counts.values())
    days_with_logged_events = sum(
        event_count_for_day > 0
        for event_count_for_day in day_counts.values()
    )
    days_without_logged_events = (
        calendar_day_count - days_with_logged_events
    )
    logging_coverage_ratio = _round_half_up(
        days_with_logged_events,
        calendar_day_count,
        4,
    )
    average_events_per_logged_day = (
        _round_half_up(event_count, days_with_logged_events, 2)
        if days_with_logged_events
        else None
    )
    selected_event_count = day_counts[selected_date]

    report: dict[str, Any] = {
        "contract_version": "daily-context.v1",
        "range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "selected_date": selected_date.isoformat(),
            "calendar_day_count": calendar_day_count,
            "calendar_basis": "stored-local-date",
        },
        "summary": {
            "event_count": event_count,
            "days_with_logged_events": days_with_logged_events,
            "days_without_logged_events": days_without_logged_events,
            "logging_coverage_ratio": logging_coverage_ratio,
            "average_events_per_logged_day": (
                average_events_per_logged_day
            ),
        },
        "days": days,
        "event_name_totals": _sorted_event_name_totals(
            window_name_counts
        ),
        "selected_day": {
            "date": selected_date.isoformat(),
            "event_count": selected_event_count,
            "event_name_totals": _sorted_event_name_totals(
                selected_name_counts
            ),
        },
        "quality": {
            "invalid_occurred_at_count": invalid_occurred_at_count,
            "invalid_occurred_at_scope": "corpus",
            "blank_event_name_count": blank_event_name_count,
            "blank_event_name_scope": "window",
            "timezone_history_available": False,
        },
        "privacy": {
            "aggregate_only": True,
            "includes_event_name_labels": True,
            "includes_details": False,
            "includes_identifiers": False,
            "includes_individual_timestamps": False,
        },
    }

    _verify_contract_invariants(report)
    return report
