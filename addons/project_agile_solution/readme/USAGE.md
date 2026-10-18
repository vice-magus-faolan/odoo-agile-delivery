## Build and approve a specification

Use the Project Manager account and Project access described in Configuration.
The following example starts with a Solution Specification / Internal Brief.

1. In **Project > Requirements**, create a requirement with **Name** and
   **Solution**. Save, then choose **Open / New Content Revision**. Fill **Title**,
   **Requirement Type** (Functional or Nonfunctional), **Priority**, **Audience**,
   **Description**, **Rationale**, **Verification Method**, and **Acceptance
   Expectations**. Save the exact content revision; it is not a task.
2. In **Project > Solution Documents**, open your document and choose
   **Open / New Working Revision**. Edit **Title** and add sections under
   **Ordered Narrative**, including their **Audience** and **Body**. Alternatively,
   **Copy Template Sections** lets you select a starting template and **Confirm**
   the copy. Later template changes do not update the copied sections.
3. Under **Exact Requirements**, select the requirement revision you just saved.
   Under **Exact Supporting Context**, optionally select content prepared through
   **Project > Solution Supporting Context** and **Open / New Context Revision**.
   Questions can name an owner, planning significance and existing Spike tasks;
   resolving discovery does not approve additional scope.
4. If a SOW exists, set **Based Sow Revision** to its currently approved revision.
   Use **Scope Disposition** and **Scope Change Reason** to describe an explicit
   change. Expanded specification scope needs a separately approved successor
   SOW marked **Explicit Scope Change**, not merely a discovery answer.
5. Save and choose **Submit for Review**. The content is frozen **In Review**,
   but is still unapproved. The designated approver chooses **Approve Exact
   Revision**. To edit a review, use **Return with Reason**, enter **Reason** and
   **Confirm**. Requirement/context content already sealed by a reference stays
   sealed; revise it through its stable identity instead.
6. For later changes, open the approved revision and choose **New Working
   Revision**. Create successor requirement/context revisions as needed and
   deliberately select them in the new draft. Approving the successor marks the
   previous baseline **Superseded** without rewriting its content or decisions.

## Link delivery work deliberately

As a Project Manager with write access to the affected tasks, open **Project >
Deliberate Task Previews**. Create a preview with **Solution**, **Operation**
(**Link Existing Native Task** or **Create Native Task**), **Name**, and one to
twenty exact **Requirement Revisions**. Select **Task** for existing work; for
new work, select **Agile Item Type** and optionally **Description**. An optional
**Document Revision** must contain the selected exact requirements.

Save, choose **Review and Confirm**, inspect the proposed work, then choose
**Confirm This Preview** as the same user. Saving or canceling the preview does
not create work. Changed source content requires a fresh preview; confirming an
already consumed preview returns its existing task rather than creating another.
Inspect links under **Project > Requirement Work Links**. Use **Retire Working
Link** with a reason when replacing coverage, then deliberately link the successor.

Tasks remain editable delivery work. Specification changes do not rewrite their
descriptions, criteria, estimates, workflow or Sprint allocation. For legitimately
unlinked maintenance, enter an explanation on the task **Solution Maintenance**
tab rather than inventing a requirement.

## Preview the chosen audience

1. Open the exact document revision through **Project > Solution Revisions**
   and choose **Preview / Coverage**. Project users need current access to the
   revision and every required reference, including archived references.
2. Select **Internal** or **Redacted Customer**. For internal change comparison,
   select an approved or superseded **Baseline** of the same document. Read
   **Honest Coverage / Change Impact** for missing links, older revisions,
   unresolved questions and explicit decisions; it is not a completion percentage.
3. Choose **Render Selected Audience** for HTML output. Draft and review output
   remains unapproved; approved/superseded output uses that exact frozen baseline,
   not current task descriptions.

Redacted customer output includes only customer-tagged narrative, requirements
and section/domain/deliverable context. Questions, decisions, actors and acceptance
evidence are excluded even when tagged customer. Narrative formatting is reduced
to text; links, images and remote resources are not embedded. This is a redacted
projection, not a full internal baseline or customer portal. Review exported files
before sharing; do not give customers internal report URLs.

Missing access to required content refuses rendering rather than silently
omitting it. Internal coverage also refuses collections above 1,000 rows; use
smaller initiatives instead of treating a partial view as complete.

## Record exact acceptance

Only the active internal Project Manager who actually approved the selected
specification baseline may record its decisions, with current Project, record
and company access. Changing the document Approver does not transfer that past
authority.

1. Open **Project > Exact Requirement Decisions** and create a record.
2. Select **Requirement Revision** and its currently approved specification
   **Document Revision**. The requirement must be included in that exact baseline.
3. Set **Decision** to **Accepted**, supply **Asserted Authority / Role**,
   **Criteria Evaluated**, and nonempty manual **Evidence**. Save. The recorder
   and UTC decision time are recorded automatically.

Document approval, task Done and PR merge are not acceptance. Evidence is a manual
observation/reference, not an automatically verified URL, test result or external
signature. Acceptance applies only to this exact requirement/baseline pair; it
does not carry into a successor, even if content is reused.

Saved decisions cannot be edited or deleted. Append **Rejected** or **Withdrawn**
with criteria and evidence to correct history; those corrections also allow a
superseded baseline. Withdrawal requires a currently accepted decision for the
same exact pair. The acceptance-events list filter shows history, not necessarily
current accepted status.
