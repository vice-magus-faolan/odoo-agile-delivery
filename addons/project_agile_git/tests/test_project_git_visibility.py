"""Runtime coverage for access-controlled standard Git fact visibility."""

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestProjectGitVisibility(TransactionCase):
    """Keep counts, actions, and URLs inside the current user's visible scope."""

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Visibility",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "VIS",
            }
        )
        self.task = self.env["project.task"].create(
            {"name": "Visible task", "project_id": self.project.id}
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "visibility",
                "provider": "github",
                "provider_repository_id": "visibility-1",
                "canonical_url": "https://github.com/acme/visibility",
                "project_id": self.project.id,
            }
        )
        self.branch = self.env["project.git.branch"].create(
            {
                "repository_id": self.repository.id,
                "provider_branch_id": "refs/heads/feature/VIS-1",
                "name": "feature/VIS-1",
                "url": "https://github.com/acme/visibility/tree/feature/VIS-1",
            }
        )
        self.commit = self.env["project.git.commit"].create(
            {
                "repository_id": self.repository.id,
                "sha": "a" * 40,
                "url": "https://github.com/acme/visibility/commit/" + "a" * 40,
            }
        )
        self.pull_request = self.env["project.git.pull.request"].create(
            {
                "repository_id": self.repository.id,
                "provider_request_id": "101",
                "number": "101",
                "url": "https://github.com/acme/visibility/pull/101",
            }
        )
        self.check = self.env["project.git.check"].create(
            {
                "repository_id": self.repository.id,
                "provider_check_id": "201",
                "name": "CI",
                "url": "https://github.com/acme/visibility/runs/201",
            }
        )
        for source_type, source_provider_id in (
            ("branch", self.branch.provider_branch_id),
            ("commit", self.commit.sha),
            ("pull_request", self.pull_request.provider_request_id),
            ("check", self.check.provider_check_id),
        ):
            self.env["project.git.task.association"].create(
                {
                    "repository_id": self.repository.id,
                    "task_id": self.task.id,
                    "source_type": source_type,
                    "source_provider_id": source_provider_id,
                }
            )

    def test_project_and_task_actions_are_limited_to_visible_fact_associations(self):
        self.env.invalidate_all()

        self.assertEqual(self.project.git_repository_count, 1)
        self.assertEqual(
            (
                self.task.git_branch_count,
                self.task.git_commit_count,
                self.task.git_pull_request_count,
                self.task.git_check_count,
            ),
            (1, 1, 1, 1),
        )
        repository_action = self.project.action_open_git_repositories()
        self.assertEqual(
            self.env["project.git.repository"].search(repository_action["domain"]), self.repository
        )
        for action_name, model_name, expected in (
            ("action_open_git_branches", "project.git.branch", self.branch),
            ("action_open_git_commits", "project.git.commit", self.commit),
            ("action_open_git_pull_requests", "project.git.pull.request", self.pull_request),
            ("action_open_git_checks", "project.git.check", self.check),
        ):
            action = getattr(self.task, action_name)()
            self.assertEqual(self.env[model_name].search(action["domain"]), expected)

    def test_external_urls_must_stay_under_the_validated_repository(self):
        with self.assertRaises(ValidationError):
            self.env["project.git.repository"].create(
                {
                    "name": "unsafe repository",
                    "provider": "github",
                    "provider_repository_id": "unsafe-1",
                    "canonical_url": "http://github.com/acme/unsafe",
                    "project_id": self.project.id,
                }
            )
        with self.assertRaises(ValidationError):
            self.branch.write({"url": "https://github.com/other/repository/tree/VIS-1"})

    def test_ordinary_user_cannot_count_or_select_private_or_other_company_facts(self):
        reader = mail_new_test_user(
            self.env, "Git fact reader", groups="project.group_project_user"
        )
        with self.assertRaises(AccessError):
            self.repository.with_user(reader).action_open_git_deliveries()
        hidden_project = self.env["project.project"].create(
            {
                "name": "Hidden visibility",
                "privacy_visibility": "followers",
                "agile_enabled": True,
                "agile_key": "HID",
            }
        )
        hidden_repository = self.env["project.git.repository"].create(
            {
                "name": "hidden visibility",
                "provider": "github",
                "provider_repository_id": "hidden-1",
                "canonical_url": "https://github.com/acme/hidden",
                "project_id": hidden_project.id,
            }
        )
        hidden_branch = self.env["project.git.branch"].create(
            {
                "repository_id": hidden_repository.id,
                "provider_branch_id": "refs/heads/hidden",
                "name": "hidden",
            }
        )
        other_company = self.env["res.company"].create({"name": "Other visibility company"})
        other_project = self.env["project.project"].with_company(other_company).create(
            {
                "name": "Other company visibility",
                "company_id": other_company.id,
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTH",
            }
        )
        other_repository = self.env["project.git.repository"].with_company(other_company).create(
            {
                "name": "other visibility",
                "provider": "github",
                "provider_repository_id": "other-1",
                "canonical_url": "https://github.com/acme/other",
                "project_id": other_project.id,
            }
        )
        other_branch = self.env["project.git.branch"].with_company(other_company).create(
            {
                "repository_id": other_repository.id,
                "provider_branch_id": "refs/heads/other",
                "name": "other",
            }
        )

        self.assertEqual(self.task.with_user(reader).git_branch_count, 1)
        visible_action = self.task.with_user(reader).action_open_git_branches()
        self.assertEqual(
            self.env["project.git.branch"].with_user(reader).search(visible_action["domain"]), self.branch
        )
        branches = self.env["project.git.branch"].with_user(reader)
        self.assertFalse(branches.search([("id", "in", [hidden_branch.id, other_branch.id])]))
