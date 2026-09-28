# ADR-010: Advanced Agile UI Contract

## Status

Accepted for Milestone 5 skeleton; implementation of the planning board is deferred to its dependent delivery card.

## Context

`project_agile` and `project_scrum` already own Agile configuration, task keys,
item-type eligibility, project/company validation, Sprint lifecycle, task-to-
Sprint assignment, and immutable scope facts. `project_scrum_analytics` owns
historical replay. A planning UI must compose that truth without recreating a
Jira-like backend or changing ordinary Odoo Project behavior.

The deployed fixture is Odoo Community 19.0 image
`odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c`.
The exact 19.0 web source was inspected for manifest asset declarations,
`web.assets_unit_tests`, `@odoo/hoot`, `@web/core/registry`, and the registry
API. The skeleton therefore uses only the standard manifest asset extension
point. A later client action, when there is actual UI to render, must register
through `registry.category("actions")`; it must not patch a global Project
Kanban view or use framework-private registries.

## Decision

### Addon and dependency boundary

`project_agile_ui` is an optional LGPL-3 addon with exactly one dependency:
`project_scrum`. It has no models, ACLs, controllers, menu entries, server
actions, global view inheritance, or backend assets in this milestone. Its only
asset is a native Odoo 19 `web.assets_unit_tests` Hoot fixture. Consequently
`project_agile`, `project_scrum`, and ordinary Project remain independently
installable and their existing standard views/actions remain the only user
interface until the read-only board lands.

No Git indicators. No Task-document controls or dependency on unmerged
`document_page_project_task` exists, and no duplicated backend business rules are in
this addon or its contract.

### Later read-only user journeys

1. A Project user opens a project-scoped **Sprint Planning** client action from
   an additive Agile entry point. They see visible draft/active Sprints and the
   eligible unscheduled Product Backlog for that one Agile project.
2. They can open the existing native Sprint or Task form from an item. The
   standard Product Backlog and Sprint Backlog actions remain an equivalent
   fallback for every read path.
3. A Project manager sees the same read-only workspace. Mutating assignment,
   ordering, or lifecycle controls are absent from the first board card; later
   mutation work must use existing validated server actions rather than client
   writes.
4. A user without Project/Sprint access receives the normal Odoo access failure,
   not a partial or existence-revealing response. A non-Agile, archived, or
   unavailable project uses its standard Project views; it does not receive the
   planning action.

### Data and authority contract for the later board

The later implementation adds one narrow, current-user service on a named
Agile/Scrum model, for example `project.agile.planning.get_snapshot`. It accepts
only `project_id`, a server-validated opaque/typed backlog cursor, and bounded
limits. It must reject booleans/non-integers, missing records, non-Agile
projects, unavailable companies, and records failing ACL or record-rule read
checks before it constructs any payload. It performs no `sudo()`, accepts no
caller-selected model/method/fields/company/team, and never accepts context as
authority.

The response contains only the selected project, up to 20 visible draft/active
Sprints, and the first/backlog cursor page of up to 50 eligible unscheduled
work items. Task data is limited to id, display name, Agile key, item type,
story points, parent/Epic display context when the existing `parent_id` allows
it, and native-form navigation identity. Sprint data is limited to id, name,
team display name, state, goal, current assigned-point total, and immutable
committed-point total. Current and committed totals must derive respectively
from authoritative task assignment and `committed` scope events; the UI must not
recompute lifecycle/history semantics.

The server scopes every domain by project, current available companies,
Agile enablement, Sprint eligibility, and active/non-template task boundaries.
It uses current-user ORM searches. Its budget is one authorized project lookup,
one bounded Sprint read, one grouped current-task aggregate, one grouped
committed-event aggregate, and one bounded backlog query, plus at most one
parent-name batch read. No loop may query per Sprint or per task. The contract
is a maximum of six logical ORM reads per first page and must be protected with
a query-count regression test when implemented.

### Component boundary and client behavior

The future action owns only orchestration, request cancellation/sequence
protection, and rendering. It has a container with `SprintList`, `SprintCard`,
`BacklogList`, and `BacklogItem` presentation components. Components receive
narrow immutable props; only the action service handles Odoo navigation. The
client must ignore an older response when the project, cursor, or component
lifecycle has changed. Cached data is labelled stale until refreshed and is
never used to authorize a link or mutation.

The desktop layout has labelled **Sprints** and **Product Backlog** regions.
At a narrow breakpoint it becomes a single column, Sprints first, without
horizontal drag surfaces. Controls use semantic buttons/links, visible focus,
logical heading order, and announced loading/error changes (`aria-busy` and a
polite status region). Keyboard operation relies on normal Tab/Shift+Tab and
Enter/Space activation; no single-key shortcuts or pointer-only interaction are
introduced. Drag/drop is intentionally absent from the read-only card.

Loading uses non-interactive skeletons. Empty has distinct Sprint and Backlog
messages with native-action recovery links. Error preserves already-rendered
stale content only when labelled as stale and offers retry. No-access and
unavailable project states reveal no hidden metadata. Closed Sprint state is
shown only through explicit later filtering; standard list/form fallback remains
available.

### Frontend verification strategy

Odoo 19 uses Hoot in `web.assets_unit_tests`; the skeleton provides a discoverable
`*.test.js` test rather than a parallel npm, Jest, or QUnit harness. The fixture
is installed with the addon and exercised by Odoo's native frontend test bundle.
The board card must add Hoot tests for rendering, loading/empty/error/stale
transitions, navigation, responsive semantics, and keyboard focus. It must add
Python tests for authorized snapshot scope, no-access, multi-company isolation,
multiple active-team Sprints, cursor bounds, and query budget. A native Odoo
tour is required only once the browser flow has meaningful server/client
integration; it must cover the standard-view fallback and never automate writes
on the read-only card.

## Alternatives considered

- Extend `project` Kanban globally: rejected because Agile is opt-in and
  ordinary Project behavior must remain unchanged.
- Put a generic `search_read` RPC in the browser: rejected because it leaks
  authority and duplicates domain/lifecycle policy in the client.
- Depend on the OCA Document Page bridge: rejected because it is unmerged and
  Task-document behavior is outside the planning contract.
- Add a bespoke JavaScript test runner: rejected because Odoo 19 already owns
  the asset and Hoot test mechanism.

## Consequences

The skeleton delivers a validated installation and frontend discovery seam but
no planning board, drag/drop, writes, Git integration, or document controls.
Future cards have one explicit service boundary, bounded payload/query rules,
and a browser-test route without guessing framework APIs.
