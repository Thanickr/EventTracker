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

const amountInput =
    document.getElementById("amount");

const unitInput =
    document.getElementById("unit");

const saveButton =
    document.getElementById("save-button");

const statusMessage =
    document.getElementById("status-message");

const eventsList =
    document.getElementById("events-list");

const exportButton =
    document.getElementById("export-button");

const importButton =
    document.getElementById("import-button");

const importFileInput =
    document.getElementById("import-file");

const dataStatusMessage =
    document.getElementById("data-status-message");

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
    const isVisible = recentEventsAreVisible();

    eventsList.hidden = !isVisible;
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
}

async function loadEvents() {
    try {
        const events = await getLocalEvents();
        const eventCount = events.length;

        localEventCount.textContent =
            eventCount === 0
                ? "No events stored on this device."
                : `${eventCount} event` +
                  `${eventCount === 1 ? "" : "s"} ` +
                  `stored on this device.`;

        eventsList.innerHTML = "";

        if (eventCount === 0) {
            eventsList.textContent =
                "No recent events.";
            return;
        }

        events.slice(0, 20).forEach((event) => {
            const eventElement =
                document.createElement("div");

            eventElement.className = "event";

            const main =
                document.createElement("div");

            main.className = "event-main";
            if (
                event.unit === "event" &&
                event.amount === 1
            ) {
                main.textContent =
                    event.exercise_type;
            } else {
                main.textContent =
                    `${event.exercise_type} ` +
                    `${event.amount} ${event.unit}`;
            }

            const meta =
                document.createElement("div");

            meta.className = "event-meta";
            meta.textContent =
                formatEventTime(event.occurred_at);

            eventElement.appendChild(main);
            eventElement.appendChild(meta);

            if (event.note) {
                const note =
                    document.createElement("div");

                note.className = "event-meta";
                note.textContent = event.note;

                eventElement.appendChild(note);
            }

            eventsList.appendChild(eventElement);
        });
    } catch (error) {
        localEventCount.textContent =
            "Unable to count local events.";

        eventsList.textContent =
            "Unable to load local events.";

        console.error(
            "Unable to load events:",
            error
        );
    }
}


async function saveEvent() {
    const eventName =
        eventNameInput.value.trim();

    const amount =
        Number.parseFloat(amountInput.value);

    const unit =
        unitInput.value.trim();

    const details =
        detailsInput.value.trim();

    if (
        !eventName ||
        Number.isNaN(amount) ||
        !unit
    ) {
        statusMessage.textContent =
            "Event, amount, and unit are required.";

        return;
    }

    saveButton.disabled = true;
    statusMessage.textContent = "Saving...";

    try {
        const createdAt =
            getCurrentLocalTimestamp();

        const occurredAt =
            selectedOccurredAt();

        const event = {
            id: createEventId(),
            created_at: createdAt,
            occurred_at: occurredAt,
            event_type: "event",

            // Retained for compatibility with the current
            // IndexedDB and SQLite schema.
            exercise_type: eventName,

            amount,
            unit,
            note: details || null,
            sync_status: "pending",
        };

        await saveLocalEvent(event);

        statusMessage.textContent =
            "Saved on this device.";

        eventNameInput.value = "";
        detailsInput.value = "";

        resetTimestampControls();

        eventNameInput.focus();

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

exportButton.addEventListener(
    "click",
    exportData
);

importButton.addEventListener(
    "click",
    chooseImportFile
);

importFileInput.addEventListener(
    "change",
    importData
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

detailsInput.addEventListener(
    "keydown",
    (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            saveEvent();
        }
    }
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

initializeApplication();