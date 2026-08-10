# Daily Context Explorer v0.1 Specification

## 1. Status and Authority

This document is the authoritative product and data-contract specification for
Daily Context Explorer v0.1. This documentation PR does not implement the
explorer, its API endpoint, or its dashboard.

Later implementation PRs must update this document when they intentionally
change behavior defined here. They must not silently invent different product,
privacy, validation, ordering, rounding, or edge-case rules.

## 2. Purpose

The Daily Context Explorer is:

> A local, read-only view of logged events in relation to calendar days and
> event names.

It describes the stored record. It does not reconstruct or judge the user's
complete context, conduct, health, wellbeing, productivity, or internal state.

### 2.1 User-facing terminology

The interface must use descriptive logging language:

| Use | Avoid |
| --- | --- |
| Days with logged events | Active days |
| Days without logged events | Inactive days |
| Logging coverage | Behavioral coverage |
| Event count | Activity level |
| Logged-event distribution | Behavior pattern |

A day without events means only that no event was logged. Missing logs cannot
be interpreted as inactivity. Event volume is not a measure of effort,
productivity, importance, health, or wellbeing. Data-quality warnings limit
interpretation but do not judge the underlying behavior.

## 3. Questions v0.1 Answers

v0.1 answers only:

1. How many valid events were logged during the selected window?
2. On how many calendar days were events logged?
3. How were logged-event counts distributed across the window?
4. Which event names occurred most often?
5. What aggregate event-name mix occurred on the selected day?
6. Are timestamp or naming problems limiting interpretation?

v0.1 does not answer:

- why something happened
- whether a pattern is good or bad
- whether the user was active or inactive
- whether an AURA state changed
- whether two events are causally related

## 4. Future Interface

v0.1 plans one dashboard screen. The screen and its endpoint do not exist yet.

### 4.1 Window controls

- Presets are 7, 30, and 90 inclusive calendar days.
- The UI default is 30 days ending on the user's current local date.
- A 7-day request begins six calendar days before its end date; 30- and 90-day
  requests use the same inclusive rule.
- The UI provides an end-date picker and a **Today** action.
- v0.1 permits a minimum one-day window and a maximum 90-day window.
- v0.1 provides no custom window longer than 90 calendar days.

The UI may read the user's current local date to choose its default request.
The API remains deterministic for a given database and request and returns no
current-time or generated-at field.

### 4.2 Summary

The summary displays:

- Logged events
- Days with logged events
- Days without logged events
- Logging coverage
- Average events per day with logs

### 4.3 Daily logging chart

- Include one point or bar for every calendar date in the requested window.
- Include zero-event dates explicitly.
- Order dates ascending.
- Selecting a date updates the selected-day summary.
- Do not use qualitative or inferential color coding.

### 4.4 Selected-day summary

Display only:

- selected calendar date
- total valid event count
- aggregate counts by event-name label

Do not display individual event times, notes, IDs, raw event records, or edit
or delete actions.

### 4.5 Event mix

Display aggregate event-name counts for the requested window. Sort by event
count descending and then by the deterministic label rule in Section 8. Do not
perform semantic grouping, normalization, categorization, or AI interpretation.

### 4.6 Data-quality panel

Display:

- invalid occurrence-timestamp count, clearly labeled as corpus-scoped
- blank event-name count, clearly labeled as window-scoped
- a warning that stored timestamps do not provide validated timezone history
- an explanation that invalid occurrence timestamps are excluded from date
  buckets and date-based metrics

The interface must not imply that the corpus-wide invalid-timestamp count
belongs only to the requested window.

## 5. Future API Request Contract

The planned endpoint is:

```text
GET /api/v1/daily-context
    ?start=YYYY-MM-DD
    &end=YYYY-MM-DD
    &selected_date=YYYY-MM-DD
```

The endpoint is not implemented by this documentation PR.

### 5.1 Parameters

