Optional Odoo 19 Community bridge designating one OCA Document Page as the documentation
root for an Agile Project. It depends on `project_agile` and OCA
`document_page_project`, which requires `document_page` and `document_knowledge`.
The bridge and these OCA modules use AGPL-3; review the combined deployment's
corresponding-source obligations before use.

Pages retain the native OCA editor, hierarchy, revision history and Project
relation. Clearing the root designation does not delete or reparent the page.
This is a Project-page bridge, not a Task-page connector or an Enterprise
Knowledge integration.
