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

`project.project.get_agile_planning_snapshot(project_id, cursor=False, team_id=False, milestone_id=False, *, sprint_cursor=False, task_cursor=False, team_cursor=False)`
resolves one active, non-template Agile Project as the current user with current company
and native record permissions. It rejects unavailable Projects and invalid typed
IDs/cursors without exposing hidden metadata. Context does not grant authority; there is
no caller-selected model, method, field set or company. An optional team identity is
resolved by current-user ORM within that Project/company; it narrows selection, never
grants authority. The selector pages through active teams, 100 per request plus the
selected team when it lies outside the current window.

The snapshot returns at most 20 visible Draft/Active Sprints with active teams, 100
assigned items across those Sprints and 50 Product Backlog items per page. Independent
Sprint, assigned-item and team continuation controls expose every window without
increasing those bounds. Sprint pages use state then descending ID rather than mutable
start dates; assigned items use sequence then ID and teams use ID. The client replaces
these windows and can restart each at its first page. Each Sprint carries a
caller-filtered active assigned-item count, so omitted work is explicit even when the
current page contains none of its cards. New page cursors bind Project, team, milestone,
planning revision, page kind and current anchor ID/write version. Assigned-item cursors
also bind the Sprint window. The server re-resolves the anchor under current caller
rules before deriving the keyset; invalid, unavailable or changed anchors and mismatched
scopes reject. Lookahead is one row per page, not global materialization. Cursors
describe live positions, not frozen membership: native edits outside planning may change
the visible set; refresh restarts navigation. Native Task
identity/key/type/points/parent context and form navigation remain bounded projections.
Current points and counts share one grouped query over the same active, caller-visible,
company/milestone-filtered assigned Tasks as the card pages. Committed points sum
immutable committed events for that same currently assigned Task scope through a
caller-bound Task subquery. They are not the whole historical Sprint commitment after
removals; native Sprint history retains that evidence. Totals include other pages, never
hidden or out-of-filter Tasks.

The general native Product Backlog action/search includes active, unscheduled,
non-template Agile work, excluding native Done and Canceled states, irrespective of item
type or Sprint eligibility. The Sprint queue is the Product Backlog plus Sprint
eligibility. It serves the Sprint's Product Backlog button, planning snapshot, planning
changes and planning-scoped native fallback. Project, company, caller and optional team
scope still apply. The Product Backlog field doesn't read any Scrum field, so
uninstalling Scrum doesn't break it. Ordering is sequence then ID. A cursor names
sequence, ID, Project backlog revision and the selected team, if any; a different
revision or team rejects the old cursor.

Reads use batched current-user ORM queries and grouped sums rather than per-card
queries. Fetch the fields consumed by card and version serialization together, including
Task team and Sprint identity and write timestamps, instead of implicit full-record
reads. Keep the native payload/query-budget regressions, including increased team/card
counts with empty ORM caches; representative snapshots remain bounded to ten SQL queries
on initial pages, plus at most one anchor lookup for each active new continuation (up to
thirteen queries with all three cursors), not a full-render or deployment latency SLA.
Initial budgets are preserved: counts share the existing points aggregation, and
continuation lookups validate current scope without per-card queries. Native Sprint and
planning-scoped backlog lists remain read/navigation fallbacks with the same
permissions.

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

## Context-aware keyboard work

The optional planning action registers board-lifetime commands through Odoo 19
`useCommand`, including its native hotkey registration. It does not replace the palette
or global shortcuts. Direct shortcuts are scoped to the board, without
editable-protection bypass or global registration; native hotkeys exclude IME
composition and inactive dialog contexts. The visible help exposes the same commands to
keyboard and pointer users.

Name-only quick create uses native `Dialog` and current-user Task ORM creation. The
Project resolver and team/milestone resolvers are rechecked when saving; caller defaults
are discarded before native Task defaults, key allocation and validation run. No Task is
created by opening or canceling before Save. A component-local native Dialog subclass
guards its Escape/header dismissal boundary while the create request is pending; a
native dismiss-hook return cannot veto closing. It reads live save state rather than
waiting for a render. This prevents false cancellation, not an in-flight server
rollback. Successful creation reloads the current filtered snapshot, including when the
default type is absent from the Sprint-eligible queue. A rejected save preserves the
draft; a failed post-save refresh never offers the same submitted draft as unsaved work.
Failed creation restores dismissal.

