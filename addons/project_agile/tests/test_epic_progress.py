"""Full visible-hierarchy progress and ordinary native-form navigation."""

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


class EpicProgressFixture:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env, "epic_progress_member", groups="project_agile.group_agile_member"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Progress client",
                "agile_enabled": True,
                "agile_key": "PROGRESS",
                "agile_estimation_method": "fibonacci",
                "privacy_visibility": "employees",
            }
        )
        cls.epic_type = cls.env.ref("project_agile.project_agile_item_type_epic")
        cls.feature_type = cls.env.ref("project_agile.project_agile_item_type_feature")
        cls.story_type = cls.env.ref("project_agile.project_agile_item_type_story")
        cls.subtask_type = cls.env.ref("project_agile.project_agile_item_type_subtask")
        cls.hours_type = cls.env.ref(
            "project_agile.project_agile_item_type_configuration"
        )
        cls.epic_type.allowed_child_type_ids = [Command.link(cls.hours_type.id)]
        cls.tasks = cls.env["project.task"].with_user(cls.user)
        cls.epic = cls.tasks.create(
            {
                "name": "Customer rollout",
                "project_id": cls.project.id,
                "agile_item_type_id": cls.epic_type.id,
                "agile_story_points": 89,
            }
        )

    def _task(self, name, parent=None, item_type=None, **values):
        return self.tasks.create(
            {
                "name": name,
                "project_id": self.project.id,
                "parent_id": (parent or self.epic).id,
                "agile_item_type_id": (item_type or self.story_type).id,
                **values,
            }
        )

    def _assert_work(self, epic, work, done, points, done_points, unknown=0):
        self.assertEqual(epic.agile_progress["items"], len(work))
        self.assertEqual(epic.agile_progress["done"], done)
        self.assertEqual(epic.agile_progress["points"], points)
        self.assertEqual(epic.agile_progress["done_points"], done_points)
        self.assertEqual(epic.agile_progress["unestimated"], unknown)
        action = epic.action_agile_progress_work()
        actual = self.tasks.with_context(**action["context"]).search(action["domain"])
        self.assertEqual(set(actual.ids), set(work.ids))


