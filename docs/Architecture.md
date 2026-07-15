# Event Tracker Architecture

## 1. Purpose

Event Tracker is a local-first personal event capture system designed for long-term daily use.

The highest architectural priority is adherence. The capture process must remain available, fast, and cognitively inexpensive.

The system separates two responsibilities:

1. frictionless event capture on the phone
2. durable storage and future analysis on the user's computer

The guiding principle is:

> Capture first. Analyze later.

---

## 2. Current System Boundary

Event Tracker currently supports exercise-oriented event capture, but the storage model is generic enough to represent other event types later.

The current system consists of:

- a static Progressive Web App hosted through GitHub Pages
- IndexedDB storage on the user's phone
- local JSON backup and synchronization files
- a Python synchronization utility on the user's Windows computer
- a local SQLite database as the canonical long-term store
- legacy FastAPI and command-line components retained for development and testing

No personal event data is stored by GitHub Pages.

---

## 3. Architectural Principles

### 3.1 Local-First Data Ownership

Personal event data remains under the user's control.

GitHub Pages hosts only static application files:

- HTML
- CSS
- JavaScript
- manifest
- service worker

Personal events are stored locally in:

- IndexedDB on the capture device
- SQLite on the user's computer
- user-controlled JSON files during backup or synchronization

The application does not transmit event data to GitHub or another cloud service.

### 3.2 Capture Availability

Phone capture must not depend on:

- the Windows computer being powered on
- FastAPI or Uvicorn running
- the phone being connected to the home network
- a stable local IP address

The phone PWA therefore writes directly to IndexedDB.

### 3.3 Canonical Storage

SQLite on the user's computer is the canonical long-term database.

IndexedDB is primarily a temporary capture and synchronization queue.

### 3.4 Incremental Development

New functionality is added only when real usage demonstrates a need.

Complexity is postponed unless it materially improves:

- adherence
- reliability
- data ownership
- recoverability

### 3.5 Idempotent Synchronization

Repeatedly processing the same synchronization package must not create duplicate database records.

Stable source event IDs provide duplicate protection.

---

## 4. Current High-Level Architecture

```text
GitHub Pages
    │
    │ serves static PWA files only
    ▼
iPhone PWA
    │
    │ saves new events locally
    ▼
IndexedDB
    │
    │ exports pending events
    ▼
JSON Sync Package
    │
    │ transferred by the user
    ▼
Windows Python Import Utility
    │
    │ validates and imports transactionally
    ▼
SQLite Database
    │
    │ produces acknowledgment receipt
    ▼
JSON Sync Receipt
    │
    │ returned to phone
    ▼
IndexedDB
    │
    └── acknowledged events removed
```

---

## 5. Capture Layer

### 5.1 Progressive Web App

The phone application is implemented as a static PWA.

Files are located in:

```text
app/static/
```

Current static files include:

```text
index.html
style.css
db.js
app.js
manifest.json
service-worker.js
```

The PWA is hosted through GitHub Pages over HTTPS.

### 5.2 Service Worker

The service worker caches the application shell so the interface can remain available after initial loading.

Cached assets include:

- application HTML
- stylesheet
- IndexedDB helper code
- application logic
- manifest

The service worker does not upload or synchronize personal data.

### 5.3 IndexedDB

IndexedDB is the primary phone-side capture store.

Each event is stored immediately on the device.

New events are marked as pending synchronization.

IndexedDB serves two roles:

1. temporary event queue
2. short-term recovery buffer before SQLite acknowledgment

It is not intended to be the permanent analytical database.

---

## 6. Event Model

### 6.1 Logical Event Structure

A captured event currently contains:

```text
id
created_at
occurred_at
event_type
exercise_type
amount
unit
note
sync_status
```

### 6.2 Field Definitions

| Field | Purpose |
|---|---|
| `id` | Stable device-generated event identifier |
| `created_at` | Time the event record was created |
| `occurred_at` | Time the event actually occurred |
| `event_type` | Generic event category; currently `exercise` |
| `exercise_type` | Exercise or activity description |
| `amount` | Numeric quantity |
| `unit` | Unit associated with the amount |
| `note` | Optional descriptive text |
| `sync_status` | Phone-side synchronization state |

### 6.3 Current Synchronization Status

New phone events use:

```text
sync_status = "pending"
```

Events remain pending until a valid synchronization receipt acknowledges successful SQLite ingestion.

---

## 7. SQLite Architecture

### 7.1 Database Location

The local database is stored at:

```text
database/event_tracker.db
```

The database file is excluded from Git.

### 7.2 Schema Source

The reproducible schema definition is stored at:

```text
database/schema.sql
```

### 7.3 Events Table

The SQLite `events` table currently includes:

| Field | Type | Purpose |
|---|---|---|
| `id` | integer | Internal SQLite primary key |
| `source_event_id` | text | Stable device-generated ID for duplicate-safe imports |
| `created_at` | text | Record creation timestamp |
| `occurred_at` | text | Event occurrence timestamp |
| `event_type` | text | Generic event category |
| `exercise_type` | text | Exercise or activity description |
| `amount` | real | Numeric quantity |
| `unit` | text | Measurement unit |
| `note` | text | Optional note |

### 7.4 Key Strategy

SQLite retains an internal integer primary key.

Phone-generated event IDs are stored separately in:

```text
source_event_id
```

A unique index prevents the same phone event from being inserted more than once.

Legacy SQLite-created records may have:

```text
source_event_id = NULL
```

---

