# Event Tracker Decision Log

This document records important project decisions and the reasoning behind them.

---

## Decision 0001: Project Name

**Decision:** Use the working name Event Tracker.

**Reason:** The name supports the long-term idea that many logged behaviors can be represented as events, while still being simple and clear.

**Date:** 2026-07-05

---

## Decision 0002: Start with Exercise Logging Only

**Decision:** Version 0.1 will only support exercise logging.

**Reason:** Exercise logging has the highest probability of becoming a repeatable habit. The goal is adherence, not feature count.

**Date:** 2026-07-05

---

## Decision 0003: Local-First Storage

**Decision:** Prefer local storage and user-controlled data.

**Reason:** The user wants durable ownership of personal data and wants to avoid subscriptions or proprietary cloud dependencies.

**Date:** 2026-07-05

---

## Decision 0004: SQLite as Leading Database Choice

**Decision:** Use SQLite unless a simpler option proves clearly better for Version 0.1.

**Reason:** SQLite provides one portable database file, reliability, easy backup, CSV export, and future analytical capability.

**Date:** 2026-07-05

---

## Decision 0005: Separate Created Time from Occurred Time

**Decision:** Store both `created_at` and `occurred_at` for each event.

**Reason:** `created_at` records when the database entry was made, while `occurred_at` records when the behavior happened. For Version 0.1 both will default to the current time, but separating them preserves timeline accuracy without adding user-interface complexity.

**Date:** 2026-07-05

---

## Decision 0006: Use a Generic Events Table

**Decision:** Store exercise logs in a generic `events` table rather than an `exercise_events` table.

**Reason:** The long-term model is that behaviors are events. This supports future event types at essentially no cost to Version 0.1.

**Date:** 2026-07-05

---

## Decision 0007: Keep Version 0.1 Schema Minimal

**Decision:** Version 0.1 uses a single `events` table with only the fields required to log exercise events.

**Reason:** The highest priority is long-term adherence. Additional tables for users, settings, tags, exercise catalogs, or analytics would increase complexity before real usage justifies them.

**Date:** 2026-07-05

---

## Decision 0008: Build a Local Python Backend Before the PWA

**Decision:** Version 0.1 will first expose the SQLite data layer through a small local Python web backend.

**Reason:** A browser-based PWA cannot directly write to the local SQLite database file. A Python backend allows the application to preserve the SQLite-first architecture while giving the future PWA a simple interface for saving and reading events.

**Tradeoff:** This means the Windows computer must be running the backend for the phone to log directly to SQLite. If real-world use shows that this creates friction, phone-local browser storage will be reconsidered.

**Date:** 2026-07-05

---

## Decision 0009: Build the First Browser Interface Before Full PWA Installation

**Decision:** Build a simple browser-based logging interface before adding full PWA behavior.

**Reason:** The highest-risk workflow is basic capture: form input, backend save, database write, and recent event display. Proving this path first reduces implementation risk before adding PWA installation, offline support, or phone-specific behavior.

**Date:** 2026-07-05

---

## Decision 0010: Add Basic PWA Support Before Offline Logging

**Decision:** Add basic Progressive Web App support so Event Tracker can be launched from the phone home screen.

**Reason:** Reducing launch friction directly supports long-term adherence. Offline logging is intentionally postponed because the current system already works when the local backend is reachable, and offline sync would add complexity before real usage justifies it.

**Date:** 2026-07-05

---

## Decision 0011: Make Phone-Local Storage the Primary Capture Layer

**Decision:** Event Tracker will store newly captured events directly in IndexedDB on the user's phone rather than requiring an immediate connection to the Windows FastAPI backend.

**Reason:** Real-world testing showed that requiring the phone to remain connected to the home network created substantial friction and interfered with event capture. Long-term adherence takes priority over preserving the original backend-first capture architecture.

**Consequences:**

- Event capture will work without the Windows computer or home network.
- SQLite remains the intended durable analysis and archival database.
- A later synchronization or export process will transfer phone-local events into SQLite.
- The application must be served over HTTPS for reliable service-worker-based offline launching.

**Date:** 2026-07-12

---

## Decision 0012: Use Local JSON Files for Backup and Transfer

**Decision:** Event Tracker will support exporting and importing local event data as a versioned JSON backup file.

**Reason:** IndexedDB data is local to a particular browser origin and device. A portable backup is required before relying on phone-local storage for long-term collection.

**Privacy:** Export and import occur entirely on the user's device. Event data is not uploaded to GitHub or another remote service.

**Date:** 2026-07-13

---

## Decision 0013: Treat Phone Storage as a Temporary Synchronization Queue

**Decision:** IndexedDB on the phone will serve as a temporary capture and synchronization queue. SQLite on the user's computer will be the canonical long-term event store.

**Synchronization model:**

1. New phone events are marked as pending.
2. The phone exports only pending events in an incremental sync package.
3. The computer imports the package into SQLite using stable event IDs for duplicate protection.
4. After the SQLite transaction succeeds, the computer produces a receipt containing the accepted event IDs.
5. The phone imports the receipt and removes only the acknowledged events.

**Reason:** The user does not want to repeatedly transfer the complete dataset between devices. Incremental synchronization minimizes file size and keeps the authoritative dataset in the local SQLite database.

**Safety:** Events are not removed from the phone merely because they were exported. They are removed only after a successful SQLite import is acknowledged by a receipt.

**Date:** 2026-07-15

---

## Decision 0014: Preserve SQLite Integer Keys and Add Stable Source Event IDs

**Decision:** SQLite will retain its internal integer primary key. Phone-generated event IDs will be stored separately in a nullable, unique `source_event_id` field.

**Reason:** Replacing the existing SQLite primary key would require rebuilding the table and would unnecessarily disrupt existing records. A separate stable source ID provides duplicate-safe incremental imports while preserving the database's current structure.

**Behavior:**

- SQLite-created legacy events may have a null `source_event_id`.
- Phone-imported events must have a stable `source_event_id`.
- A unique index prevents the same phone event from being inserted more than once.

**Date:** 2026-07-15

---

## Decision 0015: Separate Normal Synchronization from Full Backup

**Decision:** The phone interface will expose two separate data workflows:

1. incremental synchronization for pending events
2. full backup and restore for disaster recovery

**Reason:** Normal synchronization should transfer only new records and clear them only after SQLite acknowledgment. Full backups serve a different purpose and must not alter synchronization state.

**Date:** 2026-07-15

---

## Decision 0016: Clear Acknowledged Phone Events and Separate Visibility from Deletion

**Decision:** Events acknowledged by a valid SQLite synchronization receipt will be removed from IndexedDB. The phone should normally return to an empty local queue after synchronization.

**Safety:** Events created after a sync package was exported are not removed by that package's receipt.

**Privacy controls:**

- The recent-events list may be hidden without changing stored data.
- The visibility preference is retained locally.
- A separate confirmed action may delete all events from phone storage.

**Reason:** The phone is a temporary capture queue, not the canonical archive. Visibility and deletion are separate concerns and must not be conflated.

**Date:** 2026-07-15