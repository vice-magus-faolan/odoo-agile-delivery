## Plan a draft Sprint

Open the Sprint and choose **Product Backlog**. This action is scoped to its Project
and shows only unscheduled tasks whose **Agile Item Type** permits Sprint scheduling.
Typeless tasks are not eligible. Create work in the Agile Project, set its item type,
acceptance criteria and estimate, then prioritize with the backlog list handle.

As a Project administrator, select unscheduled tasks from one Project and use
**Actions > Assign to Sprint**. Select the Draft Sprint and choose **Apply**.
The ordinary assignment wizard also accepts Active Sprints, recording added scope.
Alternatively, edit a task's **Sprint** field subject to normal task write access.
Tasks can join only a Draft or Active Sprint in their own Project and company.

Choose **Sprint Backlog** on the Sprint to review assigned work. To return selected
assigned tasks, use **Actions > Remove from Sprint** and **Apply**. The general
Project **Product Backlog** menu is the Agile core backlog, not this Sprint-scoped
unscheduled queue.

## Start and work

Choose **Start Sprint** on the Draft Sprint as a Project administrator. Another
Active Sprint for the same Project/team must be closed first. Starting freezes the
original committed task set and records **Committed** scope events. Tasks already
in native **Done** state also receive completion evidence.

During the Active Sprint, assignment changes record **Added** or **Removed** events;
changed estimates record **Reestimated** with the previous and new story points.
Moving a task into native **Done** (`1_done`) records **Completed**; moving out records
**Reopened**. A stage name alone is not the native Done state. Repeated unchanged
writes do not add completion events.

## Close and read history

Choose **Close Sprint** as a Project administrator. If unfinished tasks remain,
choose **Move to Product Backlog** or **Move to Draft Sprint** in the wizard, then
confirm **Close Sprint**. A carry-over target must be a different Draft Sprint for
the same Project, company and team. Every task not in native Done state counts as
unfinished, including canceled tasks. Closing checks the whole unfinished selection,
including archived tasks; hidden or unwritable work must not be silently omitted.

The close records **Carried to Product Backlog** or **Carried to Draft Sprint**
evidence and moves unfinished work atomically. Completed work stays assigned to the
closed Sprint. With no unfinished work, the action closes directly.

Read **Scope History** on the Sprint for task-level events, observed points, actor,
time and carry-over target (an optional list column). This ledger preserves original
commitment and subsequent changes rather than reconstructing the past from current
task membership. It is read-only in ordinary workflow. Closed Sprint records and
assignments are frozen for ordinary users; later native task state/estimate changes
do not rewrite the closed scope ledger. There is no ordinary reopen action.