- `start` and `end` are required.
- Both bounds are inclusive.
- Dates must use strict `YYYY-MM-DD` syntax and identify real Gregorian dates.
- `start` must not be after `end`.
- The inclusive window must contain between 1 and 90 calendar days.
- `selected_date` is optional and defaults to `end`.
- When supplied, `selected_date` must fall inside the requested window.

Calendar bucketing uses the project's documented stored local-calendar-date
semantics. v0.1 performs no timezone conversion, offset correction, or timezone
history reconstruction. A stored occurrence timestamp is bucketable only when
it produces a valid calendar date under those semantics.

### 5.2 Service boundary

- The endpoint is read-only.
- It uses a dedicated aggregate analysis path, not the raw `/events` response.
- It is available only through the application's loopback/local boundary.
- It opens SQLite read-only and performs no schema write or migration.
- Importing the future endpoint or analysis module must not open a database.
- Successful and error responses include `Cache-Control: no-store`.
- Responses contain no current-time or generated-at value.

## 6. Successful Response Contract

The following structure is normative:

```json
{
  "contract_version": "daily-context.v1",
  "range": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD",
    "selected_date": "YYYY-MM-DD",
    "calendar_day_count": 30,
    "calendar_basis": "stored-local-date"
  },
  "summary": {
    "event_count": 0,
    "days_with_logged_events": 0,
    "days_without_logged_events": 30,
    "logging_coverage_ratio": 0.0,
    "average_events_per_logged_day": null
  },
  "days": [
    {
      "date": "YYYY-MM-DD",
      "event_count": 0
    }
  ],
  "event_name_totals": [
    {
      "label": "Example",
      "event_count": 0
    }
  ],
  "selected_day": {
    "date": "YYYY-MM-DD",
    "event_count": 0,
    "event_name_totals": []
  },
  "quality": {
    "invalid_occurred_at_count": 0,
    "invalid_occurred_at_scope": "corpus",
    "blank_event_name_count": 0,
    "blank_event_name_scope": "window",
    "timezone_history_available": false
  },
  "privacy": {
    "aggregate_only": true,
    "includes_event_name_labels": true,
    "includes_details": false,
    "includes_identifiers": false,
    "includes_individual_timestamps": false
  }
}
```

The placeholder strings and counts above illustrate the normative object and
field structure. The field rules below govern valid runtime values. In
particular, an event-name item has a positive count; when no valid event-name
aggregate exists, its containing array is empty.

## 7. Field Definitions

All fields are required unless a field is explicitly nullable. Objects do not
gain undocumented fields in `daily-context.v1`.

### 7.1 Contract and range

| Field | JSON type | Meaning and scope | Nullability and empty state | Ordering |
| --- | --- | --- | --- | --- |
| `contract_version` | string | Response contract identifier; always `daily-context.v1` | Never null | Not applicable |
| `range.start` | string | Inclusive requested start date | Never null | Not applicable |
| `range.end` | string | Inclusive requested end date | Never null | Not applicable |
| `range.selected_date` | string | Selected date, supplied or defaulted to `end` | Never null | Not applicable |
| `range.calendar_day_count` | integer | Inclusive count of dates from `start` through `end` | Never null; at least 1 and at most 90 | Not applicable |
| `range.calendar_basis` | string | Bucketing basis; always `stored-local-date` | Never null | Not applicable |

### 7.2 Summary

| Field | JSON type | Meaning and scope | Nullability and empty state | Ordering |
| --- | --- | --- | --- | --- |
| `summary.event_count` | integer | Valid, bucketable events inside the window | Never null; `0` when none | Not applicable |
| `summary.days_with_logged_events` | integer | Window dates with at least one valid event | Never null; `0` when none | Not applicable |
| `summary.days_without_logged_events` | integer | Window dates with zero valid events | Never null; equals the full window size when none | Not applicable |
| `summary.logging_coverage_ratio` | number | Days with logs divided by calendar-day count | Never null; `0.0` when none | Not applicable |
| `summary.average_events_per_logged_day` | number or null | Valid event count divided by days with logs | `null` when no day contains a valid event | Not applicable |

### 7.3 Daily sequence

