# M8 cumulative acceptance candidate — t_f0b10ab9

## Identity and decision boundary

This is a full-scope candidate for independent review, not builder approval. The
unchanged accepted scope is [the scope record](../milestone-8-approved-scope.md),
SHA-256 `5a3e4a5c374d3d9d668031ae358825976e6beb0831eaa51f5283273ba0c08326`. ADR-013 owns
the domain contract; the original root plan and every earlier run, including failures,
remain historical evidence rather than rewritten completion claims.

- Published base / unchanged target: `5376f2d2c2ada5c7e18e73b673076343671992ca`.
- Canonical repository: `/srv/projects/odoo-agile-delivery`; target `refs/heads/main`.
- Registered lane:
  `/srv/projects/kanban-worktrees/odoo-agile-delivery/t_f1a8ee89-m8-solution-definition`.
- Branch: `feature/t_f1a8ee89-m8-solution-definition`.
- Independently assessed implementation: `f260292cddd73cba29dacc30582c4c8a34a5dc8d`.
- This cumulative slice adds this acceptance/disposition record only. It does not change
  source, tests, dependencies, authority or the accepted scope. The exact new cumulative
  SHA and its newly executed results belong in the native handoff.

Odoo 19 Community `19.0-20260908`, exact upstream source
`8da213dc6785e097f2558dc2d648b588957786a1`, is the verified target. This repository is
Odoo-compatible, not an OCA-conformity claim. LGPL-3 remains unchanged. Core
`project_agile_solution` depends only on `project_agile` / native Community Project;
`project_agile_solution_scrum` depends on core plus `project_scrum`. No new external
package, Sales, Git, document backend, Enterprise feature or runtime service is needed.
Pinned native/OCA alternatives and license/dependency decisions remain in
[the discovery record](../research/m8-solution-alternatives.md).

## Approved scope → concrete acceptance examples

Test paths below are relative to `addons/project_agile_solution/tests/` unless
explicitly marked bridge. Tests are imported native behavioral suites, not only source
assertions. Full discovery, native result summaries and disposable receipts must pass in
the current exact-SHA run; this table alone proves no execution.

| Approved clause                                                           | Delivered boundary and executable evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Optional specification, stable lifecycle and exact immutable baselines | `test_solution_baseline.py`: `test_optional_internal_brief_and_exact_snapshot`, `test_review_freezes_content_and_explicit_return_reopens_draft`, `test_successor_is_distinct_and_supersession_preserves_content`, `test_approved_orm_import_x2many_and_sudo_mutations_fail`, `test_sow_and_spec_approval_are_independent`. Actual nested content, membership, ordered narrative and template provenance are frozen; approved records are not pointers to today's text. `test_solution_rendering.py::test_exact_baseline_stays_reproducible_after_rename_archive_and_successor` checks historical output.              |
| 2. Requirements, not Tasks                                                | `test_solution_requirements.py`: stable project keys/archive, working FR/NFR validation, review sealing, one exact revision per identity and distinct successors. Content includes rationale, priority, verification method and acceptance expectations. `test_solution_rendering.py`: exact acceptance criteria/evidence/authority, historical corrections and `test_acceptance_does_not_follow_done_or_merge_and_withdrawal_appends`. No Task-state or Git observer creates requirement acceptance.                                                                                                                 |
| 3. Supporting context, deliberately small vocabulary                      | Requirements suite: typed context/owner validation, explicit audited resolution, existing authorized Spike links, affected exact revisions, separate SOW/spec lineage, editable template copy and all three scenario records. `solution_fixture.py` materializes decisions/context/choice/consequences, actors/business roles, domains/deliverables and ordered journey/persona narrative without creating Odoo accounts/groups.                                                                                                                                                                                      |
| 4. Explicit existing-Task links and authorized deliberate creation        | `test_solution_task_trace.py`: many-to-many exact edges, preview/native wizard then confirm, unchanged manual work, forged defaults rejected, changed draft/requirement/spec heads invalidate pending previews, nonadmin/Task ACL denial, hidden/foreign IDs, injected failure rollback and consumed retry after retirement/archive. `task_concurrency.py`, executed by `scripts/solution_source_probe.py`, uses separate OS/PostgreSQL workers for duplicate create AND link confirmation with complete-transaction retry and one result. No estimates, Sprint allocation, regeneration or manual-content overwrite. |
| 5. Meaningful readable working/exact native projection                    | Rendering suite: exact native Form/QWeb/export and PDF-entrypoint checks, fixed report audience, escaping/no embedded external resources, customer allowlist and both-audience refusal of inaccessible required closure. `test_solution_render_tour.py` runs three real browser preview/direct exact-report journeys plus HTTP public/revocation and authenticated dataset JSON-RPC bypass negatives. Draft/review is unapproved; customer output is explicitly redacted, not a full internal baseline or customer-authenticated portal. No independent editable rendered master.                                     |
| 6. Honest coverage and change impact, manual explicit evidence            | Rendering suite: unlinked exact requirements, legitimately unlinked maintenance, unexplained work, unresolved questions/discovery work, older-revision links and added/changed/removed requirement/context/narrative comparison to an explicit baseline. Exact accepted/rejected/withdrawn/unaccepted categories retain manual evidence. Hidden work refuses complete-looking coverage; no completion percentage or inferred acceptance. Native coverage collections are bounded, not a large-tenant SLA.                                                                                                             |

