"""Asynchronous GitHub-to-provider-neutral Git fact normalization."""

import json
import secrets
from datetime import datetime, timezone
from urllib.parse import quote, unquote

from psycopg2 import IntegrityError
from psycopg2.errors import SerializationFailure

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .github_keys import (
    MAX_PROVIDER_COMMITS,
    MAX_RETAINED_COMMITS,
    source_key_summary,
    validated_key_summary,
)

BATCH_SIZE = 20
LEASE_SECONDS = 300
MAX_ATTEMPTS = 5
MAX_RETRY_SECONDS = 3600
MAX_SOURCE_TEXT = 4096


class GitHubPayloadError(ValueError):
    """A retained GitHub payload is malformed or cannot be normalized safely."""


class GitHubDiscarded(ValueError):
    """A valid but unsupported GitHub delivery is retained as a terminal diagnostic."""


def _utc_datetime(value):
    """Return a UTC-naive datetime only for an unambiguous provider timestamp."""

    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _text(value, maximum=MAX_SOURCE_TEXT):
    """Return a bounded string or fail closed for a malformed provider field."""

    if not isinstance(value, str) or len(value) > maximum:
        raise GitHubPayloadError(
            "A required GitHub text field is malformed or oversized."
        )
    return value


def _optional_text(value, maximum=MAX_SOURCE_TEXT):
    """Return a bounded optional string without coercing provider data."""

    if value is None:
        return False
    return _text(value, maximum)


def _identifier(value, maximum=128):
    """Return one provider identifier without accepting boolean or missing values."""

    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise GitHubPayloadError("A GitHub provider identifier is malformed.")
    return _text(str(value), maximum)


def _commit_message_excerpt(value):
    """Read compact message evidence or the previously delivered text shape."""

    if isinstance(value, dict):
        try:
            return validated_key_summary(value, with_excerpt=True)["excerpt"]
        except ValueError as error:
            raise GitHubPayloadError(
                "The GitHub commit evidence is malformed."
            ) from error
    return _text(value)[:255]


def _github_state(status, conclusion):
    """Map GitHub check state without assigning any task workflow meaning."""

    if status in {"queued", "pending", "requested", "waiting"}:
        return "pending"
    if status in {"in_progress", "running"}:
        return "running"
    if status != "completed":
        return "unknown"
    return {
        "success": "success",
        "failure": "failure",
        "timed_out": "failure",
        "action_required": "failure",
        "cancelled": "cancelled",
        "skipped": "neutral",
        "neutral": "neutral",
    }.get(conclusion, "unknown")


def _github_branch_name(value):
    """Return a URL-safe GitHub branch name or reject traversal aliases."""

    name = _text(value)
    for component in name.split("/"):
        decoded = unquote(component)
        if decoded in {".", ".."} or "/" in decoded or "\\" in decoded:
            raise GitHubPayloadError("The GitHub branch ref is unsafe.")
    return name


def _github_fact_url(repository, path, identifier, preserve_slashes=False):
    """Derive an external GitHub fact URL from validated repository configuration
    only.
    """

    try:
        repository._validated_canonical_url()
    except ValidationError as error:
        raise GitHubPayloadError("The GitHub repository URL is invalid.") from error
    safe = "/" if preserve_slashes else ""
    return (
        repository.canonical_url.rstrip("/")
        + "/"
        + path
        + "/"
        + quote(identifier, safe=safe)
    )


