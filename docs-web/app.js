const exerciseTypeInput = document.getElementById("exercise-type");
const amountInput = document.getElementById("amount");
const unitInput = document.getElementById("unit");
const noteInput = document.getElementById("note");
const saveButton = document.getElementById("save-button");
const statusMessage = document.getElementById("status-message");
const eventsList = document.getElementById("events-list");

function getCurrentLocalTimestamp() {
    const now = new Date();
    const offsetMilliseconds = now.getTimezoneOffset() * 60_000;

    return new Date(now.getTime() - offsetMilliseconds)
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
            eventsList.textContent = "No events logged yet.";
            return;
        }

        events.slice(0, 20).forEach((event) => {
            const eventElement = document.createElement("div");
            eventElement.className = "event";

            const main = document.createElement("div");
            main.className = "event-main";
            main.textContent =
                `${event.exercise_type} ${event.amount} ${event.unit}`;

            const meta = document.createElement("div");
            meta.className = "event-meta";
            meta.textContent = formatEventTime(event.occurred_at);

            eventElement.appendChild(main);
            eventElement.appendChild(meta);

            if (event.note) {
                const note = document.createElement("div");
                note.className = "event-meta";
                note.textContent = event.note;
                eventElement.appendChild(note);
            }

            eventsList.appendChild(eventElement);
        });
    } catch (error) {
        eventsList.textContent = "Unable to load local events.";
        console.error(error);
    }
}

async function saveExerciseEvent() {
    const exerciseType = exerciseTypeInput.value.trim();
    const amount = Number.parseFloat(amountInput.value);
    const unit = unitInput.value.trim();
    const note = noteInput.value.trim();

    if (!exerciseType || Number.isNaN(amount) || !unit) {
        statusMessage.textContent =
            "Exercise, amount, and unit are required.";
        return;
    }

    saveButton.disabled = true;
    statusMessage.textContent = "Saving...";

    try {
        const timestamp = getCurrentLocalTimestamp();

        const event = {
            id: createEventId(),
            created_at: timestamp,
            occurred_at: timestamp,
            event_type: "exercise",
            exercise_type: exerciseType,
            amount,
            unit,
            note: note || null,
            sync_status: "local",
        };

        await saveLocalEvent(event);

        statusMessage.textContent = "Saved on this device.";
        noteInput.value = "";

        await loadEvents();
    } catch (error) {
        statusMessage.textContent = "Error saving event.";
        console.error(error);
    } finally {
        saveButton.disabled = false;
    }
}

saveButton.addEventListener("click", saveExerciseEvent);

async function initializeApplication() {
    await loadEvents();
}

initializeApplication();