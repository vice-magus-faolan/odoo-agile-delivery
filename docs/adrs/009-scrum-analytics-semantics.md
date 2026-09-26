# ADR-009: Trustworthy Scrum Analytics Semantics

## Status

Accepted — Milestone 3 calculation contract. The minimal history extension is implemented in `project_scrum`; report models and views remain deferred.

## Context

ADR-003 did not make estimate changes, tasks born done, or Sprint close time reconstructable. Reports must replay immutable facts, never current task relationships or `write_date`.

## Decision

### Timeline and replay

Sort events by `(event_at, id)` ascending. `event_at` is UTC and id breaks same-timestamp ties. Calculate in UTC; render bucket labels in the requesting user timezone.

Per task, replay `(in_scope, done, points)`: `committed` and `added` set in-scope with event points; `removed` clears in-scope; `reestimated` changes points from `previous_story_points` to `story_points`; `completed` sets done; `reopened` clears done. `closed_at`, recorded after carry-over facts in the close transaction, is the close boundary.

A multi-field write orders source removal at the pre-write estimate, destination addition at the post-write estimate, in-place reestimate, then completion or reopening. Generated event ids preserve the order. A task created or assigned already in `1_done` emits `added` then `completed`.

Zero or empty Float estimates are explicit zero-point work. Calculators sum stored Float values without intermediate rounding; presentation rounds once to two decimal places.

### Point-in-time formulas

At bucket `t`, replay events at or before `t`.

- Burndown: `sum(points for in_scope and not done)`.
- Burnup: completed `sum(points for in_scope and done)`; total `sum(points for in_scope)`.
- Scope change: initial is committed-event points; added and removed are their event sums; final scope is task replay, which includes reestimate deltas and repeated add/remove paths.
- Velocity: only at `closed_at`, sum final points for in-scope, done tasks. It includes added scope and excludes work removed before close.
- Commitment versus completion: commitment is committed-event points. Completed commitment is those original values for committed tasks whose replayed done state is true at `closed_at`; percentage is zero for zero commitment, otherwise completed divided by commitment.

Completed → reopened → completed resolves to final done. Native `1_canceled` is neither completion nor removal and remains scope until an explicit remove or carry-over fact. Carry-over is unfinished at close and is not velocity; a target Sprint gets no commitment until its own start.

### Freeze and correction

Closed reports replay only facts at or before `closed_at`; later task state, estimate, project, or assignment edits cannot alter them. Ordinary users cannot create, edit, or delete scope events or write `closed_at`. Superuser administration is the explicit recovery boundary and may correct facts or close time. This is trusted recovery, not ordinary workflow.

## Consequences

One replay path can support all five reports. Closed Sprints predating this extension lack reestimate or close-time facts and must not claim ADR-009 precision for those gaps.

## Alternatives

- Current task state or `write_date`: rejected because later edits rewrite apparent history.
- Aggregate-only snapshots: rejected because they cannot explain a value from task facts.
- Cancellation as completion: rejected because ADR-003 distinguishes `1_canceled` from `1_done`.

## Evidence

- [Mission brief: historical Scrum data](../mission-brief.md#rule-10--historical-scrum-data-must-remain-historical)
- [ADR-003](003-sprint-scope-history-strategy.md)
