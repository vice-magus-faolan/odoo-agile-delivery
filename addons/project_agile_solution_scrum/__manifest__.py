{
    "name": "Agile Solution Scrum Context",
    "summary": (
        "Optional frozen exact requirement context at native Sprint scope events"
    ),
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile_solution", "project_scrum"],
    "data": [
        "security/ir.model.access.csv",
        "security/solution_scrum_rules.xml",
        "views/sprint_context_views.xml",
    ],
    "installable": True,
    "application": False,
}
