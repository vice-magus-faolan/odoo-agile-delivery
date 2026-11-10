As a Git Policy Manager, open **Project > Tasks > Git Repositories**, select
the repository and choose **Evaluate Dry Run (20 PRs)**, or choose **Preview
Repository (20 PRs)** on a rule. Inspect the resulting decisions, their outcomes
and reasons. **Project > Configuration > Git Policy Dry Runs** lists history.
The button examines only the first page, not every PR; the
[dry-run guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/19.0/docs/git-policy-dry-run.md)
describes pagination and exact evidence requirements.

For a meaningful preview, use an eligible merged PR on the configured branch
with task keys linked by the ingress adapter. Both merge and original receipt
must be later than the approval cutoff, with fresh source timestamps and any
required successful checks on the exact PR head. If several provider checks have the same required name, that named check is
not treated as passed, even if one run succeeded. After a matching check arrives,
explicitly evaluate again to obtain a new decision; a preview does not move tasks or approve later task changes.

Check the dry-run decisions before enabling task changes, and obtain the required
operator approval. Choosing
**Select Apply Mode** revokes existing approval: create a **New Revision** and
obtain distinct-person approval with a fresh cutoff. Earlier merges cannot be
backfilled. Native stage writes can generate tracking messages and notifications,
change timestamps and durations, and recompute nonterminal state. They do not
set native Done state. Odoo.sh scheduling is best effort, not a one-minute SLA;
backlog and retry limits can prevent otherwise eligible work from executing.

Use **View Attempts** on the Project for state, reason and retry diagnostics.
**Retry Transient Failure** only requeues an eligible unchanged transient
attempt, without resetting the limit of five processing tries. Waiting for checks uses
those same tries. Terminal attempts cannot be
revived. If authority or configuration is wrong, choose **Emergency Disable**
on the Project or **Disable Rule**, correct the cause and create and approve a new revision. Restoring old access does not restore revoked approval.
Disable stops future work; it does not undo committed task changes or queued
notifications.

Before update, rollback or uninstall, disable policies and preserve database and
filestore backups plus approval, attempt and consumed-effect history. Uninstall
deletes policy history; reinstall does not restore approvals. Restoring a backup without **Consumed Effects** can move the same tasks twice.
Keep policies disabled while reconciling that history, then approve a new revision
with a new cutoff instead of re-enabling an old approval. Follow the
[operations runbook](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/19.0/docs/runbooks/git-policy-operations.md)
for recovery, history retention and Odoo.sh staging precautions, and the
[apply boundary](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/19.0/docs/git-policy-apply-boundary.md)
for compatibility and native side effects.
