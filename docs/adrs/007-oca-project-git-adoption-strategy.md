# ADR-007: OCA Git connector adoption

## Status

Superseded by [ADR-011](011-git-facts-and-visibility-contract.md) and
[ADR-012](012-git-workflow-policy-contract.md). This ADR preserves the adoption
rationale, not a pending implementation plan. The suite now supplies its Git addons and
uses native `ir.cron`, not `queue_job`.

## Examined alternative

The 2026-09-24 survey found OCA Project PR 1792 to be an open 17.0 draft proposing
`project_git`, `project_github` and `project_gitlab`; those connector directories were
absent from the surveyed 19.0 Project branch. The proposal separates generic Git facts
from providers, with branches, commits, pull requests and events. Its PR CI selection
and provider/project/request uniqueness were useful design input. This is historical
survey evidence, not current upstream status.

Exact inspected excerpts:

- [Git event model at 769d464e1fc1aff006e21f1668d47e4f13840138](https://github.com/OCA/project/blob/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_event.py)
- [Pull-request model at the same revision](https://github.com/OCA/project/blob/769d464e1fc1aff006e21f1668d47e4f13840138/project_git/models/project_git_pull_request.py)
- [OCA Project PR 1792](https://github.com/OCA/project/pull/1792)

Matching mutable Task names and database-ID forms such as `taskid#` does not meet this
suite's immutable project-prefixed Agile-key contract. `project_task_code` also supplies
a global company-unique sequence, not the same project-local key. The surveyed
`version-control-platform` 19.0 branch was scaffolding without an installable addon
catalog, so was not a dependency.

## Decision and consequences

Do not locally fork, forward-port or depend on that draft. Agile and Scrum remain
independent of Git/OCA dependencies. The maintained implementation instead separates
authenticated ingress, durable delivery identity, normalized provider-neutral facts,
explicit repository-scoped Agile-key association and opt-in workflow policy. Repository
credentials, idempotency, retention, retries, failure visibility and company/Project
isolation are mandatory boundaries, not implied by a CI field.

The original proposal to evaluate OCA `queue_job` was superseded by the deployment
constraint against external queue runners. Native bounded `ir.cron` provides the current
portable processing boundary. Provider expansion and upstream contribution remain
separate decisions; neither draft availability nor this rationale grants production
dependency or activation authority.

See
[dependency compatibility](../dependency-compatibility.md#git-adoption-and-deferred-capabilities)
for the related alternatives and [ADR-008](008-git-automation-model.md) for the
historical fact-versus-policy distinction. Current exact provenance, provider ordering,
retry and action semantics belong to ADR-011/012, not to this superseded proposal.
