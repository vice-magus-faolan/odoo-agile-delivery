Installation assigns no **Git Policy Manager** members and creates no rules.
An authorized administrator must explicitly grant that capability to the rule
owner and a different approver. It includes Project administrator permissions;
Project administrator access alone is not sufficient. Use an active internal,
non-superuser execution account with current company membership and actual
write access to all affected Project tasks.

1. Configure an active company-scoped Agile Project and a repository using the
   [Git Facts guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile_git#configuration).
2. As a Git Policy Manager, open the Project form, **Git Policy**, and choose
   **Enable Dry Run**. Do not select Apply mode for a preview.
3. As the intended rule owner, open **Project > Configuration > Git Policy
   Rules**. Create a named rule and select its repository; Odoo records you as
   its owner. Then create its draft revision under **Git Policy Revisions**.
   Select the rule, exact target branch, 1 to 20 active nonpersonal
   source stages linked to the Project, one eligible target stage, the execution
   user and up to 20 exact check names. No names means CI is not a condition,
   not that CI passed. Rating, email-template and SMS-template stages are refused.
4. A different Git Policy Manager opens the revision and chooses **Approve and
   Activate**, acknowledges the native side effects, then confirms. Review the
   saved mode and cutoff: approval in Dry Run does not enable task writes.

Unknown authority profiles refuse activation. Review installed Task extensions
and the [bounded authority profile](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/git-policy-authority-profiles.md)
before approval; additional extensions can have external effects a stage write
cannot undo. See the [configuration guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/git-policy-configuration.md)
for supported selectors and revocation conditions.
