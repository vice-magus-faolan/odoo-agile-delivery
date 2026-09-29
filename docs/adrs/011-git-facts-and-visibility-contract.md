# ADR-011: Milestone 6 Git Facts and Visibility Contract

## Status

Accepted — provider-neutral contract, signed GitHub ingress, and portable asynchronous normalization.

## Context

The suite needs repository, branch/ref, commit, pull-request, and check visibility without turning provider payloads into workflow policy. OCA Project 19.0 at `4bc441b839819603b06c9064db8f7a7fa97fdfb3` has no `project_git`, `project_github`, or `project_gitlab` addon. OCA Project PR #1792 remains an open 17.0 draft; its provider/generic split is useful evidence, but mutable task-name/database-id matching is not acceptable here.

Odoo 19 at `c2957158eb2f7a341a874c3c58884c8a162ef59a` supplies the supported `ir.cron` scheduler and `SQL` wrapper. Its scheduled work is a portable Odoo.sh-compatible runtime boundary; it must not be replaced by request-thread processing or a mandatory external runner.

## Decision

`project_agile_git` remains an LGPL-3 Odoo-compatible private-suite module depending only on `project_agile`; core Agile, Scrum, analytics, document bridges, and planning UI remain independently installable. `project_agile_git_github` is the optional GitHub adapter.

A repository is one globally unique provider repository identity mapped to one Agile project and company. Durable delivery identity is `(repository_id, provider_delivery_id)`. Repository IDs, pull-request IDs, check-run IDs, commit SHAs, source timestamps, last-seen timestamps, and delivery provenance are persisted. GitHub push payloads do not expose an immutable branch object ID: the source ref is recorded as an explicit provider ref observation, and a rename is never guessed to be the same branch.

The GitHub webhook validates an exact raw-body HMAC before making one ledger write and returning. Receipt is persistence-only: it enqueues the ledger state but does not normalize facts, associate tasks, mutate workflow, call GitHub, or decide caller authority. Duplicate reception remains one row by database constraint.

The native scheduled processor claims at most 20 eligible GitHub deliveries with parameterized `SQL`, `FOR UPDATE SKIP LOCKED`, a random five-minute lease token, and an expiring processing lease. Each delivery settles in a savepoint: facts and the processed state commit together, while malformed payloads roll back facts and dead-letter the ledger row. Transient failures retry with bounded exponential backoff and become failed after five attempts. Expired leases are eligible again. `ir.cron._commit_progress` commits one settled item at a time and leaves remaining work for a later run.

The supported GitHub subset is `push`, `pull_request`, and `check_run`. Missing optional push `head_commit`/`commits` and check-run `output` are treated as absent source material; when present, those containers must be a JSON object, list, and JSON object respectively, or the delivery is terminally malformed. Newer source timestamps replace current branch/PR/check values; older observations do not regress them, and absent/equal-conflicting timestamps are marked ambiguous rather than guessed. Unsupported delivery types are terminally `discarded` with a diagnostic.

Default payload retention is digest-only. Such a delivery is deliberately non-normalizable and terminally visible; a repository must select `redacted_excerpt` before receipt to retain the bounded credential-scrubbed data needed for the supported parser. Raw payloads and webhook secrets are never exposed through ordinary reads, logs, errors, exports, or chatter.

Task association accepts only explicit immutable keys matching `ENG-142`-style uppercase project keys with a positive decimal suffix. Bounded sources are push branch refs and commit messages; pull-request title, body, and head ref; and check-run name/output title. Key extraction and its association/audit decision always use the current delivery’s validated source text, even if fact ordering retains a newer stored observation. Exact project-local task key matches create immutable association facts. Unknown, wrong-project, archived, invalid, duplicate, or excessive references create immutable audit decisions and never cause task, Sprint, follower, message, or stage writes. No task names, database IDs, payload project/company fields, context, or heuristic match is authority.

Facts and audit records remain repository, project, and company scoped through ORM validation, ACLs, multi-company rules, and Project visibility. Reprocess is a Project Manager-only server-side action for a terminal GitHub delivery; it requeues the existing ledger row, and fact/association uniqueness makes replay idempotent.

## Queue Job Decision

Reject OCA `queue_job` as a required or production runtime dependency for Milestone 6. Its 19.0 manifest is mature and LGPL-3 but has a jobrunner model not accepted as the portable Odoo.sh target. A separately approved self-hosted adapter may be evaluated later; it cannot alter the core schema, native processing contract, or canonical verifier.

## Consequences

Connector facts are observations, not evidence that an Odoo task is complete. No workflow automation, configurable task policy, provider polling, or outbound provider operation exists in this milestone. Every schema/security/cron change requires clean install, update, and dependency-safe uninstall/reinstall verification.

## Sources

- OCA Project 19.0 tree: https://github.com/OCA/project/tree/19.0
- OCA Project PR #1792: https://api.github.com/repos/OCA/project/pulls/1792
- Odoo 19 scheduled actions: https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/addons/base/models/ir_cron.py
- Odoo 19 SQL wrapper: https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/tools/sql.py
