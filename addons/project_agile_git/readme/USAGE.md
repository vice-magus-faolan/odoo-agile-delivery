1. Open an Agile-enabled Project and choose **Repositories** to see its
   repositories. Open one and use **Branches**, **Commits**, **Pull Requests**
   or **Checks** to inspect the observations and follow their provider links.
2. Open an Agile task and use the same fact buttons to see observations linked
   to its stable Agile key. Visibility and counters follow your access rights.
   The GitHub connector guide explains which source fields can establish links.
3. As a Project administrator, open the repository and choose **Deliveries**.
   Inspect **Provider Delivery Id**, **Event Type**, **State**, **Attempt Count**,
   **Next Retry At** and **Error Summary** when facts have not appeared.

Facts are read-only observations. **Ordering State** identifies **Stale** or
**Ambiguous** source ordering when an incoming observation cannot safely replace
current values. Review the provider record and delivery details before acting
on those observations.

To stop future GitHub deliveries, archive the repository. Existing deliveries
and facts remain, and already queued work can still be processed.

## Historical environment merges

Open the task **Git Merge Evidence** tab. **Merge observed in** shows the
configured environments with at least one linked, known merged PR targeting
their exact branch. **Observed merged PRs** opens those PR records, including
provider links and retained provenance. The details identify the repository,
branch, PR, merge time, source time, last-seen time and confidence.

One merged PR is partial task progress even if another is open, uncertain or
in another repository. No links are unknown; no visible active mapping is
unconfigured. A merge is historical evidence, not a deployment, current code
presence or proof that all work for the task has arrived. Reverts, reapplications,
cherry-picks, promotions, branch deletion, force-push and renames do not infer
current presence or absence. A head SHA is not a merge SHA.

In Tasks search, select **UAT merge observed; no production merge observed
(visible evidence)** and choose the exact UAT environment. Typing a name matches
the whole name, ignoring case, not a substring such as Pre-UAT. The filter
requires a visible active production mapping in the same Project and excludes
a task with any qualifying visible production merge, even from a different PR.
A missing or uncertain production observation can leave a task included as
unknown, never as proof that its code is absent. Results follow your current
Task, Project, environment, repository, mapping, association and PR access.

Only **Known** ordering can establish a positive. **Stale** and **Ambiguous**
remain uncertain until a strictly newer unambiguous observation arrives. This
conservative rule can hide a genuine merge after an otherwise harmless late
event. Delayed, failed, digest-only or prematurely purged deliveries are not
backfilled by inference. Purging an already processed payload leaves normalized
merge facts readable.

The separate manual **Environments** panel remains authoritative for BA
Configuration and Data import status. Git evidence never updates those lines,
their actor/time/history, stages or task completion.
