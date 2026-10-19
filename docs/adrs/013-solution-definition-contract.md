# ADR-013: Solution definition, revisions and delivery traceability

## Status and outcome

Accepted and implemented by optional `project_agile_solution` and
`project_agile_solution_scrum`. This ADR owns the domain decisions;
[dependency compatibility](../dependency-compatibility.md) records exact native/OCA
selections, and [Solution operations](../runbooks/solution-operations.md) owns
transaction, privacy and recovery constraints.

Agile teams need to explain agreed intent, uncertainty, delivery coverage and explicit
acceptance. Requirements express delivery intent, not another Task system. The design
was informed by one prospective user's request and synthetic scenarios; these do not
establish customer demand, actual external APIs or legal suitability.

## Dependencies and native boundaries

Solution core depends only on LGPL-3 `project_agile`, transitively native Community
Project. Both Solution addons retain LGPL-3. The base target is self-hosted Odoo 19
Community, with custom functionality kept deployable on Odoo.sh. Enterprise and Odoo.sh
installed-extension behavior require separate verification. This is an Odoo-compatible
suite, not a claim of full OCA conformity.

Reuse native Tasks, hierarchy, dependencies, Agile keys/types/criteria, Project
permissions, ORM, constraints, transactions, `ir.sequence`, views and QWeb. No Sales,
Git, Scrum, Enterprise, document backend, SDK, external queue runner or custom
wiki/editor is required by core. Native `ir.cron` is the suite's scheduling boundary;
`queue_job` is not supported. General documentation remains with its selected backend.
OCA page history and Task templates do not supply immutable requirement revisions,
separate scope approval and frozen delivery references.

## Records and identity

Every identity belongs to a Project through its solution lineage. Company follows that
Project, not caller context. Company-less Projects are supported without allowing
cross-company references.

| Model                                     | Purpose                                                                                                                      |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `project.agile.solution`                  | Named, archivable initiative lineage; a Project may have several.                                                            |
| `project.agile.solution.document`         | Stable SOW or specification identity with a designated approver. An internal brief is a specification, not another workflow. |
| `project.agile.solution.revision`         | Numbered content, predecessor, lifecycle and exact baseline references.                                                      |
| `project.agile.requirement`               | Permanent project-scoped `REQ-<sequence>` key; FR/NFR type belongs to content, not the key.                                  |
| `project.agile.requirement.revision`      | Actual FR/NFR title/text, rationale, must/should/could priority, verification method, acceptance expectations and audience.  |
| `project.agile.solution.context`          | Permanent `CTX-<sequence>` key with fixed section/question/decision/actor/domain/deliverable kind.                           |
| `project.agile.solution.context.revision` | Numbered typed context and exact affected-requirement references.                                                            |
| `project.agile.solution.template`         | Editable SOW/spec narrative starting point with version and ordered source content.                                          |
| `project.agile.requirement.task.link`     | Auditable same-Project Task-to-exact-requirement edge, unique per Task/revision pair.                                        |
| `project.agile.solution.task.intent`      | Creator-owned durable preview, bounded proposed Task values, exact source and consumed result.                               |
| `project.agile.requirement.acceptance`    | Append-only exact-revision acceptance, rejection or withdrawal with authority, criteria, evidence, recorder and UTC time.    |

Native sequences may have rollback gaps; allocated keys are never reused. Numbered
revisions are unique per document or stable identity. Requirement membership uses stable
row identity for order; context uses sequence then ID. Document-owned narrative sections
retain explicit order, sanitized HTML and audience. Exact references never resolve
implicitly to today's latest text.

Questions retain an active internal responsible owner, optional external-owner
narrative, affected exact requirements, informational/planning/blocking significance,
optional existing same-Project Agile Spike Tasks, and resolution with actor, time and
rationale. A successor reopens its resolution. Decisions retain context, choice,
consequences and affected revisions. Deliverables retain evaluation expectations. Actors
and domain descriptions are design vocabulary, not accounts, groups or authentication
grants. Journeys and personas use narrative rather than additional models.
Kind-inappropriate and cross-scope values are rejected.

The editable SOW starting template covers purpose/beneficiaries/outcomes; included
capabilities/exclusions/boundaries; deliverables/evaluation;
discovery/delivery/verification/handover checkpoints; customer/team responsibilities;
assumptions/dependencies/constraints; acceptance authority/criteria/evidence; proposed
changes and explicit approvals; optional commercial narrative/references; and
approval/revision history. It supplies no pricing, payment, financial or legal defaults.
The internal-brief template omits commercial/SOW assumptions. Both are shared editable
`noupdate` starting points, not universally mandatory content. Copying selected sections
appends sanitized content with exact source provenance; later template edits never
propagate to existing documents.

