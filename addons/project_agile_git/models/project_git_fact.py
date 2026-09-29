"""Provider-neutral Git facts; provider ingress and workflow policy stay separate."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_PROVIDER_SELECTION = [
    ("github", "GitHub"),
    ("gitlab", "GitLab"),
    ("bitbucket", "Bitbucket"),
]


class ProjectGitRepository(models.Model):
    """A provider repository scoped to one Agile project and company."""

    _name = "project.git.repository"
    _description = "Git Repository"
    _check_company_auto = True
    _order = "project_id, name, id"

    name = fields.Char(required=True)
    provider = fields.Selection(_PROVIDER_SELECTION, required=True, index=True)
    provider_repository_id = fields.Char(required=True, copy=False, index=True)
    canonical_url = fields.Char(required=True)
    project_id = fields.Many2one(
        "project.project", required=True, ondelete="restrict", index=True, check_company=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, index=True
    )
    active = fields.Boolean(default=True)
    webhook_secret = fields.Char(
        copy=False,
        groups="base.group_system",
        password=True,
        help="Ingress-only secret. It is never exposed to ordinary project users.",
    )
    webhook_secret_fingerprint = fields.Char(readonly=True, copy=False)
    retention_policy = fields.Selection(
        [("digest_only", "Digest Only"), ("redacted_excerpt", "Redacted Excerpt")],
        required=True,
        default="digest_only",
    )

    _provider_repository_unique = models.Constraint(
        "UNIQUE(provider, provider_repository_id)",
        "A provider repository can be configured only once.",
    )

    @api.constrains("project_id")
    def _check_agile_project(self):
        for repository in self:
            if not repository.project_id.agile_enabled:
                raise ValidationError(_("Git repositories require an Agile-enabled project."))


class ProjectGitDelivery(models.Model):
    """A durable authenticated provider delivery, not a synchronous work item."""

    _name = "project.git.delivery"
    _description = "Git Delivery"
    _check_company_auto = True
    _order = "received_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository", required=True, ondelete="restrict", index=True, check_company=True
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True, index=True
    )
    provider = fields.Selection(related="repository_id.provider", store=True, readonly=True)
    provider_delivery_id = fields.Char(required=True, copy=False, index=True)
    event_type = fields.Char(required=True, index=True)
    payload_sha256 = fields.Char(required=True, readonly=True, copy=False, index=True)
    payload_size = fields.Integer(required=True, readonly=True, copy=False)
    retained_payload = fields.Text(groups="base.group_system", copy=False)
    retained_until = fields.Datetime(readonly=True, copy=False, index=True)
    state = fields.Selection(
        [
            ("received", "Received"),
            ("queued", "Queued"),
            ("processing", "Processing"),
            ("retryable", "Retryable"),
            ("failed", "Failed"),
            ("processed", "Processed"),
            ("discarded", "Discarded"),
        ],
        required=True,
        default="received",
        copy=False,
        index=True,
    )
    attempt_count = fields.Integer(default=0, readonly=True, copy=False)
    next_retry_at = fields.Datetime(readonly=True, copy=False, index=True)
    lease_token = fields.Char(readonly=True, copy=False, index=True)
    lease_expires_at = fields.Datetime(readonly=True, copy=False, index=True)
    error_summary = fields.Char(readonly=True, copy=False)
    last_error_at = fields.Datetime(readonly=True, copy=False, index=True)
    received_at = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True, index=True)
    processed_at = fields.Datetime(readonly=True, copy=False, index=True)

    _delivery_unique = models.Constraint(
        "UNIQUE(repository_id, provider_delivery_id)",
        "This provider delivery has already been received for the repository.",
    )


class ProjectGitBranch(models.Model):
    """A provider-neutral repository branch fact."""

    _name = "project.git.branch"
    _description = "Git Branch"
    _check_company_auto = True
    _order = "repository_id, name, id"

    repository_id = fields.Many2one(
        "project.git.repository", required=True, ondelete="cascade", index=True, check_company=True
    )
    company_id = fields.Many2one(related="repository_id.company_id", store=True, readonly=True)
    name = fields.Char(required=True, index=True)
    head_sha = fields.Char(index=True)
    url = fields.Char()

    _branch_unique = models.Constraint(
        "UNIQUE(repository_id, name)", "A branch can be recorded only once per repository."
    )


class ProjectGitCommit(models.Model):
    """An immutable commit identity with a bounded display excerpt."""

    _name = "project.git.commit"
    _description = "Git Commit"
    _check_company_auto = True
    _order = "authored_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository", required=True, ondelete="cascade", index=True, check_company=True
    )
    company_id = fields.Many2one(related="repository_id.company_id", store=True, readonly=True)
    sha = fields.Char(required=True, copy=False, index=True)
    message_excerpt = fields.Char(copy=False)
    authored_at = fields.Datetime(index=True)
    url = fields.Char()

    _commit_unique = models.Constraint(
        "UNIQUE(repository_id, sha)", "A commit can be recorded only once per repository."
    )


class ProjectGitPullRequest(models.Model):
    """A normalized pull or merge request fact without workflow meaning."""

    _name = "project.git.pull.request"
    _description = "Git Pull Request"
    _check_company_auto = True
    _order = "updated_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository", required=True, ondelete="cascade", index=True, check_company=True
    )
    company_id = fields.Many2one(related="repository_id.company_id", store=True, readonly=True)
    provider_request_id = fields.Char(required=True, copy=False, index=True)
    number = fields.Char(index=True)
    title = fields.Char()
    state = fields.Selection(
        [("open", "Open"), ("closed", "Closed"), ("merged", "Merged"), ("draft", "Draft")],
        index=True,
    )
    source_branch = fields.Char()
    target_branch = fields.Char()
    head_sha = fields.Char(index=True)
    url = fields.Char()
    merged_at = fields.Datetime(index=True)
    updated_at = fields.Datetime(index=True)

    _pull_request_unique = models.Constraint(
        "UNIQUE(repository_id, provider_request_id)",
        "A pull request can be recorded only once per repository.",
    )


class ProjectGitCheck(models.Model):
    """A provider-neutral pipeline, status, or check result fact."""

    _name = "project.git.check"
    _description = "Git Check"
    _check_company_auto = True
    _order = "completed_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository", required=True, ondelete="cascade", index=True, check_company=True
    )
    company_id = fields.Many2one(related="repository_id.company_id", store=True, readonly=True)
    provider_check_id = fields.Char(required=True, copy=False, index=True)
    name = fields.Char(required=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("running", "Running"),
            ("success", "Success"),
            ("failure", "Failure"),
            ("cancelled", "Cancelled"),
            ("neutral", "Neutral"),
            ("unknown", "Unknown"),
        ],
        required=True,
        default="unknown",
        index=True,
    )
    head_sha = fields.Char(index=True)
    url = fields.Char()
    completed_at = fields.Datetime(index=True)

    _check_unique = models.Constraint(
        "UNIQUE(repository_id, provider_check_id)",
        "A check can be recorded only once per repository.",
    )


class ProjectGitTaskAssociation(models.Model):
    """An immutable, repository-scoped association to one Agile task key."""

    _name = "project.git.task.association"
    _description = "Git Task Association"
    _check_company_auto = True
    _order = "matched_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository", required=True, ondelete="cascade", index=True, check_company=True
    )
    company_id = fields.Many2one(related="repository_id.company_id", store=True, readonly=True)
    task_id = fields.Many2one(
        "project.task", required=True, ondelete="restrict", index=True, check_company=True
    )
    agile_key = fields.Char(required=True, readonly=True, copy=False, index=True)
    source_type = fields.Selection(
        [("branch", "Branch"), ("commit", "Commit"), ("pull_request", "Pull Request"), ("check", "Check")],
        required=True,
        readonly=True,
        copy=False,
    )
    source_provider_id = fields.Char(required=True, readonly=True, copy=False, index=True)
    matched_at = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)

    _association_unique = models.Constraint(
        "UNIQUE(repository_id, task_id, source_type, source_provider_id)",
        "The Git fact is already associated with this task.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        values_list = [dict(values) for values in vals_list]
        repositories = self.env["project.git.repository"].browse(
            [values["repository_id"] for values in values_list if values.get("repository_id")]
        )
        tasks = self.env["project.task"].browse(
            [values["task_id"] for values in values_list if values.get("task_id")]
        )
        for values in values_list:
            repository = repositories.browse(values.get("repository_id"))
            task = tasks.browse(values.get("task_id"))
            if not repository or not task or repository.project_id != task.project_id:
                raise ValidationError(_("Git task associations must stay within the repository project."))
            if not task.agile_key:
                raise ValidationError(_("Git task associations require an immutable Agile key."))
            values["agile_key"] = task.agile_key
        return super().create(values_list)

    def write(self, values):
        immutable_fields = {
            "repository_id",
            "task_id",
            "agile_key",
            "source_type",
            "source_provider_id",
            "matched_at",
        }
        if immutable_fields.intersection(values):
            raise ValidationError(_("An Agile key association is immutable."))
        return super().write(values)

    def unlink(self):
        raise ValidationError(_("An Agile key association is immutable."))
