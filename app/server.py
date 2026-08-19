"""
Local web backend for Event Tracker.

Version 0.1 exposes the SQLite data layer through a small FastAPI server.

Initial endpoints:
- GET /health
- GET /events
- POST /events
- GET /api/v1/daily-context
"""

from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path
import re
import sqlite3
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Request, Response
from pydantic import BaseModel
import uvicorn

from analysis.daily_context import build_daily_context_report
from .log_event import list_events, log_exercise_event

from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "event_tracker.db"

STATIC_DIR = PROJECT_ROOT / "app" / "static"

app = FastAPI(title="Event Tracker API")

DAILY_CONTEXT_PATH = "/api/v1/daily-context"
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _get_daily_context_database_path() -> Path:
    """Return the explicit database selected for Daily Context requests."""

    return DATABASE_PATH


def _parse_query_date(value: str) -> date:
    """Parse one strict ASCII YYYY-MM-DD query value."""

    if DATE_PATTERN.fullmatch(value) is None:
        raise ValueError("A date parameter is invalid.")

    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("A date parameter is invalid.") from None


def _error_response(
    code: str,
    message: str,
    *,
    status_code: int,
) -> JSONResponse:
    """Return one stable, non-sensitive API error envelope."""

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


@app.middleware("http")
async def _add_daily_context_no_store(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Prevent caching of every Daily Context endpoint response."""

    if request.url.path != DAILY_CONTEXT_PATH:
        return await call_next(request)

    try:
        response = await call_next(request)
    except Exception:
        response = _error_response(
            "internal_error",
            "The request could not be completed.",
            status_code=500,
        )

    response.headers["Cache-Control"] = "no-store"

    return response


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


@app.get(DAILY_CONTEXT_PATH)
def get_daily_context(
    database_path: Annotated[
        Path,
        Depends(_get_daily_context_database_path),
    ],
    start: str | None = None,
    end: str | None = None,
    selected_date: str | None = None,
) -> JSONResponse:
    """Return one validated Daily Context aggregate response."""

    if start is None or end is None:
        return _error_response(
            "missing_parameter",
            "A required date parameter is missing.",
            status_code=400,
        )

    try:
        start_date = _parse_query_date(start)
        end_date = _parse_query_date(end)
    except ValueError:
        return _error_response(
            "invalid_date_format",
            "A date parameter is invalid.",
            status_code=400,
        )

    if start_date > end_date:
        return _error_response(
            "start_after_end",
            "The start date must not be after the end date.",
            status_code=400,
        )

    calendar_day_count = (end_date - start_date).days + 1

    if calendar_day_count > 90:
        return _error_response(
            "range_too_large",
            "The date range exceeds 90 days.",
            status_code=400,
        )

    if selected_date is None:
        selected_date_value = end_date
    else:
        try:
            selected_date_value = _parse_query_date(selected_date)
        except ValueError:
            return _error_response(
                "invalid_date_format",
                "A date parameter is invalid.",
                status_code=400,
            )

    if not start_date <= selected_date_value <= end_date:
        return _error_response(
            "selected_date_out_of_range",
            "The selected date is outside the requested range.",
            status_code=400,
        )

    try:
        report = build_daily_context_report(
            database_path,
            start=start_date,
            end=end_date,
            selected_date=selected_date_value,
        )
    except Exception:
        return _error_response(
            "internal_error",
            "The request could not be completed.",
            status_code=500,
        )

    return JSONResponse(content=report)


@app.get("/")
def read_index() -> FileResponse:
    """Serve the one-screen Event Tracker web interface."""

    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main() -> None:
    """Run the supported local-only Event Tracker API server."""

    uvicorn.run(
        "app.server:app",
        host="127.0.0.1",
        port=8000,
        access_log=False,
    )


if __name__ == "__main__":
    main()
