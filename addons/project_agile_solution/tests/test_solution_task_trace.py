"""Actual nonadmin native Task boundary, freshness, atomicity and retry checks."""

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import Form

from .test_solution_requirements import TestSolutionRequirements


class TestSolutionTaskTrace(TestSolutionRequirements):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager.write(
            {"group_ids": [Command.link(cls.env.ref("base.group_allow_export").id)]}
        )

    def _task(self, **values):
        return (
            self._spike(item_type="story").with_user(self.manager)
            if not values
            else self.env["project.task"]
            .with_user(self.manager)
            .create(
                {
                    "name": "SYNTHETIC manual work",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.env.ref(
                        "project_agile.project_agile_item_type_story"
                    ).id,
                    **values,
                }
            )
        )

    def _intent(self, revisions=None, **values):
        revisions = revisions or self._requirement()
        return (
            self.env["project.agile.solution.task.intent"]
            .with_user(self.manager)
            .create(
                {
                    "solution_id": self.solution.id,
                    "operation": "create",
                    "name": "SYNTHETIC deliberate Task",
                    "description": "<p>Explicit proposed description.</p>",
                    "agile_item_type_id": self.env.ref(
                        "project_agile.project_agile_item_type_story"
                    ).id,
                    "requirement_revision_ids": [Command.set(revisions.ids)],
                    **values,
                }
            )
        )

    def _link(self, revision, task, **values):
        return (
            self.env["project.agile.requirement.task.link"]
            .with_user(self.manager)
            .create(
                {"requirement_revision_id": revision.id, "task_id": task.id, **values}
            )
        )

    def test_history_publication_fields_are_server_owned(self):
        revision, task = self._requirement(), self._task()
        document = self._revision()
        for record, field in (
            (self.project.with_user(self.manager), "solution_last_history_ref"),
            (self.solution.with_user(self.manager), "_last_document_id"),
            (self.solution.with_user(self.manager), "_last_approved_revision_id"),
            (document.document_id, "_last_revision_id"),
            (document, "_narrative_version"),
            (revision.requirement_id, "_latest_revision_ref"),
            (revision, "_last_acceptance_id"),
            (task, "solution_last_reference"),
        ):
            record = record.with_user(self.manager)
            with self.assertRaises(AccessError):
                record.write({field: False})
        fresh_document = document.document_id.create(
            {
                "name": "SYNTHETIC default isolation",
                "solution_id": self.solution.id,
            }
        )
        fresh_identity = revision.requirement_id.create(
            {
                "name": "SYNTHETIC default isolation",
                "solution_id": self.solution.id,
            }
        )
        for model, field, values in (
            (
                self.project.with_user(self.manager),
                "solution_last_history_ref",
                {"name": "SYNTHETIC ordinary Project"},
            ),
            (
                self.solution.with_user(self.manager),
                "_last_document_id",
                {"name": "SYNTHETIC ordinary solution", "project_id": self.project.id},
            ),
            (
                self.solution.with_user(self.manager),
                "_last_approved_revision_id",
                {"name": "SYNTHETIC ordinary solution", "project_id": self.project.id},
            ),
            (
                document.document_id,
                "_last_revision_id",
                {
                    "name": "SYNTHETIC ordinary document",
                    "solution_id": self.solution.id,
                },
            ),
            (
                revision.requirement_id,
                "_latest_revision_ref",
                {
                    "name": "SYNTHETIC ordinary requirement",
                    "solution_id": self.solution.id,
                },
            ),
            (
                revision,
                "_last_acceptance_id",
                {
                    **revision._copy_content_values(),
                    "requirement_id": fresh_identity.id,
                },
            ),
            (
                document,
                "_narrative_version",
                {
                    "title": "SYNTHETIC ordinary revision",
                    "document_id": fresh_document.id,
                },
            ),
            (
                task,
                "solution_last_reference",
                {
                    "name": "SYNTHETIC ordinary Task",
                    "project_id": self.project.id,
                    "agile_item_type_id": task.agile_item_type_id.id,
                },
            ),
        ):
            model = model.with_user(self.manager)
            with self.assertRaises(AccessError):
                model.create({**values, field: False})
            forged = model.with_context(
                **{
                    "default_" + field: "project.agile.requirement.task.link,1"
                    if field.endswith(("ref", "reference"))
                    else 5000
                }
            )
            with self.assertRaises(AccessError):
                forged.create(values)
            created = model.create(values)
            self.assertFalse(created.sudo()[field])
            if model._name == "project.task":
                self.assertTrue(self._link(revision, created))
                self.assertEqual(
                    created.sudo().solution_last_reference.task_id, created
                )

    def test_many_to_many_exact_edges_seal_without_changing_work(self):
        first, second = self._requirement(), self._requirement(requirement_type="nfr")
        task, another = self._task(), self._task()
        fields = [
            "name",
            "description",
            "state",
            "stage_id",
            "agile_story_points",
            "agile_backlog_sequence",
            "agile_acceptance_criteria",
        ]
        task.write(
            {
                "description": "<p>Manual description</p>",
                "agile_acceptance_criteria": "<p>Manual criteria</p>",
                "agile_backlog_sequence": 43,
            }
        )
        before = task.read(fields)
        edges = (
            self._link(first, task)
            | self._link(second, task)
            | self._link(second, another)
        )
        self.assertEqual(len(edges), 3)
        self.assertTrue(first.sealed and second.sealed)
        self.assertEqual(task.read(fields), before)
        successor = first.browse(first.requirement_id.action_new_revision()["res_id"])
        successor.write({"description": "Later delivery intent"})
        self.assertEqual(task.read(fields), before)
        self.assertEqual(edges.requirement_revision_id, first | second)

    def test_preview_then_wizard_confirm_is_idempotent(self):
        count = self.env["project.task"].search_count([])
        intent = self._intent()
        self.assertEqual(self.env["project.task"].search_count([]), count)
        action = intent.action_request_confirmation()
        wizard = (
            self.env[action["res_model"]]
            .with_user(self.manager)
            .with_context(**action["context"])
            .create({})
        )
        result = wizard.action_confirm()
        self.assertEqual(result["res_id"], intent.task_id.id)
        self.assertEqual(intent.action_confirm()["res_id"], result["res_id"])
        self.assertEqual(self.env["project.task"].search_count([]), count + 1)
        self.assertEqual(intent.state, "consumed")
        self.assertTrue(intent.consumed_at)
        self.assertEqual(
            self.env["project.agile.requirement.task.link"].search_count(
                [("task_id", "=", intent.task_id.id)]
            ),
            1,
        )

    def test_existing_work_confirm_never_writes_manual_values(self):
        task = self._task(
            description="<p>Keep me</p>",
            agile_acceptance_criteria="<p>Human criteria</p>",
            agile_backlog_sequence=37,
        )
        before = task.read(
            [
                "name",
                "description",
                "state",
                "stage_id",
                "agile_acceptance_criteria",
                "agile_backlog_sequence",
                "agile_story_points",
            ]
        )
        intent = self._intent(
            operation="link", task_id=task.id, name="Not the native Task name"
        )
        self.assertEqual(intent.action_confirm()["res_id"], task.id)
        self.assertEqual(task.read(list(before[0].keys())), before)

    def test_confirm_strips_forged_context_defaults_and_workflow_hints(self):
        intent = self._intent()
        action = intent.with_context(
            default_agile_story_points=89,
            default_agile_backlog_sequence=777,
            default_agile_acceptance_criteria="<p>Injected</p>",
            default_parent_id=True,
            default_sprint_id=True,
        ).action_confirm()
        task = self.env["project.task"].browse(action["res_id"])
        self.assertEqual(task.agile_story_points, 0)
        self.assertEqual(task.agile_backlog_sequence, 10)
        self.assertFalse(task.agile_acceptance_criteria)
        self.assertFalse(task.parent_id)
        if "sprint_id" in task._fields:
            self.assertFalse(task.sprint_id)

    def test_changed_working_revision_rejects_pending_preview_atomically(self):
        revision = self._requirement()
        intent = self._intent(revision)
        count = self.env["project.task"].search_count([])
        revision.write({"rationale": "Different observed intent"})
        with self.assertRaises(ValidationError):
            intent.action_confirm()
        self.assertEqual(self.env["project.task"].search_count([]), count)
        self.assertEqual(intent.state, "preview")
        self.assertFalse(revision.sealed)
        self._intent(revision).action_confirm()

    def test_new_requirement_head_rejects_pending_but_not_consumed_retry(self):
        revision = self._requirement()
        consumed = self._intent(revision)
        task_id = consumed.action_confirm()["res_id"]
        pending = self._intent(revision)
        revision.requirement_id.action_new_revision()
        with self.assertRaises(ValidationError):
            pending.action_confirm()
        self.assertEqual(consumed.action_confirm()["res_id"], task_id)

    def test_specification_head_change_invalidates_preview_separate_from_approval(self):
        requirement = self._requirement()
        document = self._revision(
            requirement_revision_ids=[Command.set(requirement.ids)]
        )
        intent = self._intent(requirement, document_revision_id=document.id)
        document.write({"title": "Changed draft specification"})
        with self.assertRaises(ValidationError):
            intent.action_confirm()
        fresh = self._intent(requirement, document_revision_id=document.id)
        document.action_submit()
        with self.assertRaises(ValidationError):
            fresh.action_confirm()
        self.assertEqual(document.state, "review")

    def test_failure_after_task_and_links_rolls_back_everything(self):
        revision = self._requirement()
        intent = self._intent(revision)
        count = self.env["project.task"].search_count([])
        original = type(intent)._link_task

        def fail(record, task):
            original(record, task)
            # Exact synthetic fault-injection text is not a user-facing translation.
            raise ValidationError(  # pylint: disable=translation-required
                "SYNTHETIC failure after edge writes"
            )

        with patch.object(type(intent), "_link_task", fail):
            with self.assertRaises(ValidationError):
                intent.action_confirm()
        self.assertEqual(self.env["project.task"].search_count([]), count)
        self.assertFalse(intent.task_id)
        self.assertEqual(intent.state, "preview")
        self.assertFalse(revision.sealed)
        self.assertFalse(
            self.env["project.agile.requirement.task.link"].search(
                [("requirement_revision_id", "=", revision.id)]
            )
        )
        intent.action_confirm()

    def test_real_user_cannot_create_link_preview_confirm_or_retire(self):
        revision, task = self._requirement(), self._task()
        edge = self._link(revision, task)
        for records, values in (
            (
                edge.with_user(self.user),
                {"requirement_revision_id": revision.id, "task_id": task.id},
            ),
            (
                self.env["project.agile.solution.task.intent"].with_user(self.user),
                {"solution_id": self.solution.id, "name": "Denied"},
            ),
        ):
            with self.assertRaises(AccessError):
                records.create(values)
        with self.assertRaises(AccessError):
            edge.with_user(self.user).action_retire("Unauthorized")
        intent = self._intent(revision)
        with self.assertRaises(AccessError):
            intent.with_user(self.user).action_confirm()

    def test_concrete_task_rule_denies_manager_link_preview_and_consumed_retry(self):
        revision, task = self._requirement(), self._task()
        intent = self._intent(revision, operation="link", task_id=task.id)
        intent.action_confirm()
        self._hide("project.task", task)
        for action in (
            lambda: self._link(revision, task),
            lambda: self._intent(revision, operation="link", task_id=task.id),
            intent.action_confirm,
        ):
            with self.assertRaises(AccessError):
                action()
        self.assertNotIn(intent, intent.search([]))
        edges = self.env["project.agile.requirement.task.link"].with_user(self.manager)
        self.assertEqual(edges.search_count([("task_id", "=", task.id)]), 0)
        self.assertEqual(
            edges._read_group([("task_id", "=", task.id)], ["task_id"], ["__count"]), []
        )

    def test_hidden_requirement_filters_entire_intent_and_edges_search_export(self):
        revision, other = self._requirement(), self._requirement()
        intent = self._intent(revision | other)
        task = self.env["project.task"].browse(intent.action_confirm()["res_id"])
        edges = (
            self.env["project.agile.requirement.task.link"]
            .with_user(self.manager)
            .search([("task_id", "=", task.id)])
        )
        self._hide("project.agile.requirement.revision", revision)
        self.assertNotIn(intent, intent.search([]))
        with self.assertRaises(AccessError):
            intent.read(["name", "preview_text"])
        with self.assertRaises(AccessError):
            edges.export_data(["requirement_revision_id", "task_id"])
        self.assertEqual(
            edges.search_count([("requirement_revision_id", "=", revision.id)]), 0
        )

    def test_foreign_project_and_company_and_literal_ids_are_rejected(self):
        revision = self._requirement()
        foreign_task = self._spike(
            project=self.foreign, item_type="story"
        ).with_context(allowed_company_ids=(self.company | self.other_company).ids)
        with self.assertRaises(ValidationError):
            self._link(revision, foreign_task)
        with self.assertRaises(ValidationError):
            self._intent(revision, operation="link", task_id=foreign_task.id)
        with self.assertRaises(ValidationError):
            self.env["project.agile.requirement.task.link"].with_user(
                self.manager
            ).with_context(
                allowed_company_ids=(self.company | self.other_company).ids
            ).create(
                {"task_id": foreign_task.id, "requirement_revision_id": revision.id}
            )
        for value in (True, str(self._task().id), -1):
            with self.assertRaises(ValidationError):
                self._link(revision, self._task(), task_id=value)
        with self.assertRaises(ValidationError):
            self._intent(revision, requirement_revision_ids=[Command.set([True])])

    def test_bounded_proposal_no_generic_api_or_forged_audit(self):
        revision = self._requirement()
        for values in (
            {"token": "Caller chosen"},
            {"creator_id": self.user.id},
            {"state": "consumed"},
            {"model": "project.task"},
            {"name": "x" * 201},
            {"description": "x" * 20001},
        ):
            with self.assertRaises(ValidationError):
                self._intent(revision, **values)
        with self.assertRaises(ValidationError):
            self._intent(
                revision, requirement_revision_ids=[Command.set(revision.ids * 21)]
            )
        intent = self._intent(revision)
        with self.assertRaises(ValidationError):
            intent.sudo().write({"name": "Hidden overwrite"})
        with self.assertRaises(ValidationError):
            intent.unlink()
        with self.assertRaises(AccessError):
            intent.read(["_source_digest"])

    def test_task_acl_create_deny_is_not_elevated_by_confirmation(self):
        intent = self._intent()
        acls = self.env["ir.model.access"].search(
            [
                ("model_id", "=", self.env["ir.model"]._get_id("project.task")),
                ("perm_create", "=", True),
            ]
        )
        acls.write({"perm_create": False})
        self.env.registry.clear_cache()
        with self.assertRaises(AccessError):
            intent.action_confirm()
        self.assertFalse(intent.task_id)
        self.assertEqual(intent.state, "preview")

    def test_retirement_and_archive_preserve_retry_identity_and_exact_history(self):
        intent = self._intent()
        task_id = intent.action_confirm()["res_id"]
        edge = (
            self.env["project.agile.requirement.task.link"]
            .with_user(self.manager)
            .search([("task_id", "=", task_id)])
        )
        edge.action_retire("SYNTHETIC replaced by revised delivery intent")
        self.assertFalse(edge.active)
        self.assertEqual(edge.retired_by_id, self.manager)
        with self.assertRaises(ValidationError):
            edge.sudo().write({"requirement_revision_id": self._requirement().id})
        intent.task_id.write({"active": False})
        self.assertEqual(intent.action_confirm()["res_id"], task_id)
        with self.assertRaises(ValidationError):
            intent.task_id.unlink()
        with self.assertRaises(ValidationError):
            self._link(self._requirement(), intent.task_id)

    def test_confirmation_wizard_cannot_disclose_another_creators_intent(self):
        intent = self._intent()
        self.user.write(
            {
                "group_ids": [
                    Command.link(self.env.ref("project.group_project_manager").id)
                ]
            }
        )
        with self.assertRaises(AccessError):
            intent.with_user(self.user).read(["name"])
        # Transient ownership alone cannot authorize a related intent projection.
        with self.assertRaises(AccessError):
            wizard = (
                self.env["project.agile.solution.task.confirm.wizard"]
                .with_user(self.user)
                .create({"intent_id": intent.id})
            )
            wizard.read(["name", "description"])

    def test_confirmation_wizard_rechecks_hidden_reference_after_creation(self):
        revision = self._requirement()
        intent = self._intent(revision)
        model = self.env["project.agile.solution.task.confirm.wizard"].with_user(
            self.manager
        )
        wizard = model.create({"intent_id": intent.id})
        self.assertEqual(wizard.read(["name"])[0]["name"], intent.name)
        self.assertIn(wizard, model.search([]))
        self._hide("project.agile.requirement.revision", revision)
        self.assertNotIn(wizard, model.search([]))
        self.assertEqual(model.search_count([("id", "=", wizard.id)]), 0)
        self.assertEqual(model.name_search(intent.name), [])
        with self.assertRaises(AccessError):
            wizard.read(["name", "description"])
        with self.assertRaises(AccessError):
            wizard.export_data(["name"])
        with self.assertRaises(AccessError):
            model.create({"intent_id": intent.id})

    def test_confirmation_wizard_rejects_literal_ids_and_projection_overwrites(self):
        intent = self._intent()
        model = self.env["project.agile.solution.task.confirm.wizard"].with_user(
            self.manager
        )
        for value in (True, str(intent.id), -1):
            with self.assertRaises(ValidationError):
                model.create({"intent_id": value})
        with self.assertRaises(ValidationError):
            model.create({"intent_id": intent.id, "name": "Forged projection"})
        wizard = model.create({"intent_id": intent.id})
        with self.assertRaises(ValidationError):
            wizard.write({"intent_id": self._intent().id})

    def test_real_native_form_shows_preview_and_confirmation(self):
        requirement = self._requirement()
        model = self.env["project.agile.solution.task.intent"].with_user(self.manager)
        with Form(model) as form:
            form.solution_id = self.solution
            form.operation = "create"
            form.name = "SYNTHETIC native preview"
            form.agile_item_type_id = self.env.ref(
                "project_agile.project_agile_item_type_story"
            )
            form.requirement_revision_ids.add(requirement)
        intent = form.record
        self.assertEqual(intent.state, "preview")
        self.assertIn(requirement.requirement_id.key, intent.preview_text)
        action = intent.action_request_confirmation()
        with Form(
            self.env[action["res_model"]]
            .with_user(self.manager)
            .with_context(**action["context"])
        ) as wizard:
            self.assertEqual(wizard.name, intent.name)
        wizard.record.action_confirm()
