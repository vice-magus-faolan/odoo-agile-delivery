{
    "name": "Agile Git Policy Contract",
    "summary": "Disabled optional Git workflow policy contract fixture",
    "version": "19.0.1.0.0",
    "author": "Odoo Agile Delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile_git"],
    "data": [
        "security/ir.model.access.csv",
        "security/project_git_policy_security.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
