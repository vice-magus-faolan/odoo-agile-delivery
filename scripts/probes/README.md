# External verification probes

Use only disposable databases; these probes commit synthetic data.

- `solution_concurrency_probe.py`: standalone dependency isolation and solution races.
- `baseline_concurrency.py`: revision allocation, approval and narrative submission
  races.
- `requirement_concurrency.py`: stable-key/content allocation and frozen-baseline races.
- `task_concurrency.py`: duplicate-safe confirm/link and stale-source rejection races.
- `solution_scrum_probe.py`: relink, Sprint transition and completion races.
- `item_type_lifecycle_probe.py`: upgrades pointed Stories in an active Sprint and
  checks their points, Sprint events, planning totals, seeds and quick defaults.
- `solution_lifecycle_probe.py`: populated upgrade and uninstall/reinstall lifecycles.
- `git_policy_concurrency_{probe,worker}.py`: cron claims, budget and crash recovery
  races.
- `github_association_concurrency_{probe,worker}.py`: duplicate normalization and audit
  continuity.
- `planning_concurrency_{probe,worker}.py`: assign/return, reorder and team/Sprint
  ownership versus Task placement races with established transaction snapshots.

Run from the repository root with Docker Compose v2 available:

`./scripts/verify` runs the core probes, including planning races, after ordinary addon
installation in its disposable database.

The item-type upgrade needs the prior Git revision selected in `scripts/verify`. The
verifier extracts its addons into a temporary directory and updates the same populated
disposable database with the current checkout.
