## Plan a draft Sprint

As a Scrum master or Project administrator, open Project **Tasks > Sprints** and select the Draft
Sprint. Choose **Product Backlog** to see its Project unscheduled tasks whose
**Agile Item Type** allows Sprint scheduling. Typeless tasks are not eligible.
Create and estimate work, then prioritize it with the backlog list handle.

Select tasks from one Project and use **Actions > Assign to Sprint**. Select the
Draft Sprint and choose **Apply**. The wizard also accepts Active Sprints and
records added scope. Alternatively, users with task write access can edit the
**Sprint** field. Tasks can join only a Draft or Active Sprint in their own Project
and company.

Set **Agile Team** on a task to separate BA and development work within one
Project. Leave it empty when ownership is not yet known. Assignment gives an
unteamed task the Sprint's team; work already owned by another team is refused.
When assigning a selection, either every task moves or none does. Returning work
to Product Backlog keeps its team. Filter or group the backlog by **Agile Team**.

As a Scrum master or Project administrator, choose **Sprint Backlog** to review assigned work.
When the Project uses milestones, this task list shows **Milestone** and supports
native milestone search and grouping. Active Sprint cards show the milestone.
Use the milestone's **Release contents** to inspect work across
Sprints, including completed tasks; a release is not limited to the current Sprint.
Select tasks and use **Actions > Remove from Sprint**, then **Apply**, to return
work to the backlog. Project **Tasks > Product Backlog** shows all open,
unscheduled work, including unschedulable item types and tasks without an item type.
The Sprint button and Sprint Planning board show only Sprint-eligible work.
Done, Canceled, archived and template tasks stay out of both backlog queues.

## Start and work

Open Project **Tasks > Active Sprint** for current work grouped by stage.
Use **Agile Team** in search to focus on your team. The **Active Sprint** search
filter excludes Draft and Closed Sprints; **Sprint Backlog** still includes history.

As a Scrum master or Project administrator, choose **Start Sprint**. Close any Active Sprint for
the same Project/team first. Starting freezes the committed task set and records
**Committed** events. Tasks already in **Done** state also receive **Completed** events.

To complete a task, set its state to **Done**. Merely moving it to a stage named
Done does not change its state.

In an Active Sprint, membership changes record **Added** or **Removed** events;
estimate changes record **Reestimated** with previous and new points. Moving into
**Done** records **Completed**; moving out records **Reopened**.
Unchanged writes do not add events.

## Close and read history

As a Scrum master or Project administrator, choose **Close Sprint**. When the close wizard opens,
choose **Move to Product Backlog** or **Move to Draft Sprint**, then **Close Sprint**.
A carry-over target must be a different Draft Sprint for the same Project, company
and team. Closing requires edit access to every unfinished task, including archived
tasks. Canceled tasks also count as unfinished.

Closing moves all unfinished work or none and records **Carried to Product Backlog**
or **Carried to Draft Sprint** events. Completed work stays on the closed Sprint.
With no unfinished work, closing is direct.

Open **Scope History** on the Sprint to read immutable events with task, observed
points, actor, time and an optional carry-over target column. Closed Sprint
assignments are frozen; later task state or estimate changes do not rewrite history.
There is no reopen action.
