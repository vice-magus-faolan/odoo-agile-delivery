"""Native work remains authoritative; traceability does not regenerate or move it."""

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.project_agile.utils import claim_records

from .solution_content import check_reference_commands, reference_command_ids


class ProjectTaskTrace(models.Model):
    _inherit = "project.task"

    solution_can_select_actors = fields.Boolean(compute="_compute_can_select_actors")

    @api.depends_context("uid")
    def _compute_can_select_actors(self):
        allowed = self.env.user.has_group(
            "project.group_project_manager"
        ) or self.env.user.has_group("project_agile_solution.group_business_analyst")
        for task in self:
            task.solution_can_select_actors = allowed

    solution_actor_ids = fields.Many2many(
        "project.agile.solution.context",
        "solution_task_actor_rel",
        "task_id",
        "context_id",
        string="Actors",
        groups="project.group_project_user",
        copy=False,
        check_company=True,
        help="This Project serves these Actors; not frozen requirement acceptance.",
    )

    @api.model
    def _check_actor_commands(self, values):
        commands = values.get("solution_actor_ids", [])
        if not commands:
            return
        user = self.env.user
        if not user.active or not (
            user.has_group("project.group_project_manager")
            or user.has_group("project_agile_solution.group_business_analyst")
        ):
            raise AccessError(
                _(
                    "An active Business analyst or Project administrator "
                    "is required to select Actors."
                )
            )
        check_reference_commands(commands)
        ids = [item for command in commands for item in reference_command_ids(command)]
        actors = self.env["project.agile.solution.context"].sudo(False).browse(ids)
        actors.check_access("read")
        if len(actors.exists()) != len(set(ids)):
            raise ValidationError(_("Select available Actors."))
        actors.solution_id.check_access("read")
        actors.project_id.check_access("read")

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["solution_actor_ids"])
        for values in vals_list:
            self._check_actor_commands(defaults | values)
        return super().create(vals_list)

    @api.constrains("solution_actor_ids", "project_id", "company_id")
    def _check_actor_scope(self):
        for task in self:
            actors = task.solution_actor_ids
            actors.check_access("read")
            actors.solution_id.check_access("read")
            actors.project_id.check_access("read")
            if any(
                actor.kind != "actor"
                or actor.project_id != task.project_id
                or actor.company_id != task.company_id
                for actor in actors
            ):
                raise ValidationError(
                    _("Actors must belong to the task Project and company.")
                )

    def copy_data(self, default=None):
        values_list = super().copy_data(default=default)
        for task, values in zip(self, values_list, strict=False):
            if (
                "solution_actor_ids" not in (default or {})
                and not self.env.context.get("copy_project")
                and values.get("project_id") == task.project_id.id
                and task.solution_actor_ids
            ):
                values["solution_actor_ids"] = [
                    Command.set(task.solution_actor_ids.ids)
                ]
        return values_list

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
        self._check_actor_commands(values)
        if "project_id" in values or "company_id" in values:
            self.sudo(False).check_access("write")
            claim_records(self, allow_referencing=True)
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
        claim_records(self)
        if self._trace_retained():
            # Trace/retry evidence must survive Task deletion requests.
            raise ValidationError(  # pylint: disable=no-raise-unlink
                _(
                    "Retain linked or generated work and its retry identity; "
                    "archive instead."
                )
            )
        return super().unlink()
