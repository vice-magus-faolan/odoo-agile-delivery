# ADR-004: Teams and multiple active Sprints

## Status

Accepted and implemented in `project_scrum`.

## Context and decision

A Project may host several delivery teams. A global or per-Project single-active-Sprint
rule would block legitimate parallel work; unowned concurrent Sprints would make
capacity and reporting ambiguous.

The narrow `project.agile.team` model supplies a durable Sprint ownership boundary that
native Project roles do not provide. A team belongs to one Agile-enabled Project and
inherits its company. Different teams may have active Sprints in the same Project.

A native Odoo 19 `models.UniqueIndex` prevents two active Sprints with the same
`(project_id, team_id)`, including competing transactions. Draft and closed Sprints do
not reserve the slot. Activation preserves permission, state and consistency checks and
translates the index's `IntegrityError` into a business error within a savepoint,
rolling back commitment and scope evidence.

## Alternatives and consequences

One active Sprint globally couples unrelated workspaces. One per Project prevents
parallel teams. Unlimited Sprints without teams obscure ownership. The selected boundary
instead requires Project/team/company compatibility and reports which team owns each
Sprint.

Team membership, a configurable per-team concurrency policy and no-team Sprints are not
supplied by this model. Carry-over targets must be compatible Draft Sprints for the same
team; this does not establish a general cross-team transfer policy. Such changes need
their own Task ownership and scope-history decisions.
