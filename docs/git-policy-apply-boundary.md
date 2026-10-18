# Git policy apply boundary

Odoo 19 Community-compatible, optional LGPL-3 private-suite addon. No OCA conformity
claim, new dependency, default rule, provider call or live activation.

## Execution and recovery

Explicit two-person apply approval creates a durable repository discovery cursor. The
one-minute native cron visits one bounded PR page and up to twenty attempts per
invocation. Receipt processing, normalization and dry-run evaluation remain effect-free.
Approved cutoffs exclude historical facts.

Attempts retain their original Task/stage/monotonic transition fence, activation and
sealed observation. Claims expire after five minutes. Waiting/transient attempts use
exponential backoff from one minute, capped at one hour; five processing claims end in
terminal failure. Terminal attempts are not revived by discovery or replay. Later CI
evidence may settle a waiting attempt, never widen its Task or approved action. The
native Retry Transient Failure action requeues only an eligible existing transient
attempt, without resetting its budget/fence or replacing evidence/identity. Terminal,
exhausted, stale, expired and consumed candidates remain nonretryable. See the
[operations runbook](runbooks/git-policy-operations.md).

Immediately before mutation the worker claims the Attempt and revalidates persisted
controls, current native identity/record access, Task fence, exact evidence/checks and
target-stage eligibility. Only `stage_id` reaches native Task write, under the approved
non-superuser identity with clean context. Normal native tracking is not suppressed.
Completion/reopen, Sprint, estimates, hierarchy, followers and messages are not action
targets. Postconditions roll back unsupported native effects. Closed Sprint history
stays unchanged.

Task write, immutable consumed effect, before/after/actor/revision/evidence audit and
settlement share one savepoint. One repository/PR/Agile-key/action marker survives rule
revisions and manual moves; replay cannot move the Task again. Private system scheduling
writes use narrow elevation, not elevation for Task authorization or mutation. No
exception text enters retained diagnostics.

Disable or revoke stops pending work; it does not undo a committed Task change. A manual
away-and-back move increments the server-owned fence and terminally conflicts with the
old attempt. Under repeatable-read, concurrent changes raise serialization failures that
must restart from a fresh transaction; a savepoint cannot refresh evidence. Native cron
owns progress commits. Ordinary RPC/model context cannot invoke that commit path.

## Compatibility and verification

The Task fence also observes native `_compute_state` dependency transitions, not just
named `write` inputs: linking/unlinking an open blocker and blocker-state propagation
both advance it on each actual state change, including away-and-back. A no-change
recompute does not increment it. The token is a stored field sharing native
`_compute_state`: the observer calls `super`, then assigns only its token within native
field protection. This avoids recursive Task writes, a second business-state mutation,
and changes to dependency-computed tracking, actor/timestamps or Scrum history. Direct
stage/scope/active writes advance the token through a private `super` write under the
same actor, preserving the remaining native addon chain. Unsaved/onchange records do not
advance durable tokens. A direct stage/state write and its native recompute can both
advance the monotonic token; it is not an event count. No actor authority is gained from
native `compute_sudo`.

This follows inspected runtime `addons/project/models/project_task.py:385-399` and
`orm/fields.py:1898-1921`: `Field.compute_value` removes the pending stored recompute
before calling the method, making the old-state read safe just as in native
`_compute_state`. The latter file SHA-256 is
`a21483829a42fe958faff5a8ee6118f0a2946a031604ec4df055c0a74174ed14` in the originally
inspected image (historical source evidence, not a runtime pin). Do not replace this
hook with a dependency-input-only fence: changes on another blocking Task would escape
that boundary. Native
[field compute protection and assignment](https://github.com/odoo/odoo/blob/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/orm/fields.py)
keep the token update inside the compute, without manufacturing Task metadata.

Actual approvals publish on Project and repository; effects publish only on repository
and rule. These private, server-owned publication markers create ORM shared-row write
conflicts with competing authority/evidence mutations, not recovery/navigation features,
authorization, lease counters or approval-epoch bumps. First approval shares the Project
row because there may be no current activation to revoke. Authority-relevant Project
changes revoke current activations through their rules, already conflicting with rule
effect publication; unrelated Project edits need no additional effect conflict.
Repository evidence inputs share the repository row with approval/effect publication.
Competing mutations roll back the complete stale effect; retry starts a fresh
transaction. Leasing independent attempts never writes a shared parent.

Apply uses ordinary Odoo ORM inheritance, including installed Task addons; it does not
inspect or hash their source files. The approved non-superuser identity, current record
access, approved stage configuration and atomic postconditions remain the execution
boundary. Target stages with rating, mail or SMS templates remain excluded because
irreversible sends cannot be rolled back. Additional extensions with external effects
need behavioral assessment; a stage/field postcondition cannot undo an external send. No
live Odoo.sh or Enterprise installation has been exercised.

Canonical `env -u COMPOSE_PROJECT_NAME ./scripts/verify` covers standalone optional
install (no Scrum/GitHub), aggregate install/upgrade/uninstall-reinstall and discovered
apply tests with Scrum and the real native `hr_timesheet` addon. The timesheet
regression requires the installed module and native fields, applies through the approved
actor and preserves allocation/timesheet data. `hr_timesheet` is a verifier scenario
only, not a production dependency. Verification builds from current `odoo:19.0`; check
the verify log for the Odoo build (for example, `Odoo version 19.0-20260926`). It also
runs `scripts/probes/git_policy_concurrency_probe.py` through disposable Odoo shell:
native cron progress, independent OS processes/PostgreSQL backends claiming
concurrently, disable/revoke/revision/manual/identity/fact/stage and native
dependency-link/blocker-state races, effect-before-disable settlement and process death
between claim/write/audit with rollback and recovery. TransactionCase tests cover native
dependency away-and-back/no-change recomputes, expired/replaced leases, CI waiting,
five-failure dead letter, partial batches, non-admin visibility/count/group/export and
immutable audits. Test scripts commit only in their declared disposable database, never
production model code.

The canonical verification overlay additionally constrains Odoo's filesystem/addon mount
to read-only and networking to internal DB-only access, runs native
approval/preview/disable/retry form tours and tests real native progress commits with
exhausted time budgets at settled boundaries. A 1,001-PR synthetic repository load
verifies a hard 20-PR page and bounded query count. These are local constraints, not a
live Odoo.sh result.

No deployment, publication, live provider configuration or shared database change is
authorized by these checks. Consumed markers must survive future retention design;
deleting them destroys idempotency. Customer/live outcome remains unobserved.
