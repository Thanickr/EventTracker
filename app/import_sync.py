"""
Import an Event Tracker phone synchronization package into SQLite.

The importer:

- validates the sync package
- inserts new events transactionally
- skips events already present in SQLite
- produces a JSON acknowledgment receipt
- never modifies the source sync package
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"
RECEIPTS_DIRECTORY = PROJECT_ROOT / "database" / "sync_receipts"

SYNC_PACKAGE_FORMAT = "event-tracker-sync-package"
SYNC_RECEIPT_FORMAT = "event-tracker-sync-receipt"
SYNC_VERSION = 1


class SyncPackageError(ValueError):
    """Raised when a synchronization package is invalid."""


def current_utc_timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Read and decode a JSON object from disk."""

    if not file_path.exists():
        raise FileNotFoundError(f"Sync package not found: {file_path}")

    try:
        raw_data = file_path.read_text(encoding="utf-8")
        decoded = json.loads(raw_data)
    except json.JSONDecodeError as error:
        raise SyncPackageError(
            f"Sync package is not valid JSON: {error}"
        ) from error

    if not isinstance(decoded, dict):
        raise SyncPackageError(
            "Sync package root must be a JSON object."
        )

    return decoded


def require_nonempty_string(
    value: Any,
    field_name: str,
) -> str:
    """Validate and return a required nonempty string."""

    if not isinstance(value, str) or not value.strip():
        raise SyncPackageError(
            f"Field '{field_name}' must be a nonempty string."
        )

    return value.strip()


def validate_event(event: Any, index: int) -> dict[str, Any]:
    """Validate one event from the synchronization package."""

    if not isinstance(event, dict):
        raise SyncPackageError(
            f"Event {index} must be a JSON object."
        )

    event_id = require_nonempty_string(
        event.get("id"),
        f"events[{index}].id",
    )

    created_at = require_nonempty_string(
        event.get("created_at"),
        f"events[{index}].created_at",
    )

    occurred_at = require_nonempty_string(
        event.get("occurred_at"),
        f"events[{index}].occurred_at",
    )

    event_type = require_nonempty_string(
        event.get("event_type"),
        f"events[{index}].event_type",
    )

    exercise_type = require_nonempty_string(
        event.get("exercise_type"),
        f"events[{index}].exercise_type",
    )

    unit = require_nonempty_string(
        event.get("unit"),
        f"events[{index}].unit",
    )

    amount = event.get("amount")

    if (
        isinstance(amount, bool)
        or not isinstance(amount, (int, float))
    ):
        raise SyncPackageError(
            f"Field 'events[{index}].amount' must be numeric."
        )

    note = event.get("note")

    if note is not None and not isinstance(note, str):
        raise SyncPackageError(
            f"Field 'events[{index}].note' must be text or null."
        )

    return {
        "id": event_id,
        "created_at": created_at,
        "occurred_at": occurred_at,
        "event_type": event_type,
        "exercise_type": exercise_type,
        "amount": float(amount),
        "unit": unit,
        "note": note,
    }


def validate_sync_package(
    package: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    """Validate the package and return its ID and events."""

    if package.get("format") != SYNC_PACKAGE_FORMAT:
        raise SyncPackageError(
            "File is not an Event Tracker sync package."
        )

    if package.get("version") != SYNC_VERSION:
        raise SyncPackageError(
            f"Unsupported sync package version: "
            f"{package.get('version')!r}"
        )

    package_id = require_nonempty_string(
        package.get("package_id"),
        "package_id",
    )

    events = package.get("events")

    if not isinstance(events, list):
        raise SyncPackageError(
            "Field 'events' must be an array."
        )

    validated_events = [
        validate_event(event, index)
        for index, event in enumerate(events)
    ]

    return package_id, validated_events


def source_event_exists(
    connection: sqlite3.Connection,
    source_event_id: str,
) -> bool:
    """Return True if an event is already stored in SQLite."""

    row = connection.execute(
        """
        SELECT 1
        FROM events
        WHERE source_event_id = ?
        LIMIT 1
        """,
        (source_event_id,),
    ).fetchone()

    return row is not None


def import_events(
    events: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """
    Import events in one SQLite transaction.

    Returns:
        accepted_event_ids
        already_present_event_ids
    """

    accepted_event_ids: list[str] = []
    already_present_event_ids: list[str] = []

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("BEGIN")

        try:
            for event in events:
                source_event_id = event["id"]

                if source_event_exists(
                    connection,
                    source_event_id,
                ):
                    already_present_event_ids.append(
                        source_event_id
                    )
                    continue

                connection.execute(
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
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_event_id,
                        event["created_at"],
                        event["occurred_at"],
                        event["event_type"],
                        event["exercise_type"],
                        event["amount"],
                        event["unit"],
                        event["note"],
                    ),
                )

                accepted_event_ids.append(
                    source_event_id
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return (
        accepted_event_ids,
        already_present_event_ids,
    )


def build_receipt(
    package_id: str,
    accepted_event_ids: list[str],
    already_present_event_ids: list[str],
) -> dict[str, Any]:
    """Build a synchronization receipt."""

    return {
        "format": SYNC_RECEIPT_FORMAT,
        "version": SYNC_VERSION,
        "receipt_id": str(uuid4()),
        "package_id": package_id,
        "processed_at": current_utc_timestamp(),
        "accepted_event_ids": accepted_event_ids,
        "already_present_event_ids": (
            already_present_event_ids
        ),
        "acknowledged_event_ids": (
            accepted_event_ids
            + already_present_event_ids
        ),
        "rejected_events": [],
    }


def write_receipt(
    receipt: dict[str, Any],
) -> Path:
    """Write a receipt to the local receipts directory."""

    RECEIPTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    receipt_path = (
        RECEIPTS_DIRECTORY
        / f"event-tracker-receipt-{timestamp}.json"
    )

    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )

    return receipt_path


def import_sync_package(
    package_path: Path,
) -> Path:
    """Import one sync package and return the receipt path."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    package = load_json_file(package_path)

    package_id, events = validate_sync_package(
        package
    )

    accepted, already_present = import_events(
        events
    )

    receipt = build_receipt(
        package_id=package_id,
        accepted_event_ids=accepted,
        already_present_event_ids=already_present,
    )

    receipt_path = write_receipt(receipt)

    print(f"Package ID: {package_id}")
    print(f"Events in package: {len(events)}")
    print(f"New events imported: {len(accepted)}")
    print(
        "Events already present: "
        f"{len(already_present)}"
    )
    print(f"Receipt created: {receipt_path}")

    return receipt_path


def main() -> None:
    """Run the importer from the command line."""

    if len(sys.argv) != 2:
        print(
            "Usage: "
            "python app/import_sync.py "
            "<sync-package.json>"
        )
        raise SystemExit(2)

    package_path = Path(sys.argv[1]).expanduser()

    try:
        import_sync_package(package_path)
    except (
        FileNotFoundError,
        SyncPackageError,
        sqlite3.DatabaseError,
    ) as error:
        print(f"Import failed: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()