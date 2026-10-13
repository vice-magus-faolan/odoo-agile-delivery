"""One immutable semantic effect per repository/PR/Task, across all approval epochs."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ProjectGitPolicyEffect(models.Model):
    _name = "project.git.policy.effect"
    _inherit = "project.git.policy.task.scope"
    _description = "Consumed Git Task Stage Effect"
    _check_company_auto = True
    _order = "id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    project_id = fields.Many2one(
        "project.project", required=True, readonly=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, ondelete="restrict", index=True
    )
    task_id = fields.Many2one(
        "project.task", required=True, readonly=True, ondelete="restrict", index=True
    )
    agile_key = fields.Char(required=True, readonly=True, index=True)
    provider_request_id = fields.Char(required=True, readonly=True, index=True)
    effect_type = fields.Selection(
        [("task_stage_transition", "Task Stage Transition")],
        required=True,
        readonly=True,
    )
    attempt_id = fields.Many2one(
        "project.git.policy.attempt", required=True, readonly=True, ondelete="restrict"
    )
    activation_id = fields.Many2one(
        "project.git.policy.activation",
        required=True,
        readonly=True,
        ondelete="restrict",
    )
    revision_id = fields.Many2one(
        "project.git.policy.revision", required=True, readonly=True, ondelete="restrict"
    )
    observation_id = fields.Many2one(
        "project.git.policy.observation",
        required=True,
        readonly=True,
        ondelete="restrict",
    )
    execution_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict"
    )
    before_stage_id = fields.Many2one(
        "project.task.type", required=True, readonly=True, ondelete="restrict"
    )
    after_stage_id = fields.Many2one(
        "project.task.type", required=True, readonly=True, ondelete="restrict"
    )
    before_state = fields.Char(required=True, readonly=True)
    after_state = fields.Char(required=True, readonly=True)
    before_version = fields.Integer(required=True, readonly=True)
    after_version = fields.Integer(required=True, readonly=True)
    applied_at = fields.Datetime(required=True, readonly=True)
    _semantic_once = models.Constraint(
        "UNIQUE(repository_id, provider_request_id, agile_key, effect_type)",
        "This PR/Task stage effect has already been consumed.",
    )

    @api.model_create_multi
    # Public callers cannot forge consumed effects; private append follows write.
    def create(self, vals_list):  # pylint: disable=method-required-super
        raise AccessError(
            _("Only an atomic authorized stage write consumes an effect.")
        )

    # Consumed effects are immutable tombstones.
    def write(self, values):  # pylint: disable=method-required-super
        raise ValidationError(_("Consumed effect evidence is immutable."))

    # Deletion would reopen an already consumed semantic effect.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Consumed effect tombstones are retained."))

    @api.model
    def _consumed(self, repository, provider_request_id, agile_key):
        """Private recovery check; marker survives manual moves and rule revisions."""
        return self.sudo().search(
            [
                ("repository_id", "=", repository.id),
                ("provider_request_id", "=", provider_request_id),
                ("agile_key", "=", agile_key),
                ("effect_type", "=", "task_stage_transition"),
            ],
            limit=1,
        )

    @api.model
    def _append(self, attempt, observation, task, before):
        """Call only after revalidation/write/postconditions in the same item
        savepoint.
        """
        if task.env.su or task.env.uid != attempt.activation_id.execution_user_id.id:
            raise AccessError(
                _("Consumed effects require the approved non-superuser actor.")
            )
        if (
            attempt.state != "processing"
            or task.stage_id != attempt.revision_id.target_stage_id
        ):
            raise ValidationError(_("A settled approved stage transition is required."))
        # Exclude caller defaults from the authorized effect receipt.
        # pylint: disable-next=context-overridden
        return super(ProjectGitPolicyEffect, self.sudo().with_context({})).create(
            {
                "repository_id": attempt.repository_id.id,
                "project_id": attempt.project_id.id,
                "company_id": attempt.company_id.id,
                "task_id": task.id,
                "agile_key": attempt.agile_key,
                "provider_request_id": attempt.provider_request_id,
                "effect_type": "task_stage_transition",
                "attempt_id": attempt.id,
                "activation_id": attempt.activation_id.id,
                "revision_id": attempt.revision_id.id,
                "observation_id": observation.id,
                "execution_user_id": task.env.uid,
                "before_stage_id": before["stage_id"],
                "after_stage_id": task.stage_id.id,
                "before_state": before["state"],
                "after_state": task.state,
                "before_version": before["version"],
                "after_version": task.git_policy_transition_version,
                "applied_at": fields.Datetime.now(),
            }
        )
