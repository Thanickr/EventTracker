from html.parser import HTMLParser
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

import app.server as server


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "app" / "static"
DASHBOARD_HTML = STATIC_DIR / "daily-context.html"
DASHBOARD_CSS = STATIC_DIR / "daily-context.css"
DASHBOARD_JS = STATIC_DIR / "daily-context.js"

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


class DashboardDocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.attributes_by_id: dict[str, dict[str, str | None]] = {}
        self.labels_for: set[str] = set()
        self.heading_text: list[str] = []
        self.resource_urls: list[str] = []
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")

        if element_id is not None:
            self.attributes_by_id[element_id] = attributes

        if tag == "label" and attributes.get("for") is not None:
            self.labels_for.add(str(attributes["for"]))

        if tag == "script" and attributes.get("src") is not None:
            self.resource_urls.append(str(attributes["src"]))

        if tag == "link" and attributes.get("href") is not None:
            self.resource_urls.append(str(attributes["href"]))

        if tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._heading_parts = []

    def handle_data(self, data: str) -> None:
        if self._heading_tag is not None:
            self._heading_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._heading_tag:
            text = " ".join("".join(self._heading_parts).split())
            self.heading_text.append(text)
            self._heading_tag = None
            self._heading_parts = []


class DailyContextDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = DASHBOARD_HTML.read_text(encoding="utf-8")
        cls.css = DASHBOARD_CSS.read_text(encoding="utf-8")
        cls.javascript = DASHBOARD_JS.read_text(encoding="utf-8")
        cls.document = DashboardDocumentParser()
        cls.document.feed(cls.html)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "synthetic.db"
        connection = sqlite3.connect(self.database_path)

        try:
            connection.executescript(SCHEMA)
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
                ) VALUES (NULL, ?, ?, 'event', ?, NULL, NULL, NULL)
                """,
                (
                    "2026-08-18T08:00:00",
                    "2026-08-18T08:00:00",
                    "Synthetic dashboard event",
                ),
            )
            connection.commit()
        finally:
            connection.close()

        server.app.dependency_overrides[
            server._get_daily_context_database_path
        ] = lambda: self.database_path
        self.client = TestClient(server.app)

    def tearDown(self) -> None:
        self.client.close()
        server.app.dependency_overrides.clear()
        self.temporary_directory.cleanup()

    def test_dashboard_page_is_available_at_dedicated_route(self) -> None:
        response = self.client.get("/daily-context")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("<h1>Daily Context</h1>", response.text)

    def test_existing_routes_remain_registered_without_execution(self) -> None:
        paths = {route.path for route in server.app.routes}

        self.assertTrue(
            {
                "/",
                "/health",
                "/events",
                "/static",
                server.DAILY_CONTEXT_PATH,
                "/daily-context",
            }.issubset(paths)
        )

    def test_dashboard_static_assets_are_available(self) -> None:
        for path, content_type in (
            ("/static/daily-context.css", "text/css"),
            ("/static/daily-context.js", "javascript"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(content_type, response.headers["content-type"])

    def test_required_semantic_sections_and_headings_are_present(self) -> None:
        required_headings = {
            "Daily Context",
            "Date range",
            "Summary",
            "Daily activity",
            "Event-name totals",
            "Selected day",
            "Data quality",
            "Response privacy",
        }

        self.assertTrue(required_headings.issubset(self.document.heading_text))
        self.assertEqual(
            self.document.attributes_by_id["dashboard-status"].get("role"),
            "status",
        )
        self.assertEqual(
            self.document.attributes_by_id["dashboard-error"].get("role"),
            "alert",
        )

    def test_date_controls_use_explicit_labels_and_native_inputs(self) -> None:
        for control_id in ("start-date", "end-date", "selected-date"):
            with self.subTest(control_id=control_id):
                attributes = self.document.attributes_by_id[control_id]
                self.assertEqual(attributes.get("type"), "date")
                self.assertIn("required", attributes)
                self.assertIn(control_id, self.document.labels_for)

        self.assertIn("load-button", self.document.attributes_by_id)
        self.assertIn("today-button", self.document.attributes_by_id)
        self.assertEqual(self.html.count("data-day-count="), 3)
        self.assertIn('data-day-count="7"', self.html)
        self.assertIn('data-day-count="30"', self.html)
        self.assertIn('data-day-count="90"', self.html)

    def test_default_dates_use_local_today_and_thirty_inclusive_days(self) -> None:
        self.assertIn("const end = new Date();", self.javascript)
        self.assertIn("const start = addLocalDays(end, -29);", self.javascript)
        self.assertIn("selectedInput.value = endInput.value;", self.javascript)
        self.assertIn("value.getFullYear()", self.javascript)
        self.assertNotIn("toISOString", self.javascript)

    def test_request_uses_same_origin_url_parameters_and_no_store(self) -> None:
        self.assertIn('const API_PATH = "/api/v1/daily-context";', self.javascript)
        self.assertIn("new URLSearchParams", self.javascript)
        self.assertIn('cache: "no-store"', self.javascript)
        self.assertNotIn("http://", self.javascript)
        self.assertNotIn("https://", self.javascript)

    def test_loading_state_disables_duplicate_form_submissions(self) -> None:
        self.assertIn("loadButton.disabled = isBusy;", self.javascript)
        self.assertIn("if (loadButton.disabled)", self.javascript)
        self.assertIn('loadButton.textContent = isBusy ? "Loading…"', self.javascript)
        self.assertIn('statusMessage.textContent = "Loading Daily Context…";', self.javascript)

    def test_stale_responses_are_aborted_and_sequence_guarded(self) -> None:
        self.assertIn("activeController.abort();", self.javascript)
        self.assertIn("const currentRequest = requestSequence;", self.javascript)
        self.assertIn("currentRequest !== requestSequence", self.javascript)
        self.assertIn("signal: controller.signal", self.javascript)

    def test_summary_targets_every_documented_metric(self) -> None:
        expected_ids = {
            "summary-events",
            "summary-calendar-days",
            "summary-days-with",
            "summary-days-without",
            "summary-coverage",
            "summary-average",
        }
        self.assertTrue(expected_ids.issubset(self.document.attributes_by_id))

        for field in (
            "event_count",
            "calendar_day_count",
            "days_with_logged_events",
            "days_without_logged_events",
            "logging_coverage_ratio",
            "average_events_per_logged_day",
        ):
            with self.subTest(field=field):
                self.assertIn(field, self.javascript)

    def test_daily_chart_preserves_zero_filled_buckets_and_exact_counts(self) -> None:
        self.assertIn("report.days.forEach((day)", self.javascript)
        self.assertIn("count.textContent = String(day.event_count);", self.javascript)
        self.assertIn("`${readableDate}: ${day.event_count} events`", self.javascript)
        self.assertIn("selectedInput.value = day.date;", self.javascript)
        self.assertIn("overflow-x: auto", self.css)
        self.assertIn("height: max(4px", self.css)
        self.assertIn('bar.style.setProperty("--bar-height"', self.javascript)

    def test_empty_and_selected_day_states_remain_visible(self) -> None:
        for element_id in (
            "empty-state",
            "event-name-empty",
            "selected-day-empty",
            "selected-day-count",
            "selected-day-totals",
        ):
            self.assertIn(element_id, self.document.attributes_by_id)

        self.assertIn("emptyState.hidden = report.summary.event_count !== 0;", self.javascript)
        self.assertIn("emptyMessage.hidden = totals.length !== 0;", self.javascript)

    def test_event_name_labels_are_rendered_with_safe_dom_apis(self) -> None:
        self.assertIn("label.textContent = total.label;", self.javascript)
        self.assertIn("list.replaceChildren();", self.javascript)
        self.assertNotIn("innerHTML", self.javascript)
        self.assertNotIn("insertAdjacentHTML", self.javascript)

    def test_error_envelopes_are_mapped_without_raw_failure_output(self) -> None:
        for code in (
            "missing_parameter",
            "invalid_date_format",
            "start_after_end",
            "range_too_large",
            "selected_date_out_of_range",
            "internal_error",
        ):
            with self.subTest(code=code):
                self.assertIn(code, self.javascript)

        self.assertIn("publicErrorMessage(errorCodeFromResponse(body))", self.javascript)
        self.assertNotIn("response.text", self.javascript)
        self.assertNotIn("JSON.stringify", self.javascript)
        self.assertNotIn("error.message", self.javascript)

    def test_dashboard_has_no_external_storage_analytics_or_console_use(self) -> None:
        combined = "\n".join((self.html, self.css, self.javascript))

        for prohibited in (
            "localStorage",
            "sessionStorage",
            "indexedDB",
            "document.cookie",
            "serviceWorker",
            "console.",
            "eval(",
            "new Function",
            "analytics",
            "telemetry",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, combined)

        self.assertTrue(
            all(url.startswith("/static/") for url in self.document.resource_urls)
        )

    def test_unexpected_or_prohibited_response_fields_are_rejected(self) -> None:
        self.assertIn("PROHIBITED_FIELDS", self.javascript)
        self.assertIn("!hasProhibitedField(report)", self.javascript)

        for field in (
            "source_event_id",
            "occurred_at",
            "created_at",
            "database_path",
            "sync_status",
        ):
            with self.subTest(field=field):
                self.assertIn(f'"{field}"', self.javascript)

    def test_quality_and_privacy_contract_fields_are_rendered(self) -> None:
        for field in (
            "invalid_occurred_at_count",
            "blank_event_name_count",
            "timezone_history_available",
            "aggregate_only",
            "includes_event_name_labels",
            "includes_details",
            "includes_identifiers",
            "includes_individual_timestamps",
        ):
            with self.subTest(field=field):
                self.assertIn(field, self.javascript)

        self.assertIn("entire corpus", self.html)
        self.assertIn("selected range", self.html)

    def test_layout_declares_narrow_wide_and_overflow_behavior(self) -> None:
        self.assertIn("@media (max-width: 760px)", self.css)
        self.assertIn("@media (min-width: 980px)", self.css)
        self.assertIn("max-width: 100%", self.css)
        self.assertIn("overflow-x: auto", self.css)
        self.assertIn("grid-template-columns: 1fr", self.css)
        self.assertIn(".field-group {\n    min-width: 0;", self.css)
        self.assertIn("flex-wrap: wrap", self.css)

    def test_synthetic_endpoint_integration_returns_dashboard_contract(self) -> None:
        response = self.client.get(
            "/api/v1/daily-context",
            params={
                "start": "2026-08-18",
                "end": "2026-08-19",
                "selected_date": "2026-08-18",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["contract_version"], "daily-context.v1")
        self.assertEqual(response.json()["summary"]["event_count"], 1)
        self.assertEqual(response.json()["days"][1]["event_count"], 0)
        self.assertEqual(
            response.json()["selected_day"]["event_name_totals"],
            [{"label": "Synthetic dashboard event", "event_count": 1}],
        )

    def test_import_does_not_open_database_or_start_server(self) -> None:
        script = (
            "from unittest.mock import patch\n"
            "with patch('sqlite3.connect', side_effect=RuntimeError('opened')), "
            "patch('uvicorn.run', side_effect=RuntimeError('started')):\n"
            "    import app.server\n"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertNotIn("opened", completed.stderr)
        self.assertNotIn("started", completed.stderr)


if __name__ == "__main__":
    unittest.main()
