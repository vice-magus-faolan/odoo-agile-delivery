{
    "name": "Agile Solution Definition",
    "summary": "Optional project-scoped solution lineage foundation",
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile"],
    "data": [
        "security/ir.model.access.csv",
        "security/project_agile_solution_rules.xml",
        "views/project_agile_solution_views.xml",
    ],
    "installable": True,
    "application": False,
}
