# Milestone 7 Opt-in Git Policy Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Deliver an optional, disabled/dry-run-first, explicitly authorized merged-PR stage-transition policy without making connector facts workflow authority.

**Architecture:** ADR-012 fixes a finite schema and separates sealed observations, deterministic proposals, and independently authorized effects. The serial Kanban lane owns durable phases and exact-SHA review; short reasoning subagents cannot replace those board handoffs. Native Odoo 19 ir.cron owns bounded scheduling and cursor/progress commits; normal Task ORM owns native behavior.

**Tech Stack:** Odoo 19 Community, PostgreSQL constraints/row locks, standard ORM views, imported TransactionCase/HttpCase fixtures, isolated Docker Compose canonical verification. LGPL-3 private Odoo-compatible suite; no OCA-conformity claim or mandatory provider/Scrum/queue dependency.

---

## Outcome contract and execution instructions

Beneficiary/problem/acceptance: project owners need explicitly configured Ready for
QA-style transitions after merged PR evidence, not a hardcoded Done rule. Read
[ADR-012](../adrs/012-git-workflow-policy-contract.md), ADR-011, historical ADR-008,
mission brief section 15, AGENTS.md, and exact runtime Odoo 19 source before work.
The module base dependency remains only project_agile_git. No publication, live
policy/provider setup, credentials, shared runtime change, or main advancement.

Serial lane: feature/t_9a70c1bb-m7-git-policy in
/srv/projects/kanban-worktrees/odoo-agile-delivery/t_9a70c1bb-m7-git-policy.
Original base/expected main: 338954ff356702b98d412e11af4bf390a1648dea.
Read the newest lane-contract and verify registered branch, HEAD, target and clean
state; do not recreate/reset/rebase the lane. Use the approved remote wrapper;
all commands below run inside that remote worktree. Each board phase starts only
after fresh exact-SHA approval of its parent, with one active writer.

Tasks below are small test/change slices; each numbered step is one action. For
new model work, promote one acceptance example at a time into a real imported test,
run RED, implement GREEN, rerun, review the diff and commit the logical slice.
The schema/names/reasons in ADR-012 are authoritative; don't invent a generic
rule language or delegate unresolved architecture. Do not apply the illustrative
future test snippets before the corresponding board phase is released.

## Root phase: t_9a70c1bb (this deliverable)

### Task 1: Prove the missing optional lifecycle (2–5 minutes)

Objective: fail because the addon and verifier entry do not yet exist.

Files: create tests/test_project_agile_git_automation_contract.py.

1. Write manifest/base-dependency, no Task override/evaluator/cron, imported test,
   and seven-module/independent-install/reverse-uninstall assertions.
2. Run `python3 -m unittest discover -s tests -p test_project_agile_git_automation_contract.py -v`.
   Expected RED: missing manifest/tests package and absent seventh verifier entry.
3. Preserve the actual failure, not a fabricated expected-output transcript.

### Task 2: Install the inert fixture (2–5 minutes per file group)

Objective: expose only a bounded synthetic audit receipt, not configuration or execution.

Files: create addons/project_agile_git_automation/__manifest__.py, __init__.py,
models/__init__.py, models/project_git_policy_audit.py,
security/ir.model.access.csv, security/project_git_policy_security.xml.

1. Declare sole dependency project_agile_git, LGPL-3, installable, not auto_install.
2. Define only project.git.policy.audit with company-required repository/delivery,
   dry_run-only mode, finite contract_fixture reason and server timestamp.
3. Enforce no non-superuser create; reject context-forged authors, wrong repository
   provenance, and ORM write/unlink for every identity. Do not add a producer.
4. Grant Project users read only; global company/Project visibility constrain
   searches, reads, counts, grouping and exports. No group member can create effects.
5. Rerun Task 1 after Task 4; expected GREEN. Commit with the fixture tests.

### Task 3: Exercise the exact native boundary (2–5 minutes per test)

Files: create addons/project_agile_git_automation/tests/__init__.py,
tests/test_policy_contract.py. Test package must import the fixture; class uses
post_install/-at_install tags so complete optional inheritance is visible.

1. Add an actual reader and manager, follower-only project, another company, and
   manager enabled for both companies. Test general ACL success separately from
   denial on a concrete record; test read/search/count/group/export and forged
   allowed_company_ids/context/public provenance creation.
2. Test bounded reason, repository mismatch, superuser append-only invariants,
   default dry_run and absent rule/cron/apply entry point.
3. Prove native semantics through a nonadmin normal Task write. Example:

```python
task.state = "03_approved"
task.with_user(reader).write({"stage_id": qa_stage.id})
self.assertEqual(task.state, "01_in_progress")
self.assertFalse(task.is_closed)
self.assertTrue(task.date_last_stage_update)
```

