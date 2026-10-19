Optional Odoo 19 Community bridge designating one OCA Document Page as the documentation
root for an Agile Project. It depends on `project_agile` and OCA
`document_page_project`, which requires `document_page` and `document_knowledge`.
The bridge and these OCA modules declare AGPL-3 licenses.

Pages retain the native OCA editor, hierarchy, revision history and Project
relation. Clearing the root designation does not delete or reparent the page.
This is a Project-page bridge, not a Task-page connector or an Enterprise
Knowledge integration.

Before public or production use, review the combined deployment's AGPL-3
corresponding-source obligations as recorded in the adoption decision.
