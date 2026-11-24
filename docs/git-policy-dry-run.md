# Deterministic Git policy dry runs

Target: Odoo 19 Community, with an optional Odoo-compatible LGPL-3 addon. The evaluator
records informational proposals, never operational authority. It does not write Tasks or
effect markers or schedule attempts; the separate apply worker owns those boundaries.
There is no provider call or ingress hook in evaluation.

## Explicit entry point and visibility

A Git Policy Manager opens a readable Repository and selects **Evaluate Dry Run (20
PRs)**. The action opens immutable decisions in native list and form views; the Project
configuration menu also lists historical dry runs. Counters use the current user's
permissions. Current native Task visibility intersects current native Project visibility
and company rules for searches, counts, grouping, reads and exports. Hidden Tasks
produce no proposals or public existence result. Context values and defaults cannot
grant capability or company membership, select Tasks, or supply a snapshot or action.

`action_dry_run_git_policy(after_id=0)` evaluates one ascending normalized PR-ID page,
at most twenty merged PRs. `next_pr_cursor` in its serializable action is the last
examined PR ID; authorized RPC callers can pass that cursor to examine the next page.
The ordinary button evaluates the first page only. Paging is a query cursor, never a
Task selector or provider authority. Empty pages are harmless. Dry-run reevaluation is
explicit: the same page after a matching check arrives rechecks the complete rule and
all names. The separate apply scheduler rechecks existing eligible waiting attempts with
the same repository and head predicates, never associating Tasks from check names.

Each page loads at most twenty rules, twenty Tasks per PR, 400 associations, 8,000
current-delivery key audits, 400 relevant checks, and 8,000 prior decisions. The extra
row detects overflow; `evidence_limit` fails closed and does not choose a winner from
incomplete evidence. At most twenty visible Task diagnostics are emitted for an
oversized PR. Authorities are checked on the concrete visible Task batch once per
approval, not repeatedly for each PR and Task. A denied executor record rejects the
approval batch conservatively. New snapshots necessarily require inserts; repeat polling
does not append identical evidence or decisions.

## Provenance is not a boolean or a post-retention signature

ADR-012 explicitly trusts database administration and reviewed server code. The
protected delivery ledger represents authenticated ingress: the existing GitHub
controller verifies exact-body HMAC before its private recorder. Ordinary callers cannot
create or edit ledger facts or association audits. No new authentication boolean is
added, and a digest is not claimed to independently prove HMAC after retained payload
removal. A provider implementation outside that reviewed trust boundary requires
separate review; this addon does not add an ingress adapter.

The private sealer re-resolves fixed-model records in its own current-user environment.
The delivery must be processed and have a real attempt. It must have no lease token or
lease expiry, a valid SHA-256 digest, and a payload size from 1 to 262,144 bytes. These
bounds are fixed, not configurable. Its receipt time must be no later than its
settlement time, which must be no later than the server time. Its repository, company
and source event must match exactly. A fake processed flag alone is insufficient. PR
identity and the complete 40- or 64-character hexadecimal head SHA are preserved without
repair. The current delivery audit must identify the exact PR, repository-local
immutable key and current Task. Its outcome must be Associated or Already Associated,
and its source must be the PR title, body or head branch. An old immutable association
is not proof of the current PR's keys. Raw PR strings are never reparsed by policy to
choose Tasks. Only normalized association and audit records supply candidates. Wrong
scope, stale links, absent provenance, unprocessed or unsettled receipts and seals
produced by public calls or context values are rejected.

One version-1 immutable PR and Task evidence bundle stores the exact normalized PR,
bounded current audit references, and up to twenty check references with their receipt
metadata. Those checks must belong to the same repository and exact PR head. Canonical
sorted JSON and SHA-256 identify the snapshot; retained payloads, titles, bodies,
secrets and exception text are absent. Snapshots are capped at 65,536 characters. Server
timestamps are separate from the material fingerprint, and exact microseconds are
retained rather than truncating Task write_date into false stale-change reports. Public
creation, editing and deletion are rejected even in superuser mode; only private
validated append paths elevate.

## Deterministic predicates and failure precedence

The PR order must be reliable. The PR's merge time must be no later than its last
update, and the last update must be no later than now. The branch must match the
configured branch exactly. Both the source merge and original receipt must be strictly
after the immutable activation cutoff. The merge and update must each be within the last
twenty-four hours. Equal cutoff times, old merges redelivered later, future or missing
times, unknown or stale ordering, and refreshed receipt or last-seen times cannot create
new eligibility.

Zero configured checks explicitly records `no_ci_condition`, never CI success. For each
exact required name, only that repository and the PR's exact head qualify. Missing,
pending or running checks cause the candidate to wait. Failed, cancelled or neutral
checks reject it. Success requires known ordering, reliable update and completion times,
completion no later than update or now, and both completion and update within the
accepted twenty-four-hour bounds. Unknown timestamps, states or ordering reject the
candidate. Two same-name provider identities always remain ambiguous, even if a
newer-looking or numerically larger run succeeded. There is no rerun ordering inferred
from IDs, receipt order or unrelated checks. A single identity's ordering comes solely
from the normalized Known, Stale or Ambiguous state. A failed required name outranks
waiting on another name, independent of the order of names, records or deliveries.

Only fully eligible rules enter conflict detection. More than one for the same PR and
Task pair conflicts, including identical targets; no priority, record-order winner or
racing Task write exists. Diagnostics list at most twenty stable rule IDs. Disabled,
revised or archived authority, an inactive repository or Task, an ineligible or closed
Task, an already-reached target, and a changed manual Task snapshot are explicit skips
or rejections. The Task's initial stage, state and exact write_date are retained per
evaluation epoch: polling cannot silently revive a stale candidate.

## Effects and recovery

Dry runs append only observations and proposals. They do not mutate Tasks, Sprints or
their history, facts, followers, chatter or approval epochs. They do not reserve or
consume real effect idempotency keys, or authorize execution. A mode or revision change
needs fresh approval and a new cutoff; no proposal can be promoted to an effect. An
already reached target is informational only. The implemented Task transition fence and
independent-connection races between application, manual edits and disabling protect the
separate apply boundary, not this dry-run snapshot. Proposals do not use that fence to
prove an identical manual away-and-back change; they are deliberately never executable.

Database uniqueness deduplicates concurrent append producers; proposals remain
informational snapshots, not execution authority. Serialization and uniqueness races
require a fresh transaction, not an in-transaction privilege bypass or stale-cache
retry. No business write can be partially applied here. If evidence or authority is
uncertain, disable or revoke through existing authorized controls, retain the immutable
diagnostic, correct the source or configuration and obtain fresh approval where
required. Do not alter timestamps or replay old receipts to create eligibility.
