{
    "name": "Scrum Analytics",
    "summary": "Deterministic Sprint analytics from immutable scope facts",
    "version": "19.0.1.0.1",
    "author": "McCann Hub",
    "maintainer": "Jimmy McCann",
    "website": "https://github.com/vice-magus-faolan/odoo-agile-delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_scrum"],
    "data": [
        "security/ir.model.access.csv",
        "security/project_scrum_analytics_security.xml",
        "data/project_scrum_analytics_data.xml",
        "views/project_scrum_analytics_views.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "project_scrum_analytics/static/tests/tours/analytics_navigation.js",
        ],
    },
    "installable": True,
    "application": False,
}
