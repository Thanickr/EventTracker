const eventNameInput =
    document.getElementById("event-name");

const detailsInput =
    document.getElementById("details");

const useCustomTimeInput =
    document.getElementById("use-custom-time");

const customTimeFields =
    document.getElementById("custom-time-fields");

const occurredAtInput =
    document.getElementById("occurred-at");

const saveButton =
    document.getElementById("save-button");

const statusMessage =
    document.getElementById("status-message");

const eventsList =
    document.getElementById("events-list");

const exportPendingButton =
    document.getElementById(
        "export-pending-button"
    );

const applyReceiptButton =
    document.getElementById(
        "apply-receipt-button"
    );

const receiptFileInput =
    document.getElementById(
        "receipt-file"
    );

const syncStatusMessage =
    document.getElementById(
        "sync-status-message"
    );

const localEventCount =
    document.getElementById("local-event-count");

const toggleEventsButton =
    document.getElementById("toggle-events-button");

const clearLocalEventsButton =
    document.getElementById(
        "clear-local-events-button"
    );

const deviceStorageStatus =
    document.getElementById(
        "device-storage-status"
    );

const editActions =
    document.getElementById("edit-actions");

const cancelEditButton =
    document.getElementById("cancel-edit-button");

let editingEventId = null;
let editingCreatedAt = null;

let editingOriginalAmount = null;
let editingOriginalUnit = null;

const showAllEventsButton =
    document.getElementById(
        "show-all-events-button"
    );

const DEFAULT_RECENT_EVENT_LIMIT = 20;

let showAllRecentEvents = false;

const eventViewControls =
    document.getElementById(
        "event-view-controls"
    );

const timelineViewButton =
    document.getElementById(
        "timeline-view-button"
    );

const listViewButton =
    document.getElementById(
        "list-view-button"
    );

const timelineView =
    document.getElementById(
        "timeline-view"
    );

const listView =
    document.getElementById(
        "list-view"
    );

const timelineScroll =
    document.getElementById(
        "timeline-scroll"
    );

const timeline =
    document.getElementById(
        "timeline"
    );

const previousDayButton =
    document.getElementById(
        "previous-day-button"
    );

const nextDayButton =
    document.getElementById(
        "next-day-button"
    );

const selectedDayButton =
    document.getElementById(
        "selected-day-button"
    );

const timelineFocusControls =
    document.getElementById(
        "timeline-focus-controls"
    );

const timelineBackButton =
    document.getElementById(
        "timeline-back-button"
    );

const timelineFocusLabel =
    document.getElementById(
        "timeline-focus-label"
    );

const EVENT_VIEW_MODE_KEY =
    "event-tracker-view-mode";

const DAY_HOUR_HEIGHT_PIXELS = 72;
const DAY_TIMELINE_TOP_PADDING_PIXELS = 24;
const DAY_TIMELINE_BOTTOM_PADDING_PIXELS = 24;
const DAY_EVENT_MARKER_HEIGHT_PIXELS = 52;
const TIMELINE_HEIGHT_PIXELS =
    DAY_TIMELINE_TOP_PADDING_PIXELS +
    24 * DAY_HOUR_HEIGHT_PIXELS +
    DAY_TIMELINE_BOTTOM_PADDING_PIXELS;
const FOCUSED_TIMELINE_MINUTES = 15;
const FOCUSED_EVENT_GAP_PIXELS = 52;
const FOCUSED_TIMELINE_PADDING_PIXELS = 24;

let selectedDay = startOfLocalDay(
    new Date()
);

let focusedTimelineEventIds = null;
let timelineScrollTargetDate = null;
let shouldAutoScrollTimeline = true;

function startOfLocalDay(date) {
    const day = new Date(date);

    day.setHours(0, 0, 0, 0);

    return day;
}


function addDays(date, numberOfDays) {
    const result = new Date(date);

    result.setDate(
        result.getDate() + numberOfDays
    );

    return startOfLocalDay(result);
}


function datesAreSameLocalDay(
    firstDate,
    secondDate
) {
    return (
        firstDate.getFullYear() ===
            secondDate.getFullYear() &&
        firstDate.getMonth() ===
            secondDate.getMonth() &&
        firstDate.getDate() ===
            secondDate.getDate()
    );
}


function parseLocalTimestamp(timestamp) {
    if (
        typeof timestamp !== "string" ||
        !timestamp.trim()
    ) {
        return null;
    }

    const parsedDate = new Date(timestamp);

    if (
        Number.isNaN(
            parsedDate.getTime()
        )
    ) {
        return null;
    }

    return parsedDate;
}


function formatSelectedDay(date) {
    const today =
        startOfLocalDay(new Date());

    if (
        datesAreSameLocalDay(
            date,
            today
        )
    ) {
        return "Today";
    }

    return date.toLocaleDateString(
        undefined,
        {
            weekday: "short",
            month: "short",
            day: "numeric",
            year:
                date.getFullYear() ===
                today.getFullYear()
                    ? undefined
                    : "numeric",
        }
    );
}

