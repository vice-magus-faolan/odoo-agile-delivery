"""Authenticated native portal adapters for issued customer bytes only."""

from werkzeug.exceptions import BadRequest, NotFound

from odoo import http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager


class SolutionPortal(CustomerPortal):
    @http.route(
        ["/my/solution-documents", "/my/solution-documents/page/<int:page>"],
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
    )
    def solution_documents(self, page=1, **kw):
        if kw or page < 1:
            raise BadRequest()
        model = request.env["project.agile.solution.portal.publication"]
        navigation = pager(
            url="/my/solution-documents",
            total=model.search_count([]),
            page=page,
            step=20,
        )
        return request.render(
            "project_agile_solution.portal_solution_list",
            {
                "publications": model.search([], limit=20, offset=navigation["offset"]),
                "pager": navigation,
                "page_name": "solution_documents",
            },
        )

    def _publication(self, publication_id):
        row = request.env["project.agile.solution.portal.publication"].search(
            [("id", "=", publication_id)], limit=1
        )
        if not row:
            raise NotFound()
        return row

    @http.route(
        "/my/solution-documents/<int:publication_id>",
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
    )
    def solution_document(self, publication_id, **kw):
        if kw:
            raise BadRequest()
        row = self._publication(publication_id)
        return request.render(
            "project_agile_solution.portal_solution_document",
            {
                "publication": row,
                "view": row.action_view(),
                "download": False,
                "page_name": "solution_documents",
            },
        )

    @http.route(
        "/my/solution-documents/<int:publication_id>/download",
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
    )
    def solution_download(self, publication_id, **kw):
        if kw:
            raise BadRequest()
        row = self._publication(publication_id)
        return request.render(
            "project_agile_solution.portal_solution_document",
            {
                "publication": row,
                "view": row.action_view(),
                "download": True,
                "page_name": "solution_documents",
            },
            headers=[("Content-Disposition", "attachment; filename=solution.html")],
        )

    @http.route(
        "/my/solution-documents/<int:publication_id>/decision",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def solution_decision(self, publication_id, **kw):
        allowed = {
            "kind",
            "decision",
            "expected_event_id",
            "comment",
            "key",
            "number",
            "criteria_evaluated",
            "evidence",
        }
        if set(kw) - allowed:
            raise BadRequest()
        row = self._publication(publication_id)
        try:
            previous = kw.get("expected_event_id", "")
            previous = int(previous) if previous else False
            if kw.get("kind") == "document":
                if set(kw) - {"kind", "decision", "expected_event_id", "comment"}:
                    raise BadRequest()
                row.action_decide_document(
                    kw.get("decision"), previous, kw.get("comment", "")
                )
            elif kw.get("kind") == "requirement":
                if "comment" in kw:
                    raise BadRequest()
                row.action_decide_requirement(
                    kw.get("key"),
                    int(kw.get("number", "")),
                    kw.get("decision"),
                    kw.get("criteria_evaluated"),
                    kw.get("evidence"),
                    previous,
                )
            else:
                raise BadRequest()
        except (AccessError, MissingError) as error:
            raise NotFound() from error
        except (ValidationError, ValueError, TypeError) as error:
            raise BadRequest(
                "Decision unavailable or stale. Reload the publication."
            ) from error
        return request.redirect(f"/my/solution-documents/{row.id}", code=303)
