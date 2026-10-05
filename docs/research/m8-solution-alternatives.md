# M8 public guidance and native/OCA alternative discovery

## Evidence bounds

Accessed 2026-10-05, rechecking the preserved 2026-10-01 discovery. No real customer
SOW, interface specification or observed customer acceptance exists. These sources
inform synthetic design inputs, not legal advice, market validation or a universal
contract template. ADR-013 chooses the optional boundary; this note records why.
Public acquisitions are identified by URL and immutable revision below; source hashes
and access timestamps are in `m8-source-receipts.json`. Runtime source is separately
checked by the canonical disposable Odoo probe, not inferred from upstream HEAD.

## Primary guidance

- [FAR 37.602](https://www.acquisition.gov/far/37.602), displayed FAC 2026-01,
  effective 2026-03-13: distinguish statement of objectives from performance work
  statement, describe required results and measurable evaluation, state purpose,
  scope/background and constraints. This is US federal procurement guidance, not
  an applicable legal mandate or a private-software SOW industry standard. Reuse
  results/evaluation/boundaries; do not import financial incentives or legal clauses.
- [NASA Systems Engineering Handbook appendices](https://www.nasa.gov/reference/system-engineering-handbook-appendix/),
  Appendix C requirement-writing guidance and Appendix D verification matrix:
  identifiable, clear/verifiable requirements, rationale/assumptions and traceable
  verification. Reuse identity, rationale and verifiable expectations, not NASA
  organizational authority or a complete systems-engineering process.
- [Official Odoo 19 licensing](https://www.odoo.com/documentation/19.0/legal/licenses.html):
  Community LGPLv3, Enterprise separate proprietary terms. Existing repository
  manifests stay LGPL-3. No Enterprise/OPL dependency or license change is selected.
  Public visibility does not establish open-source compatibility for proprietary code.

## Exact native implementation, not today's branch

Tested image is Odoo 19 Community `19.0-20260908`, upstream source revision
`8da213dc6785e097f2558dc2d648b588957786a1`, image identity recorded in the task's
runtime discovery. Current upstream 19.0 on recheck is
`b55592d4f08e5f1ab528103861fb7e756190d7ff` (2026-10-05); it is NOT the runtime API.
Pinned source links use prefix
`https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/`:

| Source | Reused mechanism / exact boundary |
| --- | --- |
| `addons/project/models/project_project.py`, `addons/project/security/project_security.xml` | Native Project company/privacy/follower rules and Manager/User groups; current rule composition rather than duplicating follower visibility. |
| `addons/project/models/project_task.py` | Native Task identity, hierarchy/dependencies, ordinary creation/workflow; suite Agile keys/types/criteria remain authoritative. |
| `odoo/orm/models.py` | `check_access`, `_filtered_access`, batched ORM, `BaseModel._search` subquery and company enforcement. `export_data` additionally requires `base.group_allow_export`; test a permitted export before denied-record export. |
| `odoo/orm/domains.py` | `Domain` composition, `any/any!` and search-field hooks. Rule SQL is optimized on sudo by `_search`; do NOT assume `any` inside `ir.rule` checks related Project access. |
| `odoo/addons/base/models/ir_rule.py` | Rule caching/composition and current-user evaluation; no cached materialized list of accessible Projects. |
| `odoo/addons/base/models/ir_actions_report.py` | Native report/QWeb flow, `_get_report_values`, `_render_qweb_html`; actions/routes/sudo/attachment reuse do not establish audience authority. |

The skeleton's global searchable access rule compiles a current-user Project subquery
via `sudo(False)`, not elevated discovery. `_search` is a private exact-version seam;
keep independent native custom-rule/search/read/export regressions across upgrades.
Initial real tests exposed the plain `any` rule leak; retaining that failed run is
important evidence against source-only claims. Native Project's transitive dependencies
include analytic/base_setup/mail/portal/rating/resource/web/web_tour/digest; native portal
installation does not expose solution records. No solution controller/public ACL exists.
Native `ir.sequence`, constraints, record rules, views and QWeb are chosen; do not copy
core methods, generic document editor/history or a second Task engine.

## OCA 19.0 candidates and decision

Rechecked branch trees/manifests/README maturity and native model excerpts. Project
repository revision `2ba869c7466476ec7fb913ae55a1ee49be62392b` (2026-10-02), Knowledge
`dbf80041c7c0e90337ef1a6d3be84b607da3501c` (2026-10-01). Both show recent repository
activity, not a guarantee of module maintenance or response time. All listed README
maturity badges are Beta; absent manifest `development_status` is not Production status.
Per-module maintenance cadence, compatibility and full runtime tests would remain an
adoption gate. No candidate is adopted, so this research is not runtime certification.

Pinned URL patterns:

- `https://github.com/OCA/project/tree/2ba869c7466476ec7fb913ae55a1ee49be62392b/<addon>`
- `https://github.com/OCA/knowledge/tree/dbf80041c7c0e90337ef1a6d3be84b607da3501c/<addon>`

| Candidate | Version / license / direct dependencies | Overlap, hosting and decision |
| --- | --- | --- |
| `project_task_description_template` | 19.0.1.0.2 / LGPL-3 / project | Reusable Task description; onchange appends template text to mutable Task description. Not immutable requirement/document content or independent approval. Existing manual Tasks must not be rewritten; no adoption. Ordinary addon, but its actual extension set still needs staging. |
| `project_task_code` | 19.0.1.1.0 / AGPL-3 / project | Generic sequential Task code; native suite already owns Agile Task keys. Hooks/dependency overlap and AGPL distribution obligations; not requirement identity. Do not duplicate or replace existing keys. |
| `project_key` | 19.0.1.0.0 / LGPL-3 / portal, project | Project/Task key overlap; would collide with delivered key semantics. Not requirements/approval. |
| `project_version` | 19.0.1.0.0 / AGPL-3 / project | Release/version relationships belong to deferred ADR-005, not actual specification content revisions. Named maintainer `lbarry-apsl`; adoption would widen M8 into excluded release management. |
| `document_knowledge` | 19.0.1.0.1 / AGPL-3 / base | Generic knowledge foundation, optional existing M4 boundary; not mandatory M8 core. |
| `document_page` | 19.0.1.0.2 / AGPL-3 / mail, document_knowledge, html_editor | Page/history/report UI; useful optional general docs but not revision-scoped requirements, approved closure or frozen Sprint context. Would impose the unwanted editor/backend dependency. |
| `document_page_approval` | 19.0.1.0.0 / AGPL-3 / document_page, mail | Page approval/history workflow; no entire M8 identity/membership/Task/Sprint contract. Do not fork/copy approval code or claim equivalent semantics. |
| `document_page_project` | 19.0.1.1.0 / AGPL-3 / project, document_page | Project/page link, named maintainer `LoisRForgeFlow`; optional docs navigation, not exact-requirement Task linkage. |

Knowledge transitive chain is document_page -> document_knowledge/base plus native
mail/html_editor; project bridge also brings native project dependencies. Approval adds
mail but does not remove the document chain. Any future optional adoption preserves
upstream attribution/AGPL obligations, requires actual target-image tests, transitive
license review and deployment-specific Odoo.sh staging; LGPL/AGPL compatibility does not
mean Enterprise/OPL compatibility. No SDK/queue/daemon dependency is selected here.

`OCA/project-agile` 19.0 at `df78fbaf857ba95d0ef43862410791da1ee51c8d`
(2025-09-30) contains only `.github`, not an available migrated Scrum/requirements suite.
`project_template` and `project_task_project_template` were absent from the checked
project branch/tree and manifest URLs returned 404; this bounded observation is not a
claim that the ecosystem has no alternatives. Native templates still do not meet the
separate immutable specification/Task-intent contract without deliberate domain logic.

[OCA/knowledge PR 641](https://github.com/OCA/knowledge/pull/641) remained open/unmerged
on 2026-10-05, updated 2026-09-09, head
`b790965e66a008da4421a8763c489037bbb8a43a`. Do not treat an unmerged Task-document
connector as an available core API. Its standing M4 optional blocker remains separate.

## Selected boundary and residual risks

`project_agile_solution` depends only on existing LGPL-3 `project_agile`, transitively
native Community project. The small custom domain is solution lineage plus later
actual document/requirement/context revisions, auditable edges/intents and acceptance;
it reuses generic native mechanisms rather than rebuilding a wiki/task engine.
`project_agile_solution_scrum` is a downstream optional bridge to existing Scrum history,
not a new scheduler or mandatory dependency. No other candidate changes suite licensing.

This is Odoo-compatible private repository work, not an OCA-conformity attestation.
No repository-pinned pre-commit/pylint-odoo gate exists. Disposable native lifecycle,
nonadmin/custom-rule/company tests and existing browser/concurrency regressions are
required. Customer fit, legal sufficiency, unknown API details and actual Odoo.sh/runtime
activation remain unverified; none is authorized by root implementation/review.
