from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectSprintBacklog(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Scrum Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "SCRUM",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Delivery Team", "project_id": self.project.id}
        )
        self.eligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Eligible Story",
                "code": "test_eligible_story",
                "can_schedule_in_sprint": True,
            }
        )
        self.ineligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Ineligible Task",
                "code": "test_ineligible_task",
                "can_schedule_in_sprint": False,
            }
        )
        self.task = self._create_task("Product Backlog work")

    def _create_task(self, name, **values):
        task_values = {
            "name": name,
            "project_id": self.project.id,
            "agile_item_type_id": self.eligible_type.id,
        }
        task_values.update(values)
        return self.env["project.task"].create(task_values)

    def _create_sprint(self, name="Sprint 1"):
        return self.env["project.sprint"].create(
            {
                "name": name,
                "project_id": self.project.id,
                "team_id": self.team.id,
            }
        )

    def _create_wizard(self, tasks, operation, sprint=False):
        values = {
            "task_ids": [Command.set(tasks.ids)],
            "project_id": self.project.id,
            "operation": operation,
        }
        if sprint:
            values["sprint_id"] = sprint.id
        return self.env["project.sprint.task.assignment.wizard"].create(values)

    def test_product_backlog_action_is_project_scoped_and_sprint_eligible(self):
        sprint = self._create_sprint()
        foreign_project = self.env["project.project"].create(
            {
                "name": "Other Scrum Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTHER",
            }
        )
        foreign_task = self.env["project.task"].create(
            {
                "name": "Other product backlog work",
                "project_id": foreign_project.id,
                "agile_item_type_id": self.eligible_type.id,
            }
        )
        ineligible_task = self._create_task(
            "Unschedulable work", agile_item_type_id=self.ineligible_type.id
        )
        typeless_task = self._create_task("Untyped work", agile_item_type_id=False)
        scheduled_task = self._create_task("Scheduled work", sprint_id=sprint.id)
        self._create_task("Done work", state="1_done")
        self._create_task("Canceled work", state="1_canceled")

        action = sprint.action_open_product_backlog()
        task_ids = self.env["project.task"].search(action["domain"])

        self.assertEqual(task_ids, self.task)
        self.assertNotIn(foreign_task, task_ids)
        self.assertNotIn(ineligible_task, task_ids)
        self.assertNotIn(typeless_task, task_ids)
        self.assertNotIn(scheduled_task, task_ids)
        self.assertEqual(action["context"]["default_project_id"], self.project.id)

    def test_general_backlog_keeps_unschedulable_and_untyped_work_as_caller(self):
        user = mail_new_test_user(
            self.env, "General backlog user", groups="project.group_project_user"
        )
        self.task.agile_team_id = self.team
        ineligible = self._create_task(
            "Unschedulable backlog",
            agile_item_type_id=self.ineligible_type.id,
            agile_team_id=self.team.id,
        )
        untyped = self._create_task(
            "Untyped backlog", agile_item_type_id=False, agile_team_id=self.team.id
        )
        unteamed = self._create_task("Unteamed backlog", agile_item_type_id=False)
        for state in ("1_done", "1_canceled"):
            self._create_task(state, state=state, agile_team_id=self.team.id)
        self._create_task("Archived backlog", active=False, agile_team_id=self.team.id)
        self._create_task(
            "Template backlog",
            is_template=True,
            agile_item_type_id=False,
            agile_team_id=self.team.id,
        )
        self._create_task("Assigned backlog", sprint_id=self._create_sprint().id)
        model = self.env["project.task"].with_user(user)
        action = self.env.ref("project_agile.action_project_agile_backlog")
        search = etree.fromstring(
            model.get_view(
                self.env.ref("project_scrum.view_task_search_scrum").id, "search"
            )["arch"].encode()
        )
        filter_domain = safe_eval(
            search.xpath("//filter[@name='agile_backlog']")[0].get("domain")
        )
        expected = self.task | ineligible | untyped | unteamed
        for domain in (safe_eval(action.domain), filter_domain):
            with self.subTest(domain=domain):
                self.assertEqual(set(model.search(domain).ids), set(expected.ids))
                self.assertEqual(
                    set(
                        model.search(
                            domain + [("agile_team_id", "=", self.team.id)]
                        ).ids
                    ),
                    set((expected - unteamed).ids),
                )
        self.assertTrue(
            all(expected.with_user(user).mapped("agile_is_product_backlog"))
        )

    def test_two_team_assignment_inherits_and_rejects_a_mixed_batch_as_caller(self):
        user = mail_new_test_user(
            self.env, "Team planner", groups="project.group_project_user"
        )
        sprint = self._create_sprint()
        second_team = self.env["project.agile.team"].create(
            {"name": "BA", "project_id": self.project.id}
        )
        ba = self._create_task("BA work", agile_team_id=second_team.id)
        unteamed = self._create_task("Unteamed work")
        sprint.action_start()
        caller_tasks = (self.task | ba | unteamed).with_user(user)
        for operation in ("write", "wizard"):
            with self.subTest(operation=operation), self.assertRaises(ValidationError):
                if operation == "write":
                    caller_tasks.write({"sprint_id": sprint.id})
                else:
                    self._create_wizard(caller_tasks, "assign", sprint).with_user(
                        user
                    ).action_confirm()
            self.assertFalse((self.task | ba | unteamed).sprint_id)
            self.assertFalse((self.task | unteamed).agile_team_id)
            self.assertFalse(sprint.scope_event_ids)
        self.task.with_user(user).write({"sprint_id": sprint.id})
        self.assertEqual(self.task.agile_team_id, self.team)
        self.assertEqual(sprint.scope_event_ids.mapped("event_type"), ["added"])
        self.task.with_user(user).write({"sprint_id": False})
        self.assertEqual(self.task.agile_team_id, self.team)
        self.assertEqual(
            sprint.scope_event_ids.mapped("event_type"), ["added", "removed"]
        )

    def test_create_defaults_explicit_mismatch_and_ownership_edits(self):
        sprint = self._create_sprint()
        team = self.env["project.agile.team"].create(
            {"name": "BA", "project_id": self.project.id}
        )
        created = (
            self.env["project.task"]
            .with_context(
                default_project_id=self.project.id, default_sprint_id=sprint.id
            )
            .create({"name": "Quick assigned work"})
        )
        self.assertEqual(created.agile_team_id, self.team)
        with self.assertRaises(ValidationError):
            self.env["project.task"].create(
                [
                    {
                        "name": "Compatible",
                        "project_id": self.project.id,
                        "sprint_id": sprint.id,
                    },
                    {
                        "name": "Mismatch",
                        "project_id": self.project.id,
                        "sprint_id": sprint.id,
                        "agile_team_id": team.id,
                    },
                ]
            )
        self.assertFalse(
            self.env["project.task"].search(
                [("name", "in", ["Compatible", "Mismatch"])]
            )
        )
        with self.assertRaises(ValidationError):
            created.write({"agile_team_id": team.id})
        with self.assertRaises(ValidationError):
            created.write({"agile_team_id": False})
        with self.assertRaises(ValidationError):
            sprint.write({"team_id": team.id})
        other = self.env["project.project"].create(
            {"name": "Other", "agile_enabled": True, "agile_key": "TEAMOTHER"}
        )
        with self.assertRaises(ValidationError):
            self.team.write({"project_id": other.id})
        with self.assertRaises(ValidationError):
            self._create_task(
                "Foreign team", project_id=other.id, agile_team_id=team.id
            )

    def test_membership_coordination_keeps_task_and_team_authority_separate(self):
        user = mail_new_test_user(
            self.env, "Membership user", groups="project.group_project_user"
        )
        manager = mail_new_test_user(
            self.env, "Membership manager", groups="project.group_project_manager"
        )
        sprint = self._create_sprint()
        self.task.with_user(user).write({"sprint_id": sprint.id})
        self.assertEqual(self.task.agile_team_id, self.team)
        with self.assertRaises(AccessError):
            self.team.with_user(user).write({"name": "Unauthorized team edit"})
        with self.assertRaises(AccessError):
            self.team.with_user(manager).write({"membership_revision": 0})
        with self.assertRaises(AccessError):
            self.env["project.agile.team"].with_user(manager).create(
                {
                    "name": "Forged revision",
                    "project_id": self.project.id,
                    "membership_revision": 100,
                }
            )
        self.assertEqual(self.task.sprint_id, sprint)

    def test_team_coordination_preserves_archived_project_task_writes(self):
        user = mail_new_test_user(
            self.env, "Archived membership user", groups="project.group_project_user"
        )
        sprint = self._create_sprint()
        self.project.active = False
        self.task.with_user(user).write({"sprint_id": sprint.id})
        self.assertEqual(self.task.agile_team_id, self.team)
        self.task.with_user(user).return_sprint_tasks_to_product_backlog()
        self.assertFalse(self.task.sprint_id)
        self.assertEqual(self.task.agile_team_id, self.team)

    def test_unused_team_and_empty_sprint_can_still_change_ownership(self):
        other_project = self.env["project.project"].create(
            {"name": "Unused destination", "agile_enabled": True, "agile_key": "UNUSED"}
        )
        unused_team = self.env["project.agile.team"].create(
            {"name": "Unused", "project_id": self.project.id}
        )
        unused_team.write({"project_id": other_project.id})
        self.assertEqual(unused_team.project_id, other_project)
        sprint = self._create_sprint()
        second_team = self.env["project.agile.team"].create(
            {"name": "BA", "project_id": self.project.id}
        )
        sprint.write({"team_id": second_team.id})
        self.assertEqual(sprint.team_id, second_team)

    def test_native_backlog_team_filter_and_active_sprint_action(self):
        sprint = self._create_sprint()
        active_task = self._create_task("Active work", sprint_id=sprint.id)
        sprint.action_start()
        draft = self._create_sprint("Draft")
        draft_task = self._create_task("Draft work", sprint_id=draft.id)
        closed = self._create_sprint("Closed")
        closed._set_lifecycle_state("closed")
        action = self.env.ref("project_scrum.action_project_active_sprint")
        self.assertEqual(action.view_mode.split(",")[0], "kanban")
        self.assertEqual(safe_eval(action.context)["group_by"], "stage_id")
        self.assertEqual(
            self.env["project.task"].search(safe_eval(action.domain)), active_task
        )
        model = self.env["project.task"]
        search = etree.fromstring(
            model.get_view(
                self.env.ref("project_scrum.view_task_search_scrum").id, "search"
            )["arch"].encode()
        )
        active_domain = safe_eval(
            search.xpath("//filter[@name='active_sprint']")[0].get("domain")
        )
        self.assertEqual(model.search(active_domain), active_task)
        self.assertNotIn(draft_task, model.search(active_domain))
        self.task.agile_team_id = self.team
        product_action = self.env.ref("project_agile.action_project_agile_backlog")
        self.assertEqual(
            model.search(
                safe_eval(product_action.domain)
                + [("agile_team_id", "=", self.team.id)]
            ),
            self.task,
        )

    def _check_project_copy_placement(self, from_template):
        manager = mail_new_test_user(
            self.env, "Project copy manager", groups="project.group_project_manager"
        )
        self.eligible_type.allowed_child_type_ids = [
            Command.link(self.eligible_type.id)
        ]
        self.task.agile_team_id = self.team
        child = self._create_task(
            "Teamed child", parent_id=self.task.id, agile_team_id=self.team.id
        )
        sprint = self._create_sprint()
        sprint.action_start()
        scheduled = self._create_task("Sprint work", sprint_id=sprint.id)
        returned = self._create_task("Returned work", sprint_id=sprint.id)
        returned.return_sprint_tasks_to_product_backlog()
        self.assertEqual(returned.agile_team_id, self.team)
        if from_template:
            self.project.is_template = True
        tasks = self.task | child | scheduled | returned
        task_fields = [
            "name",
            "project_id",
            "company_id",
            "parent_id",
            "agile_key",
            "agile_item_type_id",
            "agile_team_id",
            "sprint_id",
        ]
        original_tasks = tasks.read(task_fields, load=None)
        original_project_key = self.project.agile_key
        original_task_keys = set(tasks.mapped("agile_key"))
        self.assertTrue(original_project_key)
        self.assertNotIn(False, original_task_keys)
        event_fields = [
            "sprint_id",
            "task_id",
            "event_type",
            "story_points",
            "previous_story_points",
            "actor_id",
            "event_at",
            "reason",
            "carryover_target_sprint_id",
        ]
        original_events = sprint.scope_event_ids.read(event_fields, load=None)
        original_team = self.team.read(["name", "project_id", "company_id"], load=None)
        original_sprint = sprint.read(["project_id", "team_id", "state"], load=None)
        caller = self.project.with_user(manager)
        self.assertFalse(caller.env.su)
        copied = (
            caller.action_create_from_template() if from_template else caller.copy()
        )
        self.assertNotEqual(copied, caller)
        self.assertFalse(copied.is_template)
        self.assertNotEqual(copied.agile_key, original_project_key)
        self.assertEqual(copied.company_id, self.project.company_id)
        copied_tasks = self.env["project.task"].search([("project_id", "=", copied.id)])
        self.assertEqual(len(copied_tasks), len(tasks))
        self.assertEqual(set(copied_tasks.mapped("name")), set(tasks.mapped("name")))
        self.assertFalse(copied_tasks & tasks)
        self.assertFalse(copied_tasks.agile_team_id)
        self.assertFalse(copied_tasks.sprint_id)
        self.assertFalse(
            original_task_keys.intersection(copied_tasks.mapped("agile_key"))
        )
        copied_child = copied_tasks.filtered(lambda task: task.name == child.name)
        self.assertEqual(copied_child.parent_id.name, self.task.name)
        self.assertIn(copied_child.parent_id, copied_tasks)
        self.assertEqual(tasks.read(task_fields, load=None), original_tasks)
        self.assertEqual(self.project.agile_key, original_project_key)
        self.assertEqual(
            sprint.scope_event_ids.read(event_fields, load=None), original_events
        )
        self.assertEqual(
            self.team.read(["name", "project_id", "company_id"], load=None),
            original_team,
        )
        self.assertEqual(
            sprint.read(["project_id", "team_id", "state"], load=None), original_sprint
        )

    def test_project_copy_clears_source_team_and_sprint_placement(self):
        self._check_project_copy_placement(from_template=False)

    def test_project_template_clears_source_team_and_sprint_placement(self):
        self._check_project_copy_placement(from_template=True)

    def test_plain_project_copy_keeps_a_subtask_in_its_other_project(self):
        projects = self.env["project.project"].create(
            [{"name": "Plain source"}, {"name": "Other plain Project"}]
        )
        root = self.env["project.task"].create(
            {"name": "Plain parent", "project_id": projects[0].id}
        )
        child = self.env["project.task"].create(
            {
                "name": "Other Project subtask",
                "project_id": projects[1].id,
                "parent_id": root.id,
            }
        )
        copied = projects[0].copy()
        copied_root = self.env["project.task"].search([("project_id", "=", copied.id)])
        self.assertEqual(len(copied_root), 1)
        self.assertNotEqual(copied_root, root)
        self.assertEqual(len(copied_root.child_ids), 1)
        self.assertNotEqual(copied_root.child_ids, child)
        self.assertEqual(copied_root.child_ids.project_id, projects[1])
        self.assertEqual(child.parent_id, root)
        self.assertEqual(child.project_id, projects[1])

    def test_same_project_task_copy_keeps_team_and_sprint(self):
        self.task.agile_team_id = self.team
        scheduled = self._create_task(
            "Scheduled duplicate", sprint_id=self._create_sprint().id
        )
        for task in (self.task, scheduled):
            with self.subTest(task=task.name):
                copied = task.copy()
                self.assertEqual(copied.project_id, task.project_id)
                self.assertEqual(copied.agile_team_id, task.agile_team_id)
                self.assertEqual(copied.sprint_id, task.sprint_id)
                self.assertTrue(copied.agile_key)
                self.assertNotEqual(copied.agile_key, task.agile_key)

    def test_cross_project_task_copy_keeps_explicit_destination_placement(self):
        self.task.write({"sprint_id": self._create_sprint().id})
        destination = self.env["project.project"].create(
            {"name": "Copy destination", "agile_enabled": True, "agile_key": "COPY"}
        )
        team = self.env["project.agile.team"].create(
            {"name": "Destination team", "project_id": destination.id}
        )
        sprint = self.env["project.sprint"].create(
            {
                "name": "Destination Sprint",
                "project_id": destination.id,
                "team_id": team.id,
            }
        )
        copied = self.task.copy({"project_id": destination.id})
        self.assertFalse(copied.agile_team_id)
        self.assertFalse(copied.sprint_id)
        self.assertTrue(copied.agile_key.startswith("COPY-"))
        placed = self.task.copy(
            {
                "project_id": destination.id,
                "agile_team_id": team.id,
                "sprint_id": sprint.id,
            }
        )
        self.assertEqual(placed.agile_team_id, team)
        self.assertEqual(placed.sprint_id, sprint)

    def test_sprint_backlog_action_returns_only_the_selected_sprint_tasks(self):
        sprint = self._create_sprint()
        other_sprint = self._create_sprint("Sprint 2")
        sprint_task = self._create_task("Current Sprint work", sprint_id=sprint.id)
        other_sprint_task = self._create_task(
            "Other Sprint work", sprint_id=other_sprint.id
        )

        action = sprint.action_open_sprint_backlog()
        task_ids = self.env["project.task"].search(action["domain"])

        self.assertEqual(task_ids, sprint_task)
        self.assertNotIn(other_sprint_task, task_ids)

    def test_server_actions_open_the_assignment_wizard_for_the_selected_tasks(self):
        assign_action = (
            self.env.ref("project_scrum.action_assign_tasks_to_sprint")
            .with_context(active_model="project.task", active_ids=self.task.ids)
            .run()
        )
        remove_action = (
            self.env.ref("project_scrum.action_remove_tasks_from_sprint")
            .with_context(active_model="project.task", active_ids=self.task.ids)
            .run()
        )

        self.assertEqual(
            assign_action["res_model"], "project.sprint.task.assignment.wizard"
        )
        self.assertEqual(assign_action["context"]["default_operation"], "assign")
        self.assertEqual(
            remove_action["res_model"], "project.sprint.task.assignment.wizard"
        )
        self.assertEqual(remove_action["context"]["default_operation"], "remove")

    def test_assign_wizard_adds_active_sprint_scope_event(self):
        sprint = self._create_sprint()
        sprint.action_start()

        self._create_wizard(self.task, "assign", sprint).action_confirm()

        self.assertEqual(self.task.sprint_id, sprint)
        self.assertEqual(sprint.scope_event_ids.mapped("event_type"), ["added"])
        self.assertEqual(sprint.scope_event_ids.task_id, self.task)

    def test_remove_wizard_removes_from_active_sprint_and_records_scope_event(self):
        sprint = self._create_sprint()
        sprint.action_start()
        self.task.write({"sprint_id": sprint.id})

        self._create_wizard(self.task, "remove").action_confirm()

        self.assertFalse(self.task.sprint_id)
        self.assertEqual(
            sprint.scope_event_ids.mapped("event_type"), ["added", "removed"]
        )

    def test_assign_wizard_rejects_an_ineligible_item_type(self):
        sprint = self._create_sprint()
        for item_type_id in (self.ineligible_type.id, False):
            task = self._create_task("Ineligible work", agile_item_type_id=item_type_id)
            with (
                self.subTest(item_type_id=item_type_id),
                self.assertRaises(ValidationError),
            ):
                self._create_wizard(task, "assign", sprint).action_confirm()
            self.assertFalse(task.sprint_id)

    def test_assign_wizard_rejects_a_closed_sprint(self):
        sprint = self._create_sprint()
        sprint.action_start()
        sprint.action_close()

        with self.assertRaises(ValidationError):
            self._create_wizard(self.task, "assign", sprint).action_confirm()

        self.assertFalse(self.task.sprint_id)

    def test_assign_wizard_rejects_mixed_scheduled_and_unscheduled_tasks(self):
        sprint = self._create_sprint()
        already_scheduled = self._create_task("Scheduled work", sprint_id=sprint.id)

        with self.assertRaises(ValidationError):
            self._create_wizard(
                self.task | already_scheduled, "assign", sprint
            ).action_confirm()

        self.assertFalse(self.task.sprint_id)
        self.assertEqual(already_scheduled.sprint_id, sprint)

    def test_assignment_wizard_rejects_cross_project_task_selection(self):
        foreign_project = self.env["project.project"].create(
            {
                "name": "Other Scrum Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTHER",
            }
        )
        foreign_task = self.env["project.task"].create(
            {
                "name": "Other work",
                "project_id": foreign_project.id,
                "agile_item_type_id": self.eligible_type.id,
            }
        )

        with self.assertRaises(ValidationError):
            self._create_wizard(
                self.task | foreign_task, "assign", self._create_sprint()
            )

    def test_typeless_agile_task_cannot_bypass_product_backlog_eligibility(self):
        sprint = self._create_sprint()
        task = self._create_task("Typeless work", agile_item_type_id=False)

        with self.assertRaises(ValidationError):
            task.write({"sprint_id": sprint.id})

        self.assertFalse(task.sprint_id)

    def test_scheduled_item_type_cannot_become_ineligible(self):
        sprint = self._create_sprint()
        self.task.write({"sprint_id": sprint.id})

        with self.assertRaises(ValidationError):
            self.eligible_type.write({"can_schedule_in_sprint": False})

        self.assertTrue(self.eligible_type.can_schedule_in_sprint)

    def test_project_user_can_assign_and_remove_editable_tasks(self):
        user = mail_new_test_user(
            self.env, "Scrum user", groups="project.group_project_user"
        )
        self.assertFalse(user.has_group("project.group_project_manager"))
        sprint = self._create_sprint()
        wizard_model = self.env["project.sprint.task.assignment.wizard"].with_user(user)

        wizard_model.create(
            {
                "task_ids": [Command.set(self.task.ids)],
                "project_id": self.project.id,
                "operation": "assign",
                "sprint_id": sprint.id,
            }
        ).action_confirm()
        self.task.invalidate_recordset(["sprint_id"])
        self.assertEqual(self.task.sprint_id, sprint)

        wizard_model.create(
            {
                "task_ids": [Command.set(self.task.ids)],
                "project_id": self.project.id,
                "operation": "remove",
            }
        ).action_confirm()
        self.task.invalidate_recordset(["sprint_id"])
        self.assertFalse(self.task.sprint_id)

    def test_project_user_cannot_mutate_private_tasks_through_assignment_wizard(self):
        user = mail_new_test_user(
            self.env, "Scrum outsider", groups="project.group_project_user"
        )
        self.assertFalse(user.has_group("project.group_project_manager"))
        sprint = self._create_sprint()
        self.project.write({"privacy_visibility": "followers"})
        with self.assertRaises(AccessError):
            self.task.with_user(user).check_access("write")

        for operation in ("assign", "remove"):
            with self.subTest(operation=operation):
                original_sprint = sprint if operation == "remove" else False
                self.task.write(
                    {"sprint_id": original_sprint.id if original_sprint else False}
                )
                values = {
                    "task_ids": [Command.set(self.task.ids)],
                    "project_id": self.project.id,
                    "operation": operation,
                }
                if operation == "assign":
                    values["sprint_id"] = sprint.id
                with self.assertRaises(AccessError), self.cr.savepoint():
                    self.env["project.sprint.task.assignment.wizard"].with_user(
                        user
                    ).create(values).action_confirm()
                self.task.invalidate_recordset(["sprint_id"])
                self.assertEqual(
                    self.task.sprint_id,
                    sprint if original_sprint else self.env["project.sprint"],
                )
