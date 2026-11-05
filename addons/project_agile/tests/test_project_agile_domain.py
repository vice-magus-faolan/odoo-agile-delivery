from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectAgileDomain(TransactionCase):
    def setUp(self):
        super().setUp()
        self.item_type_model = self.env["project.agile.item.type"]
        self.epic_type = self.item_type_model.create(
            {"name": "Epic", "code": "test_epic"}
        )
        self.story_type = self.item_type_model.create(
            {"name": "Story", "code": "test_story"}
        )
        self.task_type = self.item_type_model.create(
            {"name": "Task", "code": "test_task"}
        )
        self.epic_type.write(
            {"allowed_child_type_ids": [Command.set(self.story_type.ids)]}
        )
        self.story_type.write(
            {"allowed_child_type_ids": [Command.set(self.task_type.ids)]}
        )
        self.project = self._create_agile_project("Engineering", "ENG")
        self.other_project = self._create_agile_project("Operations", "OPS")

    def _create_agile_project(self, name, key, **values):
        return self.env["project.project"].create(
            {
                "name": name,
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": key,
                **values,
            }
        )

    def _create_task(self, name, item_type=None, **values):
        return self.env["project.task"].create(
            {
                "name": name,
                "project_id": self.project.id,
                **({"agile_item_type_id": item_type.id} if item_type else {}),
                **values,
            }
        )

    def test_agile_task_receives_immutable_key(self):
        task = self._create_task("Implement key allocation")

        self.assertEqual(task.agile_key, "ENG-1")
        with self.assertRaises(ValidationError):
            task.write({"agile_key": "ENG-99"})

    def test_generated_keys_are_stable_and_unique(self):
        first = self._create_task("First")
        second = self._create_task("Second")

        self.assertEqual((first.agile_key, second.agile_key), ("ENG-1", "ENG-2"))
        first.write({"name": "Renamed"})
        self.assertEqual(first.agile_key, "ENG-1")
        with self.assertRaises(ValidationError):
            self.project.write({"agile_key": "NEW"})

    def test_non_agile_tasks_do_not_receive_keys_or_policy(self):
        project = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )

        task = self.env["project.task"].create(
            {
                "name": "Ordinary task",
                "project_id": project.id,
                "agile_key": "FORCED-1",
                "agile_story_points": 13,
            }
        )

        self.assertFalse(task.agile_key)
        self.assertEqual(task.agile_story_points, 13)

    def test_parent_type_policy_and_project_isolation_are_enforced(self):
        parent = self._create_task("Epic", self.epic_type)
        child = self._create_task("Story", self.story_type, parent_id=parent.id)
        invalid_parent = self._create_task("Task", self.task_type)

        self.assertEqual(child.parent_id, parent)
        with self.assertRaises(ValidationError):
            invalid_parent.write({"parent_id": parent.id})

        foreign_child = self.env["project.task"].create(
            {
                "name": "Foreign story",
                "project_id": self.other_project.id,
                "agile_item_type_id": self.story_type.id,
            }
        )
        key_before = foreign_child.agile_key
        with self.assertRaises(ValidationError):
            foreign_child.write({"parent_id": parent.id})
        self.assertEqual(
            (foreign_child.project_id, foreign_child.agile_key),
            (self.other_project, key_before),
        )

    def test_keyed_task_cannot_move_to_another_project(self):
        task = self._create_task("Pinned work item")

        with self.assertRaises(ValidationError):
            task.write({"project_id": self.other_project.id})

        self.assertEqual((task.project_id, task.agile_key), (self.project, "ENG-1"))

    def test_type_policy_cannot_be_reconfigured_to_invalidate_tasks(self):
        parent = self._create_task("Epic", self.epic_type)
        self._create_task("Story", self.story_type, parent_id=parent.id)

        with self.assertRaises(ValidationError):
            self.epic_type.write({"allowed_child_type_ids": [Command.clear()]})

        self.assertIn(self.story_type, self.epic_type.allowed_child_type_ids)

    def test_native_task_cycle_protection_remains_active(self):
        parent = self._create_task("Untyped parent", agile_item_type_id=False)
        child = self._create_task(
            "Untyped child", parent_id=parent.id, agile_item_type_id=False
        )

        with self.assertRaises(ValidationError):
            parent.write({"parent_id": child.id})

        self.assertFalse(parent.parent_id)

    def test_fibonacci_estimation_is_narrow_and_validated(self):
        self.project.write({"agile_estimation_method": "fibonacci"})
        task = self._create_task("Estimated", agile_story_points=5)

        self.assertEqual(task.agile_story_points, 5)
        with self.assertRaises(ValidationError):
            self._create_task("Invalid estimate", agile_story_points=4)
        self.project.write({"agile_estimation_method": "none"})
        with self.assertRaises(ValidationError):
            self._create_task("No-estimate project", agile_story_points=1)

    def test_default_type_acceptance_criteria_and_backlog_sequence_are_stored(self):
        self.project.write({"agile_default_item_type_id": self.story_type.id})

        task = self._create_task(
            "Refine acceptance criteria",
            agile_acceptance_criteria="<p>Acceptance criterion</p>",
            agile_backlog_sequence=30,
        )

        self.assertEqual(task.agile_item_type_id, self.story_type)
        self.assertEqual(task.agile_backlog_sequence, 30)
        self.assertIn("Acceptance criterion", task.agile_acceptance_criteria)

    def test_project_manager_configures_types_and_employee_creates_keyed_tasks(self):
        manager = mail_new_test_user(
            self.env, "Agile manager", groups="project.group_project_manager"
        )
        employee = mail_new_test_user(
            self.env, "Agile employee", groups="project.group_project_user"
        )

        self.item_type_model.with_user(manager).create(
            {"name": "Configured Type", "code": "configured_type"}
        )
        self.item_type_model.with_user(employee).read(["name"])
        with self.assertRaises(AccessError):
            self.item_type_model.with_user(employee).create(
                {"name": "Blocked", "code": "blocked"}
            )

        task = (
            self.env["project.task"]
            .with_user(employee)
            .create({"name": "Employee work", "project_id": self.project.id})
        )
        self.assertEqual(task.agile_key, "ENG-1")

    def test_seeded_item_types_and_stable_ui_xml_ids_are_installed(self):
        epic = self.env.ref("project_agile.project_agile_item_type_epic")
        story = self.env.ref("project_agile.project_agile_item_type_story")
        task = self.env.ref("project_agile.project_agile_item_type_task")

        self.assertEqual((epic.code, story.code, task.code), ("epic", "story", "task"))
        self.assertIn(story, epic.allowed_child_type_ids)
        self.assertIn(task, story.allowed_child_type_ids)

        for xml_id in (
            "project_agile.view_project_form_agile",
            "project_agile.view_task_form_agile",
            "project_agile.view_task_list_agile",
            "project_agile.view_task_kanban_agile",
            "project_agile.view_task_search_agile",
            "project_agile.action_project_agile_backlog",
            "project_agile.action_project_agile_item_type",
        ):
            self.assertTrue(self.env.ref(xml_id))

        backlog_action = self.env.ref("project_agile.action_project_agile_backlog")
        self.assertEqual(backlog_action.res_model, "project.task")

    def test_backlog_ordering_respects_explicit_sequence_and_opt_in(self):
        later = self._create_task("Later backlog item", agile_backlog_sequence=30)
        earlier = self._create_task("Earlier backlog item", agile_backlog_sequence=10)
        ordinary_project = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )
        ordinary = self.env["project.task"].create(
            {
                "name": "Ordinary task",
                "project_id": ordinary_project.id,
                "agile_backlog_sequence": 1,
            }
        )

        backlog = self.env["project.task"].search(
            safe_eval(
                self.env.ref("project_agile.action_project_agile_backlog").domain
            ),
            order="agile_backlog_sequence, id",
        )

        self.assertLess(backlog.ids.index(earlier.id), backlog.ids.index(later.id))
        self.assertNotIn(ordinary, backlog)

    def test_backlog_action_and_search_exclude_closed_archived_and_template_work(self):
        opened = self._create_task("Open work")
        done = self._create_task("Finished work", state="1_done")
        canceled = self._create_task("Canceled work", state="1_canceled")
        archived = self._create_task("Archived work", active=False)
        template = self._create_task(
            "Template work", is_template=True, agile_item_type_id=False
        )
        child = self._create_task("Template descendant", parent_id=template.id)
        folded = self.env["project.task.type"].create(
            {
                "name": "Folded but open",
                "fold": True,
                "project_ids": [Command.set(self.project.ids)],
            }
        )
        opened.stage_id = folded
        tasks = opened | done | canceled | archived | template | child
        model = self.env["project.task"].with_context(active_test=False)
        action = self.env.ref("project_agile.action_project_agile_backlog")
        view = model.get_view(
            self.env.ref("project_agile.view_task_search_agile").id, "search"
        )
        search = etree.fromstring(view["arch"].encode())
        filter_domain = safe_eval(
            search.xpath("//filter[@name='agile_backlog']")[0].get("domain")
        )
        for domain in (safe_eval(action.domain), filter_domain):
            self.assertEqual(model.search(domain + [("id", "in", tasks.ids)]), opened)
        self.assertTrue(opened.agile_is_product_backlog)
        opened.state = "1_done"
        self.assertFalse(opened.agile_is_product_backlog)
        self.assertEqual(
            set(
                model.search(
                    [("agile_is_product_backlog", "=", False), ("id", "in", tasks.ids)]
                ).ids
            ),
            set(tasks.ids),
        )

    def test_native_key_name_search_and_display(self):
        member = mail_new_test_user(
            self.env, "key_search_member", groups="project_agile.group_agile_member"
        )
        task = self._create_task("Selectable work")
        model = self.env["project.task"].with_user(member)
        self.assertEqual(
            model.name_search("ENG-1", operator="="),
            [(task.id, "[ENG-1] Selectable work")],
        )
        self.assertIn(task.id, dict(model.name_search("ENG-")))
        self.assertIn(task.id, dict(model.name_search("Selectable")))
        task.write({"name": "Renamed work"})
        self.assertEqual(task.display_name, "[ENG-1] Renamed work")
        plain = model.create({"name": "Plain selectable"})
        self.assertEqual(plain.display_name, "Plain selectable")
        self.assertIn(plain.id, dict(model.name_search("Plain selectable")))

    def test_exact_key_precedes_prefix_matches_at_picker_limit(self):
        member = mail_new_test_user(
            self.env, "picker_key_member", groups="project_agile.group_agile_member"
        )
        tasks = self.env["project.task"].create(
            [
                {"name": f"Work {index}", "project_id": self.project.id}
                for index in range(25)
            ]
        )
        model = self.env["project.task"].with_user(member)
        domain = [("project_id", "=", self.project.id)]
        native_matches = model.search(domain + [("agile_key", "ilike", "ENG-1")])
        self.assertNotIn(tasks[0], native_matches[:8])
        expected = [tasks[0].id] + (native_matches - tasks[0]).ids
        results = model.name_search("ENG-1", domain=domain, limit=8)
        self.assertEqual([task_id for task_id, _ in results], expected[:8])
        self.assertEqual(results[0][1], "[ENG-1] Work 0")
        self.assertEqual(len(dict(results)), 8)
        self.assertEqual(
            model.name_search("eng-1", domain=domain, limit=1), results[:1]
        )
        self.assertEqual(
            [
                task_id
                for task_id, _ in model.name_search("ENG-1", domain=domain, limit=0)
            ],
            expected,
        )
        excluded = domain + [("id", "!=", tasks[0].id)]
        self.assertEqual(
            [
                task_id
                for task_id, _ in model.name_search("ENG-1", domain=excluded, limit=8)
            ],
            (native_matches - tasks[0]).ids[:8],
        )
        self.assertEqual(
            model.name_search("ENG-1", domain=domain, operator="="), results[:1]
        )
        self.assertEqual(model.name_search("Work 0", domain=domain), results[:1])
        self.assertEqual(
            [
                task_id
                for task_id, _ in model.name_search("ENG-", domain=domain, limit=8)
            ],
            model.search(domain, limit=8).ids,
        )
        self.assertEqual(
            [
                task_id
                for task_id, _ in model.name_search(
                    "ENG-1", domain=domain, operator="not ilike", limit=8
                )
            ],
            model.search(
                domain + [("display_name", "not ilike", "ENG-1")], limit=8
            ).ids,
        )

    def test_enable_keys_existing_archived_and_template_work_in_order(self):
        project = self.env["project.project"].create(
            {"name": "Existing", "agile_key": "EXIST"}
        )
        model = self.env["project.task"]
        tasks = model.create(
            [
                {
                    "name": "Later",
                    "project_id": project.id,
                    "create_date": "2026-01-02 00:00:00",
                    "agile_item_type_id": self.story_type.id,
                },
                {
                    "name": "Earlier archived",
                    "project_id": project.id,
                    "create_date": "2026-01-01 00:00:00",
                    "active": False,
                },
                {
                    "name": "Same date",
                    "project_id": project.id,
                    "create_date": "2026-01-02 00:00:00",
                },
            ]
        )
        template = model.create(
            {"name": "Template", "project_id": project.id, "is_template": True}
        )
        child = model.create(
            {
                "name": "Template child",
                "project_id": project.id,
                "parent_id": template.id,
            }
        )
        project.write({"agile_enabled": True})
        self.assertEqual(tasks.mapped("agile_key"), ["EXIST-2", "EXIST-1", "EXIST-3"])
        self.assertEqual(tasks[0].agile_item_type_id, self.story_type)
        self.assertFalse(tasks[1].agile_item_type_id)
        self.assertFalse(template.agile_key)
        self.assertFalse(child.agile_key)
        keys = tasks.mapped("agile_key")
        project.write({"agile_enabled": False})
        project.write({"agile_enabled": True})
        self.assertEqual(tasks.mapped("agile_key"), keys)
        fresh = model.create({"name": "Next", "project_id": project.id})
        self.assertEqual(fresh.agile_key, "EXIST-4")
        fresh.active = False
        tasks.write({"active": False})
        with self.assertRaises(ValidationError):
            project.write({"agile_key": "REKEY"})
        template_project = self.env["project.project"].create(
            {
                "name": "Project template",
                "is_template": True,
                "agile_enabled": True,
                "agile_key": "TEMPLATE",
            }
        )
        project_task = model.create(
            {"name": "Template project task", "project_id": template_project.id}
        )
        self.assertFalse(project_task.agile_key)

    def test_native_template_undo_keys_restored_subtree_and_preserves_identity(self):
        manager = mail_new_test_user(
            self.env, "template_key_manager", groups="project.group_project_manager"
        )
        parent = self._create_task(
            "Template", is_template=True, agile_item_type_id=False
        )
        child = self._create_task(
            "Child", parent_id=parent.id, active=False, agile_item_type_id=False
        )
        nested = self._create_task(
            "Still template",
            parent_id=parent.id,
            is_template=True,
            agile_item_type_id=False,
        )
        excluded = self._create_task(
            "Still excluded", parent_id=nested.id, agile_item_type_id=False
        )
        self.assertFalse(any((parent | child | nested | excluded).mapped("agile_key")))
        parent.with_user(manager).action_undo_convert_to_template()
        self.assertTrue(parent.agile_key)
        self.assertTrue(child.agile_key)
        self.assertNotEqual(parent.agile_key, child.agile_key)
        self.assertFalse(any((nested | excluded).mapped("agile_key")))
        keys = (parent | child).mapped("agile_key")
        parent.with_user(manager).action_convert_to_template()
        parent.with_user(manager).action_undo_convert_to_template()
        self.assertEqual((parent | child).mapped("agile_key"), keys)

    def test_native_project_undo_keys_eligible_work_and_preserves_identity(self):
        manager = mail_new_test_user(
            self.env, "project_template_manager", groups="project.group_project_manager"
        )
        original = self._create_task("Original work", self.story_type)
        original_key = original.agile_key
        action = self.project.with_user(manager).action_create_template_from_project()
        project = self.env["project.project"].browse(action["params"]["project_id"])
        self.assertTrue(project.is_template)
        self.assertTrue(project.agile_enabled)
        self.assertNotEqual(project.agile_key, self.project.agile_key)
        model = self.env["project.task"]
        parent = model.create(
            {
                "name": "Added to Project template",
                "project_id": project.id,
                "agile_item_type_id": self.story_type.id,
            }
        )
        child = model.create(
            {
                "name": "Archived descendant",
                "project_id": project.id,
                "parent_id": parent.id,
                "agile_item_type_id": self.task_type.id,
                "active": False,
            }
        )
        nested = model.create(
            {
                "name": "Task template",
                "project_id": project.id,
                "is_template": True,
                "agile_item_type_id": self.story_type.id,
            }
        )
        excluded = model.create(
            {
                "name": "Excluded descendant",
                "project_id": project.id,
                "parent_id": nested.id,
                "agile_item_type_id": self.task_type.id,
            }
        )
        eligible = model.with_context(active_test=False).search(
            [("project_id", "=", project.id), ("id", "not in", (nested | excluded).ids)]
        )
        self.assertIn(parent, eligible)
        self.assertIn(child, eligible)
        self.assertFalse(any(eligible.mapped("agile_key")))
        before = eligible.read(
            ["name", "agile_item_type_id", "parent_id", "active"], load=None
        )
        project.with_user(manager).action_undo_convert_to_template()
        self.assertFalse(project.is_template)
        self.assertTrue(all(eligible.mapped("agile_key")))
        self.assertEqual(len(set(eligible.mapped("agile_key"))), len(eligible))
        self.assertFalse(any((nested | excluded).mapped("agile_key")))
        self.assertEqual(
            eligible.read(
                ["name", "agile_item_type_id", "parent_id", "active"], load=None
            ),
            before,
        )
        keys = eligible.mapped("agile_key")
        project.with_user(manager).action_undo_convert_to_template()
        self.assertEqual(eligible.mapped("agile_key"), keys)
        self.assertEqual(original.agile_key, original_key)
        ordinary = self.env["project.project"].create(
            {"name": "Ordinary template", "is_template": True}
        )
        ordinary_task = model.create(
            {"name": "Ordinary work", "project_id": ordinary.id}
        )
        ordinary.with_user(manager).action_undo_convert_to_template()
        self.assertFalse(ordinary_task.agile_key)

    def test_native_project_undo_rejects_hidden_archived_work_atomically(self):
        manager = mail_new_test_user(
            self.env,
            "restricted_template_manager",
            groups="project.group_project_manager",
        )
        project = self._create_agile_project(
            "Restricted template", "RESTRICTED", is_template=True
        )
        tasks = self.env["project.task"].create(
            [
                {"name": "Visible", "project_id": project.id},
                {"name": "Hidden archived", "project_id": project.id, "active": False},
            ]
        )
        self.env["ir.rule"].create(
            {
                "name": "Hide Project-template task",
                "model_id": self.env.ref("project.model_project_task").id,
                "domain_force": repr([("id", "!=", tasks[1].id)]),
            }
        )
        with self.assertRaises(AccessError):
            project.with_user(manager).action_undo_convert_to_template()
        self.assertTrue(project.is_template)
        self.assertFalse(any(tasks.mapped("agile_key")))

    def test_bulk_template_restoration_keeps_ineligible_work_unkeyed(self):
        ordinary = self.env["project.project"].create({"name": "Ordinary templates"})
        project_template = self._create_agile_project(
            "Project template", "TPL", is_template=True
        )
        eligible = self._create_task("Eligible template", is_template=True)
        ordinary_task = self.env["project.task"].create(
            {
                "name": "Ordinary template",
                "project_id": ordinary.id,
                "is_template": True,
            }
        )
        project_task = self.env["project.task"].create(
            {
                "name": "Project template task",
                "project_id": project_template.id,
                "is_template": True,
            }
        )
        keyed = self._create_task("Existing identity")
        key = keyed.agile_key
        keyed.action_convert_to_template()
        (eligible | ordinary_task | project_task | keyed).write({"is_template": False})
        self.assertTrue(eligible.agile_key)
        self.assertEqual(keyed.agile_key, key)
        self.assertFalse(ordinary_task.agile_key)
        self.assertFalse(project_task.agile_key)

    def test_move_keys_incoming_parent_and_archived_child(self):
        manager = mail_new_test_user(
            self.env, "scoped_move_manager", groups="project.group_project_manager"
        )
        ordinary = self.env["project.project"].create(
            {"name": "Scope source", "privacy_visibility": "employees"}
        )
        incoming = self.env["project.task"].create(
            {"name": "Incoming parent", "project_id": ordinary.id}
        )
        child = self.env["project.task"].create(
            {
                "name": "Archived incoming child",
                "parent_id": incoming.id,
                "active": False,
            }
        )
        incoming.with_user(manager).write({"project_id": self.project.id})
        self.assertEqual((incoming | child).project_id, self.project)
        self.assertTrue(all((incoming | child).mapped("agile_key")))

    def test_move_defaults_preserve_same_project_choices_and_batch_identity(self):
        ordinary = self.env["project.project"].create({"name": "Move source"})
        self.project.write({"agile_default_item_type_id": self.story_type.id})
        model = self.env["project.task"]
        incoming = model.create(
            [
                {
                    "name": "Incoming typed",
                    "project_id": ordinary.id,
                    "agile_item_type_id": self.task_type.id,
                },
                {"name": "Incoming two", "project_id": ordinary.id},
            ]
        )
        stages = self.env["project.task.type"].create(
            [
                {
                    "name": "Task only",
                    "sequence": 1,
                    "project_ids": [Command.link(self.project.id)],
                    "agile_item_type_ids": [Command.link(self.task_type.id)],
                },
                {
                    "name": "Story only",
                    "sequence": 2,
                    "project_ids": [Command.link(self.project.id)],
                    "agile_item_type_ids": [Command.link(self.story_type.id)],
                },
            ]
        )
        existing = self._create_task("Deliberate type", self.task_type)
        (incoming | existing).write({"project_id": self.project.id})
        self.assertEqual(incoming.mapped("agile_key"), ["ENG-2", "ENG-3"])
        self.assertEqual(incoming[0].agile_item_type_id, self.task_type)
        self.assertEqual(incoming[1].agile_item_type_id, self.story_type)
        self.assertEqual(incoming[0].stage_id, stages[0])
        self.assertEqual(incoming[1].stage_id, stages[1])
        self.assertEqual(existing.agile_item_type_id, self.task_type)
        existing.write({"project_id": self.project.id})
        self.assertEqual(existing.agile_item_type_id, self.task_type)
        explicit = model.create(
            [
                {
                    "name": "Explicit typed",
                    "project_id": ordinary.id,
                    "agile_item_type_id": self.task_type.id,
                },
                {"name": "Explicit untyped", "project_id": ordinary.id},
            ]
        )
        explicit.write({"project_id": self.project.id, "agile_item_type_id": False})
        self.assertFalse(explicit.agile_item_type_id)
        self.assertTrue(all(explicit.mapped("agile_key")))
        chosen = model.create(
            [
                {
                    "name": "Choice typed",
                    "project_id": ordinary.id,
                    "agile_item_type_id": self.task_type.id,
                },
                {"name": "Choice untyped", "project_id": ordinary.id},
            ]
        )
        chosen.write(
            {"project_id": self.project.id, "agile_item_type_id": self.story_type.id}
        )
        self.assertEqual(chosen.agile_item_type_id, self.story_type)
        self.assertEqual(chosen.stage_id, stages[1])
        self.assertTrue(all(chosen.mapped("agile_key")))
        waiting = model.create({"name": "Wait", "project_id": ordinary.id})
        with self.assertRaises(ValidationError):
            (waiting | existing).write({"project_id": self.other_project.id})
        self.assertEqual(waiting.project_id, ordinary)
        self.assertFalse(waiting.agile_key)

    def test_complete_onboarding_rejects_hidden_archived_work_before_mutation(self):
        manager = mail_new_test_user(
            self.env, "key_onboarding_manager", groups="project.group_project_manager"
        )
        project = self.env["project.project"].create(
            {
                "name": "Restricted onboarding",
                "privacy_visibility": "employees",
                "agile_key": "HIDDEN",
            }
        )
        tasks = self.env["project.task"].create(
            [
                {"name": "Visible", "project_id": project.id},
                {"name": "Hidden archived", "project_id": project.id, "active": False},
            ]
        )
        self.env["ir.rule"].create(
            {
                "name": "Hide onboarding task",
                "model_id": self.env.ref("project.model_project_task").id,
                "domain_force": repr([("id", "!=", tasks[1].id)]),
            }
        )
        caller_tasks = (
            self.env["project.task"].with_user(manager).with_context(active_test=False)
        )
        self.assertNotIn(
            tasks[1].id, caller_tasks.search([("project_id", "=", project.id)]).ids
        )
        with self.assertRaises(AccessError):
            project.with_user(manager).write({"agile_enabled": True})
        self.assertFalse(project.agile_enabled)
        self.assertFalse(any(tasks.mapped("agile_key")))
        self.assertFalse(
            self.env["ir.sequence"]
            .sudo()
            .search_count([("code", "=", project._agile_sequence_code())])
        )

    def test_key_search_respects_record_rules_and_company_scope(self):
        member = mail_new_test_user(
            self.env, "restricted_key_member", groups="project_agile.group_agile_member"
        )
        visible = self._create_task("Visible key")
        hidden = self._create_task("Hidden key")
        company = self.env["res.company"].create({"name": "Foreign key company"})
        foreign_project = self._create_agile_project(
            "Foreign", "FOREIGN", company_id=company.id
        )
        foreign = self.env["project.task"].create(
            {"name": "Foreign work", "project_id": foreign_project.id}
        )
        self.env["ir.rule"].create(
            {
                "name": "Hidden key",
                "model_id": self.env.ref("project.model_project_task").id,
                "domain_force": repr([("id", "!=", hidden.id)]),
            }
        )
        model = (
            self.env["project.task"]
            .with_user(member)
            .with_context(allowed_company_ids=[self.env.company.id])
        )
        self.assertIn(visible.id, dict(model.name_search("ENG-")))
        self.assertNotIn(hidden.id, dict(model.name_search("ENG-")))
        self.assertEqual(model.name_search(hidden.agile_key, operator="="), [])
        self.assertEqual(model.name_search(foreign.agile_key, operator="="), [])
        self.assertEqual(model.name_search(hidden.agile_key, limit=8), [])
        self.assertEqual(model.name_search(foreign.agile_key, limit=8), [])
        with self.assertRaises(AccessError):
            foreign.with_user(member).with_context(
                allowed_company_ids=[self.env.company.id]
            ).read(["display_name"])
