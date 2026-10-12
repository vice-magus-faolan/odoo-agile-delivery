# Architecture Decision Records

Each ADR records a status, Context, Decision, Alternatives, Consequences, Open
Questions, and evidence links.

Implemented decisions:

- [ADR-001 Work-Item Key Generation](001-work-item-key-generation.md)
- [ADR-002 Configurable Item-Type Hierarchy](002-configurable-item-type-hierarchy.md)
- [ADR-003 Sprint Scope History Strategy](003-sprint-scope-history-strategy.md)
- [ADR-004 Agile Team / Multiple Active Sprint Model](004-agile-team-multiple-active-sprints.md)
- [ADR-009 Trustworthy Scrum Analytics Semantics](009-scrum-analytics-semantics.md)
- [ADR-011 Git Facts and Visibility Contract](011-git-facts-and-visibility-contract.md)

Accepted M7 contract with configuration, dry-run, apply and operator controls
implemented; independent adversarial/cumulative delivery gates and live activation
remain separate:

- [ADR-012 Milestone 7 Opt-in Git Workflow Policy Contract](012-git-workflow-policy-contract.md)

Proposed, intentionally deferred decisions:

- [ADR-005 Release / Version Model](005-release-version-model.md)
- [ADR-006 Knowledge Relationship Model](006-knowledge-relationship-model.md)
- [ADR-007 OCA `project_git` Adoption Strategy](007-oca-project-git-adoption-strategy.md)
- [ADR-008 Git Automation Model](008-git-automation-model.md) — historical, superseded
  by ADR-012

Proposed M8 contract with a real optional lineage skeleton, pending independent
same-card exact-SHA review (all other M8 functionality remains downstream):

- [ADR-013 Solution Definition, Revisions and Delivery Traceability](013-solution-definition-contract.md)

The proposed ADRs do not independently authorize new runtime dependencies or widen
approved scope. M8 work is bounded by its separately approved scope and serial plan.
