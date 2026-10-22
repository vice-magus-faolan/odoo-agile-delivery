from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

_AUDIT_FIELDS = {
    "actor_id",
    "changed_at",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
    "applicable",
    "company_id",
    "project_id",
    "sequence",
    "native_access",
}


class ProjectTaskEnvironmentStatus(models.Model):
    _name = "project.task.environment.status"
    _description = "Task Environment Status"
    _inherit = ["mail.thread"]
    _rec_name = "environment_id"
    _order = "sequence, id"
    _check_company_auto = True

    task_id = fields.Many2one(
        "project.task",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    environment_id = fields.Many2one(
        "project.agile.environment",
        required=True,
        ondelete="restrict",
        check_company=True,
    )
    project_id = fields.Many2one(related="task_id.project_id", store=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True)
    sequence = fields.Integer(related="environment_id.sequence", store=True)
    status = fields.Selection(
        [("todo", "To do"), ("done", "Done"), ("verified", "Verified")],
        required=True,
        default="todo",
        tracking=True,
    )
    actor_id = fields.Many2one(
        "res.users", string="Set by", readonly=True, required=True
    )
    changed_at = fields.Datetime(string="Set on", readonly=True, required=True)
    applicable = fields.Boolean(compute="_compute_applicable", store=True)
    native_access = fields.Boolean(
        compute="_compute_native_access", search="_search_native_access"
    )

    def _compute_native_access(self):
        for line in self:
            line.native_access = line.task_id.sudo(False).has_access("read")

    def _search_native_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        # Rules compile under sudo; restore the caller before building RHS queries.
        tasks = self.env["project.task"].sudo(False).with_context(active_test=False)
        projects = (
            self.env["project.project"].sudo(False).with_context(active_test=False)
        )
        accessible = Domain("task_id", "in", tasks._search([])) & Domain(
            "project_id", "in", projects._search([])
        )
        positive = Domain.OR(accessible if flag else ~accessible for flag in value)
        return positive if operator == "in" else ~positive

    _task_environment_unique = models.Constraint(
        "UNIQUE(task_id, environment_id)",
        "A task has only one status per environment.",
    )

    @api.depends("environment_id.active", "task_id.agile_tracks_environments")
    def _compute_applicable(self):
        for line in self:
            line.applicable = (
                line.environment_id.active and line.task_id.agile_tracks_environments
            )

    @api.constrains("task_id", "environment_id")
    def _check_environment_project(self):
        for line in self:
            if line.task_id.project_id != line.environment_id.project_id:
                raise ValidationError(
                    self.env._("Task and environment must belong to the same Project.")
                )

    @api.model
    def _check_audit_input(self, values):
        defaults = {
            key.removeprefix("default_")
            for key in self.env.context
            if key.startswith("default_")
        }
        if _AUDIT_FIELDS & (values.keys() | defaults):
            raise AccessError(self.env._("Status actor and time are recorded by Odoo."))

    def _check_task_status_access(self):
        self.check_access("write")
        self.task_id.check_access("write")
        self.task_id.project_id.check_access("read")
        if any(not line.applicable for line in self):
            raise ValidationError(
                self.env._("Only applicable environment statuses can be changed.")
            )

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["task_id", "environment_id"])
        for values in vals_list:
            self._check_audit_input(values)
            task = self.env["project.task"].browse(
                values.get("task_id", defaults.get("task_id"))
            )
            environment = self.env["project.agile.environment"].browse(
                values.get("environment_id", defaults.get("environment_id"))
            )
            task.check_access("write")
            task.project_id.check_access("read")
            environment.check_access("read")
            if not task.agile_tracks_environments or not environment.active:
                raise ValidationError(
                    self.env._("This task does not track this active environment.")
                )
            if task.project_id != environment.project_id:
                raise ValidationError(
                    self.env._("Task and environment must belong to the same Project.")
                )
        return super().create(
            [
                dict(values, actor_id=self.env.uid, changed_at=fields.Datetime.now())
                for values in vals_list
            ]
        )

    def write(self, values):
        self._check_audit_input(values)
        if {"task_id", "environment_id"} & values.keys():
            raise ValidationError(
                self.env._("A status line's task and environment cannot change.")
            )
        self._check_task_status_access()
        if "status" in values:
            values = dict(
                values, actor_id=self.env.uid, changed_at=fields.Datetime.now()
            )
        # Native tracking supplies history without a second event subsystem.
        return super(
            ProjectTaskEnvironmentStatus,
            self.with_context(tracking_disable=False, mail_notrack=False),
        ).write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_history(self):
        raise ValidationError(
            self.env._("Keep status history; archive the environment instead.")
        )
