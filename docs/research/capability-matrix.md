# Dependency Capability Matrix

## Status

Research snapshot for later phases. This matrix does not authorize a new dependency or
implementation.

| Capability              | Native / current basis                                               | OCA or ecosystem evidence                                                                              | Recommendation                                                                               |
| ----------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Task hierarchy          | Native `project.task.parent_id` / `child_ids` is the suite boundary. | Helpers are not foundational to the required hierarchy.                                                | Keep native hierarchy; do not add a dependency.                                              |
| Task dependencies       | Native Project blocking relationships are authoritative.             | No external dependency selected.                                                                       | Keep native dependencies; add semantic links only when a real invariant requires them.       |
| Agile task keys         | `project_agile` provides project-prefixed immutable keys.            | `project_task_code` exists on OCA 19.0 but uses a global company-unique sequential code.[1][8]         | Keep the reviewed `ir.sequence` strategy; no hard OCA dependency.                            |
| Release/version         | No Milestone 1 runtime model.                                        | OCA `project_version` 19.0 is installable and depends on `project`.[3]                                 | Evaluate as a future extension/contribution candidate; do not install now.                   |
| Knowledge relationships | Knowledge-first architecture; no custom wiki.                        | No selected helper is needed for the initial relationship design.                                      | Defer optional `project_agile_knowledge`; preserve templates and link conventions now.       |
| Generic Git connector   | No Milestone 1 connector.                                            | PR #1792 is an open draft for 17.0; OCA Project 19.0 does not expose its proposed Git addons.[1][2]    | Do not forward-port or fork locally; pursue upstream-first design when scheduled.            |
| Git platform foundation | No Milestone 1 connector.                                            | `version-control-platform` 19.0 is repository scaffolding rather than an installable addon catalog.[4] | Treat as a direction, not a dependency.                                                      |
| Async webhook work      | No worker is needed now.                                             | OCA `queue_job` has a 19.0 manifest and is the first async mechanism to evaluate.[9]                   | Evaluate `queue_job` before custom workers; require durable event persistence independently. |

## Evidence Notes

- This matrix preserves the read-only Git/OCA spike and current repository evidence; it
  does not claim upstream stability beyond the cited source state.
- Provider facts and workflow automation remain separate decisions; see
  [ADR-008](../adrs/008-git-automation-model.md).
- Deferred decisions remain proposed so Milestone 1 stays independent of Scrum,
  Knowledge, Git, analytics, and release modules.

## Sources

[1] https://github.com/OCA/project/tree/19.0 [2]
https://api.github.com/repos/OCA/project/pulls/1792 [3]
https://raw.githubusercontent.com/OCA/project/19.0/project_version/__manifest__.py [4]
https://github.com/OCA/version-control-platform/tree/19.0 [8]
https://raw.githubusercontent.com/OCA/project/19.0/project_task_code/models/project_task.py
[9] https://raw.githubusercontent.com/OCA/queue/19.0/queue_job/__manifest__.py
