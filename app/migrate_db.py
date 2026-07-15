"""
Apply small, explicit database migrations for Event Tracker.

Version 0.1 currently has one migration:
- Add source_event_id for duplicate-safe phone imports.

The migration is safe to run repeatedly.
"""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"


def column_exists(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    """Return True when a column already exists in a SQLite table."""

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(row[1] == column_name for row in rows)


def migrate_database() -> None:
    """Apply all currently required database migrations."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}\n"
            "Run python app/init_db.py first."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        if not column_exists(
            connection,
            "events",
            "source_event_id",
        ):
            connection.execute(
                """
                ALTER TABLE events
                ADD COLUMN source_event_id TEXT
                """
            )

            connection.execute(
                """
                CREATE UNIQUE INDEX
                IF NOT EXISTS idx_events_source_event_id
                ON events(source_event_id)
                WHERE source_event_id IS NOT NULL
                """
            )

            print("Applied migration: add source_event_id")
        else:
            print("Migration already applied: source_event_id exists")

    print(f"Database migration complete: {DATABASE_PATH}")


if __name__ == "__main__":
    migrate_database()