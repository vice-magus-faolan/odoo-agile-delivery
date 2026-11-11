{
    "name": "Agile Git Workflow Policy",
    "summary": (
        "Opt-in typed Git policies, dry runs and bounded native stage application"
    ),
    "version": "19.0.1.5.0",
    "author": "McCann Hub",
    "maintainer": "Jimmy McCann",
    "website": "https://github.com/vice-magus-faolan/odoo-agile-delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile_git"],
    "data": [
        "security/project_git_policy_groups.xml",
        "security/ir.model.access.csv",
        "security/project_git_policy_security.xml",
        "security/project_git_policy_rules.xml",
        "security/project_git_policy_apply_rules.xml",
        "data/project_git_policy_cron.xml",
        "views/project_git_policy_views.xml",
        "views/project_git_policy_evaluation_views.xml",
        "views/project_git_policy_operations_views.xml",
    ],
    "installable": True,
    "assets": {
        "web.assets_tests": [
            "project_agile_git_automation/static/tests/tours/git_policy_operations.js"
        ],
    },
    "auto_install": False,
    "application": False,
}
