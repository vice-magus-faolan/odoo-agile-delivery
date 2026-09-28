# Agile Planning UI

`project_agile_ui` is an optional Odoo 19 Sprint Planning workspace. It depends
only on `project_scrum`; ordinary Project, `project_agile`, and `project_scrum`
remain usable when this addon is absent.

## Read-only planning board

An active Agile project's stat button opens an additive client action. It shows
only the current caller's visible draft/active Sprints and a bounded page of the
same project's eligible unscheduled Product Backlog work. The board renders:

- Sprint team, lifecycle state, goal, authoritative current points, and
  committed points derived from immutable `committed` scope events.
- Stable Agile key, item type, story points, and available parent context for
  each Product Backlog item.
- Native Sprint and Task form navigation, plus project-scoped standard Sprints
  and Product Backlog list fallbacks.

The snapshot service accepts only a project ID and a validated typed backlog
cursor. It always uses the caller's ORM access rules and available companies;
it does not use `sudo()`, generic client-selected model methods, arbitrary
fields, or client-provided totals. Each response contains at most 20 Sprints
and 50 Product Backlog items. Data is read-only: no drag/drop, assignment,
reordering, or Sprint lifecycle controls are included.

## User-facing recovery and accessibility

The workspace has labelled Sprints and Product Backlog regions, normal buttons
and links for keyboard navigation, a polite status region, `aria-busy` loading
state, distinct empty messages, stale-data labelling after failed refreshes,
and a single-column mobile layout. The standard Odoo list/form actions remain
the recovery path for every essential read journey.

## Verification

The module's Python tests cover current-user scope, no access, current-company
isolation, inactive work, multiple active teams, authoritative totals, bounded
cursor pagination, and project-scoped navigation. Frontend tests use Odoo 19's
native Hoot bundle declared in `web.assets_unit_tests`; no separate npm, Jest,
or QUnit runner is introduced. `./scripts/verify` clean-installs, upgrades, and
uninstalls/reinstalls the optional addon alongside the existing Community
modules.

The accepted boundary is [ADR-010](../../docs/adrs/010-advanced-agile-ui-contract.md).
