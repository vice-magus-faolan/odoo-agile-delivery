# Git workflow policy operations

## Scope and authority

Odoo 19 Community, optional LGPL-3 private-suite `project_agile_git_automation`. Not an
OCA-conformity claim. Its only dependency is `project_agile_git`; GitHub, Scrum,
analytics, document bridges and planning UI remain optional and independent. Fact
ingress/normalization is observation-only with policy absent, disabled or in dry-run. No
installation default moves merged PRs to Done. The sole policy action is an explicitly
approved eligible Task `stage_id` transition; native completion, Sprint/history,
estimates, followers and messages are not configurable targets. Native
tracking/notifications, timestamps/durations and nonterminal recomputation are real side
effects. Rating, email-template and SMS-template targets are refused.

This runbook is not approval to deploy, grant capabilities, configure a scheduler or
webhook, enable live policies, publish code, or restore a database. Obtain operator
approval for those effects separately and record the exact delivered SHA. Fixture
approval is not live approval. Customer production outcome is unobserved.

## Approval and dry-run-before-enable

1. Back up the database and filestore together; record the exact code/image/addon
   versions and test restoration in an isolated environment. Inventory native Task
   overrides, access rules and notification configuration. Unknown installed
   source/authority profiles fail closed; never bypass them with context or sudo.
2. An authorized administrator assigns Git Policy Manager explicitly to the owner and a
   different approver; installation assigns nobody. Use a least-privileged active
   internal execution user, not uid 1 or a portal account. All three need current
   company membership and concrete Project/Task authority. A System Administrator may
   emergency-disable but does not implicitly gain activation.
3. In Project → Git Policy, select Enable Dry Run. Configure a repository-local rule and
   draft revision in Project → Configuration → Git Policy Rules/Revisions: exact branch,
   1–20 eligible source stages, one eligible target, 0–20 exact check names and the
   approved executor. No names means CI is not a condition, not that CI passed. No
   domains, scripts, wildcard checks or caller-selected Tasks exist.
4. A distinct approver opens the revision, selects Approve and Activate, and explicitly
   acknowledges native effects. Review immutable activation mode, server UTC cutoff,
   revision, owner/approver/executor and scope. Dry-run proposals never reserve an
   effect, increment a Task fence or authorize execution.
5. Preview from the rule or Repository (20 PRs per request). Inspect ordinary Dry Runs
   list/form, bounded finite reason and normalized observation. The native button
   previews the first page; the validated `action_dry_run_git_policy(after_id)` RPC
   returns `next_pr_cursor` for explicitly controlled further pages. The cursor is
   pagination only, never authority. Do not claim the first page is all evidence.
   Exercise synthetic post-cutoff events in staging before production approval.
6. Only after separate live-effect approval and review of dry runs: select Apply Mode on
   the Project. This revokes old approvals; it does NOT promote previews. The owner
   creates a fresh successor revision; a different approver activates it with a new
   cutoff. Only later eligible merges AND original authenticated receipts strictly after
   that cutoff can execute. Activation is not a historical backfill.

The Project page exposes enabled/mode/authority epoch and scoped Attempts navigation;
rule status distinguishes Disabled, Dry Run and Active. Status represents persisted
controls, not a promise of current Task eligibility. Configuration menus expose
Attempts, Consumed Effects and Discovery. Ordinary native list/form widgets render
untrusted names/SHA text as text, not HTML; no production custom OWL is required.
Task-specific search/count/group/read/export always intersects current native
Task/Project/company rules. No elevated counters or counts of inaccessible Tasks.

## Diagnostics and safe recovery

Attempts retain the original activation/revision, repository/PR identity, immutable
Agile key, Task/stage/fence and sealed observation. Forms show finite state/reason,
claim count, next retry, lease expiry and append-only events. New events retain the
initiating actor; earlier rows may have no actor (upgrade does not fabricate one). This
actor is not necessarily the business execution user; Consumed Effects shows that
approved actor and historical before/after stage/native state/version/time. No payload,
Task description, arbitrary exception or secret is retained in policy reasons.
Raw/redacted GitHub payload operations remain governed by the separate
[Git facts runbook](github-git-facts-operations.md).

