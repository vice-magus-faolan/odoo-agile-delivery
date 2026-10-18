1. Configure an Agile-enabled Project, key, default item type and estimation method
   using the [Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile#configuration).
2. As a Project administrator (`project.group_project_manager`), open Project
   **Configuration > Agile Teams**. Create a named team and select that Project.
   The team belongs to one Project and inherits its company; it is not a separate
   user-membership or permission configuration.
3. In **Configuration > Agile Item Types**, open each type you plan to schedule and
   review **Can Schedule In Sprint**. The field defaults to enabled. Disable it for
   types you want to keep outside Sprints, before assigning tasks of those types.
   A type already used by a scheduled task cannot be made ineligible.
4. Open **Sprints** in Project and create a Sprint with a name, the same Project and
   its **Team**. Set **Date Start**, **Date End** and a **Goal**. The end date cannot
   precede the start date. Save it in **Draft** before assigning work.

Project users can read teams, Sprints and scope history within their permitted
company/Project visibility. Project administrators manage teams/Sprints and use the
assignment/close wizards; they also need access to all affected tasks. Task edits
retain native Project access checks. A team does not itself grant Project access.
