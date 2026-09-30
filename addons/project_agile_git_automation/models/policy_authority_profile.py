"""Fail-closed support classification, never an access-rule evaluator.

Native Odoo still evaluates permissions. These private metadata reads establish
whether every applicable dependency has a fixed revoke-only observer. Unknown
rules cannot be made supported by caller context or by restoring a fingerprint.
"""

import ast
import hashlib
from typing import NoReturn

from odoo import _
from odoo.exceptions import AccessError


# Observed on the pinned Odoo 19 image; AST hashes ignore comments/whitespace,
# not operators, identifiers or literal values. Permissions are read/write/create/unlink.
# Exact XML identity, model, groups and all four permissions are part of the profile.
NATIVE_RULES = {
    "base.res_users_rule": ("res.users", "6298ea1e6b44086eb1018b9f46c61c6bc9ecdec0a383cffaa98c2b98343da1dc", (), (True, True, True, True)),
    "project.task_type_manager_rule": ("project.task.type", "848eb6c7d33657dff56281b95c2f43e918520387630daeca7b3551617be4f7f0", ("project.group_project_manager",), (True, True, True, True)),
    "project.task_type_visibility_rule": ("project.task.type", "b28629dd0f391bb3209f8fd57b564b28aa3e6bf46114fa5cd366f3389b0bba9b", (), (True, True, True, True)),
    "project.task_type_own_write_rule": ("project.task.type", "9a793612f300280803bfe510c4567489227dea84925530780c36d5d0a19a3f7e", ("project.group_project_user",), (False, True, True, True)),
    "project_agile_git.project_git_repository_company_rule": ("project.git.repository", "8ad6ca0d9ca45f0f824c5aeed23a475dbfae6a051d0bb315fbe34dcc691c94bb", (), (True, True, True, True)),
    "project_agile_git.project_git_repository_visibility_rule": ("project.git.repository", "a09c4f702a0ba96da99cfcd260a0f5b87c2d1fc927d9d3358730dd1758b6eb1e", ("project.group_project_user",), (True, True, True, True)),
    "project_agile_git.project_git_repository_manager_visibility_rule": ("project.git.repository", "848eb6c7d33657dff56281b95c2f43e918520387630daeca7b3551617be4f7f0", ("project.group_project_manager",), (True, True, True, True)),
    "project.task_comp_rule": ("project.task", "8ad6ca0d9ca45f0f824c5aeed23a475dbfae6a051d0bb315fbe34dcc691c94bb", (), (True, True, True, True)),
    "project.task_visibility_rule": ("project.task", "8e99b4b11fb6135ca9bb1153e97f9d8566a5259355ff393477333bd3236860f2", ("base.group_user",), (True, False, False, False)),
    "project.project_manager_all_project_tasks_rule": ("project.task", "41851a54e76ed252930e37ac03e1a0afca879e16895853e3711eb2bda1ce87fe", ("project.group_project_manager",), (True, True, True, True)),
    "project.task_visibility_rule_project_user": ("project.task", "8e99b4b11fb6135ca9bb1153e97f9d8566a5259355ff393477333bd3236860f2", ("project.group_project_user",), (False, True, True, True)),
    "project.ir_rule_private_task": ("project.task", "2e25af4cb7c85ec7967d534550a412470d499d811d5c4a1d65b3a87bf929ddae", ("project.group_project_user",), (True, True, True, True)),
    "project_todo.task_edition_rule_internal": ("project.task", "1d9bb81a785e3a215c3b1a9539df7060180c3f3ec9193626615ea7fc8118daae", ("base.group_user",), (True, True, True, True)),
    "project.project_comp_rule": ("project.project", "8ad6ca0d9ca45f0f824c5aeed23a475dbfae6a051d0bb315fbe34dcc691c94bb", (), (True, True, True, True)),
    "project.project_project_manager_rule": ("project.project", "848eb6c7d33657dff56281b95c2f43e918520387630daeca7b3551617be4f7f0", ("project.group_project_manager",), (True, True, True, True)),
    "project.project_public_members_rule": ("project.project", "bcac010237a0fe80c8c826d3227370b22dc6a83ea544620cab7e7d53aeb8835b", ("base.group_user",), (True, True, True, True)),
}

