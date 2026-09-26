{
    "name": "Scrum Analytics",
    "summary": "Deterministic Sprint analytics from immutable scope facts",
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_scrum"],
    "data": [
        "security/ir.model.access.csv",
        "security/project_scrum_analytics_security.xml",
        "data/project_scrum_analytics_data.xml",
        "views/project_scrum_analytics_views.xml",
    ],
    "installable": True,
    "application": False,
}
