# Solution document baselines

The optional `project_agile_solution` addon provides SOW and specification baselines for
Odoo 19 Community. It depends on `project_agile` and uses native ORM, views and actions.
Its license is LGPL-3.

## Records and normal operation

- `project.agile.solution.document`: stable SOW/spec identity under a lineage, explicit
  active internal native Project Manager approver, rename/archive metadata.
- `project.agile.solution.revision`: server-numbered draft -> review -> approved ->
  superseded lifecycle, exact predecessor and optional same-lineage SOW reference.
- `project.agile.solution.section`: actual ordered sanitized HTML/title/audience, owned
  by one exact revision. Sections cannot be reassigned by inverse/x2many edits.
- `project.agile.solution.template`: editable company/shared narrative starting point.
  Explicit copy appends selected sanitized sections and captures version, title and
  actual source content. Later template edits never propagate.
- One native transient operation wizard collects a return reason or chosen template.

Use Project's Solution Documents/Revisions menus. Create the document and name its
approver. Open/New Working Revision returns an existing draft/review or creates a
numbered successor. Edit actual narrative sections in their native forms; submit freezes
content and stores the exact payload/digest. The designated approver approves only that
document. Explicit return with reason reopens a review; approved content requires a
distinct successor. Approval of the successor supersedes the previous baseline without
altering its content/approval evidence.

Internal briefs do not require SOW. When a SOW document exists, spec approval requires
an independently approved selected SOW baseline. Hidden scope cannot be treated as
absence. A spec explicitly marked scope change requires an approved changed successor
SOW, not merely discovery or spec approval. A SOW-content change during spec review
invalidates approval and requires return/resubmission. This is an explicit human scope
disposition, not a semantic/legal engine that detects unreported scope expansion in
prose. Self-approval is allowed only for the specifically designated active manager, as
ADR-013 states; authority is checked again at approval and never inferred from context.

## Exact content and current authority

The review payload holds actual ordered section content and immutable provenance, not
mutable linked names. It includes original document/lineage/Project labels, revision
identity, scope disposition/rationale, actual referenced SOW content, exact section
IDs/order/audience/HTML and template source content/version. Rename/archive changes
navigation, not payload bytes. The digest covers content; this is not a legal signature
or tamper-proof proof against trusted server code/DB administrators.

`action_read_snapshot()` is the explicit exact read/RPC API. Native `read` and exports
invalidate cached projection fields and recheck current Project/document/lineage,
section, exact requirement/context and referenced SOW closure before exposing sealed
text/digest. Template provenance follows the same current narrative-access boundary.
Internal storage is field-group restricted; a narrow elevation fetches already stored
payload only after parent authority and cannot approve, mutate or supply reference
authority. The three raw fields (`_snapshot_content`, `_snapshot_digest`,
`_template_content`) use the unassigned, non-implied
`project_agile_solution.group_snapshot_storage` sentinel. Never assign it to users or
imply it from a user role. Technical Features (`base.group_no_one`) is not deny-all:
native browser debug mode enables it for internal users. Debug mode must not grant raw
read/export access. The checked public projections still serve intact closure and refuse
newly inaccessible closure in both normal and debug sessions. Trusted administrators
changing group policy or arbitrary server/DB code remain the trust root, not an
application immutability guarantee. Inaccessible closure fails, never silently renders
incomplete content as a complete baseline. Native QWeb reports use the checked
projection API and revalidate the complete reference closure. See
[rendering, coverage and acceptance](solution-rendering-and-acceptance.md) for internal
and redacted customer output.

Global Project/company rules additionally resolve each parent through an unevaluated
current-user query. Custom/native parent rules therefore constrain descendants rather
than relying on sudo rule compilation or a cached list of allowed IDs. The existing
private exact-version `_search` seam remains upgrade-sensitive.

## Concurrency and atomicity

Operations use Odoo 19 nonblocking ORM claims on their actual document, revision,
identity and authority records. A shared helper requires a complete native
`try_lock_for_update` claim and raises `ConcurrencyError` if any row is unavailable.
Odoo automatically rolls back and retries the complete request in a fresh transaction,
up to five total attempts, as it does for supported PostgreSQL concurrency failures.
Exhaustion still fails the request; there is no indefinite retry or business-code retry
loop. Never refresh half a transaction or commit business code. Non-identifier claims
allow unrelated foreign-key references; destructive/identifier guards keep stronger
claims. Unique `(document_id, number)` remains the final database invariant.

New retained history publishes its reference on Project to conflict with company
changes/deletion and concurrent first-use key allocation. Document creation publishes on
its solution, approval publishes the approved revision there, and revision allocation
publishes on its document. These shared ORM writes preserve SOW/spec ordering and force
stale allocation contenders to restart. Actual lifecycle writes conflict with concurrent
revision edits. Narrative section changes also advance their parent revision content
version so a concurrent submission or pending preview cannot miss a child-only edit.
Publication fields are server-owned, group-restricted and carry no approval authority.

The canonical isolated source probe runs actual separate Odoo shell processes and
PostgreSQL backends for successor-allocation and approval races. Both contenders
establish old snapshots; the winner holds its transaction while the loser attempts
mutation. The loser must retry a fresh transaction, then reject stale intent. Exactly
two revisions remain, v1 is unchanged, and only v2 becomes approved. Probe commits and
subprocess cleanup exist solely inside the explicitly disposable test fixture.

Batch model creation and multi-step revision operations use savepoints to prevent
partial rows even if a trusted Python caller catches an error. RPC/import writes use the
same model boundaries. Lifecycle/audit/identity fields and review/history edits are
rejected even through ordinary sudo, context defaults and relational commands.

## Retention and recovery

Draft-only unused revisions can be explicitly removed after authority checks. Children
are removed through guarded model operations; restrictive references prevent dangling
history. Reviewed/approved/superseded revisions and referenced document/lineage/Project
history cannot be destructively deleted. Native Project company reassignment with
solution document history is refused; archive/rename remain available. No purge cron,
automated backfill, task regeneration or persistent-data deletion is introduced. Correct
through return/successor events; normal sudo is not a recovery bypass. Back up
DB/filestore before production migration/uninstall. Odoo addon uninstall drops its
tables; disposable uninstall/reinstall proves lifecycle health, not retention across
uninstall. Controlled restore must validate immutable content/reference identities
before enabling creation.

## Verification

From the repository root, run `./scripts/verify` in a disposable Docker environment. It
exercises native baseline tests, persisted-data upgrade/uninstall/reinstall,
separate-process allocation and approval races, and browser journeys, then removes its
owned resources automatically. The log records the actual Odoo build and per-phase
native test results.
