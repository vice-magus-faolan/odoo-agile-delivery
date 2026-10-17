# ADR-013: Solution definition, revisions and delivery traceability

## Status and outcome

Proposed M8 contract for independent same-card exact-SHA review. The root implements
only the optional lineage skeleton; this document specifies downstream obligations, not
delivered functionality. Approved product scope is preserved verbatim in
[the scope record](../milestone-8-approved-scope.md). See the
[gap map and serial plan](../plans/2026-10-05-milestone-8-solution-definition.md),
[research](../research/m8-solution-alternatives.md) and
[synthetic fixture contract](../research/m8-synthetic-fixtures.md).

Beneficiary: Agile teams explaining agreed intent, uncertainty, coverage and explicit
acceptance. Problem evidence is one prospective user's request, not validated market
fit. No customer SOW exists. Fixtures are synthetic, publicly informed design examples,
not legal standards, observed production data or evidence of customer acceptance.
Delivery, publication, runtime deployment and live activation are separate effects.

## Context and dependency decision

Keep `project_agile_solution`: the name makes the opt-in Agile solution boundary
explicit and does not imply a Sales contract, wiki, portal or work-item replacement. It
depends only on `project_agile`, transitively Community `project`. Preserve the suite's
LGPL-3 choice; no existing license changes. The repository is Odoo-compatible, not
OCA-hosted or an OCA-conformity claim. Odoo 19 Community is the tested edition.
Odoo.sh-first means ordinary ORM, views, actions and native QWeb reports; no daemon,
SDK, Sales, Git, queue_job, Enterprise or document backend is required. Odoo.sh
compatibility of the actual deployed extension set is still a separate staging test.

Reuse native Tasks, hierarchy/dependencies, Agile keys/types/acceptance criteria,
Project authority, ORM/constraints, transactions, `ir.sequence`, native form/list/search
and QWeb. Do not copy generic Task templates, document-page history/editor or approval
workflows. OCA candidates and exact pinned APIs were researched rather than inferred;
none supplies this complete requirement-revision/Task/Sprint contract. M4's optional OCA
backend and unmerged Task connector remain separate; no M8 parent depends on them.

## Finite vocabulary and records

Names below are owned by this contract. Only `project.agile.solution` exists in the
root. Later cards add these models in their own bounded phases, not empty placeholders.
Every identity is project-bound; relations use restrictive deletion where history
exists. Company follows the project's actual company, never caller context. Company-less
native Projects remain supported but are not a loophole for cross-company references.

| Model                                     | Meaning and justification                                                                                                                                                                                                       |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `project.agile.solution`                  | Shared scope lineage; one Project can have several initiatives. Name/archive is not a revision.                                                                                                                                 |
| `project.agile.solution.document`         | Stable document identity, kind `sow` or `spec`; separate approval chains under one lineage. Internal brief is a spec, not a mandatory third workflow.                                                                           |
| `project.agile.solution.revision`         | Ordered numbered document content, lifecycle, predecessor and exact baseline references. A distinct draft working revision never aliases an approved row.                                                                       |
| `project.agile.requirement`               | Stable project-scoped key, solution, archive flag; never a Task. Keys are allocated with native sequence, unique within Project, immutable and never reused.                                                                    |
| `project.agile.requirement.revision`      | Numbered actual FR/NFR content: title/text, rationale, `must/should/could` priority, verification method/expectations and audience. Exact revisions, not mutable requirement text, are linked.                                  |
| `project.agile.solution.context`          | Stable section/question/decision/actor/domain/deliverable identity using a finite `kind`. One model, not a separate lifecycle for every noun.                                                                                   |
| `project.agile.solution.context.revision` | Actual versioned typed content and references. Necessary because decisions/questions and narrative must remain explainable after edits.                                                                                         |
| `project.agile.solution.template`         | Reusable named/versioned ordered narrative section payload, SOW or spec kind, company-scoped or intentionally shared; not a wiki/editor. Copy explicit selected content into draft, retain template version/content provenance. |
| `project.agile.requirement.task.link`     | Explicit same-Project Task to exact requirement revision edge; uniqueness `(task_id, requirement_revision_id)`. Many-to-many through this auditable edge, not a live latest-requirement alias.                                  |
| `project.agile.solution.task.intent`      | Durable preview/confirm identity and finite proposed Task values, source revisions, creator and consumed result. Needed for deliberate retry-safe creation, not a queue.                                                        |
| `project.agile.requirement.acceptance`    | Append-only exact-revision acceptance/rejection/withdrawal event with named authority, evidence, recorder, UTC time and superseded event where applicable. Not test management.                                                 |

