Make the OCA 19.0 `document_knowledge`, `document_page` and
`document_page_project` addons available before installing this bridge. See the
[adoption decision](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/19.0/docs/adrs/006-knowledge-relationship-model.md)
for backend selection, then follow the
[Scrum setup guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_scrum#configuration).

Select **Administrator** under **Project** in user access rights, called Project
administrator below, to manage Sprints and their retrospective links. OCA
Document Page editor access is also needed to create and edit pages; page read
access is required to link or open an existing page. OCA page managers can delete
pages, subject to record and company access. Project permissions do not grant
these page permissions.
