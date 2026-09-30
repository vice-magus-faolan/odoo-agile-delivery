# Odoo Agile Delivery

An Odoo 19-native suite that adds software-delivery semantics to Project and Knowledge without replacing Odoo's core models or behavior.

## Current scope

Delivered modules are:

- `project_agile`: opt-in Agile configuration, configurable work-item types,
  stable project-scoped task keys, story points, acceptance criteria, explicit
  backlog ordering, and native hierarchy validation.
- `project_scrum`: explicit Agile teams, draft/active/closed Sprint lifecycle,
  team-scoped active-Sprint enforcement, native task-to-Sprint assignment,
  immutable commitment snapshots, append-only scope events, and explicit
  unfinished-work disposition to the Product Backlog or a compatible draft Sprint.
- `project_scrum_analytics`: additive Sprint Velocity, Burndown, Burnup, Scope
  Change, and Commitment vs Completion projections replayed from immutable
  scope facts, with native list, pivot, graph, export, and authorized drill-down
  reporting surfaces.
- `project_agile_git`: provider-neutral repository, delivery-ledger, branch,
  commit, pull-request, check, immutable Agile-key association, and read-only
  Project/Task visibility.
- `project_agile_git_github`: signed, bounded GitHub webhook persistence, native
  scheduled normalization, replay/idempotency, leases/retries, terminal recovery,
  and bounded redacted-payload retention. It remains observation-only.

Delivered optional Milestone 4 modules are `project_agile_document_page` and
`project_scrum_document_page`; they use the separately verified OCA Document Page
fixture and do not become dependencies of the Community core. Milestone 5 additionally
delivers the optional `project_agile_ui` planning board: a bounded Odoo client action
with current-user, server-authoritative draft-Sprint assignment, Product Backlog return,
and deterministic backlog reordering. Pointer drag/drop is an interaction layer;
ordinary Odoo views and keyboard-accessible actions remain available. Git integration
now delivers its Milestone 6 facts-and-visibility capability, including the optional
GitHub adapter. Milestone 7 has an accepted opt-in policy contract and an installable
`project_agile_git_automation` configuration addon with typed revisions,
two-person activation and terminal authority revocation. Evaluation and authorized
task-stage execution remain pending downstream work.
Workflow automation is not operational or activated. Jira migration, release/version
management, other providers, richer Git UI, and the Task-document connector remain
later work; ordinary Project behavior is unchanged.

See [the mission brief](docs/mission-brief.md) for the full direction and non-goals.

## Development environment

Prerequisites: Docker with Compose v2.

```bash
cp .env.example .env
docker compose up -d db odoo
docker compose ps
```

Odoo binds to `127.0.0.1:8079` by default. Override `ODOO_HTTP_PORT` in `.env` if needed. The database is not published to the host network.

Stop the environment without deleting data:

```bash
docker compose down
```

Delete development data only when explicitly intended:

```bash
docker compose down --volumes
```

## Verification

```bash
./scripts/verify
```

This runs static/syntax checks, an independent optional policy-fixture install, and
seven-module install, targeted upgrade, and dependency-safe uninstall/reinstall
with discovered Odoo tests against three declared disposable databases.

## Repository layout

```text
addons/          Odoo modules
config/          local container configuration
scripts/         reproducible verification helpers
docs/adrs/       concise architecture decisions
docs/research/   ecosystem and dependency research
```

## Delivery constraints

- `project.task` remains the work-item model.
- Native task hierarchy and dependencies remain authoritative.
- Agile behavior is opt-in per project.
- Scrum remains a separate module.
- No custom OWL planning UI in Milestone 1.
- Git connectors record facts; configurable automation decides workflow effects.


## Milestone 5 planning-board verification boundary

`./scripts/verify` is the canonical release-candidate gate for
`project_agile`, `project_scrum`, `project_scrum_analytics`, and the optional
`project_agile_ui` planning board, plus `project_agile_git`,
`project_agile_git_github`, and the optional `project_agile_git_automation` addon.
It fails fast on syntax, static-contract, Compose,
or Odoo-test failures and exercises all three supported lifecycles against
disposable Odoo 19 databases:

- clean install of all seven modules with their focused test tags;
- install followed by `--update project_agile,project_scrum,project_scrum_analytics,project_agile_ui,project_agile_git,project_agile_git_github,project_agile_git_automation`;
- install, dependency-safe ORM uninstall in reverse order, then reinstall with
  focused tests.

The verifier defaults to a deterministic, worktree-local Compose namespace
(`odoo-agile-verify-<worktree>`), avoiding the normal development namespace and
removing only that disposable namespace and its volumes on exit. An explicitly
provided `COMPOSE_PROJECT_NAME` is respected and never cleaned automatically.
The check starts only the Compose `db` service and uses transient
`docker compose run --rm` Odoo containers from a committed test-only verification image
(`Dockerfile.verify` plus `compose.verify.yaml`). That image adds a pinned
Google Chrome package and the pinned `websocket-client` package so the native Odoo HttpCase runs the
`project_agile_ui` Hoot suite; it does not alter the normal development image or
module dependencies. The Docker build context excludes `.env` and Git metadata.

