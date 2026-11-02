"""Native stable-identity discussions, bounded by current source authority."""

from odoo import _, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain

DISCUSSION_MODELS = (
    "project.agile.requirement",
    "project.agile.solution.document",
    "project.agile.solution.context",
)


def source_access_domain(env, model_field, source_models=DISCUSSION_MODELS):
    """Keep native mail exceptions from becoming a Solution access grant."""
    unrelated = Domain(model_field, "not in", source_models)
    caller = env(su=False)
    if not caller.user.active or not caller.user._is_internal():
        return unrelated
    return Domain.OR(
        [
            unrelated,
            *(
                Domain.AND(
                    [
                        Domain(model_field, "=", model),
                        Domain(
                            "res_id",
                            "in",
                            caller[model].with_context(active_test=False)._search([]),
                        ),
                    ]
                )
                for model in source_models
                if caller["ir.model.access"].check(model, "read", False)
            ),
        ]
    )


def source_readable(records):
    """Use an actual caller search, not cached computed access predicates."""
    caller = records.sudo(False).with_context(active_test=False)
    if not caller.env.user.active or not caller.env.user._is_internal():
        return caller.browse()
    if not caller.env["ir.model.access"].check(caller._name, "read", False):
        return caller.browse()
    return caller.search([("id", "in", caller.ids)])


def forbidden_source_rows(records, model_field, source_models=DISCUSSION_MODELS):
    """Constrain native mail exceptions using current concrete source access."""
    forbidden = records.browse()
    for model, rows in records.sudo().grouped(model_field).items():
        if model in source_models:
            sources = records.env[model].browse(rows.mapped("res_id"))
            allowed = set(source_readable(sources).ids)
            forbidden |= records.browse(
                row.id for row in rows if row.res_id not in allowed
            )
    return forbidden


def source_access_result(records, model_field, result, source_models=DISCUSSION_MODELS):
    """Intersect concrete source authority with native record restrictions."""
    if records.env.su:
        return result
    forbidden = forbidden_source_rows(records, model_field, source_models)
    if not forbidden:
        return result
    if result:
        return (result[0] | forbidden, result[1])
    return (
        forbidden,
        lambda: AccessError(_("Current Solution source access is required.")),
    )


def check_source_target(env, model, record_id):
    """Relocating a native mail row also requires destination authority."""
    if model in DISCUSSION_MODELS and not source_readable(env[model].browse(record_id)):
        raise AccessError(_("Current Solution source access is required."))


class SolutionDiscussion(models.AbstractModel):
    _name = "project.agile.solution.discussion"
    _inherit = "mail.thread"
    _description = "Source-authorized Stable Solution Discussion"
    _mail_post_access = "read"

    def message_post(self, **kwargs):
        if len(source_readable(self)) != len(self):
            raise AccessError(_("Current Solution source access is required."))
        return super().message_post(**kwargs)

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        if len(source_readable(self)) != len(self):
            raise AccessError(_("Current Solution source access is required."))
        return super().message_subscribe(partner_ids, subtype_ids)

    def message_unsubscribe(self, partner_ids=None):
        # Native self-unfollow skips source access; Solution operations do not.
        if len(source_readable(self)) != len(self):
            raise AccessError(_("Current Solution source access is required."))
        return super().message_unsubscribe(partner_ids)

    def _get_thread_with_access(self, thread_id, *, mode="read", **kwargs):
        if not source_readable(self.browse(thread_id)):
            raise AccessError(_("Current Solution source access is required."))
        # Preserve native write-to-read fallback for read-authorized posting.
        return super()._get_thread_with_access(thread_id, mode=mode, **kwargs)

    def _discussion_recipient_allowed(self, partner_id):
        """A follower/mention cannot disclose source content to an outsider."""
        users = self.env["res.partner"].sudo().browse(partner_id).user_ids
        users = users.filtered("active")
        return bool(users) and all(
            not user.share
            and bool(
                source_readable(
                    self.with_user(user).with_context(
                        allowed_company_ids=user.company_ids.ids
                    )
                )
            )
            for user in users
        )

    def _notify_get_recipients(self, message, msg_vals=False, **kwargs):
        recipients = super()._notify_get_recipients(message, msg_vals, **kwargs)
        return [
            recipient
            for recipient in recipients
            if recipient["id"] and self._discussion_recipient_allowed(recipient["id"])
        ]


