"""Shared bounded key evidence for ingress and retained GitHub processing."""

import re

MAX_KEYS_PER_SOURCE = 20
MAX_KEYS_PER_PR_BODY = 100
MAX_KEY_LENGTH = 128
MAX_RETAINED_COMMITS = 100
MAX_PROVIDER_COMMITS = 2048
AGILE_KEY_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_\u0080-\U0010FFFF])(?P<key>[A-Z][A-Z0-9]{1,9}-[1-9][0-9]*)(?![A-Za-z0-9_\u0080-\U0010FFFF])"
)
KEY_LIKE_PATTERN = re.compile(r"[A-Z][A-Z0-9]{0,32}-[0-9]+")


def source_key_summary(text, *, pull_request_body=False):
    """Match the entire source, keeping only bounded distinct key evidence."""

    limit = MAX_KEYS_PER_PR_BODY if pull_request_body else MAX_KEYS_PER_SOURCE
    keys = {}
    for match in AGILE_KEY_PATTERN.finditer(text):
        key = match.group("key")
        if len(key) > MAX_KEY_LENGTH:
            raise ValueError("A GitHub task key is oversized.")
        keys[key] = None
        if len(keys) > limit:
            # Release bodies keep a useful bounded prefix; other fields retain
            # their stricter all-or-nothing policy and storage/work budgets.
            return {
                "keys": list(keys)[:limit] if pull_request_body else [],
                "reason": "too_many_keys",
            }
    reason = "invalid_key" if not keys and KEY_LIKE_PATTERN.search(text) else False
    return {"keys": list(keys), "reason": reason}


def validated_key_summary(value, with_excerpt=False, *, pull_request_body=False):
    """Reject malformed compact evidence before it can affect association audits."""

    expected = {"keys", "reason"}
    if with_excerpt:
        expected.add("excerpt")
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("The GitHub key evidence is malformed.")
    keys = value["keys"]
    reason = value["reason"]
    limit = MAX_KEYS_PER_PR_BODY if pull_request_body else MAX_KEYS_PER_SOURCE
    if not isinstance(keys, list) or len(keys) > limit:
        raise ValueError("The GitHub key evidence collection is malformed.")
    for key in keys:
        if (
            not isinstance(key, str)
            or len(key) > MAX_KEY_LENGTH
            or not AGILE_KEY_PATTERN.fullmatch(key)
        ):
            raise ValueError("The GitHub key evidence contains an invalid key.")
    if len(set(keys)) != len(keys):
        raise ValueError("The GitHub key evidence contains duplicate keys.")
    if reason is not False and reason not in ("invalid_key", "too_many_keys"):
        raise ValueError("The GitHub key evidence reason is malformed.")
    if (
        reason
        and keys
        and not (pull_request_body and reason == "too_many_keys" and len(keys) == limit)
    ):
        raise ValueError("Rejected GitHub key evidence cannot contain keys.")
    if with_excerpt and (
        not isinstance(value["excerpt"], str) or len(value["excerpt"]) > 255
    ):
        raise ValueError("The GitHub commit excerpt is malformed.")
    return value
