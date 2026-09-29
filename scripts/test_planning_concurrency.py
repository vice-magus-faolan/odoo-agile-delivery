#!/usr/bin/env python3
# Run bounded multi-process regressions for planning mutation serialization.

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATABASE = "odoo_agile_planning_concurrency_t_b1f7013f"
WORKER_TIMEOUT_SECONDS = 20
READY_TIMEOUT_SECONDS = 10


def compose(arguments: list[str], *, check: bool = True, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *arguments],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def terminate_database_sessions() -> None:
    compose(
        [
            "exec", "-T", "db", "psql", "-U", "odoo", "-d", "postgres", "-v", "ON_ERROR_STOP=1",
            "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{DATABASE}' AND pid <> pg_backend_pid()",
        ],
        timeout=30,
    )


def reset_database() -> None:
    compose(["up", "-d", "db"], timeout=120)
    terminate_database_sessions()
    compose(["exec", "-T", "db", "dropdb", "-U", "odoo", "--if-exists", DATABASE], timeout=30)
    compose(
        [
            "run", "--rm", "--no-deps", "-T", "odoo", "odoo", "--config=/etc/odoo/odoo.conf",
            "--stop-after-init", "--without-demo=True", "--database", DATABASE,
            "--init", "project_agile,project_scrum,project_agile_ui",
        ],
        timeout=300,
    )


def shell_command(script_name: str) -> str:
    return f"odoo shell --config=/etc/odoo/odoo.conf --database {DATABASE} --no-http < /mnt/planning-scripts/{script_name}"


def shell_arguments(workdir: Path, script_name: str, environment: dict[str, str] | None = None) -> list[str]:
    arguments = [
        "run", "--rm", "--no-deps", "-T",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{SCRIPTS}:/mnt/planning-scripts:ro",
        "-v", f"{workdir}:/mnt/planning-concurrency",
    ]
    for key, value in (environment or {}).items():
        arguments.extend(["-e", f"{key}={value}"])
    arguments.extend(["odoo", "sh", "-lc", shell_command(script_name)])
    return arguments


def run_shell(workdir: Path, script_name: str) -> None:
    completed = compose(shell_arguments(workdir, script_name), check=False, timeout=60)
    if completed.returncode:
        raise RuntimeError(f"{script_name} failed with exit {completed.returncode}:\n{completed.stdout}\n{completed.stderr}")


def wait_for_ready(workdir: Path, workers: tuple[str, ...]) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if all((workdir / f"{worker}.ready").exists() for worker in workers):
            return
        time.sleep(0.05)
    missing = [worker for worker in workers if not (workdir / f"{worker}.ready").exists()]
    raise RuntimeError(f"workers did not reach their pre-mutation rendezvous: {', '.join(missing)}")


def run_scenario(workdir: Path, workers: tuple[str, str]) -> None:
    processes = [
        subprocess.Popen(
            ["docker", "compose", *shell_arguments(workdir, "planning_concurrency_worker.py", {"PLANNING_WORKER": worker})],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for worker in workers
    ]
    try:
        wait_for_ready(workdir, workers)
        (workdir / "start").write_text("start\n")
        for worker, process in zip(workers, processes):
            stdout, stderr = process.communicate(timeout=WORKER_TIMEOUT_SECONDS)
            if process.returncode:
                raise RuntimeError(f"{worker} worker exited {process.returncode}:\n{stdout}\n{stderr}")
            if not (workdir / f"{worker}.json").exists():
                raise RuntimeError(f"{worker} worker exited without a result: \n{stdout}\n{stderr}")
    except BaseException:
        for process in processes:
            if process.poll() is None:
                process.kill()
        for process in processes:
            process.communicate()
        raise


def main() -> int:
    cleanup_error: Exception | None = None
    try:
        reset_database()
        with tempfile.TemporaryDirectory(prefix="t_b1f7013f-planning-concurrency-") as temporary_directory:
            workdir = Path(temporary_directory)
            run_shell(workdir, "planning_concurrency_setup.py")
            run_scenario(workdir, ("assign", "return"))
            run_scenario(workdir, ("reorder_first", "reorder_second"))
            run_shell(workdir, "planning_concurrency_assert.py")
            print(json.dumps(json.loads((workdir / "assertion.json").read_text()), indent=2, sort_keys=True))
    finally:
        try:
            terminate_database_sessions()
            compose(["exec", "-T", "db", "dropdb", "-U", "odoo", "--if-exists", DATABASE], timeout=30)
        except Exception as error:
            cleanup_error = error
    if cleanup_error:
        raise cleanup_error
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.SubprocessError, RuntimeError, TimeoutError) as error:
        print(f"planning concurrency harness failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
