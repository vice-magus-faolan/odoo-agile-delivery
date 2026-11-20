# View boundary

`project_agile` uses inherited Odoo Project and Task views only. It adds no custom
JavaScript or OWL component.

The inherited views expose opt-in Project and environment configuration, conditional
Agile task fields and environment statuses, Epic progress, Project-administrator
item-type configuration, Product Backlog navigation and Agile search filters and
grouping. Native milestones include **Release contents**. Backlog ordering uses the
existing list handle widget against `agile_backlog_sequence`.
