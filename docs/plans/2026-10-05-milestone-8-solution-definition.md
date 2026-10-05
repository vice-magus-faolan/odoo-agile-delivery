# Milestone 8 gap map and serial implementation plan

## Bounded outcome contract

Beneficiary: an Agile team explaining agreed solution intent, uncertainty, delivery
coverage and explicit evidence-bound acceptance. Evidence: one prospective user's
request; customer demand and market fit are unvalidated. All examples are synthetic,
not a real SOW or a universal/legal standard. Approved scope is copied unchanged at
`docs/milestone-8-approved-scope.md` (SHA-256
`5a3e4a5c374d3d9d668031ae358825976e6beb0831eaa51f5283273ba0c08326`).
ADR-013 owns model/API/authority decisions; later workers cannot quietly remove scope.

Base: `5376f2d2c2ada5c7e18e73b673076343671992ca` (published M7).
Lane: `feature/t_f1a8ee89-m8-solution-definition`, registered remote worktree
`/srv/projects/kanban-worktrees/odoo-agile-delivery/t_f1a8ee89-m8-solution-definition`.
Canonical repository `/srv/projects/odoo-agile-delivery`; target `refs/heads/main`.
The local Hermes coordination workspace is not a source checkout.

Review: each builder commits a clean artifact, hands off full SHA/test commands/results
and requests native same-card review by Gilfoyle. Reviewer must independently verify the
same SHA and record `approved=true`, `review_outcome=approved`, `reviewed_commit` equal
to that SHA. Request changes returns the same card/lane. Downstream consumes the exact
approved parent commit, not card-order assumptions. Security/cumulative/delivery and
publication gates remain distinct. No per-component reviewer/remediation cards.

Allowed: this branch's source/docs/tests and isolated disposable verification with the
approved task-scoped driver. No main advancement, push/PR/tag/release, deployment/restart,
credentials/provider/profile/Hermes-core/live customer changes or persistent/shared
resource deletion. Only the delivery card may guarded-integrate locally; publication
needs the separate Jimmy latch. No production/customer outcome observation is claimed.

## Explicit gap map

| Area | Delivered at published M7 | M8 required, not yet implemented in root | Exclusions/later work |
| --- | --- | --- | --- |
| Delivery truth | Native Tasks, Agile keys/types/criteria/hierarchy/dependencies/backlog; Scrum/history/analytics; planning UI | Exact requirement-revision links, deliberate idempotent creation, frozen optional Scrum context | Parallel issue system, automatic planning/regeneration |
| Intent | Native Task criteria; optional M4 documentation | Optional SOW/internal brief, separate document approval chains, distinct working revision and immutable actual baselines | Sales/e-sign/legal/contract/billing engine |
| Requirements | None; Task is not requirement | Stable FR/NFR keys/revisions, rationale/priority/verification, evidence-bound explicit acceptance | Full test-management engine, Done/merge inference |
| Context | Native documentation remains authoritative for general docs | Reusable solution section templates, owned questions/resolutions/Spikes, decisions/consequences, actors/domains | Custom wiki/editor/history or mandatory OCA/Enterprise backend |
| Readability/privacy | Native Project/Task rules, document and Git visibility | Exact/current native rendering, customer projection vs internal full completeness, fail-closed inaccessible closure | Actual customer portal/public route or customer exposure |
| Coverage/impact | Sprint analytics and Git observations | Honest unlinked/maintenance/old-revision/question/changed/accepted categories | Misleading aggregate completion %, release management |
| Root artifact | No solution addon at base | Root now adds only lineage identity/authority/views, imported tests and synthetic native seeds; contract/plan/research | Root does not claim approved baselines, links, acceptance or complete M8 |
| Operations | Canonical M1-M7 lifecycle/browser/concurrency gate | Add isolated solution install plus cumulative lifecycle discovery and adversarial M8 regression | Runtime activation, provider expansion, Jira migration |

## Card-to-acceptance mapping (seeded graph, no new cards)

