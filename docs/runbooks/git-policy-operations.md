# Git workflow policy operations

## Before enabling Task changes

The optional LGPL-3 `project_agile_git_automation` addon changes only an eligible Task's
stage through normal Odoo ORM. It does not set Done, reopen work, assign Sprints, change
estimates or configure follower/message actions. Ordinary native tracking,
notifications, timestamps, durations and nonterminal-state recomputation still occur.
Rating, email-template and SMS-template target stages are refused. Git ingress and
normalization remain observations, not Task writes.

An authorized administrator must grant **Git Policy Manager** to the owner and a
different approver. Installation assigns nobody and enables no rules. Project
administrator access alone is insufficient. Use a least-privileged active internal
execution user, not uid 1 or a portal account. All three need current company and
concrete Project/Task access. Visible System Administrators may emergency-disable, not
activate merely by virtue of that role.

Before live Apply mode, take a consistent database/filestore backup, test isolated
restoration and assess the installed Task extensions and notification settings. Unknown
permission profiles prevent approval; compare
[supported permissions and extensions](../git-policy-authority-profiles.md), not just
the user's model ACLs. Do not bypass refusal with sudo or context.

## Preview and approve

1. Follow the
   [addon configuration guide](../../addons/project_agile_git_automation/README.rst#configuration).
   On the Project's **Git Policy** tab choose **Enable Dry Run**. Configure the
   repository-local rule and draft revision with an exact branch, eligible source and
   target stages, execution user and optional exact check names. No check names means CI
   is not a condition, not that it passed.
2. A different Git Policy Manager selects **Approve and Activate**, acknowledges native
   side effects and confirms. Check the saved Dry Run mode, cutoff and
   owner/approver/execution user. Approval does not itself enable Task writes.
3. On the repository select **Evaluate Dry Run (20 PRs)**, or use **Preview Repository
   (20 PRs)** on its rule. Read the outcomes and reasons in the resulting decisions;
   **Project > Configuration > Git Policy Dry Runs** lists history. The button examines
   only the first page. The [dry-run guide](../git-policy-dry-run.md) describes bounded
   pagination and exact evidence requirements. Exercise synthetic post-cutoff events in
   staging before considering live changes.
4. Review those decisions and obtain the required operational approval before choosing
   **Select Apply Mode**. This revokes earlier approvals; previews cannot be executed.
   Create a **New Revision** and have a different Git Policy Manager approve it with a
   new cutoff. Only eligible merges and original authenticated receipts strictly later
   than that cutoff may run. Old merges are not backfilled.

The Project shows enabled/mode controls and **View Attempts**. Configuration menus
include **Git Policy Attempts**, **Git Policy Consumed Effects** and **Git Policy
Discovery**. A rule's Disabled, Dry Run or Active status reports saved controls, not a
promise that a particular Task is currently eligible. Lists, counts, reads and exports
still require current Project, Task and company permissions.

## Diagnose an attempt

Use **View Attempts** for state, reason, processing count, next retry and lease expiry.
Events retain the initiating actor where available; older rows may have no actor.
**Consumed Effects** identifies the approved execution user and the historical
before/after stage, native state and time. Policy diagnostics contain no provider
payload, Task description, arbitrary exception text or secret. Use the
[Git facts runbook](github-git-facts-operations.md) for ingress/payload recovery.

- **Waiting:** a required exact-head check is missing or pending. Waiting uses the same
  limit of five processing tries as transient failures, not a separate 24-hour wait.
  After five claims, the next due scan records `failed/attempt_limit`; a late successful
  check does not reopen it. Several provider checks with the same required name remain
  ambiguous, even if one succeeds. Missing update times, ambiguous ordering, another
  head/repository or invalid timestamps also prevent success. Do not invent dates.
- **Retryable / transient failure:** correct the operational cause. A Git Policy Manager
  with access to the attempt and write access to its rule may choose **Retry Transient
  Failure**. It requeues the same eligible unchanged candidate, without replacing its
  Task, evidence or execution user, or resetting its five tries. The scheduler checks
  everything again; there is no public apply-now action.
- **Processing:** the private lease expires after five minutes. Let the native worker
  recover an expired committed lease; do not copy tokens or edit it. An uncommitted
  failed process rolls back instead.
- **Failed, Rejected, Expired, Revoked, No Op or Applied:** terminal. Discovery,
  reprocessing and new approvals do not reopen that attempt. A consumed effect prevents
  another transition for the same repository, PR and immutable Task key, even after a
  manual move back or a different target, revision or head. A new PR is the normal
  future trigger. Do not reset counters or delete consumed history.

Each batch handles at most 20 processing claims with a complete item savepoint before
native scheduler progress commits. Retry delay starts at 60 seconds and doubles, with a
configured 3600-second cap. Five claims exhaust the attempt before that cap becomes an
ordinary retry wait; waiting and transient faults share the budget. Actual waits also
depend on scheduler service. A five-minute lease is not an execution deadline or
permission grant. Database serialization/deadlock recovery requires a fresh whole
transaction, not a partial retry on an old snapshot.

## Discovery capacity and late evidence

One due repository cursor is visited per cron invocation and examines one PR per visit.
Expired history still uses visits. A repository with 40 older PRs before an eligible new
PR needs 41 visits to reach it. Inactive repositories can still consume cursor visits.
Bounded pages reject overflow rather than choosing a partial winner. Cursor movement,
duplicate receipts and retries do not refresh source timestamps; candidates expire 24
hours after merge.

Before relying on live Apply mode, measure the largest credible scheduler service gap
`C`, retained repository cursor count `R`, eligible merge age `A`, and the number `H` of
rows ahead of it in the ascending-ID scan. With regular fair service, allow
`(H + 1) * R * C`, plus a wrap visit if the cursor has passed that merge. Include
ingress delay, CI readiness, attempt service and a safety margin; the total including
`A` must remain below 24 hours. This is deployment planning, not a server-enforced
capacity guarantee. If no credible bound/margin exists, keep facts-only or Dry Run mode.
Monitor Discovery progress and expired reasons; never backfill by changing cutoffs or
timestamps.

With one cursor and a measured five-minute service gap, 40 rows ahead alone take 205
minutes. Additional repositories and service gaps increase latency. The platform's
five-minute warning is not an upper bound on scheduler delay. No production throughput
or service bound follows from disposable verification.

For `invalid_provenance`, check whether a genuinely later eligible delivery has current
repository/provider/key/Task association evidence. A permanent Task link alone is
insufficient; old Task-less association decisions are not backfilled. Reprocessing
retains the original receipt, cutoff and immutable audit, so cannot manufacture missing
historical proof. Do not edit old audits or relax validation.

## Stop, restore and retain history

Choose **Emergency Disable** on the Project or **Disable Rule**. Verify saved disabled
controls and revoked approvals, not only that the dialog closed. Once disable commits,
later pending effects cannot settle; an effect committed first remains historical.
Stopping the cron alone is not the kill switch. Restoring permissions or configuration
does not revive revoked approvals: create and approve a new revision.

Disable does not undo committed Task changes, queued notifications or external messages.
Make any necessary stage correction as an ordinary authorized Task edit without
overwriting later manual work. Transaction rollback cannot retract a sent mail or SMS;
excluded template stages and installed-extension review matter.

Before rollback, update or uninstall, disable policies and preserve a consistent backup
plus approval, revocation, attempt and consumed-effect history with exact
source/image/addon versions. Test the migration/restore path in isolation. Uninstall
removes policy history and is not archival. Restoring a backup without **Consumed
Effects** can move the same tasks twice. Keep policies disabled while reconciling
external observations and Task state, then approve a new revision with a cutoff
excluding old observations. Never restore one policy table independently or enable an
old restored approval automatically.

Consumed effects and used approval/revocation history remain for the repository's
lifetime. Ordinary ORM cannot rewrite/delete immutable decisions, observations or
events. Do not delete/recreate/repurpose a repository to escape its identity. There is
no policy purge API or job; a future archival design must preserve idempotency.
Current-authority exports are not a backup of inaccessible history. Delivery-payload
purge does not remove consumed policy effects. Trusted database administration remains
outside the application's immutability guarantee.

## Hosting and compatibility

Odoo.sh is the primary expected target, portable to self-hosted Odoo. Runtime needs
native ORM/PostgreSQL and `ir.cron`, not `queue_job`, an external daemon, provider
SDK/API, shell executable or writable addon tree. Verification uses
Docker/browser/subprocess tools; these are not runtime dependencies. The
[apply boundary](../git-policy-apply-boundary.md) describes native inheritance,
transactional safeguards and exercised verification; the actual Odoo build appears in
the verify log. Community tests do not prove Enterprise, Odoo.sh or arbitrary
Task-extension behavior, especially irreversible external effects.

The official
[Odoo.sh technical FAQ](https://www.odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html)
says scheduled actions are best effort and must not be expected more often than every
five minutes. The configured one-minute interval is not a one-minute SLA; backlog and
waiting limits can prevent otherwise eligible work from running.

Odoo.sh
[staging branches](https://www.odoo.com/documentation/19.0/administration/odoo_sh/getting_started/branches.html)
are neutralized: scheduled actions are disabled and outgoing mail intercepted. Database
copies can retain Project enable flags and approvals. Explicitly disable and revoke them
before experiments; use fresh synthetic approvals/cutoffs and trigger/re-enable only the
intended synthetic scheduled work. Less-active databases may run cron less often. Local
Compose checks do not establish platform scheduling, mail neutralization or a production
deployment result.
