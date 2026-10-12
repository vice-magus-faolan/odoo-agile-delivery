# `project_agile` Milestone 1 Design

## Boundary

Beneficiary: delivery teams that need Agile semantics while retaining Odoo Project. The
module depends only on `project`, is opt-in per project, and never introduces a parallel
issue model. Native `project.task.parent_id`, `child_ids`, and dependencies remain
authoritative. Scrum is isolated to a future `project_scrum` module.

Non-goals: Scrum lifecycle, analytics, Knowledge, Git providers, OWL UI, Jira migration,
a custom wiki, and a custom dependency model.

## Module tree

```text
addons/project_agile/
  __init__.py
  __manifest__.py
  README.md
  data/
  models/
  security/
  tests/
  views/
docs/adrs/001-work-item-key-generation.md
docs/adrs/002-configurable-item-type-hierarchy.md
```

The module now installs its data, access rules, and inherited Odoo views with the
reviewed domain contract. It does not replace a global Project or Task view; ordinary
projects remain outside the Agile action domain and conditional fields.

## Current domain contract

`project.project` includes:

- `agile_enabled`: per-project opt-in switch.
- `agile_key`: validated, unique namespace for generated work-item keys.
- `agile_default_item_type_id`: optional default configuration.
- `agile_estimation_method`: narrow MVP selection (`none`, `fibonacci`).

`project.task` includes:

- `agile_item_type_id`: configuration-backed work-item type.
- `agile_key`: immutable, indexed generated identifier.
- `agile_story_points`: numeric estimation value.
- `agile_acceptance_criteria`: dedicated rich-text acceptance criteria.
- `agile_backlog_sequence`: explicit backlog ordering, not creation date.

`project.agile.item.type` is the one new model justified by a persistent,
customer-configurable type-policy invariant. It exposes `name`, `code`, `sequence`,
`active`, and canonical `allowed_child_type_ids`. Do not add stored computed fields, a
duplicate allowed-parent relation, or other models unless a new invariant requires one.

## Constraints and sequence strategy

See ADR-001 and ADR-002. In brief: project-local `ir.sequence` allocation gives
concurrency-safe immutable keys; a database uniqueness constraint backs task keys;
native hierarchy is constrained at the model layer for Agile type policy and project
isolation. Non-Agile projects receive no key or policy enforcement.

## Security model

Item-type configuration has an explicit ACL: existing Project managers may read, create,
update, and delete configuration; Project users may only read it. The menu is
manager-only. Existing Project task access rules remain authoritative for task fields;
no broad ACL bypasses native task record rules. Employee and manager ORM paths are
covered by tests.

## Initial ordinary views and actions

The module uses inherited standard Odoo Project and Task views plus standard list,
Kanban, and search views. It adds a manager-only item-type configuration action and a
Product Backlog action scoped to Agile work and explicitly ordered by
`agile_backlog_sequence`. It introduces no Scrum fields or custom JavaScript. Exact Odoo
19 view external IDs were inspected in the target image before the view inheritance was
added.

## Test plan

The module contract and Odoo tests cover clean installation, Agile key
generation/uniqueness/stability, cross-project move rejection, ordinary-project
isolation, valid and invalid type policy, native cycle handling, story-point validation,
type reconfiguration, manager/employee access, seeded configuration, stable view/action
XML IDs, and explicit backlog ordering. Focused tests and `./scripts/verify` run against
disposable verification databases. Recovery is a clean database/container rerun; no
persistent volume is deleted.

## Open questions

- Validate final Odoo 19 field and view naming against the exact target source.
- Resolve whether a missing type is permitted during Agile project onboarding.
- Decide key padding only after a consumer demonstrates a need.