@tagged("post_install", "-at_install", "agile_epic_progress")
class TestEpicProgress(EpicProgressFixture, TransactionCase):
    def test_nested_mixed_estimates_and_read_only_rollup(self):
        feature = self._task(
            "Feature", item_type=self.feature_type, agile_story_points=55
        )
        story = self._task("Story", parent=feature, agile_story_points=21)
        leaf = self._task(
            "Delivered leaf",
            parent=story,
            item_type=self.subtask_type,
            agile_story_points=3,
            state="1_done",
        )
        open_work = self._task("Open story", agile_story_points=5)
        unknown = self._task("Unestimated")
        hours = self._task(
            "Configuration",
            item_type=self.hours_type,
            allocated_hours=4,
            agile_story_points=89,
            state="1_done",
        )
        self._task("Cancelled", agile_story_points=89, state="1_canceled")
        self._task("Archived", agile_story_points=89, active=False)
        work = leaf | open_work | unknown | hours
        before = (self.epic | feature | story | work).read(
            ["parent_id", "state", "agile_story_points", "write_date"], load=None
        )
        self._assert_work(self.epic, work, 2, 8, 3, 1)
        self.assertIn("1 unestimated", self.epic.agile_progress_points)
        self.assertEqual(
            (self.epic | feature | story | work).read(
                ["parent_id", "state", "agile_story_points", "write_date"], load=None
            ),
            before,
        )
        self.assertEqual(self.epic.state, "01_in_progress")
        self._assert_work(feature, leaf, 1, 3, 3)

    def test_empty_hours_unknown_and_unsaved_form(self):
        self._assert_work(self.epic, self.tasks.browse(), 0, 0, 0)
        self.assertEqual(self.epic.agile_progress_items, "No contributing work")
        self.assertEqual(self.epic.agile_progress_points, "No story-point work")
        draft = self.tasks.new({"project_id": self.project.id})
        self.assertEqual(draft.agile_progress_items, "No contributing work")
        hours = self._task("Hours only", item_type=self.hours_type)
        self._assert_work(self.epic, hours, 0, 0, 0)
        self.assertEqual(self.epic.agile_progress_points, "No story-point work")
        unknown = self._task("Unknown points", state="1_done")
        self._assert_work(self.epic, hours | unknown, 1, 0, 0, 1)
        self.assertIn(
            "0 / 0 known points; 1 unestimated", self.epic.agile_progress_points
        )

    def test_refresh_deep_edits_moves_archive_and_policy(self):
        destination = self.epic.copy({"name": "Destination"})
        feature = self._task(
            "Move feature", item_type=self.feature_type, agile_story_points=13
        )
        source_action = self.epic.action_agile_progress_work()
        destination_action = destination.action_agile_progress_work()
        leaf = self._task("Nested work", parent=feature, agile_story_points=3)
        self._assert_work(self.epic, leaf, 0, 3, 0)
        self._assert_work(destination, self.tasks.browse(), 0, 0, 0)
        leaf.write({"state": "1_done", "agile_story_points": 5})
        self._assert_work(self.epic, leaf, 1, 5, 5)
        feature.write({"parent_id": destination.id})
        self._assert_work(self.epic, self.tasks.browse(), 0, 0, 0)
        self._assert_work(destination, leaf, 1, 5, 5)
        self.assertFalse(self.tasks.search(source_action["domain"]))
        self.assertEqual(self.tasks.search(destination_action["domain"]), leaf)
        leaf.write({"active": False})
        self._assert_work(destination, feature, 0, 13, 0)
        leaf.write({"active": True})
        self._assert_work(destination, leaf, 1, 5, 5)
        self.story_type.uses_story_points = False
        self._assert_work(destination, leaf, 1, 0, 0)
        self.story_type.uses_story_points = True
        self._assert_work(destination, leaf, 1, 5, 5)
        leaf.state = "1_canceled"
        self._assert_work(destination, feature, 0, 13, 0)
        feature.active = False
        self._assert_work(destination, self.tasks.browse(), 0, 0, 0)

    def test_hidden_intermediate_branch_and_caller_cache(self):
        visible = self._task("Public work", agile_story_points=3)
        hidden = self._task(
            "Private feature", item_type=self.feature_type, agile_story_points=55
        )
        descendant = self._task("Visible orphan", parent=hidden, agile_story_points=8)
        hidden_leaf = self._task("Private leaf", agile_story_points=89)
        rule = self.env["ir.rule"].create(
            {
                "name": "Hide progress contributors",
                "model_id": self.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("id", "not in", (hidden | hidden_leaf).ids)]),
            }
        )
        self.env.invalidate_all()
        self.assertEqual(self.tasks.search_count([("id", "=", hidden.id)]), 0)
        self.assertEqual(self.tasks.search_count([("id", "=", descendant.id)]), 1)
        self._assert_work(self.epic, visible, 0, 3, 0)
        self.assertEqual(self.epic.sudo().agile_progress["points"], 100)
        self._assert_work(self.epic, visible, 0, 3, 0)
        with self.assertRaises(AccessError):
            hidden.action_agile_progress_work()
        rule.unlink()
        self.env.invalidate_all()
        self._assert_work(self.epic, visible | descendant | hidden_leaf, 0, 100, 0)

    def test_company_project_and_template_boundaries(self):
        work = self._task("Allowed", agile_story_points=3)
        company = self.env["res.company"].create({"name": "Other progress company"})
        self.user.company_ids = [Command.set((self.env.company | company).ids)]
        foreign = self.env["project.project"].create(
            {
                "name": "Foreign client",
                "company_id": company.id,
                "agile_enabled": True,
                "agile_key": "FOREIGNPROGRESS",
                "privacy_visibility": "employees",
            }
        )
        foreign_epic = self.env["project.task"].create(
            {
                "name": "Foreign Epic",
                "project_id": foreign.id,
                "agile_item_type_id": self.epic_type.id,
            }
        )
        restricted = foreign_epic.with_user(self.user).with_context(
            allowed_company_ids=[self.env.company.id]
        )
        with self.assertRaises(AccessError):
            restricted.action_agile_progress_work()
        self._assert_work(self.epic, work, 0, 3, 0)
        template = self._task("Template", is_template=True, agile_story_points=89)
        self._assert_work(self.epic, work, 0, 3, 0)
        self.assertNotIn(
            template,
            self.tasks.search(self.epic.action_agile_progress_work()["domain"]),
        )
        self.project.active = False
        self._assert_work(
            self.epic.with_context(active_test=False), self.tasks.browse(), 0, 0, 0
        )

    def test_large_full_set_and_multi_epic_query_growth(self):
        roots = self.epic | self.epic.copy({"name": "Second large Epic"})
        small = self._task("Small", agile_story_points=1)
        self.env.flush_all()
        self.env.invalidate_all()
        # Warm only native rule metadata, not Task field caches.
        roots.check_access("read")
        start = self.cr.sql_log_count
        roots.read(["agile_progress"], load=None)
        baseline = self.cr.sql_log_count - start
        expanded = roots | self.tasks.create(
            [
                {
                    "name": f"Additional Epic {index}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.epic_type.id,
                }
                for index in range(6)
            ]
        )
        large = self.tasks.create(
            [
                {
                    "name": f"Large leaf {index}",
                    "project_id": self.project.id,
                    "parent_id": root.id,
                    "agile_item_type_id": self.story_type.id,
                    "agile_story_points": 1,
                    "state": "1_done",
                }
                for root in roots
                for index in range(260)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        expanded.check_access("read")
        start = self.cr.sql_log_count
        expanded.read(["agile_progress"], load=None)
        self.assertLessEqual(self.cr.sql_log_count - start, baseline + 2)
        self.assertTrue(
            all(not root.agile_progress["items"] for root in expanded - roots)
        )
        self._assert_work(
            roots[0],
            large.filtered(lambda task: task.parent_id == roots[0]) | small,
            260,
            261,
            260,
        )
        self._assert_work(
            roots[1],
            large.filtered(lambda task: task.parent_id == roots[1]),
            260,
            260,
            260,
        )


@tagged("post_install", "-at_install", "agile_epic_progress")
class TestEpicProgressTour(EpicProgressFixture, HttpCase):
    def test_native_progress_summary_and_contributors(self):
        destination = self.epic.copy({"name": "Browser destination"})
        feature = self._task(
            "Nested feature", item_type=self.feature_type, agile_story_points=55
        )
        self._task(
            "Delivered browser leaf",
            parent=feature,
            agile_story_points=3,
            state="1_done",
        )
        self._task("Pending browser leaf", agile_story_points=5)
        self._task("Cancelled browser leaf", state="1_canceled", agile_story_points=89)
        action = self.env.ref("project.action_view_task")
        self.start_tour(
            f"/odoo/action-{action.id}/{self.epic.id}",
            "agile_epic_progress",
            login=self.user.login,
        )
        feature.write({"parent_id": destination.id})
        self.start_tour(
            f"/odoo/action-{action.id}/{self.epic.id}",
            "agile_epic_progress_source_after_move",
            login=self.user.login,
        )
        self.start_tour(
            f"/odoo/action-{action.id}/{destination.id}",
            "agile_epic_progress_destination_after_move",
            login=self.user.login,
        )