| Field | JSON type | Meaning and scope | Nullability and empty state | Ordering |
| --- | --- | --- | --- | --- |
| `days` | array of objects | One bucket for every requested date | Never null or empty for a valid request | Dates ascending |
| `days[].date` | string | Calendar date represented by the bucket | Never null | Ascending within `days` |
| `days[].event_count` | integer | Valid events on that date | Never null; `0` for a date without logs | Not applicable |

### 7.4 Window event-name totals

| Field | JSON type | Meaning and scope | Nullability and empty state | Ordering |
| --- | --- | --- | --- | --- |
| `event_name_totals` | array of objects | Aggregate labels for valid events in the window | Never null; empty array when no valid events | Count descending, then label ascending |
| `event_name_totals[].label` | string | Exact stored nonblank event name or `(blank)` | Never null | Unicode code-point order for ties |
| `event_name_totals[].event_count` | integer | Valid window events assigned to the label | Never null; positive when an item exists | Primary descending sort key |

### 7.5 Selected day

| Field | JSON type | Meaning and scope | Nullability and empty state | Ordering |
| --- | --- | --- | --- | --- |
| `selected_day` | object | Aggregate-only view of the selected date | Never null | Not applicable |
| `selected_day.date` | string | Selected calendar date | Never null | Not applicable |
| `selected_day.event_count` | integer | Valid events on the selected date | Never null; `0` when none | Not applicable |
| `selected_day.event_name_totals` | array of objects | Aggregate labels on the selected date | Never null; empty array when none | Count descending, then label ascending |
| `selected_day.event_name_totals[].label` | string | Exact stored nonblank event name or `(blank)` | Never null | Unicode code-point order for ties |
| `selected_day.event_name_totals[].event_count` | integer | Selected-day events assigned to the label | Never null; positive when an item exists | Primary descending sort key |

### 7.6 Quality

| Field | JSON type | Meaning and scope | Nullability and empty state | Ordering |
| --- | --- | --- | --- | --- |
| `quality.invalid_occurred_at_count` | integer | Rows in the entire corpus whose occurrence timestamp cannot be bucketed | Never null; `0` when none | Not applicable |
| `quality.invalid_occurred_at_scope` | string | Scope marker; always `corpus` | Never null | Not applicable |
| `quality.blank_event_name_count` | integer | Valid window events with null, empty, or whitespace-only event names | Never null; `0` when none | Not applicable |
| `quality.blank_event_name_scope` | string | Scope marker; always `window` | Never null | Not applicable |
| `quality.timezone_history_available` | boolean | Whether validated historical timezone data is available; `false` in v0.1 | Never null | Not applicable |

### 7.7 Privacy declaration

| Field | JSON type | Meaning and scope | Nullability and empty state | Ordering |
| --- | --- | --- | --- | --- |
| `privacy.aggregate_only` | boolean | Response contains aggregates rather than raw records; always `true` | Never null | Not applicable |
| `privacy.includes_event_name_labels` | boolean | Sensitive aggregate event names are present; always `true` | Never null | Not applicable |
| `privacy.includes_details` | boolean | Details or notes are present; always `false` | Never null | Not applicable |
| `privacy.includes_identifiers` | boolean | Database or source identifiers are present; always `false` | Never null | Not applicable |
| `privacy.includes_individual_timestamps` | boolean | Individual occurrence or creation timestamps are present; always `false` | Never null | Not applicable |

## 8. Metric, Ordering, and Rounding Semantics

### 8.1 Valid event count

`summary.event_count` counts only rows with a valid, bucketable occurrence date
inside the inclusive window. Invalid occurrence timestamps do not contribute to
event count, daily buckets, days with logs, coverage, selected-day totals, or
event-name totals. They remain visible only in the corpus-scoped diagnostic.

### 8.2 Days and logging coverage

```text
days_without_logged_events =
    calendar_day_count - days_with_logged_events
```

```text
logging_coverage_ratio =
    days_with_logged_events / calendar_day_count
```

- The ratio is between `0.0` and `1.0` inclusive.
- Round the API ratio to four decimal places using decimal half-up rounding.
- The UI displays it as a percentage rounded to one decimal place using the
  same decimal half-up rule.
