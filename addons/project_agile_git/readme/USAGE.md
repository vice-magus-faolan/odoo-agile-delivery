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

The task **Git Merge Evidence** tab shows one line per configured environment:
linked PRs with **Known** ordering merged into its exact mapped branch, or no
merge seen. It is hidden without visible active mappings. **Observed merged
PRs** opens source details. In Tasks search, **Merged into, not Production**
finds tasks with a merge into the selected environment but none into any visible
production mapping in that Project; a production mapping is required. Typed
names match the whole name, ignoring case, so UAT does not match Pre-UAT.
The tab and filter follow your access rights; the BA's manual **Environments**
panel stays separate.

A merge is not a deployment or proof that all task code is present. Only PRs
linked by task keys in their title, body or head branch count: put promoted
task keys in the release PR body when merging UAT into Production. The GitHub
connector considers the first 100 distinct body keys and records an overflow
audit beyond that limit. Split larger releases across PRs to retain all links;
see the GitHub connector guide for key eligibility and other source limits.
A late source event can hide a merge until a strictly newer, unambiguous event
arrives; no merge seen does not prove absence.
