# ADR-010: Additive Agile planning UI

## Status

Accepted and implemented in optional `project_agile_ui`: a current-user planning board
with bounded reads and explicit assign, return and reorder actions. The initial
read-only skeleton is superseded by the delivered board described here.

## Context and dependency boundary

Agile and Scrum own keys, type eligibility, Project/company checks, Sprint lifecycle,
membership and immutable scope events; analytics owns historical calculations. The UI
composes those contracts rather than recreating a backend. It retains LGPL-3 and depends
only on `project_scrum`. Ordinary Project views and core addons remain usable without
the board. No Git indicator or Task-document backend is required.

Use the standard Odoo 19 `registry.category("actions")` client-action extension,
manifest assets, OWL and native Hoot in `web.assets_unit_tests`. Do not patch global
Project Kanban, use private registries or add a parallel JavaScript test runner.
Original web/API inspection used Community image
`odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c`; that
historical finding does not pin future verifier builds.

## Snapshot and authority

`project.project.get_agile_planning_snapshot(project_id, cursor=False, team_id=False)`
resolves one active, non-template Agile Project as the current user with current company
and native record permissions. It rejects unavailable Projects and invalid typed
IDs/cursors without exposing hidden metadata. Context does not grant authority; there is
no caller-selected model, method, field set or company. An optional team identity is
resolved by current-user ORM within that Project/company; it narrows selection, never
grants authority. The selector returns at most 100 active teams.

The snapshot returns at most 20 visible Draft/Active Sprints with active teams, 100
assigned items across those Sprints and 50 Product Backlog items per page. Native Task
identity/key/type/points/parent context and form navigation remain bounded projections.
Current points come from Task assignment; committed points come from immutable committed
events, not browser arithmetic. Totals may include work omitted from the capped item
list.

Backlog eligibility is active, unscheduled, Sprint-eligible, non-template work in that
Project/company, excluding native Done and Canceled states. Native action/search, Sprint
fallback and planning use the same extensible Task domain; the core searchable
membership field never references optional Scrum fields after uninstall. Ordering is
sequence then ID. A cursor names sequence, ID, Project backlog revision and the selected
team, if any; a different revision or team rejects the old cursor.

Reads use batched current-user ORM queries and grouped sums rather than per-card
queries. Fetch the fields consumed by card and version serialization together, including
Task team and Sprint identity and write timestamps, instead of implicit full-record
reads. Keep the native payload/query-budget regressions, including increased team/card
counts with empty ORM caches; representative snapshots remain bounded to ten SQL
queries, not a full-render or deployment latency SLA. Native Sprint and planning-scoped
backlog lists remain read/navigation fallbacks with the same permissions.

## Explicit planning changes

`project.project.apply_agile_planning_change` accepts only assign, return or reorder
with typed identities and exact expected Task/Sprint versions. It checks the whole
selected set's current access before mutation, at most 20 Tasks. Assign uses the
existing validated Scrum operation and targets Draft Sprints with active teams. Return
supports Draft/Active Sprints and preserves native scope events; closed membership is
not mutable. Reorder acts on one eligible backlog Task and a validated placement target.
No client value grants lifecycle authority.

The server validates versions, eligibility, Project/company and lifecycle in a
savepoint. A shared Project backlog-revision write conflicts with concurrent planning
changes; rejection leaves no partial placement/order change. The UI refreshes current
data after changes and instructs the user to refresh/retry a stale action instead of
silently applying it to different work. Only the private coordination-field write is
narrowly elevated; Task mutations use caller ORM. These actions do not approve
requirements, alter analytics formulas or automatically plan work from Git or documents.

## Client behavior and accessibility

The action owns request sequencing/cancellation, rendering and native navigation;
presentation components receive narrow data. Ignore stale responses after Project, team,
page or lifecycle changes. Cached content is not mutation authority. Show loading,
empty, error and stale states distinctly; retry and standard-view fallbacks do not widen
access. An unavailable Project exposes no hidden metadata.

Use labeled Sprint and Product Backlog regions, logical headings, semantic
buttons/links, visible focus and announced loading/errors. Narrow layouts stack without
mandatory horizontal dragging. Keyboard buttons provide every supported planning action;
drag/drop is an alternative, not the only control.

## Verification and consequences

Keep native Python permission/company/cursor/payload/atomic-change regressions, Hoot
rendering/loading/error/navigation/focus tests and meaningful browser journeys, with
distinct-process planning races in the existing verifier. Tests exercise the real
server/client boundary rather than only a discoverable skeleton asset. See the
[addon workflow](../../addons/project_agile_ui/README.rst) for current controls and
[contributor checks](../contributing.md) for commands.

Rejected alternatives are global Kanban replacement, generic browser `search_read` with
duplicated domain rules, a mandatory document backend, and a separate frontend test
framework. The additive board costs explicit bounded service/action contracts but keeps
native work and history authoritative. Richer provider/document controls, automatic
planning and changed backlog eligibility are not supplied by this ADR.
