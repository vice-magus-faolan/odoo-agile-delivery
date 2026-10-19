As a Git Policy Manager, open **Project > Tasks > Git Repositories**, select
the repository and choose **Evaluate Dry Run (20 PRs)**, or choose **Preview
Repository (20 PRs)** on a rule. Inspect the resulting decisions, their outcomes
and reasons. **Project > Configuration > Git Policy Dry Runs** lists history.
The button examines only the first page, not every PR; the
[dry-run guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/git-policy-dry-run.md)
describes pagination and exact evidence requirements.

For a meaningful preview, use an eligible merged PR on the configured branch
with task keys linked by the ingress adapter. Both merge and original receipt
must be later than the approval cutoff, with fresh source timestamps and any
required successful checks on the exact PR head. Multiple same-name check
identities are ambiguous and fail closed. After a matching check arrives,
explicitly evaluate again to obtain a new decision; a preview never reserves or
authorizes an effect.

Live application requires separate operator approval and dry-run review. Choosing
**Select Apply Mode** revokes existing approval: create a **New Revision** and
obtain distinct-person approval with a fresh cutoff. Earlier merges cannot be
backfilled. Native stage writes can generate tracking messages and notifications,
change timestamps and durations, and recompute nonterminal state. They do not
set native Done state. Odoo.sh scheduling is best effort, not a one-minute SLA;
backlog and retry limits can prevent otherwise eligible work from executing.

Use **View Attempts** on the Project for state, reason and retry diagnostics.
**Retry Transient Failure** only requeues an eligible unchanged transient
attempt, without resetting its five-claim budget. Terminal attempts cannot be
revived. If authority or configuration is wrong, choose **Emergency Disable**
on the Project or **Disable Rule**, correct the cause and obtain a fresh
successor approval. Restoring old access does not restore revoked approval.
Disable stops future work; it does not undo committed task changes or queued
notifications.

Before update, rollback or uninstall, disable policies and preserve database and
filestore backups plus approval, attempt and consumed-effect history. Uninstall
deletes policy history; reinstall does not restore approvals. Losing consumed
markers destroys duplicate-effect protection, so never enable an old restored
activation automatically. Follow the
[operations runbook](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/runbooks/git-policy-operations.md)
for recovery, history retention and Odoo.sh staging precautions, and the
[apply boundary](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/git-policy-apply-boundary.md)
for compatibility and native side effects.
