Follow the [Scrum setup guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_scrum#configuration)
for Project configuration, team and Sprint setup, and the roles required for
Sprint lifecycle actions. Create an active team and save a Draft Sprint before
planning work.

Project users can open the workspace for a visible, active Agile Project that is
not a template. Changing work requires write access to the affected tasks;
Sprint setup and lifecycle permissions follow the Scrum guide linked above.

## Advisory WIP limits

WIP warnings are off by default. As a Project administrator, open the Project form
and choose **Advisory WIP**. Enable **Advisory WIP Limits**. Add a Project stage
and a positive **Advisory Limit** to **Stage WIP Limits**, then save.
Configure each stage once per Project. Stages without a row have no limit.
A shared stage can have different limits in different Projects.

Open **Active Sprint board** to see the warnings. Limits are advisory, not
hard caps: even an already-overfull stage remains editable. Lowering a limit does
not move or reject existing work. Disabling warnings retains the configured rows.
Project copies start with warnings off and no copied limits.
