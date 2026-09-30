# ADR-012: Milestone 7 Opt-in Git Workflow Policy Contract

## Status

Accepted for the bounded Milestone 7 continuation of mission brief section 15.
Supersedes ADR-008's proposed automation design, not ADR-011's observation-only
connector contract. Acceptance of this design is not production activation or a
claim that the engine is delivered. The root slice installs an inert audit fixture;
rules, evaluator, apply worker, operational controls, and adversarial review follow
in the serial M7 graph. There was no previously accepted numbered M7 specification.

## Outcome and boundaries

Beneficiary: a Project owner who explicitly wants a merged PR to make an eligible
Agile task ready for their next workflow stage. Evidence: M6 already persists
repository-scoped PR/check observations and immutable Agile-key associations;
mission brief section 15 distinguishes these facts from workflow policy.

`project_agile_git_automation` is optional, LGPL-3, Odoo 19 Community-compatible
private-suite code, not an OCA-conformity claim. Its sole base dependency is
`project_agile_git`. No GitHub, Scrum, queue_job, SDK, polling, daemon, outbound
provider operation, or synchronous webhook task write is required. Existing addons
must not depend on it. Odoo.sh is the primary expected target, not the sole target.

Only one typed effect is permitted: `task_stage_transition`, writing exactly
`{'stage_id': approved_target_stage.id}` through normal Task ORM under an approved
non-superuser internal user. No arbitrary domain, expression, Python/eval, server
action, model/method/field, wildcard branch/check, task-name/database-ID matching,
completion/reopen, Sprint, estimate, follower, or message action is configurable.
No default merged-to-Done rule or automatically enabled demo policy exists.
Jira migration, releases, other providers, Knowledge connectors, and richer UI
indicators remain non-goals and do not gate M7.

## Exact source findings (observed, not inferred)

Inspected the current Odoo 19 Community container image
`odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c`
read-only, alongside ADR-011's pinned official Odoo source at
`c2957158eb2f7a341a874c3c58884c8a162ef59a`. Runtime files are under
`/usr/lib/python3/dist-packages/odoo/`:

- `addons/base/models/ir_cron.py`: `user_id` is the Scheduler User;
  `method_direct_trigger` uses a separate cursor; `_commit_progress` commits and
  returns remaining time. Outside a cron it still commits. Do not invoke it in a
  normal model/RPC transaction or a TransactionCase. Runtime file SHA-256:
  `ee4b0a79704e1dc9ff914ff44347ff62f8de99555434398725e24c494fea783c`.
- `orm/models.py`: `check_access('write')` on a nonempty recordset checks model ACL
  and record-level rules; an empty recordset checks only model authority.
  `with_user` disables superuser mode except for uid 1; `with_company` alone does
  not grant company access. Runtime file SHA-256:
  `68b2f57f19dbff2d0a54fc0e0ac14446233cf5b254499fe2004c642cd6e09d6d`.
- `addons/project/models/project_task_type.py`: stages have active/project_ids,
  optional mail templates and rating configuration; stage `fold` is not completion.
  Runtime file SHA-256:
  `fe5eaab282843119266516a8ed0dfc7d8d18661cf9928f2c7232acf8c1334cec`.
- `addons/project/models/project_task.py`: state is separate from stage. Its
  stage-dependent `_compute_state` preserves closed states but may reset Approved
  or Changes Requested to In Progress, or set Waiting for dependencies. Normal
  `write` checks access, updates stage timestamps/date-end, and invokes tracking;
  rating-enabled stage transitions can force-send mail synchronously. Runtime
  file SHA-256:
  `95f4f20c26bcf97f3c147b141b7411c5c0c9c31aec578e68a24f9869996aecb4`.
- `addons/project/security/project_security.xml`: native managers see project
  tasks broadly; global company rules still intersect group grants. Project users
  require native Project/task visibility; additive ACLs are not record authority.
  Runtime file SHA-256:
  `34698c4ee327698a9056e7e6ee0e7beec9bc2a0d7c4c89eb4919fe50e9441cb8`.
