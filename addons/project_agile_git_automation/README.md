# Agile Git Workflow Policy and Dry Runs

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
The evaluator adds sealed normalized evidence and deterministic, informational
dry-run decisions. The apply slice adds separately scheduled durable attempts,
expiring leases, five bounded retries, immutable consumed effects and native
stage-only Task writes under the approved non-superuser identity. Dry-run rows
never authorize execution. A server-owned monotonic Task fence detects manual
away-and-back changes; native tracking is not suppressed. Read the
[apply boundary](../../docs/git-policy-apply-boundary.md) for recovery and exact
installed-source compatibility limits.
Live apply remains separately operator-gated. The [operations runbook](../../docs/runbooks/git-policy-operations.md)
documents native rule status, approval/cutoff, Project-scoped attempt navigation,
confirmed transient-only retry, immutable before/after/actor effects, retention,
backups, shutdown, rollback limits and Odoo.sh staging restrictions. Native form
tours exercise server/UI controls with non-admin synthetic users; no production
OWL widget is required. Retry never replaces a candidate or resets its budget.

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

During native removal of this addon, Odoo 19 drops policy fields and tables
before its final metadata callbacks, while the old registry remains loaded.
Revocation hooks are suspended only inside the private `_module_data_uninstall`
call that removes `project_agile_git_automation`, using execution-local state
reset on success or failure. Caller context (including `_force_unlink`) cannot
enable this exemption; other module removals and normal authority changes still
revoke approvals. Missing policy schema on a ready registry remains an error.
Uninstall destroys policy history; reinstall never restores an approval epoch.

Read the [dry-run guide](../../docs/git-policy-dry-run.md) for exact head/name/repo,
cutoff/freshness/provenance predicates, unsupported same-name reruns, bounded
pagination, fail-closed conflicts, immutable fingerprints and current Task-safe
counts/exports. A later matching check can change a waiting decision only after
explicit reevaluation. No proposal reserves an effect or authorizes execution.

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
Existing Git ingress/normalization stay observation-only with this addon installed.
Only separately enabled/approved apply epochs can cause future eligible stage writes.
Production policy activation remains a separate future operator-approved effect.