TASK_AUTHORITY_FIELDS = frozenset({
    "name", "active", "project_id", "company_id", "parent_id", "display_in_project",
    "user_ids", "message_partner_ids", "message_follower_ids", "personal_stage_type_ids",
})
TASK_SCOPE_FIELDS = frozenset({"project_id", "company_id", "parent_id", "display_in_project", "child_ids"})


def _unsupported() -> NoReturn:
    # No rule names/domains, hidden metadata or record IDs escape this boundary.
    raise AccessError(_("Installed authority profile is unsupported; reviewed dependency coverage is required."))


def _literal_value(field, value):
    if field == "active":
        return type(value) is bool
    return value is False or (isinstance(value, str) and len(value) <= 255)


def _literal_leaf(token):
    if not isinstance(token, (tuple, list)) or len(token) != 3:
        return False
    field, operator, value = token
    if field not in ("name", "active") or operator not in ("=", "!=", "in", "not in"):
        return False
    if operator in ("in", "not in"):
        return isinstance(value, (tuple, list)) and 1 <= len(value) <= 64 and all(_literal_value(field, v) for v in value)
    return _literal_value(field, value)


def _literal_tokens(source):
    """Bound parsing independently of the boolean grammar validation."""
    try:
        if not isinstance(source, str) or len(source) > 8192:
            _unsupported()
        tokens = ast.literal_eval(source)
    except (ValueError, SyntaxError, RecursionError, MemoryError):
        _unsupported()
    if not isinstance(tokens, list) or not 1 <= len(tokens) <= 127:
        _unsupported()
    return tokens


def _check_literal_domain(source):
    """Parse bounded existing rule data without evaluating any Python expression."""
    tokens = _literal_tokens(source)
    # Prefix boolean operators plus ordinary implicit AND of complete expressions.
    # Reverse-stack arity validation prevents malformed prefix trees being accepted.
    expressions, leaves = 0, 0
    for token in reversed(tokens):
        if isinstance(token, str) and token in ("&", "|", "!"):
            arity = 1 if token == "!" else 2
            if expressions < arity:
                _unsupported()
            expressions -= arity - 1
        elif _literal_leaf(token):
            expressions += 1
            leaves += 1
        else:
            _unsupported()
    if not expressions or leaves > 64:
        _unsupported()


FIELD_PROFILE = (
    ("project.task", "name", "char", True, None, ()),
    ("project.task", "active", "boolean", True, None, ()),
    ("project.task", "parent_id", "many2one", True, None, ()),
    ("project.task", "user_ids", "many2many", True, None, ()),
    ("project.task", "personal_stage_type_ids", "many2many", True, None, ()),
    ("project.task.stage.personal", "task_id", "many2one", True, None, ()),
    ("project.task.stage.personal", "user_id", "many2one", True, None, ()),
    ("project.task", "project_id", "many2one", True, "_compute_project_id", ("parent_id.project_id",)),
    ("project.task", "company_id", "many2one", True, "_compute_company_id", ("project_id.company_id", "parent_id.company_id")),
    ("project.task", "display_in_project", "boolean", True, "_compute_display_in_project", ("project_id", "parent_id")),
    ("project.task", "message_partner_ids", "many2many", False, "_compute_message_partner_ids", ("message_follower_ids",)),
    ("project.project", "privacy_visibility", "selection", True, None, ()),
    ("project.project", "partner_id", "many2one", True, None, ()),
    ("project.project", "account_id", "many2one", True, None, ()),
    ("project.project", "company_id", "many2one", True, "_compute_company_id", ("account_id.company_id", "partner_id.company_id")),
    ("project.project", "message_partner_ids", "many2many", False, "_compute_message_partner_ids", ("message_follower_ids",)),
    ("res.users", "share", "boolean", True, "_compute_share", ("all_group_ids",)),
    ("res.users", "active", "boolean", True, None, ()),
    ("res.users", "partner_id", "many2one", True, None, ()),
    ("res.users", "company_ids", "many2many", True, None, ()),
    ("res.users", "group_ids", "many2many", True, None, ()),
    ("res.users", "all_group_ids", "many2many", False, "_compute_all_group_ids", ("group_ids.all_implied_ids",)),
    ("res.groups", "implied_ids", "many2many", True, None, ()),
    ("res.groups", "implied_by_ids", "many2many", True, None, ()),
    ("res.groups", "rule_groups", "many2many", True, None, ()),
    ("res.partner", "company_id", "many2one", True, None, ()),
    ("account.analytic.account", "company_id", "many2one", True, None, ()),
    ("project.task.type", "active", "boolean", True, None, ()),
    ("project.task.type", "project_ids", "many2many", True, None, ()),
    ("project.task.type", "user_id", "many2one", True, "_compute_user_id", ("project_ids",)),
)


