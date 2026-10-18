Follow the [repository installation guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/README.md#installation)
for Odoo 19 and this repository's `addons/` source. As an authorized administrator,
update the Apps list, remove the default **Apps** filter and search for
`project_scrum` (Scrum Project Foundation). It has `application=False`; installing
it also installs `project_agile` and native Project dependencies.

No Enterprise, OCA Document Page or external queue service is required for Scrum.
Back up an existing database and filestore before updates or removal; uninstalling
destroys addon-owned Sprint/history data. Use the existing
[contributor checks](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/contributing.md)
for disposable development verification, not a shared operational database.
