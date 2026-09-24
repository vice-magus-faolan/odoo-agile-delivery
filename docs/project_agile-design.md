# `project_agile` Milestone 1 Design

## Boundary

Beneficiary: delivery teams that need Agile semantics while retaining Odoo
Project. The module depends only on `project`, is opt-in per project, and never
introduces a parallel issue model. Native `project.task.parent_id`, `child_ids`,
and dependencies remain authoritative. Scrum is isolated to a future
`project_scrum` module.

Non-goals: Scrum lifecycle, analytics, Knowledge, Git providers, OWL UI, Jira
migration, a custom wiki, and a custom dependency model.

## Module tree

```text
addons/project_agile/
  __init__.py
  __manifest__.py
  README.md
  models/
  security/
  tests/
  views/
docs/adrs/001-work-item-key-generation.md
docs/adrs/002-configurable-item-type-hierarchy.md
```

The scaffold intentionally creates only importable packages and a manifest. It
contains no data records, access rules, or views before their backing model
contracts exist; this keeps clean installation reversible and avoids exposing a
half-configured UI.

## Reviewed domain contract for the next implementation slice

`project.project` will gain:

- `agile_enabled`: per-project opt-in switch.
- `agile_key`: validated, unique namespace for generated work-item keys.
- `agile_default_item_type_id`: optional default configuration.
- `agile_estimation_method`: narrow MVP selection (`none`, `fibonacci`).

`project.task` will gain:

- `agile_item_type_id`: configuration-backed work-item type.
- `agile_key`: immutable, indexed generated identifier.
- `agile_story_points`: numeric estimation value.
- `agile_acceptance_criteria`: dedicated rich-text acceptance criteria.
- `agile_backlog_sequence`: explicit backlog ordering, not creation date.

`project.agile.item.type` is the one new model justified by a persistent,
customer-configurable type-policy invariant. It will expose `name`, `code`,
`sequence`, `active`, and canonical `allowed_child_type_ids`. Do not add stored
computed fields, a duplicate allowed-parent relation, or other models unless a
new invariant requires one.

## Constraints and sequence strategy

See ADR-001 and ADR-002. In brief: project-local `ir.sequence` allocation gives
concurrency-safe immutable keys; a database uniqueness constraint backs task
keys; native hierarchy is constrained at the model layer for Agile type policy
and project isolation. Non-Agile projects receive no key or policy enforcement.

## Security model

No new model exists in this scaffold, so no premature ACL or menu is installed.
In the domain slice, item-type and Agile project configuration must be limited to
existing Project managers (or a documented dedicated group if a real separation
is needed). Existing Project access rules remain authoritative for task fields;
no broad ACL should bypass record rules. The implementation must add explicit
access CSV/rules only with the model they secure and test employee/manager ORM
paths.

## Initial ordinary views and actions

The domain slice will use inherited standard Odoo Project and Task forms plus
standard list/search views. It will add an item-type configuration action only
after `project.agile.item.type` exists, a backlog action/filter based on explicit
sequence and unscheduled eligibility, and no custom JavaScript. Exact Odoo 19
view external IDs must be inspected in the target image/source rather than
invented from memory.

## Test plan

The skeleton contract test verifies the narrow manifest and absence of custom
JavaScript. The domain slice must add Odoo tests for clean install, Agile key
generation/uniqueness/stability, no effect on ordinary projects, valid and
invalid type policy, native cycle handling, project isolation, story-point
validation, type reconfiguration, and manager/employee ORM access. Run the
focused tests and `./scripts/verify` against the disposable verification
database. Recovery is a clean database/container rerun; no persistent volume is
deleted.

## Open questions

- Validate final Odoo 19 field and view naming against the exact target source.
- Resolve whether a missing type is permitted during Agile project onboarding.
- Decide key padding only after a consumer demonstrates a need.
