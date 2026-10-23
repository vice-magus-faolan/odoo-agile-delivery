"""Native regression coverage of historical evidence and caller visibility."""

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestGitEnvironmentEvidence(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Merge evidence",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "MGE",
            }
        )
        self.repository = self._repository("one")
        self.uat = self.env["project.agile.environment"].create(
            {
                "name": "UAT",
                "project_id": self.project.id,
            }
        )
        self.production = self.env["project.agile.environment"].create(
            {
                "name": "Live",
                "project_id": self.project.id,
                "is_production": True,
            }
        )
        self.uat_mapping = self._mapping(self.uat, "release/UAT")
        self.prod_mapping = self._mapping(self.production, "main")
        self.task = self.env["project.task"].create(
            {
                "name": "Configuration",
                "project_id": self.project.id,
                "agile_item_type_id": self.env.ref(
                    "project_agile.project_agile_item_type_configuration"
                ).id,
            }
        )
        self.reader = mail_new_test_user(
            self.env,
            "merge-reader",
            groups="project.group_project_user",
        )
        self.manager = mail_new_test_user(
            self.env,
            "merge-manager",
            groups="project.group_project_manager",
        )

    def _repository(self, name, project=None):
        return self.env["project.git.repository"].create(
            {
                "name": name,
                "provider": "github",
                "provider_repository_id": name,
                "canonical_url": "https://github.com/example/" + name,
                "project_id": (project or self.project).id,
            }
        )

    def _mapping(self, environment, branch, repository=None):
        return self.env["project.git.environment.branch"].create(
            {
                "environment_id": environment.id,
                "repository_id": (repository or self.repository).id,
                "branch_name": branch,
            }
        )

    def _pr(self, identity, branch="release/UAT", repository=None, link=True, **values):
        repository = repository or self.repository
        pr = self.env["project.git.pull.request"].create(
            {
                "repository_id": repository.id,
                "provider_request_id": identity,
                "number": identity,
                "state": "merged",
                "target_branch": branch,
                "merged_at": "2026-10-20 12:00:00",
                "ordering_state": "known",
                "updated_at": "2026-10-20 12:01:00",
                **values,
            }
        )
        if link:
            self.env["project.git.task.association"].create(
                {
                    "repository_id": repository.id,
                    "task_id": self.task.id,
                    "source_type": "pull_request",
                    "source_provider_id": identity,
                }
            )
        return pr

    def _assert_projection(self, environments, count, gap, user=None):
        task = self.task.with_user(user or self.reader)
        values = task.read(
            [
                "git_merge_environment_ids",
                "git_environment_merge_count",
                "git_environment_evidence",
            ]
        )[0]
        self.assertEqual(
            set(values["git_merge_environment_ids"]), set(environments.ids)
        )
        self.assertEqual(values["git_environment_merge_count"], count)
        found = task.search(
            [
                ("id", "=", task.id),
                ("git_uat_without_production_id", "in", [self.uat.id]),
            ]
        )
        self.assertEqual(bool(found), gap)
        merged = task.search(
            [
                ("id", "=", task.id),
                ("git_merge_environment_ids", "in", [self.uat.id]),
            ]
        )
        self.assertEqual(bool(merged), self.uat in environments)
        action = task.action_open_git_environment_merges()
        prs = (
            self.env["project.git.pull.request"]
            .with_user(task.env.user)
            .search(action["domain"])
        )
        self.assertEqual(len(prs), count)
        return values

    def test_unknown_partial_multiple_prs_and_qualified_production_negative(self):
        empty = self._assert_projection(self.uat.browse(), 0, False)
        self.assertIn("Unknown", empty["git_environment_evidence"])
        self._pr("11")
        self._pr("12", state="open", merged_at=False)
        self._pr("13", ordering_state="ambiguous")
        self._assert_projection(self.uat, 1, True)
        self._pr("14", branch="main", ordering_state="stale")
        self._assert_projection(self.uat, 1, True)
        self._pr("15", branch="main")
        self._assert_projection(self.uat | self.production, 2, False)

    def test_branch_exactness_mapping_reinterpretation_and_production_required(self):
        self._pr("21", branch="release/uat")
        self._assert_projection(self.uat.browse(), 0, False)
        self.uat_mapping.branch_name = "release/uat"
        self._assert_projection(self.uat, 1, True)
        self.prod_mapping.active = False
        self._assert_projection(self.uat, 1, False)
        self.prod_mapping.active = True
        pre_uat = self.env["project.agile.environment"].create(
            {
                "name": "Pre-UAT",
                "project_id": self.project.id,
            }
        )
        self._mapping(pre_uat, "release/uat")
        self.assertEqual(
            self.task.search(
                [
                    ("git_uat_without_production_id", "=ilike", "UAT"),
                ]
            ),
            self.task,
        )
        self.uat_mapping.active = False
        self.assertFalse(
            self.task.search(
                [
                    ("git_uat_without_production_id", "=ilike", "UAT"),
                ]
            )
        )
        self.assertEqual(
            self.task.search(
                [
                    ("git_uat_without_production_id", "in", [pre_uat.id]),
                ]
            ),
            self.task,
        )
        self.production.name = "Production renamed"
        self.assertTrue(
            self.task.search(
                [
                    ("git_uat_without_production_id", "in", [pre_uat.id]),
                ]
            )
        )

    def test_exact_repository_pr_pairs_and_partial_across_repositories(self):
        other = self._repository("two")
        self._mapping(self.uat, "release/UAT", other)
        self._pr("31", state="open", merged_at=False)
        self._pr("31", repository=other, link=False)
        self._pr("32", repository=other, state="open", merged_at=False)
        self._pr("32", link=False)
        self._assert_projection(self.uat.browse(), 0, False)
        pr = self._pr("33", repository=other)
        self._assert_projection(self.uat, 1, True)
        pr.ordering_state = "stale"
        self._assert_projection(self.uat.browse(), 0, False)

    def test_repository_reparent_keeps_project_evidence_consistent_in_batches(self):
        repository = self._repository("reparented")
        self._pr("101", repository=repository)
        association = self.task.git_association_ids
        association_fields = [
            "repository_id",
            "task_id",
            "source_type",
            "source_provider_id",
        ]
        history = association.read(association_fields)
        other_project = self.env["project.project"].create(
            {
                "name": "Reparent destination",
                "company_id": self.project.company_id.id,
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "RPD",
            }
        )
        # An unmapped repository may move; its old association remains historical.
        repository.with_user(self.manager).write({"project_id": other_project.id})
        environment = (
            self.env["project.agile.environment"]
            .with_user(self.manager)
            .create({"name": "Destination UAT", "project_id": other_project.id})
        )
        self.env["project.git.environment.branch"].with_user(self.manager).create(
            {
                "environment_id": environment.id,
                "repository_id": repository.id,
                "branch_name": "release/UAT",
            }
        )
        other_task = self.env["project.task"].create(
            {"name": "Destination work", "project_id": other_project.id}
        )
        pr = self._pr("102", repository=repository, link=False)
        self.env["project.git.task.association"].create(
            {
                "repository_id": repository.id,
                "task_id": other_task.id,
                "source_type": "pull_request",
                "source_provider_id": "102",
            }
        )
        old_task = self.task.with_user(self.reader)
        new_task = other_task.with_user(self.reader)
        fields = [
            "git_merge_environment_ids",
            "git_environment_merge_count",
            "git_environment_evidence",
        ]
        singletons = {
            row["id"]: row for row in old_task.read(fields) + new_task.read(fields)
        }
        # Mix Projects in both orders after singleton cache warmup, then re-read A.
        for records in (
            old_task,
            old_task | new_task,
            new_task,
            new_task | old_task,
            old_task,
        ):
            with self.subTest(task_ids=records.ids):
                for row in records.read(fields):
                    expected = row["id"] == new_task.id
                    self.assertEqual(row, singletons[row["id"]])
                    self.assertEqual(
                        row["git_merge_environment_ids"],
                        environment.ids if expected else [],
                    )
                    self.assertEqual(row["git_environment_merge_count"], int(expected))
                    if expected:
                        self.assertIn(
                            "Destination UAT", row["git_environment_evidence"]
                        )
                        self.assertIn("PR 102", row["git_environment_evidence"])
                    else:
                        self.assertIn("Unknown", row["git_environment_evidence"])
                        self.assertNotIn(
                            "Destination UAT", row["git_environment_evidence"]
                        )
                        self.assertNotIn("PR 101", row["git_environment_evidence"])
        for task, expected_prs in ((old_task, pr.browse()), (new_task, pr)):
            action = task.action_open_git_environment_merges()
            self.assertEqual(
                self.env["project.git.pull.request"]
                .with_user(self.reader)
                .search(action["domain"]),
                expected_prs,
            )
        domain = [
            ("id", "in", (old_task | new_task).ids),
            ("git_merge_environment_ids", "in", environment.ids),
        ]
        self.assertEqual(old_task.search(domain), new_task)
        self.assertFalse(old_task.search(domain + [("id", "=", old_task.id)]))
        self.assertEqual(association.read(association_fields), history)

    def test_mapping_authority_integrity_unique_and_copy(self):
        with self.assertRaises(AccessError):
            self.uat_mapping.with_user(self.reader).write({"branch_name": "other"})
        self.uat_mapping.with_user(self.manager).write({"branch_name": "release/UAT"})
        with self.env.cr.savepoint(), self.assertRaises(IntegrityError):
            self._mapping(self.uat, "other")
        other_project = self.project.copy({"name": "Other", "agile_key": "OTH"})
        self.assertFalse(other_project.git_environment_branch_ids)
        # Native Project copies disable Agile; configure the new client first.
        other_project.agile_enabled = True
        other_repository = self._repository("elsewhere", other_project)
        with self.assertRaises(ValidationError):
            self.uat_mapping.write({"repository_id": other_repository.id})
        with self.assertRaises(ValidationError):
            self.repository.write({"project_id": other_project.id})
        for branch in (
            "refs/heads/main",
            " leading",
            "a..b",
            "a//b",
            "a.lock",
            "bad?name",
            "-option",
        ):
            with self.subTest(branch=branch), self.assertRaises(ValidationError):
                self.uat_mapping.write({"branch_name": branch})
        self.env["ir.rule"].create(
            {
                "name": "deny project writes",
                "model_id": self.env["ir.model"]._get_id("project.project"),
                "domain_force": repr([("id", "!=", self.project.id)]),
                "perm_read": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        with self.assertRaises(AccessError):
            self.uat_mapping.with_user(self.manager).write({"branch_name": "other"})
        with self.assertRaises(AccessError):
            self.uat_mapping.with_user(self.manager).unlink()

    def test_archive_template_and_task_copy_hide_but_do_not_erase_evidence(self):
        self._pr("41")
        self._assert_projection(self.uat, 1, True)
        copied = self.task.copy()
        self.assertFalse(copied.git_association_ids)
        self.assertFalse(
            copied.read(["git_merge_environment_ids"])[0]["git_merge_environment_ids"]
        )
        for record in (self.uat, self.repository, self.task, self.project):
            record.active = False
            self._assert_projection(self.uat.browse(), 0, False)
            record.active = True
            self._assert_projection(self.uat, 1, True)
        self.task.is_template = True
        self._assert_projection(self.uat.browse(), 0, False)
        self.task.is_template = False
        self._assert_projection(self.uat, 1, True)

    def test_current_custom_rules_on_every_join_and_public_read_refresh(self):
        pr = self._pr("51")
        self._assert_projection(self.uat, 1, True)
        association = self.task.git_association_ids
        for record in (
            self.uat_mapping,
            self.uat,
            self.repository,
            association,
            pr,
            self.project,
        ):
            rule = self.env["ir.rule"].create(
                {
                    "name": "hide evidence input",
                    "model_id": self.env["ir.model"]._get_id(record._name),
                    "domain_force": repr([("id", "not in", record.ids)]),
                }
            )
            self._assert_projection(self.uat.browse(), 0, False)
            rule.unlink()
            self._assert_projection(self.uat, 1, True)
        self._pr("52", branch="main")
        self._assert_projection(self.uat | self.production, 2, False)
        rule = self.env["ir.rule"].create(
            {
                "name": "hide production mapping",
                "model_id": self.env["ir.model"]._get_id(self.prod_mapping._name),
                "domain_force": repr([("id", "!=", self.prod_mapping.id)]),
            }
        )
        self._assert_projection(self.uat, 1, False)
        rule.unlink()
        self.production.is_production = False
        self._assert_projection(self.uat | self.production, 2, False)

    def test_manual_status_actor_history_and_lifecycle_are_untouched(self):
        lines = self.task.agile_environment_status_ids
        lines[0].status = "verified"
        task_fields = [
            "stage_id",
            "state",
            "agile_item_type_id",
            "message_ids",
            "write_date",
        ]
        line_fields = ["status", "actor_id", "changed_at", "message_ids", "write_date"]
        before_task = self.task.read(task_fields)
        before_lines = lines.read(line_fields)
        self._pr("61")
        self._assert_projection(self.uat, 1, True)
        action = self.uat.action_git_uat_without_production()
        self.assertIn(self.task, self.task.search(action["domain"]))
        self.assertEqual(self.task.read(task_fields), before_task)
        self.assertEqual(lines.read(line_fields), before_lines)

    def test_company_and_current_task_access_do_not_leak(self):
        self._pr("71")
        self._assert_projection(self.uat, 1, True)
        company = self.env["res.company"].create({"name": "Other merge company"})
        other = (
            self.env["project.project"]
            .with_company(company)
            .create(
                {
                    "name": "Other company",
                    "company_id": company.id,
                    "agile_enabled": True,
                    "agile_key": "CMP",
                    "privacy_visibility": "employees",
                }
            )
        )
        repository = self._repository("company", other)
        with self.assertRaises(ValidationError):
            self.uat_mapping.write({"repository_id": repository.id})
        self.assertFalse(repository.with_user(self.reader).has_access("read"))
        rule = self.env["ir.rule"].create(
            {
                "name": "hide task",
                "model_id": self.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("id", "!=", self.task.id)]),
            }
        )
        with self.assertRaises(AccessError):
            self.task.with_user(self.reader).read(["git_environment_evidence"])
        self.assertNotIn(
            self.task,
            self.task.with_user(self.reader).search(
                [
                    ("git_uat_without_production_id", "in", [self.uat.id]),
                ]
            ),
        )
        rule.unlink()

    def test_evidence_text_escapes_names_and_never_claims_current_placement(self):
        self.uat.name = "<script>alert(1)</script>"
        self._pr("81")
        values = self._assert_projection(self.uat, 1, True)
        text = values["git_environment_evidence"]
        self.assertNotIn("<script>", text)
        self.assertIn("partial", text)
        self.assertIn("not deployment", text)

    def test_configuration_create_delete_and_derived_input_authority(self):
        model = self.env["project.git.environment.branch"]
        values = {
            "environment_id": self.uat.id,
            "repository_id": self.repository.id,
            "branch_name": "uat",
        }
        self.uat_mapping.unlink()
        with self.assertRaises(AccessError):
            model.with_user(self.reader).create(values)
        mapping = model.with_user(self.manager).create(values)
        for derived in ("project_id", "company_id", "native_access"):
            with self.subTest(derived=derived):
                with self.assertRaises(AccessError):
                    mapping.write({derived: False})
                with self.assertRaises(AccessError):
                    model.with_context(**{f"default_{derived}": False}).create(values)
        with self.assertRaises(AccessError):
            mapping.with_user(self.reader).unlink()
        self.env["ir.rule"].create(
            {
                "name": "configuration requires Project write",
                "model_id": self.env["ir.model"]._get_id("project.project"),
                "domain_force": repr([("id", "!=", self.project.id)]),
                "perm_read": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        with self.assertRaises(AccessError):
            model.with_user(self.manager).create(values)
        for field in (
            "git_merge_environment_ids",
            "git_environment_merge_count",
            "git_environment_evidence",
            "git_uat_without_production_id",
        ):
            with self.subTest(field=field):
                with self.assertRaises(AccessError):
                    self.task.with_user(self.reader).write({field: False})
                with self.assertRaises(AccessError):
                    self.env["project.task"].with_context(
                        **{f"default_{field}": False}
                    ).create({"name": "Forged", "project_id": self.project.id})

    def test_bulk_projection_and_archive_context_preserve_current_membership(self):
        self._pr("91")
        tasks = self.env["project.task"].create(
            [
                {"name": f"Bulk {index}", "project_id": self.project.id}
                for index in range(20)
            ]
        )
        self.env["project.git.task.association"].create(
            [
                {
                    "repository_id": self.repository.id,
                    "task_id": task.id,
                    "source_type": "pull_request",
                    "source_provider_id": "91",
                }
                for task in tasks
            ]
        )
        tasks = tasks.with_user(self.reader).with_context(
            active_test=False, allowed_company_ids=self.reader.company_ids.ids
        )
        fields = ["git_merge_environment_ids", "git_environment_merge_count"]
        rows = tasks.read(fields)
        self.assertEqual(len(rows), 20)
        self.assertTrue(
            all(row["git_merge_environment_ids"] == self.uat.ids for row in rows)
        )
        self.assertTrue(all(row["git_environment_merge_count"] == 1 for row in rows))
        self.assertEqual(
            tasks.search(
                [
                    ("id", "in", tasks.ids),
                    ("git_uat_without_production_id", "in", self.uat.ids),
                ]
            ),
            tasks,
        )
        self.uat.active = False
        self.assertTrue(
            all(not row["git_merge_environment_ids"] for row in tasks.read(fields))
        )
        self.assertFalse(
            tasks.search(
                [
                    ("id", "in", tasks.ids),
                    ("git_uat_without_production_id", "in", self.uat.ids),
                ]
            )
        )
