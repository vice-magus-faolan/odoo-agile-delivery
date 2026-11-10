# Repository Operating Contract

## Product boundary

Follow the maintained architecture decisions in `docs/adrs/`. In particular:

- extend `project.task`; do not create a parallel issue model;
- use native `parent_id` / `child_ids` and native task dependencies;
- keep Agile opt-in per project and Scrum isolated in `project_scrum`;
- use ordinary Odoo views before custom OWL;
- do not make Git, Knowledge, analytics, or Jira migration dependencies of `project_agile`.

## Engineering workflow

- Read repo-local docs and ADRs before changing architecture.
- Work in a task-scoped branch/worktree, never directly in the canonical checkout.
- Add model-level enforcement for invariants; UI domains alone are insufficient.
- Include automated tests for new behavior and regressions.
- Use focused local checks for development feedback. Independently review committed source before PR publication; the required hosted lint and module tests must pass before merge.
- Keep new or changed functions easy to reason about; soft-warn around cyclomatic complexity 10 and justify or refactor above 15.
- Commit before review and hand off the exact full SHA, branch, changed files, checks, and residual risks.

## Effects

Do not push, merge, alter the default branch, restart shared services, publish, or delete persistent Docker volumes unless the task explicitly authorizes that effect. Docker test containers and disposable verification databases are allowed when the task requests verification.
