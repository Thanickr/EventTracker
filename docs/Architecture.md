# Event Tracker Architecture

## Version 0.1 Architecture

Event Tracker is a local-first behavior logging application.

Version 0.1 focuses only on exercise logging.

## Planned Technical Stack

- Frontend: Progressive Web App
- Backend: Python
- Database: SQLite
- Editor: Visual Studio Code
- Version Control: Git

## Core Design

The system stores user actions as events.

For Version 0.1, all events are exercise events.

## Initial Data Model

### events

| Field | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| timestamp | text | ISO-8601 timestamp |
| event_type | text | Initially always `exercise` |
| exercise_type | text | Example: running, walking, weights |
| amount | real | Numeric quantity |
| unit | text | Example: miles, minutes, reps |
| note | text | Optional |

## Architecture Principle

Capture first. Analyze later.

The application should make recording behavior easier than thinking about behavior.

## Initial Data Model

### events

| Field | Type | Notes |
|---|---|---|
| id | integer | Primary key |
| created_at | text | When the record was created |
| occurred_at | text | When the exercise occurred |
| event_type | text | Initially always `exercise` |
| exercise_type | text | Example: run, walk, weights |
| amount | real | Numeric quantity |
| unit | text | Example: mile, minute, rep |
| note | text | Optional |

## Current Local Web Architecture

Version 0.1 currently runs as a local web application.

```text
Browser UI
    ↓
FastAPI backend
    ↓
SQLite database

## Revised Capture Architecture

Event Tracker uses a phone-local-first capture architecture.

```text
iPhone PWA
    ↓
IndexedDB
    ↓
Future synchronization or export
    ↓
SQLite

## Local Backup and Transfer

Event records can be exported from IndexedDB into a versioned JSON backup file.

```text
IndexedDB
    ↓ Export
Local JSON file
    ↓ Import
IndexedDB