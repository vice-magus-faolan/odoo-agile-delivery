1. Open **Project > Projects**, open the Project form and choose **Sprint
   Planning**. The board shows visible Draft and Active Sprints with active teams.
2. Find work in **Product Backlog**. This queue includes active, unscheduled
   tasks whose item type permits Sprint scheduling, excluding templates.
   Typeless tasks are not eligible. It does not filter out Done or Canceled tasks,
   so check task state before scheduling (known limitation
   [#46](https://github.com/vice-magus-faolan/odoo-agile-delivery/issues/46)). Use **Load more backlog items** for
   additional work.
3. Choose a **Draft Sprint**, then **Assign to Sprint**. Alternatively, drag the
   item onto a Draft Sprint. The board does not assign to Active Sprints; use
   the [Scrum workflow](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum#usage)
   for the supported native assignment paths.
4. Choose **Return to Product Backlog** on an assigned item to remove it from a
   Draft or Active Sprint. Removal from an Active Sprint records scope history.
   Use **Move earlier** and **Move later**, or drag within the backlog, to
   prioritize work. Buttons provide the same actions without dragging.
5. Choose a Sprint name or backlog task key to open its form. **Open Sprints
   list** and **Open Product Backlog list** offer ordinary list and form views.
   The latter uses this workspace queue, not the broader Agile core backlog.

The board displays at most 20 Sprints and 100 assigned items across them, with
50 backlog items per page. Use the standard lists when the board is incomplete;
point totals can include work not rendered in its limited item list.

After a rejected change, the board refreshes. Review current placement before
retrying. If a page load fails, **Retry** requests that page again; a changed
backlog reloads the first page. If a stale-data warning appears, reload the page or reopen Sprint Planning
before making another change. If access is denied, check the selected companies
and ask a Project administrator to check your access. The ordinary lists still
require the same permissions.

For task completion, follow [Start and work in the Scrum guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum#start-and-work).