- Native auto-installed `project_sms/models/project_task.py` calls `_send_sms`
  on a stage write; `sms/models/mail_thread.py` defaults `put_in_queue=False`
  and calls SMS send directly. This is another nontransactional external boundary,
  not merely queued tracking. Runtime file SHA-256 values respectively:
  `7fb21f9882dc45c110b303f612818ad6db88115a4e2fabdb6d661c59ed1d54b2` and
  `a57cdd8aa198049cc94d1f5286c0f210b06cd60d0e864f1156aeda3380d80215`.
- Repository `project_scrum/models/project_task.py` captures completion edges
  only when `state` is in incoming write values. A stage-only call does not request
  Sprint assignment, reestimation, or explicit completion history. Do not bypass
  that override or manufacture Scrum events from a stage label. Flush/re-read
  native recomputation and verify no closed/open edge; unexpected closure or
  changes to protected Scrum fields roll back the entire effect.

Initial policy excludes already closed/cancelled tasks and template tasks, and
rejects target stages with `rating_active`, `mail_template_id`, or (when present)
`sms_template_id`. Template-driven external effects are not accepted in this
initial action, and synchronous rating/SMS sends are not transactionally
recoverable. Ordinary native tracking/notification behavior requires explicit
approver acknowledgment at activation. Notification configuration is revalidated
at execution; changing that configuration revokes the approval epoch. Installed
Task-write extensions must be audited before apply is available; an unreviewed
extension with irreversible effects blocks apply rather than being suppressed.
Ordinary tracking/chatter, queued notifications, date-end/stage timestamps,
durations, and nonterminal state recomputation are native side effects, not direct
action targets. Do not suppress them with context or promise zero side effects.
No fixture configures mail/rating templates or contacts an external party.

## Finite schema and decision ownership

The following names and semantics are fixed for downstream implementation. They
are planned schemas, not a claim that these tables already exist.

- Project controls: `git_policy_enabled=False`, `git_policy_mode='dry_run'`
  (`dry_run`, `apply`), `git_policy_authority_epoch` monotonic integer.
  Only explicit authorized actions may alter mode/enable/epoch, not raw RPC write.
- `project.git.policy.rule`: stable project/repository-bound rule identity, owner,
  active revision pointer; archived identities cannot be recycled for replay.
- `project.git.policy.revision`: immutable after approval; repository/project,
  required company, integer revision, owner, approver, execution_user_id,
  trigger fixed to `merged_pull_request`, exact target_branch (1..255 characters),
  nonempty allowed_source_stage_ids (max 20), one target_stage_id,
  required_check_ids (max 20 distinct exact names, 1..255 characters each),
  effect fixed to `task_stage_transition`. Target stage must be active, linked
  via project_ids, not personal, and outside allowed sources. Source stages must
  satisfy the same project validity. No caller-selected company authority.
- `project.git.policy.required.check`: revision child with one exact name;
  unique per revision. No JSON expression, glob, domain, or generic CI-success flag.
- `project.git.policy.activation`: immutable approval epoch with revision,
  approved identity, server UTC activated_at, mode, project/repository/authority
  snapshots, source/target stage configuration fingerprint, revocation events.
- `project.git.policy.observation`: bounded immutable snapshot of the exact
  normalized PR or check values and authenticated delivery provenance used by a
  decision. Private server producer only. It does not grant execution authority.
- `project.git.policy.attempt`: durable mutable scheduling state, unique candidate
  (activation, repository, PR provider identity, task immutable key), revision,
  observation references, expected task transition version, state, attempts,
  next_retry_at, token/lease expiry. Dry-run and apply attempts are distinct.
- `project.git.policy.effect`: immutable consumed apply identity plus before/after
  stages/native state, identity, activation/revision, observation references, and
  timestamp. UNIQUE(repository_id, provider_request_id, agile_key, effect_type).
- `project.git.policy.audit`: append-only bounded decision/event records. The root
  fixture has only repository/delivery scope, server timestamp, `mode='dry_run'`,
  and `reason='contract_fixture'`; it is not a seal, attempt, or effect marker.
  Later finite reason/outcome extensions must not repurpose these fixture rows.