## 8. Incremental Synchronization

### 8.1 Phone as Capture Queue

The phone does not repeatedly export the complete dataset during normal synchronization.

It exports only events that have not yet been acknowledged by SQLite.

### 8.2 Sync Package

A phone-generated synchronization package contains:

```text
format
version
package_id
exported_at
event_count
events
```

Only pending events are included.

### 8.3 Desktop Import

The desktop Python utility:

1. reads the sync package
2. validates the package structure
3. validates every event
4. begins a SQLite transaction
5. inserts new events
6. skips already-imported event IDs safely
7. commits the transaction
8. generates a synchronization receipt

### 8.4 Sync Receipt

The synchronization receipt contains:

```text
format
version
package_id
processed_at
accepted_event_ids
already_present_event_ids
rejected_events
```

Only successfully accepted or already-present event IDs may be acknowledged.

### 8.5 Phone Cleanup

The phone imports the receipt and verifies:

- receipt format
- receipt version
- package identity
- acknowledged event IDs

The phone then removes only acknowledged events from IndexedDB.

Events are never deleted merely because a sync package was exported.

### 8.6 Duplicate Protection

Synchronization is idempotent.

Re-importing the same package does not create duplicate SQLite events because:

```text
source_event_id
```

is unique.

---

## 9. Backup and Recovery

Backup is separate from synchronization.

### 9.1 Full Backup

The PWA can export the complete local IndexedDB event collection as a versioned JSON backup.

Purpose:

- disaster recovery
- migration between browser origins
- transfer to a replacement device
- protection before significant application changes

### 9.2 Full Restore

A valid backup file may be imported back into IndexedDB.

Stable event IDs prevent duplicate records when the same backup is imported repeatedly.

### 9.3 Difference Between Backup and Sync

```text
Backup:
entire local phone dataset

Sync:
pending phone events only
```

Backup files do not cause phone events to be cleared.

Only valid SQLite acknowledgment receipts may clear synchronized records.

---

## 10. Legacy and Development Components

The repository retains several earlier components because they remain useful for development, testing, and migration.

### 10.1 Database Initialization

```text
app/init_db.py
```

Creates the SQLite database from `database/schema.sql`.

### 10.2 Database Migration

```text
app/migrate_db.py
```

Applies repeat-safe schema migrations.

### 10.3 Direct Event Logging

```text
app/log_event.py
```

Provides reusable Python functions for inserting and listing SQLite events.

### 10.4 Command-Line Interface

```text
app/cli.py
```

Allows direct local event logging from the terminal.

### 10.5 FastAPI Backend

```text
app/server.py
```

The FastAPI backend was the original browser-to-SQLite capture path.

It is no longer required for normal phone capture, but remains useful for:

- development
- API experiments
- database testing
- possible future local tooling

---

## 11. Hosting and Deployment

### 11.1 Source Repository

Application source code is stored in Git.

Personal databases, virtual environments, caches, and secrets are excluded through `.gitignore`.

### 11.2 GitHub Pages

GitHub Actions deploys only:

```text
app/static/
```

The deployed site contains no personal events.

### 11.3 Privacy Boundary

Publicly hosted:

- PWA source files
- interface logic
- IndexedDB schema logic
- service-worker logic

Not publicly hosted:

- phone IndexedDB records
- SQLite database
- sync packages
- sync receipts
- backup files
- personal notes
- event history

---

## 12. Testing Strategy

The project uses incremental vertical testing.

### 12.1 Data-Layer Testing

Verify:

```text
schema → SQLite → insert → retrieve
```

### 12.2 Browser Testing

Verify:

```text
form → IndexedDB → reload → event remains
```

### 12.3 Deployment Testing

Verify:

```text
GitHub Pages → PWA loads → local save succeeds
```

### 12.4 Synchronization Testing

Verify:

```text
pending event
→ sync package
→ SQLite import
→ receipt
→ phone cleanup
```

### 12.5 Failure Testing

Synchronization must also be tested for:

- duplicate package import
- malformed JSON
- invalid event records
- missing fields
- partial rejection
- receipt mismatch
- interrupted transfer
- repeated receipt import

---

## 13. Current Scope

The current scope is:

- low-friction event capture
- exercise-oriented logging
- phone-local storage
- full local backup
- incremental phone-to-SQLite synchronization
- local durable ownership

The current scope does not include:

- cloud account storage
- shared user accounts
- analytics dashboards
- automatic background sync
- Apple Health integration
- Apple Watch capture
- GPS tracking
- mood analysis
- AI classification
- calendar integration
- multi-user collaboration

These remain in the Parking Lot until real usage justifies them.

---

## 14. Current Development Priority

The immediate development priority is completing the incremental synchronization loop:

```text
Phone pending events
    ↓
Sync package
    ↓
Desktop SQLite importer
    ↓
Acknowledgment receipt
    ↓
Phone cleanup
```

Once this loop is reliable, the system will provide:

- unrestricted phone capture
- durable local archival
- small incremental transfers
- duplicate-safe imports
- explicit acknowledgment before deletion
- no proprietary cloud dependency

---

## 15. Long-Term Architectural Direction

The event model may eventually support additional categories such as:

- state logs
- mood
- reading
- weight
- sleep
- projects
- ideas
- health metrics
- behavioral observations

Those additions should not alter the core separation:

```text
Capture layer
    ↓
Synchronization boundary
    ↓
Canonical local database
    ↓
Future analysis
```

The capture layer should remain simple even if later analytical systems become sophisticated.