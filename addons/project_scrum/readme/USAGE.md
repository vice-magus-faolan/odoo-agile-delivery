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

As a Scrum master or Project administrator, choose **Sprint Backlog** to review assigned work.
Select tasks and use **Actions > Remove from Sprint**, then **Apply**, to return
work to the backlog. Project **Tasks > Product Backlog** is the Agile core backlog,
not the Sprint-specific unscheduled queue.

## Start and work

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
