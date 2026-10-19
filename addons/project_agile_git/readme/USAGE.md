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

To stop future GitHub ingress, archive the repository. Existing deliveries and
facts remain, and already queued work can still be processed.
