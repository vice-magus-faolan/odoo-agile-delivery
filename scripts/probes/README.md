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

Use a full Git clone with the prior revisions listed in `PRIOR_SOURCE_COMMITS` in
`scripts/verify` available locally; a shallow clone is insufficient. Run from the
repository root with Docker Compose v2 available:

```bash
./scripts/verify
```

The verifier runs the core probes, including planning races, after ordinary addon
installation in its disposable database.

The item-type upgrades need the prior revisions listed in `PRIOR_SOURCE_COMMITS` in
`scripts/verify`. The verifier extracts each prior revision into a temporary directory
and updates the same populated disposable database with the current checkout. The
planning-race probe runs only through this verifier, which creates its required
database; it has no standalone invocation.