The complete detailed adversarial/lifecycle matrix remains
[m8-hardening-matrix.md](m8-hardening-matrix.md); it is not replaced by this small map.

## Chosen editable SOW skeleton — all ten entries

`data/solution_templates.xml` defines the editable starting skeleton, not a legal or
universal template. `test_sow_skeleton_all_sections_explicit_copy_and_template_reuse`
and `test_template_copy_is_explicit_and_provenance_does_not_drift` verify ordered copy
and retained provenance. Scenario-specific narrative is written to real sections by
`solution_fixture._document`; no commercial or financial behavior is implemented.

| Scope entry                                          | Ordered starting section                                                   |
| ---------------------------------------------------- | -------------------------------------------------------------------------- |
| Purpose, beneficiaries, outcomes                     | Purpose, beneficiaries and expected outcomes                               |
| Included capabilities, exclusions, boundaries        | Included capabilities, excluded scope and boundaries                       |
| Deliverables and evaluation                          | Deliverables and evaluation expectations                                   |
| Discovery/delivery/verification/handover/checkpoints | Approach and checkpoints                                                   |
| Customer/team responsibilities                       | Customer and delivery-team responsibilities                                |
| Assumptions/dependencies/constraints                 | Assumptions, dependencies and constraints                                  |
| Acceptance authority/criteria/evidence               | Acceptance authority, criteria and evidence                                |
| Proposed changes and explicit approvals              | Proposed changes and explicit approval history                             |
| Optional pricing/payment/commercial references       | Optional commercial references — narrative only, not pricing/payment logic |
| Approval/revision history                            | Approval and revision history                                              |

## Three synthetic fixture clauses

- Customer-funded service-request design: actual optional SOW and separate spec,
  requester/triage actor vocabulary, submission/tracking FRs and isolation NFR; owned
  delegation question explicitly resolved by exclusion, decision with affected
  revisions/consequences; D1 → exact FR1/NFR1 → existing native Tasks → explicit
  synthetic evaluation reference and authorized acceptance. Proven in
  `test_three_synthetic_scenarios_create_real_intent_context_and_narrative` and
  `test_three_synthetic_narratives_render_trace_and_accept_only_explicit_evidence`.
  Browser fixture runs preview plus exact customer report. This is a portal DESIGN
  example; actual service/public exposure is excluded, not claimed as delivered.
- Discovery-led API integration: unresolved schema/authentication/replay assumptions,
  owned blocking question with existing Spike, decision to discover first, and
  hypothetical decision/requirement successor.
  `test_synthetic_integration_scope_revision_requires_separate_sow_then_spec_approval`
  rejects early scope approval, approves the changed SOW then the spec separately,
  retains old Spike linkage and reports change impact. Browser projection runs on the
  synthetic approved discovery baseline, not invented API/production facts.
- Internal initiative: no SOW, actual brief/spec and company/project boundary,
  cross-cutting NFR linked to multiple native Tasks, deliberately unlinked maintenance
  reason, no inferred acceptance. The same scenario/render/browser methods cover the
  brief/maintenance. Optional bridge tests cover native deliberate planning, frozen
  v1/v2, revisions changed before commitment, original commitment versus current links,
  close/carry/remove/reopen/reestimate and no-backfill markers; M1–M7 planning
  UI/browser and native history regressions remain in canonical verify.

Discussion clarifications are retained: shared lineage has separate SOW/spec/change
approvals; reusable narrative supports journeys/personas/domain descriptions; questions
retain owner, significance, affected revisions, resolution and Spike; decisions retain
context/choice/consequences and affected revisions. None grants scope approval, user
permissions or automatic planning authority.

## Independent assessment disposition — every note and coverage limit

c1ph3r's t_4841a335 assessment reports CLEAN for the assessed implementation, with no
blocking product findings. Its report/logs remain in that card's evidence bundle. The
assertion in its artifact paragraph that t_1f505e56 supplied canonical approval is NOT
accepted: immutable reviewer run 222 omitted the required approval metadata.
Done/prose/test success cannot repair that run. This card owns the fresh full-scope
native builder/reviewer pair; no old run, comment or security status is approval.

