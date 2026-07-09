"""
Local web backend for Event Tracker.

Version 0.1 exposes the SQLite data layer through a small FastAPI server.

Initial endpoints:
- GET /health
- GET /events
- POST /events
"""

from pathlib import Path
import sqlite3
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .log_event import list_events, log_exercise_event


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"

app = FastAPI(title="Event Tracker API")


class ExerciseEventCreate(BaseModel):
    """Request body for creating an exercise event."""

    exercise_type: str
    amount: float
    unit: str
    note: Optional[str] = None


@app.get("/health")
def health_check() -> dict:
    """Confirm that the API is running."""

    return {
        "status": "ok",
        "database_exists": DATABASE_PATH.exists(),
    }


@app.get("/events")
def get_events() -> list[dict]:
    """Return recent exercise events."""

    events = list_events()

    return [
        {
            "id": event[0],
            "occurred_at": event[1],
            "event_type": event[2],
            "exercise_type": event[3],
            "amount": event[4],
            "unit": event[5],
            "note": event[6],
        }
        for event in events
    ]


@app.post("/events")
def create_event(event: ExerciseEventCreate) -> dict:
    """Create one exercise event."""

    event_id = log_exercise_event(
        exercise_type=event.exercise_type,
        amount=event.amount,
        unit=event.unit,
        note=event.note,
    )

    return {
        "id": event_id,
        "status": "created",
    }