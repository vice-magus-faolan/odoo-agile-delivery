# ADR-011: Git Facts and Visibility Contract

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
scheduler and ORM persistence APIs. Its scheduled work is a portable Odoo.sh-compatible
runtime boundary; it must not be replaced by request-thread processing or a mandatory
external runner.

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
manager-visible diagnostic without retaining the conflicting body. The private
configuration lookup uses a context-independent, narrowly elevated ORM search for the
active provider identity; elevation does not authenticate the webhook. Mismatch
accounting uses ordinary ORM writes, including optional provenance fencing. Competing
updates conflict under repeatable read and escape to the native whole-request retry; a
savepoint alone does not refresh a stale snapshot.

The native scheduled processor claims at most 20 eligible GitHub deliveries per run. It
searches one bounded FIFO window ordered by receipt time and ID, uses Odoo 19
`try_lock_for_update(limit=1)` to skip locked rows, and writes lease state through the
ORM. If the entire window is locked, claiming stops and defers work to a later run. With
optional Git policy installed, only lease/attempt/retry bookkeeping on queued, retryable
or processing deliveries without a settlement time can avoid the shared provenance
fence. This does not make them trusted evidence: settlement, identity/payload changes,
extra fields and processed or mixed recordsets remain fenced, and every write retains
native ACLs and the ORM override chain.

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
Retention selects only repository identity and event-specific normalizer inputs,
excluding unrelated provider metadata, and scrubs recognized credential-shaped scalar
text, including authorization bearer values and common GitHub/GitLab token forms. The
projection extracts explicit task keys from the entire credential-scrubbed commit
message and PR body at ingress. It retains only distinct keys and a bounded rejection
reason (`invalid_key` or `too_many_keys`), plus the first 255 characters of each
scrubbed commit message for display. Extraction precedes display truncation, so trailing
keys are not lost. Both ingress and the normalizer share one parser and validate compact
metadata shape, cardinality, key syntax/length, uniqueness, reason and excerpt bounds.
Provider-supplied metadata is never accepted as precomputed key authority. Previously
delivered retained text shapes remain processable through the same association path.

The projection has explicit field limits, not a 4,096-character aggregate cap: ordinary
text/ref/title/name fields 4,096 characters; identifiers/SHAs 128 (PR number 64);
state-like scalars 32; timestamps 64; keys 128 with at most 20 distinct keys per source.
More than 20 distinct keys rejects the field's associations with `too_many_keys`, not
partial linking. No valid key but a key-like token retains the `invalid_key` decision.
Malformed or oversized required fields fail without retaining a partial payload.

A push retains its first 100 commit entries from GitHub's at-most-2,048 collection and
the exact omitted count. The scheduled processor still records the independently
retained head SHA and timestamp with existing ordering rules. It persists both
`omitted_commit_count` and `commit_omission_reason` on the delivery; successful
settlement, reprocessing, exact HTTP replay and payload cleanup do not clear them. This
preserves branch visibility without pretending that omitted commit facts or links were
processed. A branch-only policy would unnecessarily discard the first 100 usable commit
observations.

These bounds yield fewer than 900,000 ASCII JSON characters for any supported
projection, even allowing 12 escape characters per non-BMP source character: each of 100
commit entries fits within 8,200 characters (20 ASCII keys, excerpt, ID, timestamp and
JSON structure), with fewer than 54,000 top-level characters. PR and check projections
are smaller. This is a conservative derived storage maximum, not a new generic rejection
threshold. The exact-body digest, 256 KiB HTTP body limit and bounded JSON nesting
remain independent of this projection. This is defense in depth, not permission to store
arbitrary secrets: unmatched credential formats remain residual risk and redacted
excerpts stay System Administrator-only. Raw payloads and webhook secrets are never
exposed through ordinary reads, logs, errors, exports, or chatter. Bounded retention
cleanup selects expired processed/discarded excerpts by provider, terminal state,
payload presence and expiry, then clears the selected batch with one ORM write,
preserving the ledger and recording the purge timestamp. These writes retain native
access checks, inherited hooks and conservative policy evidence fencing. A concurrent
state change causes the write to fail under repeatable read; the next scheduled run
selects eligible work in a fresh transaction.