Work lookup uses native `Many2XAutocomplete` and the existing Task key-first
`name_search`, scoped to the Project, not the loaded page or Sprint. Navigation
re-resolves the selected Task as the current caller in the current Project. Active
Sprint navigation reuses the native Sprint action with current-state and optional team
narrowing instead of selecting an arbitrary Sprint. Its awaited response is discarded
after request-sequence, Project or team changes, including unmount. Cached command
availability is presentation only; it grants neither creation nor read access.

## Active Sprint stage and lane matrix

The separate `project_agile_ui.swimlanes` client action is opt-in from the Project form.
It reuses the current-user Project/team resolvers, keyset paging helper,
`Many2XAutocomplete`, native Task forms and list actions. Standard Kanban grouping alone
does not provide a stage-by-hierarchy matrix; the optional action renders one semantic
table, without a global Kanban patch or another frontend framework.

`get_agile_swimlane_snapshot` selects active non-template Tasks from caller-visible
Active Sprints with active teams in one available Agile Project/current-company scope. A
caller-bound Sprint subquery preserves Sprint record rules independently of Task
visibility. Optional team/Sprint identities are re-resolved; presentation and context
never grant authority. Card pages and the unique full-filter count use the same domain.
Each page contains at most 50 cards and therefore at most 50 lanes and 50 occupied stage
columns. The existing anchor/version cursor binds Project, team, Sprint, grouping and
planning revision; First/Next navigation replaces the window. Changing filters or
grouping restarts it. These are live positions, not a frozen history or a completeness
claim after concurrent edits.

Epic identity is the seeded Epic item type's XML ID, not its translated label or
configurable code. Each card uses its nearest caller-readable Epic, including itself.
Ancestors are fetched in batches in the same Project/company; traversal stops at
unreadable/missing ancestry. Resolution inspects the card itself plus at most 32
ancestors and retains the card under an explicit unavailable-context lane when that
bound prevents classification. No-Epic is reserved for a traversed root without an Epic.
One assigned user gives one user lane; no assignees gives Unassigned; two or more
assignees gives one Multiple-assignees lane. Full assignment cardinality comes from one
elevated `user_ids` read restricted to the already caller-authorized card window. Native
Many2many reads can filter hidden users, so caller-visible membership cannot establish
cardinality. The transaction-shared relation cache is invalidated before this read and
again afterward, avoiding both stale filtered membership and retained privileged
membership. Single-assignee names are resolved only by caller-bound user searches; an
unreadable single assignee yields Assignee unavailable, without an ID or name. Task
discovery, stages and ancestry remain caller-bound. Every card belongs to exactly one
lane and stage cell, so no projection duplicates authoritative item totals.

Lane/cell counts and their drilldowns intentionally cover only the displayed window. The
full-filter native list uses the same predicates and current caller, with at most 100
matching Sprint identities serialized across JSON; a larger scope requires selecting one
Sprint before list navigation. The board itself continues paging across the complete
scope. Empty configured stages are not added to this occupied-stage matrix. Full
per-lane historical/whole-Sprint aggregates are not inferred from a page; native Sprint
history remains unchanged. This avoids a persisted grouping index or unbounded ancestry
scan; revisit if complete cross-page lane aggregates become a product requirement.

Presentation is read-only: no stage/parent/assignee mutation RPC or drag/drop
interpretation is introduced. Native Task edits retain current authority and per-type
stage validation. The action clears old cards during every request, discards late
responses/navigation after filter changes or unmount, and exposes safe errors,
First/Next controls, semantic headers, ordinary focusable buttons and a labeled scroll
region. The existing planning snapshot/query budgets are unchanged; the separate matrix
adds bounded ancestry reads, not an extension to that snapshot's ten-query contract.
Native ORM/window/permission regressions, Hoot rendering/stale-request coverage and a
real non-admin browser tour cover this boundary through normal addon discovery.

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

## Advisory stage WIP

The optional UI addon owns Project opt-in and unique positive Project/stage limit rows.
Configuration uses native Project-administrator authority plus actual Project write
access, including direct row/default operations. Rows use the same caller-bound native
Project visibility search pattern as environment configuration, with company rules; they
grant no Task visibility. Copies do not inherit policy. Stage/type eligibility remains
ADR-014, independent of WIP.

The swimlane snapshot reuses its complete authoritative Project/team/Active-Sprint
domain and adds native `state not in [1_done, 1_canceled]` only for WIP aggregation. One
caller-bound Task `_read_group` supplies stage counts. No sudo discovery/counts,
per-card queries, page IDs, lane cardinality or privileged totals are used. Readable
configured stages linked to this Project appear in a separate summary, including
zero/off-page stages; ordinary stage columns remain occupied-page columns. Folding is
presentation, not completion. All item types in the assigned scope count; Tasks without
a stage have no applicable stage limit. Hidden stages are not serialized.