function populateCustomTimestamp(timestamp) {
    if (!timestamp) {
        resetTimestampControls();
        return;
    }

    useCustomTimeInput.checked = true;
    customTimeFields.hidden = false;
    occurredAtInput.value = timestamp.slice(0, 16);
}


function beginEditMode(event) {
    editingEventId = event.id;
    editingCreatedAt = event.created_at;

    eventNameInput.value =
        event.exercise_type || "";

    editingOriginalAmount =
    event.amount ?? null;

    editingOriginalUnit =
    event.unit ?? null;

    detailsInput.value =
        event.note || "";

    populateCustomTimestamp(
        event.occurred_at
    );

    editActions.hidden = false;
    saveButton.textContent = "Update Event";

    statusMessage.textContent =
        "Editing local event.";

    eventNameInput.focus();

    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });
}


function resetEventForm() {
    editingEventId = null;
    editingCreatedAt = null;

    editingOriginalAmount = null;
    editingOriginalUnit = null;

    editActions.hidden = true;
    saveButton.textContent = "Save Event";

    eventNameInput.value = "";
    detailsInput.value = "";

    resetTimestampControls();

    eventNameInput.focus();
}


async function editLocalEvent(eventId) {
    try {
        const event =
            await getLocalEvent(eventId);

        if (!event) {
            throw new Error(
                "This local event could not be found."
            );
        }

        beginEditMode(event);
    } catch (error) {
        statusMessage.textContent =
            error.message ||
            "Unable to edit this event.";

        console.error(
            "Unable to load event for editing:",
            error
        );
    }
}

function getCurrentLocalTimestamp() {
    const now = new Date();
    const offsetMilliseconds =
        now.getTimezoneOffset() * 60_000;

    return new Date(
        now.getTime() - offsetMilliseconds
    )
        .toISOString()
        .slice(0, 19);
}


function formatEventTime(timestamp) {
    const parsedTimestamp = new Date(timestamp);

    if (Number.isNaN(parsedTimestamp.getTime())) {
        return timestamp;
    }

    return parsedTimestamp.toLocaleString();
}

function getDateTimeLocalValue(date = new Date()) {
    const offsetMilliseconds =
        date.getTimezoneOffset() * 60_000;

    return new Date(
        date.getTime() - offsetMilliseconds
    )
        .toISOString()
        .slice(0, 16);
}


function selectedOccurredAt() {
    if (!useCustomTimeInput.checked) {
        return getCurrentLocalTimestamp();
    }

    const customTimestamp =
        occurredAtInput.value.trim();

    if (!customTimestamp) {
        throw new Error(
            "Choose the event date and time."
        );
    }

    // datetime-local returns local time without a zone.
    // Seconds are added to match the existing timestamp format.
    return `${customTimestamp}:00`;
}


function toggleCustomTimeFields() {
    const useCustomTime =
        useCustomTimeInput.checked;

    customTimeFields.hidden =
        !useCustomTime;

    if (
        useCustomTime &&
        !occurredAtInput.value
    ) {
        occurredAtInput.value =
            getDateTimeLocalValue();
    }
}


function resetTimestampControls() {
    useCustomTimeInput.checked = false;
    occurredAtInput.value = "";
    customTimeFields.hidden = true;
}

const EVENTS_VISIBILITY_KEY =
    "event-tracker-show-recent-events";


function recentEventsAreVisible() {
    const savedValue =
        localStorage.getItem(EVENTS_VISIBILITY_KEY);

    return savedValue !== "false";
}


function applyRecentEventsVisibility() {
    const isVisible =
        recentEventsAreVisible();

    eventViewControls.hidden =
        !isVisible;

    timelineView.hidden =
        !isVisible ||
        currentEventViewMode() !==
            "timeline";

    listView.hidden =
        !isVisible ||
        currentEventViewMode() !==
            "list";

    toggleEventsButton.textContent =
        isVisible ? "Hide" : "Show";
}


function toggleRecentEventsVisibility() {
    const newVisibility =
        !recentEventsAreVisible();

    localStorage.setItem(
        EVENTS_VISIBILITY_KEY,
        String(newVisibility)
    );

    applyRecentEventsVisibility();

    if (
        newVisibility &&
        currentEventViewMode() ===
            "timeline"
    ) {
        shouldAutoScrollTimeline = true;
        loadEvents();
    }
}

async function confirmAndDeleteLocalEvent(event) {
    const eventName =
        event.exercise_type || "this event";

    const confirmed = window.confirm(
        `Delete "${eventName}" from this device?\n\n` +
        `This cannot be undone unless the event ` +
        `has already been synchronized or backed up.`
    );

    if (!confirmed) {
        return;
    }

    try {
        await deleteLocalEvent(event.id);

        if (editingEventId === event.id) {
            resetEventForm();
        }

        statusMessage.textContent =
            "Local event deleted.";

        await loadEvents();
    } catch (error) {
        statusMessage.textContent =
            "Unable to delete this event.";

        console.error(
            "Local event deletion failed:",
            error
        );
    }
}

