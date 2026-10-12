# Scrum Analytics

`project_scrum_analytics` is an additive Odoo 19 addon that derives Sprint analytics
exclusively from `project.sprint.scope.event` facts recorded by `project_scrum`.

## Calculation contract

The public service is `env["project.scrum.analytics"].get_report(sprint_id)`. It first
enforces the caller's Sprint, Project, and available-company read access. The service
performs no elevation and never accepts caller-selected records as authority.

Events are read once and replayed in `(event_at, id)` order. Each task replay state is
`(in_scope, done, points)`. Metrics are derived from that one state:

- Velocity: final in-scope completed story points, only for closed Sprints.
- Burndown: final in-scope unfinished story points.
- Burnup: final in-scope completed and total story points.
- Scope Change: initial committed, added, removed, and final story points.
- Commitment vs Completion: committed points, completed committed points, and a
  `completion_ratio` in the explicit `fraction` unit.

Stored Float values are summed without intermediate rounding and are rounded once to two
decimal places for presentation. Timeline entries retain event identifiers so
same-timestamp ordering is auditable. Closed Sprints use `closed_at` as the replay
boundary; later task, project, estimate, and assignment edits therefore cannot rewrite
history. Superuser recovery may correct `closed_at`; it synchronously rebuilds the
stored report and timeline from the corrected boundary, while lifecycle state remains
action-only, including for superuser.

## Native reporting UX

The addon adds a `Project > Scrum Analytics` menu for Agile Sprints only. It uses
standard Odoo list, form, pivot, graph, search, export, and drill-down surfaces; it
contains no custom JavaScript or OWL.

- The Sprint report has Velocity, Burndown, Burnup, Scope Change, and Commitment vs
  Completion measures. Story-point labels and the `fraction` completion-ratio unit are
  explicit.
- The Burndown & Burnup Timeline contains one stored point after every immutable scope
  event. Its timestamp is UTC; Odoo date-chart buckets render in the requesting user's
  timezone.
- Active Sprints are explicitly live replay. Closed Sprints with `closed_at` are marked
  trusted and remain frozen at that boundary.
- Report and timeline records are read-only projections. They inherit native Project
  visibility, enforce available-company access for list/export/grouped queries and
  direct ORM access, and authorize Sprint/Task drill-down actions before returning
  record identifiers.

Ordinary Project analytics are not overridden or replaced. No records are created for
non-Agile projects because only valid Scrum Sprints produce these additive projections.
