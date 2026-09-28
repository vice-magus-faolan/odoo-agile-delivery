# Agile Planning UI

`project_agile_ui` is the optional Milestone 5 Odoo 19 frontend boundary for
the Agile Sprint planning workspace. It depends only on `project_scrum`, so
`project_agile` and `project_scrum` remain independently usable without it.

## Current skeleton

This milestone installs an empty Python addon plus an Odoo-native Hoot fixture
in `web.assets_unit_tests`. It intentionally has no models, controllers,
security records, views, menus, client actions, backend asset, data loading, or
business-rule implementation. It does not change ordinary Project views or
Kanban.

The accepted contract is [ADR-010](../../docs/adrs/010-advanced-agile-ui-contract.md).
A later read-only board will use a scoped server snapshot and an additive client
action; it will not use a generic browser ORM interface or a global Project
Kanban override.

## Capability boundary

- No drag/drop, assignment, backlog reordering, Sprint lifecycle mutation, or
  any other write behavior.
- No Git indicators or Git integration.
- No Task-document controls and no dependency on unmerged
  `document_page_project_task` work.
- No duplicated task, Sprint, scope-history, company, or access-control rules.

## Verification

The repository `./scripts/verify` clean-installs, upgrades, and reinstalls the
addon with the existing Community modules against disposable databases. The
frontend fixture is declared in Odoo 19's native `web.assets_unit_tests` bundle;
run it through Odoo's standard frontend test runner when validating browser
asset discovery. Do not add a separate npm/Jest/QUnit harness.