- Task concurrency fence: `git_policy_transition_version`, incremented under
  the Task row lock for every stage/state/project/company/active change, including
  manual away-and-back changes. It is a concurrency token, never authorization.
  No Task override or field is added in this root slice.

Rule bounds are server-validated on ORM create/write/actions as well as views.
Unknown keys/enum values and mixed-company/project links are rejected, not ignored.
No evaluated rule can invent an action shape. Conflicting active candidates for
the same PR/task fail closed, even if their target happens to be the same; no
priority ordering or first-match winner.

## Ownership, approval, activation, and shutdown

A new explicit `group_git_policy_manager` capability implies Project Manager but
has no installation-time members. The rule owner must be an active internal user
with that capability and current project/repository/company read/write authority.
A different active capability holder approves the immutable revision and explicitly
activates it; approval by the author alone is insufficient. Activation validates
an active, nonportal, uid != 1 execution identity with actual per-record Task write
access and required company membership. Model ACL alone is insufficient. Approval
also acknowledges native stage side effects. Provider payloads/context never choose
owner, approver, execution identity, project, company, or activation mode.

Project enablement and rule activation are both required. Defaults are disabled
and dry-run; switching to apply creates a fresh activation/cutoff, not promotion
of dry-run results. Production enablement, scheduler identity/configuration, or
live apply activation require a separate operator-approved delivery effect. Local
fixture success and accepted ADRs do not confer this authority.

Only owner/authorized approver may edit drafts; edits after approval create a new
revision. Ownership transfer, opt-out, disable, revoke, archive/delete request,
identity inactivity/access/group/company revocation, project/company/repository
reassignment, removed stage, or changed approved stage settings invalidate pending
authority. Used revisions/activations/audits cannot be deleted; archive and append
revocation instead. Re-enable/revision changes require fresh explicit approval
and cutoff. Emergency disable is available to visible authorized capability
holders and native System Administrators; it cannot imply activation authority.

Immediately before execution, lock Project/repository/activation/attempt/Task in
that stable order, then re-read authority and facts without stale cache, revalidate
all identities and their current access, and recheck enable/mode/revocation. Disable
and worker execution serialize on the same control locks: after disable commits,
no later effect may settle. A transaction already settled before disable is
historical, not a partial effect. Already applied markers survive revocation.

## Observation, provenance, freshness, and exact CI evidence

Keep three layers distinct: observation describes a provider fact; deterministic
evaluation produces a proposal and finite reason; the worker independently
checks authority and performs the sole permitted write.

The existing M6 PR has repository/provider identity, merged_at, target_branch,
head_sha, updated_at, ordering_state, and provenance_delivery_id. Checks have
repository/provider identity, exact name, head_sha, state, completed_at,
updated_at, ordering_state, and provenance_delivery_id. Association audit supplies
the delivery/source type/provider ID/key evidence; immutable associations alone
are not proof that the current PR observation referenced that task.

Before producing a sealed observation, trusted internal code must re-resolve a
processed authenticated delivery in the same repository/company, appropriate event
type, and exact fact provenance; require a matching current-delivery PR association
audit (`associated` or `already_associated` with exact key and source_provider_id)
and re-resolve the current active project-local Task key. Never accept a caller's
fact IDs, supplied snapshot, `authenticated=True`, context lease, or payload task
ID as provenance. Public fact/delivery/association/audit creates are denied by ACL;
private sealing entry points must validate persisted scope/source before narrowly
elevating for append-only storage. Tests must forge cross-repository delivery refs,
association refs, processed flags, public create/write payloads, and context.
DB administrators and trusted server code remain the trust root; a stored digest
is not independently verifiable HMAC evidence after retention purge.

M6 has no immutable policy-ready observation seal. Downstream evaluation must add
only the above small snapshot/validation boundary, not rely on a mutable live fact
as an immutable decision record. Do not modify M6 ingress into a policy executor.
There is no need for a new PR/check correlation field in the root: exact repository
plus exact PR head SHA is represented today. No merge-commit/test-merge SHA may
substitute for PR head SHA. Validate supported full SHA format (40 or 64 hex
characters), never repair/truncate missing identifiers.