4. With Scrum installed assert unchanged assignment/history/estimates; without it
   the same fixture remains usable. Native closed state is not reopened by a stage
   label. Synthetic stages have no mail/rating template.
5. Run canonical verification; require actual discovered fixture tests, not static
   text or mocks as runtime proof.

### Task 4: Add the fixture lifecycle and current delivery docs (2–5 minutes each)

Files: modify scripts/verify, README.md, docs/adrs/008-git-automation-model.md,
docs/adrs/README.md; create docs/adrs/012-git-workflow-policy-contract.md,
this plan and addon README.

1. Install only project_agile_git_automation plus its dependency chain first on
   the existing install database, with its focused tags; reset that same disposable
   DB before the aggregate install. Do not add a shared DB or Compose namespace.
2. Append module/test tag to all six existing modules. Uninstall optional automation
   before Git core. Preserve M5 Hoot/HttpCase and M6 webhook/cron/retention discovery.
3. Supersede ADR-008, link ADR-012, correct README's stale M6 skeleton/ingress deferral,
   and call M7 an accepted pending engine with an inert root fixture only.
4. Execute all checks in the final gate below; commit the clean artifact and request
   same-card exact-SHA review from Gilfoyle. No root completion before approval.

## Rules phase: t_0ef017bf (not executed by root)

### Task 5: Draft project-scoped typed rules (2–5 minutes per invariant)

Files to create: models/project_git_policy_rule.py,
models/project_git_policy_revision.py, models/project_git_policy_required_check.py,
models/project_project.py, tests/test_policy_rules.py. Modify models/tests imports,
manifest data, security CSV/XML, and ordinary configuration views.

1. RED: direct create/write rejects cross-project stages, empty source list, target
   in sources, >20 stages/check names, duplicate names, generic expressions, and
   unknown trigger/effect/mode. Installation remains opt-out/dry-run.
2. GREEN: implement the exact finite ADR-012 schema, typed bounds and company checks;
   derive company/project from readable repository rather than trusting payload.
3. Run the focused imported tests via the disposable canonical fixture. Commit
   after both positive and negative tests pass. No evaluator or Task override.

### Task 6: Separate author and approver (2–5 minutes per action)

Files: models/project_git_policy_activation.py, tests/test_policy_authority.py,
security/project_git_policy_security.xml, project policy views.

1. RED: ordinary managers without the new capability, author self-approval,
   uid 1/portal/inactive executor, model-only Task ACL, hidden concrete Task and
   cross-company activation all fail. Raw RPC writes cannot switch enabled/mode.
2. GREEN: new capability has no initial members; immutable approved revision,
   distinct approver, approved non-superuser executor and explicit cutoff/mode.
3. Add disable/revoke/owner-change/access-removal/stage-configuration tests;
   version used authority and invalidate pending attempts. No Task stage write.
4. Run install/update/uninstall/reinstall; commit and exact-SHA review before release.

## Evaluation phase: t_33a1d9a4 (not executed by root)

### Task 7: Seal only verifiable normalized evidence (2–5 minutes per forgery)

Files: models/project_git_policy_observation.py, tests/test_policy_provenance.py.

1. RED: caller payload/context, fake processed flag, mixed repo/delivery/head,
   old association versus current PR key audit, or public create cannot mint a seal.
2. GREEN: private producer re-resolves processed delivery, matching fact provenance,
   association audit and repository-local key; stores bounded immutable snapshots.
3. Deny rather than infer absent ordering/timestamps; preserve the M6 observation-only
   ingestion transaction. No provider dependency or polling to obtain missing facts.
4. Run nonadmin/multi-company tests; commit only after actual RED/GREEN evidence.

### Task 8: Deterministic exact-head conditions (2–5 minutes per matrix row)

Files: models/project_git_policy_evaluation.py, tests/test_policy_evaluation.py.

1. RED: merged PR has exact branch/SHA, source+receipt strictly post-cutoff, and
   <=24h freshness. Reject missing/nonfuture timestamps and stale/ambiguous order.
2. RED: table-test zero required checks (no CI claim), each required exact name,
   pending/missing wait, failure/neutral reject, wrong repo/SHA, multiple same-name
   identities, and late matching check reevaluation. Missing updated_at stays closed.
3. GREEN: evaluate typed sealed observations only; no arbitrary action dispatch.
   Conflicting rules reject even identical targets; no Task writes or apply marker.
4. Persist bounded proposals/reasons; duplicate reevaluation does not grow unbounded
   audit rows. Run focused and canonical gates, commit and request exact-SHA review.

## Apply phase: t_ecfd7c3d (not executed by root)

### Task 9: Prove stable identity and manual fences (2–5 minutes per scenario)

