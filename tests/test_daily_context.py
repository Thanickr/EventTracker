from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
import importlib
from io import StringIO
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import analysis.daily_context as daily_context
from analysis.baseline import build_baseline_report
from analysis.daily_context import build_daily_context_report


SCHEMA = """
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_event_id TEXT,
    created_at TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    exercise_type TEXT,
    amount REAL,
    unit TEXT,
    note TEXT
);
"""


class DailyContextAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.start = date(2026, 1, 1)
        self.end = date(2026, 1, 5)
        self.selected_date = date(2026, 1, 3)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _create_database(
        self,
        filename: str = "synthetic.db",
        events: list[tuple[object, object]] | None = None,
    ) -> Path:
        database_path = Path(self.temporary_directory.name) / filename
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
                    ) VALUES (NULL, ?, ?, 'event', ?, NULL, NULL, NULL)
                    """,
                    [
                        (
                            "2026-01-01T00:00:00",
                            occurred_at,
                            event_name,
                        )
                        for occurred_at, event_name in events
                    ],
                )

            connection.commit()
        finally:
            connection.close()

        return database_path

    def _build_report(
        self,
        database_path: Path,
        *,
        start: date | None = None,
        end: date | None = None,
        selected_date: date | None = None,
    ) -> dict[str, object]:
        return build_daily_context_report(
            database_path,
            start=start or self.start,
            end=end or self.end,
            selected_date=selected_date or self.selected_date,
        )

    def _assert_aggregate_invariants(
        self,
        report: dict[str, object],
    ) -> None:
        summary = report["summary"]
        days = report["days"]
        window_names = report["event_name_totals"]
        selected_day = report["selected_day"]

        self.assertEqual(
            summary["event_count"],
            sum(day["event_count"] for day in days),
        )
        self.assertEqual(
            summary["event_count"],
            sum(item["event_count"] for item in window_names),
        )
        matching_day = next(
            day
            for day in days
            if day["date"] == selected_day["date"]
        )
        self.assertEqual(
            selected_day["event_count"],
            matching_day["event_count"],
        )
        self.assertEqual(
            selected_day["event_count"],
            sum(
                item["event_count"]
                for item in selected_day["event_name_totals"]
            ),
        )

    def test_empty_database_returns_zero_filled_contract(self) -> None:
        report = self._build_report(self._create_database())

        self.assertEqual(report["contract_version"], "daily-context.v1")
        self.assertEqual(
            report["range"],
            {
                "start": "2026-01-01",
                "end": "2026-01-05",
                "selected_date": "2026-01-03",
                "calendar_day_count": 5,
                "calendar_basis": "stored-local-date",
            },
        )
        self.assertEqual(
            report["summary"],
            {
                "event_count": 0,
                "days_with_logged_events": 0,
                "days_without_logged_events": 5,
                "logging_coverage_ratio": 0.0,
                "average_events_per_logged_day": None,
            },
        )
        self.assertEqual(
            report["days"],
            [
                {"date": f"2026-01-0{day}", "event_count": 0}
                for day in range(1, 6)
            ],
        )
        self.assertEqual(report["event_name_totals"], [])
        self.assertEqual(
            report["selected_day"],
            {
                "date": "2026-01-03",
                "event_count": 0,
                "event_name_totals": [],
            },
        )
        self.assertEqual(
            report["quality"],
            {
                "invalid_occurred_at_count": 0,
                "invalid_occurred_at_scope": "corpus",
                "blank_event_name_count": 0,
                "blank_event_name_scope": "window",
                "timezone_history_available": False,
            },
        )
        self.assertEqual(
            report["privacy"],
            {
                "aggregate_only": True,
                "includes_event_name_labels": True,
                "includes_details": False,
                "includes_identifiers": False,
                "includes_individual_timestamps": False,
            },
        )
        self.assertIs(type(report["summary"]["event_count"]), int)
        self.assertIs(
            type(report["summary"]["logging_coverage_ratio"]),
            float,
        )
        self._assert_aggregate_invariants(report)

    def test_window_without_valid_events_is_zero_filled(self) -> None:
        database_path = self._create_database(
            events=[("2025-12-31T23:59:59", "Synthetic outside")]
        )
        report = self._build_report(database_path)

        self.assertEqual(report["summary"]["event_count"], 0)
        self.assertEqual(report["event_name_totals"], [])
        self.assertTrue(
            all(day["event_count"] == 0 for day in report["days"])
        )
        self._assert_aggregate_invariants(report)

    def test_invalid_only_corpus_reports_quality_only(self) -> None:
        database_path = self._create_database(
            events=[
                ("not-a-timestamp", "Synthetic invalid one"),
                (" 2026-01-03T10:00:00", "Synthetic invalid two"),
            ]
        )
        report = self._build_report(database_path)

        self.assertEqual(report["summary"]["event_count"], 0)
        self.assertEqual(
            report["quality"]["invalid_occurred_at_count"],
            2,
        )
        self.assertEqual(report["event_name_totals"], [])
        self._assert_aggregate_invariants(report)

    def test_mixed_valid_and_invalid_rows_exclude_invalid_rows(self) -> None:
        database_path = self._create_database(
            events=[
                ("2026-01-03T10:00:00", "Synthetic valid"),
                ("invalid", "Synthetic excluded"),
            ]
        )
        report = self._build_report(database_path)

        self.assertEqual(report["summary"]["event_count"], 1)
        self.assertEqual(
            report["quality"]["invalid_occurred_at_count"],
            1,
        )
        self.assertEqual(len(report["event_name_totals"]), 1)
        self._assert_aggregate_invariants(report)

    def test_blank_names_map_to_blank_bucket(self) -> None:
        database_path = self._create_database(
            events=[
                ("2026-01-03T08:00:00", None),
                ("2026-01-03T09:00:00", ""),
                ("2026-01-03T10:00:00", " \t "),
                ("2026-01-03T11:00:00", "  Preserved  "),
                ("2025-12-31T11:00:00", None),
            ]
        )
        report = self._build_report(database_path)

        self.assertEqual(report["summary"]["event_count"], 4)
        self.assertEqual(
            report["quality"]["blank_event_name_count"],
            3,
        )
        self.assertEqual(
            report["event_name_totals"],
            [
                {"label": "(blank)", "event_count": 3},
                {"label": "  Preserved  ", "event_count": 1},
            ],
        )
        self._assert_aggregate_invariants(report)

    def test_selected_date_without_events_has_zero_aggregates(self) -> None:
        database_path = self._create_database(
            events=[("2026-01-02T10:00:00", "Synthetic other date")]
        )
        report = self._build_report(database_path)

        self.assertEqual(
            report["selected_day"],
            {
                "date": "2026-01-03",
                "event_count": 0,
                "event_name_totals": [],
            },
        )
        self._assert_aggregate_invariants(report)

    def test_inclusive_boundaries_and_zero_filled_gaps(self) -> None:
        database_path = self._create_database(
            events=[
                ("2026-01-01T00:00:00", "Synthetic start"),
                ("2026-01-05T23:59:59", "Synthetic end"),
            ]
        )
        report = self._build_report(database_path)

        self.assertEqual(
            [day["event_count"] for day in report["days"]],
            [1, 0, 0, 0, 1],
        )
        self.assertEqual(report["summary"]["event_count"], 2)
        self._assert_aggregate_invariants(report)

    def test_one_day_range(self) -> None:
        database_path = self._create_database(
            events=[("2026-01-03T12:00:00", "Synthetic one day")]
        )
        report = self._build_report(
            database_path,
            start=self.selected_date,
            end=self.selected_date,
        )

        self.assertEqual(len(report["days"]), 1)
        self.assertEqual(report["summary"]["logging_coverage_ratio"], 1.0)
        self._assert_aggregate_invariants(report)

    def test_ninety_day_range(self) -> None:
        database_path = self._create_database()
        end = self.start + timedelta(days=89)
        report = self._build_report(
            database_path,
            end=end,
            selected_date=end,
        )

        self.assertEqual(report["range"]["calendar_day_count"], 90)
        self.assertEqual(len(report["days"]), 90)
        self.assertEqual(report["days"][-1]["date"], end.isoformat())
        self._assert_aggregate_invariants(report)

    def test_reversed_range_is_rejected(self) -> None:
        database_path = self._create_database()

        with self.assertRaisesRegex(
            ValueError,
            "start must not be after end",
        ):
            build_daily_context_report(
                database_path,
                start=self.end,
                end=self.start,
                selected_date=self.start,
            )

    def test_non_date_inputs_are_rejected(self) -> None:
        database_path = self._create_database()

        for parameter in ("start", "end", "selected_date"):
            values: dict[str, object] = {
                "start": self.start,
                "end": self.end,
                "selected_date": self.selected_date,
            }
            values[parameter] = "2026-01-01"

            with self.subTest(parameter=parameter):
                with self.assertRaisesRegex(
                    TypeError,
                    f"{parameter} must be a date",
                ):
                    build_daily_context_report(
                        database_path,
                        start=values["start"],
                        end=values["end"],
                        selected_date=values["selected_date"],
                    )

    def test_selected_date_outside_range_is_rejected(self) -> None:
        database_path = self._create_database()

        with self.assertRaisesRegex(
            ValueError,
            "selected_date must be inside the inclusive range",
        ):
            self._build_report(
                database_path,
                selected_date=self.end + timedelta(days=1),
            )

    def test_duplicate_rows_count_separately(self) -> None:
        event = ("2026-01-03T10:00:00", "Synthetic duplicate")
        database_path = self._create_database(events=[event, event])
        report = self._build_report(database_path)

        self.assertEqual(report["summary"]["event_count"], 2)
        self.assertEqual(
            report["event_name_totals"],
            [{"label": "Synthetic duplicate", "event_count": 2}],
        )
        self._assert_aggregate_invariants(report)

    def test_ninety_one_day_range_is_rejected(self) -> None:
        database_path = self._create_database()
        end = self.start + timedelta(days=90)

        with self.assertRaisesRegex(ValueError, "1 through 90 days"):
            self._build_report(
                database_path,
                end=end,
                selected_date=end,
            )

    def test_wrong_database_path_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be a Path"):
            build_daily_context_report(
                "synthetic.db",
                start=self.start,
                end=self.end,
                selected_date=self.selected_date,
            )

    def test_missing_or_non_file_path_error_is_generic(self) -> None:
        paths = (
            Path(self.temporary_directory.name) / "missing.db",
            Path(self.temporary_directory.name),
        )

        for database_path in paths:
            with self.subTest(kind="missing" if database_path.suffix else "dir"):
                with self.assertRaises(FileNotFoundError) as raised:
                    self._build_report(database_path)

                self.assertEqual(
                    str(raised.exception),
                    "Database file was not found.",
                )
                self.assertNotIn(str(database_path), str(raised.exception))

    def test_sqlite_read_error_is_generic(self) -> None:
        database_path = self._create_database()
        connection = sqlite3.connect(database_path)

        try:
            connection.execute("DROP TABLE events")
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(RuntimeError) as raised:
            self._build_report(database_path)

        self.assertEqual(
            str(raised.exception),
            "Daily Context data could not be read.",
        )

    def test_names_preserve_text_and_use_unicode_tie_order(self) -> None:
        names = ["😀", "Å", "a", "A", "  exact  "]
        database_path = self._create_database(
            events=[
                (f"2026-01-03T0{index}:00:00", event_name)
                for index, event_name in enumerate(names, start=1)
            ]
        )
        report = self._build_report(database_path)

        self.assertEqual(
            [item["label"] for item in report["event_name_totals"]],
            ["  exact  ", "A", "a", "Å", "😀"],
        )

    def test_stored_offset_retains_stored_local_date(self) -> None:
        database_path = self._create_database(
            events=[
                ("2026-01-03T00:30:00+14:00", "Synthetic offset"),
                ("2026-01-03T23:30:00Z", "Synthetic zulu"),
            ]
        )
        report = self._build_report(database_path)

        self.assertEqual(report["selected_day"]["event_count"], 2)
        self.assertEqual(report["days"][2]["event_count"], 2)

    def test_metrics_use_decimal_half_up_rounding(self) -> None:
        coverage_path = self._create_database(
            "coverage.db",
            [("2026-01-01T08:00:00", "Synthetic coverage")],
        )
        coverage_end = self.start + timedelta(days=31)
        coverage = self._build_report(
            coverage_path,
            end=coverage_end,
            selected_date=self.start,
        )

        average_events = [
            (
                f"2026-01-{day:02d}T08:{minute:02d}:00",
                "Synthetic average",
            )
            for day, minute in [
                (1, 0),
                (1, 1),
                (2, 0),
                (3, 0),
                (4, 0),
                (5, 0),
                (6, 0),
                (7, 0),
                (8, 0),
            ]
        ]
        average_path = self._create_database("average.db", average_events)
        average = self._build_report(
            average_path,
            end=date(2026, 1, 8),
            selected_date=self.start,
        )

        self.assertEqual(
            coverage["summary"]["logging_coverage_ratio"],
            0.0313,
        )
        self.assertEqual(
            average["summary"]["average_events_per_logged_day"],
            1.13,
        )

    def test_dates_are_unique_ascending_with_all_zero_positions(self) -> None:
        database_path = self._create_database(
            events=[
                ("2026-01-02T08:00:00", "Synthetic second"),
                ("2026-01-04T08:00:00", "Synthetic fourth"),
            ]
        )
        report = self._build_report(database_path)
        returned_dates = [day["date"] for day in report["days"]]

        self.assertEqual(returned_dates, sorted(set(returned_dates)))
        self.assertEqual(
            [day["event_count"] for day in report["days"]],
            [0, 1, 0, 1, 0],
        )

    def test_response_has_exact_contract_fields_and_no_prohibited_keys(self) -> None:
        database_path = self._create_database(
            events=[("2026-01-03T08:00:00", "Synthetic permitted label")]
        )
        report = self._build_report(database_path)

        self.assertEqual(
            set(report),
            {
                "contract_version",
                "range",
                "summary",
                "days",
                "event_name_totals",
                "selected_day",
                "quality",
                "privacy",
            },
        )
        prohibited = {
            "id",
            "source_event_id",
            "created_at",
            "occurred_at",
            "note",
            "details",
            "sync_status",
            "database_path",
        }

        def assert_no_prohibited_keys(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(prohibited.isdisjoint(value))

                for nested_value in value.values():
                    assert_no_prohibited_keys(nested_value)
            elif isinstance(value, list):
                for nested_value in value:
                    assert_no_prohibited_keys(nested_value)

        assert_no_prohibited_keys(report)

    def test_sensitive_values_are_silent_and_baseline_stays_name_free(self) -> None:
        event_name = "Synthetic confidential label"
        database_path = self._create_database(
            events=[("2026-01-03T08:00:00", event_name)]
        )
        stdout = StringIO()
        stderr = StringIO()

        with (
            patch.object(logging.Logger, "_log") as log_call,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            report = self._build_report(database_path)

        self.assertIn(event_name, str(report["event_name_totals"]))
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        log_call.assert_not_called()

        baseline_report = build_baseline_report(database_path)
        self.assertNotIn(event_name, str(baseline_report))

    def test_connection_is_uri_read_only_and_query_only(self) -> None:
        database_path = self._create_database()
        real_connect = sqlite3.connect

        with patch.object(
            daily_context.sqlite3,
            "connect",
            wraps=real_connect,
        ) as connect:
            self._build_report(database_path)

        args, kwargs = connect.call_args
        self.assertTrue(args[0].endswith("?mode=ro"))
        self.assertTrue(kwargs["uri"])

        connection = daily_context._open_readonly_database(database_path)

        try:
            self.assertEqual(
                connection.execute("PRAGMA query_only").fetchone()[0],
                1,
            )

            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM events")
        finally:
            connection.close()

    def test_module_import_opens_no_database(self) -> None:
        with patch.object(sqlite3, "connect") as connect:
            importlib.reload(daily_context)

        connect.assert_not_called()

    def test_environment_cannot_select_database(self) -> None:
        database_path = self._create_database()
        environment = {
            "EVENT_TRACKER_DATABASE": "forbidden-synthetic-default.db",
            "HOME": str(Path(self.temporary_directory.name) / "unused-home"),
            "USERPROFILE": str(
                Path(self.temporary_directory.name) / "unused-profile"
            ),
        }

        with patch.dict(os.environ, environment, clear=False):
            report = self._build_report(database_path)

        self.assertEqual(report["summary"]["event_count"], 0)

    def test_invariant_failure_is_generic(self) -> None:
        database_path = self._create_database(
            events=[("2026-01-03T08:00:00", "Synthetic invariant")]
        )

        with (
            patch.object(
                daily_context,
                "_sorted_event_name_totals",
                return_value=[],
            ),
            self.assertRaises(RuntimeError) as raised,
        ):
            self._build_report(database_path)

        self.assertEqual(
            str(raised.exception),
            "Daily Context aggregate invariants failed.",
        )


if __name__ == "__main__":
    unittest.main()
