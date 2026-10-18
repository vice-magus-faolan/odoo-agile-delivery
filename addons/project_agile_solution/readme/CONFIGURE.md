Install **Agile Solution Definition** (`project_agile_solution`). Before creating
or editing solution content, use an active internal account with Project
**Administrator** access (the Project Manager group), write access to the Project
and solution records, and membership in the Project company. Project users can
read permitted content and preview reports; the manager role does not bypass
Project visibility or record rules.

1. Follow the [Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile#configuration)
   to enable **Agile Enabled** on the Project and set its **Agile Key**.
2. Open **Project > Solution Lineages**. Create a named initiative and select its
   active Agile **Project**. A lineage groups documents and requirements; saving
   it does not approve any content.
3. Open **Project > Solution Documents**. Create a document with the same
   **Solution**, a **Name**, and **Kind**: **Solution Specification / Internal
   Brief** or **Statement of Work**. Set **Approver** to an active internal
   Project Manager who can access and edit the Project and document. Only that
   designated user can approve its exact revision.

An internal initiative needs no Statement of Work (SOW). If the solution has a
SOW document, separately approve its current baseline and select it in the
specification before approving the specification. Neither approval is a legal
signature or automatic requirement acceptance.
