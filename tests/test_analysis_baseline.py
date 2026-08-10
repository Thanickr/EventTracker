from pathlib import Path
import sqlite3
import tempfile
import unittest

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
        self.database_path = (
            Path(self.temporary_directory.name) / "event_tracker.db"
        )

        connection = sqlite3.connect(self.database_path)

        try:
            connection.executescript(SCHEMA)
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
            connection.commit()
        finally:
            connection.close()

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


if __name__ == "__main__":
    unittest.main()
