# Milestone 4: OCA Document Page integration plan

Date: 2026-09-27
Status: contract established; no Agile, Task, Scrum, or UI bridge is implemented by this milestone-contract card.

## Outcome and boundaries

Milestone 4 uses OCA Document Page, not Enterprise Knowledge, as the Community documentation backend. The authoritative source is OCA `knowledge` branch `19.0` at immutable commit `e4a12c0c99866a5850840941d6f7ae3b3b27280d`. Its selected AGPL-3 modules are `document_knowledge` `19.0.1.0.1`, `document_page` `19.0.1.0.2`, and `document_page_project` `19.0.1.0.0`.

Enterprise Knowledge is a deferred alternative backend, not API-compatible with OCA Document Page. Do not reuse this plan's OCA model, field, action, ACL, record-rule, hierarchy, history, editor, or template facts to implement Enterprise Knowledge. Do not introduce a custom wiki, editor, page content store, revision model, generic Project connector, Task connector, Scrum connector, or OWL UI.

The current Community modules continue to be verified solely by `./scripts/verify`. The OCA fixture is an explicit separate surface: `./scripts/verify-oca-document-page`.

## Established fixture contract

The no-secret fixture is documented in [the OCA Document Page fixture record](../research/odoo-19-oca-document-page-fixture.md) and uses:

- `odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c`;
- `postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24`;
- a Docker build that fetches exactly the OCA commit and asserts the resolved `HEAD`;
- an isolated Compose project, no published port, a PostgreSQL `tmpfs`, and only the three fixture-named disposable databases.

Run the following before any new OCA-document implementation and retain its output with that implementation's handoff:

```bash
./scripts/verify-oca-document-page
./scripts/verify
```

The first command proves clean install, targeted upgrade, and dependency-safe uninstall/reinstall of `document_knowledge`, `document_page`, and `document_page_project`, then executes a runtime contract probe. The second preserves the existing Community boundary. Neither command supplies credentials or alters a production service.

## Exact selected behavior

The source and runtime probe establish the current OCA contract:

- `document.page` owns title (`name`), `content`, `active`, `parent_id`/`child_ids`, category `template`, `history_head`/`history_ids`, `company_id`, and `project_id` through `document_page_project`.
- `document.page.history` stores version content and cascades on page deletion. The page's computed/inverse content path creates history records.
- Only category pages are valid `parent_id` targets; native validation rejects recursive categories.
- `active` is the archive flag. Native unlink removes the page and menu; do not override it or add a tombstone.
- Access uses `document_knowledge.group_document_user`, `document_page.group_document_editor`, and `document_page.group_document_manager` plus a global multi-company rule for pages and history.
- `document_page_project` already provides the Project Wiki relation and `document_page_project.action_document_page_projects`. Do not duplicate it.
- The supported template mechanism is the category `template` field applied by the native page-parent onchange; it is not a reason to create speculative proprietary records.

## Later work sequence

### 1. Reconfirm the evidence before each dependent card

Recheck the OCA 19.0 branch ref, source commit, image digests, and PR #641 status. Run both verifier commands. If a source or digest changes, record a new immutable fixture result rather than updating a mutable tag in place.

### 2. Decide a narrow Task relationship only after its upstream gate

OCA PR #641, `[19.0][MIG] document_page_project_task`, was rechecked on 2026-09-27 as open and unmerged at `b790965e66a008da4421a8763c489037bbb8a43a`. That head can be evaluated only in a disposable fixture. It is not vendored, copied, or used as a production dependency.

A task-connector card may proceed only when one of these is true:

1. OCA has merged the capability into authoritative `19.0`, the resulting commit is pinned, and this fixture is rerun against it; or
2. an approved upstream-compatible extension is separately designed, reviewed, and verified without copying the PR.

Until then, the connector stays blocked. Do not repurpose `document_page_project` as an implicit Task API.

### 3. Preserve native security and lifecycle behavior

A future integration must use caller-visible recordsets and native ACL/rule enforcement. It must reject caller-forged company context and cannot use decision-making `sudo()`. It must not reveal a page title, identifier, count, or open action when the native page is inaccessible.

Any new relation must define its own cleanup behavior and prove it for archive, delete, reinstall, and multi-company cases. It cannot alter page content, hierarchy, template, page history, editor groups, or native Project Wiki behavior.

### 4. Treat AGPL as a delivery gate

Before public or production deployment, explicitly review the AGPL-3 obligations for the actual combined deployment, including corresponding-source availability where applicable. This is intentionally deferred from the disposable fixture; no deployment is authorized by this plan.

## Acceptance evidence for later implementation

A dependent implementation handoff must include:

- the exact OCA commit and Odoo/PostgreSQL image digests it used;
- successful clean-install, upgrade, uninstall/reinstall, runtime-probe, and Community verifier output;
- the exact model/field/action/ACL/rule behavior used, with no Enterprise compatibility claim;
- non-admin and multi-company negative tests for every new public relation or action;
- explicit archive/delete/recovery behavior and residual AGPL release gate;
- the PR #641 merge-gate outcome if the work concerns Task pages.
