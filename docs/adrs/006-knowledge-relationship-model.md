# ADR-006: OCA Document Page Relationship Model

## Status

Accepted — supersedes the blocked Enterprise Knowledge fixture direction. Milestone 4 uses OCA Document Page on the pinned OCA 19.0 source described below. Odoo Enterprise Knowledge remains a deferred alternative backend; it is not API-compatible with OCA Document Page and must not be treated as interchangeable.

## Context

The Community `odoo:19.0` environment has no `knowledge` addon. The prior ADR correctly refused to guess proprietary Enterprise APIs. Jimmy authorized a Community/OCA rescope instead of a proprietary fixture.

OCA `knowledge` 19.0 commit `e4a12c0c99866a5850840941d6f7ae3b3b27280d` contains the merged, installable AGPL-3 modules:

- `document_knowledge` `19.0.1.0.1` (`base`);
- `document_page` `19.0.1.0.2` (`mail`, `document_knowledge`, `html_editor`);
- `document_page_project` `19.0.1.0.0` (`project`, `document_page`).

The exact fixture, source inspection, licensing posture, runtime probes, and lifecycle commands are recorded in [the OCA Document Page fixture record](../research/odoo-19-oca-document-page-fixture.md).

## Decision

Use the three pinned OCA modules as Milestone 4's documentation backend. OCA remains authoritative for page content, rich-text editing, history, category hierarchy, templates, page access groups, company rule, archive state, deletion behavior, and the existing Project-to-page relationship.

This repository must not copy, vendor, fork, or reimplement those modules. It must not build a parallel editor, wiki, page-body store, revision log, hierarchy, generic Project connector, or task connector on this milestone-contract card.

### Boundary and ownership

- `project_agile`, `project_scrum`, and `project_scrum_analytics` remain Community-only and remain free of `document_*` dependencies.
- `document_page_project` is the selected, existing OCA Project relationship. It owns `document.page.project_id`, `project.project.document_page_ids`, and its standard Project Wiki action.
- A later task-specific integration is a separate decision and implementation card. It must use a merged, authoritative OCA 19.0 contract or an approved narrow upstream-compatible extension; it must not copy the open PR's code.
- Sprint or Release relations remain deferred. No Scrum bridge, Release model, or release-notes relationship is authorized here.

### Security, company, archive, and deletion contract

The selected modules provide a global company record rule for `document.page` and `document.page.history`: a page is visible only when `company_id` is false or in the caller's allowed `company_ids`. The fixture records the editor/manager ACLs and must be rerun before any new privileged operation is designed.

Future integrations must execute as the caller and preserve native record rules. They must not use `sudo()` to decide access, expose inaccessible page metadata, forge a caller-selected company, or create permissive page ACLs/rules.

`document.page.active` is the selected archive state. Its `unlink()` is native OCA behavior: it removes the page and attached menu, while `document.page.history.page_id` uses cascade deletion. The selected Project relationship is a direct `Many2one`/`One2many`, not a fabricated ownership or tombstone layer. A later relation must prove its cleanup behavior against this exact fixture.

### Templates and hierarchy

Pages and categories are `document.page` records. A page's `parent_id` accepts category pages, and the native constraint rejects recursive categories. Category `template` is the supported OCA template mechanism used by the parent onchange for a new page; content versions are native `document.page.history` records. Later work may expose this native mechanism only after applying its normal access and upgrade semantics. It must not seed speculative proprietary `knowledge.article` records.

### OCA AGPL consequence

The selected modules declare `AGPL-3`. This task records and verifies a disposable local fixture only; it neither publishes nor deploys an OCA-based service. Before any network-accessible production use, maintainers must perform a license and distribution review appropriate to the actual combined deployment and provide corresponding-source handling where applicable. This is a release gate, not a reason to obscure or relabel the dependency.

## PR #641 gate

At execution on 2026-09-27, OCA PR #641 (`[19.0][MIG] document_page_project_task`) is open, unmerged, and has head `b790965e66a008da4421a8763c489037bbb8a43a`. It is not a production dependency and is not copied or vendored here.

A later task connector may evaluate that head only in disposable resources. It may depend on it only after OCA merges it into authoritative `19.0`, the merged branch is reacquired at a new immutable commit, the fixture is rerun, and the task's exact APIs/security/lifecycle contract is recorded. If it remains unmerged, the connector remains blocked rather than silently substituting PR code.

## Consequences

`./scripts/verify` remains the canonical Community regression gate. The bounded OCA lifecycle is intentionally separate at `./scripts/verify-oca-document-page`; it uses no host port, no persistent volume, a project-scoped Compose name, a pinned Odoo image digest, and a pinned public source commit. It is required evidence for future OCA-document work but does not activate a runtime dependency in shipped Community modules.

## Alternatives

- Keep Enterprise Knowledge as the active Milestone 4 target: rejected because no licensed Enterprise fixture is available and its APIs must not be guessed.
- Build a custom wiki or document store: rejected because it duplicates OCA Document Page.
- Treat Enterprise Knowledge and OCA Document Page as compatible backends: rejected; their APIs and behavior have not been established as compatible.
- Copy PR #641 or make it a hidden dependency: rejected because it is open and unmerged.

## Evidence

- [OCA Document Page fixture record](../research/odoo-19-oca-document-page-fixture.md)
- [Mission brief: Knowledge is first-class](../mission-brief.md#rule-8--knowledge-is-first-class)
- [Mission brief: preferred contribution over duplication](../mission-brief.md#rule-12--prefer-contribution-over-duplication)
- [OCA knowledge 19.0 tree at the selected commit](https://github.com/OCA/knowledge/tree/e4a12c0c99866a5850840941d6f7ae3b3b27280d)