- The ratio is `0.0` when no dates contain valid events.
- Days without logged events can never be negative.

### 8.3 Average per logged day

```text
average_events_per_logged_day =
    event_count / days_with_logged_events
```

- Round to two decimal places using decimal half-up rounding.
- Return `null` when `days_with_logged_events` is zero.
- The UI renders `null` as an em dash or **Not available**, not as zero.

### 8.4 Daily sequence

Include every date from `start` through `end`, including leading, internal, and
trailing zero-event dates. Use integer zero for dates without valid events and
sort the sequence by date ascending.

### 8.5 Event-name labels

Event names are sensitive user content.

- Nonblank event names retain their exact stored wording.
- Do not trim, case-fold, merge, categorize, or semantically normalize a
  nonblank name.
- `NULL`, empty, and whitespace-only names map to the neutral label `(blank)`.
- Blank-name events remain included in valid event totals.
- Sort aggregates by `event_count` descending, then by label ascending using
  case-sensitive Unicode code-point order over the returned label.
- Apply identical labeling and ordering to window and selected-day aggregates.
- Do not log event names or place them in diagnostics, errors, telemetry, the
  name-free baseline audit, or examples derived from real data.

### 8.6 Aggregate consistency

The response aggregates must satisfy these invariants:

```text
summary.event_count
    = sum(days[].event_count)
    = sum(event_name_totals[].event_count)
```

```text
selected_day.event_count
    = the event_count of the days[] entry whose date equals selected_day.date
    = sum(selected_day.event_name_totals[].event_count)
```

The sum of an empty aggregate array is zero. These relationships apply in all
states, including an empty database, a window without valid events, and a
selected date without events. Invalid occurrence timestamps are excluded
consistently from every quantity in these equations. Blank-name events remain
included and contribute through the `(blank)` event-name bucket.

Every selected date has exactly one matching entry in the zero-filled `days`
sequence. Implementations must not emit aggregate lists or totals that violate
these relationships.

## 9. Validation and Error Behavior

Validation failures return HTTP 400 and a stable error response:

```json
{
  "error": {
    "code": "invalid_date_format",
    "message": "A date parameter is invalid."
  }
}
```

`error.code` is a stable string intended for programmatic handling.
`error.message` is a generic, non-sensitive string. Error responses do not echo
raw parameters.

| Error code | Condition |
| --- | --- |
| `missing_parameter` | Required `start` or `end` is absent |
| `invalid_date_format` | A date is not strict `YYYY-MM-DD` or is not a real calendar date |
| `start_after_end` | `start` is after `end` |
| `range_too_large` | Inclusive range exceeds 90 calendar days |
| `selected_date_out_of_range` | Supplied selected date falls outside the window |

Unexpected failures return HTTP 500 with code `internal_error` and a generic
message. They do not expose SQL, database paths, user content, raw parameters,
or implementation details. All successful and error responses use
`Cache-Control: no-store`.

## 10. Deterministic Edge Cases

1. **Empty database:** Return a full zero-filled daily sequence, zero summary
   counts, `0.0` logging coverage, `null` average, empty name arrays, and zero
   quality counts.
2. **No valid events in the window:** Return the same window summary and daily
   behavior as an empty database. The corpus-scoped invalid-timestamp count may
   still be nonzero.
3. **Invalid-timestamp-only corpus:** Exclude every row from date and name
   aggregates. Return zero valid counts and report all such rows only in the
   corpus-scoped invalid-timestamp diagnostic.
4. **Mixed valid and invalid timestamps:** Calculate all window and selected-day
   measures from valid rows only. Invalid rows do not change valid coverage or
   distributions.
5. **Blank event names:** Count valid rows normally, map null, empty, and
   whitespace-only names to `(blank)`, and include them in the window-scoped
   blank-name diagnostic.
6. **Selected date with no events:** Return the selected date, event count `0`,
   and an empty selected-day event-name array.
7. **Inclusive boundaries:** Include valid events exactly on both `start` and
   `end` dates.