Files: models/project_git_policy_attempt.py, models/project_git_policy_effect.py,
models/project_task.py, tests/test_policy_idempotency.py.

1. RED: unique effect key excludes revision/delivery/target/mode. Duplicate delivery,
   reprocess, changed revision, restart and manual move-back cannot repeat a write.
2. RED: manual away-and-back, state/project/company/active changes invalidate the
   expected stage/version under lock. Dry-run and manually reached target do not
   create applied markers or increment the Task fence.
3. GREEN: monotonic transition fence and immutable unique marker; source stage and
   record-level executor write checks under explicit clean user/company context.
4. Rerun focused tests; inspect every sibling write path and preserve native super().

### Task 10: Atomic apply and reversible failure (2–5 minutes per failure point)

Files: models/project_git_policy_execution.py, tests/test_policy_execution.py.

1. RED: force an audit/marker/postcondition failure after normal Task stage write.
   Assert no partial Task/effect/attempt success; sanitize the failure reason.
2. RED: reject closed/template tasks, removed/unlinked/rating-active target stages,
   revoked identity, project disable, or changed approved notification settings.
3. GREEN: locked revalidation, one typed normal ORM stage write, flush/re-read
   protected/native outcomes, effect+audit+attempt settlement in one savepoint.
4. Preserve native tracking honestly, no manual commits or state/Sprint mutation;
   run canonical lifecycle and request exact-SHA review.

## Operations phase: t_0a71e969 (not executed by root)

### Task 11: Bound scheduler and retries (2–5 minutes per state transition)

Files: models/project_git_policy_processing.py, data/project_git_policy_cron.xml,
tests/test_policy_processing.py, docs/runbooks/git-policy-operations.md.

1. RED: random five-minute lease, 20-item batch, five attempts, capped backoff,
   expired lease recovery, non-cron public call denial, no synchronous webhook write.
2. GREEN: native private ir.cron entry point, durable claims, settle item first,
   then supported _commit_progress only from scheduler-owned cursor.
3. Test state transitions individually, terminal dedupe, no audit growth on polls,
   active authority recheck and authorized retry without stale-task bypass.
4. Verify no auto-activated production scheduler/policy; document operator-approved
   activation, immediate disable, diagnostic recovery, tombstone retention.

### Task 12: Independent-connection recovery races (2–5 minutes per race)

Files: scripts/test_git_policy_concurrency.py, scripts/git_policy_concurrency_worker.py,
addons/project_agile_git_automation/tests/test_policy_recovery.py.

1. RED: two claims/apply attempts; apply versus manual stage change; apply versus
   disable; crash before/after settlement; duplicate after restart/revision.
2. GREEN: consistent control/Task lock order, fresh-transaction serialization retry,
   committed marker checked before replay; no manual overwrite or hidden partial state.
3. Use only a named disposable DB/namespace; lock/statement/wall timeouts; inspect
   post-race Task/fence/attempt/effect/audit and side effects from independent reads.
4. Run focused and canonical gates, commit, exact-SHA review.

## Assessment and delivery phases (not root implementation)

- t_db284475: c1ph3r independently assesses exact-SHA authority, forgery, privacy,
  multi-company, public RPC and retry boundaries; findings go to the same lane.
- t_a3174e38: cumulative artifact verification and Gilfoyle exact-SHA approval.
- t_5f054545: durable handoff with observed tests, recovery, and honest pending scope.
- t_302ec37b and t_d632ae54: human-gated publication boundary. Local approval does
  not authorize publication or live activation. Do not create duplicate cards.

## Exact final gate for every released implementation phase

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m compileall -q addons scripts
bash -n scripts/verify
env -u COMPOSE_PROJECT_NAME ./scripts/verify
git diff --check 338954ff356702b98d412e11af4bf390a1648dea..HEAD
git status --short
git rev-parse HEAD refs/heads/main
git diff --stat 338954ff356702b98d412e11af4bf390a1648dea..HEAD
```

Expected: real discovered Odoo tests pass independently and in all three lifecycles,
M5 native browser assets run, M6 regressions run, zero failures/errors, compile/static
and shell checks pass, feature branch clean and main unchanged. Preserve full
command/result, full SHA, base/branch/worktree, changed files, dependency/license and
complexity review, native side effects, availability limits and residual risks.

Canonical fixture cleanup removes only its deterministic worktree namespace;
explicitly named projects are not cleaned. Do not touch shared databases/volumes.
On unknown APIs, denied source/access, false discovery, drift or failed checks:
disable effects, preserve the evidence, and block this same card. Rollback is
savepoint rollback before effect commit; post-commit recovery never restores a
stage over a later manual change. Customer production outcome remains unobserved
until separately approved deployment/activation and follow-up observation.
