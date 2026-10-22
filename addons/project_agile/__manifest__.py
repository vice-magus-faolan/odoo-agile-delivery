{
    "name": "Agile Project Core",
    "summary": "Opt-in Agile delivery foundations for Odoo Project",
    "version": "19.0.1.6.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project"],
    "data": [
        "security/project_agile_groups.xml",
        "security/ir.model.access.csv",
        "security/project_environment_rules.xml",
        "data/project_agile_item_type_data.xml",
        "data/environment_tracking_data.xml",
        "views/project_agile_project_views.xml",
        "views/project_agile_task_views.xml",
        "views/project_agile_item_type_views.xml",
        "views/project_agile_stage_views.xml",
        "views/project_environment_views.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "project_agile/static/tests/tours/item_type_kanban.js",
            "project_agile/static/tests/tours/environment_status.js",
        ]
    },
    "installable": True,
    "application": False,
}
