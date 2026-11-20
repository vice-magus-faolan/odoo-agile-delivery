# ADR-005: Native milestone releases and version limits

## Status

Accepted for the delivered native milestone workflow. The richer version capabilities
listed below are deliberately unsupported. This decision replaces the earlier blanket
rejection of milestone reuse; it introduces no release model or dependency.

## Context and decision

A release can be planned using a native Project milestone without claiming that the
milestone is an immutable published version. Retain the workflow delivered by
[#49](https://github.com/vice-magus-faolan/odoo-agile-delivery/issues/49): Tasks remain
native Tasks, their milestone belongs to a Project, and a Sprint remains an independent
time-box. One release can include work from several Sprints or none. The suite adds
navigation and planning views, not evidence that a release has shipped.

Use native milestones to plan releases and browse their current contents. Do not treat a
name, Task completion, Sprint closure or the milestone **Reached** flag as evidence of
deployment or immutable publication.

The current workflow cannot hold several milestones on one Task, freeze a published
release, or link a milestone to a release-notes page. No migration has shown that it
needs any of these, so they are deliberately unsupported and no new model is planned. A
[Jira import](https://github.com/vice-magus-faolan/odoo-agile-delivery/issues/103) that
needs them must stop and report the records it cannot map, not pick one milestone or
mark work shipped.

## Delivered workflow and boundaries

With native Milestones enabled, Agile task lists show the milestone and retain native
search and grouping. A milestone exposes **View Tasks** in its list and **Release
contents** on its Agile form. The contents action always opens a list, even for one
Task, grouped by item type and Task state. It lists Tasks in every state, including Done
and Cancelled, and leaves out archived Tasks and templates. It selects only that
milestone and Project, and only Tasks the caller can read. It is a live list, not a
frozen inventory or a claim about inaccessible work.

Optional Sprint Planning filters backlog and Sprint cards by milestone; grouping covers
loaded cards only. **Release contents** opens the same grouped list as the milestone
form: every Task you can see in that milestone, not only the loaded cards or the
selected team. Sprint counts and current points include only active Tasks in that Sprint
that you can see and that match the selected milestone. Committed points sum the
commitment events of those same Tasks, so they are not the full commitment history of
the Sprint. See [ADR-003](003-sprint-scope-history-strategy.md) and
[ADR-010](010-advanced-agile-ui-contract.md). Viewing and filtering do not rewrite
Sprint membership or immutable scope history.

Agile activation does not enable Milestones. When a Project disables them, planning
controls, badges and Sprint backlog milestone columns are hidden, and an explicit
planning milestone selection is refused. Existing Task relations do not change this
behavior. Non-Agile Projects keep native task navigation.

Contents navigation checks milestone and Project read access; Tasks retain native
permissions. Planning resolves the current caller, allowed companies and available Agile
Project, then resolves a readable milestone in that Project with the native **Use
Milestones** group. A selected identity or context value grants no additional access.
Milestones remain separate for each Project, even when their names match. Counts do not
include hidden Tasks or claim to describe them.

## Scenario classification

| Scenario                         | Decision and current limit                                                                                                                                                                                                                                                                                                                                                                                                                                |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| One fix-version target per Task  | **Supported for planning:** native `project.task.milestone_id` holds zero or one milestone. The contents list retrieves current readable membership in every Task state, excluding archived Tasks and templates. A milestone name is not a validated version number.                                                                                                                                                                                      |
| Several fix versions on one Task | **Deliberately unsupported:** the single relation cannot retain several simultaneous targets or backport history. Do not silently choose one during migration or duplicate Tasks to claim parity.                                                                                                                                                                                                                                                         |
| Planned versus shipped           | **Planning supported; shipped status deliberately unsupported:** native **Reached** and `reached_date` describe a checkpoint, alongside Task states. They do not establish release publication, deployment or approval.                                                                                                                                                                                                                                   |
| Ordering and dates               | **Supported for planning:** native sequence, deadline, Reached and reached date; default order is `sequence, deadline, is_reached desc, name`. Semantic-version comparison, unique numbering, a release calendar and an independently retained shipment timestamp are deliberately unsupported.                                                                                                                                                           |
| Publication and corrections      | **Deliberately unsupported:** permitted native edits can change milestone metadata and current Task membership. Toggling Reached changes or clears its computed date. There is no frozen membership, release-specific correction log or immutable published revision.                                                                                                                                                                                     |
| Release-note contents            | **Template supported; milestone association deliberately unsupported:** the live grouped contents list identifies readable work, not authored release notes. Optional `project_scrum_document_page` seeds an unbound **Release Notes Template** with Version, Release Date, Highlights, Features, Bug Fixes, Breaking Changes, Upgrade Notes and Known Issues. Automatic note generation and a published-note snapshot are also deliberately unsupported. |

The current workflow supports release planning and navigation, not lossless migration of
several Jira fix versions per Task or published release history. The optional document
backend permits manually authored pages, but neither this ADR nor
[ADR-006](006-knowledge-relationship-model.md) implements a link between a milestone and
a release-notes page. Solution approval and Git facts likewise do not supply a release
lifecycle.

## Conditions for reconsidering unsupported capabilities

No new implementation is planned. Before proposing a change, the migration team must
provide representative source records and the maintainer must agree which information
must survive. Report unmappable records rather than silently discarding information. The
following are finite acceptance examples for a separately approved requirement, not
approved work or delivered guarantees.

If several targets or backports become required, a first slice could preserve one Task
with two version memberships in the same Project and another Task with only one. Import
and export must preserve Task identities and both memberships, with usable contents
navigation for each target. Access checks must reject unreadable targets and links
outside the permitted Project or companies. Disabled-milestone behavior and Sprint
history must remain unchanged. Agree whether targets mean plans or shipped fixes before
choosing a relationship design.

If publication becomes required, first agree who may publish, exactly which contents
must be frozen, whether archived or hidden work belongs in that record, the shipment
evidence and date, and the permitted corrections. A first slice must publish one defined
content set, preserve it after later Task moves or edits, and expose one authorized
correction without rewriting the original. Denied callers must neither publish nor learn
hidden work.

If linked release notes become required, a first slice must associate one milestone with
one authorized page, check current access to the Project, page and company, and preserve
the agreed note revision on publication and correction. Reuse the chosen document
backend; do not copy its editor or history or make it mandatory for core Agile.

Evaluate native facilities in the supported Odoo version first for any approved
requirement. An OCA candidate such as `project_version` would need a pinned API,
dependency, license, upgrade and runtime assessment before any adoption proposal. No
capability or license equivalence is asserted here. Consider another model only if a
demonstrated requirement cannot be met by a smaller extension.

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
  [native and browser planning regressions](../../addons/project_agile_ui/tests/test_milestones.py)
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
specification in user guides. Revisit only for an approved requirement; retain native
optionality, Project and company permissions, and Sprint history.
