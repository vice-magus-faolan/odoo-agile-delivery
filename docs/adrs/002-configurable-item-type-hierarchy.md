# ADR-002: Configurable Item-Type Hierarchy

## Context

Teams need configurable work-item terminology and valid parent/child policies,
without a hardcoded Jira hierarchy or a parallel issue model. Odoo 19 already
owns task hierarchy through `project.task.parent_id` and `child_ids`.

## Decision

The domain implementation will add the justified configuration model
`project.agile.item.type`. It will contain a stable code, display name, active
flag, display ordering, and one canonical many-to-many relation:
`allowed_child_type_ids`. A task's `parent_id` remains native. For two Agile
tasks with item types, the parent type must allow the child type. Empty allowed
children means that the type cannot parent a typed Agile work item. The relation
is not duplicated as stored allowed-parent data; parent eligibility is derived
by traversing the canonical relation when needed.

A model-level constraint validates hierarchy on task parent/type/project changes
and type-policy changes. It also rejects cross-project parentage for Agile tasks.
UI domains guide selection but are not authoritative. Native Odoo recursion/cycle
handling remains responsible for generic tree-cycle protection.

## Alternatives

- Hardcoded Epic/Story/Task/Subtask conditionals: rejected because terminology
  and policy must be configurable.
- A separate relation model for hierarchy: rejected because native `parent_id`
  already represents containment.
- Both allowed-parent and allowed-child stored relations: rejected because two
  editable sources of truth drift.
- UI-only domains: rejected because imports, RPC, and batch ORM calls bypass UI.

## Consequences

The model count increases by one only because configurable type policy has a
persistent domain invariant. Existing non-Agile task hierarchies remain native
and unmodified. Policy edits can invalidate existing data, so configuration
writes must fail with an actionable validation error rather than silently
reclassify or detach tasks.

## Open Questions

- Should a missing item type on an Agile task be permitted during incremental
  adoption, or should it be required once a project is enabled?
- Should cross-project parentage be prohibited globally by Project or only for
  the Agile opt-in boundary in this milestone?
