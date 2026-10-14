# ADR-007: OCA `project_git` Adoption Strategy

## Status

Superseded in part by accepted
[ADR-011: Git facts and visibility](011-git-facts-and-visibility-contract.md) and
[ADR-012: Opt-in Git workflow policy](012-git-workflow-policy-contract.md). The original
proposal below records the earlier adoption assessment; it is not the current connector
or scheduling contract.

## Current decision

Do not install or locally forward-port the originally assessed OCA connector. The suite
now ships optional `project_agile_git` provider-neutral facts and durable delivery
records, and `project_agile_git_github` signed GitHub ingress with bounded asynchronous
normalization through native Odoo `ir.cron`. Neither becomes a dependency of Agile or
Scrum. Immutable project-scoped Agile keys remain the association boundary; provider
payloads do not grant workflow authority.

ADR-011 supersedes the future-only implementation language and async-mechanism question
in this proposal: OCA `queue_job` is **not** a required runtime dependency. Its rejected
mandatory jobrunner model is not the portable Odoo.sh-first target. Any separately
approved self-hosted adapter remains outside the current contract. This design is
portable to self-hosted Odoo and does not claim live Odoo.sh deployment evidence.

ADR-012 owns the separately optional `project_agile_git_automation` addon: approved
stage-only effects, disabled/dry-run defaults, explicit authority and bounded native
scheduling. Git receipt/normalization remains observation-only and never writes Tasks,
even when that policy addon is enabled. Installing these addons activates no production
policy or provider configuration. See the
[GitHub operations runbook](../runbooks/github-git-facts-operations.md) and
[policy operations runbook](../runbooks/git-policy-operations.md).

The earlier preference for upstream reuse informed the assessment, but its rejection of
a private webhook implementation is superseded by ADR-011's explicit private-suite
contract. The shipped implementation is Odoo-compatible, not an OCA adoption or full
OCA-conformity claim. This update changes the documentation status, not architecture.

## Original context (historical)

The proposed Git integration needed provider-neutral facts, secure webhooks, idempotency
and explicit Agile-key association. At the original assessment, OCA Project PR #1792 was
an open draft for 17.0, while the inspected 19.0 Project branch exposed related modules
but not `project_git`, `project_github` or `project_gitlab`.[1][2] The proposed generic
connector had branch, commit, pull-request and event handling, but its task matching
included mutable task names and database-id forms that did not meet this suite's
immutable `agile_key` contract.[5][6]

These are historical findings, not a fresh check of the moving upstream branch or PR.
The pinned source links below preserve the evidence used at the time; current runtime
behavior and dependency choices are governed by ADR-011/012 and the shipped manifests.

## Original proposal (superseded where noted above)

Do not install, locally forward-port or depend on the proposed connector during the
initial Agile/Scrum work. When Git work was scheduled, pursue an upstream-first Odoo 19
design/contribution with provider ingestion, a durable authenticated delivery ledger,
normalized Git facts, immutable Agile-key association and opt-in automation policy.
Evaluate OCA `queue_job` before a custom worker.

The no-forward-port and immutable-key boundaries remain useful. The future-only
implementation, private-stack rejection and required-runtime evaluation are resolved by
the current decisions above; the original text is not an instruction to introduce
`queue_job` or postpone the delivered Git addons.

## Original alternatives and consequences (historical)

- Local fork/forward-port of PR #1792: rejected because the assessed work was draft 17.0
  code and would create a competing maintenance line.
- New private webhook stack: originally rejected because it duplicated an active
  upstream design space and raised security/operability risk; later superseded by the
  bounded ADR-011 implementation contract.
- Depend on `project_task_code`: rejected because its global company-unique code was not
  the required project-prefixed immutable Agile key.[8]

The initial Agile core remained free of Git/OCA dependencies. The proposal required
later work to define repository-scoped credentials, delivery-id idempotency, event
retention, retry/failure visibility, CI mapping and cross-project association isolation.
ADR-011 now defines the delivered GitHub subset and those boundaries. `queue_job` was an
async candidate, never a substitute for a durable delivery ledger.[9]

## Original open questions and their disposition

- Upstream home (`OCA/project`, `version-control-platform` or elsewhere): remains an
  upstream contribution question, not an installation prerequisite.
- Provider delivery IDs and replay constraints: resolved for the shipped GitHub adapter
  by ADR-011's repository/delivery identity and exact replay contract.
- Explicit `ENG-142` grammar, multiple keys and project scoping: resolved by ADR-011's
  bounded immutable-key association contract.
- Out-of-order GitHub checks and GitLab pipeline normalization: GitHub ordering and
  ambiguity are defined in ADR-011; no GitLab adapter is delivered.

## Historical evidence and sources

- [Git/OCA research note](../research/oca-git-adoption.md)
- [Mission brief: Git research spike](../mission-brief.md#12-git-integration-research-spike)
- [Mission brief: webhook requirements](../mission-brief.md#16-webhook-requirements)

Moving URLs below are retained for historical provenance, not presented as newly
verified upstream status.

[1] https://github.com/OCA/project/tree/19.0 [2]
https://api.github.com/repos/OCA/project/pulls/1792 [5]
https://raw.githubusercontent.com/OCA/project/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_event.py
[6]
https://raw.githubusercontent.com/OCA/project/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_pull_request.py
[8]
https://raw.githubusercontent.com/OCA/project/19.0/project_task_code/models/project_task.py
[9] https://raw.githubusercontent.com/OCA/queue/19.0/queue_job/__manifest__.py
