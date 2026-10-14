# Odoo Agile Delivery

Optional software-delivery addons for Odoo Project: Agile work items, Scrum planning,
Git visibility, and solution-definition traceability. Work stays on native
`project.task`, with native hierarchy and dependencies; Agile is opt-in per Project.
Install only the capabilities you need. Ordinary Project behavior remains available.

## Supported target

The tested edition is **Odoo 19 Community**. The architecture is **Odoo.sh-first but
portable to self-hosted Odoo**: ordinary ORM, views, QWeb and native `ir.cron`, without
a required external queue runner. This is a design target, not proof of a live Odoo.sh
or Enterprise deployment. Validate the actual installed extensions, permissions and
scheduler behavior in staging before production use.

This repository is Odoo-compatible and uses OCA-aligned contributor tooling; it does
not claim full OCA conformity. Licenses are per addon, not a blanket suite license.

## Addons and direct dependencies

All addons below are installable, non-application modules. Dependencies are the direct
`depends` entries in their manifests; Odoo resolves their transitive dependencies.
`project` is native Community Project. Everything beyond `project_agile` is optional
for the Agile core; some optional addons require other optional modules as listed.

| Addon | Capability | Direct dependencies | License |
| --- | --- | --- | --- |
| `project_agile` | Opt-in Agile configuration, configurable work-item types, immutable project-scoped task keys, story points, acceptance criteria and backlog ordering | `project` | LGPL-3 |
| `project_scrum` | Agile teams, Sprint lifecycle, commitment snapshots, scope history and explicit unfinished-work disposition | `project_agile` | LGPL-3 |
| `project_scrum_analytics` | Velocity, Burndown, Burnup, Scope Change and Commitment vs Completion in native reporting views | `project_scrum` | LGPL-3 |
| `project_agile_ui` | Optional planning board for draft-Sprint assignment, Product Backlog return and backlog ordering, with keyboard-accessible actions | `project_scrum` | LGPL-3 |
| `project_agile_document_page` | Explicit Agile Project documentation root on OCA Document Page | `project_agile`, `document_page_project` | AGPL-3 |
| `project_scrum_document_page` | Explicit Sprint retrospective pages on OCA Document Page | `project_scrum`, `document_page_project` | AGPL-3 |
| `project_agile_git` | Provider-neutral repository, delivery ledger, branch, commit, pull-request and check facts with immutable Agile-key associations and read-only Project/Task visibility | `project_agile` | LGPL-3 |
| `project_agile_git_github` | Signed GitHub webhook persistence, scheduled normalization, bounded retries, retention and authorized terminal reprocessing | `project_agile_git` | LGPL-3 |
| `project_agile_git_automation` | Opt-in approved stage-only policy, dry-run previews, bounded scheduling, audit and recovery controls | `project_agile_git` | LGPL-3 |
| `project_agile_solution` | Solution/document lineage, immutable SOW/spec baselines, exact requirement/context revisions, explicit Task links and retry-safe creation intents, audience-safe native reports, coverage and recorded acceptance | `project_agile` | LGPL-3 |
| `project_agile_solution_scrum` | Frozen exact requirement context at native Sprint scope events, without backfilling history | `project_agile_solution`, `project_scrum` | LGPL-3 |

The Document Page bridges need separately supplied OCA `knowledge` 19.0 modules:
`document_page_project` depends on `project` and `document_page`; `document_page`
depends on `mail`, `document_knowledge` and `html_editor`; `document_knowledge`
depends on `base`. The selected OCA modules are AGPL-3. See the
[pinned fixture and licensing considerations](docs/research/odoo-19-oca-document-page-fixture.md)
before choosing this optional backend. It is not Enterprise Knowledge, and no
Task-document-page connector is delivered. Solution documents do not require either
Document Page or Enterprise Knowledge.

Git facts are observations, not proof of Task completion. GitHub ingress itself never
writes Tasks. The separate policy addon can write only an explicitly approved eligible
Task stage under its approved non-superuser executor; native ORM side effects remain.
It can install without GitHub or Scrum, seeds no enabled policy, and defaults to disabled
and dry-run. **No production policy, provider setup or deployment is activated by
installation or successful verification.** Consult the operator guides before enablement.

Solution approval and recorded exact-revision acceptance are explicit actions, not
inferences from Task Done or PR merge. Customer output is an internally generated
redacted projection, not a customer portal or legal signature. Jira migration,
release/version management and additional provider adapters are not delivered addons.

## Installation

1. Use an Odoo 19 environment with native Project and its dependencies available.
   Back up the database and filestore before updating or removing existing addons;
   uninstall removes addon-owned data and is not archival.
2. Add this repository's `addons/` directory to the server's `addons_path`, retaining
   the native Odoo paths. On Odoo.sh, include the repository in the build's addon sources
   and confirm module discovery in a staging build. On self-hosted Odoo, ensure the Odoo
   process can read the addon directories and use your normal server restart procedure
   after adding code. No external Python SDK or `queue_job` is required by these addons.