Trigger eligibility requires: known ordering, merged PR, nonfuture merged_at and
updated_at, exact configured target branch, active repository/project, and source
merge time AND original authenticated delivery received_at strictly later than
activation's UTC cutoff. Equality is rejected conservatively (Odoo timestamps may
have second precision). Late delivery of a pre-cutoff merge and reprocess of a
pre-cutoff receipt cannot become a new trigger. Activation is not a backfill.
A candidate expires 24 hours after merge; snapshots must be no older than 24 hours
at evaluation/apply and source timestamps cannot be in the future. Duplicate
receipt or last_seen_at refresh does not renew source freshness.

With zero required names, CI is explicitly not a condition; audit records that
choice and never claims CI passed. With required names, for EACH name require
exactly one provider check identity in the same repository at the PR's exact head
SHA, `ordering_state='known'`, `state='success'`, reliable updated_at and completed_at,
and completion within [merged_at - 24 hours, current server time] and within the
24-hour freshness bound. Pending/missing checks wait; failed/cancelled/neutral,
unknown timestamp/order, contradictory or multiple run identities fail closed.
Do not pick any success, newest-looking run, another SHA/repo, or infer rerun
ordering from numeric IDs. Multiple same-name runs are intentionally unsupported.

A later matching check observation wakes only existing eligible waiting PRs in
that repository/head SHA; the evaluator rechecks every condition and all required
names. It never associates tasks from check names instead of PR keys. The M6
GitHub check parser reads updated_at; real check_run deliveries without it remain
ambiguous and cannot satisfy this policy. Do not synthesize updated_at from
received_at, completed_at, IDs, or a PR timestamp. Better provider ordering support
is later observation work; the initial contract sacrifices availability to safety.

## Idempotency, manual changes, dry-run, and failure

The consumed effect identity is (stable repository, provider PR identity, immutable
Agile task key, `task_stage_transition`), deliberately excluding delivery, attempt,
lease, revision, activation, head SHA, target stage, and mode. This permits at most
one applied transition per PR/task across duplicate delivery, reprocess, revision,
restart, disable/re-enable, or a manual move back. A new rule cannot replay that PR
into a second stage. A changed manual task does not get overwritten by replay.

Used repository identities must not be deleted/recreated or repurposed to change
that key: activation/effect relations use restrictive deletion, and changes to
provider/provider_repository_id are refused after policy history exists. Archive
instead; a genuinely different provider repository gets a new scoped record.
Project/company reassignment revokes pending epochs and preserves historical
scope snapshots. Never use cascading repository deletion as audit retention.

Evaluation captures Task stage and monotonic transition version. Apply requires
both to match under lock plus source eligibility; otherwise terminal `stale_task`.
A target already reached manually is a no-op, not permission to consume an applied
marker. New evaluation cannot silently revive a stale attempt; explicit authorized
retry still requires unchanged cutoff, task fence, facts, and unconsumed identity.
A new PR is the normal future trigger. Dry-run appends a bounded proposal only;
it never creates a consumed effect, increments the Task fence, or mutates Task.
Switching to apply discards dry-run execution eligibility and creates a fresh epoch.

Worker states: queued, waiting, processing, retryable, failed, rejected, dry_run,
applied, no_op, revoked, expired. Bound each batch to 20 attempts; random private
five-minute leases; max five attempts; exponential retries from 60 seconds capped
at 3600 seconds. Claim/scheduling state is distinct from append-only event history.
Native `ir.cron` owns cursor/progress commits; `_commit_progress` is called only
AFTER the complete settled item savepoint. No model/controller cr.commit/rollback,
no webhook Task writes, no required queue_job. Expired leases are reclaimable, not
authority. Retry serialization failures from a fresh transaction, not a stale cache.