## Revision, scope and approval

Documents follow `draft -> review -> approved -> superseded`. Submission freezes actual
ordered content, membership, audience, exact references and template provenance. Return
to draft requires a reason. Approved or superseded content is not rewritten by ORM,
import, RPC, relational commands, context or ordinary sudo; correction creates a
successor. Direct lifecycle-state writes are rejected even for superuser; private
actions change lifecycle metadata only after authorization.

Requirement/context content seals when used in review, confirmed Task intent/link,
Sprint capture or acceptance. Returning a document does not unseal reused content.
Unchanged sealed revisions may be reused; editing creates a numbered successor.
Snapshots retain actual nested content, original labels and source-template
version/content, not only pointers to mutable names. Rename/archive affects navigation
rather than stored bytes. A digest is not protection against trusted server code or
database administrators.

SOW is optional. When one exists, a specification selects an independently approved
exact SOW revision and records scope disposition and rationale. SOW approval does not
approve a specification, later detail or expanded scope. An expanded specification
requires an explicitly approved changed successor SOW first; discovery alone does not
authorize expansion. Without SOW, an internal initiative still requires specification
approval. This is an explicit human scope decision, not semantic detection of undeclared
expansion in prose.

Each document names an active internal native Project Manager approver. Approval
requires that exact current user plus current lineage, Project, document, revision and
company authority. A manager group alone is insufficient. Unlike Git policy, Solution
approval does not require two people: the designated approver may also be the author.
Recorded external authority is an internal assertion, not external authentication or a
legal signature.

