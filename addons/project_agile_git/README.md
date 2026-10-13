# Agile Git Facts

`project_agile_git` is the provider-neutral Milestone 6 boundary for repository,
delivery-ledger, branch/ref, commit, pull-request, check, immutable Agile-key
association, and association-audit records.

It depends only on `project_agile`. It intentionally has no controller, provider SDK,
`queue_job` dependency, custom JavaScript, task-stage mutation, or workflow automation.
Provider adapters own authenticated ingress and native Odoo 19 `ir.cron` processing
without making the generic module provider-dependent.

Repository configuration is project- and company-scoped. Webhook secrets and retained
payloads are system-administrator-only fields. Facts remain protected by Project
visibility plus global multi-company rules. Delivery retention defaults to digest-only;
the GitHub adapter documents the explicit redacted retention setting required for its
asynchronous normalization subset.

## Read-only visibility

The addon adds ordinary Project, Task, repository, and fact list/form/search actions;
there is no custom Git dashboard or provider request while rendering a view. Project and
Task counters use the current user's record rules and grouped reads. Task actions
resolve immutable local associations server-side before selecting their branch, commit,
pull-request, or check facts.

External fact links are derived from each validated public provider repository URL, not
from provider payload URLs. The current providers use HTTPS public hosts only: GitHub
(`github.com`), GitLab (`gitlab.com`), and Bitbucket (`bitbucket.org`). GitHub is the
only adapter in this milestone. Connector facts are observations, not evidence that an
Odoo task is complete.
