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
task keys.

Cross-project moves of a task that already has an `agile_key` are rejected with an
actionable `ValidationError`: the key identifies its original Agile project and must not
be regenerated or reassigned. To move the work, a user creates or copies a new task in
the target project, which receives a key in the target-project namespace. The database
uniqueness constraint is global on `agile_key`, not project-local, so every issued key
remains an unambiguous instance-wide reference.

Odoo's sequence allocation is used instead of custom counters or Python `max(...) + 1`,
because the latter races under concurrent creates. Non-Agile projects do not allocate a
sequence or receive an Agile key.

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

The implementation creates `ir.sequence` records only for projects that opt in. Sequence
gaps are acceptable, as with native Odoo sequences. Key allocation is not a stored
computed field and does not modify ordinary Project behavior.

## Open Questions

- Should an administrator be allowed to retire a project key before any task key exists,
  or should it be immutable from enablement?
- Is a configurable numeric padding useful before integrations consume keys?
