# Agile Project Core

`project_agile` provides opt-in Agile delivery foundations for Odoo 19 Project. It
depends only on `project` and extends `project.project` and `project.task` rather than
creating a parallel work-item model.

## Domain behavior

- Agile is enabled per project and requires a globally unique uppercase Agile key such
  as `ENG`.
- Agile task keys are generated through a project-local native `ir.sequence`, remain
  immutable, and cannot be moved between projects after assignment.
- Configurable `project.agile.item.type` records define the canonical allowed-child
  relationship. Native `parent_id` and `child_ids` remain authoritative, with Agile
  hierarchy and project-isolation checks at the ORM layer.
- Story points support only `none` and `fibonacci` estimation methods in this milestone.
  Acceptance criteria and explicit backlog sequence are task fields.

## Ordinary Odoo views

Project managers opt into Agile and configure its key, default item type, and estimation
method on the standard Project form. The standard Task form, list, Kanban, and search
views expose Agile details only for Agile projects. The Product Backlog action is
restricted to Agile project tasks and orders them by `agile_backlog_sequence`; its
native list handle persists priority changes. There is no Sprint field or Scrum
lifecycle in this module.

The configuration menu seeds Epic, Feature, Story, Bug, Task, Spike, and Subtask types
with practical default hierarchy policy. Seed XML IDs are upgrade-stable and marked
`noupdate` so administrator customizations survive module upgrades. Project managers may
manage item types; Project users may read them but cannot create, edit, or delete them.

Scrum lifecycle, analytics, Knowledge, Git integrations, custom OWL interfaces, and Jira
import remain separate future concerns. The reviewed domain contract is in
`docs/project_agile-design.md`; key and hierarchy decisions are recorded in
`docs/adrs/001-work-item-key-generation.md` and
`docs/adrs/002-configurable-item-type-hierarchy.md`.
