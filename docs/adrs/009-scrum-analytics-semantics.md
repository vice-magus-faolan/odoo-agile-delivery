# ADR-009: Trustworthy Scrum Analytics Semantics

## Status

Accepted — Milestone 3 calculation and additive native-reporting contract.

## Context

ADR-003 did not make estimate changes, tasks born done, or Sprint close time
reconstructable. Reports must replay immutable facts, never current task relationships
or `write_date`.

## Decision

### Timeline and replay

Sort events by `(event_at, id)` ascending. `event_at` is UTC and id breaks
same-timestamp ties. Calculate in UTC; render bucket labels in the requesting user
timezone.

Per task, replay `(in_scope, done, points)`: `committed` and `added` set in-scope with
event points; `removed` clears in-scope; `reestimated` changes points from
`previous_story_points` to `story_points`; `completed` sets done; `reopened` clears
done; `carried_to_backlog` and `carried_to_sprint` each clear in-scope without changing
done. `closed_at`, recorded after carry-over facts in the close transaction, is the
close boundary.

A multi-field write orders source removal at the pre-write estimate, destination
addition at the post-write estimate, in-place reestimate, then completion or reopening.
Generated event ids preserve the order. At Sprint start, a task assigned while draft and
already in `1_done` emits `committed` then `completed`. A task created or assigned while
active already in `1_done` emits `added` then `completed`.

Zero or empty Float estimates are explicit zero-point work. Calculators sum stored Float
values without intermediate rounding; presentation rounds once to two decimal places.

### Point-in-time formulas

At bucket `t`, replay events at or before `t`.

- Burndown: `sum(points for in_scope and not done)`.
- Burnup: completed `sum(points for in_scope and done)`; total
  `sum(points for in_scope)`.
- Scope change: initial is committed-event points; added and removed are their event
  sums; final scope is task replay, which includes reestimate deltas and repeated
  add/remove paths.
- Velocity: only at `closed_at`, sum final points for in-scope, done tasks. It includes
  added scope and excludes work removed before close.
- Commitment versus completion: commitment is committed-event points. Completed
  commitment is those original values for committed tasks whose replayed done state is
  true at `closed_at`; percentage is zero for zero commitment, otherwise completed
  divided by commitment.

Completed → reopened → completed resolves to final done. Native `1_canceled` is neither
completion nor removal and remains scope until an explicit remove or carry-over fact.
Carry-over is unfinished at close and is not velocity; a target Sprint gets no
commitment until its own start.

### Native reporting projections

`project_scrum_analytics` stores one read-only report projection per Scrum Sprint and
one read-only timeline projection per immutable scope event. The projections only make
the accepted replay available to Odoo list, pivot, graph, export, filter, and drill-down
surfaces; they do not change native Project analytics or create records for non-Agile
projects.

Velocity, Burndown, Burnup, Scope Change, and Commitment vs Completion label story
points explicitly. The completion ratio remains an explicit `fraction`, not a silently
formatted percentage. Active Sprints are live replay; closed Sprints with `closed_at`
are trusted frozen replay. Timeline timestamps remain UTC and chart date buckets render
in the requesting user's timezone.

Read access is the intersection of available-company access and the native Project
access result. Stored report records are read-only for ordinary Project users and
managers. Export, grouped results, direct ORM access, and drill-down actions apply the
same project/company authorization; a browser-provided report, Sprint, timeline, or Task
identifier is never authority.

### Freeze and correction

Closed reports replay only facts at or before `closed_at`; later task state, estimate,
project, or assignment edits cannot alter them. Ordinary users cannot create, edit, or
delete scope events or write `closed_at`. Superuser recovery may correct `closed_at` or
immutable scope facts; a close-time correction synchronously rebuilds that Sprint's
stored report and timeline from the corrected boundary; lifecycle state remains
action-only, including for superuser. This is trusted recovery, not ordinary workflow.

## Consequences

One replay path supports all five reports. Closed Sprints predating this extension lack
reestimate or close-time facts and must not claim ADR-009 precision for those gaps.

## Alternatives

- Current task state or `write_date`: rejected because later edits rewrite apparent
  history.
- Aggregate-only snapshots: rejected because they cannot explain a value from task
  facts.
- Cancellation as completion: rejected because ADR-003 distinguishes `1_canceled` from
  `1_done`.
- Custom OWL charts: rejected because native list, pivot, graph, filters, export, and
  drill-down views satisfy the reporting contract without a frontend-specific
  authorization surface.

## Open Questions

None for the delivered Milestone 3 replay and projection contract.

## Evidence

- [ADR-003](003-sprint-scope-history-strategy.md)
