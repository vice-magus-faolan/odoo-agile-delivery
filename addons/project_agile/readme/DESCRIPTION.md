Agile Project Core (`project_agile`) adds opt-in Agile work items to Odoo 19
Community Project. Work items remain native Project tasks (`project.task`), with
native subtasks and dependencies rather than a separate issue model.

Use it for configurable work-item types, stable task keys, Fibonacci story points,
acceptance criteria and an ordered backlog. Agile is enabled separately on each
Project; installing the addon does not enable it on existing Projects.

The addon is LGPL-3 and depends only on native `project`. For teams and Sprint
lifecycle, add [Scrum Project Foundation](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum).
Scrum, analytics, the planning board, Git and document integrations are separate
addons, not dependencies of the Agile core.
