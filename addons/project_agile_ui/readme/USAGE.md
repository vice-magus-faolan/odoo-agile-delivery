1. Open **Project > Projects**, open the Project form and choose **Sprint
   Planning**. The board shows visible Draft and Active Sprints with active teams.
2. Find work in **Product Backlog**. This queue includes active, unscheduled
   tasks whose item type permits Sprint scheduling, excluding templates.
   Typeless, Done and Canceled tasks are not eligible. Choose **Agile Team** to
   filter the backlog and Sprints, or **All teams** to include unteamed work.
   Changing teams starts from the first page. Use **Load more backlog items** for
   additional work from the same team.
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
   The latter keeps the selected team and the same open, unscheduled queue.

The board displays at most 20 Sprints and 100 assigned items across them, with
50 backlog items per page. Use the standard lists when the board is incomplete;
point totals can include work not rendered in its limited item list.
The team selector lists up to 100 active teams for this Project; use native task
search for other teams. Assignment inherits a Sprint team only for unteamed work;
an incompatible team selection is refused without moving any work.

After a rejected change, the board refreshes. Review current placement before
retrying. If a page load fails, **Retry** requests that page again; a changed
backlog reloads the first page. If a stale-data warning appears, reload the page or reopen Sprint Planning
before making another change. If access is denied, check the selected companies
and ask a Project administrator to check your access. The ordinary lists still
require the same permissions.

For task completion, follow [Start and work in the Scrum guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum#start-and-work).
