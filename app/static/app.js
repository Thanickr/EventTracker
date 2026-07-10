const exerciseTypeInput = document.getElementById("exercise-type");
const amountInput = document.getElementById("amount");
const unitInput = document.getElementById("unit");
const noteInput = document.getElementById("note");
const saveButton = document.getElementById("save-button");
const statusMessage = document.getElementById("status-message");
const eventsList = document.getElementById("events-list");

async function loadEvents() {
    const response = await fetch("/events");
    const events = await response.json();

    eventsList.innerHTML = "";

    if (events.length === 0) {
        eventsList.textContent = "No events logged yet.";
        return;
    }

    events.slice(0, 5).forEach((event) => {
        const eventElement = document.createElement("div");
        eventElement.className = "event";

        const main = document.createElement("div");
        main.className = "event-main";
        main.textContent = `${event.exercise_type} ${event.amount} ${event.unit}`;

        const meta = document.createElement("div");
        meta.className = "event-meta";
        meta.textContent = event.occurred_at;

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
}

async function saveExerciseEvent() {
    const exerciseType = exerciseTypeInput.value.trim();
    const amount = Number.parseFloat(amountInput.value);
    const unit = unitInput.value.trim();
    const note = noteInput.value.trim();

    if (!exerciseType || Number.isNaN(amount) || !unit) {
        statusMessage.textContent = "Exercise, amount, and unit are required.";
        return;
    }

    saveButton.disabled = true;
    statusMessage.textContent = "Saving...";

    try {
        const response = await fetch("/events", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                exercise_type: exerciseType,
                amount: amount,
                unit: unit,
                note: note || null,
            }),
        });

        if (!response.ok) {
            throw new Error("Save failed.");
        }

        statusMessage.textContent = "Saved.";
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

loadEvents();