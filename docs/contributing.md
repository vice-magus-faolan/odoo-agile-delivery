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
python -m unittest discover -s tests -p 'test_*.py' -v
./scripts/verify
```

The configuration pins Ruff, pylint-odoo, OCA module/translation and README checks,
Prettier, ESLint and standard hygiene hooks. Node 22.9.0 is installed by pre-commit for
the JavaScript hooks. No changed-file-only replacement or addon-wide exclusion is used.
README generation runs when source fragments exist; it does not invent fragments for
addons that have none. Protected `AGENTS.md` is excluded only from Prettier, not other
hygiene checks.

## Translation preference exception

Until issue #7, `prefer-env-translation` (`W8161`) is the sole rule omitted from the
template's mandatory pylint list. It remains enabled in `.pylintrc`, executes in the
standard optional pylint hook, and its warnings are reported, not fixed. All other
mandatory rules remain blocking. This explicit advisory choice preserves existing `_()`
language resolution: conversion to `env._()` is not mechanically equivalent for plain
helpers and sanitized contexts. Issue #7 must assess those language fallbacks and
exercise multilingual compatibility before restoring mandatory gating. Do not convert
translations, merge caller context or add an adapter merely to silence lint.

Other exceptions must be source-specific, name the rule and explain the invariant:
immutable records reject deletion/mutation, authority boundaries replace rather than
merge untrusted context, and disposable probes receive Odoo-shell globals and emit
stdout for their consumers. They are not a blanket legacy baseline or permission to
weaken security tests. Source hash pins may change only after reviewing the referenced
diff; retain exact-byte matching and the existing compatibility assertions.

## Pull request checks

`.github/workflows/ci.yml` runs the same all-files lint and `./scripts/verify` on
ordinary hosted runners for pull requests to `main` and pushes to `main`. It has
read-only repository permissions, no live credentials or deployment. The module job
retains the native log, including discovery, lifecycle and teardown results. The
canonical verifier owns a fresh Compose project and removes its disposable containers,
volumes and networks on success and failure. Do not substitute the separate OCA Document
Page fixture for this canonical gate or add its current missing-teardown path to CI.

Local source review, actual exact-head hosted results, human PR approval and merge
authorization are distinct. Main branch provider protection is explicitly out of scope
for issue #1 under the current private repository plan; local PR-only policy is not
provider protection. Do not change plans or repository settings to satisfy this issue.
