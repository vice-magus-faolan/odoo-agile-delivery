{
    "name": "Scrum Document Page",
    "summary": "Optional Sprint retrospective pages on OCA Document Page",
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "AGPL-3",
    "depends": ["project_scrum", "document_page_project"],
    "data": [
        "data/document_page_templates.xml",
        "views/project_sprint_document_page_views.xml",
    ],
    "installable": True,
    "application": False,
}
