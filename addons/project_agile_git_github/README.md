# Agile GitHub Delivery Ingress

`project_agile_git_github` accepts only bounded `application/json` GitHub webhook
deliveries with an exact-body `X-Hub-Signature-256` HMAC SHA-256, an event header, and a
delivery ID. The adapter derives repository scope only from the signed payload's GitHub
repository ID; it ignores payload project/company fields and performs no fact, task,
chatter, or workflow mutation in the request transaction.

A valid delivery creates at most one durable `project.git.delivery`, using the core
`(repository_id, provider_delivery_id)` database constraint for replay and
concurrent-delivery safety. Receipt transitions the ledger row to `queued`; the native
Odoo 19 `ir.cron` action subsequently claims it through a random, expiring
PostgreSQL-backed lease. No `queue_job` runtime is required, so the processor remains
portable to Odoo.sh.

The processor currently supports GitHub `push`, `pull_request`, and `check_run` events.
It writes provider-neutral repository-scoped facts only. Every retry, unsupported event,
malformed payload, exhausted retry, and explicit Agile-key association decision remains
visible in the durable ledger or association audit. Processing never updates a task
stage, Sprint, followers, messages, or other workflow state.

Raw payloads are never logged. Default core retention is digest-only, which
intentionally makes a delivery non-normalizable and terminally visible. Enable
`redacted_excerpt` on a repository before receipt to retain a credential-scrubbed,
bounded payload suitable for the supported asynchronous normalization subset. Explicit
keys are parsed only from documented bounded fields: push branch refs and commit
messages; pull-request title, body, and head branch; and check-run name/output title. No
task names, database IDs, or heuristics are used.
