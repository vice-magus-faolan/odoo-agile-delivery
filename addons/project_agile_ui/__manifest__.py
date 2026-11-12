{
    "name": "Agile Planning UI",
    "summary": "Optional Odoo frontend for authoritative Agile planning",
    "version": "19.0.1.4.0",
    "author": "McCann Hub",
    "maintainer": "Jimmy McCann",
    "website": "https://github.com/vice-magus-faolan/odoo-agile-delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_scrum"],
    "data": ["views/project_agile_ui_views.xml"],
    "assets": {
        "web.assets_backend": [
            "project_agile_ui/static/src/quick_create.js",
            "project_agile_ui/static/src/planning_board.js",
            "project_agile_ui/static/src/planning_board.xml",
            "project_agile_ui/static/src/planning_board.scss",
        ],
        "web.assets_unit_tests": [
            "project_agile_ui/static/tests/**/*.test.js",
        ],
        "web.assets_tests": ["project_agile_ui/static/tests/tours/milestones.js"],
    },
    "installable": True,
    "application": False,
}
