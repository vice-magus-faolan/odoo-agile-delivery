# ADR-006: Knowledge Relationship Model

## Status

Proposed — implementation is deferred beyond Milestone 1.

## Context

The product needs architecture documents, ADRs, runbooks, retrospectives, Definition of Done, and release notes without recreating a wiki. Project, task, Sprint, and release need navigable links to the relevant Knowledge articles.

## Decision

Use Odoo Knowledge as the authoritative document system. A future optional `project_agile_knowledge` integration will model relationships and navigation only: Project ↔ Knowledge root, Task ↔ related articles, Sprint ↔ retrospective, and Release ↔ release notes. It will provide templates and conventions but will not duplicate article storage, permissions, or editor behavior. The integration remains optional because Knowledge is not a Milestone 1 dependency.

## Alternatives

- Build a custom wiki: rejected because it duplicates Knowledge.
- Store ADR/runbook content on Project or Task fields: rejected because article lifecycle, navigation, and reuse are lost.
- Make Knowledge a hard dependency of `project_agile`: rejected because Agile core must remain independently installable.

## Consequences

Future integrations must respect Knowledge ACLs and avoid broad access through smart buttons. Relationship cardinality, unlink behavior, and template provisioning require upgrade-safe tests. Milestone 1 retains only documentation conventions in this repository.

## Open Questions

- Which relations are one-to-one, many-to-one, or many-to-many?
- How should archives and deleted articles be represented without losing historical links?
- Which templates are seeded versus user-created?

## Evidence

- [Mission brief: Knowledge is first-class](../mission-brief.md#rule-8--knowledge-is-first-class)
- [Mission brief: intended Knowledge relationships](../mission-brief.md#knowledge-relationships)
- [Milestone 1 design: Knowledge is a non-goal](../project_agile-design.md#boundary)