In one savepoint: lock/revalidate, verify no consumed identity, normal Task write,
flush/re-read native effects, insert unique immutable effect and audit, settle
attempt. An audit insert or postcondition failure rolls back Task and effect;
only a sanitized failure event outside that rolled-back savepoint may persist.
A uniqueness collision never repeats the write. Recovery reads the committed marker
before retry; it neither compensates a later manual change nor hides partial state.
Use real independent-connection tests for crash/lease/disable/manual-write races.
Do not claim to roll back already force-sent external mail (hence rating exclusion).
The same restriction applies to already-sent SMS; no post-write audit or rollback
can retract it. Do not add context flags to suppress native notification code.

## Visibility, bounded audit, and retention

Company is required for policy (company-less/shared projects remain facts-only).
Global company rules intersect native Project visibility; no sudo counters,
searches, exports, RPC reads, or retry controls. Root receipts use native manager
visibility and follower/public visibility for Project users, with global company
rules. Later task-specific records must additionally enforce current Task read
visibility rather than leak it through a Project-only record. Existing custom
Project/Task rules must be honored by action boundaries and task-specific queries.

Reason/outcome are finite selections. Store IDs, immutable key/SHA, timestamps,
before/after stage/native state, approved actor, and bounded fingerprints; never
provider payload/title/body, secret, authorization, arbitrary exception text, or
retained provider excerpts in audit/chatter/logs. Cap check/source references at
20 per decision and one event per attempt/outcome transition. No duplicate-poll
audit growth. Append-only effect tombstones and used revision/activation references
are retained for the lifetime of the repository; they cannot be garbage-collected
into replay eligibility. Terminal diagnostics may be archived (not modified or
silently deleted); retention policy and authorized purge/export need separate
review. Root has no production producer, purge, counters, or retry controls.
Uninstall/reinstall must never backfill: old observations predate a newly approved
cutoff; losing markers by database restoration is a recovery incident requiring
disabled policies and a fresh cutoff, never automatic replay.

## Acceptance, verification, and recovery

Root acceptance: independent optional installation with only its base chain;
seven-module install/update/reverse-uninstall/reinstall; imported nonadmin,
private-project, multi-company, forged-provenance/context, immutable/bounded-audit,
and native stage semantics fixtures. Preserve M5 native Hoot/HttpCase and M6
webhook/lease/retention regressions. Static checks under tests/, compileall of addons
and scripts, bash syntax, canonical verifier, diff-check, dependency/license and
complexity review must pass at the committed exact SHA.

This root delivers no working automation or production activation. Downstream
completion additionally requires dry-run nonconsumption; exact-SHA/name/repo/order
and cutoff adversarial checks; conflicting-rule rejection; record-level execution
authority; independent-connection idempotency/manual-change/disable recovery tests;
and exact-SHA review before delivery. Revoke/disable first on uncertainty, preserve
immutable evidence, and block instead of guessing APIs or upgrading privileges.
No main advancement, publication, credentials, shared-service changes, or live
provider/policy setup is authorized by local fixture work.

## Alternatives and consequences

Hardcoded Done, generic server actions/eval, arbitrary successful CI, queued
webhook task writes, and mandatory queue runners are rejected. A conservative
one-effect-per-PR/task and single-check-identity policy deliberately rejects some
valid reruns/late events; availability does not outrank authority. The smallest
root is a fixture, not premature configuration/evaluator scaffolding. Future
schema extensions need reviewed migration/install/update evidence.

## Sources

- [Mission section 15](../mission-brief.md#15-git-automation)
- [ADR-011](011-git-facts-and-visibility-contract.md)
- [M7 implementation plan](../plans/2026-09-30-milestone-7-git-policy.md)
- Official pinned Odoo source: https://github.com/odoo/odoo/tree/c2957158eb2f7a341a874c3c58884c8a162ef59a
- Odoo 19 scheduler: https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html#scheduled-actions-ir-cron
- Repository source: `addons/project_agile_git/models/project_git_fact.py`,
  `addons/project_agile_git_github/models/project_github_normalizer.py`,
  `addons/project_scrum/models/project_task.py` at baseline
  `338954ff356702b98d412e11af4bf390a1648dea`.
