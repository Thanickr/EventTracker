/*
 * Phone-local database for Event Tracker.
 *
 * IndexedDB is the primary capture store. Events are saved immediately
 * on the device without requiring the FastAPI backend or home network.
 */

const DATABASE_NAME = "event-tracker";
const DATABASE_VERSION = 1;
const EVENTS_STORE = "events";

function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

        request.onupgradeneeded = () => {
            const database = request.result;

            if (!database.objectStoreNames.contains(EVENTS_STORE)) {
                const store = database.createObjectStore(EVENTS_STORE, {
                    keyPath: "id",
                });

                store.createIndex("occurred_at", "occurred_at");
                store.createIndex("event_type", "event_type");
            }
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function createEventId() {
    if (
        globalThis.crypto &&
        typeof globalThis.crypto.randomUUID === "function"
    ) {
        return globalThis.crypto.randomUUID();
    }

    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function saveLocalEvent(event) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readwrite"
        );

        const store = transaction.objectStore(EVENTS_STORE);
        store.put(event);

        transaction.oncomplete = () => {
            database.close();
            resolve(event);
        };

        transaction.onerror = () => {
            database.close();
            reject(transaction.error);
        };

        transaction.onabort = () => {
            database.close();
            reject(transaction.error);
        };
    });
}

async function getLocalEvents() {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readonly"
        );

        const store = transaction.objectStore(EVENTS_STORE);
        const request = store.getAll();

        request.onsuccess = () => {
            const events = request.result.sort((first, second) =>
                second.occurred_at.localeCompare(first.occurred_at)
            );

            database.close();
            resolve(events);
        };

        request.onerror = () => {
            database.close();
            reject(request.error);
        };
    });
}

async function countLocalEvents() {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readonly"
        );

        const store = transaction.objectStore(EVENTS_STORE);
        const request = store.count();

        request.onsuccess = () => {
            database.close();
            resolve(request.result);
        };

        request.onerror = () => {
            database.close();
            reject(request.error);
        };
    });
}

async function exportLocalEvents() {
    return getLocalEvents();
}


async function importLocalEvents(events) {
    if (!Array.isArray(events)) {
        throw new TypeError("Imported data must contain an events array.");
    }

    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readwrite"
        );

        const store = transaction.objectStore(EVENTS_STORE);

        let importedCount = 0;

        for (const event of events) {
            if (
                !event ||
                typeof event.id !== "string" ||
                typeof event.occurred_at !== "string" ||
                typeof event.event_type !== "string"
            ) {
                transaction.abort();
                reject(
                    new Error("The backup contains an invalid event.")
                );
                return;
            }

            store.put(event);
            importedCount += 1;
        }

        transaction.oncomplete = () => {
            database.close();
            resolve(importedCount);
        };

        transaction.onerror = () => {
            database.close();
            reject(
                transaction.error ||
                new Error("Unable to import events.")
            );
        };

        transaction.onabort = () => {
            database.close();
        };
    });
}

async function getPendingEvents() {
    const events = await getLocalEvents();

    return events.filter(
        (event) => event.sync_status === "pending"
    );
}


async function deleteAcknowledgedEvents(eventIds) {
    if (!Array.isArray(eventIds)) {
        throw new TypeError(
            "Acknowledged event IDs must be an array."
        );
    }

    const uniqueEventIds = [
        ...new Set(
            eventIds.filter(
                (eventId) =>
                    typeof eventId === "string" &&
                    eventId.trim()
            )
        ),
    ];

    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readwrite"
        );

        const store =
            transaction.objectStore(EVENTS_STORE);

        let deletedCount = 0;

        for (const eventId of uniqueEventIds) {
            const getRequest = store.get(eventId);

            getRequest.onsuccess = () => {
                const event = getRequest.result;

                if (
                    event &&
                    event.sync_status === "pending"
                ) {
                    store.delete(eventId);
                    deletedCount += 1;
                }
            };
        }

        transaction.oncomplete = () => {
            database.close();
            resolve(deletedCount);
        };

        transaction.onerror = () => {
            database.close();
            reject(
                transaction.error ||
                new Error(
                    "Unable to remove acknowledged events."
                )
            );
        };

        transaction.onabort = () => {
            database.close();
            reject(
                transaction.error ||
                new Error(
                    "Acknowledgment transaction was aborted."
                )
            );
        };
    });
}

async function countStoredEvents() {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readonly"
        );

        const store = transaction.objectStore(EVENTS_STORE);
        const request = store.count();

        request.onsuccess = () => {
            database.close();
            resolve(request.result);
        };

        request.onerror = () => {
            database.close();
            reject(
                request.error ||
                new Error("Unable to count local events.")
            );
        };
    });
}


async function clearAllLocalEvents() {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            EVENTS_STORE,
            "readwrite"
        );

        const store = transaction.objectStore(EVENTS_STORE);
        const request = store.clear();

        request.onsuccess = () => {
            // Wait for transaction completion before reporting success.
        };

        transaction.oncomplete = () => {
            database.close();
            resolve();
        };

        transaction.onerror = () => {
            database.close();
            reject(
                transaction.error ||
                new Error("Unable to clear local events.")
            );
        };

        transaction.onabort = () => {
            database.close();
            reject(
                transaction.error ||
                new Error("Local event deletion was aborted.")
            );
        };
    });
}