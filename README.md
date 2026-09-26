# Odoo Agile Delivery

An Odoo 19-native suite that adds software-delivery semantics to Project and Knowledge without replacing Odoo's core models or behavior.

## Current scope

Delivered modules are:

- `project_agile`: opt-in Agile configuration, configurable work-item types,
  stable project-scoped task keys, story points, acceptance criteria, explicit
  backlog ordering, and native hierarchy validation.
- `project_scrum`: explicit Agile teams, draft/active/closed Sprint lifecycle,
  team-scoped active-Sprint enforcement, native task-to-Sprint assignment,
  immutable commitment snapshots, and append-only scope events.

Analytics, Knowledge relationships, Git integration, advanced UI, Jira migration,
and full Sprint-close unfinished-work policy remain deferred until the core
lifecycle contracts are stable.

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

Before `project_agile` exists, this validates repository and Compose structure. Once the module manifest exists, it also performs a clean Odoo install with tests against a disposable `odoo_agile_verify` database.

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


## Milestone 2 verification boundary

`./scripts/verify` is the repository release-candidate gate for both `project_agile` and `project_scrum`. It fails fast on
syntax, static-contract, Compose, or Odoo-test failures and exercises all three
supported module lifecycles on a clean Odoo 19 database:

- clean install of `project_agile`;
- install followed by `--update project_agile,project_scrum`;
- install, ORM-driven module uninstall, then reinstall.

On the Odoo 19.0-20260908 run completed on 2026-09-24, the standalone runner
completed two static contract tests. Each lifecycle logged 14 discovered project_agile
tests and reported `0 failed, 0 errors of 12 tests`. Those are the two counts
emitted by Odoo; this documentation deliberately does not collapse them into a
single total.

The check only starts the Compose `db` service and uses transient `docker compose
run --rm` Odoo containers. It drops only its three named disposable databases
(`odoo_agile_verify_install`, `odoo_agile_verify_upgrade`, and
`odoo_agile_verify_reinstall`), never force-drops a database, and does not remove
Compose volumes or touch unrelated services or databases.

`project_agile` depends only on the Odoo Community `project` module. Knowledge
integration is deliberately not part of Milestone 1: Odoo Knowledge is an
Enterprise module and belongs to a future optional `project_agile_knowledge`
integration. The module contains no custom JavaScript or OWL assets; ordinary
Odoo views are the supported interface for this milestone.
