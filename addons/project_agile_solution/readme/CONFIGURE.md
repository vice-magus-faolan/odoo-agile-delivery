Install **Agile Solution Definition** (`project_agile_solution`). Before creating
or editing solution content, use an active internal account with
**Administrator** as its Project access level. A Project administrator also needs
write access to the Project and solution records, and membership in the Project
company. Project users can read permitted content and preview reports. Project visibility and record rules apply to both roles.

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
