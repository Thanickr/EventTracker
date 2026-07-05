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