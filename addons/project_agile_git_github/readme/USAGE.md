## Link facts to tasks

Use an existing task key such as `ENG-142` in one of these supported source fields:

- `push`: branch ref and each commit message;
- `pull_request`: title, body and head branch;
- `check_run`: name and output title.

For example, use branch `feature/ENG-142-oauth` or commit message
`ENG-142: Add OAuth callback`. Keys use an uppercase prefix of 2 to 10 letters
or digits starting with a letter, a hyphen, and a positive decimal suffix.
Separate the key from surrounding word characters. Matching is limited to
active tasks in the configured repository Project and company. Keys are matched
throughout complete commit messages and PR bodies before text is discarded or
shortened for display. Other source text is limited to 4,096 characters. Keys
are at most 128 characters each.

For a release PR, put the promoted task keys in its body. The first 100 distinct
keys, in source order, are considered for linking; repeated keys take no extra
slots. With more than 100, the retained keys are still considered and the
association audit records **Too Many Keys** for the overflow. Unknown,
archived and non-local keys use slots but do not create links. List only the
intended tasks, and split larger releases across PRs to retain every link.
Other source fields keep their 20-key limit: more than 20 rejects all links
from that field. A PR title or head branch is not a substitute for the release
list. Existing links and audits survive payload cleanup. An old delivery whose
body was already reduced to an empty **Too Many Keys** summary cannot recover
the discarded keys; send a new supported PR event with the release list.

After scheduled processing, open the task and choose **Branches**, **Commits**,
**Pull Requests** or **Checks** to inspect its linked facts. A missing link can
mean the key was unknown, invalid, excessive or referred to archived work.

## Inspect and recover deliveries

Open **Project > Tasks > Git Repositories**, select the repository and choose
**Deliveries**. Inspect **Provider Delivery Id**, **Event Type**, **State**,
**Attempt Count**, **Next Retry At**, **Payload Sha256** and **Error Summary**.
**Replay Mismatch Count** and **Last Replay Mismatch At** identify conflicting
reuse of a delivery ID.

- **Queued** awaits scheduled processing. **Processing** has a five-minute
  lease; an expired lease becomes eligible for another claim.
- **Retryable** awaits **Next Retry At**. Transient failures have four retry
  waits of 1, 2, 4 and 8 minutes, totaling 15 minutes. A fifth failure becomes
  **Failed**: about 15 minutes after the first try at the configured one-minute
  scheduler cadence. Correct the cause before choosing **Reprocess** for
  another try. Malformed payloads fail without automatic retries; unsupported
  events with retained payloads become **Discarded**.
- **Processed** means processing completed. Inspect task-linked facts to see
  the observations and their source ordering. A push retains at most its first
  100 commits. **Omitted Commit Count** and **Commit Omission Reason** identify
  any remainder; the branch head still reflects the push, subject to source
  ordering. The notice survives successful processing and reprocessing.
- After correcting the cause of a **Failed** or **Discarded** delivery, choose
  **Reprocess** if a retained payload is still available. It queues the same
  delivery again and keeps its attempt count, so a delivery that used its five
  attempts gets one more try.

When a branch is deleted on GitHub, its push delivery is **Discarded**. The
branch, its commits and its task links stay as they were, so a deleted branch
keeps its last known head. A later push to a branch with the same name goes
through the usual ordering checks.

Digest-only, oversized-input and purged deliveries have no payload to
reprocess. After correcting configuration, push again or re-run the check so
GitHub sends a new delivery; for a PR, send a new supported PR event. Exact
redelivery of an old delivery does not fill its missing payload.

Retained excerpts receive a 30-day expiry. Daily cleanup removes expired
excerpts only from **Processed** or **Discarded** deliveries, in batches of at
most 100. **Retained Payload Purged At** records cleanup; delivery metadata,
digest, facts and association audit remain. **Queued**, **Processing**,
**Retryable** and **Failed** payloads are retained for recovery even after expiry.
