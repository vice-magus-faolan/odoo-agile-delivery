"""Actual nonadmin native Task boundary, freshness, atomicity and retry checks."""

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
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

    def _refinement(self, edge, *, adoption=False):
        action = (
            edge.action_request_adoption()
            if adoption
            else edge.action_request_refinement()
        )
        return (
            self.env[action["res_model"]]
            .with_user(edge.env.user)
            .browse(action["res_id"])
        )

    def test_refinement_form_preserves_approved_acceptance_and_other_work(self):
        requirement, task, other = self._requirement(), self._task(), self._task()
        baseline = self._revision(
            requirement_revision_ids=[Command.set(requirement.ids)]
        )
        self._approve(baseline)
        accepted = (
            self.env["project.agile.requirement.acceptance"]
            .with_user(self.manager)
            .create(
                {
                    "requirement_revision_id": requirement.id,
                    "document_revision_id": baseline.id,
                    "decision": "accepted",
                    "authority_label": "Exact baseline approver",
                    "criteria_evaluated": requirement.acceptance_expectations,
                    "evidence": "SYNTHETIC observed original content",
                }
            )
        )
        snapshot = baseline.action_read_snapshot()
        # Freeze the acceptance-domain payload, not native log_access metadata
        # affected by deferred stored-related recomputation.
        acceptance_fields = [
            "requirement_revision_id",
            "document_revision_id",
            "decision",
            "decision_source",
            "publication_id",
            "publication_sha256",
            "portal_partner_id",
            "authority_label",
            "criteria_evaluated",
            "evidence",
            "recorded_by_id",
            "recorded_by_label",
            "recorded_at",
            "supersedes_id",
        ]
        acceptance = accepted.read(acceptance_fields, load=None)[0]
        original = requirement._snapshot_values()
        edge = self._link(requirement, task, document_revision_id=baseline.id)
        other_edge = self._link(requirement, other, document_revision_id=baseline.id)
        task.write({"agile_acceptance_criteria": "<p>Keep manual checks</p>"})
        before = task.read(
            [
                "name",
                "description",
                "state",
                "agile_acceptance_criteria",
                "agile_story_points",
                "agile_backlog_sequence",
            ]
        )
        # Two user steps: open dialog, then edit and Apply (native saves edits).
        wizard = self._refinement(edge)
        with Form(wizard) as form:
            self.assertEqual(
                form.previous_expectations, requirement.acceptance_expectations
            )
            form.acceptance_expectations = (
                "Buyer confirms <only> their dispatch & receipt"
            )
        result = wizard.action_confirm()
        replacement = edge.sudo()._refinement_link_id.with_user(self.manager)
        successor = replacement.requirement_revision_id
        self.assertEqual(result["res_id"], task.id)
        self.assertEqual(successor.predecessor_id, requirement)
        self.assertEqual(successor.number, 2)
        self.assertTrue(successor.sealed)
        self.assertFalse(replacement.document_revision_id)
        self.assertFalse(edge.active)
        self.assertTrue(edge.retirement_reason)
        self.assertEqual(edge.retired_by_id, self.manager)
        self.assertTrue(other_edge.active)
        self.assertEqual(other_edge.requirement_revision_id, requirement)
        self.assertEqual(task.read(list(before[0])), before)
        self.assertIn(
            "Buyer confirms &lt;only&gt; their dispatch &amp; receipt",
            task.with_user(self.user).solution_requirement_acceptance,
        )
        self.assertEqual(baseline.action_read_snapshot(), snapshot)
        self.assertEqual(accepted.read(acceptance_fields, load=None)[0], acceptance)
        self.assertEqual(requirement._snapshot_values(), original)
        self.assertEqual(baseline.requirement_revision_ids, requirement)
        self.assertEqual(wizard.action_confirm(), result)
        self.assertEqual(
            requirement.requirement_id.revision_ids, successor | requirement
        )
        with self.assertRaises(ValidationError):
            requirement.sudo().write({"acceptance_expectations": "Rewrite agreement"})
        with self.assertRaises(ValidationError):
            successor.sudo().write(
                {"acceptance_expectations": "Rewrite linked successor"}
            )
        with self.assertRaises(ValidationError):
            baseline.write({"requirement_revision_ids": [Command.set(successor.ids)]})

        untouched_task = self._task()
        untouched = self._link(requirement, untouched_task)
        other.write({"agile_acceptance_criteria": "<p>B authored criteria</p>"})
        other_values = other.read(["name", "agile_acceptance_criteria", "state"])
        self.user.write(
            {
                "group_ids": [
                    Command.link(
                        self.env.ref("project_agile_solution.group_business_analyst").id
                    )
                ]
            }
        )
        selected = other_edge.with_user(self.user)
        adoption = self._refinement(selected, adoption=True)
        with Form(
            adoption, view="project_agile_solution.view_requirement_adopt_wizard"
        ) as form:
            self.assertEqual(form.task_id, other)
            self.assertEqual(form.target_revision_id, successor)
            self.assertEqual(form.target_number, 2)
            self.assertEqual(
                form.target_expectations, successor.acceptance_expectations
            )
            self.assertEqual(
                form.previous_expectations, requirement.acceptance_expectations
            )
        result_b = adoption.action_confirm()
        self.assertEqual(result_b["res_id"], other.id)
        adopted = selected.sudo()._adoption_link_id.with_user(self.user)
        self.assertEqual(adopted.requirement_revision_id, successor)
        self.assertFalse(adopted.document_revision_id)
        self.assertFalse(selected.active)
        self.assertEqual(selected.retired_by_id, self.user)
        self.assertTrue(selected.retirement_reason)
        self.assertEqual(adopted.search([("task_id", "=", other.id)]), adopted)
        self.assertEqual(adoption.action_confirm(), result_b)
        self.assertTrue(untouched.active)
        self.assertEqual(untouched.requirement_revision_id, requirement)
        self.assertEqual(other.read(list(other_values[0])), other_values)
        self.assertEqual(baseline.action_read_snapshot(), snapshot)
        self.assertEqual(accepted.read(acceptance_fields, load=None)[0], acceptance)
        self.assertEqual(requirement._snapshot_values(), original)
        self.assertEqual(
            requirement.requirement_id._complete_revisions(), requirement | successor
        )

    def test_refinement_failure_rolls_back_successor_edge_and_retirement(self):
        requirement, task = self._requirement(), self._task()
        edge = self._link(requirement, task)
        wizard = self._refinement(edge)
        wizard.write({"acceptance_expectations": "Revised expectation"})
        before = task.solution_requirement_acceptance
        retire = type(edge).action_retire

        def fail_after_retirement(records, reason):
            retire(records, reason)
            raise ValidationError("SYNTHETIC failed refinement")  # pylint: disable=translation-required

        with patch.object(type(edge), "action_retire", fail_after_retirement):
            with self.assertRaises(ValidationError):
                wizard.action_confirm()
        self.assertTrue(edge.active)
        self.assertFalse(edge.retired_at)
        self.assertFalse(edge.sudo()._refinement_link_id)
        self.assertEqual(requirement.requirement_id.revision_ids, requirement)
        self.assertEqual(task.solution_requirement_acceptance, before)
        self.assertEqual(edge.search_count([("task_id", "=", task.id)]), 1)
        wizard.action_confirm()

    def test_refinement_stale_head_retirement_and_different_retry_reject(self):
        requirement, task = self._requirement(), self._task()
        edge = self._link(requirement, task)
        wizard, competing = self._refinement(edge), self._refinement(edge)
        wizard.write({"acceptance_expectations": "Winner proposal"})
        competing.write({"acceptance_expectations": "Competing proposal"})
        wizard.action_confirm()
        with self.assertRaises(ValidationError):
            competing.action_confirm()
        replacement = edge.sudo()._refinement_link_id.with_user(self.manager)
        stale = self._refinement(replacement)
        stale.write({"acceptance_expectations": "Must not replace a newer head"})
        successor = requirement.browse(
            requirement.requirement_id.action_new_revision()["res_id"]
        )
        with self.assertRaises(ValidationError):
            stale.action_confirm()
        self.assertTrue(replacement.active)
        self.assertFalse(successor.sealed)
        self.assertNotIn("Must not replace", task.solution_requirement_acceptance)
        replacement.action_retire("Explicit coverage withdrawal")
        with self.assertRaises(ValidationError):
            stale.action_confirm()
        for value in (False, " ", "x" * 20001):
            with self.assertRaises(ValidationError):
                edge.action_refine_acceptance(value)

    def test_refinement_current_access_and_server_managed_selection(self):
        requirement, task = self._requirement(), self._task()
        edge = self._link(requirement, task)
        wizard = self._refinement(edge)
        wizard.write({"acceptance_expectations": "Visible permitted refinement"})
        with self.assertRaises(AccessError):
            edge.with_user(self.user).action_refine_acceptance("Unauthorized")
        with self.assertRaises(ValidationError):
            wizard.write({"link_id": edge.id})
        for record in (requirement, task, self.solution):
            self.assertTrue(wizard.read(["previous_expectations"]))
            rule = self._hide(record._name, record)
            self.env.invalidate_all()
            self.assertFalse(wizard.search([("id", "=", wizard.id)]))
            for action in (
                lambda: wizard.read(["previous_expectations"]),
                lambda: wizard.export_data(["previous_expectations"]),
                wizard.action_confirm,
            ):
                with self.assertRaises(AccessError):
                    action()
            self.assertTrue(edge.sudo().active)
            self.assertFalse(edge.sudo()._refinement_link_id)
            rule.unlink()
            self.env.invalidate_all()
        wizard.action_confirm()
        with self.assertRaises(AccessError):
            edge.read(["_refinement_link_id"])

    def test_adoption_rechecks_authority_stale_target_and_atomic_replacement(self):
        requirement, task, other = self._requirement(), self._task(), self._task()
        first, selected = self._link(requirement, task), self._link(requirement, other)
        first.action_refine_acceptance("Already agreed successor expectations")
        target = first.sudo()._refinement_link_id.requirement_revision_id.with_user(
            self.manager
        )
        wizard = self._refinement(selected, adoption=True)
        for value in (False, True, 0, "2", requirement.id, self._requirement().id):
            with self.assertRaises(ValidationError):
                selected.action_adopt_revision(value)
        for action in (
            selected.with_user(self.user).action_request_adoption,
            lambda: selected.with_user(self.user)
            .sudo()
            .action_adopt_revision(target.id),
        ):
            with self.assertRaises(AccessError):
                action()
        with self.assertRaises(ValidationError):
            wizard.write({"target_revision_id": target.id})
        for record in (target, other, self.project):
            self.assertTrue(wizard.read(["target_expectations"]))
            rule = self._hide(record._name, record)
            self.env.invalidate_all()
            self.assertFalse(wizard.search([("id", "=", wizard.id)]))
            for action in (
                lambda: wizard.read(["target_expectations"]),
                lambda: wizard.export_data(["target_expectations"]),
                wizard.action_confirm,
                lambda: selected.action_adopt_revision(target.id),
            ):
                with self.assertRaises(AccessError):
                    action()
            self.assertTrue(selected.sudo().active)
            self.assertFalse(selected.sudo()._adoption_link_id)
            rule.unlink()
            self.env.invalidate_all()
        with self.assertRaises(AccessError):
            selected.with_context(
                allowed_company_ids=self.other_company.ids
            ).action_adopt_revision(target.id)
        retire = type(selected).action_retire

        def fail_after_retirement(records, reason):
            retire(records, reason)
            raise ValidationError("SYNTHETIC failed adoption")  # pylint: disable=translation-required

        with patch.object(type(selected), "action_retire", fail_after_retirement):
            with self.assertRaises(ValidationError):
                wizard.action_confirm()
        self.assertTrue(selected.active)
        self.assertFalse(selected.retired_at)
        self.assertFalse(selected.sudo()._adoption_link_id)
        self.assertEqual(selected.search([("task_id", "=", other.id)]), selected)
        self.assertEqual(
            requirement.requirement_id._complete_revisions(), requirement | target
        )
        newer = requirement.browse(
            requirement.requirement_id.action_new_revision()["res_id"]
        )
        self.assertFalse(newer.sealed)
        for action in (
            wizard.action_confirm,
            lambda: selected.action_adopt_revision(target.id),
        ):
            with self.assertRaises(ValidationError):
                action()
        self.assertTrue(selected.active)
        self.assertFalse(selected.sudo()._adoption_link_id)
        with self.assertRaises(ValidationError):
            selected.action_adopt_revision(newer.id)

    def test_task_displays_all_active_exact_acceptance_and_retirement(self):
        first = self._requirement(
            title="Dispatch approval",
            acceptance_expectations="Buyer approves <only> their dispatch",
        )
        second = self._requirement(
            title="Delivery evidence",
            verification_method="Inspect signed delivery receipt",
        )
        task = self._task()
        self._link(first, task)
        edge = self._link(second, task)
        successor = first.browse(first.requirement_id.action_new_revision()["res_id"])
        successor.write({"title": "Unlinked successor must stay absent"})
        member = task.with_user(self.user)
        shown = member.read(["solution_requirement_acceptance"])[0][
            "solution_requirement_acceptance"
        ]
        for text in (
            first.title,
            second.title,
            "Revision 1",
            "Acceptance Expectations",
            "Verification Method",
            second.verification_method,
        ):
            self.assertIn(text, shown)
        self.assertIn("Buyer approves &lt;only&gt; their dispatch", shown)
        self.assertNotIn(successor.title, shown)
        edge.action_retire("Replaced delivery evidence")
        shown = member.read(["solution_requirement_acceptance"])[0][
            "solution_requirement_acceptance"
        ]
        self.assertIn(first.title, shown)
        self.assertNotIn(second.title, shown)
        with Form(member) as form:
            self.assertIn(first.title, form.solution_requirement_acceptance)
            self.assertNotIn(second.title, form.solution_requirement_acceptance)

    def test_hidden_requirement_omission_keeps_native_task_access(self):
        revision, task = (
            self._requirement(title="Private requirement identity"),
            self._task(),
        )
        self._link(revision, task)
        # Privileged caches and earlier reads do not grant later presentation access.
        self.assertIn(revision.title, task.solution_requirement_acceptance)
        member = task.with_user(self.user)
        self.assertIn(
            revision.title,
            member.read(["solution_requirement_acceptance"])[0][
                "solution_requirement_acceptance"
            ],
        )
        for record in (revision, revision.requirement_id, self.solution):
            rule = self._hide(record._name, record)
            self.env.invalidate_all()
            with self.assertRaises(AccessError):
                record.with_user(self.user).read(["display_name"])
            self.assertEqual(
                member.read(["name", "solution_requirement_acceptance"])[0][
                    "solution_requirement_acceptance"
                ],
                False,
            )
            self.assertEqual(
                member.export_data(["solution_requirement_acceptance"])["datas"], [[""]]
            )
            with Form(member) as form:
                self.assertFalse(form.solution_requirement_acceptance)
            rule.unlink()
            self.env.invalidate_all()
        acls = self.env["ir.model.access"].search(
            [
                ("model_id", "=", self.env["ir.model"]._get_id(revision._name)),
                ("perm_read", "=", True),
            ]
        )
        acls.write({"perm_read": False})
        self.env.registry.clear_cache()
        self.env.invalidate_all()
        self.assertFalse(
            member.read(["solution_requirement_acceptance"])[0][
                "solution_requirement_acceptance"
            ]
        )
        with Form(member) as form:
            self.assertFalse(form.solution_requirement_acceptance)

    def test_explicit_two_requirement_criteria_preview_saved_equality_and_editing(self):
        first = self._requirement(
            acceptance_expectations="Given a buyer <A>\n"
            "When dispatch is approved & saved"
        )
        second = self._requirement(
            acceptance_expectations="Then the warehouse sees the approved dispatch"
        )
        revisions = second | first
        off = self._intent(revisions)
        self.assertFalse(off.copy_acceptance_expectations)
        self.assertFalse(off.acceptance_criteria_preview)
        off.action_confirm()
        self.assertFalse(off.task_id.agile_acceptance_criteria)
        intent = self._intent(revisions, copy_acceptance_expectations=True)
        preview = intent.acceptance_criteria_preview
        self.assertEqual(
            preview,
            "<p>Given a buyer &lt;A&gt;<br>"
            "When dispatch is approved &amp; saved</p>"
            "<p>Then the warehouse sees the approved dispatch</p>",
        )
        wizard = (
            self.env["project.agile.solution.task.confirm.wizard"]
            .with_user(self.manager)
            .create({"intent_id": intent.id})
        )
        self.assertTrue(wizard.copy_acceptance_expectations)
        self.assertEqual(wizard.acceptance_criteria_preview, preview)
        wizard.action_confirm()
        self.assertEqual(intent.task_id.agile_acceptance_criteria, preview)
        self.assertEqual(intent.action_confirm()["res_id"], intent.task_id.id)
        intent.task_id.write(
            {"agile_acceptance_criteria": "<p>Task-specific authored checks</p>"}
        )
        intent.action_confirm()
        self.assertEqual(
            intent.task_id.agile_acceptance_criteria,
            "<p>Task-specific authored checks</p>",
        )

    def test_copy_choice_cannot_be_defaulted_mutated_or_applied_to_existing_work(self):
        revision = self._requirement()
        model = (
            self.env["project.agile.solution.task.intent"]
            .with_user(self.manager)
            .with_context(default_copy_acceptance_expectations=True)
        )
        self.assertFalse(
            model.default_get(["copy_acceptance_expectations"])[
                "copy_acceptance_expectations"
            ]
        )
        intent = model.create(
            {
                "solution_id": self.solution.id,
                "operation": "create",
                "name": "No implicit copy",
                "agile_item_type_id": self.env.ref(
                    "project_agile.project_agile_item_type_story"
                ).id,
                "requirement_revision_ids": [Command.set(revision.ids)],
            }
        )
        self.assertFalse(intent.copy_acceptance_expectations)
        with self.assertRaises(ValidationError):
            intent.write({"copy_acceptance_expectations": True})
        intent.with_context(
            copy_acceptance_expectations=True, default_copy_acceptance_expectations=True
        ).action_confirm()
        self.assertFalse(intent.task_id.agile_acceptance_criteria)
        task = self._task(agile_acceptance_criteria="<p>Keep manual checks</p>")
        with self.assertRaises(ValidationError):
            self._intent(
                revision,
                operation="link",
                task_id=task.id,
                copy_acceptance_expectations=True,
            )
        self.assertEqual(task.agile_acceptance_criteria, "<p>Keep manual checks</p>")

    def test_opted_in_copy_rejects_stale_or_inaccessible_source_atomically(self):
        revision = self._requirement()
        intent = self._intent(revision, copy_acceptance_expectations=True)
        inspected = intent.acceptance_criteria_preview
        revision.write({"acceptance_expectations": "Changed client agreement"})
        with self.assertRaises(ValidationError):
            intent.action_confirm()
        self.assertFalse(intent.task_id)
        fresh = self._intent(revision, copy_acceptance_expectations=True)
        self.assertNotEqual(fresh.acceptance_criteria_preview, inspected)
        rule = self._hide(revision._name, revision)
        self.env.invalidate_all()
        # Depending on native relation prefetch, Odoo denies the intent/row or
        # hides its selection before validation. Both must leave creation untouched.
        with self.assertRaises(UserError) as denied:
            fresh.action_confirm()
        self.assertIn(type(denied.exception), (AccessError, ValidationError))
        # Observe retained state internally; do not elevate the action under test.
        self.assertFalse(fresh.sudo().task_id)
        self.assertEqual(fresh.sudo().state, "preview")
        rule.unlink()
        self.env.invalidate_all()
        fresh.action_confirm()
        self.assertEqual(
            fresh.task_id.agile_acceptance_criteria, fresh.acceptance_criteria_preview
        )

    def test_native_short_reference_commands_keep_literal_ids_and_no_mutation(self):
        revision = self._requirement()
        intent = self._intent(
            revision,
            requirement_revision_ids=[[4, revision.id]],
            copy_acceptance_expectations=True,
        )
        intent.action_confirm()
        self.assertEqual(
            intent.task_id.agile_acceptance_criteria, intent.acceptance_criteria_preview
        )
        for command in (
            [4, True],
            [1, revision.id],
            [2, revision.id],
            [6, 0],
            [4, revision.id, 0, 999],
            [True, revision.id],
        ):
            with self.assertRaises(ValidationError):
                self._intent(revision, requirement_revision_ids=[command])

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
                # Native create overrides may mutate inputs before access denial.
                forged.create(dict(values))
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
            form.copy_acceptance_expectations = True
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
            self.assertEqual(
                wizard.acceptance_criteria_preview, intent.acceptance_criteria_preview
            )
        wizard.record.action_confirm()
        self.assertEqual(
            intent.task_id.agile_acceptance_criteria, intent.acceptance_criteria_preview
        )