| Assessment note / gap                                      | Disposition and evidence boundary                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Expected methods derive from committed source              | Non-blocking design limitation: declared-vs-executed completeness, not tamper evidence. Exact-SHA full-scope review and unchanged approved scope are drift controls; parser regressions reject omissions, skips, failures and missing/zero result summaries. Do not describe this as a frozen independent oracle.                                                                                                                                       |
| Preview wizard rows editable by Project users              | Non-blocking bounded native transient UI. Revision/Project and complete reference closure are rechecked; assessment P1/P7 and committed wizard/cache/export/RPC negatives reject wizard-as-authority. Future fields must retain that closure; no authority change in this slice.                                                                                                                                                                        |
| Native import load() reports row errors instead of raising | Informational API contract. Corrected independent P8 asserts error messages, false IDs, rollback and unchanged approved authority/state for update/create forgery. Earlier probe tuple/raise assumptions were probe defects and remain retained, not product failures. Integrations must check `messages`, never treat absence of IDs as successful import.                                                                                             |
| Incremental assessment did not add live HTTP/RPC attacks   | Already covered by committed HttpCase direct-report and authenticated `/web/dataset/call_kw` negatives, independently rerun by canonical verification. No additional security proof beyond those paths is asserted.                                                                                                                                                                                                                                     |
| No extra adversarial DOM-state persistence probe           | Honest residual test limit, not removal of accepted native browser scope. Committed tours check audience transition, markup safety, exact baseline versus draft and modal closure on all three fixtures/lifecycle phases. Arbitrarily modified browser memory, already copied/exported content and a hostile client are not a confidentiality boundary. Current-server authorization is rechecked; universal DOM forensic/erasure proof is not claimed. |
| No extra Scrum-forgery probe in incremental assessment     | Committed bridge tests reject forged capture fields/defaults/context even under ordinary sudo, hidden link/requirement/Task/event/Sprint closure and partial-registry bypass; independent native relink/start/add/close races and persisted optional lifecycle run canonically. No additional unexecuted probe is credited.                                                                                                                             |
| Static/native count ambiguity in assessment narrative      | Use fresh machine-parsed totals and receipts, not the historical 44-static baseline text. Current repository static suite declares 78 checks; exact native phase totals and actual browser/race markers are recorded in the handoff after execution.                                                                                                                                                                                                    |
| Assessment P1–P10 / superseded failed probes               | Retain corrected 10/10 adversarial evidence; wizard oracle/authority, elevation, SOW expansion, consumed retry, designated approval, forged audience, native import, cached export revocation and native Form preview boundaries hold. Probe1–4 include lifetime/discovery/API-shape defects and are not acceptance evidence. No unresolved blocking finding requires product remediation or material-authority reassessment.                           |

## Residual limitations, not dropped approved product scope

Manual evidence/external authority names are internal assertions, not verified URLs,
external authentication or legal signatures. Current access may conservatively deny
historical output. Storage sentinel must stay unassigned/non-implied; trusted server/ DB
administrators remain trust roots. Copies/exported files cannot be retroactively
revoked. Native HTML is portable release output; test-mode PDF entrypoint fallback is
not production PDF-engine verification. Private Odoo 19 search/Domain/locking and Scrum
event seams plus finite M7 source pins are extension/upgrade-sensitive.

Collections refuse more than 1000 rows; bounded helper query proof is not a full
rendering, throughput or large-Project latency SLA. Same-version persisted upgrade is
tested, not a major-version migration. Uninstall DESTROYS M8 history; native Tasks/
Sprint history survive extension removal, but only separately approved consistent
DB/filestore backup/restore can recover deleted traceability. No production restore,
Odoo.sh staging, legal suitability, customer fit or actual API behavior is validated.

Genuinely excluded product/effect items remain exactly those in the accepted scope:
contracts/e-signature/quoting/billing, mandatory Sales, custom wiki or parallel Tasks,
full test management, AI/automatic backlog or Sprint planning, Done/Git acceptance
inference, provider expansion, Jira migration, release management, customer/public
service exposure and production deployment. Publication, target integration and live
activation are separate gates, not features silently removed after a failing test.

## Required execution, review and subsequent delivery

Use the operator-authorized local driver with this same card ID:

    python3 /home/molty/.hermes/scripts/odoo_m8_verify.py t_f0b10ab9 verify

It runs the actual feature-lane `scripts/verify`: static checks, independent Git
policy/core/bridge installs; core and bridge persisted upgrade/removal/reinstall;
aggregate install/upgrade/reverse-uninstall-reinstall; imported M8 negative tests, real
native browser/HTTP/RPC journeys, Hoot, independent-process baseline/content/
intent/Sprint races and M1–M7 recovery. No weakened test selection or archive proof.
Allowlisted public fixtures must be readable by Odoo's non-root user; retain exact exit
status, artifact HEAD, discovery/results, source identity and cleanup receipt.

Gilfoyle must independently review the entire cumulative artifact at the exact clean
handoff SHA, including all earlier hardening source and all scope/fixture rows, and
independently run focused/security plus canonical checks. Approve ONLY through native
same-card completion metadata `approved=true`, `review_outcome=approved`,
`reviewed_commit=<identical full SHA>`; otherwise native same-card request-changes. The
delivery owner must pass the unchanged exact-review guard using this card, not
t_1f505e56. The baseline attestation t_5b21bfa0 remains a separate prerequisite. No
source history backfill, main advancement, push/PR/tag/release, runtime/provider/
credentials/config change or publication approval is performed by this slice.