A document revision contains ordered references to exact requirement and context
revision records with stored membership/ordering. Use explicit relational
tables/children for membership if ordering requires them; their sole purpose is
immutable structure, not another business vocabulary. Approved revisions retain actual
content in those sealed child revision rows, not a pointer to today's mutable `name`,
description, question answer or external page body. Snapshot lineage/project label,
template source, requirement key and human authority labels when needed for reproducible
display; live record pointers are for navigation and current authorization only.

Context content is validated by kind: sections have sequence/title/sanitized body;
deliverables have evaluation expectations and requirement references; questions have
owner (active internal responsible user plus optional external owner narrative),
question, resolution/status, affected exact requirements, planning significance
`informational/planning/blocking`, and optional existing Spike Tasks. Resolved questions
retain who/when and rationale; a changed answer creates a successor. Decisions have
context/choice/consequences and affected revisions; they do not infer scope approval.
Actors have business role descriptions; domains have descriptions and requirement
references. They are design vocabulary, not `res.groups`, automatic account grants or
authentication roles. Journeys/personas use narrative sections without additional
models. Unknown kind-specific fields and forged cross-scope references fail server
validation.

## Revision and approval semantics

Documents use `draft -> review -> approved -> superseded`. An authorized author may
return review to draft with a reason; approval checks the exact content/version under a
nonblocking native ORM claim. Content is frozen in review so concurrent editors cannot
change the item being approved. Rejection returns it to draft explicitly. Numbered
successors are distinct working rows; approved/superseded content, membership, ordering,
audience, references and author/time cannot be rewritten by ORM/import/RPC/x2many,
context flags or normal sudo flows. Direct state writes are rejected, including for
superuser. A narrow private transition may update lifecycle metadata only after current
caller authorization. Superseding a baseline does not delete it or make its acceptance
disappear.

