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