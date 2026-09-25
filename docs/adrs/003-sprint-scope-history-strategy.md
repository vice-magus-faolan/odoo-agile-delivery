# ADR-003: Sprint Scope History Strategy

## Status

Accepted — implemented by the Milestone 2 project_scrum foundation.

## Context

A Sprint is not a Milestone, and current task-to-Sprint assignments are mutable.
Analytics cannot reconstruct original commitment, added or removed scope,
completion, or carry-over from current relationships alone.

## Decision

The `project_scrum` module keeps Sprint lifecycle separate from milestones and
records an immutable commitment snapshot when a Sprint starts. It appends
`project.sprint.scope.event` records for committed, added, and removed scope.
Each record retains the Sprint, task, story-point value observed at the event,
timestamp, actor, and optional reason. Native Odoo 19 state `1_done` owns
completion: a non-done to `1_done` edge appends `completed`, and a `1_done` to
non-done edge appends `reopened`. `is_closed` and folded stages are rejected as
signals because `1_canceled` is closed but not completed. The task write path
captures pre-write state, so repeated writes are idempotent and bulk, UI, and
RPC writes share the same evidence.

Only transitions while the assigned Sprint is active append completion facts.
After close, native task state may change but cannot mutate the closed ledger or
historical numbers. Ordinary ORM users cannot create, change, or delete scope
events. Superuser correction is the explicit administrative recovery boundary.

## Alternatives

- Derive history from current task assignments: rejected because moved tasks
  erase history.
- Store periodic aggregate snapshots only: rejected because task-level audit and
  correction semantics are lost.
- Reuse project milestones as Sprints: rejected because their lifecycle and
  historical meaning differ.

## Consequences

Burndown, burnup, velocity, scope change, and commitment-versus-completion
remain deferred until completed and reopened event semantics exist. The
append-only record creates an audit surface and requires explicit retention,
access, and correction rules.

## Open Questions

- How should estimation changes during an active Sprint be represented?
- Which events become immutable at close versus visible as later corrections?

## Evidence

- [Mission brief: Sprint ≠ Milestone](../mission-brief.md#rule-4--a-sprint-is-not-a-milestone)
- [Mission brief: historical scope requirement](../mission-brief.md#9-sprint-scope-history)
- [Mission brief: Scrum foundation](../mission-brief.md#22-milestone-2-scrum-foundation)
