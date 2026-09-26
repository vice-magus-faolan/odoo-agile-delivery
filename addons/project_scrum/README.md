# Scrum Project Foundation

`project_scrum` is the narrow Milestone 2 Scrum domain module for Odoo 19. It
extends `project_agile` and native `project.task`. It does not introduce a
parallel work-item model, custom JavaScript, analytics, release management, or
Git or Knowledge integration.

## Scope

- An Agile team belongs to exactly one Agile-enabled Project and inherits the
  Project company.
- A Sprint belongs to exactly one Agile Project and one Agile team. Its lifecycle
  is `draft` to `active` to `closed`; lifecycle transitions are action-only at
  the ORM boundary.
- PostgreSQL and ORM constraints allow one active Sprint for a `(project, team)`
  pair, while distinct teams can run active Sprints for the same Project.
- Native `project.task` receives an optional `sprint_id`. Assignment is checked
  at the ORM layer so task, Sprint, Project, and company cannot cross boundaries.
  Ordinary non-Agile tasks remain unscheduled and otherwise behave normally.
- Starting a Sprint stores its committed task relation and appends one immutable
  `committed` scope event per task. Adding or removing a task while the Sprint is
  active appends `added` or `removed` events with observed story points, actor,
  and timestamp. Native `state` edges into `1_done` append `completed`, while
  edges out append `reopened`; repeated writes do not duplicate facts. A closed
  Sprint freezes this ledger even though native task state can still change.

## Scope-history trust boundary

`project.sprint.scope.event` is append-only for ordinary ORM users: its ACLs are
read-only and the model rejects regular create/write/unlink calls. Sprint
lifecycle code creates events as the superuser while retaining the initiating
actor in `actor_id`. Superuser use remains the explicit administrative recovery
boundary: it can correct or remove facts when required, but that action is
trusted administration rather than ordinary Scrum workflow.

## Ordinary Odoo interface

The module provides standard list, form, and search views for Agile Teams and
Sprints, lifecycle buttons on the Sprint form, a read-only scope-history page,
and a Sprint field, filter, and grouping on native Project tasks. Project
managers configure teams and manage Sprints; Project users can read Scrum
records but cannot create, modify, or delete them. No OWL component is required.

## Verification

Run the focused suite on a disposable database:

::

    docker compose up -d db
    docker compose run --rm odoo odoo --config=/etc/odoo/odoo.conf --stop-after-init \
      --without-demo=True --test-enable --database odoo_agile_scrum_test \
      --init project_scrum --test-tags /project_scrum

The repository `./scripts/verify` is the repository regression gate.
Run the focused project_scrum command above for this module on a fresh disposable
database.

The implementation follows [ADR-003](../../docs/adrs/003-sprint-scope-history-strategy.md)
and [ADR-004](../../docs/adrs/004-agile-team-multiple-active-sprints.md).

## Closing unfinished work

If unfinished tasks remain, **Close Sprint** opens a standard Odoo wizard. A
manager must move them either to the unscheduled Product Backlog or to another
Draft Sprint for the same Project, company, and Agile team. The source history
records typed `carried_to_backlog` or `carried_to_sprint` facts; the latter links
the draft target. A close is transactional, and closed Sprint assignments and
ordinary lifecycle edits are frozen. Superuser writes are the explicit recovery
boundary for exceptional administration.
