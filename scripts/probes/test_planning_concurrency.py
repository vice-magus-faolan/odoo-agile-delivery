#!/usr/bin/env python3
# Run bounded multi-process regressions for planning mutation serialization.
# CLI results and cleanup diagnostics belong on stdout/stderr, not Odoo logging.
# pylint: disable=print-used

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts/probes"
RUN_ID = uuid.uuid4().hex
PROJECT = "odoo-agile-planning-" + RUN_ID
DATABASE = "odoo_agile_planning_" + RUN_ID
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", str(ROOT / "compose.yaml")]
WORKER_TIMEOUT_SECONDS = 20
READY_TIMEOUT_SECONDS = 10


def compose(
    arguments: list[str], *, check: bool = True, timeout: int = 180
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [*COMPOSE, *arguments],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and completed.returncode:
        raise RuntimeError(
            f"Compose exited {completed.returncode}: "
            f"{completed.stdout}\n{completed.stderr}"
        )
    if check:
        print(completed.stdout + completed.stderr, end="", flush=True)
    return completed


def reset_database() -> None:
    # A fresh project owns an empty PostgreSQL volume; never reset inherited data.
    compose(["up", "-d", "--wait", "--wait-timeout", "120", "db"], timeout=150)
    compose(
        [
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "-v",
            str(ROOT / "addons") + ":/mnt/extra-addons:ro",
            "odoo",
            "odoo",
            "--config=/etc/odoo/odoo.conf",
            "--stop-after-init",
            "--without-demo=True",
            "--database",
            DATABASE,
            "--init",
            "project_agile,project_scrum,project_agile_ui",
        ],
        timeout=300,
    )


def cleanup() -> None:
    failed = False
    try:
        completed = compose(["down", "--volumes", "--remove-orphans"], check=False)
        if completed.returncode:
            print(completed.stdout + completed.stderr, file=sys.stderr)
            failed = True
    except subprocess.SubprocessError as error:
        print(f"Planning teardown command failed: {error}", file=sys.stderr)
        failed = True
    for kind, flags in (("container", "-aq"), ("volume", "-q"), ("network", "-q")):
        try:
            result = subprocess.run(
                [
                    "docker",
                    kind,
                    "ls",
                    flags,
                    "--filter",
                    "label=com.docker.compose.project=" + PROJECT,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout.strip():
                print(
                    f"Planning {kind} resources remain: {result.stdout}",
                    file=sys.stderr,
                )
                failed = True
        except subprocess.SubprocessError as error:
            print(f"Planning {kind} absence query failed: {error}", file=sys.stderr)
            failed = True
    if failed:
        raise RuntimeError("Planning owned-resource teardown failed")
    print(f"Planning teardown complete: {PROJECT} (no containers, volumes or networks)")


def shell_command(script_name: str) -> str:
    return (
        f"odoo shell --config=/etc/odoo/odoo.conf --database {DATABASE} "
        f"--no-http < /mnt/planning-scripts/{script_name}"
    )


def shell_arguments(
    workdir: Path, script_name: str, environment: dict[str, str] | None = None
) -> list[str]:
    arguments = [
        "run",
        "--rm",
        "--no-deps",
        "-T",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "-v",
        str(ROOT / "addons") + ":/mnt/extra-addons:ro",
        "-v",
        f"{SCRIPTS}:/mnt/planning-scripts:ro",
        "-v",
        f"{workdir}:/mnt/planning-concurrency",
    ]
    for key, value in (environment or {}).items():
        arguments.extend(["-e", f"{key}={value}"])
    arguments.extend(["odoo", "sh", "-c", shell_command(script_name)])
    return arguments


def run_shell(workdir: Path, script_name: str) -> None:
    completed = compose(shell_arguments(workdir, script_name), check=False, timeout=60)
    if completed.returncode:
        raise RuntimeError(
            f"{script_name} failed with exit {completed.returncode}:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )


def wait_for_ready(workdir: Path, workers: tuple[str, ...]) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if all((workdir / f"{worker}.ready").exists() for worker in workers):
            return
        time.sleep(0.05)
    missing = [
        worker for worker in workers if not (workdir / f"{worker}.ready").exists()
    ]
    raise RuntimeError(
        f"workers did not reach their pre-mutation rendezvous: {', '.join(missing)}"
    )


def run_scenario(workdir: Path, workers: tuple[str, str]) -> None:
    (workdir / "start").unlink(missing_ok=True)
    processes = [
        subprocess.Popen(
            [
                *COMPOSE,
                *shell_arguments(
                    workdir,
                    "planning_concurrency_worker.py",
                    {"PLANNING_WORKER": worker},
                ),
            ],
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
        for worker, process in zip(workers, processes, strict=False):
            stdout, stderr = process.communicate(timeout=WORKER_TIMEOUT_SECONDS)
            if process.returncode:
                raise RuntimeError(
                    f"{worker} worker exited {process.returncode}:\n{stdout}\n{stderr}"
                )
            if not (workdir / f"{worker}.json").exists():
                raise RuntimeError(
                    f"{worker} worker exited without a result: \n{stdout}\n{stderr}"
                )
    except BaseException:
        for process in processes:
            if process.poll() is None:
                process.kill()
        for process in processes:
            process.communicate()
        raise


def main() -> int:
    print(
        f"Owning fresh disposable planning project: {PROJECT}; database: {DATABASE}",
        flush=True,
    )
    subprocess.run(["chmod", "a+r", str(ROOT / "config/odoo.conf")], check=True)
    subprocess.run(
        ["chmod", "-R", "a+rX", str(ROOT / "addons"), str(SCRIPTS)], check=True
    )
    try:
        reset_database()
        with tempfile.TemporaryDirectory(
            prefix="planning-concurrency-", dir=os.environ.get("TMPDIR", str(ROOT))
        ) as temporary_directory:
            workdir = Path(temporary_directory)
            run_shell(workdir, "planning_concurrency_setup.py")
            run_scenario(workdir, ("assign", "return"))
            run_scenario(workdir, ("reorder_first", "reorder_second"))
            run_shell(workdir, "planning_concurrency_assert.py")
            # Stdout carries the existing machine-readable race result.
            print(  # pylint: disable=print-used
                json.dumps(
                    json.loads((workdir / "assertion.json").read_text()),
                    indent=2,
                    sort_keys=True,
                )
            )
    finally:
        original_error = sys.exc_info()[1]
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            cleanup()
        except Exception as error:
            print(
                f"Planning teardown failed; original failure: {original_error!r}; "
                f"cleanup: {error}",
                file=sys.stderr,
            )
            if original_error is None:
                raise
    return 0


def interrupted(signum, frame):
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        raise SystemExit(main())
    except (subprocess.SubprocessError, RuntimeError, TimeoutError) as error:
        # CLI failure output belongs on stderr, not the application logger.
        print(  # pylint: disable=print-used
            f"planning concurrency harness failed: {error}", file=sys.stderr
        )
        raise SystemExit(1) from error
