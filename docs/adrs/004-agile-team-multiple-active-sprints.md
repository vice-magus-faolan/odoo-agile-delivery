# ADR-004: Agile Team / Multiple Active Sprint Model

## Status

Accepted — implemented by the Milestone 2 project_scrum foundation.

## Context

One product Project can contain more than one delivery team. A global or
per-project one-active-Sprint rule would prevent legitimate parallel work;
unlimited concurrent Sprints without ownership would make assignment and
reporting ambiguous.

## Decision

The `project_scrum` module makes team ownership explicit on each Sprint and
enforces active-Sprint policy at the team boundary, not globally and not merely
per Project. It introduces the narrow `project.agile.team` model because native
Project roles do not provide a durable Sprint ownership boundary. A team belongs
to one Agile-enabled Project and inherits its company.

Multiple active Sprints are allowed for distinct teams in the same Project. A
partial unique index and ORM constraint reject a second active Sprint for the
same `(project_id, team_id)` pair.

## Alternatives

- One active Sprint globally: rejected because it couples unrelated workspaces.
- One active Sprint per Project: rejected because a Project may host several
  teams.
- Allow arbitrary active Sprints with no team: rejected because capacity, task
  ownership, and reporting become unclear.

## Consequences

Sprint lifecycle validates team and Project compatibility, task assignment, and
company isolation. Reporting identifies the team that owns a Sprint. Team
membership and configurable per-team concurrency policy remain deliberately out
of this narrow foundation.

## Open Questions

- Which relationship should later supply team membership and task ownership?
- Can a task move between concurrent team Sprints, and what scope events are
  required?
- Should a future policy allow a no-team Sprint for a small installation?

## Evidence

- [Mission brief: Scrum is optional](../mission-brief.md#rule-6--scrum-is-optional)
- [Mission brief: team-configured active-Sprint rule](../mission-brief.md#8-sprint-lifecycle)
- [Mission brief: Scrum foundation](../mission-brief.md#22-milestone-2-scrum-foundation)