function currentEventViewMode() {
    const savedMode =
        localStorage.getItem(
            EVENT_VIEW_MODE_KEY
        );

    return savedMode === "list"
        ? "list"
        : "timeline";
}


function applyEventViewMode() {
    const viewMode =
        currentEventViewMode();

    const timelineIsActive =
        viewMode === "timeline";

    timelineView.hidden =
        !timelineIsActive;

    listView.hidden =
        timelineIsActive;

    timelineViewButton.classList.toggle(
        "active",
        timelineIsActive
    );

    listViewButton.classList.toggle(
        "active",
        !timelineIsActive
    );
}


function setEventViewMode(viewMode) {
    localStorage.setItem(
        EVENT_VIEW_MODE_KEY,
        viewMode
    );

    applyEventViewMode();
}


function selectTimelineView() {
    shouldAutoScrollTimeline = true;
    setEventViewMode("timeline");
    loadEvents();
}


function selectListView() {
    setEventViewMode("list");
}

async function changeSelectedDay(
    numberOfDays
) {
    focusedTimelineEventIds = null;
    timelineScrollTargetDate = null;
    shouldAutoScrollTimeline = true;

    selectedDay = addDays(
        selectedDay,
        numberOfDays
    );

    await loadEvents();
}


async function returnToToday() {
    focusedTimelineEventIds = null;
    timelineScrollTargetDate = null;
    shouldAutoScrollTimeline = true;

    selectedDay =
        startOfLocalDay(new Date());

    await loadEvents();
}


function updateSelectedDayLabel() {
    selectedDayButton.textContent =
        formatSelectedDay(
            selectedDay
        );
}

function eventsForSelectedDay(events) {
    return events.filter((event) => {
        const occurredAt =
            parseLocalTimestamp(
                event.occurred_at
            );

        if (!occurredAt) {
            return false;
        }

        return datesAreSameLocalDay(
            occurredAt,
            selectedDay
        );
    });
}

function minutesSinceStartOfDay(date) {
    return (
        date.getHours() * 60 +
        date.getMinutes() +
        date.getSeconds() / 60
    );
}


function timelinePositionPixels(date) {
    const minutes =
        minutesSinceStartOfDay(date);

    return (
        DAY_TIMELINE_TOP_PADDING_PIXELS +
        (
            minutes / 60
        ) * DAY_HOUR_HEIGHT_PIXELS
    );
}


function formatTimelineTime(date) {
    return date.toLocaleTimeString(
        undefined,
        {
            hour: "numeric",
            minute: "2-digit",
        }
    );
}

function renderTimelineGrid() {
    timeline.innerHTML = "";
    timeline.classList.remove(
        "timeline-focused"
    );
    timeline.style.height =
        `${TIMELINE_HEIGHT_PIXELS}px`;
    timeline.style.minHeight =
        `${TIMELINE_HEIGHT_PIXELS}px`;

    for (
        let hour = 0;
        hour <= 24;
        hour += 1
    ) {
        const top =
            DAY_TIMELINE_TOP_PADDING_PIXELS +
            hour * DAY_HOUR_HEIGHT_PIXELS;

        const label =
            document.createElement("div");

        label.className =
            "timeline-hour-label";

        label.style.top =
            `${top}px`;

        if (hour < 24) {
            const labelDate =
                new Date(selectedDay);

            labelDate.setHours(
                hour,
                0,
                0,
                0
            );

            label.textContent =
                labelDate.toLocaleTimeString(
                    undefined,
                    {
                        hour: "numeric",
                    }
                );
        }

        const line =
            document.createElement("div");

        line.className =
            "timeline-hour-line";

        line.style.top =
            `${top}px`;

        timeline.appendChild(label);
        timeline.appendChild(line);
    }
}

function timelineEntries(events) {
    return events
        .map((event) => ({
            event,
            occurredAt:
                parseLocalTimestamp(
                    event.occurred_at
                ),
        }))
        .filter(
            (entry) => entry.occurredAt
        )
        .sort(
            (first, second) =>
                first.occurredAt -
                second.occurredAt
        );
}


function groupDayTimelineEntries(entries) {
    const groups = [];

    let currentGroup = [];
    let groupStartPosition = null;

    for (const entry of entries) {
        const entryPosition =
            timelinePositionPixels(
                entry.occurredAt
            );

        if (
            currentGroup.length === 0 ||
            entryPosition -
                groupStartPosition <
                DAY_EVENT_MARKER_HEIGHT_PIXELS
        ) {
            currentGroup.push(entry);

            if (groupStartPosition === null) {
                groupStartPosition =
                    entryPosition;
            }

            continue;
        }

        groups.push(currentGroup);
        currentGroup = [entry];
        groupStartPosition = entryPosition;
    }

    if (currentGroup.length > 0) {
        groups.push(currentGroup);
    }

    return groups;
}


