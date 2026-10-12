"""Provider-neutral Git facts; provider ingress and workflow policy stay separate."""

from urllib.parse import unquote, urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

_PROVIDER_SELECTION = [
    ("github", "GitHub"),
    ("gitlab", "GitLab"),
    ("bitbucket", "Bitbucket"),
]

_PROVIDER_HOSTS = {
    "github": "github.com",
    "gitlab": "gitlab.com",
    "bitbucket": "bitbucket.org",
}


def _parse_https_url(value, label):
    """Return a canonical public HTTPS URL or reject ambiguous navigation targets."""

    if not isinstance(value, str):
        raise ValidationError(_("The %(label)s must be an HTTPS URL.", label=label))
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ValidationError(
            _("The %(label)s must be an HTTPS URL.", label=label)
        ) from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValidationError(_("The %(label)s must be an HTTPS URL.", label=label))
    return parsed


def _has_unsafe_url_path_component(path):
    """Return whether a URL path contains a literal or encoded traversal component."""

    for component in path.split("/"):
        decoded = unquote(component)
        if decoded in {".", ".."} or "/" in decoded or "\\" in decoded:
            return True
    return False


def _validate_repository_url(provider, canonical_url):
    """Validate the provider-owned canonical repository URL used for all fact links."""

    parsed = _parse_https_url(canonical_url, "canonical repository URL")
    expected_host = _PROVIDER_HOSTS.get(provider)
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        not expected_host
        or parsed.hostname.lower() != expected_host
        or len(path_parts) < 2
        or _has_unsafe_url_path_component(parsed.path)
    ):
        raise ValidationError(
            _(
                "The canonical repository URL must use the supported host "
                "for its provider."
            )
        )
    return parsed


def _validate_fact_url(repository, value):
    """Require fact links to stay under the configured repository's validated URL."""

    if not value:
        return
    canonical = _validate_repository_url(repository.provider, repository.canonical_url)
    parsed = _parse_https_url(value, "fact URL")
    root_path = canonical.path.rstrip("/")
    if (
        parsed.hostname.lower() != canonical.hostname.lower()
        or not (parsed.path == root_path or parsed.path.startswith(root_path + "/"))
        or _has_unsafe_url_path_component(parsed.path)
    ):
        raise ValidationError(
            _("The fact URL must stay within its configured repository.")
        )


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
        "project.project",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, index=True
    )
    active = fields.Boolean(default=True)
    git_delivery_ids = fields.One2many(
        "project.git.delivery", "repository_id", readonly=True
    )
    git_branch_ids = fields.One2many(
        "project.git.branch", "repository_id", readonly=True
    )
    git_commit_ids = fields.One2many(
        "project.git.commit", "repository_id", readonly=True
    )
    git_pull_request_ids = fields.One2many(
        "project.git.pull.request", "repository_id", readonly=True
    )
    git_check_ids = fields.One2many("project.git.check", "repository_id", readonly=True)
    git_delivery_count = fields.Integer(
        compute="_compute_git_fact_counts",
        groups="project.group_project_manager",
    )
    git_branch_count = fields.Integer(compute="_compute_git_fact_counts")
    git_commit_count = fields.Integer(compute="_compute_git_fact_counts")
    git_pull_request_count = fields.Integer(compute="_compute_git_fact_counts")
    git_check_count = fields.Integer(compute="_compute_git_fact_counts")
    webhook_secret = fields.Char(
        copy=False,
        groups="base.group_system",
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

    @api.depends(
        "git_delivery_ids",
        "git_branch_ids",
        "git_commit_ids",
        "git_pull_request_ids",
        "git_check_ids",
    )
    def _compute_git_fact_counts(self):
        """Compute visible fact counts in one grouped query per fact type."""

        count_specs = (
            ("git_delivery_count", "project.git.delivery"),
            ("git_branch_count", "project.git.branch"),
            ("git_commit_count", "project.git.commit"),
            ("git_pull_request_count", "project.git.pull.request"),
            ("git_check_count", "project.git.check"),
        )
        for repository in self:
            for field_name, _model_name in count_specs:
                repository[field_name] = 0
        for field_name, model_name in count_specs:
            rows = self.env[model_name]._read_group(
                [("repository_id", "in", self.ids)], ["repository_id"], ["__count"]
            )
            for repository, count in rows:
                repository[field_name] = count

    @api.constrains("provider", "canonical_url")
    def _check_canonical_url(self):
        for repository in self:
            repository._validated_canonical_url()

    def _validated_canonical_url(self):
        """Return this repository's safe public URL for a provider adapter's
        fact links.
        """

        self.ensure_one()
        return _validate_repository_url(self.provider, self.canonical_url)

    def _action_open_git_records(self, action_xml_id):
        """Return a standard fact action limited to this readable repository."""

        self.ensure_one()
        self.check_access("read")
        action = self.env["ir.actions.actions"]._for_xml_id(action_xml_id)
        action["domain"] = [("repository_id", "=", self.id)]
        action["context"] = {"default_repository_id": self.id}
        return action

    def action_open_git_deliveries(self):
        if not self.env.user.has_group("project.group_project_manager"):
            raise AccessError(_("Only Project Managers can inspect Git deliveries."))
        return self._action_open_git_records(
            "project_agile_git.action_project_git_delivery"
        )

    def action_open_git_branches(self):
        return self._action_open_git_records(
            "project_agile_git.action_project_git_branch"
        )

    def action_open_git_commits(self):
        return self._action_open_git_records(
            "project_agile_git.action_project_git_commit"
        )

    def action_open_git_pull_requests(self):
        return self._action_open_git_records(
            "project_agile_git.action_project_git_pull_request"
        )

    def action_open_git_checks(self):
        return self._action_open_git_records(
            "project_agile_git.action_project_git_check"
        )

    @api.constrains("project_id")
    def _check_agile_project(self):
        for repository in self:
            if not repository.project_id.agile_enabled:
                raise ValidationError(
                    _("Git repositories require an Agile-enabled project.")
                )


class ProjectGitDelivery(models.Model):
    """A durable authenticated provider delivery, not a synchronous work item."""

    _name = "project.git.delivery"
    _description = "Git Delivery"
    _check_company_auto = True
    _order = "received_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True, index=True
    )
    provider = fields.Selection(
        related="repository_id.provider", store=True, readonly=True
    )
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
    received_at = fields.Datetime(
        default=fields.Datetime.now, required=True, readonly=True, index=True
    )
    processed_at = fields.Datetime(readonly=True, copy=False, index=True)
    replay_mismatch_count = fields.Integer(default=0, readonly=True, copy=False)
    last_replay_mismatch_at = fields.Datetime(readonly=True, copy=False, index=True)

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
        "project.git.repository",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True
    )
    provider_branch_id = fields.Char(readonly=True, copy=False, index=True)
    name = fields.Char(required=True, index=True)
    head_sha = fields.Char(index=True)
    url = fields.Char()
    source_updated_at = fields.Datetime(readonly=True, index=True)
    last_seen_at = fields.Datetime(readonly=True, index=True)
    provenance_delivery_id = fields.Many2one(
        "project.git.delivery", readonly=True, ondelete="restrict", index=True
    )
    ordering_state = fields.Selection(
        [("known", "Known"), ("stale", "Stale"), ("ambiguous", "Ambiguous")],
        required=True,
        default="ambiguous",
        readonly=True,
        index=True,
    )

    _branch_unique = models.Constraint(
        "UNIQUE(repository_id, provider_branch_id)",
        "A provider branch observation can be recorded only once per repository.",
    )

    @api.constrains("repository_id", "url")
    def _check_external_url(self):
        for branch in self:
            _validate_fact_url(branch.repository_id, branch.url)


