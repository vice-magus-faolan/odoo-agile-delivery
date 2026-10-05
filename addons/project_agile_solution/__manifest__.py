{
    "name": "Agile Solution Definition",
    "summary": "Optional solution documents, immutable baselines and separate approvals",
    "version": "19.0.1.1.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile"],
    "data": [
        "security/ir.model.access.csv",
        "security/project_agile_solution_rules.xml",
        "views/project_agile_solution_views.xml",
        "views/solution_document_views.xml",
    ],
    "installable": True,
    "application": False,
}
