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
