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

Switching to hours preserves previous story points without converting them to hours.
They contribute zero current planning points; existing Sprint history is unchanged.
Switching back validates the retained estimate. In an active Sprint, task type changes
record reestimation. Change active work individually before changing its shared
item-type estimation policy.
