"""Native optional Sales confirmation must retain its framework authority."""

from unittest import SkipTest

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestSolutionSales(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env["ir.module.module"].search_count(
            [("name", "=", "sale_project"), ("state", "=", "installed")]
        ):
            raise SkipTest("Optional sale_project is not installed in this registry")
        cls.salesperson = mail_new_test_user(
            cls.env,
            "solution_salesperson",
            groups="sales_team.group_sale_salesman",
            company_id=cls.env.company.id,
            company_ids=[Command.set(cls.env.company.ids)],
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "SYNTHETIC Sales customer"}
        )

    def _confirm_plain_template(self, company):
        user = self.salesperson
        self.assertFalse(user.has_group("base.group_system"))
        self.assertFalse(user.has_group("project.group_project_manager"))
        self.assertFalse(user.has_group("sales_team.group_sale_salesman_all_leads"))
        template = self.env["project.project"].create(
            {
                "name": "SYNTHETIC Plain template",
                "is_template": True,
                "company_id": company.id,
                "task_ids": [Command.create({"name": "Plain template work"})],
            }
        )
        self.assertFalse(template.agile_enabled)
        product = self.env["product.product"].create(
            {
                "name": "SYNTHETIC Template service",
                "type": "service",
                "invoice_policy": "order",
                "service_tracking": "project_only",
                "project_template_id": template.id,
                "list_price": 100,
            }
        )
        order = (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.customer.id,
                    "company_id": self.env.company.id,
                    "order_line": [
                        Command.create({"product_id": product.id, "product_uom_qty": 1})
                    ],
                }
            )
        )
        self.assertFalse(order.env.su)
        self.assertEqual(order.env.uid, user.id)
        self.assertEqual(order.user_id, user)
        # Do not elevate confirmation: sale_project owns its trusted Project writes.
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        line = order.order_line.with_env(self.env)
        project = line.project_id
        self.assertEqual(len(project), 1)
        self.assertNotEqual(project, template)
        self.assertFalse(project.is_template)
        self.assertFalse(project.agile_enabled)
        self.assertEqual(project.company_id, company)
        self.assertEqual(project.sale_line_id, line)
        self.assertIn(order.name, project.name)
        self.assertIn(template.name, project.name)
        self.assertEqual(project.task_ids.mapped("name"), ["Plain template work"])
        self.assertTrue(template.is_template)
        self.assertEqual(template.company_id, company)

    def test_own_documents_confirmation_with_company_neutral_template(self):
        # Native creation starts in the order company, then writes template company.
        self.assertTrue(self.env.company)
        self._confirm_plain_template(self.env["res.company"])

    def test_own_documents_confirmation_with_company_specific_template(self):
        self._confirm_plain_template(self.env.company)
