const exerciseTypeInput =
    document.getElementById("exercise-type");

const amountInput =
    document.getElementById("amount");

const unitInput =
    document.getElementById("unit");

const noteInput =
    document.getElementById("note");

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


async function loadEvents() {
    try {
        const events = await getLocalEvents();

        eventsList.innerHTML = "";

        if (events.length === 0) {
            eventsList.textContent =
                "No events logged yet.";
            return;
        }

        events.slice(0, 20).forEach((event) => {
            const eventElement =
                document.createElement("div");

            eventElement.className = "event";

            const main =
                document.createElement("div");

            main.className = "event-main";
            main.textContent =
                `${event.exercise_type} ` +
                `${event.amount} ${event.unit}`;

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
        eventsList.textContent =
            "Unable to load local events.";

        console.error(
            "Unable to load events:",
            error
        );
    }
}


async function saveExerciseEvent() {
    const exerciseType =
        exerciseTypeInput.value.trim();

    const amount =
        Number.parseFloat(amountInput.value);

    const unit =
        unitInput.value.trim();

    const note =
        noteInput.value.trim();

    if (
        !exerciseType ||
        Number.isNaN(amount) ||
        !unit
    ) {
        statusMessage.textContent =
            "Exercise, amount, and unit are required.";

        return;
    }

    saveButton.disabled = true;
    statusMessage.textContent = "Saving...";

    try {
        const timestamp =
            getCurrentLocalTimestamp();

        const event = {
            id: createEventId(),
            created_at: timestamp,
            occurred_at: timestamp,
            event_type: "exercise",
            exercise_type: exerciseType,
            amount,
            unit,
            note: note || null,
            sync_status: "pending",
        };

        await saveLocalEvent(event);

        statusMessage.textContent =
            "Saved on this device.";

        noteInput.value = "";

        await loadEvents();
    } catch (error) {
        statusMessage.textContent =
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
    await loadEvents();
}


saveButton.addEventListener(
    "click",
    saveExerciseEvent
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

        syncStatusMessage.textContent =
            `Confirmed ${receipt.acknowledged_event_ids.length} ` +
            `event` +
            `${
                receipt.acknowledged_event_ids.length === 1
                    ? ""
                    : "s"
            }; removed ${deletedCount} pending ` +
            `event${deletedCount === 1 ? "" : "s"} ` +
            `from this device.`;
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

initializeApplication();