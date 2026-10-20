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
revision before merge. PR module verification compares the merge base of the actual base
and head commits, testing changed addons and their transitive manifest and Python
extension dependents. Prerequisites are installed independently of test selection.
Default-branch pushes and `./scripts/verify` without arguments run the complete
supported suite; ordinary topic pushes do not duplicate PR runs.

Use `./scripts/verify --pr BASE_SHA HEAD_SHA` to reproduce PR selection on the committed
head, or `./scripts/verify --addons project_scrum_analytics` for focused native tests
including affected dependents. `python3 scripts/ci_selection.py --pr BASE_SHA HEAD_SHA`
prints the decision without starting Docker. Selector regression tests run with
`python3 -m unittest discover -s scripts/tests -v` and through the canonical verifier.
Commit source changes before using selection, which reads the checked-out Git revision.

Shared tooling, unknown paths, manifest or availability changes, deletions, renames and
failed comparison analysis conservatively run full assurance. An invalid supported
dependency graph fails visibly. Documentation-only changes report an explicit no-impact
result while completing the required job. The Community verifier excludes Document Page
bridges while their optional backend is unavailable. Native test failures remain
blocking. Standalone installations, populated upgrades, external concurrency probes and
uninstall/reinstall checks remain enabled in both full and focused modes.

Use local checks for focused development feedback and failure diagnosis. Until issue #7,
`prefer-env-translation` (`W8161`) remains advisory in the optional pylint hook, with
all other mandatory checks blocking. Issue #7 must assess language fallbacks and
multilingual compatibility before restoring mandatory gating.

External process/lifecycle checks, including the planning races run by
`./scripts/verify`, are documented in [the probe guide](../scripts/probes/README.md).
