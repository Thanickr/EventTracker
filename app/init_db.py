"""
Initialize the Event Tracker SQLite database.

This script reads the SQL schema from database/schema.sql and creates
the local SQLite database file at database/event_tracker.db.

Version 0.1 intentionally keeps this simple:
- one schema file
- one local SQLite database
- no migrations yet
"""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"


def initialize_database() -> None:
    """Create the SQLite database and apply the schema."""

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executescript(schema_sql)

    print(f"Database initialized successfully: {DATABASE_PATH}")


if __name__ == "__main__":
    initialize_database()