# Milestone 6 Git Facts Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Deliver provider-neutral Git facts and safe read-only visibility for Agile projects before any workflow automation.

**Architecture:** `project_agile_git` remains the normalized fact boundary. A provider adapter performs bounded signed-delivery persistence only; a dedicated Odoo 19 `ir.cron` processor claims leased batches and normalizes facts; immutable Agile-key association follows; policy remains a later optional addon.

**Tech Stack:** Odoo 19 Community ORM/controllers and `ir.cron`, PostgreSQL constraints and leases, Docker Compose verification fixtures.

---

## Accepted contract and boundaries

`project_agile_git` owns provider-neutral repository, authenticated-delivery ledger,
branch, commit, pull-request, check, and immutable task-association records. It depends
only on `project_agile`; neither it nor the existing Agile, Scrum, analytics,
document-page, or UI modules acquire a provider or queue dependency. A provider-specific
adapter owns authenticated ingress and a separate Odoo 19 `ir.cron` processor owns
bounded leased retries and normalization after durable ledger persistence. No webhook transaction may normalize a
fact, associate a task, call a provider, post chatter, or make a workflow change.

The sole association grammar is an explicit immutable key such as `ENG-142`, including
the bounded branch/title forms documented by ADR-011. Resolution is repository-project
scoped and records every explicit key immutably; task names, database IDs, payload
project fields, and caller-selected company/context are never authority. Fact visibility
follows Project visibility plus multi-company rules. `queue_job` is rejected as a base
or Odoo.sh runtime; the future portable processor is a bounded `ir.cron` batch with
delivery leases, retries, and failure visibility. Workflow automation remains a
separately approved future addon.

### Task 1: GitHub signed-delivery ingress

**Files:** Create `addons/project_agile_git_github/controllers/github_webhook.py`; modify `addons/project_agile_git_github/__manifest__.py`; test `addons/project_agile_git_github/tests/test_github_webhook.py`.

1. Write failing HttpCase tests for missing/invalid HMAC SHA-256, unknown/inactive repository, malformed/oversize/non-JSON payload, duplicate delivery, and cross-company repository confusion.
2. Implement a `type="http"`, `auth="public"`, `csrf=False`, POST-only route that reads the exact raw body, validates a bounded signature with `hmac.compare_digest`, resolves only an active configured repository, and persists one delivery ledger row.
3. Return after persistence. Do not normalize facts or write tasks. Use no caller-selected project/company as authority.
4. Run the focused tests, then `./scripts/verify`.

### Task 2: Native scheduled delivery processor

**Files:** Create `addons/project_agile_git/models/project_git_delivery_processor.py`; modify `data/project_agile_git_cron.xml`; test `addons/project_agile_git/tests/test_delivery_processing.py`.

1. RED: prove duplicate claims, a live lease, a transient exception, and a permanent malformed payload leave one ledger with correct state, attempt, retry, lease, and sanitized-error fields.
2. GREEN: configure a supported Odoo 19 `ir.cron` action that claims a bounded eligible batch with a tokenized expiring lease, processes in bounded transactions, calls `_commit_progress`, and leaves retries for later runs.
3. Verify concurrent claims, expired-lease recovery, rollback, and install/update/uninstall/reinstall. Do not add `queue_job` or assume an Odoo.sh queue runner.

### Task 3: Provider-neutral normalization

**Files:** Create normalized parser/services under `addons/project_agile_git/models/`; tests under `addons/project_agile_git/tests/`.

1. RED: fixture GitHub push, pull-request, and check deliveries produce repository-scoped branch/commit/PR/check facts; replay and out-of-order events converge.
2. GREEN: translate only provider payload fields into stable normalized fields. No provider objects or workflow meaning may leak into generic models.
3. Add list/form/search views with Project and multi-company record-rule checks. Run `./scripts/verify`.

### Task 4: Immutable Agile-key association

**Files:** Modify `project_git_fact.py`; test `test_task_association.py`.

1. RED: parse `ENG-142`, `[ENG-142]`, and `feature/ENG-142-short`; reject partial/malformed/cross-project keys and mutable task-name/database-id references.
2. GREEN: resolve within the repository project, store all explicit matches as immutable associations, and expose their source fact without chatter or state mutation.
3. Add non-admin and multiple-active-company tests. Run focused suite and canonical verification.

### Task 5: Read-only visibility and operational recovery

**Files:** Create views/security docs for facts and deliveries; update README/ADR if behavior changes.

1. Add manager-visible delivery state, attempts, retry timestamp, payload digest, retention deadline, and sanitized error fields. Do not show secrets or raw payloads to ordinary users.
2. Add a controlled retry action with server-side access/state checks. It must not create duplicate facts or workflow changes.
3. Verify install/update/uninstall/reinstall, native scheduled-batch recovery coverage, `./scripts/verify`, compileall, and a browser check without exposing a host port.

### Task 6: Separate workflow automation decision

Do not implement this in Milestone 6. A future ADR/card must define project-scoped rules, permissions, audit/dry-run behavior, idempotent effects, rollback, and adversarial authorization tests before any task-stage transition can occur.


## Verification and recovery

Run `python3 -m unittest tests.test_project_agile_git_contract -v`, focused Odoo tests,
and then `./scripts/verify`. The canonical verifier must cover clean install, targeted
upgrade, and dependency-safe uninstall/reinstall of the existing modules plus
`project_agile_git`; a later native processor card adds its own lease/retry coverage. Review the
complete diff, `git diff --check`, manifest/dependency/license decisions, and all changed
function complexity before review.

If Odoo scheduling or controller behavior differs from the cited exact source, retain the
failure evidence and revise the contract; do not substitute a private worker, a synchronous controller workflow, an unapproved queue runtime, or a
task-state side effect.
