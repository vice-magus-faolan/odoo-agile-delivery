# ADR-006: Knowledge Relationship Model

## Status

Blocked — architecture contract accepted; implementation is not authorized until the exact licensed Odoo 19 Knowledge fixture gate below passes.

## Context

The product needs architecture documents, ADRs, runbooks, retrospectives, Definition of Done, and release notes without recreating a wiki. Project, task, and Sprint need navigable links to the relevant Knowledge articles.

The repository's current verification environment is Community `odoo:19.0`. Its configured add-on paths are `/usr/lib/python3/dist-packages/odoo/addons` and `/mnt/extra-addons`; neither contains `knowledge`. The lane contains no licensed Odoo 19 Enterprise Knowledge source, image, or disposable verification fixture. Odoo's 19.0 user documentation establishes the intended product behavior—articles have parent/child structure, inherit parent access rights, support templates, and may be archived or moved to trash—but it does not establish supported developer model, field, action, ACL, or unlink APIs.[1]

## Decision

Knowledge remains the authoritative article store, editor, hierarchy, lifecycle, permission system, and navigation. The Agile integration may store only relationships and expose ordinary Odoo form/list actions; it must not introduce article body/content fields, an editor, a wiki hierarchy, custom JavaScript, or an OCA document dependency.

This ADR fixes the target relationship and lifecycle contract, but deliberately does not guess `knowledge` model names, fields, XML IDs, methods, record rules, or create contexts. A later implementation may begin only after the fixture gate records those exact Odoo 19 Enterprise APIs and executable evidence.

### Add-on boundary

- `project_agile` remains independent of Knowledge and Scrum.
- `project_agile_knowledge` is optional and may depend on `project_agile` and the exact licensed `knowledge` module only. It owns Project and Task relationships plus their ordinary views/actions.
- Sprint support belongs in a narrow optional `project_scrum_knowledge` bridge, depending on `project_scrum` and `project_agile_knowledge`. Installing Scrum never becomes a prerequisite for ordinary Project/Task Knowledge links.
- No Release relation is implemented. ADR-005 still has no accepted runtime release/version model; a Release Notes template may be offered, but no relation is authorized.

### Cardinality and ownership

- A Project has zero or one Knowledge root article; a root article may be the root of zero or one Project. The Project owns only the relationship, never the article.
- A Task has zero or more related articles; an article may relate to zero or more Tasks. This association neither reparents nor otherwise changes article hierarchy.
- A Sprint has zero or one retrospective article; a retrospective article may relate to zero or one Sprint. This is implemented only by the optional Scrum bridge.
- Knowledge remains the sole owner of every article's content, hierarchy, sharing, archive, trash, restoration, and permanent deletion behavior. Relation writes must never change those article properties.

### Access, company, archive, and deletion contract

- The integration creates no broad Knowledge ACL, record rule, or decision-making `sudo()` path. It relies on the exact native Knowledge authorization path established by the fixture.
- A caller must have the normal Odoo access required to modify the Agile record and native read access to every linked article before a relation is created or changed. Candidate search, smart-button counts, names, and action domains execute as the caller, not a privileged proxy.
- A caller who cannot currently read a formerly linked article must receive neither its title, identifier, count contribution, nor an open action. Access denial and absence must be indistinguishable to that caller.
- Cross-company links are rejected unless the approved fixture proves that the exact Knowledge article is explicitly shareable across those companies and the caller passes its native record rules in both company contexts. A missing or company-neutral field is not permission to invent a company rule or bypass access controls.
- Archiving or trashing an article never archives or deletes the Project, Task, or Sprint and never auto-unlinks it. It becomes unavailable through normal actions until restored and readable again.
- The integration never overrides Knowledge deletion. When Knowledge permanently removes an article, the relation follows the exact supported relational cleanup semantics recorded in the fixture; it must not leave a dangling identifier, prevent native deletion, or fabricate a tombstone. Tests must prove the selected behavior for Project, Task, and Sprint relations.

### Templates and automation

- Template source is module-owned only after the fixture identifies Knowledge's supported template API and data model. No XML or Python may seed speculative `knowledge.article` records.
- If supported, template records use stable namespaced XML IDs, `noupdate="1"`, translation files for localizable text, and an upgrade policy that never overwrites a user-customized template. Existing customer-created templates are never adopted, renamed, or deleted.
- Project roots, Task articles, Sprint retrospectives, and any template-derived articles are created or linked only through an explicit user action after native access checks. There is no automatic root creation on Project create, no automatic article on Task create/state change, no automatic retrospective on Sprint lifecycle, and no hidden reparenting.
- Allowed automation is limited to explicit, reversible relation changes: create/link, open, and unlink/clear. Each action affects only the selected relationship and is undoable by clearing that relationship; article content and lifecycle remain native Knowledge operations.

## Verification gate

Before implementation, add an immutable fixture record at `docs/research/odoo-19-knowledge-fixture.md` and attach or cite the licensed environment evidence. It must state:

1. Odoo edition, exact 19.0 build/image digest or permitted source revision, and how the license authorizes local inspection and test use;
2. the add-on path containing `knowledge`, module manifest dependency name, article model, field names/types for title/body/parent/archive/template, relation-table constraints, and applicable action/XML IDs;
3. native create/read/write/unlink API contracts, default values, parent/child behavior, archive/trash/permanent-delete behavior, and upgrade behavior;
4. Knowledge groups, ACLs, record rules, company semantics, and direct evidence for a user losing article access after linking;
5. commands for a disposable clean install, upgrade, uninstall/reinstall, and ordinary Community regression run.

No bridge code, manifest dependency, XML data, migration, or relationship UI is allowed until that record is complete and its commands pass.

## `needs_input`

Blocking operator input is required: provide a lawfully licensed Odoo 19 Enterprise Knowledge source or disposable test environment accessible to this lane, with an immutable version identifier and a non-secret command or documented procedure for a clean install, upgrade, and uninstall/reinstall run. The current Community image and public user documentation are insufficient to infer private model/action APIs. Do not provide credentials in this repository or Kanban comments.

## Alternatives

- Build a custom wiki: rejected because it duplicates Knowledge.
- Store article content on Project, Task, or Sprint fields: rejected because article lifecycle, navigation, and reuse are lost.
- Make Knowledge a hard dependency of `project_agile`: rejected because Agile core must remain independently installable.
- Silently substitute OCA `document_page` or another document add-on: rejected because that changes the product and verification contract.
- Guess Enterprise internals from another Odoo version or community examples: rejected because it is upgrade- and security-unsafe.

## Consequences

Milestone 4 implementation is deliberately paused rather than substituted with a mock or a parallel wiki. Community verification remains meaningful only for regressions: `project_agile`, `project_scrum`, and `project_scrum_analytics` must continue to install and operate without Knowledge. Enterprise fixture verification is separately required for every Knowledge bridge change.

## Evidence

- [Mission brief: Knowledge is first-class](../mission-brief.md#rule-8--knowledge-is-first-class)
- [Mission brief: intended Knowledge relationships](../mission-brief.md#knowledge-relationships)
- [ADR-005: Release / Version Model](005-release-version-model.md)
- [Odoo 19 Knowledge user documentation][1]

## Sources

[1] https://www.odoo.com/documentation/19.0/applications/productivity/knowledge.html
