# ADR-014: Mixed-work item types and native stages

## Decision

Item types are global. `uses_story_points` defaults true; Configuration and Data import
default false. Hour-based work uses native `allocated_hours`. Existing point values are
retained (never converted to hours), hidden on hour-based work and excluded from point
validation and current planning totals. Effective points are zero for hour-based work;
existing Sprint history stays frozen. Task type changes in active Sprints emit native
reestimate events. Shared estimation-policy edits are refused while that type has active
Sprint work: reclassify those tasks explicitly first. Switching back to points validates
the retained value.

An empty native stage `agile_item_type_ids` is unrestricted. For typed Agile work,
server constraints reject explicit incompatible stages, including drag/import/RPC. Type
changes preserve a compatible stage, otherwise select by native `sequence, id` among
accessible stages belonging to the Project (including folded stages). If none exists the
stage becomes unset, like native Project without stages; administrators must add a
compatible stage before board placement. Unset is not an incompatible stage.
Multi-record writes and creates use a savepoint, so rejection leaves no partial
placement. Stage policy edits reject invalidating existing work, including archived
work. Non-Agile and untyped tasks keep native behavior.

New Agile Projects use active seeded Task unless an explicit default (including none) is
supplied. Omitted task type inherits the active Project default, including native
context-only quick creation. Explicit task types or explicit none are preserved;
archived defaults are not substituted silently. Existing Projects are not backfilled.
New seed XML IDs are noupdate, preserving administrator changes on later updates. Scrum
eligibility remains in the optional Scrum addon. Its versioned post-upgrade migration
initializes eligibility for the two newly introduced BA seeds: core data loads before
the already-installed Scrum extension, so its default alone does not initialize those
existing database columns. Later same-version updates preserve administrator choices.

## Native kanban contract

Odoo19
[project.task](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/addons/project/models/project_task.py)
uses `_read_group_stage_ids(stages, domain)` for stage expansion. It unions existing
groups with Project stages only with `default_project_id`, `project_kanban`, and no
`subtask_action`; global boards otherwise expand only actual groups. `_compute_stage_id`
maintains Project membership and `stage_find` orders by `sequence, id`. Native `create`
supplies the Project-only default stage before ORM computation, so Agile
creation/default-get must select the compatible stage before delegating; a compute
override alone does not cover quick creation.

Extend these hooks, not the OWL renderer. On an Agile Project board, or an explicitly
Agile-only backlog, positive item-type filters (`=`/`in`) and the Points work / Hours
work filters narrow expanded stages to unrestricted stages plus the union applicable to
selected types. A mixed selection shows columns for either type, not their intersection.
Empty compatible Project columns remain visible under native expansion. No filter, a
domain allowing untyped work, unsupported/negated type expressions, and
non-Agile/mixed-native boards retain native expansion conservatively. Task filtering
always remains the original native search domain; column narrowing never rewrites it.
Stage configuration and task form domains guide selection but do not enforce policy. The
native
[web grouping path](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/addons/web/models/models.py)
uses `read_group_expand` and passes normalized domains (including singleton `in`, not
only equality) to the hook. Tests exercise that actual RPC path and rendered filter
changes, not just direct hook calls.

## Verification

Native non-admin tests cover mixed estimation, retained values, create/write/type
changes and batch rejection. A native HttpCase/tour checks single and mixed type filters
against actual rendered kanban columns. Existing hosted verification discovers these
alongside populated-update seed/default checks. No custom board or core copy.
