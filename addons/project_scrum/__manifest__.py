{
    "name": "Scrum Project Foundation",
    "summary": "Sprint lifecycle and historical scope foundations for Agile Project",
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_scrum_views.xml",
        "views/project_sprint_close_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
