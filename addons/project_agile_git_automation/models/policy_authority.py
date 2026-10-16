"""Fixed authority helpers; caller context and generic expressions are not policy."""

import hashlib
import json

from odoo import _
from odoo.exceptions import AccessError, ValidationError

CAPABILITY = "project_agile_git_automation.group_git_policy_manager"
MODES = [
    ("dry_run", "Dry Run"),
    ("apply", "Apply (Separate Operational Approval Required)"),
]
STAGE_SETTINGS = (
    "active",
    "project_ids",
    "user_id",
    "rating_active",
    "mail_template_id",
    "rating_template_id",
    "rating_status",
    "rating_status_period",
    "auto_validation_state",
    "sms_template_id",
)


def clean_context(env):
    """Preserve only validated caller company selection,
    never default/authority hints.
    """
    return {"allowed_company_ids": env.companies.ids}


def require_capability(env, emergency=False):
    """System administrators may shut down, never implicitly configure/activate."""
    user = env.user
    if emergency and user.has_group("base.group_system"):
        return
    if env.su or not user.active or user.share or not user.has_group(CAPABILITY):
        raise AccessError(_("Explicit Git Policy Manager capability is required."))


def reject_keys(values, allowed):
    if set(values) - set(allowed):
        raise ValidationError(
            _("Only finite policy configuration fields are accepted.")
        )


def exact_name(value, label, branch=False):
    """No trimming/repair: exact names are bounded literals,
    not wildcard expressions.
    """
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 255
        or value != value.strip()
    ):
        raise ValidationError(
            _("%(label)s must be an exact name of 1 to 255 characters.", label=label)
        )
    if any(ord(c) < 32 for c in value) or any(c in value for c in "*?[]"):
        raise ValidationError(
            _("Policy names cannot contain controls or wildcard selectors.")
        )
    if branch and any(c.isspace() for c in value):
        raise ValidationError(_("Target branch must be an exact branch name."))


def check_scope(repository, project=None, company=None, operation="write"):
    """Check actual current-user repository and Project records,
    including custom rules.
    """
    repository.ensure_one()
    repository.check_access(operation)
    repository.project_id.check_access(operation)
    current_project = repository.project_id
    current_company = current_project.company_id
    if (
        not repository.active
        or not current_project.active
        or not current_project.agile_enabled
    ):
        raise ValidationError(
            _("Policy requires an active Agile project and repository.")
        )
    if (
        not current_company
        or not current_company.active
        or current_company not in repository.env.companies
    ):
        raise AccessError(_("Policy requires a visible company-scoped project."))
    if (project and current_project != project) or (
        company and current_company != company
    ):
        raise ValidationError(_("Historical policy scope cannot be reassigned."))


def check_identity(user, repository, manager=False):
    """Re-resolve the persisted identity under an explicit clean
    single-company context.
    """
    user.ensure_one()
    if user.id == 1 or not user.active or user.share:
        raise AccessError(
            _("Policy identities must be active non-superuser internal users.")
        )
    if (
        repository.company_id.id
        not in user.with_context(active_test=False).company_ids.ids
    ):
        raise AccessError(_("Policy identity lacks the required company membership."))
    # Replace, do not merge: caller default/authority hints must not survive.
    scoped = repository.with_user(user).with_context(  # pylint: disable=context-overridden
        {"allowed_company_ids": repository.company_id.ids}
    )
    if manager:
        require_capability(scoped.env)
        check_scope(scoped)
    else:
        check_scope(scoped, operation="read")
    return scoped


def check_task_authority(user, repository, task=None):
    """Validate every concrete scoped Task, not merely an empty-model ACL.

    After the approver has repository/Project authority, a narrow Project/company
    ID-only enumeration includes records hidden from the proposed executor. IDs
    are never returned to callers; denial is generic. Empty projects fail closed.
    Apply repeats concrete Task checks before native writes and effect publication.
    """
    scoped = check_identity(user, repository)
    if task is None:
        tasks = (
            repository.env["project.task"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("project_id", "=", repository.project_id.id),
                    ("company_id", "=", repository.company_id.id),
                ]
            )
        )
    else:
        tasks = task
    if not tasks:
        raise AccessError(
            _("Activation requires concrete Project Task write authority.")
        )
    controlled = tasks.with_env(scoped.env)
    controlled.check_access("read")
    controlled.check_access("write")
    if any(
        t.project_id != scoped.project_id or t.company_id != scoped.company_id
        for t in controlled
    ):
        raise AccessError(
            _("Policy Task authority must stay within its approved scope.")
        )


def stage_fingerprint(revision):
    """Bounded snapshot of every relevant stage setting,
    including optional native SMS.
    """
    stages = revision.allowed_source_stage_ids | revision.target_stage_id
    stages.check_access("read")
    result = []
    for stage in stages.sorted("id"):
        if (
            not stage.active
            or stage.user_id
            or revision.project_id not in stage.project_ids
        ):
            raise ValidationError(
                _(
                    "Policy stages must be active, nonpersonal, "
                    "and linked to the project."
                )
            )
        row = {"id": stage.id}
        for name in STAGE_SETTINGS:
            if name in stage._fields:
                value = stage[name]
                row[name] = sorted(value.ids) if hasattr(value, "ids") else value
        result.append(row)
    target = revision.target_stage_id
    if (
        target.rating_active
        or target.mail_template_id
        or ("sms_template_id" in target._fields and target.sms_template_id)
    ):
        raise ValidationError(
            _("Policy target stages cannot have rating, email, or SMS effects.")
        )
    return hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
