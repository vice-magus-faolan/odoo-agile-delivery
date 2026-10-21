{
    "name": "Agile Planning UI",
    "summary": "Optional Odoo frontend for authoritative Agile planning",
    "version": "19.0.1.2.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_scrum"],
    "data": ["views/project_agile_ui_views.xml"],
    "assets": {
        "web.assets_backend": [
            "project_agile_ui/static/src/planning_board.js",
            "project_agile_ui/static/src/planning_board.xml",
            "project_agile_ui/static/src/planning_board.scss",
        ],
        "web.assets_unit_tests": [
            "project_agile_ui/static/tests/**/*.test.js",
        ],
    },
    "installable": True,
    "application": False,
}
