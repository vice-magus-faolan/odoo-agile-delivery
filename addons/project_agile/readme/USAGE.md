Create tasks in the configured Project. Set **Agile Item Type**. For point-using
types, set **Story Points** under the Project estimation policy. Configuration
and Data import use native **Allocated Time** in hours instead. Enter
**Acceptance Criteria** on the **Agile** tab. The generated **Agile Key**
is read-only. Use native subtasks for hierarchy and dependencies for blocking
relationships. Agile parent and child tasks must belong to the same Project and
follow the parent type policy.

Task selectors show `[KEY] Task name` and accept a full key or key prefix.
An exact key match appears first, even when many keys share its prefix.
Enabling Agile assigns keys to existing non-template tasks, including archived
work, in creation order. Existing item types remain unchanged. If you cannot
update every eligible task, enablement is refused without changing the Project.
Upgrading assigns missing keys to existing work in already-enabled Agile Projects.
Moving unkeyed work into an Agile Project assigns a key and preserves its item
type. Untyped incoming work receives the Project's default unless you explicitly
choose a type or clear it. Assigned keys stay fixed;
copy keyed work instead of moving it to another Project.

Open Project **Tasks > Product Backlog** and prioritize tasks with the list drag
handle (**Agile Backlog Sequence**). Filter by Project when managing several Agile
Projects. The backlog contains open, active work, excluding Done, Canceled and
templates. With Scrum installed it includes only unscheduled work, including tasks
whose item type does not allow Sprint scheduling and tasks without an item type.
Task search provides **Agile Work**, **Agile Item Type** and **Agile Project** filters
or groupings.

For Projects using native **Milestones**, the backlog shows each task's milestone.
Use the native **Milestone** search field and grouping to focus on a release across
Projects. Agile does not turn milestones on. Open a milestone's **View Tasks** or
**Release contents** button to see its tasks grouped by Agile item type and task
state, including Done work. Projects without Agile keep the native View Tasks.

For Sprint planning, configure
[project_scrum](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum).
The **Product Backlog** button on a Sprint narrows this queue to its Project's
Sprint-eligible work.

On a Project kanban board, filter **Agile Item Type**, **Points work** or
**Hours work** to see matching tasks and applicable columns. Selecting several
types shows columns for any selected type, plus unrestricted columns (including
empty columns). With no type filter, ordinary native columns remain visible.
Changing a task type keeps a compatible stage or selects the first compatible
Project stage by sequence, then ID. If none exists, the task has no stage until
a compatible stage is configured. An incompatible drag or explicit stage is refused.

If you switch a type to hours, its tasks keep their story points but stop counting
toward Sprint totals. Enter hours separately in **Allocated Time**. Switching back to
points checks the saved estimate against the Project estimation method. In an active
Sprint, changing a task type records the point change; earlier history stays unchanged.
To change a shared type to hours while its tasks are in active Sprints, first change
those tasks to an hour-based type, or finish their Sprints.

For Configuration, Data import or another tracking type, open the task's **Agile**
tab. Set each environment row to **To do**, **Done** or **Verified** and save.
**Set by** and **Set on** show who last changed the line and when. Task write
permission is sufficient; configuring environments remains a Project administrator
operation. There is no required completion order: urgent Production work may be
marked Done before UAT. These are manual work statuses, not deployment evidence.

In task search, type UAT and press Enter on **Done in environment**, then type
Production and press Enter on **Not done in environment**. Type the whole name;
matching ignores case and spans clients. Production does not match Pre-Production;
type Pre-Production to search that environment. To search one client's environment,
select its indented suggestion instead.
Verified counts as done. **Waiting for Production** finds tasks done somewhere but not
done in any active environment flagged **Production** in that task's Project.
Projects without an active Production environment are excluded.
Both pending searches exclude missing lines on Done or Canceled tasks. Reopening a
task adds its missing environment lines. Existing To do lines remain pending and can
still be updated on closed tasks.
Select **Environment history** on the Agile tab to inspect all lines,
including archived environments; open a line to see its status changes in chatter.
Changing to a nontracking type or converting a task to a template hides active
lines without discarding history. Task copies start with fresh To do statuses.