| Phase/card | Acceptance owned here | Bite-sized implementation and verification |
| --- | --- | --- |
| Root `t_f1a8ee89` | Full approved contract/gap map/plan/research/three fixtures; actual minimal optional install and negative authority boundary | Read baseline/scope; recheck native/OCA/public guidance; commit ADR-013 and exact fixture data; install lineage skeleton; run independent/canonical checks; exact-SHA same-card review. |
| Baseline `t_19c877cb` | Stable document identity, actual immutable content/ordering/references, separate SOW/spec approval, working draft, recovery | Add document/revision/membership and template-copy boundary; implement action-only review/approval/supersession and successor locking; prove raw ORM/x2many/sudo/context immutability and archived-reference readability; native views, isolated install/update/uninstall/reinstall. |
| Requirements `t_913965f7` | Stable project requirement keys/revisions; FR/NFR intent and context traceability | Native sequences/constraints; small typed context identity/revision model; owned question/resolution/significance/Spike and decision links; actor/domain narrative; seal actual children on use; verify cross-scope hidden IDs, key/revision races and imported nonadmin tests. |
| Traceability `t_2bedc90a` | Existing-Task many-to-many exact revision edges; preview-confirm retry-safe Task creation; no overwrite; optional historical Scrum context | Link boundary and maintenance reason first; durable intent/wizard/confirm next; add `project_agile_solution_scrum` bridge/private scope-event seam and capture status; add separate installation/lifecycle coverage; independent-process duplicate/stale/relink/Sprint capture/rollback tests; no mandatory Scrum in core. |
| Rendering `t_a7974c61` | Readable native working/exact SOW/spec output and reusable templates; audience/export/privacy/completeness; coverage/change impact and explicit acceptance | QWeb report-value boundary/forms; default SOW/internal templates with project overrides; internal vs customer projections/direct report route tests; honest categorized coverage; append-only named evidence-bound acceptance/withdrawal; old-baseline and missing/inaccessible-reference tests; meaningful native browser flow. |
| Verification `t_1f505e56` | All three scenarios executable end-to-end; no partial state, required lifecycle/browser/concurrency regression | Promote JSON contract inputs into actual model fixtures in imported helpers without invented API truths; prove D1->existing Task->evidence->explicit acceptance; discovery revision and internal no-SOW/maintenance/Sprint v1-v2 flows; strengthen canonical discovery and failure propagation. |
| Security `t_4841a335` | Independent authority/privacy challenge of exact cumulative candidate | c1ph3r verifies genuine nonadmin/private-Project/custom-rule/multi-company/forged context; closure/read/search/group/export/report leak tests; normal elevation and retention/recovery boundaries. No implicit provider fallback. |
| Cumulative `t_f0b10ab9` | No dropped approved scope; exact combined SHA and all regressions | Read every approved handoff; reproduce full scope matrix, isolated core and bridge lifecycles, native forms/report/browser/concurrency evidence; same-card Gilfoyle review, no self-approval. |
| Delivery `t_002ae0a4` | Guarded local integration of exact approved M8 candidate | Coordinator checks current target/ancestry/cleanliness/no prior writer, guarded fast-forward under policy, then canonical verification/readback of integrated exact target. Not publication/deployment. |
| Approval `t_c009385c` | Exact human M8 publication latch | Jimmy explicitly approves exact delivered SHA and publication effects; no old M7/recovery approval inheritance. Remains independent typed human gate. |
| Publication `t_bcedc3b0` | Separately approved remote publication | Depends on delivery and approval; ordinary guarded main-only non-force publication and exact remote/local/tracking readback. No deployment, restart, tags or customer contact. |

Order is root -> baseline -> requirements -> traceability -> rendering -> verification
-> security -> cumulative -> guarded delivery; publication additionally waits for the
independent human approval. Existing cards remain the work queue. Approval of this root
contract is not approval of an unimplemented downstream behavior.

## Deterministic verification and evidence discipline

Repository baseline commands: `python3 -m unittest discover -s tests -p 'test_*.py' -v`,
`python3 -m compileall -q addons scripts`, `bash -n scripts/verify`, `git diff --check`,
and canonical `./scripts/verify`. No repo pre-commit/pylint-odoo configuration was found;
do not claim OCA conformity or invent a required command. Soft complexity warning 10,
justify/refactor over 15. Added functions remain deliberately small.

In this headless lane, execute the actual canonical script via the approved LOCAL driver:
`python3 /home/molty/.hermes/scripts/odoo_m8_verify.py t_f1a8ee89 verify`.
Descendants substitute their own card ID. The driver owns fixed read-only bindings,
internal DB-only networking/no ports, declared disposable databases and verified cleanup.
Do not modify its authority/digests or bypass it with raw Compose teardown.
For focused install use action `odoo --database odoo_agile_m8_test --init project_agile_solution
--test-enable --test-tags /project_agile_solution --stop-after-init --without-demo=True --log-level test`.
Every action has its own complete lifetime; shell cannot attach to a previous action's DB.

Canonical root adds `project_agile_solution` to modules/test tags, an independent optional
core install, native source probe, and reverse uninstall before `project_agile`, preserving
all existing M1-M7 native/browser/concurrency checks. Later bridge adds its own standalone
installation and dependency-safe lifecycle with no core dependency. Count actually
executed tests and reject missing/ignored modules or zero discovered target suites; exit
0 is insufficient. Check public addon/fixture directory search and file read permissions
for Odoo's non-root user; never chmod/read credential or environment files.

Failed discovery and tests remain evidence, never plausible substitutes. Root recovery
observed shell DB lifetime misuse (no existing DB) and unreadable addon silently ignored
with zero tests; neither is a valid pass. Receipts verify cleanup. Fix minimal cause,
retain original logs, rerun real native tests. Before handoff record exact full commit,
branch/base/worktree/cleanliness, changed files, commands/results/test counts, receipts
and failures/residual scope. Do not declare full M8 complete from root success.

Recovery: request changes on the same card; amend source on the same retained lane and
get a fresh exact-SHA review. Archive history, append successors, never regenerate Tasks
or infer old Sprint context. Shared/live recovery, publication and data deletion require
separate operator approval. Back up before any later migration/uninstall of real data.
