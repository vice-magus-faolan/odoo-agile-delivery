## Build and approve a specification

Use a Business analyst or Project administrator account with the Project access
described in Configuration. The following example starts with a Solution Specification / Internal Brief.

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
   but is still unapproved. The designated Project administrator approver chooses **Approve Exact
   Revision**. To edit a review, use **Return with Reason**, enter **Reason** and
   **Confirm**. Requirement and context content already sealed by a reference
   stays sealed; revise it through its stable identity instead.
6. For later changes, open the approved revision and choose **New Working
   Revision**. Create successor requirement and context revisions as needed and
   select them in the new draft. Approving the successor marks the previous
   baseline **Superseded** and preserves its content and decisions.

## Discuss stable records

Project users with access to a requirement, Solution document or supporting
context can use **Send message**, mentions and **Follow** on its identity form.
Open **Project > Requirements**, **Solution Documents** or **Solution Supporting
Context**, rather than the numbered revision list. The conversation stays with
the identity when a new revision is created. Messages do not change sealed
content or approve scope.

A question owner follows its stable context when assigned or changed on the
working revision. Previous owners remain followers until they unfollow; their
existing subscription preferences are preserved. Following and mentioning do
not grant Project or company access. Notifications go only to active internal
users who can currently read the source; external contacts and raw email
recipients do not receive these discussions. Customer publications remain a
separate workflow.

## Link delivery work

As a Business analyst or Project administrator with write access to the affected
tasks, open
**Project > Deliberate Task Previews**. Create a preview with **Solution**,
**Operation** (**Link Existing Native Task** or **Create Native Task**), **Name**, and one to
twenty exact **Requirement Revisions**. Select **Task** for existing work; for
new work, select **Agile Item Type** and optionally **Description**. An optional
**Document Revision** must contain the selected exact requirements.

For new work, **Copy Acceptance Expectations** starts unchecked. Check it to
copy the selected exact requirements into task acceptance criteria. Inspect
**Task Acceptance Criteria Preview** before saving and again in confirmation;
the created criteria match that preview and remain editable on the task.
Leave it unchecked to create work without copying requirement criteria.
This option does not update existing tasks when linking them. To change a saved
preview or its copy choice, create a fresh preview.

Save, choose **Review and Confirm**, inspect the proposed work, then choose
**Confirm This Preview** as the same user. Work is created or linked only when
you confirm the preview. Changed source content requires a fresh preview;
confirming an already consumed preview returns its existing task rather than
creating another. Inspect links under **Project > Requirement Work Links**. Use **Retire Working
Link** with a reason when replacing coverage, then link the successor.

Manage task descriptions, criteria, estimates, workflow and Sprint allocation
on the tasks themselves. Specification changes preserve these task values. For a task
without requirements, enter its explanation on the **Solution Maintenance** tab.

On the task **Agile** tab, **Exact Requirement Acceptance** shows each accessible
active link: the exact title and revision, **Acceptance Expectations** and
**Verification Method**, read-only. A newer revision does not replace the linked
one. Retired links disappear. Inaccessible requirements are omitted without
preventing task access; this panel is not proof of complete requirement coverage.

For example, a client needs warehouse staff to dispatch only buyer-approved orders.
Their requirement expectations might say:

- Given an order awaiting the buyer approval, when a warehouse clerk attempts to
  dispatch it, then dispatch is refused and the order stays awaiting approval.
- Given that buyer approval is recorded, when the clerk dispatches the order,
  then a dispatch reference is saved and shown to the buyer.

Use **Verification Method** to record a demonstration with buyer and warehouse test
accounts. Given/When/Then is optional wording, not an enforced format. A developer
may copy these expectations at creation and add task-specific edge cases later;
editing task criteria does not change the client-agreed requirement revision.

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

## Record internal proxy acceptance

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
Read the latest Internal proxy decision for each exact pair to determine its
proxy status. Authenticated client decisions have a separate channel and history.


## Share a revision and obtain client decisions

After internal approval, a Project administrator opens the exact revision and
chooses **Preview / Share with Client**. Select the invited portal user and review
the complete customer disclosure, including its labels. Choose **Issue Customer
Publication**. Only customer-tagged narrative, requirements and permitted context
are disclosed; requirement rationale and internal history stay private.

The client opens **My Account > Solution documents**, selects the issued revision
and uses **Approve document** or **Reject document**. For each disclosed requirement
in a specification, enter **Evaluated criteria** and **Evidence**, then choose
**Accept requirement** or **Reject requirement**. The page shows the authenticated
client and server time. Decisions concern only these disclosed bytes. Internal
approval remains separate, including when the client rejects the document.

Reload before correcting an existing decision. Corrections append history rather
than edit it. A superseded publication is read-only; a successor requires a new
publication and new decisions. **Download HTML** contains the same customer-facing
content, not the internal report.

To remove access, open the publication from its Solution Document and choose
**Revoke Publication**. Removing the exact Project invitation or changing the
client identity, company access or signer also retires affected publications.
Restoring access does not reactivate them; issue a new publication. Downloaded
copies cannot be recalled.

## Name the people served

As a Business analyst or Project administrator with task write access, open the
task **Agile** tab and select **Actors** under **People Served**. First create
the named supporting context with **Kind** set to **Actor** in a Solution of
that same Project. You may select several Actors from Solutions in that Project.
The native board and Product Backlog show their names; empty selections stay
blank. Actors describe people served, not access grants or frozen acceptance.
Renaming the stable Actor updates its displayed name, not requirement history.
An Agile member can duplicate a task and its subtasks in the same Project while
retaining their Actors; this does not grant permission to select other Actors.
Archived Actors remain on historical work but cannot be newly selected. A copy
to another Project or a whole-Project/template copy starts without source-Project
Actors.
