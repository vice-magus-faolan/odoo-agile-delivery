# ADR-011: Milestone 6 Git Facts and Visibility Contract

## Status

Accepted — provider-neutral contract, signed GitHub ingress, and portable asynchronous
normalization.

## Context

The suite needs repository, branch/ref, commit, pull-request, and check visibility
without turning provider payloads into workflow policy. OCA Project 19.0 at
`4bc441b839819603b06c9064db8f7a7fa97fdfb3` has no `project_git`, `project_github`, or
`project_gitlab` addon. OCA Project PR #1792 remains an open 17.0 draft; its
provider/generic split is useful evidence, but mutable task-name/database-id matching is
not acceptable here.

Odoo 19 at `c2957158eb2f7a341a874c3c58884c8a162ef59a` supplies the supported `ir.cron`
scheduler and `SQL` wrapper. Its scheduled work is a portable Odoo.sh-compatible runtime
boundary; it must not be replaced by request-thread processing or a mandatory external
runner.

## Decision

`project_agile_git` remains an LGPL-3 Odoo-compatible private-suite module depending
only on `project_agile`; core Agile, Scrum, analytics, document bridges, and planning UI
remain independently installable. `project_agile_git_github` is the optional GitHub
adapter.

A repository is one globally unique provider repository identity mapped to one Agile
project and company. Durable delivery identity is
`(repository_id, provider_delivery_id)`. Repository IDs, pull-request IDs, check-run
IDs, commit SHAs, source timestamps, last-seen timestamps, and delivery provenance are
persisted. GitHub push payloads do not expose an immutable branch object ID: the source
ref is recorded as an explicit provider ref observation, and a rename is never guessed
to be the same branch.

The GitHub webhook bounds body size and JSON nesting before parsing, validates an exact
raw-body HMAC before making one ledger write, and returns promptly. Receipt is
persistence-only: it enqueues the ledger state but does not normalize facts, associate
tasks, mutate workflow, call GitHub, or decide caller authority. Duplicate reception
remains one row by database constraint only when the event type, body digest, and body
size exactly match. A mismatched replay is rejected and increments a bounded
manager-visible diagnostic without retaining the conflicting body.

The native scheduled processor claims at most 20 eligible GitHub deliveries per run. It
searches FIFO windows ordered by receipt time and ID, uses Odoo 19
`try_lock_for_update(limit=1)` to skip locked rows, and writes lease state through the
ORM. A fully locked window advances by its last FIFO key rather than hiding later
eligible work. With optional Git policy installed, only lease/attempt/retry bookkeeping
on queued, retryable or processing deliveries without a settlement time can avoid the
shared provenance fence. This does not make them trusted evidence: settlement,
identity/payload changes, extra fields and processed or mixed recordsets remain fenced,
and every write retains native ACLs and the ORM override chain.

Each claim receives an expiring processing lease with a random five-minute token. Each
delivery settles in a savepoint: facts and the processed state commit together, while
malformed payloads roll back facts and dead-letter the ledger row. Transient failures
retry with bounded exponential backoff and become failed after five attempts. Expired
leases are eligible again. `ir.cron._commit_progress` commits one settled item at a time
and leaves remaining work for a later run.

The supported GitHub subset is `push`, `pull_request`, and `check_run`. Missing optional
push `head_commit`/`commits` and check-run `output` are treated as absent source
material; when present, those containers must be a JSON object, list, and JSON object
respectively, or the delivery is terminally malformed. Newer source timestamps replace
current branch/PR/check values; older observations do not regress them, and
absent/equal-conflicting timestamps are marked ambiguous rather than guessed.
Unsupported delivery types are terminally `discarded` with a diagnostic.

Default payload retention is digest-only. Such a delivery is deliberately
non-normalizable and terminally visible; a repository must select `redacted_excerpt`
before receipt to retain the bounded JSON projection needed for the supported parser.
Retention removes sensitive-key values and recognized credential-shaped scalar text,
including authorization bearer values and common GitHub/GitLab token forms. This is
defense in depth, not permission to store arbitrary secrets: unmatched credential
formats remain residual risk and redacted excerpts stay System Administrator-only. Raw
payloads and webhook secrets are never exposed through ordinary reads, logs, errors,
exports, or chatter.

Task association accepts only explicit immutable keys matching `ENG-142`-style uppercase
project keys with a positive decimal suffix. Tokens must be delimited from every Unicode
word character, so embedded lowercase, underscore, and Unicode-word text is not
authority. Bounded sources are push branch refs and commit messages; pull-request title,
body, and head ref; and check-run name/output title. Key extraction and its
association/audit decision always use the current delivery’s validated source text, even
if fact ordering retains a newer stored observation. Exact project-local task key
matches create immutable association facts. Any non-local key is indistinguishable from
an unknown key in the repository-company audit; it never triggers a cross-company or
cross-project existence probe. Archived, invalid, duplicate, or excessive references
create immutable audit decisions and never cause task, Sprint, follower, message, or
stage writes. No task names, database IDs, payload project/company fields, context, or
heuristic match is authority.

Facts and audit records remain repository, project, and company scoped through ORM
validation, ACLs, multi-company rules, and Project visibility. Reprocess is a Project
Manager-only server-side action for a terminal GitHub delivery; it requeues the existing
ledger row, and fact/association uniqueness makes replay idempotent.

Read-only Project, Task, repository, and fact views use standard Odoo actions. Project
and Task counters are current-user grouped reads; Task fact actions re-resolve immutable
association facts under the current caller's ACLs and record rules. The canonical
repository URL is HTTPS and restricted to the public provider host (`github.com`,
`gitlab.com`, or `bitbucket.org`); GitHub fact links are derived under that configured
repository URL, never copied from a provider payload. Connector facts remain
observations, not evidence that an Odoo task is complete.

## Queue Job Decision

Reject OCA `queue_job` as a required or production runtime dependency for Milestone 6.
Its 19.0 manifest is mature and LGPL-3 but has a jobrunner model not accepted as the
portable Odoo.sh target. A separately approved self-hosted adapter may be evaluated
later; it cannot alter the core schema, native processing contract, or canonical
verifier.

## Consequences

Connector facts are observations, not evidence that an Odoo task is complete. M6 itself
supplies no workflow automation, configurable task policy, provider polling, or outbound
provider operation. The separately optional M7 addon in ADR-012 owns approved policy
effects; M6 receipt/normalization never writes Tasks. Every schema/security/cron change
requires clean install, update, and dependency-safe uninstall/reinstall verification.

## Sources

- OCA Project 19.0 tree: https://github.com/OCA/project/tree/19.0
- OCA Project PR #1792: https://api.github.com/repos/OCA/project/pulls/1792
- Odoo 19 scheduled actions:
  https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/addons/base/models/ir_cron.py
- Odoo 19 SQL wrapper:
  https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/tools/sql.py
