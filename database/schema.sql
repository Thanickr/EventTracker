-- Event Tracker Database Schema
-- Version 0.1
--
-- This schema defines the durable storage structure for Event Tracker.
-- Version 0.1 supports exercise events only, but stores them in a generic
-- events table to preserve the long-term event-based architecture.

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- When this record was created in the database.
    created_at TEXT NOT NULL,

    -- When the event actually occurred.
    -- For Version 0.1, this will default to the same value as created_at.
    occurred_at TEXT NOT NULL,

    -- Generic event category.
    -- For Version 0.1, this will always be 'exercise'.
    event_type TEXT NOT NULL,

    -- Exercise category, such as run, walk, weights, bike, pushups.
    exercise_type TEXT NOT NULL,

    -- Numeric amount, such as 1.0, 30, or 45.
    amount REAL NOT NULL,

    -- Unit for amount, such as mile, minute, rep, or set.
    unit TEXT NOT NULL,

    -- Optional free-text note.
    note TEXT
);