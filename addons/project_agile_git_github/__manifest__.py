{
    "name": "Agile GitHub Delivery Ingress",
    "summary": "Authenticated GitHub delivery persistence and normalization "
    "for Agile Git Facts",
    "version": "19.0.1.4.0",
    "author": "McCann Hub",
    "maintainer": "Jimmy McCann",
    "website": "https://github.com/vice-magus-faolan/odoo-agile-delivery",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": ["project_agile_git"],
    "data": [
        "data/project_github_delivery_cron.xml",
        "views/project_github_delivery_views.xml",
    ],
    "installable": True,
    "application": False,
}
