# External verification probes

Ordinary model behavior lives in owning addon `tests/` packages and runs through native
Odoo discovery. These probes remain external because they need committed fixtures,
independent Odoo processes/cursors, or registry rebuilds. They are not another test
suite or a deployment tool. Never run them on a customer database.

## Canonical core entrypoint

Run `./scripts/verify` from the repository root. It installs the declared addons
normally before piping these probes to `odoo shell`, using a fresh Compose project and
synthetic `odoo_agile_verify_install` database. It mounts this directory read-only at
`/mnt/policy-tests` for parents and nested workers. Public source must be readable by
the non-root Odoo user. No provider credentials or live GitHub calls are needed.

- `solution_concurrency_probe.py`: standalone solution dependency isolation, public
  probe readability and baseline, requirement/context and Task-intent races.
  `baseline_concurrency.py` proves revision allocation, approval and narrative
  submission with old snapshots; `requirement_concurrency.py` proves stable-key and
  content allocation without rewriting frozen baselines; `task_concurrency.py` proves
  duplicate-safe confirm/link and stale-source rejection. They launch their own bounded
  workers and are also imported by the bridge/lifecycle probes.
- `solution_scrum_probe.py`: isolated optional bridge dependencies; relink versus
  start/add/close with committed and contended orderings; frozen context and
  Sprint-close versus completion/removal/creation/target changes. Native sequential
  tests cannot establish these independent-transaction outcomes.
- `solution_lifecycle_probe.py`: the verifier supplies its closed `PHASE` literal.
  Populated upgrades and uninstall/reinstall cross registry rebuilds, preserving native
  work and existing Sprint history without fabricating historical capture.
- `git_policy_concurrency_probe.py` and `git_policy_concurrency_worker.py`: actual
  native cron commits/budget interruption, competing claims, authority/manual/fact races
  and worker-crash rollback/recovery. Separate committed cursors are required.
- `github_association_concurrency_probe.py` and
  `github_association_concurrency_worker.py`: duplicate normalization across old
  snapshots, fresh-transaction recovery and delivery-specific audit continuity, with
  unchanged native Tasks.

These probes use temporary rendezvous files inside disposable containers/volumes and
explicitly commit only synthetic fixtures. Workers have bounded waits and are terminated
on probe failure. The verifier owns teardown on success, failure and INT/TERM:
`docker compose -p <printed-project> down --volumes --remove-orphans`, then checked
project-label container, volume and network absence queries. It preserves producer
failure and reports cleanup failure separately. Do not manually invoke stdin probes
against an inherited stack.

## Standalone planning races

Run `python3 scripts/probes/test_planning_concurrency.py` from any directory.
Dependencies are Python 3.10+, Docker Compose v2 with `up --wait`, the declared
PostgreSQL/Odoo images, and readable repository addon/config sources. `TMPDIR` may
select an existing writable scratch directory on the development host; absent that, a
uniquely owned temporary directory under the checkout is removed on exit.

Every invocation ignores inherited Compose project identity, creates a UUID-named
project and database, waits for PostgreSQL readiness and installs
`project_agile,project_scrum,project_agile_ui` through the ordinary Odoo server.
`planning_concurrency_setup.py` commits synthetic fixtures;
`planning_concurrency_worker.py` runs bounded assign/return and reorder mutations in
independent Odoo processes; `planning_concurrency_assert.py` checks rejection,
serialization and absence of partial Sprint/backlog state. A separate rendezvous is used
for each race. The runner removes only its printed project containers, volumes and
networks on success, failure and INT/TERM, verifies label-scoped absence, and preserves
original failure if cleanup also fails. No historical stack/database is adopted or
reset. SIGKILL cannot execute process cleanup.

## Optional OCA backend

Run `./scripts/verify-oca-document-page` separately. It builds the pinned OCA fixture
and runs owning native addon tests, including template initialization, content history,
archive/delete and project-page relations previously checked by an external probe.
Discovery metadata/source dumps are not acceptance checks. The optional entrypoint
retains its own disposable project lifecycle; no OCA backend is required by the core
entrypoint. See `docs/contributing.md`.
