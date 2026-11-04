# Contributor checks

This private suite targets Odoo 19 Community. Its tooling is derived from the OCA addon
repository template at `0c2edf1fd55ce731ab786a6ae39d172590c7c573`, rendered explicitly
for `19.0`. This is OCA-aligned tooling, not a claim of full OCA conformity. Existing
addon licenses and authorship remain unchanged.

Use Python 3.12 and install the pinned entrypoint in an isolated environment:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lint.txt
pre-commit validate-config
pre-commit run --all-files --show-diff-on-failure
./scripts/verify
```

CI retains the required `lint` and `modules` jobs. Both must pass on the current PR
revision before merge. PR verification tests GitHub's merge of the PR into the current
base branch. It compares that merge commit against `PR_BASE` to select standalone unit
suites for changed addons and their transitive manifest and Python import dependents.
Prerequisites are installed independently of test selection. The combined installation
always runs every supported addon suite: addons can override the same ORM model without
depending on one another. It also selects the six native Project sharing UI cases and
the timesheet sharing case, so portal regressions fail normal verification and CI. The
combined registry installs optional native Sales to exercise salesperson Project
creation from plain templates. The independent Solution installation and lifecycle
checks remain Sales-free; Sales is not a production dependency of Solution.
Default-branch pushes and `./scripts/verify` without arguments also run every standalone
suite; ordinary topic pushes do not duplicate PR runs.

Use `./scripts/verify --pr BASE_SHA MERGE_SHA` with the merge commit checked out to
reproduce PR selection, or `./scripts/verify --addons project_scrum_analytics` to focus
standalone tests on those addons and affected dependents. Both commands keep the full
combined suite. `python3 scripts/ci_selection.py --pr BASE_SHA MERGE_SHA` prints the
standalone selection without starting Docker. Selector regression tests run with
`python3 -m unittest discover -s scripts/tests -v` and through the canonical verifier.
Commit source changes before using selection, which reads the checked-out Git revision.

Shared tooling, unknown paths, manifest changes, deletions, renames and failed
comparison analysis run every suite. An invalid supported dependency graph stops
verification with an error. A docs-only PR runs the selector tests, skips Odoo
verification and passes the job. The Community verifier excludes Document Page bridges
while their optional backend is unavailable. Native test failures fail the job. All
standalone installations, populated upgrades, external concurrency probes and
uninstall/reinstall checks run in both full and focused modes.

Use local checks for focused development feedback and failure diagnosis. Until issue #7,
`prefer-env-translation` (`W8161`) remains advisory in the optional pylint hook, with
all other mandatory checks blocking. Issue #7 must assess language fallbacks and
multilingual compatibility before restoring mandatory gating.

External process/lifecycle checks, including the planning races run by
`./scripts/verify`, are documented in [the probe guide](../scripts/probes/README.md).