Requirement/context content becomes sealed when included in a submitted document review,
confirmed Task intent/link, Sprint context or acceptance. Editing sealed content creates
a successor row; an abandoned review never unseals reused history. Draft-only content
can be edited, but a shared draft reference cannot mutate another document's
review/baseline. Document membership binds exact content. New document revisions may
reuse unchanged sealed rows. Unique revision numbers and server-owned publication of
newly allocated revisions on their identities prevent concurrent allocation; two
submitted successors cannot silently become current. Document creation and approval
publish their actual references on the solution to order SOW/spec scope decisions.
Native ORM claims do not wait. Incomplete claims request native Odoo whole-transaction
rollback and retry; fresh-state validation rejects stale proposals. Unlink claims also
exclude concurrent foreign-key references to records being deleted. There is no manual
cursor commit or business-code retry loop. See the
[concurrency runbook](../runbooks/solution-document-baselines.md#concurrency-and-atomicity)
for retry limits and exhaustion behavior.

SOW is optional. SOW approval never approves a spec, its working successor, or later
scope expansion. A spec records `based_sow_revision_id` only when a SOW exists, plus an
explicit scope disposition/change rationale. Within that scope, separate spec approval
is still required. Changes to included/excluded deliverables, obligations or acceptance
boundaries require an explicitly approved successor SOW before approving the expanded
spec; discovery cannot authorize expansion. Internal initiatives use an explicitly
approved spec without a SOW prerequisite. A SOW may remain approved while a detailed
spec is in draft/review. No legal signature, commercial obligation or payment automation
is implied by either approval. Template changes do not propagate into existing drafts or
baselines without a deliberate selected copy operation.

Approval authority is explicit: a document names an active internal Project Manager
approver; the public approval action requires that exact current user and current
lineage/Project/revision write access and company membership. A manager flag alone
without concrete record access is insufficient. This first release does not invent a
universal two-person contract-signing policy: self-approval is possible only if the
explicit designated approver is the author, and recorded as such. Customer signoff is an
asserted external decision recorded by an authorized internal manager, not customer
authentication or a cryptographic/legal signature. Later stricter project policies
require an explicit reviewed extension, not undocumented assumptions.

## Authority, privacy and historical access

Root ACLs: internal Project users read; native Project Managers create/rename/archive/
delete unused lineages. Global company rules intersect a global searchable
`native_project_access` rule. Its hook restores `sudo(False)` and builds an unevaluated
native Project `_search` subquery, honoring current native/custom rules. Odoo 19
`BaseModel._search` compiles security domains on a sudo recordset, so a plain relational
`any` in an `ir.rule` is insufficient: real negative tests failed with that first
design. The private `_search` seam is exact-version-sensitive and must retain
rule-change, search/read/export and multi-company regressions; no ID list is cached.
Creation additionally checks concrete Project read/write access and active Agile opt-in.
Project/company cannot be passed to change an existing lineage. No public/portal ACL or
route exists.

Downstream draft editing, submission, link and intent creation require native Manager
and actual Project/document write access; normal Project users read authorized material.
Tasks additionally require current read (and write for confirm/link mutation) checks;
Spike links require an actual permitted existing Agile Spike, not a name guess. Every
public action re-resolves typed IDs, exists/scope/company/state/content-version and
current permissions. Booleans are not integer IDs. Context defaults are selection hints,
not authority. Owner/approver IDs cannot forge group membership. Recheck active users,
allowed companies and all referenced records before elevation. Use normal caller ORM; if
immutable audit storage needs sudo, it is limited to already-validated values after
authorization, never for discovery/counts/existence or a decision. All batch operations
fail atomically, not a per-record partial success.

History remains immutable but is not permanent permission: current Project/record rules
protect history and snapshots, search/read/group/export/name lookup/counters/action
navigation. Related snapshots must not bypass new restrictions on a referenced Task,
question or document. Archived accessible records are resolved with bounded
`active_test=False` and marked historical. Inaccessible/missing required references
produce a generic incomplete/unavailable result or deny exact full rendering, with no
names, hidden counts, IDs or excerpts. No silent omission can be called a complete
approved baseline. Restrictive deletion prevents ordinary dangling references.

## Task traceability and deliberate creation

Existing Task links are the default. Link to exact requirement revisions and preserve
unlinked maintenance work with an explicit maintenance reason
(`solution_maintenance_reason` on Task in the optional addon); missing linkage is not
automatically a defect. A cross-cutting NFR can link to many Tasks; one Task can link to
many requirements. Moving a link to a successor is deliberate and records old/new
evidence; it never rewrites Sprint context, a baseline or historical acceptance.
Archived references remain historical; new work cannot target
archived/non-Agile/template/unavailable Tasks or requirements.

Preview persists a durable Task intent with server-generated token, selected exact
revisions, proposed name/description/type and creator, no Task. A native confirmation
wizard shows source revision keys and permitted values. Confirm re-resolves caller,
Project, type eligibility, exact source freshness and access. A changed draft or current
baseline invalidates the old intent; user must preview again. A consumed intent returns
the same still-authorized Task, never creates another. Database-unique intent identity,
a native nonblocking claim and the actual consumed result order two confirmations;
mismatching payload reuse is rejected.

Confirm atomically creates a native Task using only `name`, `description`, `project_id`,
and explicitly selected `agile_item_type_id`, links exact requirement revisions and
stores the consumed Task result. No implicit estimate, Sprint, acceptance-criteria,
parent/dependency, stage/state, follower or completion writes; normal Odoo creation side
effects remain native and documented. Tests must prove zero duplicate/partial
Task/link/intent result on injected failures and independent-connection retries.
Cancellation keeps consumed identity; archive/delete of a generated Task cannot renew
creation eligibility. Never automatically regenerate backlog, edit existing
descriptions, manual criteria, workflow, estimates, ordering or planning when spec text
changes.

## Optional frozen Scrum context

The traceability card delivers `project_agile_solution_scrum`, depending exactly on
`project_agile_solution` and `project_scrum`, not vice versa. No mandatory
analytics/UI/Git or document backend. Extend the existing private
`project.sprint._append_scope_events` producer via `super()` without copying lifecycle
methods. Add a minimal immutable `project.agile.solution.sprint.context` edge keyed by
`(scope_event_id, requirement_revision_id)` (and document baseline reference where
present). At each committed/added event capture all exact Task links in that transaction
with Project/Task authority established before narrow audit elevation. Store an explicit
capture-status marker on the scope event: `captured/empty/not_available`, distinguishing
known unlinked/maintenance from events predating the bridge. Existing history is never
backfilled from current Task links.

Capture current planning context even if it is draft/unapproved, but label that status
and seal the actual content; Sprint commitment is not requirements/scope approval. Later
edits or v2 links do not change an event's v1 context. Removed/completed/reopened/
carry-over events retain their observed references, and reports can navigate original
commitment separately from current coverage. When historical full references are
inaccessible, fail closed without elevated metadata. Do not change native Sprint
assignment, state, points, committed-task lists or analytics formulas. Publish each
created/retired link reference on its Task and claim that same Task for scope capture.
Preserve existing Sprint close/Task ordering and atomic rollback; sealed requirements
need no Solution-wide capture write. Installing or uninstalling the bridge cannot
fabricate historical proof. Native core works without it.

## Rendering and templates

Native forms/lists and QWeb HTML reports render either explicitly selected working
revision or exact approved/superseded baseline, never a moving 'latest' substituted for
an exact ID. Native PDF may project the same verified values when available. The report
model's `_get_report_values` must perform current-user checks; report actions and direct
report routes are not authorization. QWeb escaping and sanitized HTML apply; URLs are
displayed as validated references, never fetched or embedded as remote content.
PDF/export cannot widen scope through cached attachment reuse or sudo rendering; disable
reusable report attachments for audience-sensitive output.

Audience is finite `internal/customer`. Customer-facing is a deliberately generated
projection by an authorized internal user, not portal access. Internal-only questions,
decisions, actor/contact details and narrative do not appear in customer output. Declare
'redacted customer projection of baseline X, not the full internal baseline' without
revealing hidden item names/counts/IDs. For a complete-for-selected-audience claim, all
included permitted references must be accessible and the declared projection rules
satisfied; otherwise refuse or clearly label incomplete without leaking denied content.
Full internal exact-baseline rendering requires the entire referenced closure
accessible. Audience tags are sealed revision content, not caller-provided permission
overrides. Current working output is always labelled draft/unapproved. No independent
editable rendered master, wiki, editor/page history, Sales quote or Enterprise API is
introduced.

Reusable SOW template starts with purpose/outcomes; included/excluded scope;
deliverables/ evaluation; discovery/delivery/verification/handover/checkpoints;
responsibilities; assumptions/dependencies/constraints; acceptance
authority/criteria/evidence; proposed changes/approval history; optional commercial
external references; revision history. An internal-brief template omits commercial/SOW
assumptions. Templates are project- specific editable starting points, not universally
mandatory or legally sufficient.

## Honest coverage, change impact and explicit acceptance

Expose categories, not a fabricated completion percentage: unlinked requirements; linked
exact current revisions; Task links to older revisions; requirement/context changes
since selected baseline (added/changed/removed); unresolved planning/blocking questions
and related Spike; legitimately unlinked maintenance; unexplained unlinked work;
archived/unavailable references; approved-but-unaccepted; accepted exact revisions with
evidence; rejected/withdrawn acceptance. Current Task Done/PR merge is explanatory
context only. Aggregate/counter queries use caller access; inaccessible closure prevents
'complete coverage' claims, including grouped views and exports.

Acceptance names exact requirement revision and its approved spec baseline, criteria
actually evaluated, nonempty bounded manual evidence/reference, named acceptance
authority and UTC decision/recorder. A native Manager with concrete access records it
explicitly; external authority is an assertion with named partner/role, not an
authentication grant. Reject acceptance of an unapproved/different-project/inaccessible
revision, or empty criteria/evidence. Verification observation may precede acceptance
but is not acceptance. Rejection/withdrawal append events, never overwrite prior
evidence. Acceptance of v1 does not accept v2; supersession preserves v1 historical
acceptance. Evidence is a manual reference/assertion, not an automated test result,
immutable external artifact guarantee or an engine that verifies URL truth.

## Recovery, archive, retention and consequences

Unused root lineages may be deleted by an authorized Manager with Project write access;
archive preserves identity. Later document/requirement/context histories and used
intents, acceptance and Sprint references use `ondelete=restrict`; deletion of used
histories and Project/company reassignment which would rewrite scope is refused.
Rename/archive affects navigation, not stored approved content. No cron purge or
automatic historical deletion. Draft-only unused records may be removed in a
permission-checked transaction. Export and retention decisions require authorized scope;
snapshots can contain business-sensitive text, so retain only relevant content, never
secrets or raw credentials.

Normal ORM, even sudo, is not a recovery bypass for sealed content. Correct through an
explicit successor/rejection/withdrawal event. DB administrators/trusted server code are
the trust root; this is not tamper-proof against arbitrary SQL/admin restores. Back up
DB/filestore before uninstall or migration. Odoo uninstall removes addon tables; it is
not an archival strategy or a way to promise retention across uninstall. Root disposable
uninstall/reinstall proves dependency/lifecycle health, not preservation of deleted
data. Restore is a controlled incident: verify references/content/consumed intent
identities, keep creation disabled until consistency is checked, do not regenerate Tasks
or backfill historical Sprint context from today's links. No main advancement,
push/publication, shared service restart or live customer/provider configuration is
authorized here.

## Alternatives, open risks and verification

Rejected: requirement-as-Task (wrong lifecycle); mutable latest-text baselines;
JSON-only pointer snapshots without actual immutable content; a generic SOW/legal/Sales
engine; OCA page-history as requirement identity; Enterprise Knowledge assumptions;
automatic backlog/Sprint creation; Done/merge-as-acceptance; privileged complete-looking
exports.

Costs: explicit revision membership and limited audit models, conservative refusals on
inaccessible closure, additional optional Scrum seam tests. Residual product uncertainty
is customer demand, actual SOW authority/legal suitability, unknown external interface,
and deployment-specific permission/extensions. These are not invented validations.

Root proof: isolated optional install, imported native nonadmin/private-Project/custom-
rule/multi-company/forged-context/rollback tests, reproducible synthetic native Task
seeds, and canonical M1-M7 plus new-module install/update/reverse-uninstall/reinstall.
Downstream proof additionally includes all fixture/adversarial rows, browser
forms/report privacy, concurrent approval/intent/capture and independent
c1ph3r/cumulative review. Exact SHA review by Gilfoyle is required before the next
slice. Any contract amendment must preserve approved scope and name its evidence;
genuine product/security/dependency changes escalate.
