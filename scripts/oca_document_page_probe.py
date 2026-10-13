"""Emit and assert the installed OCA Document Page runtime contract."""

# pyright: reportUndefinedVariable=false
# Odoo's ``odoo shell`` injects ``env`` into this script's globals.

import json


def field_contract(model_name, field_names):
    """Return stable field metadata for the selected installed model."""
    model = env[model_name]
    return {
        name: {
            "comodel": model._fields[name].comodel_name,
            "required": model._fields[name].required,
            "type": model._fields[name].type,
        }
        for name in field_names
    }


def xmlid_id(xmlid):
    """Resolve one required XML ID and return its installed database ID."""
    return env.ref(xmlid).id


page_model = env["document.page"]
history_model = env["document.page.history"]
project_model = env["project.project"]

category = page_model.create(
    {
        "name": "Fixture category",
        "type": "category",
        "template": "<p>Fixture template</p>",
    }
)
draft_page = page_model.new({"name": "Fixture draft", "parent_id": category.id})
draft_page._onchange_parent_id()
assert draft_page.content == category.template

page = page_model.create(
    {
        "name": "Fixture page",
        "parent_id": category.id,
        "content": "<p>Initial fixture content</p>",
        "draft_name": "1.0",
        "draft_summary": "Initial fixture history",
    }
)
page.content = "<p>Updated fixture content</p>"
assert page.history_head
assert len(page.history_ids) == 2
history_ids = page.history_ids.ids
page.active = False
assert not page.active
page.unlink()
assert not page.exists()
assert not history_model.browse(history_ids).exists()

project = project_model.create({"name": "Fixture project"})
project_page = page_model.create(
    {"name": "Fixture project page", "project_id": project.id}
)
assert project_page in project.document_page_ids
assert project.document_page_count == 1

acl_rows = env["ir.model.access"].search(
    [("model_id.model", "in", ["document.page", "document.page.history"])]
)
rules = {
    xmlid: env.ref(xmlid).domain_force
    for xmlid in (
        "document_page.document_page_rule",
        "document_page.document_page_history_rule",
    )
}

contract = {
    "actions": {
        xmlid: xmlid_id(xmlid)
        for xmlid in (
            "document_page.view_wiki_form",
            "document_page.view_wiki_tree",
            "document_page.view_wiki_filter",
            "document_page_project.action_document_page_projects",
        )
    },
    "archive_delete": {
        "active_after_archive": False,
        "history_deleted_with_page": True,
        "page_deleted": True,
    },
    "company": {
        "default_company_id": category.company_id.id,
        "page_rule": rules["document_page.document_page_rule"],
        "history_rule": rules["document_page.document_page_history_rule"],
    },
    "fields": {
        "document.page": field_contract(
            "document.page",
            (
                "name",
                "type",
                "active",
                "parent_id",
                "child_ids",
                "content",
                "template",
                "history_head",
                "history_ids",
                "company_id",
                "project_id",
            ),
        ),
        "document.page.history": field_contract(
            "document.page.history",
            ("page_id", "name", "summary", "content", "company_id"),
        ),
        "project.project": field_contract(
            "project.project", ("document_page_ids", "document_page_count")
        ),
    },
    "history": {"count_after_content_update": 2, "template_applied": True},
    "security": {
        "acl_count": len(acl_rows),
        "groups": {
            xmlid: xmlid_id(xmlid)
            for xmlid in (
                "document_knowledge.group_document_user",
                "document_page.group_document_editor",
                "document_page.group_document_manager",
            )
        },
        "rules": rules,
    },
}
# Stdout is this disposable probe's machine-readable result ABI.
print(  # pylint: disable=print-used
    "OCA_DOCUMENT_PAGE_RUNTIME_CONTRACT=" + json.dumps(contract, sort_keys=True)
)
