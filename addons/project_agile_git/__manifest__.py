{
    "name": "Agile Git Facts",
    "summary": (
        "Provider-neutral Git facts and delivery-ledger contract for Agile Project"
    ),
    "version": "19.0.1.1.0",
    "author": "McCann Hub",
    "maintainer": "Jimmy McCann",
    "website": "https://github.com/vice-magus-faolan/odoo-agile-delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile"],
    "data": [
        "security/ir.model.access.csv",
        "security/project_agile_git_security.xml",
        "security/project_git_environment_security.xml",
        "views/project_git_fact_views.xml",
        "views/project_git_environment_views.xml",
    ],
    "installable": True,
    "application": False,
}
