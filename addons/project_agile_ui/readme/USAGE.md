1. Open **Project > Projects**, open the Project form and choose **Sprint
   Planning**. The board shows visible Draft and Active Sprints with active teams.
2. Find work in the board's **Product Backlog**. This queue includes active, unscheduled
   tasks whose item type permits Sprint scheduling, excluding templates.
   Typeless, Done and Canceled tasks are not eligible. Choose **Agile Team** to
   filter the backlog and Sprints, or **All teams** to include unteamed work.
   Changing teams starts from the first page. Use **Load more backlog items** for
   additional work from the same team.
   Project **Tasks > Product Backlog** is the general queue: it also includes
   unschedulable item types and tasks without an item type, which cannot be assigned
   to a Sprint.
3. Choose a **Draft Sprint**, then **Assign to Sprint**. Alternatively, drag the
   item onto a Draft Sprint. The board does not assign to Active Sprints; use
   the [Scrum workflow](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_scrum#usage)
   for the supported native assignment paths.
4. Choose **Return to Product Backlog** on an assigned item to remove it from a
   Draft or Active Sprint. Removal from an Active Sprint records scope history.
   Use **Move earlier** and **Move later**, or drag within the backlog, to
   prioritize work. Buttons provide the same actions without dragging.
5. Choose a Sprint name or backlog task key to open its form. **Open Sprints
   list** and **Open Product Backlog list** offer ordinary list and form views.
   The latter keeps the selected team and the board's Sprint-eligible queue.

Use **Next Sprints** to reach Sprints beyond the current 20-Sprint page.
Use **Next assigned items** to reach work beyond the current 100-card page across
those Sprints, including a single Sprint with more than 100 items. Each Sprint
shows how many of its visible, filtered items are on the current page and its
complete count. An empty column on one page does not mean the Sprint is empty.
**First Sprints** and **First assigned items** return to the beginning.
The team selector shows up to 100 active teams at a time; choose **Next teams**
to reach more, or **First teams** to start again. The selected team remains available.
These controls replace the current window; backlog paging still adds 50 items at
a time. Sprints are ordered by state and descending identity, teams by identity,
and assigned items by backlog sequence then identity.
Assignment inherits a Sprint team only for unteamed work;
an incompatible team selection is refused without moving any work.

For a Project using native milestones, choose **Milestone** to filter both backlog
and Sprint cards. Type a name and select a suggestion or press Enter. Clearing the
field restores all milestones. Changing milestones restarts backlog paging and
keeps the selected team. **Group loaded items by milestone** groups only the cards
already loaded, not the complete release. Sprint counts and current points use the
selected milestone and caller-visible active assigned work. Commitment points
show committed events for that same currently assigned, visible task scope;
use native Sprint history for the complete historical commitment.
Clear the milestone filter and grouping to reorder work; assignment and return
remain available. **Open Product Backlog list** keeps the milestone and team.
Choose **Release contents** for the selected milestone's full native task list,
grouped by item type and task state, including completed and scheduled work.
Milestone controls and badges are absent when the Project disables milestones.

After a rejected change, the board refreshes. Review current placement before
retrying. If a page load fails, **Retry** requests that page again; a changed
planning page reloads the first page. If a stale-data warning appears, reload the page or reopen Sprint Planning
before making another change. If access is denied, check the selected companies
and ask a Project administrator to check your access. The ordinary lists still
require the same permissions.

For task completion, follow [Start and work in the Scrum guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_scrum#start-and-work).
