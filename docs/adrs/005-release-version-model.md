# ADR-005: Release / Version Model

## Status

Proposed — implementation remains deferred.

## Context

A release/version represents a delivery boundary; a Sprint represents a time-box; a
Milestone represents Odoo project planning. Conflating them destroys useful reporting
and release-note relationships. OCA's 19.0 `project_version` is installable and depends
only on `project`, but it is not a reason to add a dependency before the target
semantics are agreed.[3]

## Decision

Treat release/version as a future, project-scoped concept with explicit relations to
work items, optional Sprints, and Knowledge release notes. Keep it distinct from both
`project.sprint` and `project.milestone`. Before implementation, evaluate whether OCA
`project_version` satisfies the relationship and upgrade requirements; prefer
contribution or extension over a competing parallel model.

The suite currently adds no release/version module or dependency.

## Alternatives

- Reuse Milestones as releases: rejected because planning checkpoints and shipped
  versions are different facts.
- Reuse Sprints as releases: rejected because one release may span Sprints and a Sprint
  may ship nothing.
- Create a local version model now: rejected because no immediate invariant requires it
  and OCA has an installable candidate.

## Consequences

Release management remains intentionally unavailable until its workflow, numbering,
permissions, and upgrade path are tested. Future work must define what may change after
a release is published and how release notes relate to Knowledge.

## Open Questions

- Does `project_version` meet required project/task relationships without invasive
  overrides?
- Are versions global, project-scoped, or both?
- What lifecycle and immutability rules apply after publication?

## Evidence

- [OCA `project_version` 19.0 manifest][3]

## Sources

[3] https://raw.githubusercontent.com/OCA/project/19.0/project_version/__manifest__.py
