"""Retention guards on native Project and solution identities with history."""

from odoo import _, models
from odoo.exceptions import ValidationError

from .solution_access import lock_records


class SolutionRetention(models.Model):
    _inherit = "project.agile.solution"

    def unlink(self):
        self.sudo(False).check_access("unlink")
        self.project_id.sudo(False).check_access("write")
        lock_records(self, serialize=True)
        # Retention-only elevation emits no metadata, names, IDs or counts.
        if (
            self.env["project.agile.solution.document"]
            .sudo()
            .with_context(active_test=False)
            .search_count([("solution_id", "in", self.ids)], limit=1)
        ):
            # Document history cannot be removed through lineage deletion.
            raise ValidationError(  # pylint: disable=no-raise-unlink
                _("Solution document history must be retained; archive instead.")
            )
        return super().unlink()


class ProjectSolutionRetention(models.Model):
    _inherit = "project.project"

    def _check_solution_retention(self):
        """Deny destructive scope changes even when history is currently hidden."""
        self.sudo(False).check_access("write")
        lineages = (
            self.env["project.agile.solution"]
            .sudo()
            .with_context(active_test=False)
            .search([("project_id", "in", self.ids)])
        )
        lock_records(lineages, serialize=True)
        lock_records(self)
        if (
            self.env["project.agile.solution.document"]
            .sudo()
            .with_context(active_test=False)
            .search_count([("solution_id", "in", lineages.ids)], limit=1)
        ):
            raise ValidationError(
                _(
                    "A Project with solution document history cannot change company "
                    "or be deleted; archive instead."
                )
            )
        for model in ("project.agile.requirement", "project.agile.solution.context"):
            if (
                self.env[model]
                .sudo()
                .with_context(active_test=False)
                .search_count([("solution_id", "in", lineages.ids)], limit=1)
            ):
                raise ValidationError(
                    _(
                        "A Project with solution intent history cannot change company "
                        "or be deleted; archive instead."
                    )
                )

    def write(self, values):
        if "company_id" in values and any(
            record.company_id.id != (values["company_id"] or False) for record in self
        ):
            self._check_solution_retention()
        return super().write(values)

    def unlink(self):
        self._check_solution_retention()
        return super().unlink()
