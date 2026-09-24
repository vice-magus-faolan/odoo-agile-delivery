# ADR-004: Agile Team / Multiple Active Sprint Model

## Status

Proposed — implementation is deferred beyond Milestone 1.

## Context

One product Project can contain more than one delivery team. A global or per-project one-active-Sprint rule would prevent legitimate parallel work; unlimited concurrent Sprints without ownership would make assignment and reporting ambiguous.

## Decision

A future Scrum design will make team ownership explicit on each Sprint and enforce active-Sprint policy at the team boundary, not globally and not merely per Project. The design will first evaluate available Odoo-native project/team/role concepts; it will introduce a new team model only if no native relationship can express membership, ownership, and access needs. Multiple active Sprints are allowed for distinct teams when their configured policy permits them.

Milestone 1 adds no team or Sprint fields.

## Alternatives

- One active Sprint globally: rejected because it couples unrelated workspaces.
- One active Sprint per Project: rejected because a Project may host several teams.
- Allow arbitrary active Sprints with no team: rejected because capacity, task ownership, and reporting become unclear.

## Consequences

Future Scrum rules must validate team membership, project compatibility, task assignment, and access before activation. Reporting must identify the team that owned a Sprint. Team policy becomes a configuration and migration concern, not a hardcoded Scrum assumption.

## Open Questions

- Which native Odoo role/team relation best supplies the required ownership boundary?
- Can a task move between concurrent team Sprints, and what scope events are required?
- Is a no-team Sprint permitted for small installations?

## Evidence

- [Mission brief: Scrum is optional](../mission-brief.md#rule-6--scrum-is-optional)
- [Mission brief: team-configured active-Sprint rule](../mission-brief.md#8-sprint-lifecycle)
- [Mission brief: deferred Scrum foundation](../mission-brief.md#22-milestone-2-scrum-foundation)