Nonwaiting native ORM claims and shared publication writes order allocation, submission,
SOW/spec approval and Task confirmation. A stale contender retries the whole transaction
and then rejects stale intent rather than silently approving a different revision. Batch
and multi-step operations are all-or-nothing even when a direct caller catches an
exception. Exact claim, retry-limit, exhaustion and caller-responsibility semantics are
in the
[concurrency contract](../runbooks/solution-operations.md#concurrency-and-atomicity).

## Current authority and frozen history

Internal Project users read permitted material; native Project Managers author and
mutate it only with concrete record access. Public actions re-resolve typed IDs,
existence, state, company, exact references, content version and permissions. Booleans
are not integer IDs. Defaults, owner IDs and context are not authority. Task links
require current Task access and mutation checks; discovery links require an actual
permitted existing Agile Spike. Elevation is limited to already-authorized storage,
never selecting accessible records or deciding approval.

Global descendant rules use an unevaluated current-user Project subquery. Odoo 19
compiles rule domains on sudo recordsets, so a plain relational `any` is not enough to
establish native Project visibility. The private `_search` seam is version-sensitive; no
cached list of visible IDs substitutes for current custom/native rules.

Frozen history does not grant permanent access. Reads, searches, grouping, exports,
counters, navigation and reports recheck the exact reference closure, including
sections, requirements/context, referenced SOW and discovery Tasks. Accessible archived
references remain usable. Missing or inaccessible required references refuse complete
output without leaking names, IDs, counts or excerpts. Filtered relation caches cannot
establish membership completeness. The unassigned, non-implied snapshot-storage sentinel
must remain inaccessible to user roles, including browser debug mode; see Solution
operations.

## Task traceability and deliberate creation

Existing Task links are the default. One NFR may span Tasks and one Task may address
several requirements. An explicit maintenance reason explains legitimately unlinked work
without implying approval. Link retirement preserves its reason and actor; replacement
links never rewrite old baselines, acceptance or Sprint context. New links reject
archived, template, non-Agile or inaccessible targets.

Preview stores a durable creator-owned intent and no Task. Confirmation through the
native wizard rechecks current access, Project/type eligibility and exact source
freshness after claims. Changed draft content, a new requirement head or changed
specification invalidates an unconsumed preview. Preview again rather than reuse stale
intent. A consumed intent returns the same still-authorized result, including after
requirement successors; archive or deletion cannot renew creation.

Confirmation creates one native Task using only name, description, Project and
explicitly selected Agile item type, then links exact requirements and consumes the
intent in the same savepoint. Caller default context is stripped. Native creation
effects remain native. No estimate, criteria, hierarchy, dependency, stage/state, Sprint
or ordering is supplied. Specification edits never regenerate backlogs or overwrite
manually authored Task values. Independent confirmations converge on one result;
failures leave no partial Task, links, seals or consumption.

## Optional frozen Scrum context

`project_agile_solution_scrum` depends on Solution core and `project_scrum`, never the
reverse. It extends `project.sprint._append_scope_events` via `super()` without
replacing lifecycle logic. At each native event it captures all exact active Task links,
sealed requirement content and specification number/state. Context edges are unique per
event/requirement revision. Status distinguishes `captured`, observed `empty`, and
`not_available` for history predating the bridge. There is no backfill.

Draft/unapproved context is labeled and sealed, not approved by Sprint commitment. Later
edits, links or approval cannot change historical events. Capture uses the same Task
claim as competing link/scope changes and preserves native close/Task ordering and
complete rollback; no extra Solution-wide capture write is needed. It changes no native
Sprint assignment, state, points or analytics formulas.

Current Task, Sprint and exact-reference access governs captured history. During a
dependency-ordered upgrade, the stored event rule denies ordinary reads while
`solution_native_access` is not yet registered; it does not fall back to privileged or
incomplete history. Once loaded, the extension's current-reference rule applies. Core
Scrum remains independent; installing or reinstalling the bridge cannot manufacture
missing historical proof.

## Rendering, coverage and acceptance

Native views and QWeb render explicitly selected working or exact approved/superseded
revisions. Working output is unapproved. The report-value boundary rechecks current
access; report actions, direct URLs, context, PDF and export cannot widen it. Report
attachments and attachment reuse are disabled. Rendering converts narrative to escaped
text without executable markup or remote resources. Production PDF engine behavior is
not established by native HTML or test-mode PDF-entrypoint checks.

Audience is internal or redacted customer. Customer output is generated by an authorized
internal user, not a portal/login grant or a complete internal baseline. It includes
only customer-tagged narrative, requirements and section/domain/deliverable context.
Questions, decisions, actors, owners, discovery Task labels, internal rationale, raw IDs
and acceptance evidence are excluded. Both audiences require complete current reference
access. A generated report is not an editable master.

Coverage separates linked/unlinked exact requirements, older-head links, legitimate
maintenance, unexplained work, unresolved planning/blocking questions, selected-baseline
changes and accepted/rejected/withdrawn/unaccepted requirements. No aggregate completion
percentage or Task Done/PR-merge inference replaces these categories. Task scope is
Project-wide; requirement links are solution-scoped. The operations guide defines
bounded collections and unavailable comparison behavior.

Only the active internal approver of the exact specification baseline, with current
record/company authority, can record requirement acceptance. Changing the document's
current approver does not transfer this authority. New acceptance requires the currently
approved baseline, exact requirement revision, evaluated criteria and nonempty bounded
manual evidence plus asserted authority/role. Rejection/withdrawal may correct an
approved or superseded pair; withdrawal requires a current accepted event. Events
preserve authenticated recorder, frozen label and UTC time. Acceptance of v1 never
accepts v2. Evidence is not fetched or verified as URL truth/test success.

## Recovery and consequences

Retain used identities, baselines, consumed intents, acceptance and Sprint references.
Archive instead of rewriting history. Only unused lineages and unused draft-only
document revisions are removable through authorized operations; requirement/context
identities and numbered content retain history. Project company changes/deletion are
refused once retained Solution history exists. There is no purge cron or regeneration
recovery. Ordinary sudo cannot bypass seals.

Use successors and append-only correction events. Before migration/uninstall, back up
database and filestore consistently and test isolated restoration with exact
source/configuration. Uninstall deletes addon history; surviving native Tasks and Sprint
events cannot reconstruct it. Restore must validate frozen references, content, rules
and consumed results before enabling creation. Detailed recovery is in Solution
operations; same-version lifecycle checks are not major-version migration or Odoo.sh
production proof.

Rejected alternatives are requirements-as-Tasks, mutable latest-text baselines,
pointer-only snapshots, a generic contracts/Sales engine, copied wiki/history, automatic
planning and privileged complete-looking exports. Explicit revision and audit models
cost storage and conservative historical-access refusals but preserve explainable intent
without replacing native work. Release management, Jira import, provider expansion,
public/customer routes, financial/signature engines and full test management remain out
of scope. See [contributor checks](../contributing.md) and the actual Odoo build in
verification logs for exercised verification.
