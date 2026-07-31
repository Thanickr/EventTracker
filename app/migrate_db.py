"""
Apply explicit, repeat-safe SQLite migrations for Event Tracker.

Current migrations:

1. Add source_event_id for duplicate-safe phone imports.
2. Make amount and unit nullable for general event capture.

The migration script is safe to run repeatedly.
"""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"


def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[sqlite3.Row]:
    """Return SQLite column metadata for a table."""

    return connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()


def column_exists(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    """Return True when a column exists in a table."""

    columns = get_table_columns(
        connection,
        table_name,
    )

    return any(
        column["name"] == column_name
        for column in columns
    )


def column_is_not_null(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    """Return True when SQLite marks the column NOT NULL."""

    columns = get_table_columns(
        connection,
        table_name,
    )

    for column in columns:
        if column["name"] == column_name:
            return bool(column["notnull"])

    raise ValueError(
        f"Column not found: {table_name}.{column_name}"
    )


def migrate_source_event_id(
    connection: sqlite3.Connection,
) -> None:
    """Add source_event_id when missing."""

    if column_exists(
        connection,
        "events",
        "source_event_id",
    ):
        print(
            "Migration already applied: "
            "source_event_id exists"
        )
        return

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

    print(
        "Applied migration: add source_event_id"
    )


def migrate_optional_amount_and_unit(
    connection: sqlite3.Connection,
) -> None:
    """
    Rebuild events so amount and unit may be null.

    SQLite does not support directly removing a NOT NULL
    constraint, so the table must be recreated and copied.
    """

    amount_requires_value = column_is_not_null(
        connection,
        "events",
        "amount",
    )

    unit_requires_value = column_is_not_null(
        connection,
        "events",
        "unit",
    )

    if not (
        amount_requires_value or
        unit_requires_value
    ):
        print(
            "Migration already applied: "
            "amount and unit are nullable"
        )
        return

    connection.execute(
        """
        CREATE TABLE events_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_event_id TEXT,
            created_at TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            amount REAL,
            unit TEXT,
            note TEXT
        )
        """
    )

    connection.execute(
        """
        INSERT INTO events_new (
            id,
            source_event_id,
            created_at,
            occurred_at,
            event_type,
            exercise_type,
            amount,
            unit,
            note
        )
        SELECT
            id,
            source_event_id,
            created_at,
            occurred_at,
            event_type,
            exercise_type,
            amount,
            unit,
            note
        FROM events
        """
    )

    connection.execute(
        """
        DROP TABLE events
        """
    )

    connection.execute(
        """
        ALTER TABLE events_new
        RENAME TO events
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

    print(
        "Applied migration: "
        "make amount and unit nullable"
    )


def migrate_database() -> None:
    """Apply all required database migrations."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}\n"
            "Run python app/init_db.py first."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        connection.execute("BEGIN")

        try:
            migrate_source_event_id(connection)

            migrate_optional_amount_and_unit(
                connection
            )

            connection.commit()
        except Exception:
            connection.rollback()
            raise

    print(
        f"Database migration complete: "
        f"{DATABASE_PATH}"
    )


if __name__ == "__main__":
    migrate_database()