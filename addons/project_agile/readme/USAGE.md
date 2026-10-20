Create tasks in the configured Project. Set **Agile Item Type**. For point-using
types, set **Story Points** under the Project estimation policy. Configuration
and Data import use native **Allocated Time** in hours instead. Enter
**Acceptance Criteria** on the **Agile** tab. The generated **Agile Key**
is read-only. Use native subtasks for hierarchy and dependencies for blocking
relationships. Agile parent and child tasks must belong to the same Project and
follow the parent type policy.

Open Project **Tasks > Product Backlog** and prioritize tasks with the list drag
handle (**Agile Backlog Sequence**). Filter by Project when managing several Agile
Projects. This backlog includes all Agile item types, not only unscheduled work.
Task search provides **Agile Work**, **Agile Item Type** and **Agile Project** filters
or groupings.

For Sprint planning, configure
[project_scrum](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum).
The **Product Backlog** button on a Sprint shows only its Project unscheduled,
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
