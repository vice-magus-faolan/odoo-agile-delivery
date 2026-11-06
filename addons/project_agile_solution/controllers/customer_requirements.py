"""Extend native Task pages; never establish a parallel Task portal."""

from werkzeug.exceptions import BadRequest, NotFound

from odoo import http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class CustomerRequirementPortal(ProjectCustomerPortal):
    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        values["solution_customer_requirements"] = []
        caller = task.with_env(request.env).sudo(False)
        try:
            cards = caller.action_customer_requirements()
        except (AccessError, MissingError):
            # Native token/public Task access is not a requirement disclosure grant.
            return values
        try:
            selected = int(kwargs.get("solution_link", "0"))
            before = int(kwargs.get("solution_before", "0"))
        except (ValueError, TypeError) as error:
            raise BadRequest() from error
        if selected < 0 or before < 0 or bool(selected) != bool(before):
            raise BadRequest()
        if selected and selected not in {card["link_id"] for card in cards}:
            raise BadRequest()
        for card in cards:
            card["discussion"] = caller.action_customer_requirement_discussion(
                card["link_id"],
                before if card["link_id"] == selected and before else False,
            )
        values["solution_customer_requirements"] = cards
        return values

    @http.route(
        "/my/tasks/<int:task_id>/requirement-comment",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def post_customer_requirement(self, task_id, **kw):
        if set(kw) - {"link_id", "body"}:
            raise BadRequest()
        try:
            request.env["project.task"].browse(
                task_id
            ).action_post_customer_requirement(
                int(kw.get("link_id", "")), kw.get("body", "")
            )
        except (AccessError, MissingError) as error:
            raise NotFound() from error
        except (ValueError, TypeError, ValidationError) as error:
            raise BadRequest() from error
        return request.redirect(f"/my/tasks/{task_id}#solution_requirements", code=303)
