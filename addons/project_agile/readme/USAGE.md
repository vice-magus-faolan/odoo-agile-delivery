Create tasks in the configured Project. On the task form, set **Agile Item Type**
and **Story Points**, and enter **Acceptance Criteria** on the **Agile** tab.
The generated **Agile Key** is read-only. Use native subtasks for hierarchy and
native dependencies for blocking relationships. Agile parent and child tasks must
belong to the same Project and follow the parent type's allowed-child policy.

Open **Product Backlog** in Project to prioritize Agile tasks using the list drag
handle (**Agile Backlog Sequence**). Filter by Project when working across several
Agile Projects. The core backlog includes Agile work regardless of type; it is not
an unscheduled-Sprint queue. Task search also exposes **Agile Work** and grouping by
**Agile Item Type** or **Agile Project**. Ordinary Project views remain available.

For Sprint planning, install and configure
[project_scrum](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_scrum).
Its Sprint-specific **Product Backlog** shows only unscheduled, Sprint-eligible
work for that Sprint's Project.
