## Build and approve a specification

Use the Project administrator account and Project access described in
Configuration. The following example starts with a Solution Specification / Internal Brief.

1. In **Project > Requirements**, create a requirement with **Name** and
   **Solution**. Save, then choose **Open / New Content Revision**. Fill **Title**,
   **Requirement Type** (Functional or Nonfunctional), **Priority**, **Audience**,
   **Description**, **Rationale**, **Verification Method**, and **Acceptance
   Expectations**. Save the exact content revision. Link it to delivery work
   using the task preview workflow below.
2. In **Project > Solution Documents**, open your document and choose
   **Open / New Working Revision**. Edit **Title** and add sections under
   **Ordered Narrative**, including their **Audience** and **Body**. Alternatively,
   **Copy Template Sections** lets you select a starting template and **Confirm**
   the copy. Later template changes do not update the copied sections.
3. Under **Exact Requirements**, select the requirement revision you just saved.
   Under **Exact Supporting Context**, optionally select content prepared through
   **Project > Solution Supporting Context** and **Open / New Context Revision**.
   Questions can name an owner, planning significance and existing Spike tasks.
   Approve any additional scope through a successor document baseline.
4. If a SOW exists, set **Based Sow Revision** to its currently approved revision.
   Use **Scope Disposition** and **Scope Change Reason** to describe an explicit
   change. Expanded specification scope needs a separately approved successor
   SOW marked **Explicit Scope Change**.
5. Save and choose **Submit for Review**. The content is frozen **In Review**,
   but is still unapproved. The designated approver chooses **Approve Exact
   Revision**. To edit a review, use **Return with Reason**, enter **Reason** and
   **Confirm**. Requirement and context content already sealed by a reference
   stays sealed; revise it through its stable identity instead.
6. For later changes, open the approved revision and choose **New Working
   Revision**. Create successor requirement and context revisions as needed and
   select them in the new draft. Approving the successor marks the previous
   baseline **Superseded** and preserves its content and decisions.

## Link delivery work

As a Project administrator with write access to the affected tasks, open
**Project > Deliberate Task Previews**. Create a preview with **Solution**,
**Operation** (**Link Existing Native Task** or **Create Native Task**), **Name**, and one to
twenty exact **Requirement Revisions**. Select **Task** for existing work; for
new work, select **Agile Item Type** and optionally **Description**. An optional
**Document Revision** must contain the selected exact requirements.

Save, choose **Review and Confirm**, inspect the proposed work, then choose
**Confirm This Preview** as the same user. Work is created or linked only when
you confirm the preview. Changed source content requires a fresh preview;
confirming an already consumed preview returns its existing task rather than
creating another. Inspect links under **Project > Requirement Work Links**. Use **Retire Working
Link** with a reason when replacing coverage, then link the successor.

Manage task descriptions, criteria, estimates, workflow and Sprint allocation
on the tasks themselves. Specification changes preserve these task values. For a task
without requirements, enter its explanation on the **Solution Maintenance** tab.

## Preview the chosen audience

1. Open the exact document revision through **Project > Solution Revisions**
   and choose **Preview / Coverage**. Project users need current access to the
   revision and every required reference, including archived references.
2. Select **Internal** or **Redacted Customer**. For internal change comparison,
   select an approved or superseded **Baseline** of the same document. Read
   **Honest Coverage / Change Impact** for missing links, older revisions,
   unresolved questions and explicit decisions.
3. Choose **Render Selected Audience** for HTML output. Draft and review output
   remains unapproved; approved or superseded output uses that exact frozen
   baseline.

Redacted customer output includes only customer-tagged narrative, requirements
and section, domain and deliverable context. Questions, decisions, actors and
acceptance evidence are excluded even when tagged customer. Narrative is rendered
as plain text. Review exported files before sharing them with customers. Keep
internal report URLs private.

Rendering requires access to every required reference. If rendering is refused,
ask your Project administrator to check access. Internal coverage accepts up to
1,000 rows; split larger initiatives into smaller ones.

## Record exact acceptance

Only the active internal Project administrator who actually approved the selected
specification baseline may record its decisions, with current Project, record
and company access. Changing the document Approver does not transfer that past
authority.

1. Open **Project > Exact Requirement Decisions** and create a record.
2. Select **Requirement Revision** and its currently approved specification
   **Document Revision**. The requirement must be included in that exact baseline.
3. Set **Decision** to **Accepted**, supply **Asserted Authority / Role**,
   **Criteria Evaluated**, and nonempty manual **Evidence**. Save. The recorder
   and UTC decision time are recorded automatically.

Record acceptance explicitly through this decision workflow. Evidence is free
text for your observations and references; Odoo does not open or check it.
Acceptance applies only to the exact requirement and baseline pair. Record a new
decision for a successor, even when it reuses the same content.

Saved decisions cannot be edited or deleted. Append **Rejected** or **Withdrawn**
with criteria and evidence to correct history; those corrections also allow a
superseded baseline. Withdrawal requires a currently accepted decision for the
same exact pair. The acceptance-events list filter shows the decision history.
Read the latest decision for each exact pair to determine its current accepted
status.
