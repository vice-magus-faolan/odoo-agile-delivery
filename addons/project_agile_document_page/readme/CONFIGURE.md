Make the OCA 19.0 `document_knowledge`, `document_page` and
`document_page_project` addons available before installing this bridge. The
[adoption decision](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/adrs/006-knowledge-relationship-model.md)
records the selected backend and dependency boundary.

Configure an [Agile Project](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile#configuration).
For this walkthrough, select **Administrator** under **Project** in user access
rights, called Project administrator below. The caller must also be able to
read the selected Document Page; creating a root requires OCA Document Page
editor access. Project access alone does not grant page creation. OCA page users
can read pages, editors can create and edit them, and managers can delete them,
subject to record and company access.
