# ADR-006: OCA Document Page relationships

## Status

Accepted. Optional `project_agile_document_page` and `project_scrum_document_page`
bridges use OCA Document Page on the pinned Community-compatible source below.
Enterprise Knowledge remains an optional alternative requiring its own API and runtime
verification; it is not interchangeable. Task-page integration remains separately gated.

## Context and dependency decision

Community Odoo has no Enterprise `knowledge` addon. Rather than guess proprietary APIs
or build a wiki, use OCA `knowledge` 19.0 at
[`e4a12c0c99866a5850840941d6f7ae3b3b27280d`](https://github.com/OCA/knowledge/tree/e4a12c0c99866a5850840941d6f7ae3b3b27280d):

- `document_knowledge` 19.0.1.0.1, depending on `base`;
- `document_page` 19.0.1.0.2, depending on `mail`, `document_knowledge`, `html_editor`;
- `document_page_project` 19.0.1.0.0, depending on `project`, `document_page`.

All three declare AGPL-3. The two local bridges also retain AGPL-3. Core Agile, Scrum
and analytics acquire no Document Page dependency. The
[compatibility guide](../dependency-compatibility.md#selected-document-page-runtime)
records image digests, dependency behavior and the separate fixture command.

OCA owns content, editor, page history, category hierarchy, templates, groups, company
rules, archive/delete behavior and the existing Project-page relation. Do not copy,
fork, vendor or replace those generic features. The local bridges supply narrow
Project-root and Sprint-retrospective relationships, not a second page-body store or
generic connector. Release-note relationships remain deferred with release management in
ADR-005.

`document_page_project` owns `document.page.project_id`, Project page relations and
counts, and `document_page_project.action_document_page_projects`. A Project root or
Sprint retrospective must remain a native permitted page, not a new content engine.
`knowledge.article` names are not OCA APIs.

## Access, templates and lifecycle

Pages and history have a global company rule: company-less records or records in the
caller's allowed companies. Native document users read, editors create/edit without page
unlink, and managers may unlink. Bridges additionally enforce current
Project/page/company access. They must not disclose inaccessible page titles, IDs,
counts or open actions through sudo or caller-forged company context.

`parent_id` accepts category pages and rejects recursive hierarchy. Category `template`
is the native parent-onchange source for an empty new page. Computed/ inverse content
creates `document.page.history`; no proprietary article templates or custom history
records are inferred.

`active=False` archives. Native page unlink removes its attached menu and cascades
history through `page_id`; archive rather than delete when history is needed. Local
relationships must preserve native security and define their own cleanup without
overriding page lifecycle or inventing tombstones.

## PR #641 gate

OCA Knowledge PR 641, `[19.0][MIG] document_page_project_task`, was open/unmerged on
2026-09-27 and again in the 2026-10-05 survey, head
`b790965e66a008da4421a8763c489037bbb8a43a`. This records the examined selection, not a
claim about today's upstream state. Its code is not copied, vendored or a production
dependency here.

A Task connector may use that capability only after authoritative 19.0 merge, a new
immutable source selection and rerun of the fixture with exact Task API, security and
lifecycle checks. An alternative narrow upstream-compatible extension requires a
separate reviewed decision. Until then, do not treat the Project relationship as an
implicit Task API.

## Verification and licensing consequences

`./scripts/verify` remains the Community check. The separate
`./scripts/verify-oca-document-page` exercises the selected three OCA modules and two
bridges with Agile/Scrum, using pinned source/images, disposable databases, PostgreSQL
tmpfs, no published ports and scoped teardown. It covers install, targeted update,
dependency-safe uninstall/reinstall and native runtime behavior; it does not establish
Enterprise or Odoo.sh staging compatibility.

Before public or production use, review the actual combined deployment's AGPL and
corresponding-source obligations. Disposable verification is not a production license or
deployment grant.

Rejected alternatives: guess Enterprise APIs; build a competing wiki/editor; treat OCA
and Enterprise backends as API-compatible; or silently adopt unmerged PR code. The
selected optional relationships preserve native ownership while keeping Community core
independently installable.
