"""Exercise the verifier entrypoint lifecycle with a stateful Docker boundary double."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKER = r'''
import json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ["TEST_STATE"])
with (root / "calls").open("a") as stream:
    stream.write(json.dumps(args) + "\n")
project = os.environ["COMPOSE_PROJECT_NAME"]
mode = os.environ.get("TEST_MODE", "")
if args[0] == "compose":
    command = args[args.index("compose.yaml") + 3]
    if command == "config" and "json" in args:
        config = {
            "volumes": {name: {"name": f"{project}_{name}"} for name in ("postgres-data", "odoo-data")},
            "networks": {"default": {"name": f"{project}_default"}},
            "services": {"db": {}, "odoo": {}},
        }
        if mode == "external":
            config["volumes"]["postgres-data"]["external"] = True
        if mode == "custom":
            config["volumes"]["postgres-data"]["name"] = "shared-data"
        print(json.dumps(config))
    elif command == "up":
        (root / "owned").touch()
        if mode == "up_failure": sys.exit(23)
    elif command == "run":
        if mode == "run_failure": sys.exit(47)
        if mode == "signal":
            (root / "running").touch()
            time.sleep(30)
    elif command == "down":
        if mode in ("cleanup_failure", "both_failures"): sys.exit(29)
        if mode != "leftovers": (root / "owned").unlink(missing_ok=True)
    elif command == "build" and mode == "both_failures": sys.exit(47)
else:
    if mode == "query_failure": sys.exit(31)
    kind = "container" if args[0] == "ps" else args[0]
    owned = (root / "owned").exists()
    if "--filter" in args:
        if owned or mode == "existing_" + kind: print("resource-id")
    elif "--format" in args and mode == "unlabelled_" + kind:
        names = {"container": f"{project}-db-1", "volume": f"{project}_postgres-data", "network": f"{project}_default"}
        print(names[kind])
'''


class TestVerifyLifecycle(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="verify-lifecycle-", dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ("scripts", "addons", "config", "bin"):
            (self.root / name).mkdir()
        (self.root / "scripts" / "verify").write_bytes((ROOT / "scripts" / "verify").read_bytes())
        (self.root / "config" / "odoo.conf").touch()
        for name in ("solution_lifecycle_probe.py", "solution_source_probe.py", "solution_scrum_probe.py", "git_policy_concurrency_probe.py", "github_association_concurrency_probe.py"):
            (self.root / "scripts" / name).touch()
        docker = self.root / "bin" / "docker"
        docker.write_text(f"#!{sys.executable}\n" + DOCKER)
        docker.chmod(0o755)
        python = self.root / "bin" / "python3"
        python.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ $1 == -c ]]; then exec ' + sys.executable + ' "$@"; fi\n'
            'if [[ $1 == -m ]]; then exit 0; fi\n'
            'while IFS= read -r line; do :; done\n'
        )
        python.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.root / 'bin'}:{os.environ['PATH']}",
                        XDG_RUNTIME_DIR=str(self.root), TEST_STATE=str(self.root),
                        COMPOSE_PROJECT_NAME="verify-unit-fresh")

    def run_verify(self, mode="", explicit=True):
        env = dict(self.env, TEST_MODE=mode)
        if not explicit:
            env.pop("COMPOSE_PROJECT_NAME")
        result = subprocess.run(["bash", str(self.root / "scripts" / "verify")],
                                env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15)
        calls = [json.loads(line) for line in (self.root / "calls").read_text().splitlines()]
        return result, calls

    def assert_no_mutation(self, calls):
        self.assertFalse(any(action in call for call in calls for action in ("build", "up", "exec", "run", "down")))

    def test_success_cleans_explicit_fresh_project(self):
        result, calls = self.run_verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "owned").exists())
        self.assertTrue(any(call[-4:] == ["up", "-d", "--wait", "db"] for call in calls))
        self.assertTrue(any("down" in call and "--volumes" in call for call in calls))
        self.assertIn("no containers, volumes or networks", result.stderr)

    def test_default_project_cleans_and_uses_distinct_run_names(self):
        first, calls = self.run_verify(explicit=False)
        second, more_calls = self.run_verify(explicit=False)
        self.assertEqual((first.returncode, second.returncode), (0, 0))
        first_name = next(call[call.index("-p") + 1] for call in calls if "-p" in call)
        names = {call[call.index("-p") + 1] for call in more_calls if "-p" in call}
        self.assertEqual(len(names), 2)
        self.assertIn(first_name, names)
        self.assertFalse((self.root / "owned").exists())

    def test_original_run_failure_is_preserved(self):
        result, calls = self.run_verify("run_failure")
        self.assertEqual(result.returncode, 47, result.stderr)
        self.assertTrue(any("down" in call for call in calls))
        self.assertFalse((self.root / "owned").exists())

    def test_partial_start_failure_is_cleaned(self):
        result, _ = self.run_verify("up_failure")
        self.assertEqual(result.returncode, 23)
        self.assertFalse((self.root / "owned").exists())

    def test_cleanup_failure_makes_success_fail(self):
        result, _ = self.run_verify("cleanup_failure")
        self.assertEqual(result.returncode, 1)
        self.assertIn("teardown failed", result.stderr)
        self.assertIn("resources remain", result.stderr)

    def test_cleanup_failure_does_not_mask_original_failure(self):
        result, _ = self.run_verify("both_failures")
        self.assertEqual(result.returncode, 47)
        self.assertIn("teardown failed", result.stderr)

    def test_successful_down_with_leftovers_fails(self):
        result, _ = self.run_verify("leftovers")
        self.assertEqual(result.returncode, 1)
        self.assertIn("resources remain", result.stderr)

    def test_existing_labelled_and_unlabelled_resources_are_untouched(self):
        for kind in ("container", "volume", "network"):
            for prefix in ("existing_", "unlabelled_"):
                with self.subTest(kind=kind, prefix=prefix):
                    (self.root / "calls").unlink(missing_ok=True)
                    result, calls = self.run_verify(prefix + kind)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assert_no_mutation(calls)

    def test_shared_storage_configuration_is_refused(self):
        for mode in ("external", "custom"):
            with self.subTest(mode=mode):
                (self.root / "calls").unlink(missing_ok=True)
                result, calls = self.run_verify(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assert_no_mutation(calls)

    def test_failed_resource_query_is_fail_closed(self):
        result, calls = self.run_verify("query_failure")
        self.assertEqual(result.returncode, 31)
        self.assert_no_mutation(calls)

    def test_same_name_run_lock_refuses_before_docker(self):
        import fcntl
        locks = self.root / "odoo-agile-verify"
        locks.mkdir()
        with (locks / "verify-unit-fresh.lock").open("w") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(["bash", str(self.root / "scripts" / "verify")], env=self.env,
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / "calls").exists())

    def test_term_interruption_cleans_and_preserves_signal_status(self):
        process = subprocess.Popen(["bash", str(self.root / "scripts" / "verify")],
                                   env=dict(self.env, TEST_MODE="signal"), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            deadline = time.monotonic() + 10
            while not (self.root / "running").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue((self.root / "running").exists())
            os.killpg(process.pid, signal.SIGTERM)
            _, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 143, stderr)
            self.assertFalse((self.root / "owned").exists())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