function formatTimelineRange(entries) {
    const firstTime =
        formatTimelineTime(
            entries[0].occurredAt
        );

    const lastTime =
        formatTimelineTime(
            entries[
                entries.length - 1
            ].occurredAt
        );

    return firstTime === lastTime
        ? firstTime
        : `${firstTime}–${lastTime}`;
}


function createTimelineEventButton(
    event,
    occurredAt
) {
    const eventButton =
        document.createElement("button");

    eventButton.type = "button";
    eventButton.className =
        "timeline-event";

    const name =
        document.createElement("div");

    name.className =
        "timeline-event-name";

    name.textContent =
        event.exercise_type;

    const time =
        document.createElement("div");

    time.className =
        "timeline-event-time";

    time.textContent =
        formatTimelineTime(occurredAt);

    eventButton.appendChild(name);
    eventButton.appendChild(time);

    if (event.note) {
        const details =
            document.createElement("div");

        details.className =
            "timeline-event-details";

        details.textContent =
            event.note;

        eventButton.appendChild(details);
    }

    eventButton.addEventListener(
        "click",
        () => editLocalEvent(event.id)
    );

    return eventButton;
}


function focusTimelineCluster(entries) {
    focusedTimelineEventIds =
        entries.map(
            (entry) => entry.event.id
        );

    timelineScrollTargetDate =
        new Date(entries[0].occurredAt);

    loadEvents();
}


function returnToDayTimeline() {
    focusedTimelineEventIds = null;
    shouldAutoScrollTimeline = true;
    loadEvents();
}


function createTimelineClusterButton(entries) {
    const clusterButton =
        document.createElement("button");

    clusterButton.type = "button";
    clusterButton.className =
        "timeline-cluster";

    const count =
        document.createElement("span");

    count.className =
        "timeline-cluster-count";
    count.textContent =
        String(entries.length);

    const summary =
        document.createElement("span");

    summary.className =
        "timeline-cluster-summary";

    const title =
        document.createElement("span");

    title.className =
        "timeline-cluster-title";
    title.textContent =
        `${entries.length} nearby events`;

    const time =
        document.createElement("span");

    time.className =
        "timeline-cluster-time";
    time.textContent =
        formatTimelineRange(entries);

    summary.appendChild(title);
    summary.appendChild(time);

    clusterButton.appendChild(count);
    clusterButton.appendChild(summary);

    clusterButton.setAttribute(
        "aria-label",
        `Open ${entries.length} events from ` +
            formatTimelineRange(entries)
    );

    clusterButton.addEventListener(
        "click",
        () => focusTimelineCluster(entries)
    );

    return clusterButton;
}


function renderDayTimeline(entries) {
    timelineFocusControls.hidden = true;
    renderTimelineGrid();

    if (entries.length === 0) {
        autoScrollDayTimeline(entries);
        return;
    }

    const groups =
        groupDayTimelineEntries(entries);

    for (const group of groups) {
        const top = Math.max(
            DAY_TIMELINE_TOP_PADDING_PIXELS,
            Math.min(
                timelinePositionPixels(
                    group[0].occurredAt
                ),
                TIMELINE_HEIGHT_PIXELS -
                    DAY_TIMELINE_BOTTOM_PADDING_PIXELS -
                    DAY_EVENT_MARKER_HEIGHT_PIXELS
            )
        );

        const marker =
            group.length === 1
                ? createTimelineEventButton(
                      group[0].event,
                      group[0].occurredAt
                  )
                : createTimelineClusterButton(
                      group
                  );

        marker.style.top = `${top}px`;
        timeline.appendChild(marker);
    }

    autoScrollDayTimeline(entries);
}


function preferredDayScrollDate(entries) {
    if (timelineScrollTargetDate) {
        return timelineScrollTargetDate;
    }

    const today =
        startOfLocalDay(new Date());

    if (
        datesAreSameLocalDay(
            selectedDay,
            today
        )
    ) {
        return new Date();
    }

    if (entries.length > 0) {
        return entries[0].occurredAt;
    }

    return selectedDay;
}


function autoScrollDayTimeline(entries) {
    if (
        !shouldAutoScrollTimeline ||
        currentEventViewMode() !==
            "timeline" ||
        !recentEventsAreVisible()
    ) {
        return;
    }

    const targetDate =
        preferredDayScrollDate(entries);

    shouldAutoScrollTimeline = false;
    timelineScrollTargetDate = null;

    requestAnimationFrame(() => {
        const targetPosition =
            timelinePositionPixels(
                targetDate
            );

        timelineScroll.scrollTop =
            Math.max(
                0,
                targetPosition -
                    DAY_HOUR_HEIGHT_PIXELS
            );
    });
}


