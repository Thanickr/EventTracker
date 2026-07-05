"""
Log exercise events to the Event Tracker SQLite database.

Version 0.1 keeps this intentionally small:
- create one exercise event
- store it in SQLite
- read events back for verification
"""

from datetime import datetime
from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"


def get_current_timestamp() -> str:
    """Return the current local timestamp in ISO-8601 format."""
    return datetime.now().isoformat(timespec="seconds")


def log_exercise_event(
    exercise_type: str,
    amount: float,
    unit: str,
    note: str | None = None,
) -> int:
    """
    Insert one exercise event into the database.

    Returns the ID of the newly created event.
    """

    timestamp = get_current_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO events (
                created_at,
                occurred_at,
                event_type,
                exercise_type,
                amount,
                unit,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                timestamp,
                "exercise",
                exercise_type,
                amount,
                unit,
                note,
            ),
        )

        event_id = cursor.lastrowid

    if event_id is None:
        raise RuntimeError("Failed to create exercise event.")

    return event_id


def list_events() -> list[tuple]:
    """Return all logged events, newest first."""

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                occurred_at,
                event_type,
                exercise_type,
                amount,
                unit,
                note
            FROM events
            ORDER BY occurred_at DESC
            """
        )

        return cursor.fetchall()


if __name__ == "__main__":
    new_event_id = log_exercise_event(
        exercise_type="walk",
        amount=1.0,
        unit="mile",
        note="First test event",
    )

    print(f"Created event ID: {new_event_id}")

    print("\nCurrent events:")
    for event in list_events():
        print(event)