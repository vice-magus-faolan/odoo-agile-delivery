# Agile Git Policy Contract

Optional LGPL-3, Odoo 19 Community-compatible private-suite skeleton depending
only on `project_agile_git`. It is not OCA-conformant tooling and does not require
GitHub, Scrum, queue_job, provider APIs, or an external daemon.

The accepted Milestone 7 contract is [ADR-012](../../docs/adrs/012-git-workflow-policy-contract.md).
This first slice installs only an append-only, company/project-scoped synthetic
audit fixture. It has no production producer, rule configuration, activation,
evaluator, cron, task override, or task mutation. Installation is therefore
intrinsically disabled; the only fixture mode is `dry_run`. Fixture receipts are
not trusted observations, dry-run decisions, or consumed apply markers.

Project users can read visible receipts; nobody has create/write/delete ACLs.
The ORM rejects non-superuser authors even if another addon grants an ACL.
Trusted internal fixture setup may create a row, but even superuser cannot
write/unlink one through the model. Reasons are a finite selection, not provider
text or exceptions. No payload, secret, or task description is stored.

Run `env -u COMPOSE_PROJECT_NAME ./scripts/verify` for independent optional
installation first, then the seven-module clean install, targeted upgrade, and
dependency-safe uninstall/reinstall, including imported Odoo fixture tests.
Existing Git observations stay observation-only with this skeleton installed.
Production policy activation remains a separate future operator-approved effect.
