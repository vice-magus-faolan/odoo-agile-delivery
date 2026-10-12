# Deterministic Git policy dry runs

Target: Odoo 19 Community, private Odoo-compatible LGPL-3 optional addon. The evaluator
records informational proposals, never operational authority. It does not write
Tasks/effect markers or schedule attempts; the separate apply worker owns those
boundaries. There is no provider call or ingress hook in evaluation.

## Explicit entry point and visibility

A Git Policy Manager opens a readable Repository and selects **Evaluate Dry Run (20
PRs)**. The action opens ordinary immutable list/form decisions; the Project
configuration menu also lists historical dry runs. There are no sudo counters. Current
native Task visibility intersects current native Project visibility and company rules
for searches, counts, grouping, reads and exports. Hidden Tasks produce no proposals or
public existence result. Context/defaults cannot grant capability, company membership,
select Tasks or supply a snapshot/action.

`action_dry_run_git_policy(after_id=0)` evaluates one ascending normalized PR-ID page,
at most twenty merged PRs. `next_pr_cursor` in its serializable action is the last
examined PR ID; authorized RPC callers can pass that cursor to examine the next page.
The ordinary button evaluates the first page only. Paging is a query cursor, never a
Task selector or provider authority. Empty pages are harmless. Dry-run reevaluation is
explicit: the same page after a matching check arrives rechecks the complete rule and
all names. The separate apply scheduler rechecks existing eligible waiting attempts with
the same repository/head predicates, never associating Tasks from check names.

Each page loads at most twenty rules, twenty Tasks per PR, 400 associations, 8,000
current-delivery key audits, 400 relevant checks, and 8,000 prior decisions. The extra
row detects overflow; `evidence_limit` fails closed, never selects a partial successful
winner. At most twenty visible Task diagnostics are emitted for an oversized PR.
Authorities are checked on the concrete visible Task batch once per approval, not
repeatedly per PR/Task. A denied executor record rejects the approval batch
conservatively. New snapshots necessarily require inserts; repeat polling does not
append identical evidence/decisions. The discovered 20-Task fixture asserts fewer than
800 cold queries and 200 repeat queries.

## Provenance is not a boolean or a post-retention signature

ADR-012 explicitly trusts database administration and reviewed server code. The
protected M6 ledger represents authenticated ingress: the existing GitHub controller
verifies exact-body HMAC before its private recorder. Ordinary callers cannot
create/edit ledger facts or association audits. No new authentication boolean is added,
and a digest is not claimed to independently prove HMAC after retained payload removal.
A provider implementation outside that reviewed trust boundary requires separate review;
this addon does not add an ingress adapter.

The private sealer re-resolves fixed-model records in its own current-user environment.
It requires processed state, an actual attempt, cleared leases, receipt <= settlement <=
server time, valid bounded digest/size, exact repository, company and source event. A
fake processed flag alone is insufficient. PR identity and full 40/64-hex head SHA are
preserved without repair. Current-delivery audit must have the exact PR identity,
repository-local immutable key and current Task, with associated/already-associated
outcome and supported title/body/head_ref source. An old immutable association is not
proof of the current PR's keys. Raw PR strings are never reparsed by policy to choose
Tasks. Only normalized association/audit records supply candidates. Wrong scope, stale
links, absent provenance, unprocessed or unsettled receipts and public/context-produced
seals are rejected.

One version-1 immutable PR/Task evidence bundle stores the exact normalized PR, bounded
current audit references, and up to twenty same-repository/exact-head check references
with their receipt metadata. Canonical sorted JSON and SHA-256 identify the snapshot;
retained payloads, title/body, secrets and exception text are absent. Snapshots are
capped at 65,536 characters. Server timestamps are separate from the material
fingerprint, and exact microseconds are retained rather than truncating Task write_date
into false stale-change reports. Public create/write/unlink is rejected even in
superuser mode; only private validated append paths elevate.

## Deterministic predicates and failure precedence

Require reliable PR order, merged_at <= updated_at <= now, exact configured branch,
source merge and original receipt both strictly after the immutable activation cutoff,
and merge/update freshness within twenty-four hours. Equal cutoff times, old merges
redelivered later, future/missing times, unknown/stale ordering and receipt/last_seen
refresh cannot create new eligibility.

Zero configured checks explicitly records `no_ci_condition`, never CI success. For each
exact required name, only that repository and the PR's exact head qualify.
Missing/pending/running waits; failure/cancelled/neutral rejects. Success requires known
ordering, reliable update/completion times, completion no later than update or now, and
completion/update within the accepted twenty-four-hour bounds. Unknown
timestamps/state/order reject. Two same-name provider identities always remain
ambiguous, even if a newer-looking or numerically larger run succeeded. There is no
rerun ordering inferred from IDs, receipt order or unrelated checks. A single identity's
ordering comes solely from M6's normalized known/stale/ambiguous state. A failed
required name outranks waiting on another name, independent of name/record/delivery
order.

Only fully eligible rules enter conflict detection. More than one for the same PR/Task
conflicts, including identical targets; no priority, record-order winner or racing Task
write exists. Diagnostics list at most twenty stable rule IDs. Disabled/revised/archived
authority, inactive repository/Task, ineligible or closed Task, already-reached target,
and changed manual Task snapshot are explicit skips or rejections. The initial Task
stage/state/exact write_date is retained per evaluation epoch: polling cannot silently
revive a stale candidate.

## Effects, recovery and remaining phases

Dry runs append only observations and proposals. They do not mutate Tasks,
Sprints/history, facts, followers/chatter or approval epochs, reserve/consume real
effect idempotency keys, or authorize execution. A mode/revision change needs fresh
approval/cutoff; no proposal can be promoted to an effect. An already reached target is
informational only. The implemented Task transition fence and independent- connection
apply/manual-edit/disable races protect the separate apply boundary, not this dry-run
snapshot. Proposals do not use that fence to prove an identical manual away-and-back
change; they are deliberately never executable.

Control row locks serialize scoped append producers; database uniqueness is a second
dedupe guard. Serialization/uniqueness races require a fresh transaction, not an
in-transaction privilege bypass or stale-cache retry. No business write can be partially
applied here. If evidence or authority is uncertain, disable/revoke through existing
authorized controls, retain the immutable diagnostic, correct the source/configuration
and obtain fresh approval where required. No purge, backfill, production activation,
publication or deployment is authorized.

Canonical verification discovers the ORM matrix independently without GitHub or Scrum,
then in aggregate clean install, upgrade and dependency-safe uninstall / reinstall.
Optional Scrum fixtures assert unchanged Task fields/history. Existing M5 native UI and
M6 ingress/security/normalization tests remain in the same gate. Production/customer
outcome remains unobserved.
