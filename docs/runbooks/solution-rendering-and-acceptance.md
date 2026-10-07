# M8 exact solution rendering, coverage and acceptance

## Operator journey

This optional Odoo 19 Community addon remains LGPL-3 and depends only on
`project_agile` (native Community Project transitively). No Sales, Scrum, Git,
Enterprise document backend, editor, portal ACL or custom public route is added.
The repository is Odoo-compatible, not an OCA-conformity or deployment claim.

1. In Project → Solution Revisions, open the actual document/revision. Draft and
   review content are explicitly unapproved; approved/superseded rows remain exact
   historical content. A working successor never aliases the baseline.
2. Choose Preview / Coverage and deliberately choose the exact revision and
   Internal or Redacted Customer audience. Optional comparison selects an exact
   approved/superseded baseline of the same document. Native fields have labels;
   audience uses native radio controls and status warnings are accessible.
3. Render Selected Audience opens native QWeb HTML. The Print menu also has two
   explicitly named native report actions. HTML is the portable first-release
   output; no external document engine is required. The customer result is an
   internally generated redacted projection, not customer authentication or a
   complete internal baseline. Do not expose native report URLs to customers.
4. Internal preview shows honest coverage/change categories. Use authorized
   native text/CSV export if needed. Output is recomputed from authoritative
   records; no editable generated master, completion percentage or report
   attachment is stored. Copy/export files retain sensitive content: distribution
   and retention remain an operator decision, not a new customer-access grant.
5. Project → Exact Requirement Decisions records an explicit exact requirement,
   approved spec baseline, decision, asserted authority/role, evaluated criteria
   and bounded nonempty manual evidence/reference. Only the active internal
   Project Manager who actually approved that exact baseline, with current
   Project/record/company authority, may record it. Renaming/reassigning the
   document's current approver does not transfer historical acceptance authority.
   Events record the authenticated recorder, frozen recorder label and UTC time.

Named external authority/role is an assertion by that internal approver, not
external authentication, cryptographic proof, legal signature, verified URL truth
or automatic test success. Evidence is plain text: no fetch, embedded external
resource or clickable user-selected URL. Task Done and PR merge do not create
acceptance. New acceptance requires the currently approved baseline; rejection
and withdrawal can correct an approved or superseded baseline without rewriting
prior events. Withdrawal requires a current accepted event for that exact pair.
Acceptance of v1/baseline1 does not accept v2 or baseline2, even if content is reused.

## Audience/completeness contract

Every render rechecks current internal user, exact revision and complete required
reference closure before output. Exact snapshots retain original Project/document/
lineage/narrative labels and content after rename/archive. Access is current, not
historical: loss of access to any required Project, requirement, context, section,
referenced SOW or discovery Task refuses both audiences with a generic error.
This intentionally sacrifices availability rather than silently omitting inaccessible
content and labelling a result complete. No denied names, counts, IDs or excerpts
are returned. Accessible archived references can still render their frozen content.

The customer projection allowlists only customer-tagged narrative/requirements and
customer-tagged section/domain/deliverable context. Questions, decisions and actors
are conservatively excluded even when tagged customer; describe authorized external
scope explicitly in customer narrative/deliverables instead. Internal affected
requirements, owner/contact details, Spike labels, raw relation IDs, acceptance
evidence and internal scope-change rationale are not emitted. Report identity fixes
its audience; context or report data cannot override the projection or exact docids.

Narrative HTML is reduced to text; scripts/styles, tags, links, images and remote
resource attributes are discarded. All values remain ordinary strings and QWeb
`t-out` escapes them, including text that resembles markup. Both actions explicitly
disable report attachments and reusable attachment rendering. Baseline rendering
contains frozen solution intent, not mutable current Task descriptions or evidence.
Coverage is a separate current internal projection, not frozen baseline content.

## Honest scope and bounds

Coverage is checked and internal only. Categories are unlinked exact requirements,
linked exact requirements, work linked to older requirement heads, legitimate
unlinked maintenance with reason, unexplained unlinked work, unresolved selected
planning/blocking questions with authorized affected requirements/discovery work,
explicitly accepted evidence, rejected/withdrawn decisions, approved-but-unaccepted
requirements, and added/changed/removed requirement/context identities relative to
a selected baseline. Narrative changes ignore copied section row IDs. Without a
comparison the change category explicitly says `not_selected`.

Work is project-wide native Agile work, while requirement links are solution-scoped;
other initiatives may legitimately own that work. This scope distinction is stated,
not hidden in an aggregate. Maintenance reasons are explanatory, not approval.
Current latest requirement heads include sealed and working successors. A baseline
linked to an older exact row remains historical, not silently upgraded.

Preview refuses scopes exceeding 1000 rows per queried collection (requirement
identities/revisions, active links, Project Agile Tasks or acceptance events). Each
collection uses one bounded caller query and one narrow elevated cardinality deny
check; elevated counts never reach output. Head/event grouping is linear in memory;
per-row authorization and existing closure checks remain necessary. This is a bounded
preview, not a promise of constant query count, a large-Project dashboard SLA or
enterprise performance validation. Split initiatives; never bypass limits with sudo.

## Recovery and verification

Back up DB/filestore before uninstall/migration. Append successor requirements,
new baselines, rejection or withdrawal; do not mutate seals/events even with sudo.
No cron retention or document attachment cache is introduced. Uninstall removes
addon tables and is not archival; native Tasks remain owned by their native modules.
No production restart/deployment/customer distribution is performed by verification.

Use canonical `./scripts/verify` on a disposable environment. In the registered M8
lane the approved local entrypoint is:

    python3 /home/molty/.hermes/scripts/odoo_m8_verify.py t_a7974c61 verify

Focused native checks use the same task's capability, declared disposable DB,
`--init project_agile_solution --test-enable --test-tags /project_agile_solution`
and stop-after-init. The discovery gate requires every declared rendering test
and both browser test methods in addition to all baseline/requirement/trace/bridge
methods. Canonical install, targeted upgrade, reverse uninstall/reinstall and
M1–M7 browser/concurrency/Hoot coverage remain intact. No source/archive substitute.

Tests materialize all three explicitly synthetic public-informed narratives: portal
intent/SOW → exact existing Task → recorded synthetic evidence/acceptance; unknown API
discovery → unresolved Spike → separately approved hypothetical SOW/spec scope change;
internal initiative → no SOW, cross-cutting intent and unlinked maintenance. Native
browser journeys preview draft and exact approved direct report separately. These
prove tested implementation behavior, not observed API facts, legal sufficiency,
customer acceptance, production isolation or actual Odoo.sh staging compatibility.
