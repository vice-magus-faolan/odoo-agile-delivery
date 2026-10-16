"""Retention guards on native Project and solution identities with history."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .project_agile_solution import check_history_defaults


class SolutionRetention(models.Model):
    _inherit = "project.agile.solution"

    def unlink(self):
        self.sudo(False).check_access("unlink")
        self.project_id.sudo(False).check_access("write")
        self.lock_for_update()
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

    solution_last_history_ref = fields.Reference(
        selection=[
            ("project.agile.solution.document", "Document"),
            ("project.agile.requirement", "Requirement"),
            ("project.agile.solution.context", "Context"),
        ],
        readonly=True,
        copy=False,
        groups="project_agile_solution.group_snapshot_storage",
        help=(
            "Published by new Solution history to conflict with company "
            "changes/deletion and concurrent first-use key allocation."
        ),
    )

    @api.model
    def default_get(self, names):
        return super().default_get(
            [name for name in names if name != "solution_last_history_ref"]
        )

    @api.model_create_multi
    def create(self, vals_list):
        if any("solution_last_history_ref" in values for values in vals_list):
            raise ValidationError(_("Solution history publication is server managed."))
        check_history_defaults(self.env)
        return super().create(vals_list)

    def _record_solution_history(self, record):
        self.ensure_one()
        if record.project_id != self or record._name not in {
            "project.agile.solution.document",
            "project.agile.requirement",
            "project.agile.solution.context",
        }:
            raise ValidationError(_("History must retain its Project."))
        return super(ProjectSolutionRetention, self.sudo()).write(
            {
                "solution_last_history_ref": f"{record._name},{record.id}",
            }
        )

    def _check_solution_retention(self):
        """Deny destructive scope changes even when history is currently hidden."""
        self.sudo(False).check_access("write")
        lineages = (
            self.env["project.agile.solution"]
            .sudo()
            .with_context(active_test=False)
            .search([("project_id", "in", self.ids)])
        )
        self.lock_for_update()
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
        if "solution_last_history_ref" in values:
            raise ValidationError(_("Solution history publication is server managed."))
        if "company_id" in values and any(
            record.company_id.id != (values["company_id"] or False) for record in self
        ):
            self._check_solution_retention()
        return super().write(values)

    def unlink(self):
        self._check_solution_retention()
        return super().unlink()
