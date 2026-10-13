# ADR-007: OCA `project_git` Adoption Strategy

## Status

Proposed — no Git connector is added in Milestone 1.

## Context

The future Git integration needs provider-neutral facts, secure webhooks, idempotency,
and explicit Agile-key association without creating a private competing webhook stack.
OCA Project PR #1792 is an open draft for 17.0, while the 19.0 Project branch exposes
related modules but not `project_git`, `project_github`, or `project_gitlab`.[1][2] The
proposed generic connector has branch, commit, pull-request, and event handling, but its
task matching includes mutable task names and database-id forms that do not meet this
suite's immutable `agile_key` contract.[5][6]

## Decision

Do not install, locally forward-port, or depend on the proposed connector now. Continue
Agile and Scrum work independently. When Git work is scheduled, pursue an upstream-first
Odoo 19 design/contribution with these layers: provider ingestion, durable authenticated
delivery ledger, normalized Git facts, immutable Agile-key association, and opt-in
automation policy. Evaluate OCA `queue_job` before any custom worker.

## Alternatives

- Local fork/forward-port of PR #1792: rejected because it is draft 17.0 work and
  creates a competing maintenance line.
- New private webhook stack: rejected because it duplicates an active upstream design
  space and raises security/operability risk.
- Depend on `project_task_code`: rejected because its global company-unique code is not
  the required project-prefixed immutable Agile key.[8]

## Consequences

Milestone 1 remains free of Git/OCA dependencies. Future implementation must define
repository-scoped credentials, delivery-id idempotency, raw-event retention,
retry/failure visibility, provider CI mapping, and cross-project association isolation.
`queue_job` is a candidate async mechanism, not a substitute for a durable delivery
ledger.[9]

## Open Questions

- Will the OCA work land in `OCA/project`, `version-control-platform`, or another
  upstream home?
- Which provider delivery IDs and database constraints provide replay protection?
- What grammar supports explicit `ENG-142` references, multi-key payloads, and safe
  project scoping?
- How will out-of-order GitHub checks and GitLab pipeline states normalize?

## Evidence

- [Git/OCA research note](../research/oca-git-adoption.md)
- [Mission brief: Git research spike](../mission-brief.md#12-git-integration-research-spike)
- [Mission brief: webhook requirements](../mission-brief.md#16-webhook-requirements)

## Sources

[1] https://github.com/OCA/project/tree/19.0 [2]
https://api.github.com/repos/OCA/project/pulls/1792 [5]
https://raw.githubusercontent.com/OCA/project/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_event.py
[6]
https://raw.githubusercontent.com/OCA/project/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_pull_request.py
[8]
https://raw.githubusercontent.com/OCA/project/19.0/project_task_code/models/project_task.py
[9] https://raw.githubusercontent.com/OCA/queue/19.0/queue_job/__manifest__.py
