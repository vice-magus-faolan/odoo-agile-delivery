Receive authenticated GitHub webhooks as **Deliveries**, then process supported
events through native Odoo scheduled actions. This optional Odoo 19 Community
addon depends on `project_agile_git`.

Supported events are `push`, `pull_request` and `check_run`. Processing records
branches, commits, pull requests, checks and explicit task-key associations.
Receiving and processing GitHub deliveries leave task completion and stage
decisions to your Project workflow and the separately configured policy addon.