- `waiting`: missing/pending exact-head checks; native processing may recheck them.
  Missing/pending CI consumes the same five processing claims as transient faults
  (M7-L1), not a separate 24-hour wait allowance. After five claims, the next due scan
  settles `failed/attempt_limit`; late success does not resurrect it. Claim spacing
  depends on backoff and actual cron service, so there is no fixed wall-clock wait SLA.
  Monitor waiting claim counts/next retry and exhaustion separately from transient
  failures. This conservative contract limit is retained, not remediated by resetting
  budgets, reviving old attempts or weakening freshness. Multiple same-name check
  identities, absent `updated_at`, ambiguous ordering, another SHA/repository or invalid
  timestamps fail closed. Do not synthesize dates.
- `retryable/transient_failure`: inspect sanitized events and the actual operational
  fault. A current capability holder with visible attempt and rule write authority can
  Retry Transient Failure on that existing attempt. It only requeues an unchanged
  eligible candidate; it accepts no replacement Task/evidence/identity parameters, does
  not reset the five-claim budget, and repeats cutoff/fence/authority checks. Native
  cron revalidates again. There is no public apply-now button.
- `processing`: random private five-minute lease; do not copy a lease token into RPC
  context or edit it. A committed expired lease is reclaimable through the native
  worker, not proof of permission. An uncommitted killed transaction rolls back;
  independent-process fixture coverage verifies write/audit crash recovery.
- `failed`, `rejected`, `expired`, `revoked`, `no_op`, `applied`: terminal; discovery,
  reprocess, new revision and operator retry do not resurrect the old candidate.
  Consumed markers prevent another effect for that repository/PR/Agile-key/action, even
  after a manual move back or a different target/revision/head SHA. A new PR is the
  normal future trigger. Do not reset fences, budgets or consumed markers.

Batches have at most 20 claims, each with a complete item savepoint before native
progress commit. One discovery PR is processed per repository cursor visit; loads are
bounded to 20 PRs/rules/check/source pages and overflow rejects instead of choosing a
partial winner. Repository cursors cycle existing facts but never renew source
timestamps/cutoffs. Retry delay starts at 60 seconds, doubles, caps at 3600; five claims
exhaust an attempt. Fresh-transaction retry is required after database
serialization/deadlock; a savepoint cannot refresh repeatable-read evidence.

### Discovery capacity admission (M7-L2)

Expired history still consumes cursor visits; a disposable fixture with 40 expired PRs
before one fresh PR required 41 visits. One due repository is visited per cron
invocation, not every repository. This is a retained availability limitation, not a
safety bypass or evidence that production throughput is adequate.

Before separately approving live apply, measure an upper service-gap bound `C` for cron
on that environment, the retained discovery cursor count `R` (including inactive
repositories that still consume visits), oldest undiscovered eligible merge age `A`, and
rows `H` ahead of it in the ascending-ID scan. Under regular fair service, a
conservative scan allowance is `(H + 1) * R * C`, plus one wrap visit when the cursor is
beyond that merge. Include ingress delay, CI readiness, attempt service and a safety
margin; require the total including `A` to remain below 24 hours. This is an operator
admission calculation, NOT a server-enforced capacity gate or a guaranteed Odoo.sh
service bound. Continuous backlog/cursor lag monitoring must confirm it. If no credible
service bound or margin exists, keep facts-only or dry-run; do not approve live apply as
a reliable automation service. Safety still fails closed if an event expires. Do not
backfill by changing timestamps/cutoffs.

The official five-minute guidance is a best-effort lower-frequency warning, not an upper
`C` bound. With one cursor and a hypothetical measured five-minute service gap, 40 rows
ahead alone cost 205 minutes; more repositories/gaps increase latency. Record actual
service measurements and residual late-event risk at deployment; no live measurement or
production admission is supplied by the local fixture. Bounded historical skipping or a
distinct CI polling budget remain future reviewed changes, not hidden modifications of
this candidate's authority or retry contract.

### Current-delivery provenance continuity (M7-S1)

Signed opened/merge/repeated-update events must each retain the resolved active
project/company-local Task on their new association decision, including duplicates. The
current PR delivery's exact repository/provider/key/Task audit remains mandatory; an old
permanent link is insufficient. A uniqueness exception alone is not proof: the
normalizer re-resolves an exact association, or lets the native transaction retry when
the winner is not visible. No Task is written by normalization. Monitor
`invalid_provenance`; never repair immutable old audit rows or relax the consumer. Old
Task-less decisions are not backfilled. An authorized replay preserves the same
receipt/cutoff and immutable audit; it cannot turn missing historical proof into a new
trigger. Require genuinely later eligible current delivery evidence instead.

