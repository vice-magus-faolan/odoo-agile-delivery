## Build and approve a specification

Use a Business analyst or Project administrator account with the Project access
described in Configuration. The following example starts with a Solution Specification / Internal Brief.

1. In **Project > Solutions > Requirements**, create a requirement with **Name** and
   **Solution**. Save, then choose **Open or Create Content Revision**. Fill **Title**,
   **Requirement Type** (Functional or Nonfunctional), **Priority**, **Audience**,
   **Description**, **Rationale**, **Verification Method**, and **Acceptance
   Expectations**. Save the exact content revision. Link it to delivery work
   using the task preview workflow below.
2. In **Project > Solutions > Solution Documents**, open your document and choose
   **Open or Create Working Revision**. Edit **Title** and add sections under
   **Ordered Narrative**, including their **Audience** and **Body**. Alternatively,
   **Copy Template Sections** lets you select a starting template and **Confirm**
   the copy. Later template changes do not update the copied sections.
3. Under **Exact Requirements**, select the requirement revision you just saved.
   Under **Exact Supporting Context**, optionally select content prepared through
   **Project > Solutions > Solution Supporting Context** and **Open or Create Context Revision**.
   Questions can name an owner, planning significance and existing Spike tasks.
   Approve any additional scope through a successor document baseline.
4. If a SOW exists, set **SOW Baseline** to its currently approved revision.
   Use **Scope Disposition** and **Scope Change Reason** to describe an explicit
   change. Expanded specification scope needs a separately approved successor
   SOW marked **Explicit Scope Change**.
5. Save and choose **Submit for Review**. The content is frozen **In Review**,
   but is still unapproved. The designated Project administrator approver chooses **Approve Exact
   Revision**. To request edits, a Project administrator with current access uses
   **Return with Reason**, enters **Reason** and chooses **Confirm**. Business
   analysts can edit and resubmit the returned draft, but cannot return a review,
   including their own. Requirement and context content already sealed by a reference
   stays sealed; revise it through its stable identity instead.
6. For later changes, open the approved revision and choose **New Working
   Revision**. Create successor requirement and context revisions as needed and
   select them in the new draft. Approving the successor marks the previous
   baseline **Superseded** and preserves its content and decisions.

## Discuss stable records

Project users with access to a requirement, Solution document or supporting
context can use **Send message**, mentions and **Follow** on its identity form.
Open **Project > Solutions > Requirements**, **Solution Documents** or **Solution Supporting
Context**, rather than the numbered revision list. The conversation stays with
the identity when a new revision is created. Messages do not change sealed
content or approve scope.

With native incoming mail configured, an internal user who can currently read
that source can also reply by email to its existing conversation. Unknown,
external, inactive and no-longer-authorized senders cannot post to it. Email
replies use native sender resolution and remain on the same stable identity;
they do not create another requirement, document or question.

A question owner automatically follows its stable context when assigned on a
working revision only if they can currently read the source. Assignment does
not grant Project or company access. Granting access later does not itself add
a follower; assign the owner again or let them choose **Follow**. Manual followers
and previous owners remain subscribed with their existing subtype preferences.
An internal user who loses access can still remove only their own subscription
with native **Unfollow**; this does not reveal the source or let them remove
another follower.

Following and mentioning do not grant access. Notifications go only to active
internal users who can currently read the source; external contacts and raw
email recipients do not receive these discussions. Chatter files and scheduled
messages also require current source access, including after Project membership
is revoked. A file link or public flag does not share internal Solution content
with outsiders. Customer publications remain a separate workflow.

## Discuss customer requirements from shared work

Set the exact requirement revision to **Customer Projection** and deliberately
link it to the native Story or Task. Invite the client contact through native
Project sharing. The contact needs current access to both the Project and Task;
an invitation for another contact in the same customer company is insufficient.

In the native shared Project, open the Story and choose **Requirements**. The
native Task portal also shows **Customer requirements** directly. It displays
only active linked customer revisions: key, revision, title, description,
priority, verification method and acceptance expectations. Internal Only
requirements, rationale, questions, decisions and acceptance evidence stay private.
No approved document or customer publication is needed to discuss this working
intent; discussion does not record acceptance.

The client writes a message and chooses **Post to requirement**. Internally,
open **Project > Solutions > Requirements** and the same requirement identity to see that
message in its normal chatter. Use **Reply to Customer** to compose a new shared
reply with the native composer. Only text from explicitly shared Customer
Discussion messages appears on the Task page. Ordinary Send message, internal
notes, old chatter, attachments and scheduled messages remain private. Client
messages retain the authenticated author and do not subscribe clients to the
internal source or send them internal notifications.

Customer Discussion notifications are not enabled by default. Following a
requirement alone does not notify a BA when a client posts. With the default
subscriptions, BAs find new client questions by opening **Project > Solutions > Requirements**
and inspecting that requirement's normal chatter.

The page shows twenty shared messages at a time; **Older messages** retrieves
earlier shared text. Replacing a Task link with a numbered requirement successor
keeps this same conversation. Removing current Project or Task access removes
projection and posting access, including for previous authors. Retiring the link
also removes that exact revision from the shared page. Previously read copies
cannot be recalled. Native Task chatter remains separate and unchanged.

## Link delivery work

As a Business analyst or Project administrator with write access to the affected
tasks, open
**Project > Solutions > Task Previews**. Create a preview with **Solution**,
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
creating another. Inspect links under **Project > Solutions > Requirement Work Links**. To
move an older active link to the same requirement's current sealed head, use
**Adopt Existing Revision** below to replace it and retire the old link together.
For other replacements, use the manual replacement workflow below.

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

