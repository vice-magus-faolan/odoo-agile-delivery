"""Planning milestone filtering, bounded projection and real client regressions."""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install", "agile_milestones")
class TestPlanningMilestones(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            "release_planner",
            groups="project_agile.group_agile_member,project.group_project_milestone",
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Release planning",
                "agile_enabled": True,
                "agile_key": "RELPLAN",
                "allow_milestones": True,
                "privacy_visibility": "employees",
            }
        )
        cls.team = cls.env["project.agile.team"].create(
            {
                "name": "Release developers",
                "project_id": cls.project.id,
            }
        )
        cls.sprint = cls.env["project.sprint"].create(
            {
                "name": "Release Sprint",
                "project_id": cls.project.id,
                "team_id": cls.team.id,
            }
        )
        cls.milestones = cls.env["project.milestone"].create(
            [
                {"name": name, "project_id": cls.project.id}
                for name in ("Release Alpha", "Release Beta")
            ]
        )
        cls.item_type = cls.env["project.agile.item.type"].create(
            {
                "name": "Release Story",
                "code": "release_planning_story",
                "can_schedule_in_sprint": True,
            }
        )
        cls.tasks = cls.env["project.task"].create(
            [
                {
                    "name": name,
                    "project_id": cls.project.id,
                    "agile_item_type_id": cls.item_type.id,
                    "agile_team_id": cls.team.id,
                    "milestone_id": milestone.id,
                    "sprint_id": cls.sprint.id if scheduled else False,
                    "state": state,
                }
                for name, milestone, scheduled, state in (
                    ("Alpha backlog", cls.milestones[0], False, "01_in_progress"),
                    ("Beta backlog", cls.milestones[1], False, "01_in_progress"),
                    ("Alpha scheduled", cls.milestones[0], True, "01_in_progress"),
                    ("Alpha delivered", cls.milestones[0], False, "1_done"),
                )
            ]
        )

    def _snapshot(self, **kwargs):
        return (
            self.env["project.project"]
            .with_user(self.user)
            .get_agile_planning_snapshot(self.project.id, **kwargs)
        )

    def test_filter_applies_to_backlog_sprint_and_native_fallback(self):
        snapshot = self._snapshot(
            team_id=self.team.id, milestone_id=self.milestones[0].id
        )
        self.assertTrue(snapshot["project"]["allow_milestones"])
        self.assertEqual(
            [row["name"] for row in snapshot["backlog"]["items"]], ["Alpha backlog"]
        )
        self.assertEqual(
            [row["name"] for row in snapshot["sprints"][0]["items"]],
            ["Alpha scheduled"],
        )
        self.assertEqual(
            snapshot["backlog"]["items"][0]["milestone"]["name"], "Release Alpha"
        )
        action = self.project.with_user(self.user).action_open_agile_planning_backlog(
            team_id=self.team.id, milestone_id=self.milestones[0].id
        )
        self.assertEqual(
            self.env["project.task"].with_user(self.user).search(action["domain"]).ids,
            self.tasks[0].ids,
        )
        release = self.milestones[0].with_user(self.user).action_view_tasks()
        contents = (
            self.env["project.task"].with_user(self.user).search(release["domain"])
        )
        self.assertEqual(
            set(contents.ids), set((self.tasks[0] | self.tasks[2] | self.tasks[3]).ids)
        )

    def test_pages_bind_milestone_and_team_and_reject_invalid_ids(self):
        self.env["project.task"].create(
            [
                {
                    "name": f"Alpha page {index}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "agile_team_id": self.team.id,
                    "milestone_id": self.milestones[0].id,
                }
                for index in range(51)
            ]
        )
        first = self._snapshot(team_id=self.team.id, milestone_id=self.milestones[0].id)
        cursor = first["backlog"]["next_cursor"]
        second = self._snapshot(
            cursor=cursor, team_id=self.team.id, milestone_id=self.milestones[0].id
        )
        self.assertEqual(len(first["backlog"]["items"]), 50)
        self.assertEqual(len(second["backlog"]["items"]), 2)
        self.assertFalse(second["backlog"]["next_cursor"])
        self.assertFalse(
            {r["id"] for r in first["backlog"]["items"]}
            & {r["id"] for r in second["backlog"]["items"]}
        )
        for milestone_id in (False, self.milestones[1].id):
            with self.assertRaises(ValidationError):
                self._snapshot(
                    cursor=cursor, team_id=self.team.id, milestone_id=milestone_id
                )
        for value in (True, -1, "1"):
            with self.assertRaises(ValidationError):
                self._snapshot(milestone_id=value)

    def test_disabled_project_never_returns_milestone_metadata(self):
        self.project.allow_milestones = False
        snapshot = self._snapshot()
        self.assertFalse(snapshot["project"]["allow_milestones"])
        self.assertTrue(
            all(not row["milestone"] for row in snapshot["backlog"]["items"])
        )
        with self.assertRaises(AccessError):
            self._snapshot(milestone_id=self.milestones[0].id)

    def test_other_project_milestone_cannot_be_selected(self):
        project = self.env["project.project"].create(
            {
                "name": "Hidden releases",
                "agile_enabled": True,
                "agile_key": "HIDREL",
                "allow_milestones": True,
                "privacy_visibility": "followers",
            }
        )
        milestone = self.env["project.milestone"].create(
            {"name": "Hidden Alpha", "project_id": project.id}
        )
        with self.assertRaises(AccessError):
            self._snapshot(milestone_id=milestone.id)

    def test_filtered_mutation_reconciles_and_cannot_reorder_hidden_work(self):
        snapshot = self._snapshot(milestone_id=self.milestones[0].id)
        task = snapshot["backlog"]["items"][0]
        sprint = snapshot["sprints"][0]
        kwargs = {
            "milestone_id": self.milestones[0].id,
            "expected_versions": {
                "tasks": {str(task["id"]): task["version"]},
                "sprints": {str(sprint["id"]): sprint["version"]},
            },
        }
        model = self.env["project.project"].with_user(self.user)
        with self.assertRaises(ValidationError):
            model.apply_agile_planning_change(
                self.project.id, "reorder", [task["id"]], **kwargs
            )
        result = model.apply_agile_planning_change(
            self.project.id, "assign", [task["id"]], sprint_id=sprint["id"], **kwargs
        )
        self.assertEqual(result["milestone"]["id"], self.milestones[0].id)
        self.assertFalse(result["backlog"]["items"])
        self.assertEqual(len(result["sprints"][0]["items"]), 2)
        self.assertFalse(self.tasks[1].sprint_id)

    def test_many_milestone_labels_are_batched_with_cold_caches(self):
        milestones = self.env["project.milestone"].create(
            [
                {"name": f"Batch release {i}", "project_id": self.project.id}
                for i in range(60)
            ]
        )
        self.env["project.task"].create(
            [
                {
                    "name": f"Batch card {row.id}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "milestone_id": row.id,
                    "sprint_id": self.sprint.id if i < 10 else False,
                }
                for i, row in enumerate(milestones)
            ]
        )
        # Warm access-rule caches, then discard fixture/prefetch caches.
        self._snapshot()
        self.env.flush_all()
        self.env.invalidate_all()
        count = self.cr.sql_log_count
        snapshot = self._snapshot()
        self.assertLessEqual(self.cr.sql_log_count - count, 10)
        self.assertEqual(len(snapshot["backlog"]["items"]), 50)
        self.assertTrue(snapshot["backlog"]["next_cursor"])
        self.assertTrue(all(row["milestone"] for row in snapshot["backlog"]["items"]))

    def test_native_sprint_backlog_milestone_columns(self):
        scrum_master = mail_new_test_user(
            self.env,
            "release_scrum_master",
            groups="project_scrum.group_scrum_master",
        )
        self.assertFalse(scrum_master.has_group("base.group_system"))
        self.assertFalse(scrum_master.has_group("project.group_project_manager"))
        self.env["project.project"].create(
            {"name": "Other milestone project", "allow_milestones": True}
        )
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Release Sprint",
                "res_model": "project.sprint",
                "res_id": self.sprint.id,
                "view_mode": "form",
            }
        )
        for enabled in (True, False):
            self.project.allow_milestones = enabled
            # Another Project keeps the native feature group enabled throughout.
            self.assertTrue(scrum_master.has_group("project.group_project_milestone"))
            for backlog in ("product", "sprint"):
                with self.subTest(enabled=enabled, backlog=backlog):
                    self.start_tour(
                        f"/odoo/action-{action.id}",
                        f"agile_{backlog}_backlog_milestones_{enabled}",
                        login=scrum_master.login,
                    )

    def test_native_planning_milestone_tour(self):
        action = self.env["ir.actions.client"].create(
            {
                "name": "Release planning",
                "tag": "project_agile_ui.planning",
                "context": repr({"project_id": self.project.id}),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}",
            "agile_planning_milestones",
            login=self.user.login,
        )
        milestone_action = self.env["ir.actions.act_window"].create(
            {
                "name": "Release milestone",
                "res_model": "project.milestone",
                "res_id": self.milestones[0].id,
                "view_mode": "form",
            }
        )
        self.start_tour(
            f"/odoo/action-{milestone_action.id}",
            "agile_milestone_form_contents",
            login=self.user.login,
        )
        self.project.allow_milestones = False
        self.start_tour(
            f"/odoo/action-{action.id}",
            "agile_planning_milestones_disabled",
            login=self.user.login,
        )