Task association accepts only explicit immutable keys matching `ENG-142`-style uppercase
project keys with a positive decimal suffix. Tokens must be delimited from every Unicode
word character, so embedded lowercase, underscore, and Unicode-word text is not
authority. Bounded sources are push branch refs and commit messages; pull-request title,
body, and head ref; and check-run name/output title. Key extraction and its
association/audit decision always use the current delivery's validated source key
evidence (or previously retained source text), even if fact ordering retains a newer
stored observation. Exact project-local task key matches create immutable association
facts. Any non-local key is indistinguishable from an unknown key in the
repository-company audit; it never triggers a cross-company or cross-project existence
probe. Archived, invalid, duplicate, or excessive references create immutable audit
decisions and never cause task, Sprint, follower, message, or stage writes. No task
names, database IDs, payload project/company fields, context, or heuristic match is
authority.

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

Reject OCA `queue_job` as a required or production runtime dependency for Git facts. Its
19.0 manifest is mature and LGPL-3 but has a jobrunner model not accepted as the
portable Odoo.sh target. A separately approved self-hosted adapter may be evaluated
later; it cannot alter the core schema, native processing contract, or canonical
verifier.

## Consequences

Connector facts are observations, not evidence that an Odoo task is complete. The
connector supplies no workflow automation, configurable task policy, provider polling,
or outbound provider operation. The separately optional addon in ADR-012 owns approved
policy effects; receipt/normalization never writes Tasks. Every schema/security/cron
change requires clean install, update, and dependency-safe uninstall/reinstall
verification.

## Sources

- OCA Project 19.0 tree: https://github.com/OCA/project/tree/19.0
- OCA Project PR #1792: https://api.github.com/repos/OCA/project/pulls/1792
- Odoo 19 scheduled actions:
  https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/addons/base/models/ir_cron.py
- Odoo 19 native transaction retry:
  https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/service/model.py
- Odoo 19 repeatable-read cursor and savepoints:
  https://raw.githubusercontent.com/odoo/odoo/c2957158eb2f7a341a874c3c58884c8a162ef59a/odoo/sql_db.py

## Historical environment merge projection

The optional Git facts addon owns `project.git.environment.branch`: one active or
archived exact short branch mapping per environment/repository. Both links must share an
Agile Project and company. Configuration reuses the native Project-administrator plus
Project-write boundary from ADR-015; ownership fields are derived and protected. Native
caller-bound environment and repository rule subqueries protect mapping visibility.
Copies do not inherit mappings.

Task evidence is a nonstored projection, not a second status ledger. One batched
caller-context join resolves exact `(repository, provider PR ID)` associations. The sole
positive predicate requires merged state, merge time, known ordering and exact mapped
target branch. Counts, environment tags, details, PR navigation and searches use this
predicate. Public reads refresh the projection to account for current record rules;
ordinary dependency triggers invalidate fact and configuration changes. No elevated
result contributes to a projection.

Any qualifying linked PR establishes historical partial progress. UAT/no-production
search requires the selected visible active environment and a production mapping in the
same Project, and excludes any visible production positive across all mapped
repositories. Its negative is qualified visible evidence, not completeness or code
absence. Current mappings reinterpret retained observations. Reverts and branch
operations do not establish current code placement or deployment.

Known-only confidence is intentional: the retained normalizer can mark an equal-time
conflict ambiguous and then an older event stale without reconciling its values. Stale
therefore cannot restore a positive, including production exclusion. A strictly newer
unambiguous observation can restore confidence; harmless late events may temporarily
hide valid positives. No new confidence storage, source ordering semantics, scheduler or
normalizer behavior is added. Retained normalized facts survive terminal payload purge;
missing processing is not inferred. Manual environment status, audit and
configuration/data-import lifecycle remain independent under ADR-015. This keeps a
future mapping or confidence-rule change in one projection owner without coupling core
Agile to Git.