class SolutionDiscussionMessage(models.Model):
    _inherit = "mail.message"

    # SQL search projection only. Record authorization below independently searches
    # the source: native filtered_domain can evaluate this cached value in Python.
    solution_source_access = fields.Boolean(
        compute="_compute_solution_source_access",
        search="_search_solution_source_access",
    )

    def _compute_solution_source_access(self):
        for row in self:
            row.solution_source_access = True

    def _search_solution_source_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        allowed = source_access_domain(self.env, "model")
        positive = Domain.OR(allowed if item is True else ~allowed for item in value)
        return positive if operator == "in" else ~positive

    def _message_fetch(self, domain, **kwargs):
        # Native HTTP fetch may elevate after its thread check. Keep source
        # visibility in the fetch query itself, including unscoped inbox fetches.
        domain = Domain(True if domain is None else domain)
        domain &= source_access_domain(self.env, "model")
        return super()._message_fetch(domain, **kwargs)

    def _get_forbidden_access(self, operation):
        return super()._get_forbidden_access(operation) | forbidden_source_rows(
            self, "model"
        )

    def write(self, values):
        if not self.env.su and {"model", "res_id"} & values.keys():
            for row in self:
                check_source_target(
                    self.env,
                    values.get("model", row.model),
                    values.get("res_id", row.res_id),
                )
        return super().write(values)

    def fetch(self, field_names=None):
        # Native mail fetch deliberately sudoes; protect direct field ORM reads too.
        if not self.env.su:
            protected = (
                self.sudo()
                .filtered(lambda row: row.model in DISCUSSION_MODELS)
                .sudo(False)
            )
            protected.check_access("read")
        return super().fetch(field_names)


class SolutionDiscussionFollowers(models.Model):
    _inherit = "mail.followers"

    solution_source_access = fields.Boolean(
        compute="_compute_solution_source_access",
        search="_search_solution_source_access",
    )

    def _compute_solution_source_access(self):
        for row in self:
            row.solution_source_access = True

    def _search_solution_source_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        allowed = source_access_domain(self.env, "res_model")
        positive = Domain.OR(allowed if item is True else ~allowed for item in value)
        return positive if operator == "in" else ~positive

    def _check_access(self, operation):
        return source_access_result(self, "res_model", super()._check_access(operation))

    def read(self, fields=None, load="_classic_read"):
        self.check_access("read")
        return super().read(fields, load=load)

    def write(self, values):
        if not self.env.su and {"res_model", "res_id"} & values.keys():
            for row in self:
                check_source_target(
                    self.env,
                    values.get("res_model", row.res_model),
                    values.get("res_id", row.res_id),
                )
        return super().write(values)


# Composer attachments move to the scheduled row before they move to its thread.
ATTACHMENT_SOURCE_MODELS = (*DISCUSSION_MODELS, "mail.scheduled.message")


class SolutionDiscussionAttachment(models.Model):
    _inherit = "ir.attachment"

    def _search(
        self, domain, offset=0, limit=None, order=None, *, bypass_access=False, **kwargs
    ):
        if not self.env.su and not bypass_access:
            domain = Domain(domain) & source_access_domain(
                self.env, "res_model", ATTACHMENT_SOURCE_MODELS
            )
        return super()._search(
            domain, offset, limit, order, bypass_access=bypass_access, **kwargs
        )

    def _check_access(self, operation):
        # Native public/creator exceptions must not become a source grant.
        return source_access_result(
            self,
            "res_model",
            super()._check_access(operation),
            ATTACHMENT_SOURCE_MODELS,
        )


class SolutionDiscussionScheduledMessage(models.Model):
    _inherit = "mail.scheduled.message"

    def _search(
        self, domain, offset=0, limit=None, order=None, *, bypass_access=False, **kwargs
    ):
        if not self.env.su and not bypass_access:
            domain = Domain(domain) & source_access_domain(self.env, "model")
        return super()._search(
            domain, offset, limit, order, bypass_access=bypass_access, **kwargs
        )

    def _check_access(self, operation):
        return source_access_result(self, "model", super()._check_access(operation))


class SolutionDiscussionBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record(
        self,
        xmlid=None,
        res_model="ir.attachment",
        res_id=None,
        access_token=None,
        field=None,
    ):
        record = super()._find_record(xmlid, res_model, res_id, access_token, field)
        # Native public and both token routes can return an elevated attachment.
        # Rebind to the request caller before resolving its current source access.
        if record._name == "ir.attachment" and forbidden_source_rows(
            record.with_env(self.env), "res_model", ATTACHMENT_SOURCE_MODELS
        ):
            raise AccessError(_("Current Solution source access is required."))
        return record
