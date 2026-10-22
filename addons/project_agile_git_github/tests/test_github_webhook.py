"""End-to-end authenticated GitHub delivery ingress coverage."""

import hashlib
import hmac
import json
import threading
from pathlib import Path

import requests

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestGitHubWebhook(HttpCase):
    """Exercise the public route without granting the HTTP caller any project access."""

    route = "/project_agile_git_github/webhook"
    secret = "fixture-github-secret"

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "GitHub ingress",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "GHI",
            }
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "ingress",
                "provider": "github",
                "provider_repository_id": "4242",
                "canonical_url": "https://github.com/acme/ingress",
                "project_id": self.project.id,
                "webhook_secret": self.secret,
            }
        )

    def _payload(self, repository_id="4242", **extra):
        return {"repository": {"id": repository_id, **extra}}

    def _post(self, payload, delivery_id="delivery-1", secret=None, **headers):
        raw_body = json.dumps(payload, separators=(",", ":")).encode()
        signing_secret = self.secret if secret is None else secret
        signature = (
            "sha256="
            + hmac.new(signing_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        )
        request_headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": delivery_id,
            "X-Hub-Signature-256": signature,
            **headers,
        }
        return self.url_open(self.route, data=raw_body, headers=request_headers)

    def _delivery_count(self):
        return self.env["project.git.delivery"].search_count(
            [("repository_id", "=", self.repository.id)]
        )

    def test_valid_delivery_is_persisted_once_without_workflow_mutation(self):
        task = self.env["project.task"].create(
            {"name": "Must stay untouched", "project_id": self.project.id}
        )
        before = task.read(["stage_id", "message_partner_ids"])[0]

        response = self._post(self._payload(), delivery_id="delivery-valid")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b"")
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", "delivery-valid"),
            ]
        )
        self.assertEqual((delivery.state, delivery.attempt_count), ("queued", 0))
        self.assertEqual(
            delivery.payload_sha256,
            hashlib.sha256(b'{"repository":{"id":"4242"}}').hexdigest(),
        )
        self.assertEqual(task.read(["stage_id", "message_partner_ids"])[0], before)

    def test_replay_returns_accepted_without_duplicate_ledger_work(self):
        response = self._post(self._payload(), delivery_id="delivery-replay")
        replay = self._post(self._payload(), delivery_id="delivery-replay")

        self.assertEqual((response.status_code, replay.status_code), (202, 202))
        self.assertEqual(self._delivery_count(), 1)

    def test_mismatched_replay_is_rejected_and_recorded_without_a_second_delivery(self):
        first = self._post(self._payload(), delivery_id="delivery-mismatched-replay")
        replay = self._post(
            self._payload(extra="different authenticated payload"),
            delivery_id="delivery-mismatched-replay",
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(self._delivery_count(), 1)
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", "delivery-mismatched-replay"),
            ]
        )
        self.assertEqual(delivery.replay_mismatch_count, 1)
        self.assertTrue(delivery.last_replay_mismatch_at)

    def test_event_mismatched_replay_is_rejected_without_a_second_delivery(self):
        first = self._post(self._payload(), delivery_id="delivery-event-mismatch")
        replay = self._post(
            self._payload(),
            delivery_id="delivery-event-mismatch",
            **{"X-GitHub-Event": "pull_request"},
        )

        self.assertEqual((first.status_code, replay.status_code), (202, 409))
        self.assertEqual(self._delivery_count(), 1)
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", "delivery-event-mismatch"),
            ]
        )
        self.assertEqual(delivery.replay_mismatch_count, 1)

    def test_deeply_nested_and_large_number_json_are_rejected_without_a_delivery(self):
        deeply_nested = b"[" * 2000 + b"]" * 2000
        large_number = b'{"repository":{"id":' + b"9" * 5000 + b"}}"
        responses = []
        for body, delivery_id in (
            (deeply_nested, "delivery-deep-json"),
            (large_number, "delivery-large-number"),
        ):
            signature = (
                "sha256="
                + hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
            )
            responses.append(
                self.url_open(
                    self.route,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-GitHub-Event": "push",
                        "X-GitHub-Delivery": delivery_id,
                        "X-Hub-Signature-256": signature,
                    },
                )
            )

        self.assertEqual([response.status_code for response in responses], [400, 400])
        self.assertEqual(self._delivery_count(), 0)

    def test_concurrent_replay_creates_one_delivery(self):
        """Exercise duplicate-key recovery through concurrent signed HTTP requests."""

        start_requests = threading.Barrier(2)
        statuses = []
        failures = []
        raw_body = json.dumps(self._payload(), separators=(",", ":")).encode()
        request_url = self.base_url() + self.route
        request_headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-concurrent",
            "X-Hub-Signature-256": "sha256="
            + hmac.new(self.secret.encode(), raw_body, hashlib.sha256).hexdigest(),
        }

        def post_delivery(test_cookies):
            try:
                start_requests.wait(timeout=5)
                statuses.append(
                    requests.post(
                        request_url,
                        data=raw_body,
                        headers=request_headers,
                        cookies=test_cookies,
                        timeout=10,
                    ).status_code
                )
            except BaseException as error:  # pragma: no cover - asserted below
                failures.append(error)

        with self.allow_requests():
            test_cookies = self.opener.cookies.get_dict()
            first_thread = threading.Thread(target=post_delivery, args=(test_cookies,))
            replay_thread = threading.Thread(target=post_delivery, args=(test_cookies,))
            first_thread.start()
            replay_thread.start()
            first_thread.join(10)
            replay_thread.join(10)

        self.assertFalse(first_thread.is_alive())
        self.assertFalse(replay_thread.is_alive())
        self.assertFalse(failures, failures)
        self.assertEqual(statuses, [202, 202])
        self.assertEqual(self._delivery_count(), 1)

    def test_invalid_unknown_and_inactive_repositories_are_rejected(self):
        invalid = self._post(self._payload(), secret="wrong-secret")
        unknown = self._post(self._payload("9999"), delivery_id="delivery-unknown")
        self.repository.active = False
        inactive = self._post(self._payload(), delivery_id="delivery-inactive")

        self.assertEqual(
            (invalid.status_code, unknown.status_code, inactive.status_code),
            (401, 401, 401),
        )
        self.assertTrue(
            all(not response.content for response in (invalid, unknown, inactive))
        )
        self.assertEqual(self._delivery_count(), 0)

    def test_cross_company_repository_requires_its_own_configured_secret(self):
        other_company = self.env["res.company"].create({"name": "Other company"})
        other_project = (
            self.env["project.project"]
            .with_company(other_company)
            .create(
                {
                    "name": "Other GitHub ingress",
                    "company_id": other_company.id,
                    "privacy_visibility": "employees",
                    "agile_enabled": True,
                    "agile_key": "OTH",
                }
            )
        )
        other_repository = self.env["project.git.repository"].create(
            {
                "name": "other-ingress",
                "provider": "github",
                "provider_repository_id": "4243",
                "canonical_url": "https://github.com/other/ingress",
                "project_id": other_project.id,
                "webhook_secret": "other-company-secret",
            }
        )

        response = self._post(
            self._payload("4243"),
            delivery_id="delivery-cross-company",
            secret=self.secret,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, b"")
        self.assertFalse(
            self.env["project.git.delivery"].search(
                [("repository_id", "=", other_repository.id)]
            )
        )

        accepted = self._post(
            self._payload("4243"),
            delivery_id="delivery-cross-company-valid",
            secret="other-company-secret",
        )
        self.assertEqual(accepted.status_code, 202)
        self.assertEqual(accepted.content, b"")
        self.assertEqual(
            self.env["project.git.delivery"].search_count(
                [("repository_id", "=", other_repository.id)]
            ),
            1,
        )

    def test_malformed_oversized_and_unsupported_requests_are_rejected(self):
        malformed_body = b"{"
        malformed_signature = (
            "sha256="
            + hmac.new(self.secret.encode(), malformed_body, hashlib.sha256).hexdigest()
        )
        malformed = self.url_open(
            self.route,
            data=malformed_body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-GitHub-Delivery": "delivery-malformed",
                "X-Hub-Signature-256": malformed_signature,
            },
        )
        unsupported = self._post(self._payload(), **{"Content-Type": "text/plain"})
        oversized = self.url_open(
            self.route,
            data=b"x" * (256 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(
            (malformed.status_code, unsupported.status_code, oversized.status_code),
            (400, 415, 413),
        )
        self.assertTrue(
            all(
                not response.content for response in (malformed, unsupported, oversized)
            )
        )
        self.assertEqual(self._delivery_count(), 0)

    def test_missing_signature_is_rejected_without_creating_a_delivery(self):
        raw_body = json.dumps(self._payload(), separators=(",", ":")).encode()

        response = self.url_open(
            self.route,
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-GitHub-Delivery": "delivery-missing-signature",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._delivery_count(), 0)

    def test_redacted_excerpt_never_retains_credential_shaped_payload_values(self):
        self.repository.retention_policy = "redacted_excerpt"

        response = self._post(
            self._payload(token="must-not-be-retained"), delivery_id="delivery-redacted"
        )

        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", "delivery-redacted"),
            ]
        )
        self.assertEqual(
            json.loads(delivery.retained_payload), {"repository": {"id": "4242"}}
        )
        self.assertNotIn("must-not-be-retained", delivery.retained_payload)
        self.assertTrue(delivery.retained_until)

    def test_redacted_excerpt_scrubs_credential_shaped_scalar_text(self):
        self.repository.retention_policy = "redacted_excerpt"
        credential = "TOPSECRET123"

        response = self._post(
            {
                **self._payload(),
                "commits": [{"message": "Authorization: " + "Bearer " + credential}],
            },
            delivery_id="delivery-scalar-secret",
        )

        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", "delivery-scalar-secret"),
            ]
        )
        self.assertNotIn(credential, delivery.retained_payload)
        self.assertIn("[redacted]", delivery.retained_payload)

    def test_redacted_excerpt_scrubs_github_fine_grained_token_text(self):
        self.repository.retention_policy = "redacted_excerpt"
        credential = "github_pat_" + "A" * 24

        response = self._post(
            {
                **self._payload(),
                "ref": "refs/heads/rotated-provider-credential-" + credential,
            },
            delivery_id="delivery-github-pat",
        )

        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", "delivery-github-pat"),
            ]
        )
        self.assertNotIn(credential, delivery.retained_payload)
        self.assertIn("[redacted]", delivery.retained_payload)

    def _branch_deletion_payload(self, ref):
        payload = json.loads(
            (Path(__file__).parent / "fixtures" / "push.json").read_text()
        )
        payload["repository"]["id"] = 4242
        payload.update(
            ref=ref,
            before=payload["after"],
            after="0" * 40,
            created=False,
            deleted=True,
            head_commit=None,
            commits=[],
        )
        return payload

    def _post_and_settle_push(self, payload, delivery_id):
        self.assertEqual(self._post(payload, delivery_id).status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [
                ("provider_delivery_id", "=", delivery_id),
                ("repository_id", "=", self.repository.id),
            ]
        )
        self.assertEqual(delivery.state, "queued", delivery.error_summary)
        claimed = self.env["project.git.delivery"]._claim_github_delivery()
        self.assertEqual(claimed, delivery)
        claimed._settle_github_delivery()
        self.env.invalidate_all()
        return delivery

    def _github_fact_snapshot(self):
        return {
            model: self.env[model]
            .search([("repository_id", "=", self.repository.id)], order="id")
            .read(load=None)
            for model in (
                "project.git.branch",
                "project.git.commit",
                "project.git.task.association",
                "project.git.association.audit",
            )
        }

    def test_branch_deletion_without_facts_is_discarded(self):
        self.repository.retention_policy = "redacted_excerpt"
        task = self.env["project.task"].create(
            {"name": "Deletion is not task activity", "project_id": self.project.id}
        )
        task_fields = ["stage_id", "message_partner_ids", "write_date"]
        task_before = task.read(task_fields)
        facts_before = self._github_fact_snapshot()
        payload = self._branch_deletion_payload("refs/heads/feature/" + task.agile_key)
        delivery = self._post_and_settle_push(payload, "branch-deletion-absent")

        self.assertEqual((delivery.state, delivery.attempt_count), ("discarded", 1))
        self.assertEqual(
            delivery.error_summary,
            "Branch deleted on GitHub. Its branch and commit records are unchanged.",
        )
        self.assertTrue(delivery.processed_at)
        self.assertFalse(delivery.lease_token)
        self.assertFalse(delivery.lease_expires_at)
        self.assertEqual(
            json.loads(delivery.retained_payload),
            {
                "repository": {"id": 4242},
                "ref": payload["ref"],
                "after": "0" * 40,
                "deleted": True,
                "head_commit": None,
                "commits": [],
                "omitted_commit_count": 0,
            },
        )
        self.assertTrue(delivery.retained_until)
        self.assertEqual(self._github_fact_snapshot(), facts_before)
        self.assertEqual(task.read(task_fields), task_before)

    def test_branch_deletion_preserves_existing_facts_and_push_ordering(self):
        def adapt(payload, key):
            payload["ref"] = "refs/heads/feature/" + key
            payload["commits"][0]["message"] += " " + key

        normal, original, task = self._sample_delivery("push", adapt)
        task_fields = ["stage_id", "message_partner_ids", "write_date"]
        task_before = task.read(task_fields)
        before = self._github_fact_snapshot()
        deletion = self._post_and_settle_push(
            self._branch_deletion_payload(normal["ref"]), "branch-deletion-existing"
        )
        self.assertEqual(deletion.state, "discarded", deletion.error_summary)
        self.assertEqual(self._github_fact_snapshot(), before)
        deletion.action_reprocess_github_delivery()
        claimed = self.env["project.git.delivery"]._claim_github_delivery()
        self.assertEqual(claimed, deletion)
        claimed._settle_github_delivery()
        self.env.invalidate_all()
        self.assertEqual((deletion.state, deletion.attempt_count), ("discarded", 2))
        self.assertEqual(self._github_fact_snapshot(), before)

        normal["after"] = "a" * 40
        normal["head_commit"]["timestamp"] = "2026-01-03T03:04:05Z"
        normal["commits"] = []
        later = self._post_and_settle_push(normal, "push-after-deletion")
        self.assertEqual(later.state, "processed", later.error_summary)
        branch = self.env["project.git.branch"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(
            (branch.head_sha, branch.provenance_delivery_id), ("a" * 40, later)
        )
        self.assertEqual(branch.ordering_state, "known")
        normal["after"] = "b" * 40
        normal["head_commit"]["timestamp"] = "2026-01-01T03:04:05Z"
        stale = self._post_and_settle_push(normal, "stale-push-after-deletion")
        self.assertEqual(stale.state, "processed", stale.error_summary)
        self.assertEqual(
            (branch.head_sha, branch.provenance_delivery_id), ("a" * 40, later)
        )
        self.assertEqual(branch.ordering_state, "stale")
        self.assertNotEqual(branch.provenance_delivery_id, original)
        self.assertEqual(task.read(task_fields), task_before)

    def test_malformed_or_nondeletion_null_heads_are_not_discarded(self):
        self.repository.retention_policy = "redacted_excerpt"
        changes = (
            (None, "normalizer"),
            ({"deleted": "true"}, "normalizer"),
            ({"deleted": 1}, "normalizer"),
            ({"deleted": 0}, "normalizer"),
            ({"deleted": None}, "normalizer"),
            ({"deleted": False, "head_commit": {}}, "normalizer"),
            ({"deleted": False}, "normalizer"),
            ({"after": "a" * 40}, "normalizer"),
            ({"head_commit": {}}, "normalizer"),
            ({"head_commit": []}, "ingress"),
            ({"commits": [{"id": "a" * 40, "message": "GHI-1"}]}, "normalizer"),
            ({"ref": "refs/heads/../../other-repository"}, "normalizer"),
            ({"ref": "refs/heads/%2e%2e/other-repository"}, "normalizer"),
        )
        before = self._github_fact_snapshot()
        for index, (change, expected_phase) in enumerate(changes):
            with self.subTest(change=change, expected_phase=expected_phase):
                payload = self._branch_deletion_payload("refs/heads/feature/GHI-1")
                if change is None:
                    del payload["deleted"]
                else:
                    payload.update(change)
                delivery_id = "invalid-deletion-" + str(index)
                self.assertEqual(self._post(payload, delivery_id).status_code, 202)
                delivery = self.env["project.git.delivery"].search(
                    [
                        ("repository_id", "=", self.repository.id),
                        ("provider_delivery_id", "=", delivery_id),
                    ]
                )
                self.assertEqual(
                    delivery.state,
                    "queued" if expected_phase == "normalizer" else "failed",
                    delivery.error_summary,
                )
                if expected_phase == "normalizer":
                    claimed = self.env["project.git.delivery"]._claim_github_delivery()
                    self.assertEqual(claimed, delivery)
                    claimed._settle_github_delivery()
                    self.env.invalidate_all()
                self.assertEqual(delivery.state, "failed", delivery.error_summary)
                self.assertTrue(delivery.error_summary)
                self.assertEqual(self._github_fact_snapshot(), before)

    def _sample_delivery(self, event, adapt):
        self.repository.retention_policy = "redacted_excerpt"
        task = self.env["project.task"].create(
            {"name": "Official sample reference", "project_id": self.project.id}
        )
        payload = json.loads(
            (Path(__file__).parent / "fixtures" / (event + ".json")).read_text()
        )
        payload["repository"]["id"] = 4242
        adapt(payload, task.agile_key)
        raw = json.dumps(payload, separators=(",", ":")).encode()
        self.assertGreater(len(raw), 4096)
        response = self._post(payload, "sample-" + event, **{"X-GitHub-Event": event})
        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", "sample-" + event),
            ]
        )
        self.assertEqual(delivery.payload_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(delivery.payload_size, len(raw))
        self.assertEqual(delivery.state, "queued", delivery.error_summary)
        retained = json.loads(delivery.retained_payload)
        self.assertEqual(retained["repository"], {"id": 4242})
        self.assertNotIn("sender", retained)
        self.assertNotIn("installation", retained)
        self.assertNotIn("users.noreply.github.com", delivery.retained_payload)
        claimed = self.env["project.git.delivery"]._claim_github_delivery()
        self.assertEqual(claimed, delivery)
        claimed._settle_github_delivery()
        self.env.invalidate_all()
        self.assertEqual(delivery.state, "processed", delivery.error_summary)
        return payload, delivery, task

    def _assert_sample_link(self, task, source_type, provider_id):
        links = self.env["project.git.task.association"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("source_type", "=", source_type),
                ("source_provider_id", "=", provider_id),
            ]
        )
        self.assertEqual(links.task_id, task)
        self.assertEqual(links.agile_key, task.agile_key)

    def test_realistic_push_produces_facts_and_links(self):
        def adapt(payload, key):
            payload["ref"] = "refs/heads/feature/" + key
            payload["commits"][0]["message"] += " " + key
            payload["head_commit"]["message"] += " " + key

        payload, delivery, task = self._sample_delivery("push", adapt)
        branch = self.env["project.git.branch"].search(
            [("repository_id", "=", self.repository.id)]
        )
        commit = self.env["project.git.commit"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(branch.name, "feature/" + task.agile_key)
        self.assertEqual(branch.head_sha, "6113728f27ae82c7b1a177c8d03f9e96e0adf246")
        self.assertEqual(str(branch.source_updated_at), "2019-05-15 15:19:25")
        self.assertEqual(commit.sha, branch.head_sha)
        self.assertEqual(commit.message_excerpt, "Initial commit " + task.agile_key)
        self.assertEqual(commit.provenance_delivery_id, delivery)
        retained = json.loads(delivery.retained_payload)
        self.assertEqual(set(retained["commits"][0]), {"id", "message", "timestamp"})
        self._assert_sample_link(task, "branch", payload["ref"])
        self._assert_sample_link(task, "commit", commit.sha)

    def test_realistic_pull_request_produces_facts_and_links(self):
        def adapt(payload, key):
            payload["pull_request"]["title"] += " " + key
            payload["pull_request"]["body"] += " " + key
            payload["pull_request"]["head"]["ref"] += "/" + key

        payload, delivery, task = self._sample_delivery("pull_request", adapt)
        pull = self.env["project.git.pull.request"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(pull.provider_request_id, "279147437")
        self.assertEqual(pull.number, "2")
        self.assertEqual(
            pull.title, "Update the README with new information. " + task.agile_key
        )
        self.assertEqual(
            (pull.state, pull.source_branch, pull.target_branch),
            ("open", "changes/" + task.agile_key, "master"),
        )
        self.assertEqual(str(pull.updated_at), "2019-05-15 15:20:33")
        self.assertEqual(pull.head_sha, "ec26c3e57ca3a959ca5aad62de7213c562f8c821")
        self.assertEqual(pull.provenance_delivery_id, delivery)
        self.assertNotIn("user", json.loads(delivery.retained_payload)["pull_request"])
        self._assert_sample_link(
            task, "pull_request", str(payload["pull_request"]["id"])
        )
        audits = self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id), ("task_id", "=", task.id)]
        )
        self.assertEqual(
            set(audits.mapped("source_field")), {"title", "body", "head_ref"}
        )

    def test_realistic_check_run_produces_facts_and_links(self):
        def adapt(payload, key):
            payload["check_run"]["name"] += " " + key
            payload["check_run"]["output"]["title"] = key

        payload, delivery, task = self._sample_delivery("check_run", adapt)
        check = self.env["project.git.check"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(check.provider_check_id, "128620228")
        self.assertEqual(check.name, "Octocoders-linter " + task.agile_key)
        self.assertEqual(check.state, "success")
        self.assertEqual(check.head_sha, "ec26c3e57ca3a959ca5aad62de7213c562f8c821")
        self.assertEqual(str(check.completed_at), "2019-05-15 15:21:12")
        self.assertFalse(check.updated_at)
        self.assertEqual(check.provenance_delivery_id, delivery)
        output = json.loads(delivery.retained_payload)["check_run"]["output"]
        self.assertEqual(output, {"title": task.agile_key})
        self._assert_sample_link(task, "check", str(payload["check_run"]["id"]))
        audits = self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id), ("task_id", "=", task.id)]
        )
        self.assertEqual(set(audits.mapped("source_field")), {"name", "output_title"})

    def test_oversized_required_field_is_terminal_without_partial_facts(self):
        self.repository.retention_policy = "redacted_excerpt"
        payload = {
            **self._payload(),
            "ref": "refs/heads/" + "x" * 4096,
            "after": "a" * 40,
            "commits": [{"id": "a" * 40, "message": "GHI-1"}],
        }
        response = self._post(payload, "required-overflow")
        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(delivery.state, "failed")
        self.assertIn("oversized processing input", delivery.error_summary)
        self.assertFalse(delivery.retained_payload)
        self.assertFalse(delivery.retained_until)
        self.assertEqual(delivery.attempt_count, 0)
        self.assertFalse(self.env["project.git.delivery"]._claim_github_delivery())
        self.assertFalse(
            self.env["project.git.branch"].search(
                [("repository_id", "=", self.repository.id)]
            )
        )
        with self.assertRaises(ValidationError):
            delivery.action_reprocess_github_delivery()

    def test_projection_does_not_hide_mismatched_raw_body_replays(self):
        self.repository.retention_policy = "redacted_excerpt"
        payload = {**self._payload(), "sender": {"login": "first"}}
        first = self._post(payload, "projection-replay")
        payload["sender"]["login"] = "second"
        second = self._post(payload, "projection-replay")
        self.assertEqual((first.status_code, second.status_code), (202, 409))
        delivery = self.env["project.git.delivery"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(delivery.replay_mismatch_count, 1)
        self.assertNotIn("sender", delivery.retained_payload)

    def test_fifty_real_length_commit_messages_keep_keys_after_display_excerpt(self):
        credential = "ghp_" + "S" * 24
        narrative = (
            "Explain the migration, compatibility and verification details. " * 12
        )

        def adapt(payload, key):
            payload["ref"] = "refs/heads/main"
            payload["commits"] = [
                {
                    "id": f"{index:040x}",
                    "timestamp": "2026-10-19T12:00:00Z",
                    "message": credential + " " + narrative + key + " " + key,
                }
                for index in range(1, 51)
            ]
            payload["after"] = payload["commits"][-1]["id"]
            payload["head_commit"]["timestamp"] = "2026-10-19T12:00:00Z"
            payload["omitted_commit_count"] = 999

        payload, delivery, task = self._sample_delivery("push", adapt)
        commits = self.env["project.git.commit"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(len(commits), 50)
        self.assertTrue(all(len(commit.message_excerpt) == 255 for commit in commits))
        self.assertNotIn(credential, delivery.retained_payload)
        self.assertNotIn(narrative, delivery.retained_payload)
        self.assertEqual(delivery.omitted_commit_count, 0)
        retained = json.loads(delivery.retained_payload)
        self.assertEqual(retained["omitted_commit_count"], 0)
        for commit in payload["commits"]:
            self._assert_sample_link(task, "commit", commit["id"])
        for commit in retained["commits"]:
            self.assertEqual(commit["message"]["keys"], [task.agile_key])
            self.assertNotIn(task.agile_key, commit["message"]["excerpt"])
        audits = self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id)]
        )
        self.assertEqual(len(audits), 50)
        self.assertEqual(set(audits.mapped("source_field")), {"message"})
        self.assertEqual(set(audits.mapped("reason")), {"exact_key"})

    def test_ten_thousand_character_pr_body_keeps_only_late_key_evidence(self):
        credential = "github_pat_" + "S" * 24
        private_text = "Private generated change narrative. " * 300

        def adapt(payload, key):
            payload["pull_request"]["body"] = credential + " " + private_text + key

        payload, delivery, task = self._sample_delivery("pull_request", adapt)
        self.assertGreater(len(payload["pull_request"]["body"]), 10000)
        self.assertNotIn(credential, delivery.retained_payload)
        self.assertNotIn("Private generated", delivery.retained_payload)
        retained_body = json.loads(delivery.retained_payload)["pull_request"]["body"]
        self.assertEqual(retained_body, {"keys": [task.agile_key], "reason": False})
        pull = self.env["project.git.pull.request"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(pull.provider_request_id, str(payload["pull_request"]["id"]))
        self.assertEqual(pull.title, payload["pull_request"]["title"])
        self._assert_sample_link(task, "pull_request", pull.provider_request_id)
        audits = self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id)]
        )
        self.assertEqual((audits.source_field, audits.reason), ("body", "exact_key"))

    def test_large_push_advances_head_and_persists_exact_omission_after_replay(self):
        branch = self.env["project.git.branch"].create(
            {
                "repository_id": self.repository.id,
                "provider_branch_id": "refs/heads/main",
                "name": "main",
                "head_sha": "f" * 40,
                "source_updated_at": "2026-10-18 12:00:00",
            }
        )

        def adapt(payload, key):
            payload["ref"] = "refs/heads/main"
            payload["after"] = f"{150:040x}"
            payload["head_commit"]["timestamp"] = "2026-10-19T12:00:00Z"
            payload["commits"] = [
                {"id": f"{index:040x}", "message": "Merge work for " + key}
                for index in range(1, 151)
            ]

        payload, delivery, task = self._sample_delivery("push", adapt)
        self.assertEqual(branch.head_sha, payload["after"])
        self.assertEqual(branch.ordering_state, "known")
        self.assertEqual(branch.provenance_delivery_id, delivery)
        self.assertEqual(str(branch.source_updated_at), "2026-10-19 12:00:00")
        commits = self.env["project.git.commit"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(
            set(commits.mapped("sha")), {f"{i:040x}" for i in range(1, 101)}
        )
        self.assertEqual(delivery.omitted_commit_count, 50)
        self.assertEqual(
            delivery.commit_omission_reason,
            "Only the first 100 commits in a push are retained.",
        )
        self.assertFalse(delivery.error_summary)
        self.assertEqual(len(json.loads(delivery.retained_payload)["commits"]), 100)
        links = self.env["project.git.task.association"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(len(links), 100)
        self.assertEqual(links.task_id, task)
        audits = self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id)]
        )
        self.assertEqual(len(audits), 100)
        replay = self._post(payload, "sample-push")
        self.assertEqual(replay.status_code, 202)
        self.env.invalidate_all()
        self.assertEqual(self._delivery_count(), 1)
        self.assertEqual(
            (delivery.state, delivery.omitted_commit_count), ("processed", 50)
        )
        self.assertTrue(delivery.commit_omission_reason)
        self.assertEqual(
            delivery.payload_sha256,
            hashlib.sha256(
                json.dumps(payload, separators=(",", ":")).encode()
            ).hexdigest(),
        )
        # Reprocessing is another settlement; it must not clear the notice or
        # duplicate facts/decisions even when associations already exist.
        delivery.state = "failed"
        delivery.action_reprocess_github_delivery()
        claimed = self.env["project.git.delivery"]._claim_github_delivery()
        self.assertEqual(claimed, delivery)
        claimed._settle_github_delivery()
        self.env.invalidate_all()
        self.assertEqual(
            (delivery.state, delivery.omitted_commit_count), ("processed", 50)
        )
        self.assertTrue(delivery.commit_omission_reason)
        self.assertEqual(
            self.env["project.git.commit"].search_count(
                [("repository_id", "=", self.repository.id)]
            ),
            100,
        )
        self.assertEqual(
            self.env["project.git.association.audit"].search_count(
                [("delivery_id", "=", delivery.id)]
            ),
            100,
        )

    def test_compact_sources_preserve_invalid_excessive_and_deduplicated_audits(self):
        def adapt(payload, key):
            payload["ref"] = "refs/heads/main"
            messages = [
                "GHI-01",
                " ".join(f"GHI-{index}" for index in range(1, 22)),
                key + " " + key + " GHI-01",
                "é" + key + " _" + key + " " + key + "_",
            ]
            payload["commits"] = [
                {"id": f"{index:040x}", "message": "x" * 5000 + " " + message}
                for index, message in enumerate(messages, 1)
            ]

        _payload, delivery, task = self._sample_delivery("push", adapt)
        audits = self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id)]
        )
        self.assertEqual(len(audits), 4)
        self.assertEqual(
            {audit.source_provider_id: audit.reason for audit in audits},
            {
                f"{1:040x}": "invalid_key",
                f"{2:040x}": "too_many_keys",
                f"{3:040x}": "exact_key",
                f"{4:040x}": "invalid_key",
            },
        )
        self.assertEqual(set(audits.mapped("source_field")), {"message"})
        self._assert_sample_link(task, "commit", f"{3:040x}")
        self.assertEqual(
            self.env["project.git.task.association"].search_count(
                [("repository_id", "=", self.repository.id)]
            ),
            1,
        )

    def _post_environment_pr(
        self, task, identity, branch, timestamp, suffix, merged=True
    ):
        payload = {
            "repository": {"id": 4242},
            "number": identity,
            "pull_request": {
                "id": identity,
                "number": identity,
                "title": task.agile_key,
                "body": "",
                "state": "closed" if merged else "open",
                "merged": merged,
                "head": {"ref": "feature/" + task.agile_key, "sha": "a" * 40},
                "base": {"ref": branch},
                "updated_at": timestamp,
                "merged_at": "2026-10-20T11:00:00Z" if merged else None,
            },
        }
        response = self._post(payload, suffix, **{"X-GitHub-Event": "pull_request"})
        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", suffix),
            ]
        )
        claimed = self.env["project.git.delivery"]._claim_github_delivery()
        self.assertEqual(claimed, delivery)
        claimed._settle_github_delivery()
        self.assertEqual(delivery.state, "processed", delivery.error_summary)
        return payload, delivery

    def _assert_environment_pr_evidence(self, task, uat, production, expected, gap):
        values = task.read(["git_merge_environment_ids"])[0]
        self.assertEqual(set(values["git_merge_environment_ids"]), set(expected))
        found = task.search(
            [
                ("id", "=", task.id),
                ("git_uat_without_production_id", "in", [uat.id]),
            ]
        )
        self.assertEqual(bool(found), gap)
        self.assertEqual(
            bool(
                task.search(
                    [
                        ("id", "=", task.id),
                        ("git_merge_environment_ids", "in", [uat.id]),
                    ]
                )
            ),
            uat.id in expected,
        )
        self.assertEqual(
            bool(
                task.search(
                    [
                        ("id", "=", task.id),
                        ("git_merge_environment_ids", "in", [production.id]),
                    ]
                )
            ),
            production.id in expected,
        )

    def test_signed_merge_conflict_recovery_replay_purge_and_manual_isolation(
        self,
    ):
        self.repository.retention_policy = "redacted_excerpt"
        uat, production = self.env["project.agile.environment"].create(
            [
                {"name": "UAT", "project_id": self.project.id},
                {
                    "name": "Production",
                    "project_id": self.project.id,
                    "is_production": True,
                },
            ]
        )
        self.env["project.git.environment.branch"].create(
            [
                {
                    "environment_id": uat.id,
                    "repository_id": self.repository.id,
                    "branch_name": "uat",
                },
                {
                    "environment_id": production.id,
                    "repository_id": self.repository.id,
                    "branch_name": "main",
                },
            ]
        )
        task = self.env["project.task"].create(
            {
                "name": "Manual configuration",
                "project_id": self.project.id,
                "agile_item_type_id": self.env.ref(
                    "project_agile.project_agile_item_type_configuration"
                ).id,
            }
        )
        lines = task.agile_environment_status_ids
        lines[0].status = "verified"
        task_fields = [
            "stage_id",
            "state",
            "agile_item_type_id",
            "write_date",
            "message_ids",
        ]
        line_fields = ["status", "actor_id", "changed_at", "message_ids", "write_date"]
        before_task, before_lines = task.read(task_fields), lines.read(line_fields)
        timestamp = "2026-10-20T12:00:00Z"
        self._post_environment_pr(task, 801, "uat", timestamp, "uat-known")
        self._assert_environment_pr_evidence(task, uat, production, [uat.id], True)
        self._post_environment_pr(task, 802, "main", timestamp, "prod-known")
        self._assert_environment_pr_evidence(
            task, uat, production, [uat.id, production.id], False
        )
        for identity, branch, other_id in (
            (801, "uat", production.id),
            (802, "main", uat.id),
        ):
            with self.subTest(branch=branch):
                self._post_environment_pr(
                    task,
                    identity,
                    "other",
                    timestamp,
                    branch + "-conflict",
                    merged=False,
                )
                self._assert_environment_pr_evidence(
                    task, uat, production, [other_id], branch == "main"
                )
                self._post_environment_pr(
                    task, identity, branch, "2026-10-19T12:00:00Z", branch + "-older"
                )
                self._assert_environment_pr_evidence(
                    task, uat, production, [other_id], branch == "main"
                )
                self._post_environment_pr(
                    task, identity, branch, timestamp, branch + "-same-time"
                )
                self._assert_environment_pr_evidence(
                    task, uat, production, [other_id], branch == "main"
                )
                self._post_environment_pr(
                    task, identity, branch, "2026-10-21T12:00:00Z", branch + "-recovery"
                )
                self._assert_environment_pr_evidence(
                    task, uat, production, [uat.id, production.id], False
                )
        # Even a harmless late event demotes confidence; it does not prove absence.
        self._post_environment_pr(task, 801, "uat", timestamp, "uat-harmless-late")
        self._assert_environment_pr_evidence(
            task, uat, production, [production.id], False
        )
        payload, delivery = self._post_environment_pr(
            task, 801, "uat", "2026-10-22T12:00:00Z", "uat-final"
        )
        self._assert_environment_pr_evidence(
            task, uat, production, [uat.id, production.id], False
        )
        self.assertEqual(
            self._post(
                payload, "uat-final", **{"X-GitHub-Event": "pull_request"}
            ).status_code,
            202,
        )
        delivery.retained_until = "2000-01-01 00:00:00"
        self.env["project.git.delivery"]._purge_expired_github_payloads()
        self.assertFalse(delivery.retained_payload)
        self.assertTrue(delivery.retained_payload_purged_at)
        self._assert_environment_pr_evidence(
            task, uat, production, [uat.id, production.id], False
        )
        # Reverts are linked observations, not current-presence arithmetic.
        self._post_environment_pr(task, 803, "uat", timestamp, "revert-observation")
        self._assert_environment_pr_evidence(
            task, uat, production, [uat.id, production.id], False
        )
        deleted = self._post_and_settle_push(
            self._branch_deletion_payload("refs/heads/uat"), "uat-deleted"
        )
        self.assertEqual(deleted.state, "discarded")
        self._assert_environment_pr_evidence(
            task, uat, production, [uat.id, production.id], False
        )
        self.assertEqual(task.read(task_fields), before_task)
        self.assertEqual(lines.read(line_fields), before_lines)
