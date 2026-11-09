"""Revoke released grants in native access mutations, never grant authority."""

from odoo import models


def revoke_publications(env, domain):
    """After native authorization, conflict on the same rows decisions write."""
    if not env.registry.ready:
        module = (
            env["ir.module.module"]
            .sudo()
            .search(
                [
                    ("name", "=", "project_agile_solution"),
                ],
                limit=1,
            )
        )
        if module.state not in ("installed", "to upgrade"):
            # Native initial construction/owned uninstall has no live grant table.
            return
    env["project.agile.solution.portal.publication"].sudo().search(
        [("revoked_at", "=", False)] + domain
    )._revoke()


class SolutionPortalFollowers(models.Model):
    # Grant revocation is separate from discussion and publication locking.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "mail.followers"

    def _publication_scopes(self):
        return [
            [("project_id", "=", row.res_id), ("partner_id", "=", row.partner_id.id)]
            for row in self.sudo().filtered(
                lambda item: item.res_model == "project.project"
            )
        ]

    def write(self, values):
        scopes = (
            self._publication_scopes()
            if {"res_model", "res_id", "partner_id"} & values.keys()
            else []
        )
        result = super().write(values)
        for domain in scopes:
            revoke_publications(self.env, domain)
        return result

    def unlink(self):
        scopes = self._publication_scopes()
        result = super().unlink()
        for domain in scopes:
            revoke_publications(self.env, domain)
        return result


class SolutionPortalUsers(models.Model):
    _inherit = "res.users"

    def _publication_portal_eligibility(self):
        """Snapshot native recipient eligibility, not incidental access groups."""
        # Read native fields without warming has_group's registry-wide user cache
        # with membership that an enclosing savepoint may subsequently roll back.
        portal = self.env.ref("base.group_portal")
        return {
            user.id: (portal in user.all_group_ids, user.share) for user in self.sudo()
        }

    def _revoke_changed_portal_eligibility(self, before):
        after = self._publication_portal_eligibility()
        changed = [user_id for user_id in before if before[user_id] != after[user_id]]
        if changed:
            revoke_publications(self.env, [("recipient_id", "in", changed)])

    def write(self, values):
        before = (
            self._publication_portal_eligibility()
            if {"group_ids", "all_group_ids", "share", "role"} & values.keys()
            else {}
        )
        result = super().write(values)
        if {
            "active",
            "partner_id",
            "company_id",
            "company_ids",
        } & values.keys():
            revoke_publications(self.env, [("recipient_id", "in", self.ids)])
        elif before:
            self._revoke_changed_portal_eligibility(before)
        return result


class SolutionPortalPartners(models.Model):
    _inherit = "res.partner"

    def write(self, values):
        result = super().write(values)
        if {"active", "parent_id", "company_id", "user_ids"} & values.keys():
            revoke_publications(self.env, [("partner_id", "in", self.ids)])
        return result


class SolutionPortalGroups(models.Model):
    _inherit = "res.groups"

    def write(self, values):
        relevant = {
            "user_ids",
            "all_user_ids",
            "implied_ids",
            "implied_by_ids",
        } & values.keys()
        users = self.sudo().all_user_ids if relevant else self.env["res.users"]
        before = users._publication_portal_eligibility()
        result = super().write(values)
        if relevant:
            # Keep departed users in the comparison. Only existing effective
            # members can lose portal eligibility through this group's mutation;
            # newly implied members gain membership, not lose it.
            users._revoke_changed_portal_eligibility(before)
        return result


class SolutionPortalCompanies(models.Model):
    _inherit = "res.company"

    def write(self, values):
        before = (
            {company.id: set(company.sudo().user_ids.ids) for company in self}
            if "user_ids" in values
            else {}
        )
        result = super().write(values)
        if "active" in values:
            revoke_publications(self.env, [("company_id", "in", self.ids)])
        elif before:
            for company in self:
                affected = before[company.id] ^ set(company.sudo().user_ids.ids)
                revoke_publications(
                    self.env,
                    [
                        ("company_id", "=", company.id),
                        ("recipient_id", "in", sorted(affected)),
                    ],
                )
        return result
