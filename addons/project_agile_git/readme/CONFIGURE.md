Repository configuration requires **Administrator** under **Project** in the
user access rights. The instructions below call this role Project administrator.
Setting **Webhook Secret** also requires System Administrator access.

1. Enable Agile on the Project and configure its stable task-key prefix.
2. Open **Project > Tasks > Git Repositories** and create a repository. Enter
   **Name**, **Provider**, **Provider Repository Id**, **Project** and
   **Canonical Url**. **Company** follows the selected Project.
3. For GitHub, run `gh api repos/OWNER/REPO --jq .id` and enter the returned
   number in **Provider Repository Id**. Each provider repository can be mapped
   only once.
4. Set **Canonical Url** to the HTTPS repository URL on `github.com`,
   `gitlab.com` or `bitbucket.org`, matching **Provider**, for example
   `https://github.com/example/delivery`. Fact links are derived from this URL.
   Keep it aligned with the provider repository identity.
5. Choose **Retention Policy** before receiving deliveries. **Digest Only** is
   the default. GitHub asynchronous processing needs **Redacted Excerpt**;
   changing the setting later cannot restore payloads for earlier deliveries.
6. For GitHub deliveries, follow the
   [GitHub connector configuration](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile_git_github#configuration).

Redacted excerpts can still contain sensitive business text and unrecognized
credentials. Keep secrets out of commit messages and other webhook text.

## Environment branch mappings

As a Project administrator with write access to the Project, first configure
its environments in the Project settings. Flag each production environment
with **Production**; the name does not determine its role.

Open **Project > Tasks > Environment Git Branches**. Select an **Environment**
and a **Repository** from the same Agile Project and enter **Target branch**
as the exact, case-sensitive short branch name, for example `release/uat`,
not `refs/heads/release/uat`. Each environment maps a repository once. Edit
or reactivate that mapping instead of adding a duplicate.

Configure every repository needed for that environment and at least one
production mapping before using the UAT/no-production filter. Archived
mappings, repositories and environments are excluded. Mapping edits immediately
reinterpret retained PR observations. Project copies start without mappings.
