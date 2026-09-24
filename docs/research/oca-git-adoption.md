# OCA Git Integration Research Note

## Status

Research snapshot, 2026-09-24. It informs ADR-007; it is not an adoption approval.

## Findings

OCA Project PR #1792 is an open draft titled for 17.0, with proposed `project_git`, `project_github`, and `project_gitlab` addons.[2] The OCA Project 19.0 branch lists related Project addons but not those three connector directories.[1] The proposal separates generic Git handling from provider bridges and includes branch, commit, pull-request, and event behavior; pull requests carry a normalized CI-status selection and a uniqueness constraint over provider/project/request identifiers.[5][6]

The proposal's matching accepts a Jira-style key found in a task name and database-id forms such as `taskid#`; those mutable or database-oriented references are not the immutable, project-prefixed `agile_key` required here.[2][8] Its controller/provider shape is useful design evidence, but a future architecture still needs repository-scoped credentials, a persisted delivery ledger, delivery-id idempotency, queue failure visibility, and explicit project-scoped association.

OCA `project_version` is an installable 19.0 module depending on `project`; it is relevant to release evaluation but not a reason to add a release dependency now.[3] The 19.0 `version-control-platform` branch is scaffolding without an addon catalog, so it is a possible upstream destination rather than an installable foundation.[4] OCA `queue_job` has a 19.0 manifest and is the first asynchronous mechanism to evaluate before inventing a worker system.[9]

## Recommendation

Keep Milestone 1 independent. Do not fork or forward-port the draft connector and do not build a private webhook stack. When Git work is funded, begin with an upstream 19.0 design/contribution proposal that isolates provider ingestion, durable event persistence, normalized facts, Agile-key association, and opt-in automation policy. See [ADR-007](../adrs/007-oca-project-git-adoption-strategy.md) and [ADR-008](../adrs/008-git-automation-model.md).

## Open Questions

1. Which upstream repository will own generic event persistence and provider ingestion?
2. Which delivery identifiers, unique constraints, and queue identity keys prevent replay and duplicate processing?
3. How will GitHub checks and GitLab pipelines map with timestamps and out-of-order deliveries?
4. What test matrix proves authentication, secret isolation, retries, association scope, and automation safety?

## Sources

[1] https://github.com/OCA/project/tree/19.0
[2] https://api.github.com/repos/OCA/project/pulls/1792
[3] https://raw.githubusercontent.com/OCA/project/19.0/project_version/__manifest__.py
[4] https://github.com/OCA/version-control-platform/tree/19.0
[5] https://raw.githubusercontent.com/OCA/project/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_event.py
[6] https://raw.githubusercontent.com/OCA/project/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_pull_request.py
[8] https://raw.githubusercontent.com/OCA/project/19.0/project_task_code/models/project_task.py
[9] https://raw.githubusercontent.com/OCA/queue/19.0/queue_job/__manifest__.py
