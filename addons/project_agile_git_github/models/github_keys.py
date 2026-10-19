"""Shared bounded key evidence for ingress and retained GitHub processing."""

import re

MAX_KEYS_PER_SOURCE = 20
MAX_KEY_LENGTH = 128
MAX_RETAINED_COMMITS = 100
MAX_PROVIDER_COMMITS = 2048
AGILE_KEY_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_\u0080-\U0010FFFF])(?P<key>[A-Z][A-Z0-9]{1,9}-[1-9][0-9]*)(?![A-Za-z0-9_\u0080-\U0010FFFF])"
)
KEY_LIKE_PATTERN = re.compile(r"[A-Z][A-Z0-9]{0,32}-[0-9]+")


def source_key_summary(text):
    """Match the entire source, keeping only bounded distinct key evidence."""

    keys = {}
    for match in AGILE_KEY_PATTERN.finditer(text):
        key = match.group("key")
        keys[key] = None
        if len(keys) > MAX_KEYS_PER_SOURCE:
            return {"keys": [], "reason": "too_many_keys"}
    if any(len(key) > MAX_KEY_LENGTH for key in keys):
        raise ValueError("A GitHub task key is oversized.")
    reason = "invalid_key" if not keys and KEY_LIKE_PATTERN.search(text) else False
    return {"keys": list(keys), "reason": reason}


def validated_key_summary(value, with_excerpt=False):
    """Reject malformed compact evidence before it can affect association audits."""

    expected = {"keys", "reason"}
    if with_excerpt:
        expected.add("excerpt")
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("The GitHub key evidence is malformed.")
    keys = value["keys"]
    reason = value["reason"]
    if not isinstance(keys, list) or len(keys) > MAX_KEYS_PER_SOURCE:
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
    if reason and keys:
        raise ValueError("Rejected GitHub key evidence cannot contain keys.")
    if with_excerpt and (
        not isinstance(value["excerpt"], str) or len(value["excerpt"]) > 255
    ):
        raise ValueError("The GitHub commit excerpt is malformed.")
    return value
