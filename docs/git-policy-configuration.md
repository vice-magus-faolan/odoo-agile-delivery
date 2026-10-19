# Git policy configuration and approval

The optional `project_agile_git_automation` addon depends only on `project_agile_git`
and retains LGPL-3. It targets Odoo 19 Community; validate installed extensions and
Odoo.sh behavior separately. Installing it creates no rules, assigns no policy
capability members and does not enable Task changes. Projects start disabled and in Dry
Run mode.

## Roles and supported configuration

An authorized administrator must grant **Git Policy Manager** to the intended rule owner
and a different approver. This includes Project administrator permissions; Project
administrator access alone does not allow policy configuration or activation. A visible
System Administrator can emergency-disable without gaining activation authority.

Use the
[addon setup guide](../addons/project_agile_git_automation/README.rst#configuration) for
visible controls. Select:

- an active Agile Project with a company and its configured repository;
- the exact target branch and 1 to 20 active source stages shared with that Project, not
  a user's personal stages;
- one active shared target stage outside the source selection, without rating, email or
  SMS templates;
- up to 20 distinct exact check names, each 1 to 255 characters;
- an active internal execution user, not a superuser or portal account, with company
  membership and actual access to every affected Task.

No check names means CI is not a condition, not that CI passed. Several provider checks
with the same required name do not count as success even if one passed. No wildcard,
script, arbitrary field action or caller-selected Task is supported. An empty Project
cannot be activated because there is no concrete Task on which to establish the required
permissions.

## Approve in Dry Run first

The owner prepares a draft revision. A different Git Policy Manager approves that exact
revision and acknowledges normal native stage side effects. Check the saved mode,
cutoff, Project, repository and execution user. Dry-run approval permits preview
decisions, not Task writes. Use the [dry-run guide](git-policy-dry-run.md) to inspect
outcomes and reasons before considering Apply mode.

The installed permissions must match the
[supported native rules and extensions](git-policy-authority-profiles.md). Only the
documented custom Task-name and active-status rules are supported; unknown Project,
repository, stage, identity or other Task-rule changes prevent approval. Do not bypass
refusal with sudo or context. Odoo still checks the actual records as each user; a
matching supported configuration is not an access grant.

## Changing or revoking approval

Approved selectors and approval details are immutable. Create a **New Revision** to
change them. Draft changes revoke existing approval, and a different person must approve
the new revision. Selecting Apply mode also revokes earlier approvals; reviewing
previews does not make them executable. A new approval cutoff admits only later eligible
merges and their original authenticated receipts, not old history.

Disabling, ownership changes, archive/delete requests and changes to Project,
repository, stages, identities, company membership, ACLs or record rules may revoke
approval. Both directions of stage membership and user/group changes are observed.
Restoring old settings or access does not restore revoked approval: correct the cause,
create a new revision and obtain distinct-person approval again. A delete request
archives a rule; used history and provider identities cannot be removed or reassigned to
permit another execution.

Before live changes, assess installed Task extensions and notification behavior. Normal
stage writes can create tracking messages and notifications, change timestamps/durations
and recompute nonterminal state. They do not request Done, reopening, Sprint changes or
estimates. Already-sent external effects cannot be retracted by transaction rollback;
template-driven target stages are excluded.

For uncertainty or shutdown, use **Emergency Disable** on the Project or **Disable
Rule**. This stops pending work, not already committed changes. Follow the
[operations runbook](runbooks/git-policy-operations.md) for diagnostics, retry limits,
backups and restore. Technical shared-write/concurrency behavior is in the
[apply boundary](git-policy-apply-boundary.md), with the full contract in
[ADR-012](adrs/012-git-workflow-policy-contract.md).
