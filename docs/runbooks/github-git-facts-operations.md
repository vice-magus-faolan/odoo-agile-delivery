# GitHub Git-facts operator runbook

## Scope and safety boundary

This runbook covers the `project_agile_git_github` adapter only. A delivery is an
immutable observation: it never changes a task stage, Sprint, follower, message,
or external GitHub state. Use the standard Odoo UI; do not edit PostgreSQL rows,
disable route authentication, or replay a request by changing a database record.

## Rotate a repository webhook secret

1. As a System Administrator, open Git Repositories and select the exact active
   GitHub repository by provider repository ID and company.
2. Replace the ingress-only webhook secret and save. Verify the repository remains
   active and its canonical URL still names the intended public GitHub repository.
3. In the authorized GitHub administration workflow, update the matching webhook
   with the same new secret. Do not create a second repository row for the same
   provider repository ID.
4. Send an approved fixture/test delivery only in the authorized non-production
   environment. Confirm one queued delivery has the expected repository, payload
   digest, and delivery ID; do not inspect, copy, or export a raw payload.
5. Retain the old secret only for the provider-side overlap period approved by the
   operator, then remove it there. The Odoo route returns generic failures and
   deliberately does not reveal which secret or repository was rejected.

## Disable a repository safely

Project Managers disable ingress by archiving the repository record. The webhook
then rejects future deliveries without exposing configuration detail. Archiving
never deletes existing deliveries, facts, association audits, or failed evidence.
Do not remove the repository to stop delivery.

## Diagnose delivery and retry

Project Managers open the repository's Deliveries action and diagnose using the
repository, provider delivery ID, state, attempt count, payload SHA-256, timestamps,
and bounded error summary. The redacted excerpt and webhook secret are restricted
to System Administrators and must not be copied to chatter, exports, tickets, or
user-facing errors.

`queued` and `retryable` records are owned by the scheduled processor. `processing`
records have an expiring lease and are recovered automatically. `failed` and
`discarded` records are terminal diagnostics. After correcting the configuration
that caused a terminal error, a Project Manager may use **Reprocess** only when a
redacted retained payload remains available; the operation requeues the same
ledger row and fact/association uniqueness makes it idempotent. A digest-only or
privacy-truncated delivery cannot be safely reconstructed and is intentionally
not reprocessable.

## Retention and cleanup

For `redacted_excerpt`, the adapter stores a bounded, credential-scrubbed JSON
excerpt for 30 days. Oversized excerpts are never sliced into invalid JSON: the
signed delivery remains terminal with its digest, size, and bounded diagnostic,
but no raw or partial payload is retained. The daily cleanup cron purges only an
expired excerpt from `processed` or `discarded` GitHub deliveries. It preserves the
ledger row, company, digest, size, processing result, facts, and association audits,
and records `Retained Payload Purged At`. It never purges `queued`, `processing`,
`retryable`, or `failed` evidence.

To investigate retention, filter Deliveries by company, state, and retention
expiry/purge timestamp. If cleanup is delayed, restore the normal scheduled action
through Odoo administration and investigate the cron log; do not run ad-hoc SQL or
manually clear payload fields.

## Rollback

Disable ingress by archiving each affected repository, then allow already leased
work to settle or expire. Roll back the adapter only through the repository's
verified Odoo module lifecycle: take an application-consistent backup, use the
standard module-management flow, and run the documented clean install, upgrade,
and dependency-safe uninstall/reinstall verification. No rollback step requires a
live webhook change, direct database edit, or authentication bypass.
