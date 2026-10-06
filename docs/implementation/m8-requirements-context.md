# M8 requirement identities and supporting context slice

## Boundary and dependency posture

This slice on `feature/t_f1a8ee89-m8-solution-definition` extends historical parent
artifact `df782236c395aae758b3443ef2a404c7d8c35f61`, not `main`. Parent review run 208
omitted canonical approval metadata; prose/comments do not repair that omission.
Fresh read-only exact-artifact attestation `t_5b21bfa0` must independently recover
that evidence before accepted-parent lineage/local delivery is asserted. This
successor still requires genuine same-card exact-SHA review on `t_913965f7`.

Odoo 19 Community `19.0-20260908`; Odoo-compatible, not an OCA-conformity claim.
Addon `project_agile_solution` remains optional, LGPL-3 and dependent only on
existing LGPL-3 `project_agile` and transitive Community Project. No new native,
OCA, proprietary, SDK or service dependency. Scrum/Git/Sales/docs remain optional.
ADR-013 and its pinned native/OCA discovery remain the authority. The canonical
source probe additionally inspects installed `ir_sequence.py` / `next_by_id`.

The optional Task inverse/edit guard extends the native Task inheritance chain.
M7's finite `policy_write_profile.SOURCES` therefore includes this exact source
digest: ordinary stage writes delegate unchanged to `super()`, while discovery
inverse edits remain rejected. No dependency on Solution is added to Git policy;
the pin is only evaluated if Solution is installed. Unknown inheritance, modified
files and runtime write monkeypatches still fail closed. The first cumulative
run exposed 21 M7 `unsupported_extension` failures and was retained, not waived.
The focused static pin regression proves RED before adding the exact pin; full
canonical native apply/rollback and unreviewed-write negatives prove coexistence.

## Concrete records and operations

- `project.agile.requirement`: permanent project-scoped `REQ-<sequence>` identity,
  separate from native Agile Task keys. Type is content, not a mutable key prefix.
- `project.agile.requirement.revision`: actual FR/NFR description, rationale,
  must/should/could priority, verification method and acceptance expectations.
- `project.agile.solution.context`: permanent `CTX-<sequence>` identity and fixed
  section/question/decision/actor/domain/deliverable kind. Journeys/personas use
  narrative, never a new account, group, wiki or work-item model.
- `project.agile.solution.context.revision`: numbered, audience-tagged typed
  content, ordered narrative and exact affected requirement revision references.
  Questions name an active internal responsible owner, optional external-owner
  narrative, informational/planning/blocking significance and permitted existing
  same-Project Agile Spike Tasks. Explicit resolution records answer, rationale,
  recorder and time. Decisions preserve context, choice and consequences.
- Documents select exact requirement/context rows; a document cannot select two
  revisions of the same identity or content from another solution. Requirement
  ordering is explicit stable row identity; context ordering is sequence then ID.
  Existing document-owned sections remain the ordered SOW narrative mechanism.

New identity creation checks caller Manager/Project/company/active Agile lineage
before a narrow native sequence allocation. The Project row serializes first-use
sequence creation even across different lineages. Standard native sequences allow
harmless rollback gaps, never reuse an allocated key. Database unique constraints
cover `(project_id, key)` and `(identity_id, number)`. Native locks use the existing
parameterized fixed-table helper; no business method commits/rolls back a cursor.

Content stays editable until used in submitted review. Submission atomically seals
all selected requirement/context rows and all affected requirements, including rows
referenced only through questions/decisions. Return to draft never unseals content.
New Revision reuses an existing working row or creates a numbered distinct successor
from sealed content. A question successor intentionally reopens its answer/resolution;
it does not claim a later answer was already approved. Stable identities archive;
identities and numbered rows are not deleted, even if currently unreferenced.

Current native rules govern identity/content search, read/group/export and mutation.
Snapshot closure rechecks exact members, affected requirements, owner and Spike
access; hidden/missing content cannot silently become a complete baseline. Snapshot
membership completeness uses inverse ORM queries, not sudo relation caches: native
many-to-many fetching filters inaccessible rows and a cached relation is not proof
of completeness. A storage-only Task inverse permits a bounded ORM Spike count;
its sentinel group is not implied by debug/user roles, and inverse mutation/defaults
are rejected. Counts are never returned; incomplete closure raises a generic denial.
The payload freezes actual content/key/owner/Spike labels, not today's mutable names.
Normal sudo/context cannot author, bypass seals, forge numbers/audit, reparent rows,
edit inverse membership or mutate related records with reference commands. Native
Project company moves/deletion are denied once any solution intent identity exists;
referenced discovery Tasks retain a deletion guard. Archive preserves navigation.

SOW/spec approval chains remain separate. Selecting the same sealed requirements
or template does not approve another document or expand authorized scope. Native
Task descriptions, acceptance criteria, workflow, estimates and Sprint state are
never updated by requirement/context edits.

## Editable starting templates and fixtures

Two deliberately shared, `noupdate=1`, editable starting templates are loaded:
`template_sow_skeleton` has all ten agreed sections, including optional commercial
narrative/external references without financial/legal defaults; `template_internal_brief`
has a no-SOW internal starting structure. Existing explicit template-copy action
retains copied content/version provenance. Later template changes never propagate.
Native XML install uses actual root uid=1 for template creation; the template-only
manager guard admits that trusted root, not ordinary sudo (which preserves caller
uid). This exception has no document approval or sealed-content authority.

The three explicitly synthetic scenarios create real requirements, questions,
decisions, actors, domains, deliverable evaluation and journey narrative, plus
independent exact SOW/spec approvals (internal initiative has no SOW). The portal
question is explicitly resolved to exclude delegation. API discovery remains open
and links a real Spike; no external schema/auth/replay truth is invented. All ten
SOW sections are populated with scenario-specific narrative. Commercial references
are plain synthetic text only. Task links, requirement acceptance events, optional
Scrum context and full rendered coverage remain downstream; fixture intent is not
customer validation, legal sufficiency or observed production behavior.

## Verification and recovery

Imported `TestSolutionRequirements` exercises native nonadmin/custom-rule/company
boundaries, typed input, server-managed fields, inverse edits, atomic batch failure,
seal/return/successor behavior, archive readability, full snapshot closure and template
reuse. `requirement_concurrency.run_probe` adds independent-process key/revision races
for both vocabularies to the canonical isolated source probe; prior baseline and
M1-M7 lifecycle/browser/concurrency checks remain untouched. Native discovery gates
reject missing baseline or requirements tests instead of accepting zero discovery.

Commands use only the approved local task-scoped capability:

    python3 /home/molty/.hermes/scripts/odoo_m8_verify.py t_913965f7 probe
    python3 /home/molty/.hermes/scripts/odoo_m8_verify.py t_913965f7 odoo --database odoo_agile_m8_test --init project_agile_solution --test-enable --test-tags /project_agile_solution --stop-after-init --without-demo=True --log-level test
    python3 /home/molty/.hermes/scripts/odoo_m8_verify.py t_913965f7 verify

Canonical verification owns actual `./scripts/verify`, isolated install, full install,
upgrade and dependency-safe uninstall/reinstall plus exact resource cleanup receipts.
Source-only or parser tests are not native proof. Real results, full SHA, changed files,
failed attempts and residual risks belong in the same-card review handoff.

Recovery means request-changes on this same retained lane, revise source and repeat
verification/review. No main advancement, push/PR/tag/release, deployment/live restart,
provider/profile/Hermes changes, shared resource cleanup or customer contact is allowed.
