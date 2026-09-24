# Odoo Agile Delivery

An Odoo 19-native suite that adds software-delivery semantics to Project and Knowledge without replacing Odoo's core models or behavior.

## Current scope

The first milestone is `project_agile`:

- opt-in Agile configuration per project;
- configurable work-item types;
- stable project-scoped task keys;
- story points and acceptance criteria;
- explicit backlog ordering;
- model-level hierarchy validation using native `project.task.parent_id`.

Scrum, analytics, Knowledge relationships, Git integration, advanced UI, and Jira migration follow only after the core domain is stable.

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
