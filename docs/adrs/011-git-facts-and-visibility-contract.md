# ADR-011: Milestone 6 Git Facts and Visibility Contract

## Status

Accepted — Milestone 6 contract and skeleton; provider ingress and processing remain deferred to follow-on cards.

## Context

The suite needs repository, branch, commit, pull-request, and check visibility without turning provider payloads into workflow policy. OCA Project 19.0 at `4bc441b839819603b06c9064db8f7a7fa97fdfb3` has no `project_git`, `project_github`, or `project_gitlab` addon. PR #1792 remains an open draft for 17.0 at `769d464e1fc1aff006e21f1668d47e4f13840138`; its provider/generic split is useful evidence, but its mutable task-name and database-id matching and direct task tags do not meet this suite's immutable Agile-key contract.

Odoo 19 at `c2957158eb2f7a341a874c3c58884c8a162ef59a` supplies normal `http.Controller`/`route` extension points and a supported `ir.cron` scheduler. Its scheduler isolates a cron execution transaction, uses bounded progress through `_commit_progress`, handles partial completion and failure rescheduling, and coordinates ready jobs with `FOR NO KEY UPDATE SKIP LOCKED`. This is the portable native execution boundary for the likely Odoo.sh target and other deployments.

## Decision

Create `project_agile_git`, an LGPL-3 Odoo-compatible private-suite module, not an OCA addon. It depends only on `project_agile`; `project_agile`, `project_scrum`, analytics, document-page bridges, and `project_agile_ui` remain independently installable. The upstream contribution path is a design/19.0 contribution proposal rather than a fork or forward-port of PR #1792.

The provider-neutral records are repository, authenticated delivery ledger, branch, commit, pull request, check, and task association. A repository is one provider identity mapped to one Agile project and company. Provider IDs are strings and facts are keyed by repository plus immutable provider identifiers. Delivery idempotency is a database constraint on `(repository_id, provider_delivery_id)`; every later processor must be idempotent against that ledger.

Task association accepts explicit immutable `agile_key` references only. The grammar is an uppercase project key followed by a positive decimal number: `ENG-142`. It may occur as a standalone token, `[ENG-142]`, `ENG-142: subject`, or inside a branch token such as `feature/ENG-142-short-description`; boundary matching must reject partial keys. A future parser preserves all explicit keys, resolves them only within the repository's configured project, and records an immutable association. It must not use mutable task names or database IDs. Explicit references outrank any future heuristic; this milestone defines no heuristic.

A future provider adapter owns a narrow, authenticated ingress route. It validates provider identity, active repository, content type, bounded raw body, exact-body signature, event type, and delivery ID; it then writes one ledger row and returns promptly. It does not normalize facts, associate tasks, post chatter, call a provider, or mutate workflow state in the request transaction. Payload storage is digest-only by default; any redacted bounded excerpt, retention deadline, retries, attempt count, next retry, sanitized error summary, and expiring processing lease are ledger fields. Secrets are system-administrator-only and never belong in read APIs, exports, chatter, errors, reprs, or logs.

The later processor is an Odoo 19 `ir.cron` scheduled action, not a request-thread action and not a `queue_job` runtime. It must claim a bounded eligible batch using a database-backed lease with a random token and expiry; concurrent workers may claim neither a live lease nor the same delivery. Each delivery transition is idempotent and records attempts, next retry, sanitized error, and lease release in the same bounded transaction. The cron reports bounded progress using `_commit_progress`, leaves unfinished work for another scheduled run, and treats expired leases as recoverable retries. Failures must remain operator-visible and must never produce a task-stage change. A future implementation must isolate the narrow lock/claim SQL, parameterize it through Odoo's `SQL` wrapper, and test concurrent claim, expiry recovery, retry exhaustion, and rollback.

Facts are project- and company-scoped. ACLs plus global multi-company rules and existing Project visibility govern reads. All relationship checks run server-side; caller context, delivery payload project fields, and active company are never authority.

Fact ingestion and workflow automation policy are separate. `PR merged`, branch creation, or a successful check have no intrinsic task-stage meaning. A later, project-scoped opt-in automation addon requires independent approval, dry-run/audit behavior, and idempotent rule execution.

## Queue Job Decision

Reject OCA `queue_job` as a required or production runtime dependency for Milestone 6. Its 19.0 `queue_job` manifest at `bc1d8854d0bf5cd35c33e00c2f5af0cec05c09f2` is LGPL-3, Mature, and depends on `mail`, `base_sparse_field`, and `web`, but its regular jobrunner is not accepted as the Odoo.sh production execution model. The current Alpha/non-installable Odoo 19 cron-runner alternative is also not an acceptable dependency. A separately approved, self-hosted-only `queue_job` adapter may be evaluated later; it cannot alter the base addon, the portable processor contract, or the canonical verifier.

## Consequences

The skeleton supplies no controller, provider adapter, webhook registration, payload parser, queue enqueue, fact synchronization, scheduled-action data, or task workflow mutation. Later cards must add signed GitHub fixture ingress first, then the native scheduled batch processor, normalization and read-only visibility, and only then consider policy automation. Every schema/security change must run clean install, update, and dependency-safe uninstall/reinstall through `./scripts/verify`.

## Sources

- OCA Project 19.0 tree: https://github.com/OCA/project/tree/19.0
- OCA Project PR #1792: https://api.github.com/repos/OCA/project/pulls/1792
- OCA Queue `queue_job` manifest (rejected base-runtime candidate): https://raw.githubusercontent.com/OCA/queue/bc1d8854d0bf5cd35c33e00c2f5af0cec05c09f2/queue_job/__manifest__.py
- Odoo 19 HTTP source: https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/http.py
- Odoo 19 scheduled-action source: https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/addons/base/models/ir_cron.py
