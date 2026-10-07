# M8 cumulative hardening and acceptance matrix

This slice extends exact approved parent `bbecebccbac0ee323a372f101fed4177885a8cea`
on `feature/t_f1a8ee89-m8-solution-definition`. Accepted scope remains the verbatim
[scope record](../milestone-8-approved-scope.md); ADR-013 remains the architectural
contract. Odoo 19 Community is the runtime under test, not Enterprise or a generic
OCA certification. Core and optional Scrum bridge retain LGPL-3 and their existing
`project_agile` / `project_agile_solution,project_scrum` dependencies. No new
package, optional backend, schema, financial or public/portal service is added.

## Scope-to-executable proof

All paths below are relative to `addons/project_agile_solution/tests/`, except
bridge tests in `addons/project_agile_solution_scrum/tests/`. These are acceptance
examples, not universal authorization/security claims. The discovery gate derives
all declaring classes/methods from imported test files; a selected native addon
cannot pass because a helper/inherited duplicate merely started elsewhere.

| Accepted scope or adversarial boundary | Executable proof |
| --- | --- |
| Optional SOW / internal brief; separate approvals | `test_solution_baseline.py`: `test_sow_and_spec_approval_are_independent`, `test_expanded_spec_needs_explicit_changed_sow_successor`; rendering synthetic integration scope revision requires SOW then spec approval. |
| Stable immutable baselines, actual nested content, successors/archive | Baseline ORM/import/x2many/sudo/context mutation tests; requirements review sealing, inverse membership and mixed-visible/hidden tests; rendering exact reproducibility after rename/archive/successor. |
| FR/NFR keys, rationale/priority/evaluation; no parallel Tasks | Requirements stable keys, actual working content, native forms and three scenario seeds; lineage native Tasks-only seeds; Task trace many-to-many exact edges preserve manual descriptions/state/criteria/points/order. |
| Narrative templates, questions/owner/resolution, decisions, business actors/domains | Requirements typed context/owner validation, explicit question resolution, existing Spike authority, full editable SOW skeleton copy/provenance tests. Actors do not create accounts/groups. |
| Deliberate preview, current source, exact links, authorized retry | Task trace preview/wizard, changed draft/head rejection, finite proposal/forged audit negatives, nonadmin/Task-create ACL deny, consumption/archive retention; no automatic planning. |
| Real duplicate intent race, not same-connection mocks | `scripts/solution_source_probe.py` calls imported `task_concurrency.run_probe`: create and link operations with distinct OS PIDs and PostgreSQL backend PIDs, a forced stale snapshot, native serialization failure and bounded full-transaction retry. Exactly one Task/edge/result. Baseline and requirement allocation/approval races also retained. |
| Frozen native Sprint evidence including v1/v2, draft/empty/pre-bridge | Bridge `test_sprint_context.py`: start/add/close, revision change before start, remove/complete/reopen/reestimate/carry, original commitment and failure rollback. `scripts/solution_scrum_probe.py` runs independent relink/start/add/close transaction races. No backfill or implicit approval. |
| Native selected working/exact rendering and completeness | Rendering QWeb HTML/PDF-entrypoint, native Form/export, direct report exact-ID/audience, escaping/no remote resource, cached read/reference revocation and attachment-disabled tests. Current loss of any required access refuses output rather than complete-looking omission. |
| Internal vs redacted customer audience | Rendering allowlist excludes internal narrative/requirements/owners/questions/decisions/actors/evidence; both audiences refuse inaccessible required closure. Customer projection is internally generated, not customer authentication or complete internal content. |
| Coverage/change impact without completion percentages | Rendering exact links/old heads, legitimate maintenance/unexplained work, unresolved questions, baseline changes, exact evidence categories and unselected comparison; hidden work refuses coverage. |
| Explicit acceptance authority/evidence distinct from Done/merge | Rendering exact authenticated historical approver, current access, criteria/evidence, immutable append-only withdrawal and exact superseded historical pair tests; reassignment/current manager flag cannot transfer authority. |
| Real nonadmin multi-project/company and forged context | Lineage private/custom Project rules and enabled-company selection; requirements cross-scope literal IDs/inverse/defaults; trace hidden Task/requirement search/group/export; hardening tests same-company readable foreign Project and multi-enabled manager in wrong active company. |
| Production HTTP/RPC routes, not only direct Python calls | `test_solution_render_tour.py`: real `/web/dataset/call_kw` JSON-RPC read/export/snapshot/projection/coverage/approve with forged sudo/trusted/state/audience context after requirement revocation; reader acceptance-create authority denial; existing direct report HTTP Project/public denials. Exact Odoo 19 route inspected at upstream `8da213dc6785e097f2558dc2d648b588957786a1`, `addons/web/controllers/dataset.py`. |
| Atomic rejection and no partial native writes | Baseline batch document creation, requirement batch creation, trace injected post-Task/edge failure; hardening batch link first-edge/seal rollback and cached-intent/acceptance revocation; bridge mid-capture restores assignment/event/context and start state. |
| Synthetic end-to-end narratives | Rendering and browser materialize the public-informed portal, uncertain API-discovery and internal-no-SOW examples. Portal deliverable -> exact existing Task -> manual synthetic evidence -> authorized explicit acceptance. API uncertainty/Spike and separately approved hypothetical scope change; internal NFR/maintenance and bridge v1/v2 commitments. |

## Canonical lifecycle and bounded execution

Run the actual `./scripts/verify` through the operator-authorized local driver:

    python3 /home/molty/.hermes/scripts/odoo_m8_verify.py t_1f505e56 verify

