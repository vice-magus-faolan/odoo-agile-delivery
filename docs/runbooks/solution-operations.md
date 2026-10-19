# Solution history, access and recovery

For setup, document editing and acceptance actions, use the
[Solution guide](../../addons/project_agile_solution/README.rst) and optional
[Scrum bridge guide](../../addons/project_agile_solution_scrum/README.rst).
[ADR-013](../adrs/013-solution-definition-contract.md) defines the domain contract. This
guide covers transaction, privacy and recovery constraints.

## Concurrency and atomicity

Operations use Odoo 19 nonwaiting ORM claims on the actual document, revision, identity
and authority records. An incomplete claim requests whole-transaction rollback and
native request retry in a fresh transaction, up to five total attempts. Persistent
contention can exhaust that limit and fail the request: retries are not an
eventual-success guarantee. Direct Python callers outside the native request boundary
own their transaction retry. There is no business-code retry loop, partial-transaction
refresh or manual business-code commit. A savepoint does not refresh a repeatable-read
snapshot. Unlink claims also exclude concurrent foreign-key references to the deleted
records.

Unique document/revision numbers remain database invariants. New retained history
publishes its reference on Project to conflict with company changes, deletion and
first-use sequence allocation. Document creation and approval publish on the solution;
revision allocation publishes on its document or stable identity. These shared ORM
writes order exact SOW/spec references and competing new heads. Actual lifecycle writes
conflict with revision edits. Section edits advance the parent content version,
preventing submission or a pending Task preview from missing a child-only edit.
Publication fields are server-owned, not approval authority.

Task confirmation claims its durable intent. Consumption writes that intent so an old
snapshot cannot create another Task. After retry, a consumed intent returns the same
currently authorized result. Changed draft content, a new requirement head or a changed
specification invalidates an unconsumed preview: preview again rather than reuse stale
intent. Link creation/retirement publishes the edge on its Task; discovery references
publish the question revision. Task scope/deletion guards and Sprint capture claim that
same Task before reading exact links. Sealed requirements need no Solution-wide capture
write. Native sequence rollback gaps are harmless; allocated keys are never reused.

Batch creation and multi-step operations use savepoints. Task creation, exact links,
seals and intent consumption succeed together or leave none of those changes, even when
a direct caller catches an error. Approval races must retry and reject stale intent, not
approve a different revision implicitly. Source edits never overwrite manual Task
descriptions, criteria, estimates, workflow, order or Sprint placement.

## Current access to frozen history

Review snapshots retain actual ordered content, exact membership and references,
original labels, audience and template content/version. Rename, archive and later
template changes do not alter those bytes. Requirement ordering uses stable row
identity; context uses sequence then ID. Snapshot digests cover content, not trusted
server or database administrator tampering.

`action_read_snapshot()` is the exact read/RPC API. Read, export and QWeb projections
recheck current Project, lineage, document, section, requirement/context, referenced SOW
and discovery Task access. History is not permanent permission. Inaccessible or missing
required content refuses output for both audiences with a generic error; it cannot
silently become a complete-looking baseline. Accessible archived references can still
render frozen content. Inverse ORM queries establish complete membership; a filtered or
privileged relation cache cannot establish completeness. Global descendant rules resolve
current native Project access through an unevaluated current-user query. The private
`_search` seam is version-sensitive.

Raw `_snapshot_content`, `_snapshot_digest` and `_template_content` fields use the
unassigned, non-implied `project_agile_solution.group_snapshot_storage` sentinel. Never
assign it to a user or imply it from another role. Technical Features
(`base.group_no_one`) is not deny-all: browser debug mode enables it for internal users.
Debug mode must not expose raw snapshot storage. Narrow elevation reads already-stored
payload only after parent authorization; it cannot supply reference access or approval.
The storage-only Task inverse supports a bounded completeness check without exposing
counts or permitting inverse/default edits.

