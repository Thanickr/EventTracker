# Event Tracker Requirements

## Version 0.1 Goal

Version 0.1 exists to make logging exercise events fast, reliable, and low-friction.

The primary success criterion is that an exercise event can be logged in under 5 seconds during normal use.

## Current Scope

Version 0.1 supports logging exercise events only.

Each exercise event records:

- timestamp
- exercise type
- amount
- unit
- optional note

## Current Version 0.1 Capabilities

The application currently supports:

- creating a local SQLite database from the project schema
- logging exercise events from a command-line interface
- running a local FastAPI backend
- logging exercise events from a browser-based form
- viewing recent exercise events in the browser interface

## Functional Requirements

### FR-001: Log Exercise Event

The system shall allow the user to record an exercise event.

### FR-002: Default Timestamp

The system shall automatically assign the current timestamp when an event is created.

### FR-003: Exercise Type

The system shall allow the user to specify the type of exercise.

### FR-004: Amount

The system shall allow the user to enter a numeric amount.

### FR-005: Unit

The system shall allow the user to specify a unit such as miles, minutes, or reps.

### FR-006: Optional Note

The system may allow an optional note if it does not add meaningful friction.

## Nonfunctional Requirements

### NFR-001: Low Friction

The system should minimize taps, typing, and decisions.

### NFR-002: Local First

Data should remain under the user's control.

### NFR-003: Offline Capable

The system should function without internet access.

### NFR-004: No Account Required

The system should not require a user account.

### NFR-005: Simple Maintenance

The system should prefer simple, readable code over clever abstractions.

## Incremental Synchronization

The system shall:

- mark newly captured phone events as pending
- export only pending events during normal synchronization
- import pending events into SQLite without duplication
- generate a receipt after successful SQLite processing
- remove phone events only after receipt acknowledgment
- retain full backup and restore as a separate workflow

## Local Storage Cleanup and Privacy

The system shall:

- remove every receipt-acknowledged event from phone storage
- preserve newer events not included in the acknowledged package
- display the number of events currently stored on the device
- allow the recent-events list to be hidden without deleting data
- remember the device's recent-events visibility preference
- allow all local events to be cleared manually after explicit confirmation

## Desktop Synchronization Console

The system shall provide a local desktop interface that:

- accepts a phone-generated synchronization package
- validates the package before database changes
- imports new events into SQLite transactionally
- skips duplicate source event IDs
- reports imported and already-present event counts
- generates and automatically downloads a synchronization receipt
- operates only on the user's local computer
- does not require manual terminal commands during normal use

## General Event Capture

The system shall:

- allow the user to enter a general event name
- default the event occurrence time to the current local time
- allow an alternate occurrence date and time at entry
- retain the actual creation timestamp separately
- preserve both timestamps through synchronization into SQLite

## Local Event Correction

The system shall:

- allow locally stored events to be edited before synchronization
- populate the capture form with the selected event's current values
- preserve the event's stable ID and original creation timestamp
- allow modification of event name, amount, unit, details, and occurrence time
- keep edited events pending synchronization
- allow editing to be canceled without saving changes