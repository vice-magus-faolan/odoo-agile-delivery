"""Native work remains authoritative; traceability does not regenerate or move it."""

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .solution_access import lock_records


class ProjectTaskTrace(models.Model):
    _inherit = "project.task"

    solution_maintenance_reason = fields.Text(
        help=(
            "Optional explanation for legitimately unlinked maintenance work; "
            "not requirement acceptance."
        )
    )

    def _trace_retained(self):
        # Retention-only booleans disclose no elevated identity/name/count.
        links = (
            self.env["project.agile.requirement.task.link"]
            .sudo()
            .with_context(active_test=False)
        )
        intents = self.env["project.agile.solution.task.intent"].sudo()
        return links.search_count(
            [("task_id", "in", self.ids)], limit=1
        ) or intents.search_count([("task_id", "in", self.ids)], limit=1)

    def write(self, values):
        if "project_id" in values or "company_id" in values:
            self.sudo(False).check_access("write")
            lock_records(self, serialize=True)
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
        lock_records(self, serialize=True)
        if self._trace_retained():
            # Trace/retry evidence must survive Task deletion requests.
            raise ValidationError(  # pylint: disable=no-raise-unlink
                _(
                    "Retain linked or generated work and its retry identity; "
                    "archive instead."
                )
            )
        return super().unlink()
