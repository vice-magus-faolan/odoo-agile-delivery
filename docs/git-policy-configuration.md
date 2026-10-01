# Git policy configuration and approval authority

Target: Odoo 19 Community, private Odoo-compatible LGPL-3 addon `project_agile_git_automation`, sole dependency `project_agile_git`. Configuration, [deterministic dry runs](git-policy-dry-run.md), separate bounded native apply and [operator controls/recovery](runbooks/git-policy-operations.md) are available. Core Agile and Git facts remain independently installable; no live activation/deployment is performed by this delivery.

## Operating boundary

Installation seeds no policy capability members or rules. Projects default to disabled/dry-run. Assign the explicit Git Policy Manager capability through normal authorized administration. An ordinary Project Manager cannot configure/activate. A visible System Administrator can emergency-disable without acquiring activation authority.

Enable a company-scoped active Agile Project explicitly. Configure a repository-scoped rule and draft revision: merged PR, literal target branch, 1–20 active nonpersonal Project-linked source stages, one eligible target stage, optional 0–20 distinct literal CI names (1–255 characters), and an explicit active internal non-superuser execution user in the same company. No CI names means CI is not a condition. Empty Projects fail closed because activation requires concrete Task write-authority evidence. Selectors cannot create/edit/delete native stages.

A different authorized approver must acknowledge native side effects and approve the exact revision. Approved revisions, activation time/cutoff, identities, mode, stage fingerprint and epochs are immutable. Public actions return serializable action/result dictionaries. New-revision action returns a form action; activation returns `activation_id`.

Create a successor draft to edit approved selectors. Editing/creating a draft or changing named checks revokes existing authority; approval is never copied. Owner transfer, archive/delete request, explicit disable, Project scope/visibility/company changes, repository authority changes, relevant stage settings, identity activation/groups/company membership and ACL/record-rule changes revoke authority. A delete request archives the rule; referenced stage/provider identities cannot be deleted/reassigned. Restoration does not resurrect revoked epochs. Security-rule/ACL changes conservatively revoke all approval epochs. A fresh successor approval is required.

## Security and implementation

The [approved bounded authority profile](git-policy-authority-profiles.md) pins
native XML identities, normalized domain fingerprints, groups, permissions and
mutable dependencies. Only literal direct stored Task name/active custom rules
are initially supported; unknown Project/repository/stage/identity or other Task
profiles fail closed at activation/current validation. Native Odoo remains the
access evaluator. The Task observer revokes affected approval epochs and the apply
layer adds a monotonic stage/state concurrency fence. Successful authority-input edits,
create/delete and old/new/descendant scope changes invalidate approvals before
restoration can reuse them. Both stage relation directions are observed.

Global company rules plus fresh native Project subqueries protect search/count/read surfaces. Never cache visible record IDs inside an ir.rule expression: the cached domain can retain stale access. Public controls require caller capability and current record access before narrow server-derived writes. Company context is validated; defaults and arbitrary expressions/actions/model names/methods/fields do not grant authority. Execution identity is persisted in the approved revision, never provider/context-selected. Activation checks every current concrete Project Task under that execution identity; apply repeats actual-record access checks under locks.

Private helpers fence Project, repository, rule and approval rows and invalidate caches. Public activation/disable controls recheck authority after locking. Approval validity is rechecked against current identities, scope, mode, epochs, stages and Task permissions. Native Project/Task unfollow and follower reassignment revoke through an authorized revoke-only follower hook; restoring access before the next validation cannot resurrect an epoch. Revocation is transaction-local and durable only when the owning transaction commits. Direct database administration remains the trust root. The separate apply worker implements ADR-012 lock order, provenance, bounded evaluation, retries and actual Task checks; this delivery does not authorize live apply.

## Native effects and recovery

This configuration layer does not write Tasks. The separately approved native apply stage write can create tracking messages/notifications, update timestamps and durations, and recompute nonterminal Task state. Native completion/reopen state, Sprint/history, estimates, followers and messages are not action targets. Rating/email-template/SMS-template targets are excluded. Do not claim a native ORM write has no side effects.

Emergency disable Project/rule first. Retain immutable approval/revocation evidence. Correct source permissions/configuration, create a successor and obtain fresh distinct-author acknowledgment. No historical/backfill replay is authorized by activation. Apply remains separately operator-gated.

## Verification

Discovered post-install nonadmin ORM tests cover finite selectors, forged defaults/context/fields, owner transfer, two-person/wizard approval, Task record-rule denial, multiple companies, identity/ACL changes, historical immutability and stage mutation rejection. Canonical repository `env -u COMPOSE_PROJECT_NAME ./scripts/verify` covers independent addon install, aggregate install, upgrade, dependency-safe uninstall/reinstall and existing native UI/fact coverage. All verification uses disposable worktree-scoped Compose resources. No OCA conformity, production deployment or customer outcome is claimed.
