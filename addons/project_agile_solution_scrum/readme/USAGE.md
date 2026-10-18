1. As a Project Manager, use **Project > Deliberate Task Previews** to link exact
   requirement revisions to the Project tasks you plan to schedule. Follow the
   [Solution workflow](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile_solution#usage)
   to review and confirm those links.
2. Plan work using **Project > Tasks > Sprints** and the
   [Scrum workflow](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum#usage).
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
reopening and carry-over events. A later link to requirement v2 does not replace
v1 on an earlier commitment. Draft specification context can be captured and is
still unapproved; commitment is neither specification approval nor acceptance.
Task Done, a Completed event and PR merge do not record acceptance: use
**Project > Exact Requirement Decisions** under the Solution acceptance rules.

**No Active Requirement Links** means the event was captured without links;
**Not Available / Predates Bridge** is not proof that historical work had none.
Installation does not backfill old events from current links. Captured rows are
read-only and cannot be recaptured. Losing access to required references can hide
history or prevent capture; it must not produce apparently complete context.
The bridge does not change Sprint state, assignment, points or analytics formulas.