## Refine linked acceptance expectations

As a Business analyst or Project administrator with current Task write access,
open the selected active link under **Project > Solutions > Requirement Work Links**.

1. Choose **Refine Acceptance**. Inspect the original exact expectations and the
   selected work link in the dialog.
2. Edit **Proposed Acceptance Expectations** and choose **Apply Refinement**.
   The Task opens; its **Agile** tab shows the new exact expectations under
   **Exact Requirement Acceptance**. No separate save or relinking is needed.

Apply creates a sealed numbered successor, links it to this Task and retires the
old link together. Other linked Tasks remain on their own selected revisions.
Manual Task criteria, approved documents, recorded acceptance and historical
Sprint event content do not change. The new link has no old specification
reference or inherited approval/acceptance: select the successor in a new document
revision and follow the ordinary approval workflow when agreement is required.

Refinement requires a link to the current sealed requirement head. If another
author created a newer revision or retired the link, the old dialog is rejected
without partial changes. Reopening an older active link does not move it to the
head; use the explicit replacement workflow below when adopting existing content.
An identical retry returns the same Task without another successor; a different
proposal on an already refined link is rejected. Cancel changes no requirement
or work link.

## Move another Task to an existing revision

If Tasks A and B link requirement revision 1, refining A creates sealed revision
2 for A only. B stays on revision 1. As a Business analyst or Project
administrator with current write access to B:

1. Open the old link for B under **Project > Solutions > Requirement Work Links** and choose
   **Adopt Existing Revision**. Inspect **Task**, **Previous Expectations**,
   **Target Revision**, **Target Number** (2) and **Target Expectations**.
2. Choose **Adopt This Revision**. B opens; verify **Agile > Exact Requirement
   Acceptance** shows exactly revision 2. The old link is retired with its reason
   and actor in the same operation; no separate save or retirement is needed.

Adoption selects only a different **current sealed head** of the same requirement;
it does not select an arbitrary existing revision or the latest sealed revision
behind a newer draft. If a newer draft head exists, adoption is blocked until the
head is sealed through the ordinary workflow.
A link already at that head cannot adopt it again. A manually retired source link
cannot be used.

Adoption reuses that exact revision; it creates no revision 3. A newer working or
sealed head, withdrawn link or revoked access rejects an unconfirmed dialog
without partial changes. Cancel changes no link. An identical successful retry
returns the same Task, not another edge. Inspect and reopen a stale dialog.

Repeat only for Tasks you choose. Other Tasks, manual Task criteria, approved
baselines, recorded acceptance and historical Sprint content stay unchanged.
Adoption grants no approval or acceptance and copies no old specification
reference. Use **Refine Acceptance** instead when changing the current content.

## Replace a work link manually

For a non-head revision, a different requirement, or coverage that must name an
exact specification, use **Project > Solutions > Task Previews** rather than
**Adopt Existing Revision**:

1. Create a **Link Existing Native Task** preview for the same Task and the chosen
   exact **Requirement Revisions**. Set **Document Revision** if the new coverage
   must name a specification containing those exact requirements.
2. Save, choose **Review and Confirm**, inspect the selection and choose
   **Confirm This Preview**. Verify the successor link under
   **Project > Solutions > Requirement Work Links** before withdrawing the old coverage.
3. Open the old link, choose **Retire Working Link**, enter a meaningful **Reason**
   and choose **Retire With This Reason**. Check **Agile > Exact Requirement
   Acceptance** on the Task to verify the remaining coverage.

Confirmation and retirement are separate actions in this workflow. Confirm the
successor first so a rejected preview does not remove working coverage. This
preserves the old link's history and does not change approved baselines or
recorded acceptance. A retired exact Task/revision edge cannot be reactivated;
use a new deliberate requirement revision when that exact edge was retired.

## Preview the chosen audience

1. Open the exact document revision through **Project > Solutions > Solution Revisions**
   and choose **Preview / Coverage**. Project users need current access to the
   revision and every required reference, including archived references.
2. Select **Internal** or **Redacted Customer**. For internal change comparison,
   select an approved or superseded **Baseline** of the same document. Read
   **Coverage and Changes** for missing links, older revisions,
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

1. Open **Project > Solutions > Exact Requirement Decisions** and create a record.
2. Select **Requirement Revision** and its currently approved specification
   **Document Revision**. The requirement must be included in that exact baseline.
3. Set **Decision** to **Accepted**, supply **Decision Maker and Role**,
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

The page shows only this publication's own decisions. Reissuing the same revision
or replacing the Client Signer starts with no decisions. Internal coverage lists
current decisions only for the currently authorized signer's live publication;
its separate client history preserves earlier decisions, including revoked grants.

Reload before correcting an existing decision. Corrections append history rather
than edit it. A superseded publication is read-only; a successor requires a new
publication and new decisions. **Download HTML** contains the same customer-facing
content, not the internal report.

To remove access, open the publication from its Solution Document and choose
**Revoke Publication**. Removing the exact Project invitation or changing the
client identity, company access or signer also retires affected publications.
Restoring access does not reactivate retired publications; issue a new publication.
Before deleting a group that supplies client portal membership, explicitly revoke
its publications: group deletion can leave a grant unretired, and group-side
membership restoration can make it available again. See the group-deletion
limitation in [ADR 013](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/19.0/docs/adrs/013-solution-definition-contract.md#authenticated-client-publication-and-decisions).
Downloaded copies cannot be recalled.

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
