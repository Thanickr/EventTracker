import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from analysis.baseline import build_baseline_report, open_readonly_database


SCHEMA = """
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_event_id TEXT,
    created_at TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    exercise_type TEXT NOT NULL,
    amount REAL,
    unit TEXT,
    note TEXT
);
CREATE UNIQUE INDEX idx_events_source_event_id
ON events(source_event_id)
WHERE source_event_id IS NOT NULL;
"""


class BaselineAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = self._create_database(
            "event_tracker.db",
            [
                (
                    "source-1",
                    "2026-08-10T08:00:00",
                    "2026-08-10T08:00:00",
                    "event",
                    "Private sample name",
                    None,
                    None,
                    "Private sample details",
                ),
                (
                    "source-2",
                    "2026-08-10T09:05:00",
                    "2026-08-10T09:00:00",
                    "event",
                    "Another private name",
                    None,
                    None,
                    None,
                ),
                (
                    None,
                    "2026-08-11T07:00:00",
                    "2026-08-11T07:00:00",
                    "exercise",
                    "Legacy private name",
                    1.0,
                    "mile",
                    None,
                ),
            ],
        )

    def _create_database(
        self,
        filename: str,
        events: list[tuple[object, ...]] | None = None,
    ) -> Path:
        database_path = (
            Path(self.temporary_directory.name) / filename
        )
        connection = sqlite3.connect(database_path)

        try:
            connection.executescript(SCHEMA)

            if events:
                connection.executemany(
                    """
                    INSERT INTO events (
                        source_event_id,
                        created_at,
                        occurred_at,
                        event_type,
                        exercise_type,
                        amount,
                        unit,
                        note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    events,
                )

            connection.commit()
        finally:
            connection.close()

        return database_path

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_report_is_aggregate_and_content_free(self) -> None:
        report = build_baseline_report(self.database_path)

        self.assertEqual(report["database"]["integrity"], ["ok"])
        self.assertEqual(report["corpus"]["total_events"], 3)
        self.assertEqual(report["corpus"]["legacy_events"], 1)
        self.assertEqual(report["coverage"]["active_days"], 2)
        self.assertEqual(
            report["derived_aliases"]["event_name"],
            "events.exercise_type",
        )

        serialized = str(report)
        self.assertNotIn("Private sample name", serialized)
        self.assertNotIn("Private sample details", serialized)
        self.assertNotIn("source-1", serialized)
        self.assertNotIn("2026-08-10T08:00:00", serialized)

    def test_database_connection_rejects_writes(self) -> None:
        connection = open_readonly_database(self.database_path)

        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM events")
        finally:
            connection.close()

    def test_empty_database_reports_zero_counts(self) -> None:
        database_path = self._create_database("empty.db")
        report = build_baseline_report(database_path)

        self.assertEqual(report["corpus"]["total_events"], 0)
        self.assertEqual(report["coverage"]["active_days"], 0)
        self.assertEqual(report["coverage"]["calendar_span_days"], 0)
        self.assertEqual(
            report["coverage"]["zero_event_days_within_span"],
            0,
        )
        self.assertIsNone(report["coverage"]["first_event_date"])
        self.assertIsNone(report["coverage"]["last_event_date"])

        count_fields = {
            "synchronized_events": report["corpus"][
                "synchronized_events"
            ],
            "legacy_events": report["corpus"]["legacy_events"],
            "distinct_source_event_ids": report["corpus"][
                "distinct_source_event_ids"
            ],
            "blank_event_names": report["field_usage"][
                "blank_event_names"
            ],
            "amount_null": report["field_usage"]["amount_null"],
            "unit_blank_or_null": report["field_usage"][
                "unit_blank_or_null"
            ],
            "details_blank_or_null": report["field_usage"][
                "details_blank_or_null"
            ],
            "amount_unit_presence_mismatches": report["field_usage"][
                "amount_unit_presence_mismatches"
            ],
            "invalid_created_at": report["timestamp_quality"][
                "invalid_created_at"
            ],
            "invalid_occurred_at": report["timestamp_quality"][
                "invalid_occurred_at"
            ],
            "created_at_without_explicit_offset": report[
                "timestamp_quality"
            ]["created_at_without_explicit_offset"],
            "occurred_at_without_explicit_offset": report[
                "timestamp_quality"
            ]["occurred_at_without_explicit_offset"],
            "occurred_more_than_five_minutes_after_creation": report[
                "timestamp_quality"
            ]["occurred_more_than_five_minutes_after_creation"],
            "logged_at_least_one_hour_late": report[
                "timestamp_quality"
            ]["logged_at_least_one_hour_late"],
            "logged_at_least_one_day_late": report[
                "timestamp_quality"
            ]["logged_at_least_one_day_late"],
            "adjacent_pairs": report["event_density"]["adjacent_pairs"],
            "within_one_minute": report["event_density"][
                "within_one_minute"
            ],
            "within_five_minutes": report["event_density"][
                "within_five_minutes"
            ],
            "within_fifteen_minutes": report["event_density"][
                "within_fifteen_minutes"
            ],
            "exact_content_duplicate_groups": report[
                "duplicate_candidates"
            ]["exact_content_duplicate_groups"],
            "excess_rows_in_exact_content_groups": report[
                "duplicate_candidates"
            ]["excess_rows_in_exact_content_groups"],
        }

        for field_name, value in count_fields.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(value, 0)
                self.assertIsInstance(value, int)

    def test_invalid_timestamps_do_not_count_as_active_days(self) -> None:
        database_path = self._create_database(
            "invalid-only.db",
            [
                (
                    None,
                    "2026-08-10T08:00:00",
                    "not-a-timestamp",
                    "event",
                    "Synthetic invalid timestamp",
                    None,
                    None,
                    None,
                ),
            ],
        )
        report = build_baseline_report(database_path)

        self.assertEqual(report["coverage"]["active_days"], 0)
        self.assertEqual(report["coverage"]["calendar_span_days"], 0)
        self.assertEqual(
            report["coverage"]["zero_event_days_within_span"],
            0,
        )
        self.assertIsNone(report["coverage"]["first_event_date"])
        self.assertIsNone(report["coverage"]["last_event_date"])
        self.assertEqual(
            report["timestamp_quality"]["invalid_occurred_at"],
            1,
        )

    def test_invalid_rows_do_not_change_valid_coverage(self) -> None:
        valid_events = [
            (
                None,
                "2026-08-10T08:00:00",
                "2026-08-10T08:00:00",
                "event",
                "Synthetic valid day one",
                None,
                None,
                None,
            ),
            (
                None,
                "2026-08-12T08:00:00",
                "2026-08-12T08:00:00",
                "event",
                "Synthetic valid day three",
                None,
                None,
                None,
            ),
        ]
        invalid_event = (
            None,
            "2026-08-11T08:00:00",
            "not-a-timestamp",
            "event",
            "Synthetic invalid timestamp",
            None,
            None,
            None,
        )
        valid_path = self._create_database(
            "valid-coverage.db",
            valid_events,
        )
        mixed_path = self._create_database(
            "mixed-coverage.db",
            [*valid_events, invalid_event],
        )

        valid_report = build_baseline_report(valid_path)
        mixed_report = build_baseline_report(mixed_path)

        self.assertEqual(mixed_report["coverage"], valid_report["coverage"])
        self.assertEqual(mixed_report["coverage"]["active_days"], 2)
        self.assertEqual(mixed_report["coverage"]["calendar_span_days"], 3)
        self.assertEqual(
            mixed_report["coverage"]["zero_event_days_within_span"],
            1,
        )
        self.assertGreaterEqual(
            mixed_report["coverage"]["zero_event_days_within_span"],
            0,
        )
        self.assertEqual(
            mixed_report["timestamp_quality"]["invalid_occurred_at"],
            1,
        )

    def test_expanded_database_path_is_used_for_file_metadata(self) -> None:
        database_path = self._create_database("expanded-path.db")
        environment = {
            "HOME": self.temporary_directory.name,
            "USERPROFILE": self.temporary_directory.name,
        }

        with patch.dict(os.environ, environment):
            report = build_baseline_report(
                Path("~/expanded-path.db")
            )

        self.assertEqual(
            report["database"]["file_size_bytes"],
            database_path.stat().st_size,
        )


if __name__ == "__main__":
    unittest.main()
