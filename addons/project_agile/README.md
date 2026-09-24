# Agile Project Core

`project_agile` is the opt-in Agile domain foundation for Odoo 19 Project.

It intentionally depends only on `project`. It will extend `project.project` and
`project.task` rather than create a parallel work-item model. Scrum lifecycle,
analytics, Knowledge, Git integrations, custom OWL interfaces, and Jira import
are separate future concerns.

The initial installable skeleton contains no data files and no custom JavaScript.
The reviewed domain contract is in `docs/project_agile-design.md`; the key and
hierarchy decisions are in `docs/adrs/001-work-item-key-generation.md` and
`docs/adrs/002-configurable-item-type-hierarchy.md`.
