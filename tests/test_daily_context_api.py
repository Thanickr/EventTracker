from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from io import StringIO
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.server as server


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
"""

MISSING_PARAMETER = {
    "error": {
        "code": "missing_parameter",
        "message": "A required date parameter is missing.",
    }
}
INVALID_DATE_FORMAT = {
    "error": {
        "code": "invalid_date_format",
        "message": "A date parameter is invalid.",
    }
}
START_AFTER_END = {
    "error": {
        "code": "start_after_end",
        "message": "The start date must not be after the end date.",
    }
}
RANGE_TOO_LARGE = {
    "error": {
        "code": "range_too_large",
        "message": "The date range exceeds 90 days.",
    }
}
SELECTED_DATE_OUT_OF_RANGE = {
    "error": {
        "code": "selected_date_out_of_range",
        "message": "The selected date is outside the requested range.",
    }
}
INTERNAL_ERROR = {
    "error": {
        "code": "internal_error",
        "message": "The request could not be completed.",
    }
}


class DailyContextApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = self._create_database()
        server.app.dependency_overrides[
            server._get_daily_context_database_path
        ] = lambda: self.database_path
        self.client = TestClient(server.app)

    def tearDown(self) -> None:
        self.client.close()
        server.app.dependency_overrides.clear()
        self.temporary_directory.cleanup()

    def _create_database(
        self,
        filename: str = "synthetic.db",
        events: list[tuple[str, str]] | None = None,
        *,
        include_schema: bool = True,
    ) -> Path:
        database_path = Path(self.temporary_directory.name) / filename
        connection = sqlite3.connect(database_path)

        try:
            if include_schema:
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
                            "2026-08-01T00:00:00",
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

    def _get(
        self,
        query: str = "start=2026-08-01&end=2026-08-03",
    ):
        return self.client.get(f"{server.DAILY_CONTEXT_PATH}?{query}")

    def _assert_error(
        self,
        response,
        expected_body: dict[str, object],
        expected_status: int,
    ) -> None:
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response.json(), expected_body)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_empty_report_returns_exact_contract(self) -> None:
        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "contract_version": "daily-context.v1",
                "range": {
                    "start": "2026-08-01",
                    "end": "2026-08-03",
                    "selected_date": "2026-08-03",
                    "calendar_day_count": 3,
                    "calendar_basis": "stored-local-date",
                },
                "summary": {
                    "event_count": 0,
                    "days_with_logged_events": 0,
                    "days_without_logged_events": 3,
                    "logging_coverage_ratio": 0.0,
                    "average_events_per_logged_day": None,
                },
                "days": [
                    {"date": "2026-08-01", "event_count": 0},
                    {"date": "2026-08-02", "event_count": 0},
                    {"date": "2026-08-03", "event_count": 0},
                ],
                "event_name_totals": [],
                "selected_day": {
                    "date": "2026-08-03",
                    "event_count": 0,
                    "event_name_totals": [],
                },
                "quality": {
                    "invalid_occurred_at_count": 0,
                    "invalid_occurred_at_scope": "corpus",
                    "blank_event_name_count": 0,
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
            },
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_populated_report_returns_exact_aggregate_contract(self) -> None:
        self.database_path = self._create_database(
            "populated.db",
            [
                ("2026-08-01T08:00:00", "Synthetic Alpha"),
                ("2026-08-02T09:00:00", "Synthetic Beta"),
                ("2026-08-02T10:00:00", "Synthetic Beta"),
            ],
        )
        response = self._get(
            "start=2026-08-01&end=2026-08-03&selected_date=2026-08-02"
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {
                "contract_version": "daily-context.v1",
                "range": {
                    "start": "2026-08-01",
                    "end": "2026-08-03",
                    "selected_date": "2026-08-02",
                    "calendar_day_count": 3,
                    "calendar_basis": "stored-local-date",
                },
                "summary": {
                    "event_count": 3,
                    "days_with_logged_events": 2,
                    "days_without_logged_events": 1,
                    "logging_coverage_ratio": 0.6667,
                    "average_events_per_logged_day": 1.5,
                },
                "days": [
                    {"date": "2026-08-01", "event_count": 1},
                    {"date": "2026-08-02", "event_count": 2},
                    {"date": "2026-08-03", "event_count": 0},
                ],
                "event_name_totals": [
                    {"label": "Synthetic Beta", "event_count": 2},
                    {"label": "Synthetic Alpha", "event_count": 1},
                ],
                "selected_day": {
                    "date": "2026-08-02",
                    "event_count": 2,
                    "event_name_totals": [
                        {"label": "Synthetic Beta", "event_count": 2}
                    ],
                },
                "quality": {
                    "invalid_occurred_at_count": 0,
                    "invalid_occurred_at_scope": "corpus",
                    "blank_event_name_count": 0,
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
            },
            body,
        )

    def test_missing_required_parameters(self) -> None:
        for query in ("", "end=2026-08-03", "start=2026-08-01"):
            with self.subTest(query_kind=query.split("=")[0] if query else "both"):
                self._assert_error(self._get(query), MISSING_PARAMETER, 400)

    def test_empty_date_values(self) -> None:
        queries = (
            "start=&end=2026-08-03",
            "start=2026-08-01&end=",
            "start=2026-08-01&end=2026-08-03&selected_date=",
        )

        for query in queries:
            with self.subTest(empty_parameter=query):
                self._assert_error(self._get(query), INVALID_DATE_FORMAT, 400)

    def test_malformed_non_padded_and_impossible_dates(self) -> None:
        values = (
            "2026-8-01",
            "2026-08-1",
            "2026-02-30",
            " 2026-08-01",
            "2026-08-01 ",
            "２０２６-０８-０１",
            "not-a-date",
        )

        for value in values:
            with self.subTest(value_kind=values.index(value)):
                response = self._get(f"start={value}&end=2026-08-03")
                self._assert_error(response, INVALID_DATE_FORMAT, 400)

    def test_reversed_range(self) -> None:
        response = self._get("start=2026-08-03&end=2026-08-01")
        self._assert_error(response, START_AFTER_END, 400)

    def test_ninety_one_day_range(self) -> None:
        response = self._get("start=2026-01-01&end=2026-04-01")
        self._assert_error(response, RANGE_TOO_LARGE, 400)

    def test_one_day_range(self) -> None:
        response = self._get("start=2026-08-01&end=2026-08-01")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"]["calendar_day_count"], 1)
        self.assertEqual(len(response.json()["days"]), 1)

    def test_ninety_day_range(self) -> None:
        response = self._get("start=2026-01-01&end=2026-03-31")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"]["calendar_day_count"], 90)
        self.assertEqual(len(response.json()["days"]), 90)

    def test_selected_date_defaults_to_end(self) -> None:
        response = self._get("start=2026-08-01&end=2026-08-03")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["range"]["selected_date"],
            "2026-08-03",
        )

    def test_malformed_selected_date(self) -> None:
        response = self._get(
            "start=2026-08-01&end=2026-08-03&selected_date=2026-02-30"
        )
        self._assert_error(response, INVALID_DATE_FORMAT, 400)

    def test_selected_date_outside_range(self) -> None:
        response = self._get(
            "start=2026-08-01&end=2026-08-03&selected_date=2026-08-04"
        )
        self._assert_error(response, SELECTED_DATE_OUT_OF_RANGE, 400)

    def test_repeated_parameters_use_last_value(self) -> None:
        response = self._get(
            "start=invalid&start=2026-08-01&"
            "end=invalid&end=2026-08-03&"
            "selected_date=invalid&selected_date=2026-08-02"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"]["start"], "2026-08-01")
        self.assertEqual(response.json()["range"]["end"], "2026-08-03")
        self.assertEqual(
            response.json()["range"]["selected_date"],
            "2026-08-02",
        )

    def test_unexpected_parameters_are_ignored(self) -> None:
        response = self._get(
            "start=2026-08-01&end=2026-08-03&unexpected=value"
        )
        self.assertEqual(response.status_code, 200)

    def test_aggregate_is_not_called_for_invalid_transport(self) -> None:
        invalid_queries = (
            "end=2026-08-03",
            "start=bad&end=2026-08-03",
            "start=2026-08-03&end=2026-08-01",
            "start=2026-01-01&end=2026-04-01",
            "start=2026-08-01&end=2026-08-03&selected_date=2026-08-04",
        )

        with patch.object(server, "build_daily_context_report") as aggregate:
            for query in invalid_queries:
                with self.subTest(validation_case=invalid_queries.index(query)):
                    self._get(query)

        aggregate.assert_not_called()

    def test_aggregate_receives_parsed_dates_and_injected_path(self) -> None:
        sentinel = {"contract_version": "synthetic-sentinel"}

        with patch.object(
            server,
            "build_daily_context_report",
            return_value=sentinel,
        ) as aggregate:
            response = self._get(
                "start=2026-08-01&end=2026-08-03&selected_date=2026-08-02"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), sentinel)
        aggregate.assert_called_once_with(
            self.database_path,
            start=date(2026, 8, 1),
            end=date(2026, 8, 3),
            selected_date=date(2026, 8, 2),
        )

    def test_missing_database_is_sanitized(self) -> None:
        self.database_path = Path(self.temporary_directory.name) / "missing.db"
        response = self._get()
        self._assert_error(response, INTERNAL_ERROR, 500)
        self.assertNotIn(str(self.database_path), response.text)

    def test_malformed_database_and_missing_table_are_sanitized(self) -> None:
        malformed_path = Path(self.temporary_directory.name) / "malformed.db"
        malformed_path.write_text("synthetic non-database", encoding="utf-8")
        missing_table_path = self._create_database(
            "missing-table.db",
            include_schema=False,
        )

        for database_path in (malformed_path, missing_table_path):
            with self.subTest(database_kind=database_path.name):
                self.database_path = database_path
                response = self._get()
                self._assert_error(response, INTERNAL_ERROR, 500)
                self.assertNotIn(str(database_path), response.text)

    def test_aggregate_exceptions_are_sanitized(self) -> None:
        exceptions = (
            TypeError("synthetic type detail"),
            ValueError("synthetic value detail"),
            FileNotFoundError("synthetic path detail"),
            RuntimeError("synthetic database detail"),
            Exception("synthetic unexpected detail"),
        )

        for error in exceptions:
            with self.subTest(error_type=type(error).__name__):
                with patch.object(
                    server,
                    "build_daily_context_report",
                    side_effect=error,
                ):
                    response = self._get()

                self._assert_error(response, INTERNAL_ERROR, 500)
                self.assertNotIn(str(error), response.text)

        original_override = server.app.dependency_overrides[
            server._get_daily_context_database_path
        ]

        def fail_dependency() -> Path:
            raise RuntimeError("synthetic injection detail")

        server.app.dependency_overrides[
            server._get_daily_context_database_path
        ] = fail_dependency

        try:
            response = self._get()
        finally:
            server.app.dependency_overrides[
                server._get_daily_context_database_path
            ] = original_override

        self._assert_error(response, INTERNAL_ERROR, 500)
        self.assertNotIn("synthetic injection detail", response.text)

    def test_no_store_is_present_on_success_and_every_error(self) -> None:
        cases = (
            ("start=2026-08-01&end=2026-08-03", "GET"),
            ("end=2026-08-03", "GET"),
            ("start=bad&end=2026-08-03", "GET"),
            ("start=2026-08-03&end=2026-08-01", "GET"),
            ("start=2026-01-01&end=2026-04-01", "GET"),
            (
                "start=2026-08-01&end=2026-08-03&selected_date=2026-08-04",
                "GET",
            ),
            ("start=2026-08-01&end=2026-08-03", "POST"),
        )

        for query, method in cases:
            with self.subTest(method=method, case=cases.index((query, method))):
                response = self.client.request(
                    method,
                    f"{server.DAILY_CONTEXT_PATH}?{query}",
                )
                self.assertEqual(
                    response.headers["Cache-Control"],
                    "no-store",
                )

        with patch.object(
            server,
            "build_daily_context_report",
            side_effect=RuntimeError("synthetic detail"),
        ):
            response = self._get()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_unsupported_method_returns_405_without_aggregate_call(self) -> None:
        with patch.object(server, "build_daily_context_report") as aggregate:
            response = self.client.post(
                f"{server.DAILY_CONTEXT_PATH}?start=2026-08-01&end=2026-08-03"
            )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        aggregate.assert_not_called()

    def test_response_excludes_prohibited_fields(self) -> None:
        response = self._get()
        prohibited = {
            "id",
            "source_event_id",
            "created_at",
            "occurred_at",
            "note",
            "details",
            "database_path",
            "sync_status",
        }

        def assert_clean(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(prohibited.isdisjoint(value))

                for nested in value.values():
                    assert_clean(nested)
            elif isinstance(value, list):
                for nested in value:
                    assert_clean(nested)

        assert_clean(response.json())

    def test_sensitive_values_are_not_logged_or_exposed(self) -> None:
        event_name = "Synthetic confidential endpoint label"
        self.database_path = self._create_database(
            "sensitive.db",
            [("2026-08-02T08:00:00", event_name)],
        )
        stdout = StringIO()
        stderr = StringIO()

        with (
            patch.object(logging.Logger, "_log") as log_call,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertIn(event_name, str(response.json()["event_name_totals"]))
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        logged = " ".join(str(call) for call in log_call.call_args_list)
        self.assertNotIn(event_name, logged)

    def test_environment_cannot_select_database(self) -> None:
        environment = {
            "EVENT_TRACKER_DATABASE": "forbidden-operational-default.db",
            "DATABASE_PATH": "forbidden-operational-default.db",
        }

        with patch.dict(os.environ, environment, clear=False):
            response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["event_count"], 0)

    def test_import_opens_no_database(self) -> None:
        script = (
            "from unittest.mock import patch\n"
            "with patch('sqlite3.connect', "
            "side_effect=RuntimeError('database opened')):\n"
            "    import app.server\n"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertNotIn("database opened", completed.stderr)

    def test_existing_routes_remain_registered(self) -> None:
        paths = {route.path for route in server.app.routes}

        self.assertTrue(
            {"/", "/health", "/events", "/static", DAILY_PATH}.issubset(paths)
        )

    def test_supported_server_startup_is_loopback_and_disables_access_log(
        self,
    ) -> None:
        with patch.object(server.uvicorn, "run") as run:
            server.main()

        run.assert_called_once_with(
            "app.server:app",
            host="127.0.0.1",
            port=8000,
            access_log=False,
        )


DAILY_PATH = server.DAILY_CONTEXT_PATH


if __name__ == "__main__":
    unittest.main()
