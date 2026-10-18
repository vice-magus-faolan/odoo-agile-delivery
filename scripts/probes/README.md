# External verification probes

Use only disposable databases; these probes commit synthetic data.

- `solution_concurrency_probe.py`: standalone dependency isolation and solution races.
- `baseline_concurrency.py`: revision allocation, approval and narrative submission
  races.
- `requirement_concurrency.py`: stable-key/content allocation and frozen-baseline races.
- `task_concurrency.py`: duplicate-safe confirm/link and stale-source rejection races.
- `solution_scrum_probe.py`: relink, Sprint transition and completion races.
- `solution_lifecycle_probe.py`: populated upgrade and uninstall/reinstall lifecycles.
- `git_policy_concurrency_{probe,worker}.py`: cron claims, budget and crash recovery
  races.
- `github_association_concurrency_{probe,worker}.py`: duplicate normalization and audit
  continuity.
- `planning_concurrency_{setup,worker,assert}.py`: assign/return and reorder races.

Run from the repository root with Docker Compose v2 available:

- `./scripts/verify` runs the core probes after ordinary addon installation.
- `python3 scripts/probes/test_planning_concurrency.py` runs standalone planning races.

Both commands own and remove their disposable Compose resources.
