# Scrum Analytics

`project_scrum_analytics` is an additive Odoo 19 addon that derives Sprint
analytics exclusively from `project.sprint.scope.event` facts recorded by
`project_scrum`.

## Calculation contract

The public service is `env["project.scrum.analytics"].get_report(sprint_id)`.
It first enforces the caller's Sprint, Project, and available-company read
access. The service performs no elevation and never accepts caller-selected
records as authority.

Events are read once and replayed in `(event_at, id)` order. Each task replay
state is `(in_scope, done, points)`. Metrics are derived from that one state:

- Velocity: final in-scope completed story points, only for closed Sprints.
- Burndown: final in-scope unfinished story points.
- Burnup: final in-scope completed and total story points.
- Scope Change: initial committed, added, removed, and final story points.
- Commitment vs Completion: committed points, completed committed points, and
  a `completion_ratio` in the explicit `fraction` unit.

Stored Float values are summed without intermediate rounding and are rounded
once to two decimal places for presentation. Timeline entries retain event
identifiers so same-timestamp ordering is auditable. Closed Sprints use
`closed_at` as the replay boundary; later task, project, estimate, and
assignment edits therefore cannot rewrite history.

The addon deliberately adds no menus, views, or JavaScript. Reporting UX is a
separate additive concern that consumes this service boundary.
