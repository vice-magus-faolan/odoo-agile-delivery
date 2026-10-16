"""Native work remains authoritative; traceability does not regenerate or move it."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .project_agile_solution import check_history_defaults


class ProjectTaskTrace(models.Model):
    _inherit = "project.task"

    solution_maintenance_reason = fields.Text(
        help=(
            "Optional explanation for legitimately unlinked maintenance work; "
            "not requirement acceptance."
        )
    )

    solution_last_reference = fields.Reference(
        selection=[
            ("project.agile.requirement.task.link", "Requirement Link"),
            ("project.agile.solution.context.revision", "Discovery Context"),
        ],
        readonly=True,
        copy=False,
        groups="project_agile_solution.group_snapshot_storage",
        help=(
            "Published by link creation/retirement and discovery references to "
            "conflict with concurrent Task scope changes, deletion and Sprint "
            "capture."
        ),
    )

    @api.model
    def default_get(self, names):
        return super().default_get(
            [name for name in names if name != "solution_last_reference"]
        )

    @api.model_create_multi
    def create(self, vals_list):
        if any("solution_last_reference" in values for values in vals_list):
            raise ValidationError(_("Solution trace publication is server managed."))
        check_history_defaults(self.env)
        return super().create(vals_list)

    def _record_solution_reference(self, reference):
        if reference._name == "project.agile.requirement.task.link":
            valid = self == reference.task_id
        elif reference._name == "project.agile.solution.context.revision":
            valid = self <= reference.spike_task_ids
        else:
            valid = False
        if not valid:
            raise ValidationError(_("Trace publication must retain its native work."))
        return super(ProjectTaskTrace, self.sudo()).write(
            {
                "solution_last_reference": f"{reference._name},{reference.id}",
            }
        )

    def _trace_retained(self):
        # Retention-only booleans disclose no elevated identity/name/count.
        links = (
            self.env["project.agile.requirement.task.link"]
            .sudo()
            .with_context(active_test=False)
        )
        intents = self.env["project.agile.solution.task.intent"].sudo()
        return (
            links.search_count([("task_id", "in", self.ids)], limit=1)
            or intents.search_count([("task_id", "in", self.ids)], limit=1)
            or self.env["project.agile.solution.context.revision"]
            .sudo()
            .search_count([("spike_task_ids", "in", self.ids)], limit=1)
        )

    def write(self, values):
        if "solution_last_reference" in values:
            raise ValidationError(_("Solution trace publication is server managed."))
        if "project_id" in values or "company_id" in values:
            self.sudo(False).check_access("write")
            self.lock_for_update(allow_referencing=True)
            if self._trace_retained() and any(
                ("project_id" in values and values["project_id"] != task.project_id.id)
                or (
                    "company_id" in values
                    and values["company_id"] != (task.company_id.id or False)
                )
                for task in self
            ):
                raise ValidationError(
                    _(
                        "Traceable work cannot change Project or company; "
                        "archive instead."
                    )
                )
        return super().write(values)

    def unlink(self):
        self.sudo(False).check_access("unlink")
        self.lock_for_update()
        if self._trace_retained():
            # Trace/retry evidence must survive Task deletion requests.
            raise ValidationError(  # pylint: disable=no-raise-unlink
                _(
                    "Retain linked or generated work and its retry identity; "
                    "archive instead."
                )
            )
        return super().unlink()
