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

Local checks provide focused feedback and failure diagnosis; a duplicate full local
verifier run is not required before handoff. Independently review the committed source,
then publish an ordinary topic-branch PR to trigger the required hosted lint and
module-verification jobs. Those jobs must pass on the exact PR head before delivery
acceptance.

Until issue #7, `prefer-env-translation` (`W8161`) remains advisory in the optional
pylint hook, with all other mandatory checks blocking. Issue #7 must assess language
fallbacks and multilingual compatibility before restoring mandatory gating.

External process/lifecycle checks, including the planning races run by
`./scripts/verify`, are documented in [the probe guide](../scripts/probes/README.md).
