# Agile Git Facts

`project_agile_git` is the provider-neutral Milestone 6 foundation for repository, delivery-ledger, branch, commit, pull-request, check, and immutable Agile-key association records.

It depends only on `project_agile`. It intentionally has no controller, provider SDK, `queue_job` dependency, custom JavaScript, workflow automation, or task-stage mutation. A later provider adapter owns authenticated delivery ingestion; a later Odoo 19 `ir.cron` processor owns bounded leased batches and retry visibility; a later automation module owns workflow policy.

The repository configuration is project- and company-scoped. Webhook secrets are system-administrator-only fields and must never appear in ordinary project reads, exports, chatter, errors, or logs. Facts are visible only through Project access plus the global multi-company rule; delivery payload retention defaults to digest-only.
