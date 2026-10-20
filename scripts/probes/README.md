# External verification probes

Use only disposable databases; these probes commit synthetic data.

- `solution_concurrency_probe.py`: standalone dependency isolation and solution races.
- `baseline_concurrency.py`: revision allocation, approval and narrative submission
  races.
- `requirement_concurrency.py`: stable-key/content allocation and frozen-baseline races.
- `task_concurrency.py`: duplicate-safe confirm/link and stale-source rejection races.
- `solution_scrum_probe.py`: relink, Sprint transition and completion races.
- `item_type_lifecycle_probe.py`: prior-source active-Sprint upgrade with 3/5/8 Story
  points, preserved task audit/history, first point-change events, planning totals, BA
  eligibility and quick-task defaults.
- `solution_lifecycle_probe.py`: populated upgrade and uninstall/reinstall lifecycles.
- `git_policy_concurrency_{probe,worker}.py`: cron claims, budget and crash recovery
  races.
- `github_association_concurrency_{probe,worker}.py`: duplicate normalization and audit
  continuity.
- `planning_concurrency_{probe,worker}.py`: assign/return and reorder races.

Run from the repository root with Docker Compose v2 available:

`./scripts/verify` runs the core probes, including planning races, after ordinary addon
installation in its disposable database.

The item-type upgrade uses the retained Git history at
`898f0e105aed33aaeb6815fdc56edb10892f6165`. Use a full checkout (not a shallow clone).
The verifier creates and removes one temporary detached prior-source worktree and
updates the same populated disposable database with the current checkout.