class ProjectGitDelivery(models.Model):
    """Lease and normalize retained GitHub deliveries outside the webhook request."""

    # Asynchronous normalization is separate from authenticated ingress.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.git.delivery"

    omitted_commit_count = fields.Integer(
        readonly=True,
        copy=False,
        help="Commits omitted from this push after retaining its first 100 commits.",
    )
    commit_omission_reason = fields.Char(
        readonly=True,
        copy=False,
        help="Why this delivery retained fewer commits than GitHub supplied.",
    )

    @api.model
    def _claim_github_delivery(self):
        """Atomically lease one eligible ledger row without trusting caller context."""

        now = fields.Datetime.now()
        domain = [
            ("provider", "=", "github"),
            "|",
            "&",
            ("state", "in", ("queued", "retryable")),
            "|",
            ("next_retry_at", "=", False),
            ("next_retry_at", "<=", now),
            "&",
            ("state", "=", "processing"),
            ("lease_expires_at", "<=", now),
        ]
        # Only this private background boundary leases across companies. Public
        # replay remains subject to manager authorization and record access.
        queue = self.sudo()
        lease_token = secrets.token_urlsafe(24)
        try:
            with self.env.cr.savepoint():
                candidates = queue.search(
                    domain, order="received_at, id", limit=BATCH_SIZE
                )
                delivery = candidates.try_lock_for_update(limit=1)
                if delivery:
                    delivery.write(
                        {
                            "state": "processing",
                            "lease_token": lease_token,
                            "lease_expires_at": fields.Datetime.add(
                                now, seconds=LEASE_SECONDS
                            ),
                            "attempt_count": delivery.attempt_count + 1,
                            "next_retry_at": False,
                        }
                    )
                    return delivery.with_context(git_delivery_lease=lease_token)
        except SerializationFailure:
            return self.browse()
        return self.browse()

    @api.model
    def _cron_normalize_github_deliveries(self):
        """Process a bounded leased batch and commit each settled delivery
        separately.
        """

        remaining = self.sudo().search_count(
            [
                ("provider", "=", "github"),
                "|",
                "&",
                ("state", "in", ("queued", "retryable")),
                "|",
                ("next_retry_at", "=", False),
                ("next_retry_at", "<=", fields.Datetime.now()),
                "&",
                ("state", "=", "processing"),
                ("lease_expires_at", "<=", fields.Datetime.now()),
            ]
        )
        self.env["ir.cron"]._commit_progress(remaining=min(remaining, BATCH_SIZE))
        processed = 0
        while processed < BATCH_SIZE:
            delivery = self._claim_github_delivery()
            if not delivery:
                break
            delivery._settle_github_delivery()
            processed += 1
            if not self.env["ir.cron"]._commit_progress(processed=1):
                break
        return processed

    def _settle_github_delivery(self):
        """Settle one claimed delivery atomically, retaining either facts or
        diagnostics.
        """

        self.ensure_one()
        lease_token = self.env.context.get("git_delivery_lease")
        if (
            self.state != "processing"
            or not lease_token
            or self.lease_token != lease_token
        ):
            return False
        try:
            with self.env.cr.savepoint():
                if not self._normalize_github_delivery():
                    return True
                self.write(
                    {
                        "state": "processed",
                        "processed_at": fields.Datetime.now(),
                        "lease_token": False,
                        "lease_expires_at": False,
                        "error_summary": False,
                    }
                )
        except GitHubDiscarded as error:
            self.write(
                {
                    "state": "discarded",
                    "lease_token": False,
                    "lease_expires_at": False,
                    "error_summary": str(error)[:255],
                    "processed_at": fields.Datetime.now(),
                }
            )
        except GitHubPayloadError as error:
            self._record_github_failure(str(error), retryable=False)
        except Exception:
            self._record_github_failure(
                "GitHub fact normalization failed.", retryable=True
            )
        return True

    def _record_github_failure(self, summary, retryable):
        """Persist bounded retry/dead-letter diagnostics after savepoint rollback."""

        self.ensure_one()
        attempts = self.attempt_count
        values = {
            "lease_token": False,
            "lease_expires_at": False,
            "error_summary": summary[:255],
            "last_error_at": fields.Datetime.now(),
            "processed_at": False,
        }
        if retryable and attempts < MAX_ATTEMPTS:
            delay = min(2 ** max(attempts - 1, 0) * 60, MAX_RETRY_SECONDS)
            values.update(
                {
                    "state": "retryable",
                    "next_retry_at": fields.Datetime.add(
                        fields.Datetime.now(), seconds=delay
                    ),
                }
            )
        else:
            values.update({"state": "failed", "next_retry_at": False})
        self.write(values)

    def action_reprocess_github_delivery(self):
        """Safely requeue a failed GitHub delivery after server-side manager
        authorization.
        """

        if not self.env.user.has_group("project.group_project_manager"):
            raise AccessError(
                _("Only Project Managers can reprocess GitHub deliveries.")
            )
        self.check_access("read")
        for delivery in self:
            if delivery.provider != "github" or delivery.state not in {
                "failed",
                "discarded",
            }:
                raise ValidationError(
                    _("Only terminal GitHub deliveries can be reprocessed.")
                )
            if not delivery.sudo().retained_payload:
                raise ValidationError(
                    _("This GitHub delivery has no retained payload to reprocess.")
                )
        self.sudo().write(
            {
                "state": "queued",
                "next_retry_at": False,
                "lease_token": False,
                "lease_expires_at": False,
                "error_summary": False,
                "last_error_at": False,
                "processed_at": False,
            }
        )
        return True

    def _normalize_github_delivery(self):
        """Normalize one retained GitHub payload without changing a Project task."""

        self.ensure_one()
        if self.provider != "github" or not self.retained_payload:
            raise GitHubPayloadError(
                "No retained redacted payload is available for normalization."
            )
        try:
            payload = json.loads(self.retained_payload)
        except (TypeError, json.JSONDecodeError) as error:
            raise GitHubPayloadError(
                "The retained GitHub payload is malformed."
            ) from error
        if not isinstance(payload, dict):
            raise GitHubPayloadError(
                "The retained GitHub payload must be a JSON object."
            )
        repository = payload.get("repository")
        if (
            not isinstance(repository, dict)
            or _identifier(repository.get("id"))
            != self.repository_id.provider_repository_id
        ):
            raise GitHubPayloadError(
                "The GitHub payload repository does not match "
                "the authenticated delivery."
            )
        handlers = {
            "push": self._normalize_github_push,
            "pull_request": self._normalize_github_pull_request,
            "check_run": self._normalize_github_check_run,
        }
        handler = handlers.get(self.event_type)
        if not handler:
            raise GitHubDiscarded("Unsupported GitHub event type.")
        handler(payload)
        return True

    def _normalize_github_push(self, payload):
        """Normalize GitHub push branch and commit observations."""

        ref = _text(payload.get("ref"))
        if not ref.startswith("refs/heads/") or len(ref) == len("refs/heads/"):
            raise GitHubPayloadError("The GitHub push ref is not a branch ref.")
        branch_name = _github_branch_name(ref.removeprefix("refs/heads/"))
        head_sha = _text(payload.get("after"), 128)
        head_commit = payload.get("head_commit", {})
        deleted = payload.get("deleted", False)
        if not isinstance(deleted, bool):
            raise GitHubPayloadError("The GitHub push deletion flag is malformed.")
        if deleted:
            if (
                head_sha != "0" * 40
                or head_commit is not None
                or payload.get("commits") != []
            ):
                raise GitHubPayloadError("The GitHub branch deletion is malformed.")
            raise GitHubDiscarded(
                "Branch deleted on GitHub. Its branch and commit records are unchanged."
            )
        if head_sha == "0" * 40:
            raise GitHubPayloadError("The GitHub push has no live branch head.")
        if not isinstance(head_commit, dict):
            raise GitHubPayloadError("The GitHub push head commit is malformed.")
        source_updated_at = _utc_datetime(head_commit.get("timestamp"))
        branch = self._upsert_branch(ref, branch_name, head_sha, source_updated_at)
        self._associate_source_keys(
            "branch", branch.provider_branch_id, {"ref": branch_name}
        )
        commits = payload.get("commits", [])
        if not isinstance(commits, list) or len(commits) > MAX_RETAINED_COMMITS:
            raise GitHubPayloadError(
                "The GitHub push commits collection is malformed or oversized."
            )
        omitted = payload.get("omitted_commit_count", 0)
        if (
            type(omitted) is not int
            or not 0 <= omitted <= MAX_PROVIDER_COMMITS - MAX_RETAINED_COMMITS
            or (omitted and len(commits) != MAX_RETAINED_COMMITS)
        ):
            raise GitHubPayloadError("The GitHub omitted commit count is malformed.")
        self.write(
            {
                "omitted_commit_count": omitted,
                "commit_omission_reason": (
                    "Only the first 100 commits in a push are retained."
                    if omitted
                    else False
                ),
            }
        )
        for commit_data in commits:
            if not isinstance(commit_data, dict):
                raise GitHubPayloadError("The GitHub push contains a malformed commit.")
            commit_sha = _text(commit_data.get("id"), 128)
            commit_message = commit_data.get("message")
            self._upsert_commit(commit_data)
            self._associate_source_keys(
                "commit", commit_sha, {"message": commit_message}
            )

    def _normalize_github_pull_request(self, payload):
        """Normalize GitHub pull-request lifecycle observations and referenced
        branches.
        """

        pull_request = payload.get("pull_request")
        if not isinstance(pull_request, dict):
            raise GitHubPayloadError("The GitHub pull request is malformed.")
        provider_request_id = _identifier(pull_request.get("id"))
        number = _identifier(payload.get("number"), 64)
        head = pull_request.get("head")
        base = pull_request.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise GitHubPayloadError("The GitHub pull request branches are malformed.")
        source_branch = _github_branch_name(head.get("ref"))
        target_branch = _github_branch_name(base.get("ref"))
        head_sha = _text(head.get("sha"), 128)
        state = (
            "merged"
            if pull_request.get("merged")
            else _text(pull_request.get("state"), 32)
        )
        if state not in {"open", "closed", "merged", "draft"}:
            raise GitHubPayloadError("The GitHub pull request state is unsupported.")
        updated_at = _utc_datetime(pull_request.get("updated_at"))
        self._upsert_pull_request(
            {
                "provider_request_id": provider_request_id,
                "number": number,
                "title": _text(pull_request.get("title")),
                "state": state,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "head_sha": head_sha,
                "url": _github_fact_url(self.repository_id, "pull", number),
                "merged_at": _utc_datetime(pull_request.get("merged_at")),
                "updated_at": updated_at,
            }
        )
        self._upsert_branch(
            "refs/heads/" + source_branch, source_branch, head_sha, updated_at
        )
        self._upsert_branch(
            "refs/heads/" + target_branch, target_branch, False, updated_at
        )
        self._associate_source_keys(
            "pull_request",
            provider_request_id,
            {
                "title": _text(pull_request.get("title")),
                "body": pull_request.get("body")
                if pull_request.get("body") is not None
                else "",
                "head_ref": source_branch,
            },
        )

    def _normalize_github_check_run(self, payload):
        """Normalize a GitHub check-run state observation."""

        check_run = payload.get("check_run")
        if not isinstance(check_run, dict):
            raise GitHubPayloadError("The GitHub check run is malformed.")
        provider_check_id = _identifier(check_run.get("id"))
        updated_at = _utc_datetime(check_run.get("updated_at"))
        self._upsert_check(
            {
                "provider_check_id": provider_check_id,
                "name": _text(check_run.get("name")),
                "state": _github_state(
                    check_run.get("status"), check_run.get("conclusion")
                ),
                "head_sha": _optional_text(check_run.get("head_sha"), 128),
                "url": _github_fact_url(self.repository_id, "runs", provider_check_id),
                "completed_at": _utc_datetime(check_run.get("completed_at")),
                "updated_at": updated_at,
            }
        )
        output = check_run.get("output", {})
        if not isinstance(output, dict):
            raise GitHubPayloadError("The GitHub check output is malformed.")
        self._associate_source_keys(
            "check",
            provider_check_id,
            {
                "name": _text(check_run.get("name")),
                "output_title": _optional_text(output.get("title")) or "",
            },
        )

    def _upsert_branch(self, provider_branch_id, name, head_sha, source_updated_at):
        """Upsert a branch only when source ordering permits a state replacement."""

        branch_model = self.env["project.git.branch"].sudo()
        branch = branch_model.search(
            [
                ("repository_id", "=", self.repository_id.id),
                ("provider_branch_id", "=", provider_branch_id),
            ],
            limit=1,
        )
        values = {
            "name": name,
            "head_sha": head_sha,
            "source_updated_at": source_updated_at,
            "last_seen_at": fields.Datetime.now(),
            "provenance_delivery_id": self.id,
            "url": _github_fact_url(
                self.repository_id, "tree", name, preserve_slashes=True
            ),
            "ordering_state": "known" if source_updated_at else "ambiguous",
        }
        if not branch:
            return branch_model.create(
                {
                    "repository_id": self.repository_id.id,
                    "provider_branch_id": provider_branch_id,
                    **values,
                }
            )
        return self._apply_ordered_fact_update(branch, values, "source_updated_at")

    def _upsert_commit(self, commit_data):
        """Create an immutable GitHub commit fact or refresh its observation
        provenance.
        """

        sha = _text(commit_data.get("id"), 128)
        commit_model = self.env["project.git.commit"].sudo()
        commit = commit_model.search(
            [("repository_id", "=", self.repository_id.id), ("sha", "=", sha)], limit=1
        )
        values = {
            "message_excerpt": _commit_message_excerpt(commit_data.get("message")),
            "authored_at": _utc_datetime(commit_data.get("timestamp")),
            "url": _github_fact_url(self.repository_id, "commit", sha),
            "last_seen_at": fields.Datetime.now(),
            "provenance_delivery_id": self.id,
        }
        if commit:
            commit.write(
                {
                    "last_seen_at": values["last_seen_at"],
                    "provenance_delivery_id": self.id,
                }
            )
            return commit
        return commit_model.create(
            {"repository_id": self.repository_id.id, "sha": sha, **values}
        )

    def _upsert_pull_request(self, values):
        """Upsert a pull request without allowing old or ambiguous events to
        regress it.
        """

        model = self.env["project.git.pull.request"].sudo()
        record = model.search(
            [
                ("repository_id", "=", self.repository_id.id),
                ("provider_request_id", "=", values["provider_request_id"]),
            ],
            limit=1,
        )
        values.update(
            {
                "last_seen_at": fields.Datetime.now(),
                "provenance_delivery_id": self.id,
                "ordering_state": "known" if values["updated_at"] else "ambiguous",
            }
        )
        if not record:
            return model.create({"repository_id": self.repository_id.id, **values})
        return self._apply_ordered_fact_update(record, values, "updated_at")

    def _upsert_check(self, values):
        """Upsert a check only when the event timestamp makes the replacement safe."""

        model = self.env["project.git.check"].sudo()
        record = model.search(
            [
                ("repository_id", "=", self.repository_id.id),
                ("provider_check_id", "=", values["provider_check_id"]),
            ],
            limit=1,
        )
        values.update(
            {
                "last_seen_at": fields.Datetime.now(),
                "provenance_delivery_id": self.id,
                "ordering_state": "known" if values["updated_at"] else "ambiguous",
            }
        )
        if not record:
            return model.create({"repository_id": self.repository_id.id, **values})
        return self._apply_ordered_fact_update(record, values, "updated_at")

    def _apply_ordered_fact_update(self, record, values, timestamp_field):
        """Refresh observation metadata without guessing when source order is
        unknown.
        """

        incoming = values[timestamp_field]
        current = record[timestamp_field]
        observation_values = {"last_seen_at": values["last_seen_at"]}
        if not incoming or not current:
            observation_values["ordering_state"] = "ambiguous"
            record.write(observation_values)
            return record
        if incoming < current:
            observation_values["ordering_state"] = "stale"
            record.write(observation_values)
            return record
        if incoming == current:
            state_fields = {
                key: value
                for key, value in values.items()
                if key
                not in {"last_seen_at", "provenance_delivery_id", "ordering_state"}
            }
            if any(record[key] != value for key, value in state_fields.items()):
                observation_values["ordering_state"] = "ambiguous"
            record.write(observation_values)
            return record
        record.write(values)
        return record

    def _associate_source_keys(self, source_type, source_provider_id, fields_by_name):
        """Create immutable associations or idempotent audit facts for explicit
        key tokens.
        """

        for source_field, text in fields_by_name.items():
            try:
                evidence = (
                    validated_key_summary(
                        text,
                        with_excerpt=source_type == "commit"
                        and source_field == "message",
                    )
                    if isinstance(text, dict)
                    else source_key_summary(_text(text))
                )
            except ValueError as error:
                raise GitHubPayloadError(
                    "The GitHub key evidence is malformed."
                ) from error
            if evidence["reason"]:
                self._record_association_audit(
                    source_type,
                    source_provider_id,
                    source_field,
                    "[invalid]",
                    "rejected",
                    evidence["reason"],
                )
                continue
            keys = evidence["keys"]
            for agile_key in keys:
                self._associate_agile_key(
                    source_type, source_provider_id, source_field, agile_key
                )

    def _associate_agile_key(
        self, source_type, source_provider_id, source_field, agile_key
    ):
        """Resolve a key only inside the repository project and record the outcome."""

        task_model = (
            self.env["project.task"]
            .sudo()
            .with_company(self.repository_id.company_id)
            .with_context(active_test=False)
        )
        project_tasks = task_model.search(
            [
                ("project_id", "=", self.repository_id.project_id.id),
                ("agile_key", "=", agile_key),
            ]
        )
        if len(project_tasks) != 1:
            self._record_association_audit(
                source_type,
                source_provider_id,
                source_field,
                agile_key,
                "unassociated",
                "unknown_key",
            )
            return
        task = project_tasks
        if task.company_id != self.repository_id.company_id:
            self._record_association_audit(
                source_type,
                source_provider_id,
                source_field,
                agile_key,
                "rejected",
                "cross_company",
            )
            return
        if not task.active:
            self._record_association_audit(
                source_type,
                source_provider_id,
                source_field,
                agile_key,
                "rejected",
                "archived_task",
            )
            return
        association_model = self.env["project.git.task.association"].sudo()
        association_domain = [
            ("repository_id", "=", self.repository_id.id),
            ("company_id", "=", self.repository_id.company_id.id),
            ("task_id", "=", task.id),
            ("agile_key", "=", agile_key),
            ("source_type", "=", source_type),
            ("source_provider_id", "=", source_provider_id),
        ]
        existing = association_model.search(association_domain, limit=1)
        if existing:
            # A durable link is not current-delivery evidence by itself. Preserve
            # the freshly resolved active local Task on this immutable decision.
            self._record_association_audit(
                source_type,
                source_provider_id,
                source_field,
                agile_key,
                "already_associated",
                "duplicate",
                task,
            )
            return
        try:
            with self.env.cr.savepoint():
                association_model.create(
                    {
                        "repository_id": self.repository_id.id,
                        "task_id": task.id,
                        "source_type": source_type,
                        "source_provider_id": source_provider_id,
                    }
                )
        except IntegrityError:
            # Only an exact visible winner proves a duplicate. An unrelated
            # constraint or a winner invisible to this transaction must escape
            # to native fresh-transaction recovery, never mint an audit proof.
            if not association_model.search(association_domain, limit=1):
                raise
            self._record_association_audit(
                source_type,
                source_provider_id,
                source_field,
                agile_key,
                "already_associated",
                "duplicate",
                task,
            )
            return
        self._record_association_audit(
            source_type,
            source_provider_id,
            source_field,
            agile_key,
            "associated",
            "exact_key",
            task,
        )

    def _record_association_audit(
        self,
        source_type,
        source_provider_id,
        source_field,
        agile_key,
        outcome,
        reason,
        task=None,
    ):
        """Persist an immutable, delivery-scoped association decision without
        task writes.
        """

        audit_model = self.env["project.git.association.audit"].sudo()
        existing = audit_model.search(
            [
                ("delivery_id", "=", self.id),
                ("source_type", "=", source_type),
                ("source_provider_id", "=", source_provider_id),
                ("source_field", "=", source_field),
                ("agile_key", "=", agile_key),
            ],
            limit=1,
        )
        if not existing:
            audit_model.create(
                {
                    "repository_id": self.repository_id.id,
                    "delivery_id": self.id,
                    "source_type": source_type,
                    "source_provider_id": source_provider_id,
                    "source_field": source_field,
                    "agile_key": agile_key,
                    "outcome": outcome,
                    "reason": reason,
                    "task_id": task.id if task else False,
                }
            )
