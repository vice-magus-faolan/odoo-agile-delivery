Follow [role assignment in Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_agile#configuration)
to assign Scrum master before managing teams or Sprints, or combine it with
Business analyst for Solution authoring. A Project administrator can also
perform Scrum operations. Neither role grants access to a Project or company
by itself.

1. Have a Project administrator configure an Agile-enabled Project using the
   [Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_agile#configuration).
2. As a Scrum master, open **Project > Tasks > Agile Teams**. Create a team and select
   its Project. The team inherits the Project company.
3. Have a Project administrator open **Project > Configuration > Agile Item Types**
   and review **Can Schedule In Sprint**. It defaults to enabled. Disable it
   before scheduling tasks of a type that should stay outside Sprints. A type
   used by scheduled tasks cannot be made ineligible.
4. As a Scrum master, open **Project > Tasks > Sprints**. Create a Sprint with a
   name, Project and **Team**, then set **Date Start**, **Date End** and **Goal**.
   The end date cannot precede the start date. Save in **Draft** before assigning work.

Project users and Agile members can read permitted teams, Sprints and scope
history. They can place their editable tasks through the assignment wizard or
Sprint field. Starting and closing Sprints requires Scrum master or Project
administrator access, with current access to the affected Project and work.
