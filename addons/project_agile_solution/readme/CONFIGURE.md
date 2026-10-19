Install **Agile Solution Definition** (`project_agile_solution`). As a Settings
administrator, open an existing internal user in
**Settings > Users & Companies > Users**. On **Access Rights**, in **Services**,
select **Business analyst** in **Agile Solution** before the user creates or
edits requirements, documents,
revisions and Task previews. It includes **Agile member**, not Administrator.
For someone who also runs Sprints, select **Scrum master** separately in
**Agile Scrum** and save. Keep any already authorized **Project** access.

Authors need an active internal account, current Project visibility, write
access to the solution records, and membership in the Project company. Project users can
read permitted content and preview reports. Native Project visibility and
record rules continue to apply. A Business analyst cannot approve documents,
record acceptance or manage shared narrative templates. Assign **Administrator**
under **Project** to the approver; a Project administrator retains authoring
capabilities as well.

1. Follow the [Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile#configuration)
   to enable **Agile Enabled** on the Project and set its **Agile Key**.
2. Open **Project > Solution Lineages**. Create a named initiative and select its
   active Agile **Project**. A lineage groups documents and requirements. Approve
   its document baselines separately using the workflow below.
3. Open **Project > Solution Documents**. Create a document with the same
   **Solution**, a **Name**, and **Kind**: **Solution Specification / Internal
   Brief** or **Statement of Work**. Set **Approver** to an active internal
   Project administrator who can access and edit the Project and document. Only
   that designated user can approve its exact revision.

For an internal initiative, a Statement of Work (SOW) is optional. If the solution
has a SOW document, separately approve its current baseline and select it in the
specification before approving the specification. Record requirement acceptance
separately through Exact Requirement Decisions.
