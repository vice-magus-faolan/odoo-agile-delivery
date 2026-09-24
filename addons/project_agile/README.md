# Agile Project Core

`project_agile` provides the opt-in Agile domain foundation for Odoo 19 Project.
It depends only on `project`; it extends `project.project` and `project.task`
rather than creating a parallel work-item model.

## Domain behavior

- Agile is enabled per project and requires a globally unique uppercase Agile
  key such as `ENG`.
- Agile task keys are generated through a project-local native `ir.sequence`,
  remain immutable, and cannot be moved between projects after assignment.
- Configurable `project.agile.item.type` records define the one canonical
  allowed-child relationship. The native `parent_id` and `child_ids` remain
  authoritative, with Agile hierarchy and project-isolation checks at the ORM
  layer.
- Story points support only `none` and `fibonacci` estimation methods in this
  milestone. Acceptance criteria and explicit backlog sequence are task fields.
- Project managers administer item types; Project users have read-only access
  to those configuration records and retain ordinary task permissions.

Scrum lifecycle, analytics, Knowledge, Git integrations, custom OWL interfaces,
and Jira import remain separate future concerns. The reviewed domain contract is
in `docs/project_agile-design.md`; key and hierarchy decisions are recorded in
`docs/adrs/001-work-item-key-generation.md` and
`docs/adrs/002-configurable-item-type-hierarchy.md`.
