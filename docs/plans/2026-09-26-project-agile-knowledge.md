# Milestone 4: Odoo 19 Knowledge bridge plan

Date: 2026-09-26
Status: blocked pending the licensed Odoo 19 Enterprise Knowledge fixture defined in [ADR-006](../adrs/006-knowledge-relationship-model.md).

## Outcome and boundaries

Deliver optional, ordinary-Odoo-view relationships to native Knowledge without making `knowledge` a dependency of `project_agile`, changing ordinary Project behavior, adding custom JavaScript/OWL, adding an OCA document dependency, or storing article content outside Knowledge.

The current Community image is a regression boundary only. `compose.yaml` uses `odoo:19.0`; configured paths `/usr/lib/python3/dist-packages/odoo/addons` and `/mnt/extra-addons` contain no `knowledge` addon. It cannot establish Enterprise API or security behavior.

## Fixture gate — do this before writing bridge code

1. Operator supplies a lawfully licensed Odoo 19 Enterprise fixture and an immutable image digest or permitted source revision. Keep credentials and license artifacts outside this repository.
2. Add `docs/research/odoo-19-knowledge-fixture.md` with: edition, immutable identifier, add-on path, manifest dependency, article model, title/body/parent/archive/template fields, create/write/unlink APIs, action/XML IDs, groups/ACLs/record rules, company behavior, archive/trash/permanent-delete behavior, and commands run.
3. Add `compose.knowledge-ee.yaml` only after the fixture is available. It must mount this repository's `addons/` read-only where practical, bind no public port, and use a disposable project-scoped database/volume namespace.
4. Run these current Community-boundary checks before and after every Enterprise bridge change:

   ```bash
   docker compose config --quiet
   docker compose run --rm --no-deps --user root --entrypoint python3 odoo -c 'from pathlib import Path; paths=(Path("/usr/lib/python3/dist-packages/odoo/addons"), Path("/mnt/extra-addons")); print([(str(path), path.is_dir(), (path / "knowledge").is_dir()) for path in paths])'
   ./scripts/verify
   ```

5. Do not infer a missing field or model. If the fixture cannot supply an exact supported API, retain the `needs_input` block in ADR-006 and stop.

## TDD implementation slices after the gate passes

### 1. Capture the exact contract (RED)

Add `tests/test_knowledge_fixture_contract.py` as a static guard that reads `docs/research/odoo-19-knowledge-fixture.md`. It must reject an incomplete fixture record and require the immutable Enterprise identifier, exact model/field/action names, documented ACL/record-rule results, company result, and all four lifecycle commands.

Add an Odoo `TransactionCase` in `addons/project_agile_knowledge/tests/test_knowledge_relations.py` using the verified exact APIs. Start with failing examples for:

- creating and clearing one Project root article;
- rejecting a root article already assigned to another Project;
- linking multiple Task articles and the same article to multiple Tasks;
- a non-admin caller attempting to link a non-readable article;
- a user who loses article access after a link exists;
- a cross-company attempt;
- archived, trashed, restored, and permanently removed article behavior.

Run the targeted test tag in the Enterprise fixture; preserve the initial RED output in the fixture record or task handoff.

### 2. Project/Task bridge (GREEN)

Create `addons/project_agile_knowledge/` with only the verified dependencies `project_agile` and `knowledge`. Implement models in:

- `addons/project_agile_knowledge/models/project_project.py`
- `addons/project_agile_knowledge/models/project_task.py`
- `addons/project_agile_knowledge/models/knowledge_access.py`

Implement the ADR-006 contract with fixture-confirmed field/model names only:

- Project root is optional one-to-one and is a relationship, never article ownership.
- Task articles are optional many-to-many and do not alter Knowledge parenting.
- Relation writes and open actions run as the caller; no broad `sudo()` or new permissive Knowledge ACL/rule.
- Cross-company behavior follows the recorded native Knowledge contract; otherwise reject it.
- Archive/trash preserve the relation but do not reveal inaccessible data. Permanent deletion follows the observed supported cleanup semantics with no dangling IDs.

Keep functions small: separate access resolution, cross-company compatibility, relation validation, and action construction. Update `addons/project_agile_knowledge/models/__init__.py` and `addons/project_agile_knowledge/__init__.py`.

Add native form/list/search views in `addons/project_agile_knowledge/views/` and stable XML IDs. Use only normal fields, buttons, and `ir.actions.act_window`; no assets directory and no OWL component. The UI must not render an inaccessible article's title, identifier, count, or open link.