Reviewers substitute their own registered same-card ID. The driver owns a fixed
`odoo-agile-m8-test-<task>` namespace, isolated internal network/no published ports,
read-only source/config, declared DB/filestore volumes and exact cleanup receipts.
No direct Compose teardown, shared/live service or customer DB is a target.

Canonical verification retains M1-M7 tests, Hoot/browser and independent-process
Git policy/current-delivery association recovery. It adds persisted-data optional
lifecycles on `odoo_agile_verify_install` before aggregate install:

- Core alone: install, baseline/requirement/intent race proof, seed approved scope,
  acceptance and consumed existing-Task intent; targeted update checks byte-exact
  snapshot/projection/manual evidence/retry result and native work. Uninstall core
  then verify native work unchanged; reinstall has no fabricated solution history
  or consumed intents. Scrum/Git/Sales/document backends remain absent.
- Bridge alone with its declared dependencies: install and native event races;
  seed approved scope/consumed intent/acceptance and committed Sprint context;
  targeted core/bridge update verifies exact frozen payload and native event/Task.
  Remove only bridge and verify native Sprint/commitment and core intent remain;
  reinstall marks old event `not_available` without context backfill. A new native
  reestimate captures current exact links without rewriting that old marker.
- Aggregate: clean install on install DB, clean schema plus targeted upgrade on
  `odoo_agile_verify_upgrade`, dependency-reversed uninstall/reinstall on
  `odoo_agile_verify_reinstall`. Every tested phase requires all imported M8
  declared methods, including lineage/hardening/HTTP and optional bridge. Selected
  native skipped methods and failure summaries fail the stream gate; upstream process exit is retained by
  Bash `pipefail`. AST/parser tests are not a native execution substitute.

Non-root readability: check reviewed public files and directory traversal first.
Only exact allowlisted M8 test inputs may gain a missing other-read bit; compare
SHA-256 bytes and tracked Git modes before/after. No credential/environment file,
deferred `t_0286b468`, generic fixture refactor or capability pin is changed.

## Bounded performance, not a global SLA

Coverage collections cap caller rows at 1001 to refuse more than 1000. The narrow
elevated deny count now also uses `limit=1001`; compare only cardinality and never
return its privileged IDs/counts. This preserves denial of any hidden required row
without doing an uncapped exact count. SQL planner cost and custom rule complexity
remain deployment-dependent; a row limit is not a latency/scan limit.

A native nonadmin regression checks bounded-count arguments while executing the
real ORM, exact collection boundary/over-limit and hidden-row denial (temporarily
reducing only the test limit to three), and at most 20 SQL queries for a warm
12-Task collection. It logs actual observed queries. This collection-helper budget
is not a query/latency promise for full closure/rendering/large Projects. Per-row
current authorization remains necessary; split initiatives rather than bypassing
limits with sudo. No large-tenant or load/concurrency throughput claim is made.

## Migration, backup, recovery and retention

Same-version targeted updates are tested against persisted synthetic history;
this is not an Odoo major-version migration. Before any real migration/uninstall,
obtain separate operator approval and take a consistent DB plus filestore backup
with the exact addon/source/version/config identity. Test restoration in an
isolated environment; compare counts, frozen payloads/digests, revision membership,
current Project/company/Task rules, historical event markers and consumed intent
Task IDs before enabling deliberate creation. Never repair by regenerating Tasks,
backfilling old context from current links, raw state writes or inferred acceptance.

Uninstall deletes M8 tables/fields and is NOT archival. Native Tasks and Sprint
history survive removal of their optional extensions, but lost M8 traceability
cannot be recovered from them alone. Only a verified consistent backup can restore
it. Roll back source and restore DB/filestore together if upgrade verification
fails; do not run older code over an unverified newer schema or retry partial
transactions. A serialization failure retries the whole transaction, never commits
partial business writes. Corrections append successors/rejections/withdrawals.

No automated purge/retention cron or report attachment cache is introduced.
Authorized operators choose retention/export distribution under their policy;
export copies and business-sensitive baseline/evidence text are not access-revoked
when the source later becomes inaccessible. Keep secrets and credentials out of
narratives/evidence. Recovery SQL/admin code is the trusted root, not tamper-proof
protection or authorization from a context hint.

## Evidence and gates

Initial RED evidence preserves omitted-lineage and false-pass failure-summary
parser regressions plus native uncapped-count failure. An initial unreadable new
test-file run and a test-fixture late access error are retained, not called proof.
An additional genuine RED rejects an otherwise complete stream with a skipped
native browser method: Odoo 19 `tests/result.py` logs a skip but may still report
zero failures/errors, so a start-line plus summary is insufficient. The gate
removes skipped selected methods from observed proof. Other addons are not widened
into this M8 AST contract; their existing process/test/browser checks remain.
Another genuine RED demonstrates that all start lines with no native result summary
passed the old gate. Selected M8 execution now also requires a nonempty successful
native result summary; truncated/source-only streams cannot supply that proof.
The persisted-core retry passed, then genuine bridge seed execution exposed a
fixture-only JSON serialization error for native event datetimes. A focused
RED/GREEN covers exact ISO timestamp precision and relational normalization;
native bridge update/removal/reinstall remains required proof of preservation.
Green results and exact full commit are recorded in the same-card handoff with
real exit statuses, native discovery markers and capability cleanup receipt.

Gilfoyle must independently review that identical clean SHA; c1ph3r assessment,
cumulative approval, guarded local integration, Jimmy's separate publication latch
and publication remain downstream. No universal security, customer/production,
legal/SOW sufficiency, actual API facts, production PDF output or actual Odoo.sh
validation follows from these synthetic portable-HTML/native tests.