8. **One-day window:** Return one daily bucket. Coverage is `1.0` when that date
   has a valid event and `0.0` otherwise.
9. **Maximum window:** Accept exactly 90 inclusive dates and return exactly 90
   daily buckets.
10. **Reversed dates:** Return HTTP 400 with `start_after_end`.
11. **Malformed or impossible dates:** Return HTTP 400 with
    `invalid_date_format`.
12. **Selected date outside the window:** Return HTTP 400 with
    `selected_date_out_of_range`.
13. **Duplicate rows:** Treat each stored row as a separate logged event. v0.1
    performs no analytical deduplication beyond constraints already enforced by
    storage and synchronization.

## 11. Privacy Requirements

The explorer may return:

- aggregate counts
- aggregate calendar-date buckets
- aggregate event-name labels

It must exclude:

- details or notes
- database IDs
- source-event identifiers
- individual occurrence timestamps
- creation timestamps
- receipt information
- synchronization status
- database paths
- raw event rows
- exports or sharing
- telemetry containing user content

The surface is local and loopback-only, and its responses are not cached.
Aggregate event names remain sensitive even when accompanied only by counts.
The name-free `build_baseline_report()` contract remains unchanged. Automated
tests and documentation examples use synthetic data only.

## 12. Observation, Derived-Measure, and AURA Boundary

| Layer | v0.1 status |
| --- | --- |
| Stored logged events | Observations |
| Counts, date buckets, coverage, and distributions | Reproducible derived measures |
| Coherence, energy, emotion, mode, plasticity, meaning, and causal context | Unimplemented inferred constructs |

- v0.1 contains no AURA state estimation.
- Event volume is not AURA energy.
- Missing logs are not incoherence.
- Event-name distribution is not mode.
- Logged content is not an emotion measurement.
- Logging coverage is not behavioral coverage.
- The 7/30/90-day display windows are not AURA fast, intermediate, or slow
  dynamical timescales.
- No derived measure may be described as a psychological, behavioral,
  clinical, or wellness score.

These principles constrain product claims. v0.1 defines no equations, scores,
inferred states, or speculative mappings for AURA.

## 13. Explicit Non-goals

PR1 neither specifies nor implements:

- period-to-period comparison
- long-term trend analysis
- goals, targets, or adherence judgments
- raw event browsing
- event editing or deletion
- notes or narratives
- hour-of-day analysis
- exports or sharing
- AI summaries or classifications
- AURA state estimation
- schema changes
- endpoint code
- dashboard code

## 14. Acceptance Criteria

Daily Context Explorer v0.1 is conformant when:

- the future UI offers 7-, 30-, and 90-day inclusive windows and defaults to 30
  days ending on the user's current local date
- request validation implements every rule and stable error code in Section 9
- successful responses match `daily-context.v1` without undocumented fields
- daily output contains every requested date in ascending order
- summary metrics, name aggregates, ordering, and rounding follow Section 8
- invalid timestamps are excluded from date-based measures and remain visible
  only in the corpus-scoped diagnostic
- selected-day output contains aggregates and no raw records
- prohibited fields in Section 11 never appear in the response
- both success and error responses use `Cache-Control: no-store`
- SQLite is opened read-only and importing modules performs no database access
- event-name labels remain local, sensitive, and absent from logs and errors
- the name-free baseline audit remains unchanged
- automated tests use only synthetic temporary data and cover all edge cases
- documentation and implementation remain consistent

## 15. Planned PR Sequence

1. **PR1 — Specification:** establish this contract and its documentation
   references without code, schema, or dashboard changes.
2. **PR2 — Aggregate analysis:** implement a dedicated read-only aggregate
   function and synthetic contract tests.
3. **PR3 — Local API:** implement request validation, stable errors, no-store
   headers, and the loopback-only `/api/v1/daily-context` endpoint.
4. **PR4 — Dashboard:** implement the single-screen interface against the
   aggregate endpoint, including window controls and selected-day aggregates.

Later PRs must keep this document current when approved behavior changes.
