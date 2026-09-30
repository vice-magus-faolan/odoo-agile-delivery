# Agile Git Workflow Policy Configuration

Optional LGPL-3, Odoo 19 Community-compatible private-suite addon depending
only on `project_agile_git`. It is not OCA-conformant tooling and does not require
GitHub, Scrum, queue_job, provider APIs, or an external daemon.

The accepted Milestone 7 contract is [ADR-012](../../docs/adrs/012-git-workflow-policy-contract.md).
The configuration slice supplies finite project/repository rules, immutable
approved revisions, distinct author/approver activation and terminal revocation
epochs. Projects default disabled/dry-run; installation seeds no rule or Git
Policy Manager capability member. Selectors permit only merged PR, exact branch,
1–20 eligible source stages, one eligible target stage and 0–20 named checks.
Activation validates an explicit active internal non-superuser execution user
with actual concrete Task write authority and required company membership.
There is no evaluator, scheduler or policy-initiated Task mutation in this slice.
Jimmy's approved remediation adds a bounded revoke-only native Task observer;
it preserves normal create/write/unlink behavior and adds no concurrency field.
Live apply remains separately operator-gated.

Read the [configuration and recovery guide](../../docs/git-policy-configuration.md)
for capability assignment, two-person acknowledgment, fresh successors/cutoffs,
emergency disable and native side effects. Scope/security/stage/identity changes
and Project or Task unfollow invalidate existing approval, including when access
is restored before validation. Native/custom Project visibility is checked live
on read/search/count/group/export surfaces, not cached as a list of visible IDs.
The [bounded authority profile](../../docs/git-policy-authority-profiles.md)
requires exact native definitions/dependencies and permits only literal direct
Task name/active custom access rules. Unknown profiles refuse activation.
Native authority-input edits and their restoration require fresh approval, even
when current access did not decrease; conservative invalidation is intentional.

The retained synthetic audit fixture remains append-only and dry-run only.
Fixture receipts are not authenticated observations, evaluation decisions or
consumed apply markers.

Project users can read visible receipts; nobody has create/write/delete ACLs.
The ORM rejects non-superuser authors even if another addon grants an ACL.
Trusted internal fixture setup may create a row, but even superuser cannot
write/unlink one through the model. Reasons are a finite selection, not provider
text or exceptions. No payload, secret, or task description is stored.

Run `env -u COMPOSE_PROJECT_NAME ./scripts/verify` for independent optional
installation first, then the seven-module clean install, targeted upgrade, and
dependency-safe uninstall/reinstall, including imported Odoo fixture tests.
Existing Git observations stay observation-only with this addon installed.
Production policy activation remains a separate future operator-approved effect.
