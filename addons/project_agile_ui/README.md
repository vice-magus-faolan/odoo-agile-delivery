# Agile Planning UI

`project_agile_ui` is an optional Odoo 19 Sprint Planning workspace. It depends only on
`project_scrum`; ordinary Project, `project_agile`, and `project_scrum` remain usable
when this addon is absent.

## Authoritative planning board

An active Agile project's stat button opens an additive client action. It shows only the
current caller's visible draft/active Sprints and a bounded page of the same project's
eligible unscheduled Product Backlog work. The board renders:

- Sprint team, lifecycle state, goal, authoritative current points, and committed points
  derived from immutable `committed` scope events.
- Stable Agile key, item type, story points, and available parent context for each
  Product Backlog item.
- Native Sprint and Task form navigation, plus project-scoped standard Sprints and
  Product Backlog list fallbacks.

The snapshot service accepts only a project ID and a validated typed backlog cursor. It
always uses the caller's ORM access rules and available companies; it does not use
`sudo()`, generic client-selected model methods, arbitrary fields, or client-provided
totals. The initial-page budget is one authorized project lookup, bounded
Sprint/task/backlog reads, and grouped point totals; each response contains at most 20
Sprints, 100 rendered assigned items across those Sprints, and 50 Product Backlog items.
Incremental backlog requests use the server-returned cursor only. Cursors include a
server-maintained backlog revision; a planning mutation invalidates older cursors and
the client reloads page one instead of concatenating an incoherent page. Optimistic
versions are namespaced separately for Tasks and Sprints, so equal numeric IDs cannot
overwrite one another.

The board sends assignment, return, and reorder intents only to the current-user
`apply_agile_planning_change` boundary. The server resolves records, access,
project/company scope, eligibility, lifecycle state, immutable scope-history behavior,
versions, and deterministic locked ordering. Pointer drag/drop is a convenience layer
over those intents: it never carries authority or totals. Buttons for assignment,
return, and moving backlog items remain available for keyboard and non-pointer
operation, as do standard Odoo list/form fallbacks. Mutation payloads are capped at 20
tasks. Reorder locks only the moved row and its immediate ordering neighbors, writes
only the moved row, and uses a neighboring integer slot when existing records share a
sequence value. Rejected or stale changes reload the snapshot and display recovery
guidance. An incremental load failure retains its cursor so Retry requests the same page
rather than silently replacing the already-rendered backlog with page one. Unavailable
access, permanent project rejection, retryable transport failure, and rejected mutations
remain separate announced states.

## User-facing recovery and accessibility

The workspace has labelled Sprints and Product Backlog regions, normal buttons and links
for keyboard navigation, a polite status region, `aria-busy` loading state, distinct
empty messages, stale-data labelling after failed refreshes, and a single-column mobile
layout. Planning controls have an explicit focus-visible outline and respect
reduced-motion preferences. Drag/drop is optional: assignment, return, and backlog
movement have button controls, and edge moves are no-ops rather than unnecessary
mutations. The standard Odoo list/form actions remain the recovery path for every
essential journey.

## Verification

The module's Python tests cover current-user scope, no access, current-company
isolation, inactive work, multiple active teams, authoritative totals, bounded cursor
pagination, project-scoped navigation, multi-record assignment, rollback-safe rejection,
retry, stale ordering, Sprint lifecycle, and scope history. Frontend tests use Odoo 19's
native Hoot bundle declared in `web.assets_unit_tests`; no separate npm, Jest, or QUnit
runner is introduced. They cover native control activation, recovery after rejected
mutations, unauthorized/retryable failure distinction, stale refresh, and failed-page
cursor retention. Browser-harness availability is an environment prerequisite; if the
Odoo HttpCase browser route is unavailable, do not treat static checks as browser proof.
`./scripts/verify` clean-installs, upgrades, and uninstalls/reinstalls the optional
addon alongside the existing Community modules.

The accepted boundary is [ADR-010](../../docs/adrs/010-advanced-agile-ui-contract.md).