During dependency-ordered Scrum upgrades, the stored scope-event rule denies all
ordinary event reads until the optional `solution_native_access` search field is
registered. Once the complete registry is loaded, current Task, Sprint and exact
requirement/specification access governs history. Do not remove that rule or use
privileged reads to make partially loaded history appear complete. The optional bridge
adds no dependency to core Scrum.

Customer output is an internally generated redacted projection, not a customer login or
the full internal baseline. Only customer-tagged narrative, requirements and
section/domain/deliverable context are included. Questions, decisions, actors, internal
rationale, owners, Spike labels, raw relation IDs and acceptance evidence are excluded.
Describe external scope in customer narrative and deliverables. Both audiences still
require complete current reference access. Report identity fixes audience and exact IDs;
caller context cannot override them. Do not expose native report URLs as a
customer-access mechanism.

Narrative becomes plain escaped text: scripts, styles, markup, links, images and remote
resources are discarded. Reports disable stored/reused attachments. Frozen baseline
content excludes current Task descriptions/evidence; internal coverage is a separate
current projection. Copied/exported files cannot be access-revoked later. Keep secrets
out of narratives/evidence and restrict distribution and retention.

Coverage is project-wide for native Agile work but solution-scoped for requirement
links. Maintenance reasons explain unlinked work; they do not approve it. Latest heads
include working successors. Without a chosen comparison, changes report `not_selected`.
More than 1000 rows in any queried requirement identity/revision, active-link,
Project-task or acceptance collection refuses preview. Caller and narrow elevated
cardinality checks cap at 1001, never returning elevated counts. These bounds are not a
latency or large-Project SLA. Split initiatives rather than bypass limits with sudo.

## Acceptance and correction

Only the active internal Project administrator who actually approved an exact spec
baseline, with current record/company authority, can record its requirement acceptance.
Reassigning the current document approver does not transfer historical authority. New
acceptance requires the currently approved baseline; rejection or withdrawal can correct
an approved or superseded baseline. Withdrawal requires a current accepted event for
that exact requirement/baseline pair. Criteria and bounded manual evidence are required.
External authority names and evidence text are assertions by the authenticated recorder,
not verified URLs or test results. Task Done, PR merge and approval of another baseline
do not accept requirements.

Correct sealed content through successors; correct decisions through append-only
rejection/withdrawal. Returned document review does not unseal reused requirement
content. A question successor reopens its resolution rather than pretending its new
answer was already approved. SOW and spec approval remain separate; an expanded spec
needs an explicitly approved changed SOW successor when a SOW exists. The model does not
detect undisclosed scope expansion in prose.

## Retention, restore and uninstall

Archive preserves navigation and identity. Only unused draft-only document revisions and
unused lineages can be deleted through permission-checked operations; requirement and
context identities/numbered rows retain their history. Restrictive references protect
used documents, intents, links and decisions. Project company moves/deletion are refused
once retained Solution history exists. No automatic purge, backfill or Task regeneration
is provided. Ordinary sudo is not a sealed-content recovery bypass.

Before migration or uninstall, take a consistent database and filestore backup with
exact source, addon, image and configuration versions. Test restoration in isolation.
Validate frozen payloads/digests, revision membership/reference identities, current
Project/company/Task rules, event capture markers and consumed-intent Task IDs before
allowing creation. Do not regenerate Tasks, backfill old Sprint context from current
links, infer acceptance or retry a partial transaction. If an upgrade fails, restore
source and database/filestore together; do not run old code on an unverified new schema.
Native import callers must inspect returned error messages and result IDs; an import
that reports row errors is not a successful operation.

Uninstall deletes addon tables/fields and is not archival. Native Tasks and Sprint
history survive removal of optional extensions, but cannot reconstruct deleted Solution
traceability. Bridge reinstall leaves old events `not_available`, not fabricated
empty/captured history. Only a verified consistent backup restores lost history.
Same-version populated upgrades do not prove major-version migration. Native HTML
verification does not prove production PDF, Enterprise, Odoo.sh staging, customer
suitability or legal sufficiency. See the verify log for the exercised Odoo build and
[contributor checks](../contributing.md) for verification commands.
