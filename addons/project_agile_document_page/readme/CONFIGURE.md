Make the OCA 19.0 `document_knowledge`, `document_page` and
`document_page_project` addons available before installing this bridge.
Use the selected OCA `knowledge` commit
[`e4a12c0c99866a5850840941d6f7ae3b3b27280d`](https://github.com/OCA/knowledge/tree/e4a12c0c99866a5850840941d6f7ae3b3b27280d).
All three OCA modules and this bridge use AGPL-3.
Review the combined deployment's corresponding-source obligations before use.
Run `./scripts/verify-oca-document-page` from the repository root to check
the selected backend and bridges in disposable databases.
The separate check covers installation, update, uninstall and reinstall.
Validate your installed extensions and Odoo.sh staging separately.
The
[adoption decision](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/19.0/docs/adrs/006-knowledge-relationship-model.md)
records the selected backend and dependency boundary.

Configure an [Agile Project](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_agile#configuration).
For this walkthrough, select **Administrator** under **Project** in user access
rights, called Project administrator below. The caller must also be able to
read the selected Document Page; creating a root requires OCA Document Page
editor access. Project access alone does not grant page creation. OCA page users
can read pages, editors can create and edit them, and managers can delete them,
subject to record and company access.
