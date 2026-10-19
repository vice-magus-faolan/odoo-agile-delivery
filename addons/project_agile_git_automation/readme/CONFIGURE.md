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
   Select:

   - the rule and exact target branch;
   - 1 to 20 active source stages shared with that Project, not a user's personal stages;
   - one active shared target stage outside the source selection, without rating, email
     or SMS templates;
   - up to 20 distinct exact check names, each 1 to 255 characters;
   - an active internal execution user, not a superuser or portal account, with company
     membership and actual access to every affected Task.

   No check names means CI is not a condition, not that CI passed.
4. A different Git Policy Manager opens the revision and chooses **Approve and
   Activate**, acknowledges the native side effects, then confirms. Review the
   saved mode and cutoff: approval in Dry Run does not enable task writes.

If activation refuses the installed access rules or Task configuration, compare
them with [supported permissions and extensions](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/git-policy-authority-profiles.md)
before approval; additional extensions can have external effects a stage write
cannot undo. See the [configuration guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/git-policy-configuration.md)
for supported selectors and revocation conditions.