## Shutdown, rollback and backups

Emergency Disable on Project stops all rules; Disable Rule revokes that identity's
current epoch. Capability holders and visible System Administrators can disable. Control
locks serialize disable with execution: after disable commits, no later pending effect
settles; an effect already settled first is historical. Verify persisted disabled mode
and revoked approvals, not just a dismissed dialog. Deactivating a cron alone is not the
policy kill switch and cannot undo a running item. No model/RPC path is allowed to call
progress commits outside native cron.

Disable does NOT undo already committed Task changes, native queued messages or
notifications. Do not promise to retract external mail/SMS; template-driven effects are
excluded precisely because transaction rollback cannot retract them. If a human chooses
a stage correction, do it as an ordinary separately authorized Task change, respecting
later manual changes and preserving evidence. Do not replay for rollback.

Before code rollback/update/uninstall: disable policies, preserve backups, immutable
effect/attempt/approval/revocation evidence and exact versions; review the supported
migration path in a disposable restored database. Uninstall may remove policy tables:
this is not retention or a harmless recovery action. Loss of tombstones through
restore/uninstall is an incident: keep policy disabled, reconcile external observations
and Task state, and require fresh successor approval/cutoff excluding old observations.
Never restore only one policy table or enable an old restored activation automatically.

## Retention

Consumed effect tombstones and used revisions/activations/revocations are retained for
the repository's lifetime. Immutable observations/decisions/attempt events cannot be
edited/deleted via ORM; unique fingerprints/events bound duplicate-poll growth. Do not
delete/recreate/repurpose a repository to evade stable identities. There is no new
policy purge job or public purge API. A separate reviewed archival/export/ retention
design is required; DB administrators remain the trust root. Authorized native export
honors current scope and is not a backup of inaccessible policy history. M6 terminal
payload purge does not delete the policy consumed identity.

## Odoo.sh portability and staging limits

Primary expected target is Odoo.sh, not the sole supported host. Runtime requires native
`ir.cron` and PostgreSQL/ORM; no queue_job, external daemon, writable addon tree,
provider SDK/API, shell executable, or outbound provider connection. Tests/builds may
use Docker/Chrome/subprocesses; those are test tools, not addon runtime dependencies.

Canonical verification uses a read-only Odoo root filesystem and addon mount, writable
Odoo data and temporary storage, and an internal DB-only Docker network without provider
egress or published run-container ports. It exercises standalone optional install,
aggregate install/update/reverse-uninstall/reinstall, native form tours, M5 Hoot, M6
regressions and independent-process recovery. Native progress-budget interruption tests
call the real separate-cursor scheduler and real progress commit, then exhaust remaining
time at settled boundaries; crashes are real OS process termination in disposable
fixtures, not simulated transaction success.

This is NOT a live Odoo.sh, Enterprise or arbitrary-extension test. Verification builds
from current official `odoo:19.0` and includes the installed native `hr_timesheet` addon
in aggregate apply/lifecycle coverage. It does not use a source-file compatibility
allowlist. Actual runtime identity is recorded with each verification run. Other Task
extensions continue through ordinary ORM inheritance; assess their behavior,
particularly irreversible external effects, before enabling live apply. See
[apply boundary](../git-policy-apply-boundary.md) and ADR-012 for current identity,
stage and transactional safeguards.

Official
[Odoo.sh technical FAQ](https://www.odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html)
says scheduled actions are best effort and must not be expected more frequently than
every five minutes. The addon interval is one minute but offers no one-minute SLA.
Per-repository discovery is one PR per cursor visit: backlog latency can exceed
freshness windows; monitor Discovery cursor and expired reasons. Bounded safety is
preferred to claiming all historic observations will execute.

Official
[branch documentation](https://www.odoo.com/documentation/19.0/administration/odoo_sh/getting_started/branches.html)
says staging copies are neutralized: scheduled actions are disabled and outgoing mail is
intercepted. Manually trigger/re-enable only synthetic approved test work; less-active
databases may run cron less often. Neutralized database copies can retain Project enable
flags/approvals: explicitly disable/revoke before experimenting and create fresh
synthetic approvals/cutoffs. Local Compose fixtures do not prove staging platform
scheduling, email neutralization or production deployment behavior.
