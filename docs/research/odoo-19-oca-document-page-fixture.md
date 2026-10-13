# Odoo 19 OCA Document Page fixture

## Purpose and scope

This is the reproducible, disposable Odoo 19 Community fixture for the Milestone 4 OCA
Document Page contract. It is source and runtime evidence for the three selected OCA
modules, the two existing Community modules, and the two local optional bridges
exercised by its verifier; it is not a production deployment, a vendor copy, an
Enterprise Knowledge fixture, or proof that Enterprise Knowledge is API-compatible with
OCA Document Page.

Run it from the repository root:

```bash
./scripts/verify-oca-document-page
```

It uses no secret, publishes no port, mounts local add-ons read-only, and uses a
project-scoped Compose name with PostgreSQL storage on `tmpfs`. It drops only the three
named disposable databases inside that fixture: `odoo_agile_oca_document_page_install`,
`odoo_agile_oca_document_page_upgrade`, and `odoo_agile_oca_document_page_reinstall`. It
never removes Docker volumes.

## Immutable acquisition record

| Item               | Immutable selection                                                                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Odoo image         | `odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c` (`odoo:19.0` image digest observed 2026-09-27)                                             |
| PostgreSQL image   | `postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24` (`postgres:17-alpine` image digest observed 2026-09-27)                                |
| OCA repository     | `https://github.com/OCA/knowledge.git`                                                                                                                                    |
| OCA branch source  | `19.0` at `e4a12c0c99866a5850840941d6f7ae3b3b27280d`                                                                                                                      |
| Acquisition method | Dockerfile initializes an empty repository, fetches exactly that commit with depth 1, detaches at `FETCH_HEAD`, and asserts `git rev-parse HEAD` equals the pinned commit |
| Modules            | `document_knowledge` `19.0.1.0.1`; `document_page` `19.0.1.0.2`; `document_page_project` `19.0.1.0.0`                                                                     |
| License            | Each selected manifest declares `AGPL-3`; the OCA repository `LICENSE` is GNU AGPL v3                                                                                     |

The source is acquired in a disposable local image build from the public OCA repository.
No checkout, source tarball, license artifact, token, or host path is committed to this
repository. The build fails if the fetched commit differs from the recorded immutable
commit.

### Dependency graph

`document_knowledge` depends on Odoo `base`. `document_page` depends on `mail`,
`document_knowledge`, and `html_editor`. `document_page_project` depends on `project`
and `document_page`. The resulting Odoo core dependency closure used by this fixture is
`base`, `mail`, `html_editor`, and `project` plus the three selected OCA modules.

AGPL-3 is a material deployment constraint. This fixture is local and non-public. Before
any public or production service uses these modules, release owners must perform a legal
review of the actual combined deployment and its corresponding-source obligations. This
record does not provide legal advice or authorize a release.

## Exact source contract and runtime probe

The verifier's `oca_document_page_probe.py` runs after the clean install and asserts the
following against the installed fixture. It emits the resulting JSON contract in the
command output.

### Models, fields, and hierarchy

- `document.page` fields: `name` (required title), `type` (`content` or `category`),
  `active`, `parent_id`, `child_ids`, `content`, `template`, `history_head`,
  `history_ids`, `company_id`, `menu_id`, `backend_url`, `project_id`, and `image`.
- `document.page.history` fields: `page_id`, `name`, `summary`, `content`, `diff`, and
  related `company_id`.
- `project.project` receives `document_page_ids` and `document_page_count` from
  `document_page_project`.
- `parent_id` targets category pages; native `_check_parent_id` rejects recursive
  categories. `child_ids` builds the page/category hierarchy.
- Page content uses the native computed/inverse path. Changing content creates a
  `document.page.history` row and updates the history head.

### Editor, history, templates, and lifecycle

- The editor is OCA's standard HTML `content` field, not a local editor implementation.
- `document.page.history` is the page revision mechanism; its `page_id` uses
  `ondelete="cascade"`.
- Category `template` is the supported source mechanism: the native `parent_id` onchange
  copies it to an otherwise-empty new content page. No proprietary `knowledge.article`
  records are assumed or seeded.
- Archive is `active=False`. Native `document.page.unlink()` removes attached `menu_id`
  records, and history is removed by the page-history cascade. The probe creates,
  archives, and unlinks disposable pages and asserts that the page and history no longer
  exist after deletion.

### Actions, ACLs, record rules, and company behavior

The probe resolves these stable XML IDs: `document_page.view_wiki_form`,
`document_page.view_wiki_tree`, `document_page.view_wiki_filter`, and
`document_page_project.action_document_page_projects`.

OCA groups are `document_knowledge.group_document_user`,
`document_page.group_document_editor`, and `document_page.group_document_manager`. The
selected access CSV grants read-only page/history access to users; editors can
read/write/create pages and histories but cannot unlink pages; managers can unlink
pages. The fixture probes these ACL rows directly.

Both `document.page` and `document.page.history` have a global multi-company rule:
`company_id` must be false or belong to the caller's `company_ids`.
`document.page.company_id` defaults to the active environment company, and history
inherits it from the page. The probe confirms the fields and rule configuration. Any
future relation must still test a non-admin, multi-company caller through its own public
operation; this fixture does not authorize `sudo()`.

## Lifecycle commands and expected evidence

`./scripts/verify-oca-document-page` performs, in order. Its authoritative verifier
module declaration is
`MODULES=document_knowledge,document_page,document_page_project,project_agile,project_scrum,project_agile_document_page,project_scrum_document_page`:
the first three are the selected OCA modules, `project_agile` and `project_scrum` are
the existing Community modules, and the final two are the optional local bridges.

1. Compose syntax validation and pinned-image build.
2. Clean `--init` of that exact seven-module set with its matching test tags.
3. Runtime probe of models, fields, XML IDs, ACL rows, global rules, hierarchy, history,
   template handling, archive, delete, and Project page linkage.
4. Fresh install followed by targeted `--update` of that exact seven-module set with
   tests.
5. Fresh install, dependency-safe ORM uninstall in reverse order
   (`project_scrum_document_page`, `project_agile_document_page`, `project_scrum`,
   `project_agile`, `document_page_project`, `document_page`, `document_knowledge`),
   then reinstall of the exact seven-module set with tests.

The verified output must contain all three lifecycle success lines and
`OCA_DOCUMENT_PAGE_RUNTIME_CONTRACT=`. A failure is a fixture failure, not an invitation
to guess an OCA API.

## PR #641 gate

Rechecked 2026-09-27 through GitHub's public API: OCA PR #641,
`[19.0][MIG] document_page_project_task`, is `state=open`, `merged_at=None`, base
`19.0`, and head `b790965e66a008da4421a8763c489037bbb8a43a`. It is unmerged.

Its exact head may be evaluated only in a disposable fixture. It is not copied,
vendored, or a production dependency. A later Task connector may use its capability only
after it is merged into the authoritative OCA 19.0 branch, a new immutable merged commit
is recorded, and this fixture is rerun against that commit. Until then, no Task-page
relation is authorized.

## Recovery

The fixture has no persistent volume and no public listener. If it fails, retain the
command output, inspect the pinned source/image identity, and rerun after correcting the
documented fixture—not after changing a mutable tag or substituting an Enterprise API.
Do not use the fixture to reset, delete, or alter a shared database or service.
