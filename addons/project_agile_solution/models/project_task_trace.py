"""Native work remains authoritative; traceability does not regenerate or move it."""

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.project_agile.utils import claim_records

from .solution_content import check_reference_commands, reference_command_ids


class _CopiedActorCommands(list):
    # Server-only copy provenance; JSON/RPC receives an ordinary command list.
    def __init__(self, source):
        super().__init__([Command.set(source._actor_copy_ids())])
        self.source_id = source.id


class ProjectTaskTrace(models.Model):
    _inherit = "project.task"

    solution_requirement_acceptance = fields.Html(
        string="Linked Requirement Acceptance",
        compute="_compute_requirement_acceptance",
        compute_sudo=False,
        help="Accessible active exact links; not a Task acceptance decision.",
    )

    @api.depends("solution_last_reference")
    @api.depends_context("uid", "company")
    def _compute_requirement_acceptance(self):
        links = self.env["project.agile.requirement.task.link"].sudo(False)
        for task in self:
            content = []
            task.sudo(False).check_access("read")
            try:
                visible = (
                    links.search(
                        [("task_id", "=", task._origin.id), ("active", "=", True)],
                        order="id",
                    )
                    if task._origin.id
                    else links.browse()
                )
            except AccessError:
                visible = links.browse()
            for link in visible:
                try:
                    link._check_current_trace_read()
                    revision = link.requirement_revision_id.sudo(False)
                    revision.requirement_id.check_access("read")
                    values = revision.read(
                        [
                            "title",
                            "number",
                            "acceptance_expectations",
                            "verification_method",
                        ]
                    )[0]
                except AccessError:
                    # Task visibility is not permission to reveal a requirement.
                    continue
                content.append(
                    Markup(
                        "<section><h4>%s — %s %s</h4>"
                        "<p><strong>%s</strong></p><pre>%s</pre>"
                        "<p><strong>%s</strong></p><pre>%s</pre></section>"
                    )
                    % (
                        values["title"],
                        _("Revision"),
                        values["number"],
                        _("Acceptance Expectations"),
                        values["acceptance_expectations"],
                        _("Verification Method"),
                        values["verification_method"],
                    )
                )
            task.solution_requirement_acceptance = Markup("").join(content) or False

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

    def _actor_copy_ids(self):
        self.ensure_one()
        caller = self.sudo(False).with_context(active_test=False)
        caller.check_access("read")
        # Relation reads filter inaccessible identities. Enumerate only stored IDs on
        # this authorized source, then enforce caller access on the complete set.
        actors = caller.env["project.agile.solution.context"].browse(
            caller.sudo().solution_actor_ids.ids
        )
        actors.check_access("read")
        actors.solution_id.check_access("read")
        actors.project_id.check_access("read")
        return actors.ids

    @api.model
    def _check_actor_commands(self, values, *, creating=False):
        commands = values.get("solution_actor_ids", [])
        if not commands:
            return
        inherited = creating and isinstance(commands, _CopiedActorCommands)
        if inherited:
            source = self.browse(commands.source_id).sudo(False)
            source.check_access("read")
            if values.get("project_id") != source.project_id.id or commands != [
                Command.set(source._actor_copy_ids())
            ]:
                raise AccessError(_("Copied Actors must retain their source Project."))
        user = self.env.user
        if not user.active or not (
            inherited
            or user.has_group("project.group_project_manager")
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
        selected_ids = {
            actor_id
            for command in commands
            if command[0] in (Command.LINK, Command.SET)
            for actor_id in reference_command_ids(command)
        }
        selected = actors.browse(selected_ids)
        # Archive is a selection rule, not a retroactive historical constraint.
        retained = self.browse() if creating else self.with_context(active_test=False)
        if not inherited and any(
            not actor.active
            and (
                not retained
                or any(actor not in task.solution_actor_ids for task in retained)
            )
            for actor in selected
        ):
            raise ValidationError(_("Select active Actors."))

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["solution_actor_ids"])
        for values in vals_list:
            self._check_actor_commands(defaults | values, creating=True)
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
            ):
                commands = _CopiedActorCommands(task)
                if commands[0][2]:
                    values["solution_actor_ids"] = commands
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
