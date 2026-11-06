"""Customer-only adapters on native shared work, not source-model access grants."""

from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import AccessError, ValidationError

from .solution_discussion import SolutionDiscussion, source_readable
from .solution_projection import CUSTOMER_REQUIREMENT_FIELDS, narrative_text

CUSTOMER_SUBTYPE = "project_agile_solution.mt_requirement_customer"
PAGE_SIZE = 20


class CustomerRequirementTask(models.Model):
    _inherit = "project.task"

    def _customer_requirement_task(self):
        """Require current native rules AND this exact contact, not its company."""
        self.ensure_one()
        caller = self.sudo(False).with_context(active_test=False)
        user = caller.env.user
        if not user.active or not user.partner_id.active:
            raise AccessError(_("Current shared work access is required."))
        if not caller.search_count([("id", "=", caller.id)]):
            raise AccessError(_("Current shared work access is required."))
        caller.check_access("read")
        project = caller.project_id
        if not project or not project.search_count([("id", "=", project.id)]):
            raise AccessError(_("Current shared Project access is required."))
        project.check_access("read")
        # Native Project fields remain internal; inspect only eligibility after
        # caller-bound Project/Task authorization, never return these values.
        work = caller.sudo()
        if (
            not work.active
            or not work.project_id.active
            or not work.project_id.agile_enabled
            or work.has_template_ancestor
            or work.has_project_template
        ):
            raise AccessError(_("Active shared Agile work is required."))
        if user.share:
            if not user.has_group("base.group_portal") or not (
                caller.env["mail.followers"]
                .sudo()
                .search_count(
                    [
                        ("res_model", "=", "project.project"),
                        ("res_id", "=", project.id),
                        ("partner_id", "=", user.partner_id.id),
                    ],
                    limit=1,
                )
                or caller.env["project.collaborator"].search_count(
                    [
                        ("project_id", "=", project.id),
                        ("partner_id", "=", user.partner_id.id),
                    ]
                )
            ):
                raise AccessError(
                    _("An invitation for this exact contact is required.")
                )
        elif not user.has_group("project.group_project_user"):
            raise AccessError(_("Current Project user access is required."))
        return caller

    def _customer_requirement_links(self, link_id=False):
        caller = self._customer_requirement_task()
        links = caller.env["project.agile.requirement.task.link"]
        # Portal has no raw link/revision ACL. Elevation is confined to the
        # authorized Task and a finite customer projection, not returned records.
        if caller.env.user.share:
            links = links.sudo()
        domain = [
            ("task_id", "=", caller.id),
            ("active", "=", True),
            ("project_id", "=", caller.project_id.id),
            ("solution_id.active", "=", True),
            ("requirement_revision_id.audience", "=", "customer"),
            ("requirement_revision_id.requirement_id.active", "=", True),
        ]
        if link_id is not False:
            if type(link_id) is not int or link_id <= 0:
                raise ValidationError(_("Select an exact customer requirement link."))
            domain.append(("id", "=", link_id))
        result = links.search(domain, order="id")
        if link_id is not False and not result:
            raise AccessError(_("This customer requirement is unavailable."))
        return result

    def action_customer_requirements(self):
        """Return only the same allowlisted requirement fields as publication."""
        return [
            {
                "link_id": link.id,
                "requirement": {
                    "key": link.requirement_revision_id.requirement_id.key,
                    **{
                        name: link.requirement_revision_id[name]
                        for name in CUSTOMER_REQUIREMENT_FIELDS
                        if name != "key"
                    },
                },
            }
            for link in self._customer_requirement_links()
        ]

    def action_customer_requirement_discussion(self, link_id, before_id=False):
        link = self._customer_requirement_links(link_id)
        if before_id is not False and (type(before_id) is not int or before_id <= 0):
            raise ValidationError(_("Use a valid discussion page."))
        domain = [
            ("model", "=", "project.agile.requirement"),
            ("res_id", "=", link.requirement_revision_id.requirement_id.id),
            ("subtype_id", "=", self.env.ref(CUSTOMER_SUBTYPE).id),
            ("message_type", "=", "comment"),
        ]
        if before_id:
            domain.append(("id", "<", before_id))
        # The source remains forbidden via native mail RPC/downloads. This is a
        # text-only projection of explicitly shared messages on that one thread.
        messages = (
            self.env["mail.message"]
            .sudo()
            .search(domain, order="id desc", limit=PAGE_SIZE + 1)
        )
        page = messages[:PAGE_SIZE]
        return {
            "messages": [
                {"text": narrative_text(row.body), "date": str(row.date)}
                for row in reversed(page)
            ],
            "older_before": page[-1].id if len(messages) > PAGE_SIZE else False,
        }

    def action_post_customer_requirement(self, link_id, body):
        link = self._customer_requirement_links(link_id)
        if type(body) is not str or not body.strip() or len(body) > 10000:
            raise ValidationError(_("Write a message of at most 10000 characters."))
        author = self.env.user.partner_id
        identity = link.requirement_revision_id.requirement_id
        # No caller defaults, recipient/author/source choices, files or automatic
        # subscription. Native #61 source guards stay unchanged for public RPC.
        thread = identity.sudo().with_context(
            {},
            mail_create_nosubscribe=True,
            mail_post_autofollow=False,
            mail_notify_force_send=False,
        )
        super(SolutionDiscussion, thread).message_post(
            body=Markup("<p>%s</p>") % body.strip(),
            author_id=author.id,
            email_from=author.email_formatted,
            message_type="comment",
            subtype_id=self.env.ref(CUSTOMER_SUBTYPE).id,
            partner_ids=[],
            attachment_ids=[],
            parent_id=False,
        )
        return True

    def action_open_customer_requirements(self):
        self._customer_requirement_task()
        return {
            "type": "ir.actions.act_url",
            "url": f"/my/tasks/{self.id}#solution_requirements",
            "target": "self",
        }


class CustomerRequirementDiscussion(models.Model):
    _inherit = "project.agile.requirement"

    def action_compose_customer_discussion(self):
        self.ensure_one()
        if not source_readable(self):
            raise AccessError(_("Current Solution source access is required."))
        return {
            "name": _("Customer discussion: shared text only"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_composition_mode": "comment",
                "default_subtype_xmlid": CUSTOMER_SUBTYPE,
            },
        }
