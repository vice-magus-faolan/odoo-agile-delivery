"""Typed, pure decision predicates; no ORM writes, clocks, providers or dispatch."""

import hashlib
import json
import re
from datetime import timedelta


VERSION = 1
MAX_BATCH = 20
MAX_EVIDENCE = 20
FULL_SHA = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
KEY = re.compile(r"[A-Z][A-Z0-9]{1,9}-[1-9][0-9]*\Z")
OUTCOMES = [(n, n.title()) for n in ("matched", "waiting", "skipped", "conflicted", "rejected")]
REASONS = [(n, n.replace("_", " ").title()) for n in (
    "no_ci_condition", "checks_passed", "missing_check", "pending_check", "check_failed",
    "ambiguous_check", "invalid_provenance", "ambiguous_order", "invalid_time", "before_cutoff",
    "expired", "branch_mismatch", "inactive_task", "inactive_repository", "inactive_policy",
    "ineligible_task", "already_target", "stale_task", "conflicting_rules", "evidence_limit",
    "invalid_authority",
)]


def canonical(value):
    """Stable bounded-input JSON; datetimes are converted by the typed producer."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def pr_condition(pr, activation, now):
    """Exact branch, reliable order and strict post-cutoff source/receipt freshness."""
    if pr.ordering_state != "known":
        return "rejected", "ambiguous_order"
    if not pr.merged_at or not pr.updated_at or pr.merged_at > now or pr.updated_at > now:
        return "rejected", "invalid_time"
    if pr.updated_at < pr.merged_at:
        return "rejected", "invalid_time"
    if pr.merged_at <= activation.activated_at or pr.provenance_delivery_id.received_at <= activation.activated_at:
        return "rejected", "before_cutoff"
    if min(pr.merged_at, pr.updated_at) < now - timedelta(hours=24):
        return "skipped", "expired"
    if pr.target_branch != activation.revision_id.target_branch:
        return "skipped", "branch_mismatch"
    return None


def check_condition(check, merged_at, now):
    """A single identity is not a rerun ordering rule; pending is never success."""
    if check.ordering_state != "known" or not check.updated_at or check.updated_at > now:
        return "rejected", "ambiguous_check"
    if check.updated_at < now - timedelta(hours=24):
        return "rejected", "ambiguous_check"
    if check.state in {"pending", "running"}:
        return "waiting", "pending_check"
    if check.state in {"failure", "cancelled", "neutral"}:
        return "rejected", "check_failed"
    if check.state != "success" or not check.completed_at:
        return "rejected", "ambiguous_check"
    lower_bound = max(merged_at - timedelta(hours=24), now - timedelta(hours=24))
    if not lower_bound <= check.completed_at <= min(now, check.updated_at):
        return "rejected", "ambiguous_check"
    return None


def reduce_conditions(conditions):
    """Stable precedence; a pending earlier name cannot conceal a later failure."""
    rank = {"rejected": 0, "skipped": 1, "waiting": 2, "matched": 3}
    return min(conditions, key=lambda item: (rank[item[0]], item[1])) if conditions else None
