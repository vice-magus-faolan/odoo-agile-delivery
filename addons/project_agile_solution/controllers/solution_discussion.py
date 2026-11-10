"""Preserve native self-unfollow without serializing a revoked source."""

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.mail.controllers.mail import MailController
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store

from ..models.solution_discussion import DISCUSSION_MODELS, source_readable


class SolutionDiscussionController(ThreadController):
    @http.route()
    def mail_thread_unsubscribe(self, res_model, res_id, partner_ids):
        thread = request.env[res_model].browse(res_id)
        if res_model not in DISCUSSION_MODELS or source_readable(thread):
            return super().mail_thread_unsubscribe(res_model, res_id, partner_ids)
        # The model retains native internal-self-only authorization. Do not
        # follow this write with native source-derived recipient serialization.
        thread.message_unsubscribe(partner_ids)
        if not partner_ids:
            return {}
        return (
            Store()
            .add(
                thread,
                {"selfFollower": Store.One(request.env["mail.followers"])},
                as_thread=True,
            )
            .get_result()
        )


class SolutionDiscussionMailController(MailController):
    @http.route()
    def mail_action_unfollow(self, model, res_id, pid, token, **kwargs):
        # A signed removal link grants no access to the native sudo-rendered name.
        if model in DISCUSSION_MODELS and not source_readable(
            request.env[model].browse(int(res_id))
        ):
            raise AccessError(_("Current Solution source access is required."))
        return super().mail_action_unfollow(model, res_id, pid, token, **kwargs)
