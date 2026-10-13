"""Live Project visibility: never cache visible record IDs inside an ir.rule domain."""

from functools import partial

from odoo import _, api, models
from odoo.exceptions import AccessError
from odoo.fields import Domain


class ProjectGitPolicyScope(models.AbstractModel):
    _name = "project.git.policy.scope"
    _description = "Current Project Policy Visibility"

    @api.model
    def _search(
        self,
        domain,
        offset=0,
        limit=None,
        order=None,
        *,
        active_test=True,
        bypass_access=False,
    ):
        if not self.env.su and not bypass_access:
            # The lazy query is rebuilt under the caller's selected companies and
            # native/custom Project rules for every search/count/group/export.
            projects = self.env["project.project"]._search([], active_test=False)
            domain = Domain(domain) & Domain("project_id", "in", projects)
        return super()._search(
            domain,
            offset,
            limit,
            order,
            active_test=active_test,
            bypass_access=bypass_access,
        )

    def _check_access(self, operation):
        denied = super()._check_access(operation)
        if denied or not self or self.env.su:
            return denied
        # search uses the live query above; empty-model ACL checks do not recurse.
        forbidden = self - self.with_context(active_test=False).search(
            [("id", "in", self.ids)]
        )
        if forbidden:
            return forbidden, partial(
                AccessError, _("Policy records require current Project visibility.")
            )
        return None
