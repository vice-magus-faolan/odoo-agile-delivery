# ADR-013: Solution definition, revisions and delivery traceability

## Status and outcome

Accepted and implemented by optional `project_agile_solution` and
`project_agile_solution_scrum`. This ADR owns the domain, transaction and access
contracts. [Solution operations](../runbooks/solution-operations.md) provides admin
recovery and access instructions.

Agile teams need to explain agreed intent, uncertainty, delivery coverage and explicit
acceptance. Requirements express delivery intent, not another Task system. The design
was informed by one prospective user's request and synthetic scenarios.
[FAR 37.602](https://www.acquisition.gov/far/37.602) informed outcome-based scope and
[NASA's handbook appendices C and D](https://www.nasa.gov/reference/system-engineering-handbook-appendix/)
informed identifiable, verifiable requirements and traceability.

## Dependencies and native boundaries

Solution core depends on LGPL-3 `project_agile` and native Community `portal`,
transitively native Community Project. Both Solution addons retain LGPL-3. Odoo 19
Community is the tested edition. The architecture is Odoo.sh-first, portable to
self-hosted Odoo. Enterprise and Odoo.sh installed-extension behavior require separate
verification. This is an Odoo-compatible suite, not a claim of full OCA conformity.

Reuse native Tasks, hierarchy, dependencies, Agile keys/types/criteria, Project
permissions, ORM, constraints, transactions, `ir.sequence`, views and QWeb. No Sales,
Git, Scrum, Enterprise, document backend, SDK, external queue runner or custom
wiki/editor is required by core. Native `ir.cron` is the suite's scheduling boundary;
`queue_job` is not supported. General documentation remains with its selected backend.
OCA page history and Task templates do not supply immutable requirement revisions,
separate scope approval and frozen delivery references.

Native API and security decisions were inspected against
[Odoo revision 8da213dc6785e097f2558dc2d648b588957786a1](https://github.com/odoo/odoo/tree/8da213dc6785e097f2558dc2d648b588957786a1).
The current runtime is selected by the checked-in verification inputs; its Odoo build is
reported in the verify log.

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

## Stable identity discussions

Native `mail.thread` belongs only to requirement, document and context identities, never
their numbered revisions. Project readers may post without content-editing authority.
Question revision creation and owner changes subscribe the owner to the stable context.
Existing followers and subtype preferences are retained; owner changes do not infer
which subscriptions were manual.

Native mail author, recipient and follower exceptions alone are insufficient for
Solution isolation. Global message/follower rules constrain only these three models
using current-caller source subqueries, including custom Project/company rules and
archived source access. Native record authorization and recipient checks use fresh
source searches, not cached computed access predicates. The native thread access hook
retains the current company scope. Native message fetch queries include the same source
domain even when invoked with an elevated mail environment. Direct message field fetches
also check access because native mail fetch otherwise elevates. Polymorphic mail-row
relocation checks destination source access as well as existing native checks. Public
post, subscribe and unsubscribe actions require source read access, including native
self-unfollow. Following never grants source authority.

The native notification-recipient hook rechecks active internal recipients under their
own source access and permitted companies before inbox/email delivery. External contacts
and unbound email recipients are excluded; retained followers with revoked access
receive no new content. This does not recall already sent notifications or exported
copies.

Chatter attachments and scheduled messages also require current source read access.
Their native in-memory checks cannot enforce the search-only Project predicate, so
scoped search domains and concrete record checks reuse the same caller-bound source
queries. Attachments transferred from a composer to a scheduled message inherit that
message source boundary too. The native binary resolver revalidates the request caller
after public/token elevation: neither a public flag nor an attachment or binary-field
token publishes internal Solution content. Unrelated Task attachments and scheduled
messages retain their native rules and transports; this adds no disclosure grant.

The `_search`, `_check_access` and `ir.binary._find_record` extensions are private,
version-sensitive seams. Revisit them when upgrading the pinned upstream
[`ir.attachment`](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/odoo/addons/base/models/ir_attachment.py),
[`mail.scheduled.message`](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/addons/mail/models/mail_scheduled_message.py)
and
[`ir.binary`](https://github.com/odoo/odoo/blob/8da213dc6785e097f2558dc2d648b588957786a1/odoo/addons/base/models/ir_binary.py)
APIs, alongside the mail seams above. Native ORM and authenticated binary-route
regressions must retain authorized positives and outsider/revocation negatives.

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
Authority recorded through the internal proxy channel is an internal assertion, not
external authentication. Client decisions use the separate publication channel below.

## Concurrency and atomicity

Odoo 19 nonwaiting ORM claims cover the actual document, revision, identity and
authority records. An incomplete claim requests whole-transaction rollback and native
request retry in a fresh transaction, up to five total attempts. Persistent contention
can exhaust that limit and fail the request. Direct Python callers outside the native
request boundary own their transaction retry. There is no business-code retry loop,
partial-transaction refresh or manual business-code commit. A savepoint does not refresh
a repeatable-read snapshot. Unlink claims also exclude concurrent foreign-key references
to the deleted records.

New retained history publishes its reference on Project to conflict with company
changes, deletion and first-use sequence allocation. Document creation and approval
publish on the solution; revision allocation publishes on its document or stable
identity. These shared ORM writes order exact SOW/spec references and competing new
heads. Actual lifecycle writes conflict with revision edits. Section edits advance the
parent content version, preventing submission or a pending Task preview from missing a
child-only edit. Publication fields are server-owned, not approval authority.

Task confirmation claims and consumes its durable intent, preventing an old snapshot
from creating another Task. After retry, a consumed intent returns the same currently
authorized result. Link creation/retirement publishes the edge on its Task; discovery
references publish the question revision. Task scope/deletion guards and Sprint capture
claim that same Task before reading exact links. Sealed requirements need no
Solution-wide capture write.

Batch creation and multi-step operations use savepoints. Task creation, exact links,
seals and intent consumption succeed together or leave none of those changes, even when
a direct caller catches an error. Approval races retry and reject stale intent rather
than approve a different revision implicitly.

## Current authority and frozen history

Internal Project users read permitted material. Business analysts and native Project
administrators author and mutate it only with concrete record access. Business analyst
and Scrum master use separate native Odoo 19 privileges alongside Project in its
Services category. Each implies Agile member and native Project User, never Project
Administrator. Independent selectors preserve combined roles across user-form edits.
Shared templates, document approval and acceptance remain Project administrator
operations. The designated approver constraint and an explicit approval authority check
remain separate from authoring checks. Agile Project configuration and item types also
remain administrator-only, without restricting unrelated native Project writes. Authors
and Scrum operators need current native Project read access and write access on the
affected child records, not a new Project write ACL. Existing administrator paths still
require native Project write access. Public actions re-resolve typed IDs, existence,
state, company, exact references, content version and permissions. Booleans are not
integer IDs. Defaults, owner IDs and context are not authority. Task links require
current Task access and mutation checks; discovery links require an actual permitted
existing Agile Spike. Elevation is limited to already-authorized storage, never
selecting accessible records or deciding approval.

Global descendant rules use an unevaluated current-user Project subquery. Odoo 19
compiles rule domains on sudo recordsets, so a plain relational `any` is not enough to
establish native Project visibility. The private `_search` seam is version-sensitive; no
cached list of visible IDs substitutes for current custom/native rules.

Frozen history does not grant permanent access. Reads, searches, grouping, exports,
counters, navigation and reports recheck the exact reference closure, including
sections, requirements/context, referenced SOW and discovery Tasks. Accessible archived
references remain usable. Missing or inaccessible required references refuse complete
output without leaking names, IDs, counts or excerpts. Filtered relation caches cannot
establish membership completeness; inverse ORM queries establish the complete set.
`action_read_snapshot()` is the exact read/RPC API. Native export additionally requires
`base.group_allow_export`. Raw `_snapshot_content`, `_snapshot_digest` and
`_template_content` use the unassigned, non-implied
`project_agile_solution.group_snapshot_storage` sentinel. Never assign it to a user or
imply it from another role. Technical Features (`base.group_no_one`) is enabled by
browser debug mode for internal users and is not a deny-all boundary. Narrow elevation
reads stored payload only after parent authorization, without supplying reference access
or approval. The storage-only Task inverse permits a bounded completeness check without
exposing counts or permitting inverse/default edits.

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

Confirmation creates one native Task using name, description, Project and explicitly
selected Agile item type, then links exact requirements and consumes the intent in the
same savepoint. A creation-only, false-by-default copy choice includes the selected
exact Acceptance Expectations as escaped HTML in stable revision-ID order. The same HTML
preview is displayed at confirmation and supplied as editable task criteria; unchecked
previews supply no criteria. Ambient defaults cannot opt in, and link-only operations
cannot overwrite existing work. Caller default context is stripped. Native creation
effects remain native. No estimate, hierarchy, dependency, stage/state, Sprint or
ordering is supplied. Specification edits never regenerate backlogs or overwrite
manually authored Task values. Independent confirmations converge on one result;
failures leave no partial Task, links, seals or consumption.

The Task Agile tab renders active exact links read-only under current caller authority.
Inaccessible links are omitted, not elevated or counted, so a hidden requirement cannot
break Task access. The caller-specific nonstored escaped projection depends on the
existing Task reference publication updated by link creation/retirement; it neither
implies complete coverage nor substitutes the latest revision.

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
access. Report identity fixes audience and exact IDs; caller context cannot override
them. Do not distribute native report URLs as customer access. Rendering discards
scripts, styles, markup, links, images and remote resources. Frozen baselines exclude
current Task descriptions/evidence; internal coverage is a separate current projection.
Exported copies cannot be access-revoked later, so narratives and evidence must exclude
secrets and distribution/retention must remain restricted.

Coverage separates linked/unlinked exact requirements, older-head links, legitimate
maintenance, unexplained work, unresolved planning/blocking questions, selected-baseline
changes and accepted/rejected/withdrawn/unaccepted requirements. No aggregate completion
percentage or Task Done/PR-merge inference replaces these categories. Task scope is
Project-wide; requirement links are solution-scoped. Latest heads include working
successors. Without a selected comparison, changes report `not_selected`. More than
1,000 rows in any queried requirement identity/revision, active-link, Project-task or
acceptance collection refuses preview. Caller and narrow elevated cardinality checks cap
at 1,001 without returning elevated counts. Split initiatives rather than bypass limits.

Only the active internal approver of the exact specification baseline, with current
record/company authority, can record requirement acceptance. Changing the document's
current approver does not transfer this authority. New acceptance requires the currently
approved baseline, exact requirement revision, evaluated criteria and nonempty bounded
manual evidence plus asserted authority/role. Rejection/withdrawal may correct an
approved or superseded pair; withdrawal requires a current accepted event. Events
preserve authenticated recorder, frozen label and UTC time. Acceptance of v1 never
accepts v2. Evidence is not fetched or verified as URL truth/test success.

## Authenticated client publication and decisions

Internal approval precedes client sign-off and remains independent. A document may
designate one current active portal user separately from its internal approver. Project
administrators explicitly issue immutable per-user customer publications; Business
analysts cannot designate, publish or revoke. Native Project commercial follower
visibility and bearer tokens do not establish signing authority.

A publication is a grant on released bytes, not on internal Solution records. It retains
the exact approved snapshot digest, a versioned allowlisted payload and its digest,
recipient/contact, publisher and server time. Only customer narrative, customer
requirements and section/domain/deliverable context cross this boundary. Nested
requirements use the same allowlist; rationale, owner/actor identities, discovery Tasks,
template provenance, raw source IDs and internal evidence do not. Frozen labels are part
of the explicit disclosure preview. Existing internal report APIs keep their full
reference-closure checks and internal-only ACLs.

Authenticated portal HTML and downloadable HTML use the same released payload. There is
no attachment token, generic report endpoint or production PDF grant. Portal ACLs allow
publication read only. Current-caller Project subqueries, exact recipient and captured
contact, exact follower membership, active Project, solution/document and current
company membership govern search, counts, grouping, read, export and route retrieval.
Company-less Projects remain supported. Source relations and storage are field-group
restricted; client receipts expose only their own publication history. Current source
references are checked through the publication boundary, not by granting portal access
to undisclosed source rows.

Document client decisions are append-only and never invoke internal approval.
Requirement events retain separate `internal_proxy` and `portal` predecessor channels;
proxy correction cannot withdraw a real client decision. Legacy events receive the
internal-proxy default without changing original actor/time/evidence. Portal actors,
contact, time, exact publication digest and source revisions are server-controlled. Only
the current designated client with an issued current publication may decide. Client
correction is available while internally approved; supersession preserves authorized
history but rejects new decisions and carries nothing forward. A newer draft alone does
not invalidate the approved baseline.

Publication issuance and client decisions claim the current Solution and Project source
owners before accepting active-lineage authority. A winning Solution archive, Project
archive or Agile disable forces stale transactions through native retry and fresh
reauthorization. Reversible archive/unarchive does not permanently revoke publications.
Issuance also claims the exact native Project/contact follower and writes its latest
issued-publication reference through the ORM. Native invitation deletion or reassignment
then conflicts on that same row even when neither transaction initially sees a grant:
removal first forces issuance to retry and reject, while issuance first forces an
old-snapshot remover to retry and retire the new grant. A claim alone would not protect
the latter ordering after the issuer commits. The private reference is non-authorizing,
does not change follower identity or notification subtypes, is not copied, and uses
`ondelete="set null"` so addon teardown does not retain native followers. Reinvitation
creates a different follower and cannot revive the retired grant; deliberate fresh
issuance is required. Nullable references need no historical head reconstruction.
Decision actions also claim the publication, document, baseline and exact requirement.
Append publishes real event heads on publication/requirement to conflict with revocation
and competing submissions. The expected head from the current page rejects duplicate or
stale submission after native whole-transaction retry. Revoke-only hooks follow native
authorized follower, user/contact, group membership or implication and company-user
inverse mutations. They retire affected live publications in the same transaction. Group
membership and implication writes compare each affected user's native effective
`base.group_portal` membership and `share` eligibility before and after the authorized
mutation. Only changes to that eligibility retire live publications. Unrelated group
additions/removals, repeated commands and redundant implication paths preserve live
publications and decisions, including portal-wide feature implications. Native Project
features such as Milestones also preserve eligible clients' publications and decisions.
This is not a general security-change engine or a claim of serialization against
arbitrary administrator/SQL reconfiguration. The invitation boundary does not serialize
first issuance against every recipient/contact or group/company inverse edit. Current
availability still rejects an inactive or mismatched identity or missing membership.
Restoring eligibility cannot revive a retired publication; a fresh explicit issuance is
required. Concurrent compound administrator changes beyond these native paths remain
outside that guarantee. Signer changes retire the old signer publications. Regrant
requires a new publication; audit actors are never reassigned. Downloaded copies cannot
be recalled.

This retained per-recipient copy costs storage but keeps disclosure/revocation policy
locally understandable without broadening every internal model ACL.

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
and consumed results before enabling creation. Restrictive references protect used
documents, intents, links and decisions. Validate revision membership, current
Project/company/Task rules, event capture markers and consumed-intent Task IDs after
restore. Do not regenerate Tasks, backfill Sprint context from current links or infer
acceptance. Native import callers must inspect returned errors and result IDs rather
than treating row-error responses as success. Restore source and database/filestore
together after a failed upgrade; old code must not run on an unverified newer schema.
Bridge reinstall leaves old events `not_available`, not fabricated empty/captured
history. Only a verified consistent backup restores lost history. Admin steps are in
[Solution operations](../runbooks/solution-operations.md).

Rejected alternatives are requirements-as-Tasks, mutable latest-text baselines,
pointer-only snapshots, a generic contracts/Sales engine, copied wiki/history, automatic
planning and privileged complete-looking exports. Explicit revision and audit models
cost storage and conservative historical-access refusals but preserve explainable intent
without replacing native work. Release management, Jira import, provider expansion,
anonymous/public access, financial/signature engines and full test management remain out
of scope. See [contributor checks](../contributing.md) and the actual Odoo build in
verification logs for exercised verification.

## People served by native work

Optional Task Actors reference stable context identities of kind Actor in the same
Project and company, across its Solutions. They display the current identity name, not
implicit latest-revision content or a frozen acceptance baseline. Existing
Project/context rules govern selection; Business analysts and Project administrators
need native Task write authority. Reference commands cannot create, edit or delete
context through a Task. Core Agile remains independent. New selections explicitly reject
archived Actors, independent of active_test; retained historical links remain usable.
Ordinary same-Project Task duplication retains Actors for Agile members as well as
authors, including child work. A private Python command-list subtype marks native
copy_data inheritance, bound to the accessible source Task, exact Actor set and Project.
After checking source read access, narrowly elevated enumeration obtains that source
relation only; caller-context checks authorize the complete identities and their scope
before any copy payload is returned. This avoids silently copying a record-rule-filtered
subset. It grants no selector role: JSON/RPC roundtrips lose the subtype, explicit copy
defaults remain ordinary selections, and create/read/context/company checks still apply.
Cross-Project and whole-Project/template copies omit source-owned Actors without copying
Solution identities.