function focusedTimelineRange(entries) {
    const firstTime =
        entries[0].occurredAt.getTime();

    const lastTime =
        entries[
            entries.length - 1
        ].occurredAt.getTime();

    const minimumSpan =
        FOCUSED_TIMELINE_MINUTES *
        60 *
        1000;

    const eventSpan =
        lastTime - firstTime;

    const desiredSpan = Math.max(
        minimumSpan,
        eventSpan + 10 * 60 * 1000
    );

    const center =
        (firstTime + lastTime) / 2;

    const dayStart =
        selectedDay.getTime();

    const dayEnd =
        addDays(selectedDay, 1).getTime();

    let start = Math.max(
        dayStart,
        center - desiredSpan / 2
    );

    let end = Math.min(
        dayEnd,
        start + desiredSpan
    );

    start = Math.max(
        dayStart,
        end - desiredSpan
    );

    return {
        start,
        end,
    };
}


function focusedGridIntervalMinutes(
    rangeMinutes
) {
    if (rangeMinutes <= 20) {
        return 2;
    }

    if (rangeMinutes <= 45) {
        return 5;
    }

    if (rangeMinutes <= 120) {
        return 15;
    }

    return 30;
}


function renderFocusedTimelineGrid(
    range,
    height
) {
    timeline.innerHTML = "";
    timeline.classList.add(
        "timeline-focused"
    );
    timeline.style.height = `${height}px`;
    timeline.style.minHeight = `${height}px`;

    const rangeMilliseconds =
        range.end - range.start;

    const rangeMinutes =
        rangeMilliseconds / (60 * 1000);

    const contentHeight =
        height -
        2 * FOCUSED_TIMELINE_PADDING_PIXELS;

    const intervalMilliseconds =
        focusedGridIntervalMinutes(
            rangeMinutes
        ) *
        60 *
        1000;

    let labelTime =
        Math.ceil(
            range.start /
                intervalMilliseconds
        ) * intervalMilliseconds;

    while (labelTime <= range.end) {
        const top =
            FOCUSED_TIMELINE_PADDING_PIXELS +
            (
                (labelTime - range.start) /
                rangeMilliseconds
            ) * contentHeight;

        const label =
            document.createElement("div");

        label.className =
            "timeline-hour-label";
        label.style.top = `${top}px`;
        label.textContent =
            formatTimelineTime(
                new Date(labelTime)
            );

        const line =
            document.createElement("div");

        line.className =
            "timeline-hour-line";
        line.style.top = `${top}px`;

        timeline.appendChild(label);
        timeline.appendChild(line);

        labelTime += intervalMilliseconds;
    }
}


function focusedTimelineTopPositions(
    entries,
    range,
    height
) {
    const maximumTop =
        height -
        FOCUSED_TIMELINE_PADDING_PIXELS -
        FOCUSED_EVENT_GAP_PIXELS;

    const contentHeight =
        height -
        2 * FOCUSED_TIMELINE_PADDING_PIXELS;

    const positions = [];

    for (const entry of entries) {
        const naturalTop =
            FOCUSED_TIMELINE_PADDING_PIXELS +
            (
                (
                    entry.occurredAt.getTime() -
                    range.start
                ) /
                (range.end - range.start)
            ) * contentHeight;

        const previousTop =
            positions.length > 0
                ? positions[
                      positions.length - 1
                  ]
                : null;

        positions.push(
            previousTop === null
                ? naturalTop
                : Math.max(
                      naturalTop,
                      previousTop +
                          FOCUSED_EVENT_GAP_PIXELS
                  )
        );
    }

    const overflow = Math.max(
        0,
        positions[positions.length - 1] -
            maximumTop
    );

    return positions.map(
        (position) =>
            Math.max(
                FOCUSED_TIMELINE_PADDING_PIXELS,
                position - overflow
            )
    );
}


function renderFocusedTimeline(entries) {
    const range =
        focusedTimelineRange(entries);

    const height = Math.max(
        600,
        entries.length *
            FOCUSED_EVENT_GAP_PIXELS +
            120
    );

    timelineFocusControls.hidden = false;
    timelineFocusLabel.textContent =
        `${entries.length} events · ` +
        formatTimelineRange(entries);

    renderFocusedTimelineGrid(
        range,
        height
    );

    const positions =
        focusedTimelineTopPositions(
            entries,
            range,
            height
        );

    entries.forEach((entry, index) => {
        const eventButton =
            createTimelineEventButton(
                entry.event,
                entry.occurredAt
            );

        eventButton.style.top =
            `${positions[index]}px`;

        timeline.appendChild(eventButton);
    });

    requestAnimationFrame(() => {
        timelineScroll.scrollTop = 0;
    });
}


function renderTimelineEvents(events) {
    const entries =
        timelineEntries(events);

    if (focusedTimelineEventIds) {
        const focusedIds =
            new Set(
                focusedTimelineEventIds
            );

        const focusedEntries =
            entries.filter(
                (entry) =>
                    focusedIds.has(
                        entry.event.id
                    )
            );

        if (focusedEntries.length > 0) {
            renderFocusedTimeline(
                focusedEntries
            );
            return;
        }

        focusedTimelineEventIds = null;
    }

    renderDayTimeline(entries);
}

