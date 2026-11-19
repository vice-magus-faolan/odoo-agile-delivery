# ADR-005: Release / Version Model

## Status

Accepted for the delivered native milestone workflow. Richer version semantics remain
unresolved and are not implemented. This decision replaces the earlier blanket rejection
of milestone reuse; it does not introduce a release model or dependency.

## Context and decision

A release can be planned using a native Project milestone without claiming that the
milestone is an immutable published version. Retain the workflow delivered by #49: Tasks
remain native Tasks, their milestone belongs to a Project, and a Sprint remains an
independent time-box. One release can include work from several Sprints or none. The
suite adds navigation and planning presentation, not a shipping authority.

Use native milestones for the supported single-target planning/content workflow. Do not
interpret a name, task completion, Sprint closure or the milestone Reached flag as
evidence of deployment or immutable publication. No confirmed missing invariant
currently justifies another model. Jira import and richer requirements below need a
separate scoped decision, not naming parity with Jira fix versions.

## Delivered workflow and boundaries

With native Milestones enabled, Agile task lists show the milestone and retain native
search/grouping. A milestone exposes **View Tasks** in its list and **Release contents**
on its Agile form. The contents action always opens a list, even for one Task, grouped
by item type and Task state. It includes Done and scheduled work, excludes templates,
and selects only that milestone and Project. It is a live caller-visible list under
native archive and record-rule behavior, not a frozen inventory or a claim about
inaccessible work.

Optional Sprint Planning filters backlog and Sprint cards by milestone; grouping covers
loaded cards only. **Release contents** opens the native contents list, not just the
loaded cards or selected team. Planning counts/current points follow the selected
milestone and caller-visible active assigned work. Committed points use committed events
for that same currently assigned visible scope; they are not the complete historical
commitment. See [ADR-003](003-sprint-scope-history-strategy.md) and
[ADR-010](010-advanced-agile-ui-contract.md). Viewing/filtering does not rewrite Sprint
membership or immutable scope history.

Agile activation does not enable Milestones. When a Project disables them, planning
controls/badges and Sprint backlog milestone columns are hidden, and an explicit
planning milestone selection is refused. Existing Task relations are not a new release
requirement. Non-Agile Projects keep native task navigation.

Contents navigation checks milestone and Project read access; Tasks retain native
permissions. Planning resolves the current caller, allowed companies and available Agile
Project, then resolves a readable milestone in that Project with the native Milestones
group. A selected identity or context value grants no additional access. No
cross-Project/global version identity or privileged complete-content total is added.

## Scenario classification

| Scenario                         | Current support and limit                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| One fix-version target per Task  | **Supported as a planning mapping:** native `project.task.milestone_id` holds zero or one milestone. The contents list retrieves current visible membership, including Done work. A milestone name is not a validated version number.                                                                                                                                                   |
| Several fix versions on one Task | **Unsupported:** the single relation cannot retain several simultaneous targets or backport history. Do not silently choose one during migration or duplicate Tasks merely to claim parity. Whether this is required is **unresolved**.                                                                                                                                                 |
| Planned versus shipped           | **Limited:** native **Reached** and `reached_date` describe a checkpoint, alongside Task states. They do not establish release publication, deployment, approval or a planned/shipped lifecycle. The business meaning and required evidence for shipped are **unresolved**.                                                                                                             |
| Ordering and dates               | **Supported for planning:** native sequence, deadline, Reached and reached date; default order is `sequence, deadline, is_reached desc, name`. No semantic-version comparison, unique numbering, release calendar or independently retained shipment timestamp is supplied.                                                                                                             |
| Publication and corrections      | **Unsupported as a publication contract:** permitted native edits can change milestone metadata and current Task membership; Reached can be toggled and its computed date changes/clears with it. No frozen membership, release-specific correction log or immutable published revision is supplied. Required correction rules are **unresolved**.                                      |
| Release-note contents            | **Limited:** the live grouped contents list identifies visible work, not authored release notes. Optional `project_scrum_document_page` seeds an unbound **Release Notes Template** with Version, Release Date, Highlights, Features, Bug Fixes, Breaking Changes, Upgrade Notes and Known Issues. No milestone link, automatic note generation or published-note snapshot is provided. |

The current workflow satisfies release planning/navigation; it does not promise a
lossless Jira multi-fix-version migration or published release history. A manually
authored page is possible with the optional document backend, but its page history is
not an implemented milestone publication/correction workflow. Release-note relationships
deferred in ADR-006 refer to this richer integration, not the absence of milestone
contents or the existing template. Solution approval and Git facts likewise do not
supply a release lifecycle.

## Bounded next steps for genuine gaps

No new runtime slice is required to retain the delivered single-target workflow. The
confirmed capability gaps are multi-target membership and durable publication/ note
relationships; their necessity and business rules are not yet approved. Before a Jira
migration relies on them, the product owner must supply representative source records
and decide which information must survive. Unresolved scenarios must be reported for a
decision, not silently reduced to one target or marked shipped.

If multiple targets/backports are required, scope the first future slice to preserving
one Task with two Project-local version memberships and a single-target control.
Acceptance must demonstrate round-trip identity/membership preservation, usable content
navigation for both targets, inaccessible/cross-Project/company refusals, unchanged
disabled-milestone behavior and unchanged Sprint history. Decide whether targets mean
plans or shipped fixes before selecting a relationship design.

If publication is required, first agree the authorized publisher, the exact frozen
content (including archive/visibility policy), shipment evidence/date and permitted
correction rules. A finite slice must publish one defined content set, preserve it after
later Task moves/edits, and expose one explicitly authorized correction without silently
rewriting the original. Denied callers must neither publish nor learn hidden work. These
are conditional acceptance examples, not delivered guarantees.

If linked release notes are required, use one milestone and one authorized page to prove
an explicit association, current Project/page/company access and the agreed note
revision at publication/correction. Reuse the chosen document backend; do not copy its
editor/history or make it mandatory for core Agile.

Evaluate exact-version native facilities first for each approved invariant. An OCA
candidate such as `project_version` would need a pinned API, dependency, license,
upgrade and runtime assessment against that invariant before any adoption proposal. No
capability or license equivalence is asserted here. A parallel version model is an
alternative only if a demonstrated invariant cannot be met by a smaller extension.

## Evidence and maintenance

- [Native Odoo 19 milestone model](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/addons/project/models/project_milestone.py)
  and
  [views](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/addons/project/views/project_milestone_views.xml)
  define the planning fields, ordering and Reached toggle, not publication.
- [Agile contents action](../../addons/project_agile/models/project_milestone.py),
  [views](../../addons/project_agile/views/project_agile_task_views.xml) and
  [planning service](../../addons/project_agile_ui/models/project_project.py) own the
  delivered navigation, filtering and caller boundaries.
- Existing [core regressions](../../addons/project_agile/tests/test_milestones.py) and
  [native/browser planning regressions](../../addons/project_agile_ui/tests/test_milestones.py)
  cover grouped contents, Done work, native fallback, disabled milestones, filtering and
  access rejection. [Usage](../../addons/project_agile/README.rst#usage) and
  [planning usage](../../addons/project_agile_ui/README.rst#usage) describe the
  controls.
- The optional
  [template](../../addons/project_scrum_document_page/data/document_page_templates.xml)
  and
  [unbound-template regression](../../addons/project_scrum_document_page/tests/test_project_sprint_document_page.py)
  distinguish authored notes from release relationships.

Keep this semantic classification authoritative rather than duplicating a second release
specification in user guides. Revisit only with an approved missing invariant; retain
native optionality, Project/company permissions and Sprint history.
