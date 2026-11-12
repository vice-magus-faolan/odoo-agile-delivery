# ADR-003: Sprint scope history strategy

## Status

Accepted and implemented in `project_scrum`. [ADR-009](009-scrum-analytics-semantics.md)
defines the delivered reestimation, completion and reporting semantics.

## Context and decision

A Sprint is a time-box, not a native Project Milestone. Mutable Task-to-Sprint
assignments cannot reconstruct original commitment, scope changes or carry-over.
Starting a Sprint therefore freezes commitment and appends immutable
`project.sprint.scope.event` records with Sprint, Task, observed points, timestamp,
actor and optional reason.

Starting includes every still-assigned Task, whether live or archived. After Sprint,
Project and company authorization, activation enumerates the full assignment set,
restores the caller environment and requires read access before freezing commitment or
emitting events. Hidden assigned work rejects the whole start rather than silently
narrowing history. The same selection supplies commitment and initial completion facts.

Native Task state `1_done` means completion. Entering it records `completed`; leaving it
records `reopened`. Folded stages and `is_closed` are not completion signals:
`1_canceled` is closed but not completed. Pre-write values make repeated writes
idempotent across bulk, UI and RPC paths.

At start, every `committed` event for an already-done Task is followed by `completed`.
Later completion events occur only while the assigned Sprint is active. Task changes
after close cannot rewrite the closed ledger. Ordinary users cannot create, edit or
delete scope events. Trusted superuser recovery may correct immutable facts or
`closed_at`; lifecycle state remains action-only even for superuser.

## Close transaction and carry-over

Completed Tasks remain on the closed Sprint. A Project administrator explicitly moves
unfinished work to Product Backlog or a different compatible Draft Sprint. The source
records `carried_to_backlog` or `carried_to_sprint`; the latter names the exact target
Sprint rather than encoding it in free text. The target receives commitment only when it
starts.

Closing checks the entire unfinished set, including archived Tasks, and requires caller
write access. It validates the still-active source and same-Project, company and team
Draft target, coordinates the involved Sprints/Tasks, moves all unfinished work, records
history and closes the source in one transaction. Any access, validation, concurrency or
write failure leaves none of those changes. Closed Sprint assignments reject ordinary
changes.

## Alternatives and consequences

Current assignments lose removed work; aggregate-only snapshots lose Task-level
explanation; Milestones have different lifecycle meaning. The immutable event ledger
instead supports the additive analytics defined in ADR-009 and requires explicit access,
retention and trusted correction boundaries. Native Task and Project permissions remain
authoritative.

Archive-inclusive activation is forward-only. Already-active and closed Sprints retain
their stored commitment and events, including any earlier omissions of Tasks archived
before start. No automatic backfill, recomputation or historical repair is performed.
