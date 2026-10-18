Use an Odoo 19 environment with native Project available. Follow the maintained
[repository installation guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/README.md#installation)
to expose this repository's `addons/` directory, update the Apps list and install
`project_agile` (Agile Project Core). An authorized administrator must remove the
default **Apps** filter to find it: this is an installable, non-application addon
(`application=False`). Odoo installs its native dependencies automatically.

No OCA Document Page source, Enterprise addon or external queue runner is required.
Back up the database and filestore before updating or removing installed modules;
uninstalling removes addon-owned data. The repository guide covers deployment and
[contributor verification](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/contributing.md).
