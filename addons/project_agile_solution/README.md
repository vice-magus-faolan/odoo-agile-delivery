# Agile Solution Definition

Optional Odoo 19 Community addon for solution documents, immutable exact-revision
baselines, requirements, discovery context, native Task traceability and separate
approval/acceptance decisions. Depends only on `project_agile`; it does not make Scrum,
Git, sales or document-page integrations dependencies of the core addon.

See [the solution contract](../../docs/adrs/013-solution-definition-contract.md) and
[the user runbook](../../docs/runbooks/solution-rendering-and-acceptance.md) for the
existing lifecycle, authorization and rendering boundaries.

Run the repository's `./scripts/verify` for native discovery, installation, upgrade,
security, concurrency and lifecycle checks. Root tests supplement rather than replace
native execution.

Author: Odoo Agile Delivery. License: LGPL-3, as declared in `__manifest__.py`.
