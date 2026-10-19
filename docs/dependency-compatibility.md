# Dependency and source compatibility

The base product targets self-hosted Odoo 19 Community; custom functionality must remain
deployable on Odoo.sh. Enterprise integrations are optional, not Community core
dependencies. Validate the actual installed extensions and hosting behavior separately;
backend APIs are not interchangeable. Existing licenses remain per manifest. OCA-aligned
tooling is not full OCA conformity.

Native Project Tasks, hierarchy, dependencies, ORM, ordinary views and `ir.cron` remain
the foundation. `queue_job`, external queue runners and host-service customization are
unsupported. Git facts are separate from workflow policy, and Solution requirements are
intent rather than another Task system.

The selections below explain compatibility decisions, not current upstream status or
production certification. Before changing a dependency, reassess its exact APIs,
transitive licenses, maintenance and behavior on the deployed runtime.

## Requirements and document guidance

- [FAR 37.602](https://www.acquisition.gov/far/37.602), consulted with FAC 2026-01,
  effective 2026-03-13, distinguishes objectives from performance work statements and
  emphasizes results, evaluation, scope and constraints. It is US federal procurement
  guidance, not a mandate or private-software SOW standard. The suite borrows no
  financial incentives or legal clauses.
- [NASA Systems Engineering Handbook appendices C and D](https://www.nasa.gov/reference/system-engineering-handbook-appendix/)
  informed identifiable, verifiable requirements, rationale and traceability, not NASA
  organizational authority or a mandatory engineering process.
- [Odoo 19 licensing](https://www.odoo.com/documentation/19.0/legal/licenses.html)
  distinguishes Community LGPLv3 from proprietary Enterprise terms. No Enterprise or OPL
  dependency is selected for Solution core; public repository visibility does not
  establish proprietary-code license compatibility.

These sources informed synthetic design examples, not customer validation, actual
external-interface facts, a universal template or legal advice.

## Native source decisions

Solution discovery inspected Community `19.0-20260908` at upstream
[`8da213dc6785e097f2558dc2d648b588957786a1`](https://github.com/odoo/odoo/tree/8da213dc6785e097f2558dc2d648b588957786a1).
That immutable selection, not a moving upstream branch, explains its API decisions. The
current verifier builds the runtime declared in its Compose/Docker inputs; check the
verification log for the actual Odoo build. Historical source inspection is not a
runtime pin or assurance for later extensions.

Paths in the table refer to that immutable source revision.

| Source                                                                                     | Reused behavior and compatibility boundary                                                                                                         |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `addons/project/models/project_project.py`, `addons/project/security/project_security.xml` | Native company/privacy/follower rules and Manager/User groups; preserve custom/native rule composition.                                            |
| `addons/project/models/project_task.py`                                                    | Native identity, hierarchy, dependencies and ordinary creation/workflow; suite Agile keys/types/criteria remain authoritative.                     |
| `odoo/orm/models.py`                                                                       | `check_access`, `_filtered_access`, batched ORM, company enforcement and `_search` subqueries. Native export also needs `base.group_allow_export`. |
| `odoo/orm/domains.py`                                                                      | `Domain`, `any/any!` and search hooks. Rule compilation on sudo means relational `any` alone does not prove related Project access.                |
| `odoo/addons/base/models/ir_rule.py`                                                       | Current-user rule composition and caching; do not cache materialized visible-ID lists in rules.                                                    |
| `odoo/addons/base/models/ir_actions_report.py`                                             | QWeb/report-value flow; actions, routes, sudo and attachment reuse do not establish audience authority.                                            |

Solution rules build an unevaluated current-user Project subquery through `sudo(False)`.
The private `_search` seam is upgrade-sensitive and needs retained
custom-rule/search/read/export regressions. Native Project transitively brings analytic,
base_setup, mail, portal, rating, resource, web, web_tour and digest; portal's
installation does not expose Solution records. No Solution public ACL or custom
controller is added. Reuse sequences, constraints, rules, views and QWeb rather than
copied core methods, a Task engine or a generic editor/history store.

## OCA alternatives considered for Solution

The 2026-10-05 survey inspected OCA Project at
[`2ba869c7466476ec7fb913ae55a1ee49be62392b`](https://github.com/OCA/project/tree/2ba869c7466476ec7fb913ae55a1ee49be62392b)
and Knowledge at
[`dbf80041c7c0e90337ef1a6d3be84b607da3501c`](https://github.com/OCA/knowledge/tree/dbf80041c7c0e90337ef1a6d3be84b607da3501c).
The listed README maturity badges were Beta, not Production; repository activity was not
a guarantee of per-module maintenance. These are surveyed alternatives, not changes to
the selected Document Page fixture below.

| Candidate                           | Version; license; direct dependencies                     | Decision                                                                                                                         |
| ----------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `project_task_description_template` | 19.0.1.0.2; LGPL-3; project                               | Appends mutable Task description through onchange, not immutable intent or independent approval. Do not rewrite manual Tasks.    |
| `project_task_code`                 | 19.0.1.1.0; AGPL-3; project                               | Global company-unique sequential code overlaps the suite's project-local immutable keys; not requirement identity.               |
| `project_key`                       | 19.0.1.0.0; LGPL-3; portal, project                       | Project/Task key overlap, not requirement revision or approval.                                                                  |
| `project_version`                   | 19.0.1.0.0; AGPL-3; project                               | Release/version semantics remain deferred in ADR-005, distinct from specification revisions. Surveyed maintainer: `lbarry-apsl`. |
| `document_knowledge`                | 19.0.1.0.1; AGPL-3; base                                  | Optional general knowledge foundation, not mandatory Solution core.                                                              |
| `document_page`                     | 19.0.1.0.2; AGPL-3; mail, document_knowledge, html_editor | Page/editor/history, not exact requirement membership or frozen Sprint context.                                                  |
| `document_page_approval`            | 19.0.1.0.0; AGPL-3; document_page, mail                   | Page approval is not the complete Solution identity/reference/Task contract. Do not copy its workflow.                           |
| `document_page_project`             | 19.0.1.1.0; AGPL-3; project, document_page                | General Project navigation, not exact-requirement Task linkage. Surveyed maintainer: `LoisRForgeFlow`.                           |

Document Page transitively brings `document_knowledge/base`, native mail and
html_editor; its Project bridge adds native Project dependencies. Approval adds mail
without removing that chain. Any future adoption must preserve attribution, review the
actual transitive licenses and run target-runtime/staging checks. LGPL/AGPL
compatibility is not proof of Enterprise/OPL compatibility.

`OCA/project-agile` 19.0 at `df78fbaf857ba95d0ef43862410791da1ee51c8d` (2025-09-30)
contained only `.github`, not a migrated Scrum/requirements suite. `project_template`
and `project_task_project_template` were absent from the surveyed Project tree and
manifest URLs. This is a bounded finding, not proof that the whole ecosystem lacks
alternatives.

## Selected Document Page runtime

The separate optional fixture selects OCA `knowledge` 19.0 commit
[`e4a12c0c99866a5850840941d6f7ae3b3b27280d`](https://github.com/OCA/knowledge/tree/e4a12c0c99866a5850840941d6f7ae3b3b27280d)
and these AGPL-3 modules:

- `document_knowledge` 19.0.1.0.1: `base`;
- `document_page` 19.0.1.0.2: `mail`, `document_knowledge`, `html_editor`;
- `document_page_project` 19.0.1.0.0: `project`, `document_page`.

The fixture's Dockerfile fetches and verifies that exact commit. Its Odoo image is
`odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c`;
PostgreSQL is
`postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24`. The
later alternatives survey does not upgrade these selections.

Run `./scripts/verify-oca-document-page` from the repository root. It exercises these
three OCA modules, Agile/Scrum and optional `project_agile_document_page` and
`project_scrum_document_page` bridges: install, targeted update, reverse-dependency
uninstall/reinstall and a runtime contract probe. Its three disposable databases are
`odoo_agile_oca_document_page_install`, `odoo_agile_oca_document_page_upgrade` and
`odoo_agile_oca_document_page_reinstall`. A fresh Compose project, PostgreSQL tmpfs, no
published port and scoped teardown isolate the fixture; never target a shared database.
The normal Community entrypoint remains `./scripts/verify`.

OCA owns `document.page` content, category hierarchy, editor, templates, archive and
history. `parent_id` accepts categories and rejects recursion. Category `template` is
copied by the native parent onchange into an empty new page. Computed/inverse content
updates create `document.page.history`. Native page unlink removes its menu and cascades
history: archive when history is needed. `document_page_project` owns `project_id`,
Project page relations/counts and `document_page_project.action_document_page_projects`;
do not duplicate them.

Native page/history rules allow company-less pages or the caller's companies. Document
users read; editors create/edit without page unlink; managers may unlink. Bridges must
independently enforce caller Project/page/company access without disclosing inaccessible
titles, counts or actions through sudo. Enterprise `knowledge.article` is not an OCA
API. Review AGPL corresponding-source obligations for the actual combined deployment
before public or production use.

The [Task connector gate](adrs/006-knowledge-relationship-model.md#pr-641-gate) remains
separate. OCA Knowledge PR 641 was open/unmerged on the 2026-10-05 survey, head
`b790965e66a008da4421a8763c489037bbb8a43a`; this is not a current merge-status claim.
Unmerged code is not copied, vendored or used as a production dependency.

## Git adoption and deferred capabilities

[ADR-007](adrs/007-oca-project-git-adoption-strategy.md) retains the Git adoption
rationale and immutable source links. The 2026-09-24 survey found Project PR 1792 to be
a 17.0 draft, not installable 19.0 Git connectors; `version-control-platform` 19.0 was
scaffolding rather than an addon catalog. Mutable Task-name and `taskid#` matching do
not meet immutable project-local keys. The suite implements the durable
ingress/facts/association boundary in
[ADR-011](adrs/011-git-facts-and-visibility-contract.md) and optional native-cron policy
in [ADR-012](adrs/012-git-workflow-policy-contract.md).

Release/version remains deferred in ADR-005. Jira import must adapt to native
Task/Sprint semantics rather than reshape the runtime. No custom wiki, Git hosting, CI
engine, automatic backlog/Sprint generation or external authentication service is
selected. Solution core uses only existing Agile/native Project; its optional Scrum
bridge supplies frozen history, not another scheduler.