class ProjectGitCommit(models.Model):
    """An immutable commit identity with a bounded display excerpt."""

    _name = "project.git.commit"
    _description = "Git Commit"
    _check_company_auto = True
    _order = "authored_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True
    )
    sha = fields.Char(required=True, copy=False, index=True)
    message_excerpt = fields.Char(copy=False)
    authored_at = fields.Datetime(index=True)
    url = fields.Char()
    last_seen_at = fields.Datetime(readonly=True, index=True)
    provenance_delivery_id = fields.Many2one(
        "project.git.delivery", readonly=True, ondelete="restrict", index=True
    )

    _commit_unique = models.Constraint(
        "UNIQUE(repository_id, sha)",
        "A commit can be recorded only once per repository.",
    )

    @api.constrains("repository_id", "url")
    def _check_external_url(self):
        for commit in self:
            _validate_fact_url(commit.repository_id, commit.url)


class ProjectGitPullRequest(models.Model):
    """A normalized pull or merge request fact without workflow meaning."""

    _name = "project.git.pull.request"
    _description = "Git Pull Request"
    _check_company_auto = True
    _order = "updated_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True
    )
    provider_request_id = fields.Char(required=True, copy=False, index=True)
    number = fields.Char(index=True)
    title = fields.Char()
    state = fields.Selection(
        [
            ("open", "Open"),
            ("closed", "Closed"),
            ("merged", "Merged"),
            ("draft", "Draft"),
        ],
        index=True,
    )
    source_branch = fields.Char()
    target_branch = fields.Char()
    head_sha = fields.Char(index=True)
    url = fields.Char()
    merged_at = fields.Datetime(index=True)
    updated_at = fields.Datetime(index=True)
    last_seen_at = fields.Datetime(readonly=True, index=True)
    provenance_delivery_id = fields.Many2one(
        "project.git.delivery", readonly=True, ondelete="restrict", index=True
    )
    ordering_state = fields.Selection(
        [("known", "Known"), ("stale", "Stale"), ("ambiguous", "Ambiguous")],
        required=True,
        default="ambiguous",
        readonly=True,
        index=True,
    )

    _pull_request_unique = models.Constraint(
        "UNIQUE(repository_id, provider_request_id)",
        "A pull request can be recorded only once per repository.",
    )

    @api.constrains("repository_id", "url")
    def _check_external_url(self):
        for pull_request in self:
            _validate_fact_url(pull_request.repository_id, pull_request.url)


