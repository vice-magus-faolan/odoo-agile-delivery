Install **Agile Solution Definition** (`project_agile_solution`). Follow
[role assignment in Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_agile#configuration)
to assign Business analyst for authoring requirements, documents, revisions and
Task previews, or combine it with Scrum master for Sprint operations.

Authors need an active internal account, current Project visibility, write
access to the solution records, and membership in the Project company. Project users can
read permitted content and preview reports. Native Project visibility and
record rules continue to apply. A Business analyst cannot approve documents,
return reviews, record acceptance or manage shared narrative templates.
A Project administrator retains authoring capabilities and may return an
in-review document with a reason, whether or not they are its designated
approver. Authorship alone never permits returning a review, including your own;
self-return requires Project administrator access. Current Project, record and
company access still apply. Only the designated approver may approve.

1. Follow the [Agile core configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_agile#configuration)
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

For client sign-off, invite the exact portal contact with native Project sharing
in read mode. A commercially related contact is not automatically a signer.
As a Project administrator, set **Client Signer** on the Solution Document to the
active portal user. The contact must belong to the Project company. Designation
alone discloses nothing; issue each customer-facing revision explicitly.