Before each lifecycle, the verifier touches only its three declared disposable databases
(`odoo_agile_verify_install`, `odoo_agile_verify_upgrade`, and
`odoo_agile_verify_reinstall`), terminates their resident sessions, and refuses
any other database name. Default cleanup removes only its worktree-local disposable
namespace; it never touches unrelated services, databases, volumes, or an explicitly
selected Compose project.

Run `./scripts/test_planning_concurrency.py` for the separate real-connection
regression. It creates, tests, and removes only the task-named
`odoo_agile_planning_concurrency_t_b1f7013f` database. Two independent Odoo
shell processes race assign/return and backlog-reorder intents with lock,
statement, and wall-clock timeouts; the harness requires one serialized success
and one actionable stale rejection per race, then checks complete contiguous
backlog order and the absence of partial Sprint/history state.

`project_agile` depends only on the Odoo Community `project` module.
`project_scrum` remains isolated from ordinary Project behavior, while
`project_scrum_analytics` depends only on `project_scrum`. The optional
`project_agile_ui` depends only on `project_scrum` and contributes an optional
Odoo-native planning board plus its `web.assets_unit_tests` Hoot coverage. Its
current-user server boundary preserves Scrum assignment, return-history, ordering,
and lifecycle rules; it adds no Git indicators or Task-document controls.
Reporting uses
ordinary Odoo list, pivot, graph, filter, export, and drill-down views; it adds
no custom JavaScript or OWL assets. Superuser recovery may correct `closed_at`;
its report and timeline rebuild synchronously, while lifecycle state remains action-only,
including for superuser.

## Milestone 4 OCA Document Page fixture

Milestone 4's Community documentation backend is OCA Document Page at the
immutable OCA `knowledge` 19.0 commit recorded in
[`docs/research/odoo-19-oca-document-page-fixture.md`](docs/research/odoo-19-oca-document-page-fixture.md).
The selected `document_knowledge`, `document_page`, and
`document_page_project` modules are AGPL-3 and are deliberately not dependencies
of the existing Community modules.

Run the bounded, disposable OCA fixture separately:

```bash
./scripts/verify-oca-document-page
```

It pins Odoo/PostgreSQL image digests and the OCA source commit, exposes no host
port, and uses no persistent Docker volume. `./scripts/verify` remains the
canonical Community regression gate. Enterprise Knowledge is only a deferred
alternative backend; it is not API-compatible with OCA Document Page.


## Milestone 6 Git facts and visibility boundary

`project_agile_git` is a small, LGPL-3, Odoo-compatible private-suite module. It
depends only on `project_agile`; it keeps its provider-neutral boundary; the separately installable GitHub adapter exposes
a bounded signed webhook route, while the core has no queue runtime dependency. It defines repository-scoped,
multi-company Git fact and durable-delivery records so future provider adapters can
persist authenticated deliveries before separate processing. Explicit immutable Agile
keys are the only task-association input. Git facts are visibility, not workflow
automation: a pull-request merge or successful check cannot change a task stage.

The canonical `./scripts/verify` gate includes clean install, targeted upgrade, and
dependency-safe uninstall/reinstall of both Git addons. The delivered GitHub
processor uses Odoo 19's supported `ir.cron` scheduler: up to 20 leased deliveries,
savepoint-atomic normalization, bounded retries/dead letters, sanitized diagnostics,
and progress commits. Signed ingress returns after persistence, never Task writes.
Retention and explicit authorized terminal reprocess controls are delivered.
See [ADR-011](docs/adrs/011-git-facts-and-visibility-contract.md) and the
[operations runbook](docs/runbooks/github-git-facts-operations.md). Live webhook
registration/secrets/configuration and deployment are separate operator effects.

## Milestone 7 configuration and pending policy engine

[ADR-012](docs/adrs/012-git-workflow-policy-contract.md) supersedes historical
ADR-008 and fixes the bounded opt-in merged-PR policy contract; the
[M7 plan](docs/plans/2026-09-30-milestone-7-git-policy.md) sequences the serial
reviewed implementation. `project_agile_git_automation` depends only on
`project_agile_git` and is independently installable without GitHub or Scrum.
The configuration slice adds repository/project-scoped finite rules, editable
drafts and immutable approved revisions, distinct author/approver activation,
approved non-superuser execution identities, and append-only revocation history.
Installation seeds no rules or capability members; Projects default disabled and
dry-run. Current native/custom Project visibility, concrete Task permissions and
company membership are authority, not provider payloads or context. Ownership,
scope, security, stage settings and follower removal invalidate approval;
restoration never resurrects a used epoch. See the
[configuration guide](docs/git-policy-configuration.md).

The [bounded authority profile](docs/git-policy-authority-profiles.md) implements
Jimmy's approved revoke-only Task observer and explicit native-profile allowlist.
Only literal direct Task name/active custom access rules are supported initially;
unknown authority dependencies refuse activation. Both stage-relation directions,
native authority-input edits and inverse membership changes require fresh approval.
The bounded synthetic audit fixture remains distinct from authenticated
observations and consumed effects. There is no evaluator, cron or policy-initiated
Task mutation in this slice. No operational automation or production policy is
activated by this delivery. Live activation requires separate operator approval
and exact-SHA authorization/recovery evidence.
