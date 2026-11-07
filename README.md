# Odoo Agile Delivery

Optional software-delivery addons for Odoo Project: Agile work items, Scrum planning,
Git visibility, and solution documents. Work stays on native `project.task`, with
native hierarchy and dependencies; Agile is opt-in per Project. Install only the
capabilities you need. Ordinary Project behavior remains available.

## Supported target

The tested edition is **Odoo 19 Community**. The architecture is **Odoo.sh-first but
portable to self-hosted Odoo**: ordinary ORM, views, QWeb and native `ir.cron`, without
a required external queue runner. Validate your installed extensions, permissions
and scheduler behavior in staging before production use.

The repository uses OCA-aligned contributor tooling. Licenses are per addon.

## Addons and direct dependencies

All addons below are installable, non-application modules. Dependencies are the direct
`depends` entries in their manifests; Odoo resolves their transitive dependencies.
`project` is native Community Project. Everything beyond `project_agile` is optional
for the Agile core; some optional addons require other optional modules as listed.

| Addon | Capability | Direct dependencies | License |
| --- | --- | --- | --- |
| `project_agile` | Agile work-item types, stable task keys, story points and backlog ordering | `project` | LGPL-3 |
| `project_scrum` | Teams, Sprints, commitments and scope history | `project_agile` | LGPL-3 |
| `project_scrum_analytics` | Velocity, Burndown, Burnup and scope reports | `project_scrum` | LGPL-3 |
| `project_agile_ui` | Keyboard-accessible Sprint and backlog planning board | `project_scrum` | LGPL-3 |
| `project_agile_document_page` | Project documentation root on OCA Document Page | `project_agile`, `document_page_project` | AGPL-3 |
| `project_scrum_document_page` | Sprint retrospective pages on OCA Document Page | `project_scrum`, `document_page_project` | AGPL-3 |
| `project_agile_git` | Repository, branch, commit, pull-request and check visibility on Projects and Tasks | `project_agile` | LGPL-3 |
| `project_agile_git_github` | Signed GitHub webhooks, scheduled processing and recovery | `project_agile_git` | LGPL-3 |
| `project_agile_git_automation` | Approved Task-stage rules, dry-run previews and audit controls | `project_agile_git` | LGPL-3 |
| `project_agile_solution` | SOW/spec baselines, versioned requirements, Task links, reports and recorded acceptance | `project_agile` | LGPL-3 |
| `project_agile_solution_scrum` | Frozen requirement context in Sprint scope history | `project_agile_solution`, `project_scrum` | LGPL-3 |

Each addon includes its full licence text in `addons/<module>/LICENSE`; LGPL-3
addons also include the incorporated GNU GPL terms in `COPYING`. The
[licensing coverage index](LICENSE) also grants LGPL-3 for original project-owned
supporting material and identifies the retained MIT terms for OCA tooling-template
portions and GitHub test fixtures. Existing manifest, source and dependency
declarations remain authoritative; third-party material keeps its own terms.

The Document Page bridges need separately supplied OCA `knowledge` 19.0 modules:
`document_page_project` depends on `project` and `document_page`; `document_page`
depends on `mail`, `document_knowledge` and `html_editor`; `document_knowledge`
depends on `base`. The selected OCA modules and both bridges are AGPL-3.
Solution documents can be installed independently of Document Page.

GitHub ingress records Git facts. The separate policy addon applies approved Task-stage
rules under its approved non-superuser executor and defaults to **disabled** and
**dry-run**. Solution approval and exact-revision acceptance use explicit actions.

## Installation

1. Use an Odoo 19 environment with native Project and its dependencies available.
   Back up the database and filestore before updating or removing existing addons;
   uninstall removes addon-owned data.
2. Add this repository's `addons/` directory to the server's `addons_path`, retaining
   the native Odoo paths. On Odoo.sh, include the repository in the build's addon sources
   and confirm module discovery in a staging build. On self-hosted Odoo, ensure the Odoo
   process can read the addon directories and use your normal server restart procedure
   after adding code.
3. For Document Page bridges only, also supply the selected compatible OCA `knowledge`
   source and add its addon directory to `addons_path`. The normal development Compose
   setup below supplies only this repository's addons.
4. As an authorized administrator, enable developer mode and update the Apps list.
   Remove the default **Apps** filter: these addons have `application=False`.
   Search by technical module name, then install the desired subset. Odoo installs its
   dependencies automatically. For example, choose `project_agile` for Agile alone,
   `project_scrum` for Sprints, or `project_agile_solution` for solution documents.
5. Enable Agile explicitly on the intended Project and configure its work-item types
   and stable key prefix. Add teams/Sprints if Scrum is installed. Configure least-
   privilege Project/company access.

Use the [GitHub operations runbook](docs/runbooks/github-git-facts-operations.md) for
repository mapping, signed ingress, retention and recovery, and the
[policy configuration guide](docs/git-policy-configuration.md) plus
[policy operations runbook](docs/runbooks/git-policy-operations.md) for approval,
dry-run-before-enable and shutdown. Assess deployment-specific native stage side
effects before enabling apply mode.

## Local Docker development

Prerequisites: Docker with Compose v2 and access to the declared images. Run from the
repository root. For a new setup, copy the example settings; preserve an existing
`.env` and keep credentials private.

```bash
cp .env.example .env
docker compose up -d db odoo
docker compose ps
```

Open `http://127.0.0.1:8079` and create a disposable development database, then follow
the Apps installation steps above. The stack mounts `addons/` at `/mnt/extra-addons`;
`config/odoo.conf` includes that path alongside native addons. Install your chosen
modules through Apps. `ODOO_HTTP_PORT` in `.env` changes the default host port. Odoo
binds only to loopback, PostgreSQL has no published host port, and database/filestore
data use named volumes.

Stop the stack while retaining data:

```bash
docker compose down
```

To delete a disposable development stack's database and filestore as well:

```bash
docker compose down --volumes
```

## Developer verification

See [contributor checks](docs/contributing.md) for Python 3.12 setup, pinned tooling
and the advisory translation rule. From the repository root, with that environment:

```bash
pre-commit run --all-files --show-diff-on-failure
./scripts/verify
```

`./scripts/verify` installs, upgrades, uninstalls and reinstalls the core and optional
non-Document-Page addons in disposable databases, running native Odoo, browser
and concurrency tests. It automatically removes its owned containers, volumes and
networks on exit and checks that teardown completed.


External process/lifecycle checks and standalone planning-race usage are documented
in [the probe guide](scripts/probes/README.md).

Verify the optional OCA Document Page bridges separately:

```bash
./scripts/verify-oca-document-page
```

The fixture pins OCA `knowledge` 19.0 at
`e4a12c0c99866a5850840941d6f7ae3b3b27280d` in
`fixtures/oca-document-page/Dockerfile`. Its selected OCA modules and the two bridges
are AGPL-3; review those license obligations when choosing this backend.

## Guides and architecture

- [Solution history, access and recovery](docs/runbooks/solution-operations.md)
- [Document Page setup](addons/project_agile_document_page/README.rst#configuration)
- [Git dry-run behavior](docs/git-policy-dry-run.md) and
  [apply boundary](docs/git-policy-apply-boundary.md)
- [Contributor setup and checks](docs/contributing.md)
- [Architecture decision index](docs/adrs/README.md), especially the current
  [Git facts contract](docs/adrs/011-git-facts-and-visibility-contract.md) and
  [opt-in workflow policy contract](docs/adrs/012-git-workflow-policy-contract.md)

`addons/` contains modules, `config/` the development server configuration, `scripts/`
the verification entrypoints, and `docs/` architecture and operating guides.
