# ADR-003: Sprint Scope History Strategy

## Status

Proposed — implementation is deferred beyond Milestone 1.

## Context

A Sprint is not a Milestone, and current task-to-Sprint assignments are mutable. Analytics cannot reconstruct original commitment, added or removed scope, completion, or carry-over from current relationships alone.

## Decision

A future `project_scrum` module will keep Sprint lifecycle separate from milestones and record an immutable commitment snapshot when a Sprint starts. It will append `project.sprint.scope.event` records for committed, added, removed, completed, and reopened scope. Each record will retain the Sprint, task, story-point value observed at the event, timestamp, and actor. Corrections will be compensating events, not edits to historical facts.

No Sprint, scope-event, or analytics model is added in Milestone 1.

## Alternatives

- Derive history from current task assignments: rejected because moved tasks erase history.
- Store periodic aggregate snapshots only: rejected because task-level audit and correction semantics are lost.
- Reuse project milestones as Sprints: rejected because their lifecycle and historical meaning differ.

## Consequences

Burndown, burnup, velocity, scope change, and commitment-versus-completion remain deferred until event semantics and lifecycle tests exist. The append-only record creates an audit surface and requires explicit retention, access, and correction rules.

## Open Questions

- Which transition owns `completed` and `reopened` events?
- How should estimation changes during an active Sprint be represented?
- Which events become immutable at close versus visible as later corrections?

## Evidence

- [Mission brief: Sprint ≠ Milestone](../mission-brief.md#rule-4--a-sprint-is-not-a-milestone)
- [Mission brief: historical scope requirement](../mission-brief.md#9-sprint-scope-history)
- [Mission brief: deferred Scrum foundation](../mission-brief.md#22-milestone-2-scrum-foundation)
