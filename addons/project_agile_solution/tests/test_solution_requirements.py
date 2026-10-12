"""Real nonadmin FR/NFR, typed context, exact membership and narrative regressions."""

import json
from pathlib import Path

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import Form

from .test_solution_baseline import TestSolutionBaseline
from .test_solution_lineage import TestSolutionLineage


class TestSolutionRequirements(TestSolutionLineage):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.document = (
            cls.env["project.agile.solution.document"]
            .with_user(cls.manager)
            .create(
                {
                    "name": "SYNTHETIC Requirement Brief",
                    "solution_id": cls.solution.id,
                    "kind": "spec",
                    "approver_id": cls.manager.id,
                }
            )
        )

    _project = TestSolutionLineage.__dict__["_project"]
    _revision = TestSolutionBaseline._revision
    _approve = TestSolutionBaseline._approve

    def _requirement(self, solution=None, **values):
        identities = (
            self.env["project.agile.requirement"]
            .with_user(self.manager)
            .with_context(allowed_company_ids=(self.company | self.other_company).ids)
        )
        identity = identities.create(
            {
                "solution_id": (solution or self.solution).id,
                "name": "SYNTHETIC own-request intent",
            }
        )
        revision = (
            self.env["project.agile.requirement.revision"]
            .with_env(identities.env)
            .create(
                {
                    "requirement_id": identity.id,
                    "title": "SYNTHETIC own request",
                    "requirement_type": "fr",
                    "description": "A requester submits their own request.",
                    "rationale": "Capture service demand",
                    "priority": "must",
                    "verification_method": "Negative requester identity matrix",
                    "acceptance_expectations": (
                        "Own submission succeeds; forged requester is rejected."
                    ),
                    **values,
                }
            )
        )
        return (
            revision.with_context(allowed_company_ids=self.company.ids)
            if revision.company_id == self.company
            else revision
        )

    def _context(self, kind="question", solution=None, **values):
        identity = (
            self.env["project.agile.solution.context"]
            .with_user(self.manager)
            .create(
                {
                    "solution_id": (solution or self.solution).id,
                    "name": "SYNTHETIC " + kind,
                    "kind": kind,
                }
            )
        )
        defaults = {
            "question": {
                "question": "Who can delegate?",
                "owner_id": self.manager.id,
                "planning_significance": "blocking",
            },
            "decision": {
                "decision_context": "Unknown delegation authority",
                "choice": "Exclude delegation",
                "consequences": "Later approval required",
            },
            "actor": {"business_role": "Request service for themselves"},
            "deliverable": {
                "evaluation_expectations": (
                    "Own submission succeeds, delegated submission rejected"
                )
            },
        }.get(kind, {})
        return (
            self.env["project.agile.solution.context.revision"]
            .with_user(self.manager)
            .create(
                {
                    "context_id": identity.id,
                    "title": "SYNTHETIC " + kind,
                    "body": "<p>Project-specific intent.</p>",
                    **defaults,
                    **values,
                }
            )
        )

    def _spike(self, project=None, item_type="spike"):
        return (
            self.env["project.task"]
            .with_user(self.manager)
            .create(
                {
                    "name": "SYNTHETIC discovery",
                    "project_id": (project or self.project).id,
                    "agile_item_type_id": self.env.ref(
                        "project_agile.project_agile_item_type_" + item_type
                    ).id,
                }
            )
        )

    def _hide(self, model, record):
        return self.env["ir.rule"].create(
            {
                "name": "SYNTHETIC hide exact content",
                "model_id": self.env["ir.model"]._get_id(model),
                "domain_force": repr([("id", "!=", record.id)]),
            }
        )

    def test_stable_project_keys_survive_archive_and_cannot_be_forged(self):
        first = self._requirement()
        identity = first.requirement_id
        key = identity.key
        identity.write({"name": "Renamed", "active": False})
        second = self._requirement()
        self.assertNotEqual(second.requirement_id.key, key)
        self.assertEqual(identity.key, key)
        for values in (
            {"key": key},
            {"solution_id": self.foreign_solution.id},
            {"project_id": self.foreign.id},
            {"revision_ids": [Command.clear()]},
        ):
            with self.assertRaises(ValidationError):
                identity.write(values)
        with self.assertRaises(AccessError):
            identity.unlink()
        with self.assertRaises(ValidationError):
            identity.create(
                {"name": "Forged", "solution_id": self.solution.id, "key": key}
            )
        with self.assertRaises(ValidationError):
            first.copy()

    def test_working_content_validation_and_one_numbered_successor(self):
        for field in (
            "description",
            "rationale",
            "verification_method",
            "acceptance_expectations",
        ):
            with self.assertRaises(ValidationError):
                self._requirement(**{field: "   "})
        first = self._requirement(requirement_type="nfr")
        with self.assertRaises(ValidationError):
            first.create(
                {
                    "requirement_id": first.requirement_id.id,
                    **first._copy_content_values(),
                }
            )
        self.assertEqual(first.requirement_id.action_new_revision()["res_id"], first.id)
        revision = self._revision(requirement_revision_ids=[Command.set(first.ids)])
        self._approve(revision)
        second = first.browse(first.requirement_id.action_new_revision()["res_id"])
        self.assertEqual((second.number, second.predecessor_id), (2, first))
        second.write({"acceptance_expectations": "New explicit evaluation"})
        self.assertNotEqual(
            first.acceptance_expectations, second.acceptance_expectations
        )
        self.assertFalse(second.sealed)

    def test_review_seals_exact_content_and_return_never_unseals_it(self):
        requirement = self._requirement()
        question = self._context(
            affected_requirement_revision_ids=[Command.set(requirement.ids)]
        )
        revision = self._revision(context_revision_ids=[Command.set(question.ids)])
        revision.action_submit()
        self.assertTrue(question.sealed)
        self.assertTrue(requirement.sealed)
        for record in (requirement, requirement.sudo(), question, question.sudo()):
            with self.assertRaises(ValidationError):
                record.write({"title": "Silent mutation"})
            with self.assertRaises(ValidationError):
                record.unlink()
        revision.action_return_to_draft("Reconsider question")
        self.assertTrue(question.sealed)
        with self.assertRaises(ValidationError):
            question.action_resolve("Changed answer", "Unapproved expansion")
        revision.write({"context_revision_ids": [Command.clear()]})
        self.assertTrue(question.sealed)

    def test_resolution_is_explicit_owned_audited_and_changes_need_successor(self):
        question = self._context(external_owner="SYNTHETIC external interface owner")
        for values in (
            {"resolved_by_id": self.user.id},
            {"resolution_status": "resolved"},
            {"resolution": "Injected"},
        ):
            with self.assertRaises(ValidationError):
                question.write(values)
        with self.assertRaises(AccessError):
            question.with_user(self.user).action_resolve("Yes", "Unknown")
        with self.assertRaises(ValidationError):
            question.action_resolve("", "Unknown")
        action = question.action_request_resolution()
        wizard = (
            self.env[action["res_model"]]
            .with_user(self.manager)
            .with_context(**action["context"])
            .create(
                {
                    "resolution": "No delegation in this slice",
                    "rationale": "Authority not established",
                }
            )
        )
        wizard.action_confirm()
        self.assertEqual(question.resolved_by_id, self.manager)
        self.assertTrue(question.resolved_at)
        self.assertEqual(question.resolution_status, "resolved")
        with self.assertRaises(ValidationError):
            question.action_resolve("Changed answer", "Rewrite")
        revision = self._revision(context_revision_ids=[Command.set(question.ids)])
        self._approve(revision)
        snapshot = json.loads(revision.snapshot_json)["contexts"][0]
        self.assertEqual(snapshot["resolution"], question.resolution)
        successor = question.browse(question.context_id.action_new_revision()["res_id"])
        self.assertEqual(successor.resolution_status, "open")
        self.assertFalse(successor.resolved_at)
        self.assertFalse(successor.resolution)
        self.assertEqual(json.loads(revision.snapshot_json)["contexts"][0], snapshot)

    def test_context_kind_and_owner_are_server_validated_no_accounts_created(self):
        users = self.env["res.users"].search_count([])
        groups = self.env["res.groups"].search_count([])
        for kind in ("section", "actor", "domain", "deliverable", "decision"):
            row = self._context(kind)
            with self.assertRaises(ValidationError):
                row.write({"question": "Wrong kind"})
        with self.assertRaises(ValidationError):
            self._context("actor", choice="Privilege grant")
        for owner in (self.portal,):
            with self.assertRaises(ValidationError):
                self._context(owner_id=owner.id)
        with self.assertRaises(ValidationError):
            self._context(owner_id=True)
        self.assertEqual(self.env["res.users"].search_count([]), users)
        self.assertEqual(self.env["res.groups"].search_count([]), groups)

    def test_spikes_are_existing_same_project_accessible_native_work(self):
        spike = self._spike()
        question = self._context(spike_task_ids=[Command.set(spike.ids)])
        self.assertEqual(question.spike_task_ids, spike)
        for task in (self._spike(item_type="task"), self._spike(project=self.hidden)):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                question.write({"spike_task_ids": [Command.set(task.ids)]})
        with self.assertRaises(ValidationError):
            question.write(
                {"spike_task_ids": [Command.create({"name": "Automatic discovery"})]}
            )
        with self.assertRaises(ValidationError):
            spike.unlink()
        revision = self._revision(context_revision_ids=[Command.set(question.ids)])
        self._approve(revision)
        snapshot = revision.snapshot_json
        spike.write({"name": "Renamed discovery", "active": False})
        self.assertEqual(revision.action_read_snapshot()["snapshot_json"], snapshot)

    def test_inverse_membership_commands_and_seal_audit_cannot_rewrite_history(self):
        requirement = self._requirement()
        question = self._context(
            affected_requirement_revision_ids=[Command.set(requirement.ids)]
        )
        revision = self._revision(
            requirement_revision_ids=[Command.set(requirement.ids)],
            context_revision_ids=[Command.set(question.ids)],
        )
        self._approve(revision)
        for record, values in (
            (requirement, {"document_revision_ids": [Command.clear()]}),
            (requirement, {"context_revision_ids": [Command.clear()]}),
            (question, {"document_revision_ids": [Command.clear()]}),
            (question.context_id, {"revision_ids": [Command.clear()]}),
        ):
            with self.assertRaises(ValidationError):
                record.write(values)
        for values in ({"sealed": False}, {"number": 99}, {"predecessor_id": False}):
            with self.assertRaises(ValidationError):
                requirement.sudo().write(values)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._revision(
                document=self.document.create(
                    {"name": "Other", "solution_id": self.solution.id}
                ),
                requirement_revision_ids=[
                    Command.update(requirement.id, {"title": "Injected"})
                ],
            )

    def test_cross_project_company_and_solution_memberships_fail_atomically(self):
        other = (
            self.env["project.agile.solution"]
            .with_user(self.manager)
            .create({"name": "Other solution", "project_id": self.project.id})
        )
        foreign = self._requirement(solution=other)
        requirement = self._requirement()
        revision = self._revision()
        for name, rows in (("requirement_revision_ids", requirement | foreign),):
            with self.assertRaises(ValidationError):
                revision.write({name: [Command.set(rows.ids)]})
        self.assertFalse(revision.requirement_revision_ids)
        with self.assertRaises(ValidationError):
            self._context(affected_requirement_revision_ids=[Command.set(foreign.ids)])
        foreign_company = (
            self.env["project.agile.requirement"]
            .with_user(self.manager)
            .with_context(allowed_company_ids=(self.company | self.other_company).ids)
            .create({"name": "Foreign", "solution_id": self.foreign_solution.id})
        )
        for context in (
            {},
            {"solution_trusted": True},
            {"allowed_company_ids": self.other_company.ids},
        ):
            with self.assertRaises(AccessError):
                foreign_company.with_user(self.user).with_context(**context).read(
                    ["key"]
                )
        with self.assertRaises(ValidationError):
            revision.write({"requirement_revision_ids": [Command.set([True])]})

    def test_hidden_requirement_context_project_and_spike_read_export_fail_closed(self):
        requirement = self._requirement()
        spike = self._spike()
        question = self._context(
            affected_requirement_revision_ids=[Command.set(requirement.ids)],
            spike_task_ids=[Command.set(spike.ids)],
        )
        revision = self._revision(context_revision_ids=[Command.set(question.ids)])
        self._approve(revision)
        before = revision.with_user(self.user).action_read_snapshot()
        for model, record in (
            (requirement._name, requirement),
            (question._name, question),
            ("project.task", spike),
            ("project.project", self.project),
        ):
            rule = self._hide(model, record)
            with self.assertRaises(AccessError):
                revision.with_user(self.user).action_read_snapshot()
            with self.assertRaises(AccessError):
                revision.with_user(self.user).export_data(["snapshot_json"])
            rule.unlink()
        self.assertEqual(revision.with_user(self.user).action_read_snapshot(), before)
        rule = self._hide(requirement._name, requirement)
        with self.assertRaises(AccessError):
            question.with_user(self.user).read(["affected_requirement_revision_ids"])
        with self.assertRaises(AccessError):
            question.with_user(self.user).export_data(["title"])
        rule.unlink()

    def test_draft_membership_and_snapshot_cannot_silently_omit_hidden_members(self):
        requirement = self._requirement()
        revision = self._revision(
            requirement_revision_ids=[Command.set(requirement.ids)]
        )
        rule = self._hide(requirement._name, requirement)
        with self.assertRaises(AccessError):
            revision.action_submit()
        self.assertEqual(revision.state, "draft")
        rule.unlink()
        self.assertFalse(requirement.sealed)
        revision.action_submit()
        self.assertTrue(requirement.sealed)

    def test_nonadmin_users_read_but_cannot_author_or_resolve(self):
        requirement = self._requirement()
        question = self._context()
        for record in (
            requirement.requirement_id,
            requirement,
            question.context_id,
            question,
        ):
            record.with_user(self.user).read(["display_name"])
            for user in (self.user, self.portal):
                with self.assertRaises(AccessError):
                    record.with_user(user).write(
                        {
                            "title"
                            if "title" in record._fields
                            else "name": "Unauthorized"
                        }
                    )
                with self.assertRaises(AccessError):
                    record.with_user(user).create({})
        rule = self._hide("project.project", self.project)
        for record in (requirement, question):
            self.assertEqual(
                record.with_user(self.user).search_count([("id", "=", record.id)]), 0
            )
            self.assertEqual(
                record.with_user(self.user)._read_group(
                    [("id", "=", record.id)], ["project_id"], ["__count"]
                ),
                [],
            )
            with self.assertRaises(AccessError):
                record.sudo().write({"title": "Bypass"})
        rule.unlink()

    def test_defaults_cannot_forge_numbers_seals_owners_or_resolution(self):
        requirement = self._requirement()
        question = self._context()
        for record in (requirement, question):
            defaults = record.with_context(
                default_number=99, default_sealed=True, default_predecessor_id=record.id
            ).default_get(["number", "sealed", "predecessor_id"])
            self.assertFalse(set(defaults) & {"number", "sealed", "predecessor_id"})
        defaults = question.with_context(
            default_resolution="Injected", default_resolved_by_id=self.user.id
        ).default_get(["resolution", "resolved_by_id"])
        self.assertFalse(defaults)

    def test_exact_old_baseline_and_separate_sow_spec_lineage(self):
        requirement = self._requirement()
        question = self._context(
            affected_requirement_revision_ids=[Command.set(requirement.ids)]
        )
        sow = self.document.create(
            {"name": "SYNTHETIC SOW", "solution_id": self.solution.id, "kind": "sow"}
        )
        sow_revision = self._revision(
            document=sow,
            requirement_revision_ids=[Command.set(requirement.ids)],
            context_revision_ids=[Command.set(question.ids)],
        )
        self._approve(sow_revision)
        spec = self._revision(
            based_sow_revision_id=sow_revision.id,
            requirement_revision_ids=[Command.set(requirement.ids)],
            context_revision_ids=[Command.set(question.ids)],
        )
        self.assertEqual(spec.state, "draft")
        self._approve(spec)
        before = spec.snapshot_json
        next_requirement = requirement.browse(
            requirement.requirement_id.action_new_revision()["res_id"]
        )
        next_requirement.write({"description": "Changed working intent"})
        successor = spec.browse(spec.action_new_revision()["res_id"])
        successor.write(
            {"requirement_revision_ids": [Command.set(next_requirement.ids)]}
        )
        self.assertEqual(sow_revision.state, "approved")
        self.assertEqual(spec.snapshot_json, before)
        self.assertEqual(successor.state, "draft")
        requirement.requirement_id.write({"active": False, "name": "Archived identity"})
        question.context_id.write({"active": False})
        self.assertEqual(
            spec.with_user(self.user).action_read_snapshot()["snapshot_json"], before
        )

    def test_only_one_exact_revision_of_identity_per_document(self):
        first = self._requirement()
        revision = self._revision(requirement_revision_ids=[Command.set(first.ids)])
        self._approve(revision)
        second = first.browse(first.requirement_id.action_new_revision()["res_id"])
        successor = revision.browse(revision.action_new_revision()["res_id"])
        with self.assertRaises(ValidationError):
            successor.write(
                {"requirement_revision_ids": [Command.set((first | second).ids)]}
            )
        self.assertEqual(successor.requirement_revision_ids, first)

    def test_batch_creation_failure_has_no_partial_content_without_outer_savepoint(
        self,
    ):
        identity = self.env["project.agile.requirement"].with_user(self.manager)
        before = identity.search_count([])
        with self.assertRaises(ValidationError):
            identity.create(
                [
                    {"name": "Valid", "solution_id": self.solution.id},
                    {"name": "Invalid", "solution_id": True},
                ]
            )
        self.assertEqual(identity.search_count([]), before)
        requirement = self._requirement()
        revisions = requirement.with_user(self.manager)
        before = revisions.search_count([])
        with self.assertRaises(ValidationError):
            revisions.create(
                [
                    {
                        "requirement_id": identity.create(
                            {"name": "New", "solution_id": self.solution.id}
                        ).id,
                        **requirement._copy_content_values(),
                    },
                    {"requirement_id": True, "title": "Invalid"},
                ]
            )
        self.assertEqual(revisions.search_count([]), before)

    def test_project_company_cannot_move_even_without_document_membership(self):
        self._requirement()
        with self.assertRaises(ValidationError):
            self.project.write({"company_id": self.other_company.id})

    def test_sow_skeleton_all_sections_explicit_copy_and_template_reuse(self):
        template = self.env.ref(
            "project_agile_solution.template_sow_skeleton"
        ).with_user(self.manager)
        sections = template._validated_sections()
        self.assertEqual(len(sections), 10)
        self.assertEqual(
            [row["sequence"] for row in sections], list(range(10, 101, 10))
        )
        documents = self.document.create(
            [
                {
                    "name": "SYNTHETIC SOW A",
                    "kind": "sow",
                    "solution_id": self.solution.id,
                },
                {
                    "name": "SYNTHETIC SOW B",
                    "kind": "sow",
                    "solution_id": self.solution.id,
                },
            ]
        )
        revisions = [self._revision(document=doc) for doc in documents]
        for revision in revisions:
            revision.action_apply_template(template.id)
        provenance = revisions[0].template_snapshot
        revisions[0].section_ids[-1].write(
            {"body": "Project-specific narrative, no legal default"}
        )
        self.assertNotEqual(
            revisions[0].section_ids[-1].body, revisions[1].section_ids[-1].body
        )
        template.write({"name": "Edited project starting point"})
        self.assertEqual(revisions[0].template_snapshot, provenance)
        self._approve(revisions[0])
        self.assertIn("Project-specific narrative", revisions[0].snapshot_json)

    def test_three_synthetic_scenarios_create_real_intent_context_and_narrative(self):
        from .solution_fixture import seed_scenario

        source = json.loads(
            (Path(__file__).parent / "fixtures/synthetic_scenarios.json").read_text()
        )
        for scenario in source["scenarios"]:
            fixture = seed_scenario(self.env, self.manager, self.company, scenario)
            spec = fixture["spec"]
            self.assertEqual(
                {row.requirement_type for row in spec.requirement_revision_ids},
                {"fr", "nfr"},
            )
            self.assertEqual(
                set(spec.context_revision_ids.mapped("kind")),
                {"actor", "domain", "deliverable", "question", "decision", "section"},
            )
            self.assertTrue(all(spec.requirement_revision_ids.mapped("sealed")))
            self.assertEqual(spec.state, "approved")
            self.assertTrue(spec.snapshot_sha256)
            if fixture["sow"]:
                self.assertEqual(len(fixture["sow"].section_ids), 10)
                self.assertEqual(fixture["sow"].state, "approved")
            else:
                self.assertFalse(spec.based_sow_revision_id)
            question = fixture["question"]
            self.assertEqual(question.owner_id, self.manager)
            if scenario["id"] == "integration":
                self.assertEqual(question.resolution_status, "open")
                self.assertEqual(
                    question.spike_task_ids.agile_item_type_id.code, "spike"
                )
            if scenario["id"] == "portal":
                self.assertEqual(question.resolution_status, "resolved")
            self.assertIn("SYNTHETIC", spec.snapshot_json)

    def test_native_forms_edit_working_intent_and_explicit_question_resolution(self):
        requirement = self._requirement()
        with Form(requirement) as form:
            form.acceptance_expectations = "Form-authored observable expectations"
        self.assertEqual(
            requirement.acceptance_expectations, "Form-authored observable expectations"
        )
        question = self._context()
        with Form(question) as form:
            form.planning_significance = "planning"
            form.external_owner = "SYNTHETIC interface owner narrative"
        action = question.action_request_resolution()
        with Form(
            self.env[action["res_model"]]
            .with_user(self.manager)
            .with_context(**action["context"])
        ) as form:
            form.resolution = "Keep discovery bounded"
            form.rationale = "Unknown interface is not delivery authorization"
        form.save().action_confirm()
        self.assertEqual(question.resolution_status, "resolved")

    def test_template_install_root_exception_is_not_ordinary_sudo_authority(self):
        template = self.env.ref("project_agile_solution.template_sow_skeleton")
        for user in (self.user, self.portal):
            for record in (template.with_user(user), template.with_user(user).sudo()):
                with self.assertRaises(AccessError):
                    record.write({"name": "Unauthorized shared template change"})
        self.assertEqual(template.company_id, self.env["res.company"])

    def test_multi_company_enabled_manager_cannot_cross_link_exact_content(self):
        requirement = self._requirement()
        caller = requirement.with_context(
            allowed_company_ids=(self.company | self.other_company).ids
        )
        foreign = self._requirement(solution=self.foreign_solution)
        # The helper's manager enables both companies, but record creation with
        # the primary active context must still not permit foreign document links.
        revision = self._revision()
        with self.assertRaises(UserError):
            revision.with_env(caller.env).write(
                {"requirement_revision_ids": [Command.set(foreign.ids)]}
            )
        self.assertFalse(revision.requirement_revision_ids)

    def test_literal_rpc_reference_commands_match_native_and_reject_boolean_ids(self):
        requirement = self._requirement()
        revision = self._revision(requirement_revision_ids=[[6, 0, requirement.ids]])
        self.assertEqual(revision.requirement_revision_ids, requirement)
        for command in (
            [True, requirement.id, 0],
            [4, True, 0],
            [6, 0, [True]],
            ["6", 0, requirement.ids],
        ):
            with self.assertRaises(ValidationError):
                revision.write({"requirement_revision_ids": [command]})

    def test_spike_inverse_storage_and_forged_defaults_cannot_mutate_context(self):
        spike = self._spike()
        question = self._context(spike_task_ids=[Command.set(spike.ids)])
        revision = self._revision(context_revision_ids=[Command.set(question.ids)])
        self._approve(revision)
        for caller in (spike.with_user(self.user), spike.with_user(self.manager)):
            with self.assertRaises(AccessError):
                caller.read(["solution_question_revision_ids"])
            with self.debug_mode(), self.assertRaises(AccessError):
                caller.read(["solution_question_revision_ids"])
            with self.assertRaises(ValidationError):
                caller.sudo().write(
                    {"solution_question_revision_ids": [Command.clear()]}
                )
        with self.assertRaises(ValidationError):
            spike.sudo().create(
                {
                    "name": "Injected inverse",
                    "project_id": self.project.id,
                    "solution_question_revision_ids": [Command.set(question.ids)],
                }
            )
        protected = {"solution_question_revision_ids": [Command.set(question.ids)]}
        defaults = spike.with_context(
            **{"default_" + name: value for name, value in protected.items()}
        ).default_get(list(protected))
        self.assertFalse(defaults)
        rule = self._hide("project.task", spike)
        with self.assertRaises(AccessError):
            question.with_user(self.user).read(["spike_task_ids"])
        rule.unlink()

    def test_mixed_visible_hidden_members_are_never_a_complete_baseline(self):
        requirements = self._requirement() | self._requirement()
        revision = self._revision(
            requirement_revision_ids=[Command.set(requirements.ids)]
        )
        revision.requirement_revision_ids.read(["title"])
        rule = self._hide(requirements._name, requirements[-1])
        with self.assertRaises(AccessError):
            revision.action_submit()
        self.assertEqual(revision.state, "draft")
        rule.unlink()
        self.assertFalse(any(requirements.mapped("sealed")))