3. For Document Page bridges only, also supply the selected compatible OCA `knowledge`
   source and add its addon directory to `addons_path`. The normal development Compose
   setup below does not supply OCA modules.
4. As an authorized administrator, enable developer mode and update the Apps list.
   Remove the default **Apps** filter: these addons have `application=False`.
   Search by technical module name, then install the desired subset. Odoo installs its
   dependencies automatically. For example, choose `project_agile` for Agile alone,
   `project_scrum` for Sprints, or `project_agile_solution` for solution documents without
   Scrum/Git/document backends.
5. Enable Agile explicitly on the intended Project and configure its work-item types
   and stable key prefix. Add teams/Sprints only if Scrum is installed. Apply least-
   privilege Project/company access; installing a connector or policy addon is not
   permission to configure live provider secrets or enable production automation.

Use the [GitHub operations runbook](docs/runbooks/github-git-facts-operations.md) for
repository mapping, signed ingress, retention and recovery, and the
[policy configuration guide](docs/git-policy-configuration.md) plus
[policy operations runbook](docs/runbooks/git-policy-operations.md) for explicit
approval, dry-run-before-enable and shutdown. Assess deployment-specific native stage
side effects and source compatibility before enabling apply mode.

## Local Docker development

Prerequisites: Docker with Compose v2 and access to the declared images. Run from the
repository root. For a new setup only, copy the example settings; do not overwrite an
existing `.env`, commit it, or treat the development defaults as production credentials.

```bash
cp .env.example .env
docker compose up -d db odoo
docker compose ps
```

Open `http://127.0.0.1:8079` and create a disposable development database, then follow
the Apps installation steps above. The stack mounts `addons/` at `/mnt/extra-addons`;
`config/odoo.conf` includes that path alongside native addons. It does not automatically
install the suite. `ODOO_HTTP_PORT` in `.env` changes the default host port. Odoo binds
only to loopback, PostgreSQL has no published host port, and database/filestore data
use named volumes. This configuration is for local development, not public hosting.

Stop the stack while retaining data:

```bash
docker compose down
```

Only for a disposable development stack whose data you deliberately intend to delete:

```bash
docker compose down --volumes
```

Use the exact intended Compose project. Never use global Docker prune as test cleanup
or remove another stack's resources. Production backups, public networking and service
configuration need a deployment-specific plan.

## Developer verification

See [contributor checks](docs/contributing.md) for Python 3.12 setup, pinned tooling
and the advisory translation rule. From the repository root, with that environment:

```bash
pre-commit run --all-files --show-diff-on-failure
python -m unittest discover -s tests -p 'test_*.py' -v
./scripts/verify
```

The canonical `./scripts/verify` runs compilation and root tests, builds the dedicated
browser-capable verification image, and exercises native Odoo test discovery. It covers
independent Git-policy and solution-core installs, optional solution/Scrum bridge
checks, persisted-data solution lifecycles, and combined install, targeted upgrade and
dependency-safe uninstall/reinstall. The combined set is the nine local non-Document-
Page addons above plus native `hr_timesheet`; it includes Hoot/browser and Git/solution
concurrency checks. Inspect the actual Odoo version/build and per-phase discovery/results
in the verification log; a syntax pass alone is not native runtime evidence.

The verifier generates a fresh worktree/process-scoped Compose project, ignores an
inherited development project name, uses only its declared disposable databases, and
removes owned containers, volumes and networks on exit. It checks resource absence and
reports teardown errors separately. It is not a live Odoo.sh validation.

The optional OCA backend uses a **separate** pinned fixture, not the canonical gate:

```bash
./scripts/verify-oca-document-page
```

Read the [fixture record](docs/research/odoo-19-oca-document-page-fixture.md) first.
This existing helper uses the fixed project `odoo_agile_oca_document_page`, publishes no
host port and stores PostgreSQL data on tmpfs. Unlike the canonical verifier it has no
automatic teardown trap; use it only in a dedicated disposable environment, never
concurrently or against an existing stack. On success or failure, remove only its
owned fixture resources and verify absence:

```bash
docker compose -p odoo_agile_oca_document_page -f compose.oca-document-page.yaml down --volumes --remove-orphans
```

## Guides and architecture

- [Solution baseline operations](docs/m8-document-baselines.md) and
  [rendering, coverage and acceptance](docs/runbooks/solution-rendering-and-acceptance.md)
- [Git dry-run behavior](docs/git-policy-dry-run.md) and
  [apply boundary](docs/git-policy-apply-boundary.md)
- [Contributor setup and checks](docs/contributing.md)
- [Architecture decision index](docs/adrs/README.md), especially the current
  [Git facts contract](docs/adrs/011-git-facts-and-visibility-contract.md) and
  [opt-in workflow policy contract](docs/adrs/012-git-workflow-policy-contract.md)

`addons/` contains modules, `config/` the development server configuration, `scripts/`
the existing verification entrypoints, and `docs/` architecture and operating guides.
Historical plans describe their original phases; use the current source inventory above
and applicable operating guides to distinguish installed capabilities from proposals.
