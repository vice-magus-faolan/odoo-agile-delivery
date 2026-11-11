1. As a Project administrator, use **Project > Solutions > Task Previews** to link
   exact requirement revisions to the Project tasks you plan to schedule. Follow the
   [Solution workflow](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_agile_solution#usage)
   to review and confirm those links.
2. Plan work using **Project > Tasks > Sprints** and the
   [Scrum workflow](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_scrum#usage).
   **Start Sprint** records commitment; adding work to an active Sprint records
   added scope. Each new scope event captures the active exact requirement links
   visible at that event, including an optional document revision and its observed
   approval state.
3. Open the Sprint **Scope History** tab. Read **Solution Capture Status**:
   **Exact Context Captured**, **No Active Requirement Links**, or
   **Not Available / Predates Bridge**. Choose the event row button **Exact
   Requirements**, then open a context row to inspect **Frozen Observed Content
   and Approval State**.

Each event keeps its own observed context, including removal, **Completed**,
reopening and carry-over events. An earlier commitment retains requirement v1
when a later link selects v2. Draft specification context can be captured and is
still unapproved. Approve the specification through the Solution workflow and
record acceptance through **Project > Solutions > Exact Requirement Decisions** under the
Solution acceptance rules.

**No Active Requirement Links** means the event was captured without links;
**Not Available / Predates Bridge** means there is no bridge record for that
event; the work may still have had requirement links at the time. Installation
preserves old events as they are. Captured rows are
read-only and retain their original snapshot. Losing access to required
references can hide history or prevent capture. Continue to manage Sprint state,
assignment and points through the native Scrum workflow.