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