class ProjectGitCheck(models.Model):
    """A provider-neutral pipeline, status, or check result fact."""

    _name = "project.git.check"
    _description = "Git Check"
    _check_company_auto = True
    _order = "completed_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True
    )
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
    updated_at = fields.Datetime(index=True)
    last_seen_at = fields.Datetime(readonly=True, index=True)
    provenance_delivery_id = fields.Many2one(
        "project.git.delivery", readonly=True, ondelete="restrict", index=True
    )
    ordering_state = fields.Selection(
        [("known", "Known"), ("stale", "Stale"), ("ambiguous", "Ambiguous")],
        required=True,
        default="ambiguous",
        readonly=True,
        index=True,
    )

    _check_unique = models.Constraint(
        "UNIQUE(repository_id, provider_check_id)",
        "A check can be recorded only once per repository.",
    )

    @api.constrains("repository_id", "url")
    def _check_external_url(self):
        for check in self:
            _validate_fact_url(check.repository_id, check.url)


class ProjectGitAssociationAudit(models.Model):
    """An immutable audit fact for an explicit Agile-key association decision."""

    _name = "project.git.association.audit"
    _description = "Git Task Association Audit"
    _check_company_auto = True
    _order = "observed_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True
    )
    delivery_id = fields.Many2one(
        "project.git.delivery",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    task_id = fields.Many2one(
        "project.task", readonly=True, ondelete="restrict", check_company=True
    )
    source_type = fields.Selection(
        [
            ("branch", "Branch"),
            ("commit", "Commit"),
            ("pull_request", "Pull Request"),
            ("check", "Check"),
        ],
        required=True,
        readonly=True,
        copy=False,
    )
    source_provider_id = fields.Char(
        required=True, readonly=True, copy=False, index=True
    )
    source_field = fields.Char(required=True, readonly=True, copy=False)
    agile_key = fields.Char(required=True, readonly=True, copy=False, index=True)
    outcome = fields.Selection(
        [
            ("associated", "Associated"),
            ("already_associated", "Already Associated"),
            ("unassociated", "Unassociated"),
            ("rejected", "Rejected"),
        ],
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )
    reason = fields.Selection(
        [
            ("exact_key", "Exact Key"),
            ("duplicate", "Duplicate"),
            ("unknown_key", "Unknown Key"),
            ("wrong_project", "Wrong Project"),
            ("cross_company", "Cross Company"),
            ("archived_task", "Archived Task"),
            ("invalid_key", "Invalid Key"),
            ("too_many_keys", "Too Many Keys"),
        ],
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )
    observed_at = fields.Datetime(
        default=fields.Datetime.now, required=True, readonly=True, index=True
    )

    _audit_unique = models.Constraint(
        "UNIQUE(delivery_id, source_type, source_provider_id, source_field, agile_key)",
        "This Git association decision is already recorded for the delivery.",
    )

    # Audit facts are append-only; super would permit forbidden mutation.
    def write(self, values):  # pylint: disable=method-required-super
        raise ValidationError(_("Git association audit facts are immutable."))

    # Audit evidence must not be deleted, including through RPC.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Git association audit facts are immutable."))


class ProjectGitTaskAssociation(models.Model):
    """An immutable, repository-scoped association to one Agile task key."""

    _name = "project.git.task.association"
    _description = "Git Task Association"
    _check_company_auto = True
    _order = "matched_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True
    )
    task_id = fields.Many2one(
        "project.task",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    agile_key = fields.Char(required=True, readonly=True, copy=False, index=True)
    source_type = fields.Selection(
        [
            ("branch", "Branch"),
            ("commit", "Commit"),
            ("pull_request", "Pull Request"),
            ("check", "Check"),
        ],
        required=True,
        readonly=True,
        copy=False,
    )
    source_provider_id = fields.Char(
        required=True, readonly=True, copy=False, index=True
    )
    matched_at = fields.Datetime(
        default=fields.Datetime.now, required=True, readonly=True
    )

    _association_unique = models.Constraint(
        "UNIQUE(repository_id, task_id, source_type, source_provider_id)",
        "The Git fact is already associated with this task.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        values_list = [dict(values) for values in vals_list]
        repositories = self.env["project.git.repository"].browse(
            [
                values["repository_id"]
                for values in values_list
                if values.get("repository_id")
            ]
        )
        tasks = self.env["project.task"].browse(
            [values["task_id"] for values in values_list if values.get("task_id")]
        )
        for values in values_list:
            repository = repositories.browse(values.get("repository_id"))
            task = tasks.browse(values.get("task_id"))
            if not repository or not task or repository.project_id != task.project_id:
                raise ValidationError(
                    _("Git task associations must stay within the repository project.")
                )
            if not task.agile_key:
                raise ValidationError(
                    _("Git task associations require an immutable Agile key.")
                )
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

    # Association identity is retained evidence; super would delete it.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("An Agile key association is immutable."))
