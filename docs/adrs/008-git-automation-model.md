# ADR-008: Git Automation Model

## Status

Proposed — automation implementation is deferred beyond Milestone 1.

## Context

Provider connectors report facts such as branch creation, commit push, CI result, and pull-request merge. Workflow effects are project policy: `PR merged` must not intrinsically mean `Task Done`. A webhook controller must return promptly after validation and hand durable processing to an asynchronous path.

## Decision

Keep provider fact ingestion separate from automation policy. Future processing will: authenticate and persist a delivery; enqueue normalization after persistence; associate tasks using explicit immutable Agile keys before heuristics; record normalized Git facts; then evaluate project-scoped, opt-in automation rules. Delivery idempotency and queue identity are required before a rule can apply. Evaluate `queue_job` before creating custom workers.[9]

No webhook route, worker, automation model, provider dependency, or task-state side effect is added in Milestone 1.

## Alternatives

- Hardcode `PR merged → Done`: rejected because workflow meaning differs by project and bypasses review/QA policy.
- Perform normalization and task writes synchronously in the controller: rejected because retries, provider latency, and failure visibility become unsafe.
- Let provider payloads directly mutate tasks: rejected because facts and policy become coupled and cross-project controls are harder to audit.

## Consequences

Future implementation needs explicit rule ownership, permissions, audit records, dry-run/disable controls, retry observability, and tests for duplicate, forged, and out-of-order deliveries. It may initially expose facts without any workflow automation.

## Open Questions

- What rule conditions and actions are safe for the first release?
- Which role may create, approve, and disable a rule?
- How are failed automation attempts surfaced and replayed without duplicate task changes?

## Evidence

- [Mission brief: provider facts separated from automation](../mission-brief.md#rule-9--git-integrations-report-facts)
- [Mission brief: target automation policy](../mission-brief.md#15-git-automation)
- [ADR-007: adoption strategy](007-oca-project-git-adoption-strategy.md)

## Sources

[9] https://raw.githubusercontent.com/OCA/queue/19.0/queue_job/__manifest__.py
