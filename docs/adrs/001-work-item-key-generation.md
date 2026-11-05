# ADR-001: Work-Item Key Generation

## Context

Agile projects need stable, human-readable task identifiers such as `ENG-142` for branch
names, commits, pull requests, and cross-system references. The key must be unique,
indexed, immutable after assignment, concurrency-safe, and must not affect ordinary
projects.

## Decision

The domain implementation will use one Odoo `ir.sequence` per Agile-enabled project. Its
code will be namespaced by the project record identity, and its prefix will use that
project's validated `agile_key` plus `-`. During `project.task.create`, an Agile project
receives the next sequence number in the same ORM transaction and stores the resulting
value in an indexed, copied-false, readonly `agile_key` field. A database uniqueness
constraint will back the ORM invariant. Existing keys will never be recomputed when a
project key changes; that configuration change is rejected once a project has assigned
task keys. Before any task key has been assigned, a Project administrator can change the
Project key subject to the same validation and uniqueness rules. Changing the Project
display name does not change its key or task namespace.

Cross-project moves of a task that already has an `agile_key` are rejected with an
actionable `ValidationError`: the key identifies its original Agile project and must not
be regenerated or reassigned. To move the work, a user creates or copies a new task in
the target project, which receives a key in the target-project namespace. The database
uniqueness constraint is global on `agile_key`, not project-local, so every issued key
remains an unambiguous instance-wide reference.

Odoo's sequence allocation is used instead of custom counters or Python `max(...) + 1`,
because the latter races under concurrent creates. Non-Agile projects do not allocate a
sequence or receive an Agile key.

Project duplication and native template creation retain Agile enablement, default item
type and estimation policy. When the selected template is Agile, the native Create a
Project from Template wizard requires an editable Agile key. Its whitelist passes that
choice to the existing Project domain before copied tasks receive their keys; missing,
invalid or conflicting choices are rejected by the existing Project validation and
uniqueness constraint. Ordinary templates do not require or forward an Agile key.

Duplicate and unattended template creation, including Sales, have no Agile key prompt.
Their copy-data hook allocates a fresh COPYn Project key through a shared native
ir.sequence unless an explicit programmatic key default is supplied. This generated
fallback is already permanent when copied tasks receive keys; it is not a temporary
prefix that an administrator can rename later. Allocation skips existing namespaces,
including archived or inaccessible Projects, using elevation only for identity
allocation and existence checks. Source data is copied with caller authority. Native
task mapping then uses the new Project-local sequence; neither source task keys nor
sequence progress is copied. Project templates do not issue task keys until used.

## Alternatives

- A global sequence with the project key in a computed prefix: rejected because it does
  not provide project-local numbering and makes project-key changes ambiguous.
- A custom PostgreSQL sequence or counter table: rejected because `ir.sequence` is
  Odoo-native, transactional, administrable, and sufficient.
- OCA `project_key` or `project_task_code`: rejected as a hard dependency; the Odoo 19
  availability and upgrade posture are not adequate for the base module.
- Reusing `project.task.id`: rejected because identifiers need a project prefix and
  should not expose database implementation detail.

## Consequences

The implementation creates per-Project sequences only for projects that opt in. Sequence
gaps are acceptable, as with native Odoo sequences. Key allocation is not a stored
computed field and does not modify ordinary Project behavior.

## Open Questions

- Is a configurable numeric padding useful before integrations consume keys?
