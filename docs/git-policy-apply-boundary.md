# Git policy apply boundary

Odoo 19 Community-compatible, optional LGPL-3 private-suite addon. No OCA conformity claim, new dependency, default rule, provider call or live activation.

## Execution and recovery

Explicit two-person apply approval creates a durable repository discovery cursor. The one-minute native cron visits one bounded PR page and up to twenty attempts per invocation. Receipt processing, normalization and dry-run evaluation remain effect-free. Approved cutoffs exclude historical facts.

Attempts retain their original Task/stage/monotonic transition fence, activation and sealed observation. Claims expire after five minutes. Waiting/transient attempts use exponential backoff from one minute, capped at one hour; five processing claims end in terminal failure. Terminal attempts are not revived by discovery or replay. Later CI evidence may settle a waiting attempt, never widen its Task or approved action. No public retry API is introduced here; operator controls are the next delivery slice.

Immediately before mutation the worker locks and revalidates persisted controls, current native identity/record access, Task fence, exact evidence/checks and target-stage eligibility. Only `stage_id` reaches native Task write, under the approved non-superuser identity with clean context. Normal native tracking is not suppressed. Completion/reopen, Sprint, estimates, hierarchy, followers and messages are not action targets. Postconditions roll back unsupported native effects. Closed Sprint history stays unchanged.

Task write, immutable consumed effect, before/after/actor/revision/evidence audit and settlement share one savepoint. One repository/PR/Agile-key/action marker survives rule revisions and manual moves; replay cannot move the Task again. Private system scheduling writes use narrow elevation, not elevation for Task authorization or mutation. No exception text enters retained diagnostics.

Disable or revoke stops pending work; it does not undo a committed Task change. A manual away-and-back move increments the server-owned fence and terminally conflicts with the old attempt. Under repeatable-read, concurrent changes raise serialization failures that must restart from a fresh transaction; a savepoint cannot refresh evidence. Native cron owns progress commits. Ordinary RPC/model context cannot invoke that commit path.

## Compatibility and verification

Apply fails closed unless installed Task inheritance sources and native write methods match `models/policy_write_profile.py`. The inspected image is Odoo 19.0-20260908, with reviewed optional Scrum and native project/mail/SMS/rating mixins. Fingerprints are a compatibility gate, not tamper protection against trusted server/database administrators. Another Odoo patch, Enterprise/addon extension or monkeypatch requires source review and updated regression evidence; context cannot bypass it. No live Odoo.sh installation has been exercised.

Canonical `env -u COMPOSE_PROJECT_NAME ./scripts/verify` covers standalone optional install (no Scrum/GitHub), aggregate install/upgrade/uninstall-reinstall and discovered apply tests with Scrum. It also runs `scripts/git_policy_concurrency_probe.py` through disposable Odoo shell: native cron progress, independent OS processes/PostgreSQL backends claiming concurrently, disable/revoke/revision/manual/identity/fact/stage races, effect-before-disable settlement and process death between claim/write/audit with rollback and recovery. TransactionCase tests cover expired/replaced leases, CI waiting, five-failure dead letter, partial batches, non-admin visibility/count/group/export and immutable audits. Test scripts commit only in their declared disposable database, never production model code.

No deployment, publication, live provider configuration or shared database change is authorized by these checks. Consumed markers must survive future retention design; deleting them destroys idempotency. Customer/live outcome remains unobserved.