function renderListEvents(events) {
    eventsList.innerHTML = "";

    if (events.length === 0) {
        eventsList.textContent =
            "No events recorded for this day.";

        showAllEventsButton.hidden =
            true;

        return;
    }

    const displayedEvents =
        showAllRecentEvents
            ? events
            : events.slice(
                  0,
                  DEFAULT_RECENT_EVENT_LIMIT
              );

    displayedEvents.forEach((event) => {
        const eventElement =
        document.createElement("article");

        eventElement.className = "event";

        const eventContent =
            document.createElement("button");

        eventContent.type = "button";
        eventContent.className =
            "event-content-button";

        eventContent.setAttribute(
            "aria-label",
            `Edit ${event.exercise_type}`
        );

        const main =
            document.createElement("div");

        main.className = "event-main";

        const hasStructuredAmount =
            event.amount !== null &&
            event.amount !== undefined;

        const hasStructuredUnit =
            typeof event.unit === "string" &&
            event.unit.trim();

        if (
            hasStructuredAmount &&
            hasStructuredUnit
        ) {
            main.textContent =
                `${event.exercise_type} ` +
                `${event.amount} ${event.unit}`;
        } else {
            main.textContent =
                event.exercise_type;
        }

        const meta =
            document.createElement("div");

        meta.className = "event-meta";
        meta.textContent =
            formatEventTime(event.occurred_at);

        eventContent.appendChild(main);
        eventContent.appendChild(meta);

        if (event.note) {
            const note =
                document.createElement("div");

            note.className = "event-details-preview";
            note.textContent = event.note;

            eventContent.appendChild(note);
        }

        eventContent.addEventListener(
            "click",
            () => editLocalEvent(event.id)
        );

        const actions =
            document.createElement("div");

        actions.className = "event-actions";

        const editButton =
            document.createElement("button");

        editButton.type = "button";
        editButton.className =
            "event-edit-button";
        editButton.textContent = "Edit";

        editButton.addEventListener(
            "click",
            () => editLocalEvent(event.id)
        );

        const deleteButton =
            document.createElement("button");

        deleteButton.type = "button";
        deleteButton.className =
            "event-delete-button";
        deleteButton.textContent = "Delete";

        deleteButton.addEventListener(
            "click",
            () =>
                confirmAndDeleteLocalEvent(event)
        );

        actions.appendChild(editButton);
        actions.appendChild(deleteButton);

        eventElement.appendChild(eventContent);
        eventElement.appendChild(actions);

        eventsList.appendChild(eventElement);
    });

    showAllEventsButton.hidden =
        events.length <=
        DEFAULT_RECENT_EVENT_LIMIT;

    showAllEventsButton.textContent =
        showAllRecentEvents
            ? "Show Recent"
            : `Show All (${events.length})`;
}

async function loadEvents() {
    try {
        const allEvents =
            await getLocalEvents();

        const dayEvents =
            eventsForSelectedDay(
                allEvents
            );

        localEventCount.textContent =
            dayEvents.length === 0
                ? "No events for this day."
                : `${dayEvents.length} event` +
                  `${dayEvents.length === 1 ? "" : "s"} ` +
                  `for this day.`;

        updateSelectedDayLabel();

        renderTimelineEvents(
            dayEvents
        );

        renderListEvents(
            dayEvents
        );

        applyEventViewMode();
        applyRecentEventsVisibility();
    } catch (error) {
        localEventCount.textContent =
            "Unable to load events.";

        timeline.innerHTML =
            "Unable to load the timeline.";

        eventsList.textContent =
            "Unable to load events.";

        console.error(
            "Unable to load events:",
            error
        );
    }
}


async function saveEvent() {
    const eventName =
        eventNameInput.value.trim();

    const details =
        detailsInput.value.trim();

    if (!eventName) {
        statusMessage.textContent =
            "Event is required.";

        return;
    }

    saveButton.disabled = true;
    statusMessage.textContent = "Saving...";

    try {
        const createdAt =
            editingCreatedAt ||
            getCurrentLocalTimestamp();

        const occurredAt =
            selectedOccurredAt();

        const event = {
            id:
                editingEventId ||
                createEventId(),

            created_at: createdAt,
            occurred_at: occurredAt,
            event_type: "event",

            // Retained temporarily for schema compatibility.
            exercise_type: eventName,

            amount:
                editingEventId !== null
                    ? editingOriginalAmount
                    : null,
            unit:
                editingEventId !== null
                    ? editingOriginalUnit
                    : null,
            note: details || null,

            // Editing a local event keeps it pending.
            sync_status: "pending",
        };

        const wasEditing =
            editingEventId !== null;

        await saveLocalEvent(event);
        
        resetEventForm();
        eventNameInput.focus();

        statusMessage.textContent =
            wasEditing
                ? "Event updated on this device."
                : "Saved on this device.";
        
        await loadEvents();

    } catch (error) {
        statusMessage.textContent =
            error.message ||
            "Error saving event.";

        console.error(
            "Unable to save event:",
            error
        );
    } finally {
        saveButton.disabled = false;
    }
}


function createBackupFilename() {
    const date = new Date()
        .toISOString()
        .slice(0, 10);

    return `event-tracker-backup-${date}.json`;
}