The UI labels full visible-scope open counts separately from page card/cell counts.
Overflow is `max(0, count - limit)` and equality is within limit. Refresh re-reads
policy and work; changing team/Sprint narrows scope, while paging/grouping does not.
These live reads are not an atomic capacity reservation or hidden-work aggregate.
Lowering a limit can warn immediately without changing existing work. Disabling retains
rows. Removed Project/stage links suppress stale rows until restored.

No Task mutation hooks, blocking mode, coordination locks or Sprint-history writes are
added. Native Task create/write/bulk/complete and per-type stage checks retain their
existing authority and behavior. Ordinary configuration plus a read-only projection
avoids a second workflow engine; revisit enforcement only with an explicitly different
policy and concurrency/visibility contract.

## Forward-looking Epic and release roadmap

The Project form offers **Roadmap** through the same optional UI addon. Native Project,
Task and milestone records remain authoritative. This is a read-only projection of the
plan, not historical Scrum analytics or a dependency scheduler. Opening, filtering and
paging do not change dates, Sprint membership or history. Native forms remain the
separately authorized editing boundary.

Native date semantics were inspected at
[Odoo 19 revision `8da213dc6785e097f2558dc2d648b588957786a1`](https://github.com/odoo/odoo/tree/8da213dc6785e097f2558dc2d648b588957786a1/addons/project).
Project `date_start` and `date` define its planned interval. Work uses its native
`date_deadline`; Community assignment time (`date_assign`) is not a planned start. If
the installed edition exposes a readable native `planned_date_begin` Date or Datetime
field, work can show that start and its deadline as an interval. Otherwise it shows
deadline markers. A missing deadline remains explicitly unscheduled, even when a start
is available. No date is inherited from a parent or Sprint. Immediate readable parents
identify nested work without inventing an Epic rollup schedule. Native milestone
`deadline` and `is_reached` represent release planning and reported attainment; they are
neither Sprint boundaries nor detected deployments.

Odoo.sh and Enterprise remain the deployment priority, with Community portability. The
executable baseline is Odoo 19 Community. Native Task lists and deadline calendar
support ordinary work navigation, but do not combine Project intervals, undated
hierarchies and release milestones in one read-only projection. Enterprise Gantt is an
edition-specific scheduling view, not a Community dependency. The roadmap reuses the
existing OWL client-action architecture and one semantic date table rather than adding a
Gantt engine. Conditional field detection is not Enterprise or Odoo.sh runtime
verification.

OCA `web_timeline` 19.0 was evaluated at
[`929c108a04819a40f2e5e9be2e2c40967cb7a2e9`](https://github.com/OCA/web/tree/929c108a04819a40f2e5e9be2e2c40967cb7a2e9/web_timeline):
installable version 19.0.1.0.1, Production/Stable, dependent on `web`, AGPL-3, with
bundled vis-timeline and maintained translations. Its documented create, drag and delete
interactions and separate integration/licensing obligations are unnecessary for this
first read-only view. It is evaluated, not adopted. The suite keeps its existing
dependencies and licenses.

`get_agile_roadmap_snapshot` reuses current-caller Project/team/milestone resolvers and
keyset pagination. It selects active open non-template work in one authorized Project
and current-company scope, without requiring Sprint eligibility. Optional type, team and
milestone filters narrow work; milestones retain their own Project and optional
milestone selection, independent of work type/team. Related labels are resolved by
caller-bound searches, not privileged prefetch. Hidden parent context is reported as
unavailable, never as a named ancestor. Record drilldowns recheck current access and
Project ownership.

Date windows cover 1–366 inclusive UTC days. Deadline points lie within the window;
readable native intervals overlap it. The Unscheduled selection finds work and
milestones without deadlines, regardless of window. Independent work and milestone pages
return at most 50 records plus one lookahead, with full caller-visible totals. Groups
describe only the displayed work page. Cursors bind dates, mode, filters, companies,
page kind and the current anchor version. They describe live positions, not frozen
membership; native edits may require refreshing the first pages. **All filtered work —
all dates** opens the ordinary read-only native list without a date or loaded-page
restriction. It exposes later and unscheduled work under the same filters and rules.
Native Project milestone navigation remains available.

No persistence, new scheduling state, global frontend patch or third-party framework is
added. Revisit the renderer only if an approved requirement needs interactive scheduling
or complete cross-page grouping; do not infer either from this projection.
