# Event Tracker Analysis Foundation

This directory is deliberately separate from capture and synchronization.
Analysis opens the canonical SQLite database in read-only mode and does not
change the capture schema, events, or synchronization receipts.

## Run the baseline audit

From the project root:

```shell
python -m analysis.baseline
```

The command prints JSON containing only aggregate and schema-level facts. It
does not emit event names, details, source event IDs, or individual timestamps.

To audit a database copy at another path:

```shell
python -m analysis.baseline --database path/to/event_tracker.db
```

## Data boundaries

- **Raw:** the unchanged `events` table in SQLite.
- **Derived:** reproducible aliases, counts, time windows, quality checks, and
  later features calculated from raw events.
- **Inferred:** future semantic labels, summaries, hypotheses, or AURA
  variables. These must remain distinguishable from observations.

The analysis vocabulary uses `event_name` as an alias for the legacy physical
column `exercise_type`, and `details` as an alias for `note`. Renaming storage
columns is unnecessary for the first dashboard and would add migration risk.

## Current time limitation

Existing `created_at` and `occurred_at` values are local wall-clock timestamps
without an explicit UTC offset or IANA time-zone identifier. Daily analysis can
preserve the captured local calendar day. Cross-source alignment—especially
Apple Health, travel, and daylight-saving boundaries—must wait for an explicit
time-zone policy.