// Dormant full-backup utilities.
// Retained temporarily for possible future Advanced settings.
async function exportData() {
    exportButton.disabled = true;
    dataStatusMessage.textContent = "Preparing backup...";

    try {
        const events = await exportLocalEvents();

        const backup = {
            format: "event-tracker-backup",
            version: 1,
            exported_at: new Date().toISOString(),
            event_count: events.length,
            events,
        };

        const backupText = JSON.stringify(
            backup,
            null,
            2
        );

        const backupBlob = new Blob(
            [backupText],
            {
                type: "application/json",
            }
        );

        const backupUrl =
            URL.createObjectURL(backupBlob);

        const downloadLink =
            document.createElement("a");

        downloadLink.href = backupUrl;
        downloadLink.download =
            createBackupFilename();

        document.body.appendChild(downloadLink);
        downloadLink.click();
        downloadLink.remove();

        URL.revokeObjectURL(backupUrl);

        dataStatusMessage.textContent =
            `Exported ${events.length} events.`;
    } catch (error) {
        dataStatusMessage.textContent =
            "Unable to export data.";

        console.error(
            "Export failed:",
            error
        );
    } finally {
        exportButton.disabled = false;
    }
}


function chooseImportFile() {
    importFileInput.value = "";
    importFileInput.click();
}

// Dormant full-backup utilities.
// Retained temporarily for possible future Advanced settings.
async function importData(event) {
    const selectedFile =
        event.target.files[0];

    if (!selectedFile) {
        return;
    }

    importButton.disabled = true;
    dataStatusMessage.textContent =
        "Importing backup...";

    try {
        const fileText =
            await selectedFile.text();

        const backup =
            JSON.parse(fileText);

        if (
            backup.format !==
                "event-tracker-backup" ||
            backup.version !== 1 ||
            !Array.isArray(backup.events)
        ) {
            throw new Error(
                "This is not a valid Event Tracker backup."
            );
        }

        const importedCount =
            await importLocalEvents(
                backup.events
            );

        await loadEvents();

        dataStatusMessage.textContent =
            `Imported ${importedCount} events.`;
    } catch (error) {
        dataStatusMessage.textContent =
            "Unable to import this backup.";

        console.error(
            "Import failed:",
            error
        );
    } finally {
        importButton.disabled = false;
    }
}


async function initializeApplication() {
    applyRecentEventsVisibility();
    await loadEvents();
}


saveButton.addEventListener(
    "click",
    saveEvent
);

useCustomTimeInput.addEventListener(
    "change",
    toggleCustomTimeFields
);

exportPendingButton.addEventListener(
    "click",
    exportPendingEvents
);

applyReceiptButton.addEventListener(
    "click",
    chooseReceiptFile
);

receiptFileInput.addEventListener(
    "change",
    applySyncReceipt
);

toggleEventsButton.addEventListener(
    "click",
    toggleRecentEventsVisibility
);

clearLocalEventsButton.addEventListener(
    "click",
    clearLocalEvents
);

eventNameInput.addEventListener(
    "keydown",
    (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            saveEvent();
        }
    }
);


cancelEditButton.addEventListener(
    "click",
    () => {
        resetEventForm();

        statusMessage.textContent =
            "Edit canceled.";
    }
);

showAllEventsButton.addEventListener(
    "click",
    toggleShowAllRecentEvents
);

timelineViewButton.addEventListener(
    "click",
    selectTimelineView
);

listViewButton.addEventListener(
    "click",
    selectListView
);

previousDayButton.addEventListener(
    "click",
    () => changeSelectedDay(-1)
);

nextDayButton.addEventListener(
    "click",
    () => changeSelectedDay(1)
);

selectedDayButton.addEventListener(
    "click",
    returnToToday
);

timelineBackButton.addEventListener(
    "click",
    returnToDayTimeline
);


function createSyncPackageFilename() {
    const timestamp = new Date()
        .toISOString()
        .replaceAll(":", "-")
        .replaceAll(".", "-");

    return (
        `event-tracker-sync-package-` +
        `${timestamp}.json`
    );
}


function downloadJsonFile(data, filename) {
    const jsonText = JSON.stringify(
        data,
        null,
        2
    );

    const fileBlob = new Blob(
        [jsonText],
        {
            type: "application/json",
        }
    );

    const fileUrl =
        URL.createObjectURL(fileBlob);

    const downloadLink =
        document.createElement("a");

    downloadLink.href = fileUrl;
    downloadLink.download = filename;

    document.body.appendChild(downloadLink);
    downloadLink.click();
    downloadLink.remove();

    URL.revokeObjectURL(fileUrl);
}


