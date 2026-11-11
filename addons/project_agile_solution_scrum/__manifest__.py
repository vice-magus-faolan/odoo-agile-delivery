{
    "name": "Agile Solution Scrum Context",
    "summary": (
        "Optional frozen exact requirement context at native Sprint scope events"
    ),
    "version": "19.0.1.0.0",
    "author": "McCann Hub",
    "maintainer": "Jimmy McCann",
    "website": "https://github.com/vice-magus-faolan/odoo-agile-delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile_solution", "project_scrum"],
    "data": [
        "security/ir.model.access.csv",
        "security/solution_scrum_rules.xml",
        "views/sprint_context_views.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "project_agile_solution_scrum/static/tests/tours/agile_role_assignment.js"
        ],
    },
    "installable": True,
    "application": False,
}