def _check_fields(env):
    """Unknown computed, related, contextual or mutable dependencies fail closed."""
    for model, name, kind, stored, compute, depends in FIELD_PROFILE:
        record = env[model]
        field = record._fields.get(name)
        if field is None:
            _unsupported()
        actual, context = field.get_depends(record)
        signature = (field.type, field.store, field.compute, set(actual))
        if signature != (kind, stored, compute, set(depends)):
            _unsupported()
        if context or field.related or field.company_dependent:
            _unsupported()


def _metadata_id(env, xmlid, model):
    """Resolve fixed rule/group identities from live metadata, not cached env.ref.

    Native ir.model.data.write does not invalidate every XML lookup cache. Support
    classification must notice missing/remapped identities in this transaction.
    The model is fixed by our two internal callers, never RPC/configuration data.
    """
    module, name = xmlid.split(".", 1)
    data = env["ir.model.data"].sudo().search([("module", "=", module), ("name", "=", name)], limit=1)
    if not data or data.model != model:
        _unsupported()
    return data.res_id


def _native_matches(env, rule, expected):
    model, digest, groups, permissions = expected
    if not isinstance(rule.domain_force, str) or len(rule.domain_force) > 8192:
        return False
    try:
        normalized = ast.dump(ast.parse(rule.domain_force or "[]", mode="eval"), include_attributes=False)
    except (ValueError, SyntaxError, RecursionError):
        return False
    group_ids = {_metadata_id(env, xmlid, "res.groups") for xmlid in groups}
    actual_permissions = (rule.perm_read, rule.perm_write, rule.perm_create, rule.perm_unlink)
    return (rule.active and rule.model_id.model == model and set(rule.groups.ids) == group_ids
            and actual_permissions == permissions and hashlib.sha256(normalized.encode()).hexdigest() == digest)


def check_supported_profile(repository, identities):
    """Private support proof after current caller scope checks; no authority elevation.

    Metadata is narrowly read with sudo; access decisions still use each real user.
    Every checked-in native definition must remain present and exact. Additional
    applicable read/write rules are supported ONLY for literal direct Task inputs.
    Group/ACL/rule changes revoke all epochs; actor partner/company/group changes,
    native follower edits and observed stored/computed scope inputs have fixed hooks.
    """
    env = repository.env
    _check_fields(env)
    native_ids = set()
    for xmlid, expected in NATIVE_RULES.items():
        rule = env["ir.rule"].sudo().browse(_metadata_id(env, xmlid, "ir.rule")).exists()
        if not rule or not _native_matches(env, rule, expected):
            _unsupported()
        native_ids.add(rule.id)
    models = sorted({value[0] for value in NATIVE_RULES.values()})
    rules = env["ir.rule"].sudo().search([
        ("model_id.model", "in", models), "|", ("perm_read", "=", True), ("perm_write", "=", True),
    ], limit=129)
    if len(rules) > 128:
        _unsupported()
    groups = set(identities.sudo().all_group_ids.ids)
    for rule in rules:
        if rule.id in native_ids or (rule.groups and not groups.intersection(rule.groups.ids)):
            continue
        if rule.model_id.model != "project.task":
            _unsupported()
        _check_literal_domain(rule.domain_force)
