{
    "name": "Agile Planning UI",
    "summary": "Optional Odoo frontend fixture for the Agile planning workspace",
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_scrum"],
    "assets": {
        "web.assets_unit_tests": [
            "project_agile_ui/static/tests/**/*.test.js",
        ],
    },
    "installable": True,
    "application": False,
}
