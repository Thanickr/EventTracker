(function () {
    "use strict";

    const API_PATH = "/api/v1/daily-context";
    const CONTRACT_VERSION = "daily-context.v1";
    const PROHIBITED_FIELDS = new Set([
        "id",
        "source_event_id",
        "created_at",
        "occurred_at",
        "note",
        "details",
        "database_path",
        "receipt",
        "sync_status",
    ]);

    const form = document.getElementById("dashboard-form");
    const startInput = document.getElementById("start-date");
    const endInput = document.getElementById("end-date");
    const selectedInput = document.getElementById("selected-date");
    const loadButton = document.getElementById("load-button");
    const todayButton = document.getElementById("today-button");
    const presetButtons = Array.from(
        document.querySelectorAll("[data-day-count]")
    );
    const statusMessage = document.getElementById("dashboard-status");
    const errorMessage = document.getElementById("dashboard-error");
    const dashboardContent = document.getElementById("dashboard-content");
    const emptyState = document.getElementById("empty-state");

    let requestSequence = 0;
    let activeController = null;

    function toLocalDateValue(value) {
        const year = String(value.getFullYear()).padStart(4, "0");
        const month = String(value.getMonth() + 1).padStart(2, "0");
        const day = String(value.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function addLocalDays(value, dayCount) {
        const result = new Date(
            value.getFullYear(),
            value.getMonth(),
            value.getDate()
        );
        result.setDate(result.getDate() + dayCount);
        return result;
    }

    function setDefaultDates() {
        const end = new Date();
        const start = addLocalDays(end, -29);
        endInput.value = toLocalDateValue(end);
        startInput.value = toLocalDateValue(start);
        selectedInput.value = endInput.value;
    }

    function parseDateValue(value) {
        if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)) {
            return null;
        }

        const parts = value.split("-").map(Number);
        const parsed = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));

        if (
            parsed.getUTCFullYear() !== parts[0]
            || parsed.getUTCMonth() !== parts[1] - 1
            || parsed.getUTCDate() !== parts[2]
        ) {
            return null;
        }

        return parsed;
    }

    function shiftDateValue(value, dayCount) {
        const parsed = parseDateValue(value);

        if (parsed === null) {
            return null;
        }

        parsed.setUTCDate(parsed.getUTCDate() + dayCount);
        const year = String(parsed.getUTCFullYear()).padStart(4, "0");
        const month = String(parsed.getUTCMonth() + 1).padStart(2, "0");
        const day = String(parsed.getUTCDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function validateControls() {
        const start = parseDateValue(startInput.value);
        const end = parseDateValue(endInput.value);
        const selected = parseDateValue(selectedInput.value);

        if (start === null || end === null || selected === null) {
            return "Enter a valid start, end, and selected date.";
        }

        if (start > end) {
            return "The start date must not be after the end date.";
        }

        const calendarDayCount = Math.round((end - start) / 86400000) + 1;

        if (calendarDayCount > 90) {
            return "Choose a date range of 90 days or fewer.";
        }

        if (selected < start || selected > end) {
            return "The selected date must be inside the date range.";
        }

        return null;
    }

    function setBusy(isBusy) {
        loadButton.disabled = isBusy;
        todayButton.disabled = isBusy;
        presetButtons.forEach((button) => {
            button.disabled = isBusy;
        });
        loadButton.textContent = isBusy ? "Loading…" : "Load dashboard";
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.hidden = false;
    }

    function clearError() {
        errorMessage.textContent = "";
        errorMessage.hidden = true;
    }

    function hasProhibitedField(value) {
        if (Array.isArray(value)) {
            return value.some(hasProhibitedField);
        }

        if (value !== null && typeof value === "object") {
            return Object.entries(value).some(([key, child]) => (
                PROHIBITED_FIELDS.has(key) || hasProhibitedField(child)
            ));
        }

        return false;
    }

    function isCount(value) {
        return Number.isInteger(value) && value >= 0;
    }

    function isNameTotal(value) {
        return value !== null
            && typeof value === "object"
            && hasExactKeys(value, ["label", "event_count"])
            && typeof value.label === "string"
            && isCount(value.event_count);
    }

    function hasExactKeys(value, expectedKeys) {
        const actualKeys = Object.keys(value).sort();
        const sortedExpectedKeys = [...expectedKeys].sort();
        return actualKeys.length === sortedExpectedKeys.length
            && actualKeys.every((key, index) => key === sortedExpectedKeys[index]);
    }

    function isExpectedReport(report) {
        return report !== null
            && typeof report === "object"
            && hasExactKeys(report, [
                "contract_version",
                "range",
                "summary",
                "days",
                "event_name_totals",
                "selected_day",
                "quality",
                "privacy",
            ])
            && report.contract_version === CONTRACT_VERSION
            && report.range !== null
            && typeof report.range === "object"
            && hasExactKeys(report.range, [
                "start",
                "end",
                "selected_date",
                "calendar_day_count",
                "calendar_basis",
            ])
            && typeof report.range.start === "string"
            && typeof report.range.end === "string"
            && typeof report.range.selected_date === "string"
            && isCount(report.range.calendar_day_count)
            && report.range.calendar_basis === "stored-local-date"
            && report.summary !== null
            && typeof report.summary === "object"
            && hasExactKeys(report.summary, [
                "event_count",
                "days_with_logged_events",
                "days_without_logged_events",
                "logging_coverage_ratio",
                "average_events_per_logged_day",
            ])
            && isCount(report.summary.event_count)
            && isCount(report.summary.days_with_logged_events)
            && isCount(report.summary.days_without_logged_events)
            && typeof report.summary.logging_coverage_ratio === "number"
            && (
                report.summary.average_events_per_logged_day === null
                || typeof report.summary.average_events_per_logged_day === "number"
            )
            && Array.isArray(report.days)
            && report.days.length === report.range.calendar_day_count
            && report.days.every((day) => (
                day !== null
                && typeof day === "object"
                && hasExactKeys(day, ["date", "event_count"])
                && typeof day.date === "string"
                && isCount(day.event_count)
            ))
            && Array.isArray(report.event_name_totals)
            && report.event_name_totals.every(isNameTotal)
            && report.selected_day !== null
            && typeof report.selected_day === "object"
            && hasExactKeys(report.selected_day, [
                "date",
                "event_count",
                "event_name_totals",
            ])
            && typeof report.selected_day.date === "string"
            && report.selected_day.date === report.range.selected_date
            && isCount(report.selected_day.event_count)
            && Array.isArray(report.selected_day.event_name_totals)
            && report.selected_day.event_name_totals.every(isNameTotal)
            && report.quality !== null
            && typeof report.quality === "object"
            && hasExactKeys(report.quality, [
                "invalid_occurred_at_count",
                "invalid_occurred_at_scope",
                "blank_event_name_count",
                "blank_event_name_scope",
                "timezone_history_available",
            ])
            && isCount(report.quality.invalid_occurred_at_count)
            && report.quality.invalid_occurred_at_scope === "corpus"
            && isCount(report.quality.blank_event_name_count)
            && report.quality.blank_event_name_scope === "window"
            && typeof report.quality.timezone_history_available === "boolean"
            && report.privacy !== null
            && typeof report.privacy === "object"
            && hasExactKeys(report.privacy, [
                "aggregate_only",
                "includes_event_name_labels",
                "includes_details",
                "includes_identifiers",
                "includes_individual_timestamps",
            ])
            && report.privacy.aggregate_only === true
            && report.privacy.includes_event_name_labels === true
            && report.privacy.includes_details === false
            && report.privacy.includes_identifiers === false
            && report.privacy.includes_individual_timestamps === false
            && !hasProhibitedField(report);
    }

    function formatDate(value) {
        const parsed = parseDateValue(value);

        if (parsed === null) {
            return "Unknown date";
        }

        return new Intl.DateTimeFormat(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
            timeZone: "UTC",
        }).format(parsed);
    }

    function replaceCountList(list, emptyMessage, totals) {
        list.replaceChildren();
        emptyMessage.hidden = totals.length !== 0;

        totals.forEach((total) => {
            const item = document.createElement("li");
            const label = document.createElement("span");
            const count = document.createElement("span");
            label.className = "count-label";
            count.className = "count-value";
            label.textContent = total.label;
            count.textContent = String(total.event_count);
            item.append(label, count);
            list.append(item);
        });
    }

    function renderSummary(report) {
        document.getElementById("range-label").textContent = (
            `${formatDate(report.range.start)} – ${formatDate(report.range.end)}`
        );
        document.getElementById("summary-events").textContent = (
            String(report.summary.event_count)
        );
        document.getElementById("summary-calendar-days").textContent = (
            String(report.range.calendar_day_count)
        );
        document.getElementById("summary-days-with").textContent = (
            String(report.summary.days_with_logged_events)
        );
        document.getElementById("summary-days-without").textContent = (
            String(report.summary.days_without_logged_events)
        );
        document.getElementById("summary-coverage").textContent = (
            `${(report.summary.logging_coverage_ratio * 100).toFixed(1)}%`
        );
        document.getElementById("summary-average").textContent = (
            report.summary.average_events_per_logged_day === null
                ? "—"
                : String(report.summary.average_events_per_logged_day)
        );
        emptyState.hidden = report.summary.event_count !== 0;
    }

    function renderDailyChart(report) {
        const chart = document.getElementById("daily-chart");
        const maximum = Math.max(1, ...report.days.map((day) => day.event_count));
        chart.replaceChildren();

        report.days.forEach((day) => {
            const item = document.createElement("li");
            const button = document.createElement("button");
            const bar = document.createElement("span");
            const count = document.createElement("span");
            const dateLabel = document.createElement("span");
            const readableDate = formatDate(day.date);

            item.className = "daily-chart-item";
            button.className = "daily-bar-button";
            button.type = "button";
            button.setAttribute(
                "aria-label",
                `${readableDate}: ${day.event_count} events`
            );

            if (day.date === report.range.selected_date) {
                button.setAttribute("aria-current", "date");
            }

            bar.className = "daily-bar";
            bar.setAttribute("aria-hidden", "true");
            const barHeight = Math.round((day.event_count / maximum) * 170);
            bar.style.setProperty("--bar-height", `${barHeight}px`);
            count.className = "daily-count";
            count.textContent = String(day.event_count);
            dateLabel.className = "daily-date-label";
            dateLabel.textContent = readableDate;

            button.addEventListener("click", () => {
                selectedInput.value = day.date;
                loadDashboard();
            });
            button.append(bar, count, dateLabel);
            item.append(button);
            chart.append(item);
        });
    }

    function appendDiagnostic(list, labelText, valueText) {
        const row = document.createElement("div");
        const label = document.createElement("dt");
        const value = document.createElement("dd");
        label.textContent = labelText;
        value.textContent = valueText;
        row.append(label, value);
        list.append(row);
    }

    function yesOrNo(value) {
        return value === true ? "Yes" : "No";
    }

    function renderDetails(report) {
        replaceCountList(
            document.getElementById("event-name-totals"),
            document.getElementById("event-name-empty"),
            report.event_name_totals
        );
        document.getElementById("selected-day-date").textContent = (
            formatDate(report.selected_day.date)
        );
        document.getElementById("selected-day-count").textContent = (
            String(report.selected_day.event_count)
        );
        replaceCountList(
            document.getElementById("selected-day-totals"),
            document.getElementById("selected-day-empty"),
            report.selected_day.event_name_totals
        );

        document.getElementById("quality-invalid").textContent = (
            String(report.quality.invalid_occurred_at_count)
        );
        document.getElementById("quality-blank").textContent = (
            String(report.quality.blank_event_name_count)
        );
        document.getElementById("timezone-note").textContent = (
            report.quality.timezone_history_available
                ? "Validated timezone history is available."
                : "Stored timestamps do not provide validated timezone history."
        );

        const privacyList = document.getElementById("privacy-list");
        privacyList.replaceChildren();
        appendDiagnostic(
            privacyList,
            "Aggregate-only response",
            yesOrNo(report.privacy.aggregate_only)
        );
        appendDiagnostic(
            privacyList,
            "Event-name labels included",
            yesOrNo(report.privacy.includes_event_name_labels)
        );
        appendDiagnostic(
            privacyList,
            "Details included",
            yesOrNo(report.privacy.includes_details)
        );
        appendDiagnostic(
            privacyList,
            "Identifiers included",
            yesOrNo(report.privacy.includes_identifiers)
        );
        appendDiagnostic(
            privacyList,
            "Individual timestamps included",
            yesOrNo(report.privacy.includes_individual_timestamps)
        );
    }

    function renderReport(report) {
        renderSummary(report);
        renderDailyChart(report);
        renderDetails(report);
        dashboardContent.hidden = false;
    }

    function publicErrorMessage(code) {
        const messages = {
            missing_parameter: "Choose both a start and end date.",
            invalid_date_format: "One or more dates are invalid.",
            start_after_end: "The start date must not be after the end date.",
            range_too_large: "Choose a date range of 90 days or fewer.",
            selected_date_out_of_range: "The selected date must be inside the date range.",
            internal_error: "The dashboard could not be loaded. Please try again.",
        };
        return messages[code] || "The dashboard could not be loaded. Please try again.";
    }

    function errorCodeFromResponse(value) {
        if (
            value !== null
            && typeof value === "object"
            && value.error !== null
            && typeof value.error === "object"
            && typeof value.error.code === "string"
        ) {
            return value.error.code;
        }

        return null;
    }

    async function loadDashboard(event) {
        if (event !== undefined) {
            event.preventDefault();

            if (loadButton.disabled) {
                return;
            }
        }

        const validationMessage = validateControls();

        if (validationMessage !== null) {
            statusMessage.textContent = "";
            dashboardContent.hidden = true;
            showError(validationMessage);
            return;
        }

        requestSequence += 1;
        const currentRequest = requestSequence;

        if (activeController !== null) {
            activeController.abort();
        }

        const controller = new AbortController();
        activeController = controller;
        clearError();
        setBusy(true);
        dashboardContent.hidden = true;
        statusMessage.textContent = "Loading Daily Context…";

        const parameters = new URLSearchParams({
            start: startInput.value,
            end: endInput.value,
            selected_date: selectedInput.value,
        });

        try {
            const response = await fetch(`${API_PATH}?${parameters.toString()}`, {
                method: "GET",
                headers: {Accept: "application/json"},
                cache: "no-store",
                signal: controller.signal,
            });
            let body = null;

            try {
                body = await response.json();
            } catch (_error) {
                body = null;
            }

            if (currentRequest !== requestSequence) {
                return;
            }

            if (!response.ok) {
                showError(publicErrorMessage(errorCodeFromResponse(body)));
                statusMessage.textContent = "";
                return;
            }

            if (!isExpectedReport(body)) {
                showError("The server returned an unexpected dashboard response.");
                statusMessage.textContent = "";
                return;
            }

            renderReport(body);
            statusMessage.textContent = "Daily Context loaded.";
        } catch (error) {
            if (
                (error !== null && error !== undefined && error.name === "AbortError")
                || currentRequest !== requestSequence
            ) {
                return;
            }

            showError("The local dashboard server is unavailable. Try again when it is running.");
            statusMessage.textContent = "";
        } finally {
            if (currentRequest === requestSequence) {
                setBusy(false);
                activeController = null;
            }
        }
    }

    form.addEventListener("submit", loadDashboard);
    todayButton.addEventListener("click", () => {
        setDefaultDates();
        loadDashboard();
    });
    presetButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const dayCount = Number(button.dataset.dayCount);
            const start = shiftDateValue(endInput.value, -(dayCount - 1));

            if (start === null) {
                showError("Enter a valid end date before choosing a quick range.");
                return;
            }

            startInput.value = start;
            selectedInput.value = endInput.value;
            loadDashboard();
        });
    });

    setDefaultDates();
    loadDashboard();
}());
