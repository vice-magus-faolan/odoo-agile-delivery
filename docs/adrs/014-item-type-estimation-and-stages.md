# ADR-014: Mixed-work item types and native stages

## Estimation

Item types are shared across Projects. Configuration and Data import use native
allocated hours; other seeded types use story points. The Project estimation method
validates only point-based work. Switching to hours keeps the old points but excludes
them from current planning totals. Switching back validates the retained estimate. Task
type changes in active Sprints record reestimate events without rewriting history.
Change those tasks individually before editing their shared estimation policy.

Enabling Agile defaults a missing Project item type to active Task, unless the caller
explicitly chooses another type or none. New tasks inherit an active Project default;
existing tasks and archived choices are not silently reclassified. Seed customizations
survive updates. Core post-migration recomputes stored effective points; optional Scrum
initializes Sprint eligibility for the new Configuration and Data import seeds.

## Stages and boards

An empty stage item-type selection allows all types. Typed Agile tasks cannot be placed
in a stage restricted to other types. Changing a task type keeps a compatible stage,
otherwise chooses the first compatible Project stage by sequence and ID. Without one,
the task has no stage. Stage policy edits cannot invalidate existing or archived work.
Non-Agile and untyped tasks remain unrestricted.

Extend Odoo 19
[Project hooks](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/addons/project/models/project_task.py),
not the kanban renderer. Select compatible defaults before native create supplies its
Project-only stage. Use `_read_group_stage_ids` for columns: a type filter shows its
stages plus unrestricted stages, including empty columns. Mixed filters show the union,
so either type can use the board. With no type filter, untyped work or a domain that
cannot safely narrow columns, keep native columns. Never rewrite the task search.
