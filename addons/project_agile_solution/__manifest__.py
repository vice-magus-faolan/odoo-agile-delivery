{
    "name": "Agile Solution Definition",
    "summary": (
        "Optional solution documents, immutable baselines and separate approvals"
    ),
    "version": "19.0.1.8.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile", "portal"],
    "data": [
        "security/project_agile_solution_groups.xml",
        "security/ir.model.access.csv",
        "security/project_agile_solution_rules.xml",
        "data/solution_templates.xml",
        "views/project_agile_solution_views.xml",
        "views/solution_document_views.xml",
        "views/solution_content_views.xml",
        "views/solution_task_views.xml",
        "report/solution_reports.xml",
        "views/solution_render_views.xml",
        "views/solution_portal_templates.xml",
        "views/solution_portal_views.xml",
    ],
    "installable": True,
    "assets": {
        "web.assets_tests": [
            "project_agile_solution/static/tests/tours/solution_render.js",
            "project_agile_solution/static/tests/tours/task_actors.js",
            "project_agile_solution/static/tests/tours/solution_portal.js",
        ],
    },
    "application": False,
}
