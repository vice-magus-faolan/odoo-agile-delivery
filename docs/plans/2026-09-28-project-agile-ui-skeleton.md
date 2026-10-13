# Project Agile UI Skeleton Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan
> task-by-task.

**Goal:** Deliver an optional Odoo 19 `project_agile_ui` foundation that proves native
frontend test discovery while preserving a precise read-only Sprint planning contract.

**Architecture:** Keep the addon empty of business models and user-facing actions until
the read-only planning card implements the authorized snapshot endpoint. The addon
depends only on `project_scrum`; its sole runtime seam is the Odoo 19
`web.assets_unit_tests` bundle containing a Hoot fixture. ADR-010 fixes the later
action/service/payload/authority boundary so no client guesses backend rules.

**Tech Stack:** Odoo Community 19.0, Python/ORM, Odoo manifest assets, OWL/Hoot, Docker
Compose, unittest.

---

### Task 1: Write the failing structural contract

**Objective:** Make dependency, frontend-fixture, documentation, and verifier
requirements executable before adding the addon.

**Files:**

- Create: `tests/test_project_agile_ui_contract.py`

**Step 1: Write failing test**

```python
manifest = ast.literal_eval((module_root / "__manifest__.py").read_text())
self.assertEqual(manifest["depends"], ["project_scrum"])
self.assertEqual(manifest["assets"]["web.assets_unit_tests"], [
    "project_agile_ui/static/tests/**/*.test.js",
])
```

**Step 2: Run test to verify failure**

Run: `python3 -m unittest tests/test_project_agile_ui_contract.py -v` Expected: FAIL
because `addons/project_agile_ui/__manifest__.py` does not exist.

**Step 3: Keep the test focused**

Also assert the contract prohibits Git/Task-document behavior and that the canonical
verifier includes `project_agile_ui`.

**Step 4: Commit**

Keep this regression test in the same focused contract commit as the skeleton.

### Task 2: Record the accepted planning-board contract

**Objective:** Remove ambiguity about journeys, authority, data, accessibility, state
handling, and performance before an OWL component exists.

**Files:**

- Create: `docs/adrs/010-advanced-agile-ui-contract.md`

**Step 1: Write the service boundary**

```text
project.agile.planning.get_snapshot(project_id, backlog_cursor, limits)
```

The future service must authorize the project and company server-side, use current-user
ORM searches, return bounded data, and never `sudo()` or accept a caller-selected
model/method/company.

**Step 2: Specify first-page limits**

```text
sprints <= 20
backlog <= 50
logical ORM reads <= 6
```

**Step 3: Specify the additive client action**

Use `registry.category("actions")` only when a board exists. Do not patch ordinary
`project` Kanban, add global menus, or implement drag/drop in this read-only scope.

**Step 4: Document tests and fallback**

Name Hoot tests, later Python scope/query tests, a later native tour, and the existing
Project Backlog/Sprint list/form routes as standard fallbacks.

**Step 5: Commit**

Commit ADR-010 with the addon boundary after review of terminology and scope.

### Task 3: Add the smallest installable addon

**Objective:** Create an independently removable frontend shell with no business logic.

**Files:**

- Create: `addons/project_agile_ui/__init__.py`
- Create: `addons/project_agile_ui/__manifest__.py`
- Create: `addons/project_agile_ui/README.md`

**Step 1: Implement the manifest**

```python
{
    "depends": ["project_scrum"],
    "assets": {
        "web.assets_unit_tests": [
            "project_agile_ui/static/tests/**/*.test.js",
        ],
    },
    "installable": True,
}
```

**Step 2: Confirm non-goals in the module README**

State that the addon currently contains no models, controllers, menu/actions, backend
assets, Git, Task-document, or mutation behavior.

**Step 3: Add no data/security XML**

The empty addon has no persistent models or authority boundary to secure yet.

**Step 4: Commit**

Commit only the skeleton and its test asset; do not add a placeholder board.

### Task 4: Add a native Odoo frontend fixture

**Objective:** Prove asset discovery without inventing a parallel JavaScript harness.

**Files:**

- Create: `addons/project_agile_ui/static/tests/planning_board_contract.test.js`
- Create: `addons/project_agile_ui/tests/__init__.py`
- Create: `addons/project_agile_ui/tests/test_module_contract.py`

**Step 1: Write the Hoot fixture**

```javascript
/** @odoo-module **/
import {expect, test} from "@odoo/hoot";

test("project_agile_ui frontend fixture is included", () => {
  expect("project_agile_ui").toBe("project_agile_ui");
});
```

**Step 2: Write the installed-module contract test**

Assert the installed module is present and the manifest retains the exact
`project_scrum` dependency and `web.assets_unit_tests` declaration.

**Step 3: Run the Python structural suite**

Run: `python3 -m unittest tests/test_project_agile_ui_contract.py -v` Expected: PASS.

**Step 4: Commit**

Commit test discovery evidence with the static fixture.

### Task 5: Extend the canonical verifier and documentation

**Objective:** Make clean install, update, and reinstall exercise the optional addon.

**Files:**

- Modify: `scripts/verify:10-12`
- Modify: `README.md:Current scope and Verification sections`

**Step 1: Update module and test-tag lists**

```bash
MODULES=project_agile,project_scrum,project_scrum_analytics,project_agile_ui
TEST_TAGS=/project_agile,/project_scrum,/project_scrum_analytics,/project_agile_ui
```

**Step 2: Update README scope**

Describe Milestone 4 as delivered, and Milestone 5 as a bounded optional
skeleton/contract rather than a usable board.

**Step 3: Run focused and canonical verification**

Run:

```bash
python3 -m compileall -q addons
python3 -m unittest discover -s tests -p "test_*.py" -v
./scripts/verify
```

Expected: all structural checks pass; the canonical verifier clean-installs, updates,
and uninstalls/reinstalls all four modules using its disposable named databases. Run
Odoo's standard frontend test bundle against the installed `web.assets_unit_tests`
fixture; do not substitute Jest, npm, or a custom runner.

**Step 4: Review the diff**

Run:

```bash
git diff --check 71aea57f1edaafa4b1655cfc841a91b6cc24d04f..HEAD
git diff --stat 71aea57f1edaafa4b1655cfc841a91b6cc24d04f
```

**Step 5: Commit**

Commit the verified documentation/verifier change and record the full SHA for exact-SHA
review.

### Task 6: Implement the dependent read-only board (not this skeleton)

**Objective:** Use ADR-010 rather than re-deciding APIs during OWL work.

**Files:**

- Create later: `addons/project_agile_ui/models/project_agile_planning.py`
- Create later: `addons/project_agile_ui/static/src/planning_board/*`
- Create later: Python, Hoot, and tour tests adjacent to those files.

**Step 1: Write Python no-access/multi-company/cursor/query-budget tests.**

**Step 2: Run them RED against the absent service.**

**Step 3: Implement the bounded current-user snapshot service.**

**Step 4: Add read-only Hoot rendering/state/focus tests and a standard-view fallback
tour.**

**Step 5: Run focused Odoo and frontend suites GREEN, then commit.**

No drag/drop, writes, Git status, or Task-document control belongs in this dependent
read-only board task.
