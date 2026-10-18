1. Configure an Agile-enabled Project using the
   [Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile#configuration).
2. As a Project administrator, open Project **Configuration > Agile Teams**.
   Create a team and select its Project. The team inherits the Project company;
   it does not grant users Project access.
3. Open Project **Configuration > Agile Item Types** and review **Can Schedule In
   Sprint** for each type. It defaults to enabled. Disable it before scheduling
   tasks of a type you want to keep outside Sprints; a type in use by scheduled
   tasks cannot be made ineligible.
4. Open Project **Tasks > Sprints**. Create a Sprint with a name, Project and
   **Team**, then set **Date Start**, **Date End** and **Goal**. The end date cannot
   precede the start date. Save in **Draft** before assigning work.

Project users can read teams, Sprints and scope history within their Project and
company access. Project administrators manage teams and Sprints and use assignment
and close wizards. Editing a task Sprint field uses task write permissions.
