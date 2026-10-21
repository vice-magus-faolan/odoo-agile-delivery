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

Tasks optionally reference this same team in `project_scrum`; core Agile does not depend
on Scrum. Assignment inherits the Sprint team only for unteamed work and rejects
incompatible teams through task creation, task updates, the assignment wizard and the
planning board. Returning work retains its team. Project/company compatibility is
enforced, and ownership edits cannot invalidate assigned work. A versioned ORM update
assigns existing Sprint work its owning team without rewriting scope history.

Task placement, Sprint creation and Sprint ownership changes advance a private team
membership revision through the ORM. Sprint ownership changes include both the old and
requested team; carry-over registers its target team too. Team Project changes write
that same team row. These shared writes make an older ownership snapshot conflict even
after a concurrent placement has committed. Claims alone would protect only the overlap,
not a later edit using the earlier repeatable-read snapshot.

Native nonwaiting claims raise the existing retryable concurrency error on contention;
stale row versions use native transaction retry. A fresh transaction rechecks membership
and compatibility. Coordination is team-scoped and can serialize simultaneous placement
changes for one team. Caller Task, Sprint, Project and company checks remain in force;
only the private revision write is elevated after team/Project read checks. This
revision is a conflict marker, not membership history or permission, and does not alter
Sprint scope events or require the optional planning UI.

Copying a Project or creating one from a template clears the copied tasks' source team
and Sprint, including subtasks. Copying a task into another Project also clears implicit
placement while accepting valid destination defaults. Ordinary task duplicates in the
same Project keep their team and Sprint. Original tasks and Sprint history are
unchanged.

Team membership, a configurable per-team concurrency policy and no-team Sprints are not
supplied. Carry-over targets remain compatible Draft Sprints for the same team.