async function exportPendingEvents() {
    exportPendingButton.disabled = true;

    syncStatusMessage.textContent =
        "Preparing sync package...";

    try {
        const pendingEvents =
            await getPendingEvents();

        if (pendingEvents.length === 0) {
            syncStatusMessage.textContent =
                "No pending events to export.";
            return;
        }

        const syncPackage = {
            format:
                "event-tracker-sync-package",
            version: 1,
            package_id: createEventId(),
            exported_at:
                new Date().toISOString(),
            event_count:
                pendingEvents.length,
            events: pendingEvents,
        };

        downloadJsonFile(
            syncPackage,
            createSyncPackageFilename()
        );

        syncStatusMessage.textContent =
            `Exported ${pendingEvents.length} ` +
            `pending event` +
            `${pendingEvents.length === 1 ? "" : "s"}.`;
    } catch (error) {
        syncStatusMessage.textContent =
            "Unable to export pending events.";

        console.error(
            "Pending-event export failed:",
            error
        );
    } finally {
        exportPendingButton.disabled = false;
    }
}


function chooseReceiptFile() {
    receiptFileInput.value = "";
    receiptFileInput.click();
}

function validateSyncReceipt(receipt) {
    if (
        !receipt ||
        receipt.format !==
            "event-tracker-sync-receipt" ||
        receipt.version !== 1 ||
        typeof receipt.package_id !== "string" ||
        !Array.isArray(
            receipt.acknowledged_event_ids
        )
    ) {
        throw new Error(
            "This is not a valid Event Tracker sync receipt."
        );
    }

    const invalidId =
        receipt.acknowledged_event_ids.some(
            (eventId) =>
                typeof eventId !== "string" ||
                !eventId.trim()
        );

    if (invalidId) {
        throw new Error(
            "The receipt contains an invalid event ID."
        );
    }
}


async function applySyncReceipt(event) {
    const selectedFile =
        event.target.files[0];

    if (!selectedFile) {
        return;
    }

    applyReceiptButton.disabled = true;

    syncStatusMessage.textContent =
        "Applying synchronization receipt...";

    try {
        const fileText =
            await selectedFile.text();

        const receipt =
            JSON.parse(fileText);

        validateSyncReceipt(receipt);

        const deletedCount =
            await deleteAcknowledgedEvents(
                receipt.acknowledged_event_ids
            );

        await loadEvents();

        const remainingEventCount =
            await countStoredEvents();

        syncStatusMessage.textContent =
            `Sync complete. Removed ${deletedCount} ` +
            `acknowledged event` +
            `${deletedCount === 1 ? "" : "s"} ` +
            `from this device.` +
            (
                remainingEventCount === 0
                    ? " No events remain locally."
                    : ` ${remainingEventCount} newer or ` +
                    `unacknowledged event` +
                    `${
                        remainingEventCount === 1
                            ? ""
                            : "s"
                    } remain locally.`
            );
    } catch (error) {
        syncStatusMessage.textContent =
            "Unable to apply this sync receipt.";

        console.error(
            "Receipt application failed:",
            error
        );
    } finally {
        applyReceiptButton.disabled = false;
    }
}

async function clearLocalEvents() {
    let eventCount;

    try {
        eventCount = await countStoredEvents();
    } catch (error) {
        deviceStorageStatus.textContent =
            "Unable to inspect local storage.";

        console.error(
            "Unable to count events before clearing:",
            error
        );
        return;
    }

    if (eventCount === 0) {
        deviceStorageStatus.textContent =
            "No local events to clear.";
        return;
    }

    const confirmed = window.confirm(
        `Delete all ${eventCount} event` +
        `${eventCount === 1 ? "" : "s"} ` +
        `currently stored on this device?\n\n` +
        `This cannot be undone unless the events ` +
        `have already been synchronized or backed up.`
    );

    if (!confirmed) {
        deviceStorageStatus.textContent =
            "Local deletion canceled.";
        return;
    }

    clearLocalEventsButton.disabled = true;
    deviceStorageStatus.textContent =
        "Clearing local events...";

    try {
        await clearAllLocalEvents();
        await loadEvents();

        deviceStorageStatus.textContent =
            `Deleted ${eventCount} local event` +
            `${eventCount === 1 ? "" : "s"}.`;
    } catch (error) {
        deviceStorageStatus.textContent =
            "Unable to clear local events.";

        console.error(
            "Unable to clear IndexedDB:",
            error
        );
    } finally {
        clearLocalEventsButton.disabled = false;
    }
}

async function deleteLocalEvent(eventId) {
    if (
        typeof eventId !== "string" ||
        !eventId.trim()
    ) {
        throw new TypeError(
            "A valid local event ID is required."
        );
    }

    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readwrite"
        );

        const store =
            transaction.objectStore(EVENTS_STORE);

        const request = store.delete(eventId);

        transaction.oncomplete = () => {
            database.close();
            resolve();
        };

        transaction.onerror = () => {
            database.close();
            reject(
                transaction.error ||
                new Error(
                    "Unable to delete the local event."
                )
            );
        };

        transaction.onabort = () => {
            database.close();
            reject(
                transaction.error ||
                new Error(
                    "Local event deletion was aborted."
                )
            );
        };
    });
}

function toggleShowAllRecentEvents() {
    showAllRecentEvents =
        !showAllRecentEvents;

    loadEvents();
}

initializeApplication();