Re-run the relation tests GREEN, then add multi-record writes and a realistic non-admin Project user case.

### 3. Explicit templates and user-driven automation

Only after fixture verification identifies a supported Knowledge template API, add source/data files under `addons/project_agile_knowledge/data/`:

- `knowledge_template_data.xml` for module-owned templates with stable XML IDs and `noupdate="1"`;
- `i18n/project_agile_knowledge.pot` and translations for localizable headings.

Use the exact documented template mechanism—not speculative `knowledge.article` XML records. Ship only ADR, Sprint Retrospective, Runbook, and Release Notes blueprints. Do not create a Project root or any article during record create/write, Sprint lifecycle, installation, or upgrade.

Add explicit user actions for create-from-template, link, open, and unlink/clear. Each must be reversible by clearing the relation and must leave article content, hierarchy, sharing, archive, and deletion under native Knowledge control.

Add tests for idempotent install/upgrade, no overwrite of a customized template, localization loading, and no adoption/deletion of customer-created templates.

### 4. Narrow Scrum bridge

Create `addons/project_scrum_knowledge/` only after the Project/Task bridge passes. Its exact dependencies are `project_scrum` and `project_agile_knowledge`; `project_scrum` itself remains Knowledge-free.

Implement `project.sprint` optional one-to-one retrospective relation in:

- `addons/project_scrum_knowledge/models/project_sprint.py`
- `addons/project_scrum_knowledge/tests/test_sprint_knowledge_relations.py`
- `addons/project_scrum_knowledge/views/project_sprint_views.xml`

Test that non-Scrum Agile users need not install this bridge, that a retrospective cannot cross project/company boundaries, that native article access applies after rights are revoked, and that closed-Sprint immutability is not weakened. The relation may be linked/cleared only through the explicit contract; it must not create a retrospective automatically when a Sprint is started or closed.

Do not add a Release field or model. The Release Notes blueprint remains unbound until ADR-005 has an accepted runtime release/version decision.

### 5. Install, upgrade, uninstall/reinstall, and Community regression

Extend `scripts/verify` only if its current Community-only module list must remain separate. Do not make Community verification attempt to install the Enterprise-only bridge.

In the licensed fixture, provide a separate checked-in, no-secret command path that executes all of the following against disposable project-scoped resources:

```bash
# Names and image/source reference are supplied by docs/research/odoo-19-knowledge-fixture.md.
docker compose -p odoo_agile_knowledge_ee -f compose.knowledge-ee.yaml up -d db
docker compose -p odoo_agile_knowledge_ee -f compose.knowledge-ee.yaml run --rm odoo odoo --config=/etc/odoo/odoo.conf --stop-after-init --without-demo=True --database odoo_agile_knowledge_install --init project_agile_knowledge,project_scrum_knowledge --test-enable
docker compose -p odoo_agile_knowledge_ee -f compose.knowledge-ee.yaml run --rm odoo odoo --config=/etc/odoo/odoo.conf --stop-after-init --without-demo=True --database odoo_agile_knowledge_upgrade --init project_agile_knowledge,project_scrum_knowledge
docker compose -p odoo_agile_knowledge_ee -f compose.knowledge-ee.yaml run --rm odoo odoo --config=/etc/odoo/odoo.conf --stop-after-init --without-demo=True --database odoo_agile_knowledge_upgrade --update project_agile_knowledge,project_scrum_knowledge --test-enable
docker compose -p odoo_agile_knowledge_ee -f compose.knowledge-ee.yaml run --rm odoo odoo shell --config=/etc/odoo/odoo.conf --database odoo_agile_knowledge_reinstall --no-http
./scripts/verify
```

The final shell command must be replaced with the exact fixture-verified uninstall/reinstall procedure before it is accepted; no database or volume deletion command belongs in this plan without an explicit disposable-resource guard.

## Completion evidence for implementation

An implementation handoff must distinguish:

- verified Enterprise behavior: exact fixture identifier, models/fields/actions, test command results, ACL/record-rule and lifecycle cases;
- Community regression coverage: `./scripts/verify` result and confirmation that core modules still have no `knowledge` dependency;
- unverified assumptions: none are acceptable for model, field, ACL, archive, unlink, or action APIs;
- residual operator input: only an unavailable/revoked licensed fixture or a new Odoo 19 Enterprise build requiring the fixture gate to be rerun.
