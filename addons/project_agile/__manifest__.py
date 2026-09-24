{
    "name": "Agile Project Core",
    "summary": "Opt-in Agile delivery foundations for Odoo Project",
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project"],
    "data": [
        "security/ir.model.access.csv",
        "data/project_agile_item_type_data.xml",
        "views/project_agile_project_views.xml",
        "views/project_agile_task_views.xml",
        "views/project_agile_item_type_views.xml",
    ],
    "installable": True,
    "application": False,
}
