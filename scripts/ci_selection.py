"""Conservative native unit selection for the supported Community verifier."""

# This CLI's stdout is the verifier's machine-readable selection protocol.
# pylint: disable=print-used

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

# These optional bridges belong to verify-oca-document-page, not this runtime.
OPTIONAL_DEPENDENCIES = {"document_page_project"}
NATIVE_DEPENDENCIES = {"project", "hr_timesheet"}
NAME = re.compile(r"[a-z][a-z0-9_]*\Z")


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], stderr=subprocess.PIPE
    ).decode()


def graph_at(root, revision):
    paths = git(root, "ls-tree", "-r", "--name-only", revision, "addons").splitlines()
    manifests = {}
    for path in paths:
        parts = path.split("/")
        if len(parts) != 3 or parts[2] != "__manifest__.py":
            continue
        name = parts[1]
        manifest = ast.literal_eval(git(root, "show", f"{revision}:{path}"))
        if not isinstance(manifest, dict):
            raise ValueError(f"Invalid manifest: {path}")
        depends = manifest.get("depends", [])
        if not NAME.fullmatch(name) or not isinstance(depends, list):
            raise ValueError(f"Invalid manifest: {path}")
        if not all(isinstance(dep, str) and NAME.fullmatch(dep) for dep in depends):
            raise ValueError(f"Invalid dependencies: {path}")
        if manifest.get("installable", True):
            manifests[name] = set(depends)
    if not manifests:
        raise ValueError("No installable addons discovered")
    excluded = set()
    for name, depends in manifests.items():
        unknown = depends - manifests.keys() - NATIVE_DEPENDENCIES
        if unknown - OPTIONAL_DEPENDENCIES:
            raise ValueError(f"Unsupported dependencies for {name}: {sorted(unknown)}")
        if unknown:
            excluded.add(name)
    while True:
        blocked = {name for name, deps in manifests.items() if deps & excluded}
        if blocked <= excluded:
            break
        excluded |= blocked
    graph = {
        name: deps & manifests.keys()
        for name, deps in manifests.items()
        if name not in excluded
    }
    if not graph:
        raise ValueError("No supported addons discovered")
    # Validate cycles even on a full/default run: an invalid full is not safe.
    topological(graph)
    return graph, excluded, paths


def topological(graph):
    pending = {name: set(deps) for name, deps in graph.items()}
    ordered = []
    while pending:
        ready = sorted(name for name, deps in pending.items() if not deps)
        if not ready:
            raise ValueError("Cyclic or unavailable addon dependencies")
        ordered.extend(ready)
        for name in ready:
            del pending[name]
        for deps in pending.values():
            deps.difference_update(ready)
    return ordered


def import_edges(root, revision, paths, graph):
    edges = {name: set(deps) for name, deps in graph.items()}
    for path in paths:
        parts = path.split("/")
        if len(parts) < 3 or parts[1] not in edges or not path.endswith(".py"):
            continue
        tree = ast.parse(git(root, "show", f"{revision}:{path}"), filename=path)
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
                if node.module == "odoo.addons":
                    modules = [f"odoo.addons.{alias.name}" for alias in node.names]
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            for module in modules:
                imported = module.split(".")
                if len(imported) > 2 and imported[:2] == ["odoo", "addons"]:
                    dependency = imported[2]
                    if dependency in edges and dependency != parts[1]:
                        edges[parts[1]].add(dependency)
    return edges


def dependents(graph, changed):
    selected = set(changed)
    while True:
        affected = {name for name, deps in graph.items() if deps & selected}
        if affected <= selected:
            return selected
        selected |= affected


def documentation(path):
    parts = path.split("/")
    if path.startswith("docs/"):
        return path.endswith((".md", ".rst"))
    if len(parts) == 1:
        return path in {"README.md", "LICENSE", "COPYING"}
    if len(parts) < 3 or parts[0] != "addons":
        return False
    return (len(parts) == 3 and parts[2] in {"README.rst", "README.md"}) or (
        parts[2] == "readme" and path.endswith((".md", ".rst"))
    )


def decide(root, base=None, head=None, addons=None):
    current = git(root, "rev-parse", "HEAD").strip()
    graph, excluded, paths = graph_at(root, current)
    supported = topological(graph)
    result = {
        "mode": "full",
        "reason": "complete developer/default-branch suite",
        "selected": sorted(graph),
        "install": supported + ["hr_timesheet"],
        "excluded": sorted(excluded),
    }
    if addons is not None:
        if not addons or set(addons) - graph.keys():
            raise ValueError("Focused selection requires supported addon names")
        edges = import_edges(root, current, paths, graph)
        result.update(
            mode="selected",
            reason="focused addons and transitive manifest/import dependents",
            selected=sorted(dependents(edges, addons)),
        )
        return result
    if base is None:
        return result
    try:
        if git(root, "rev-parse", "--verify", f"{head}^{{commit}}").strip() != current:
            raise ValueError("comparison head is not the checked-out candidate")
        ancestor = git(root, "merge-base", base, head).strip()
        old_graph, old_excluded, _ = graph_at(root, ancestor)
        if git(
            root,
            "diff",
            "--no-renames",
            "--diff-filter=D",
            "--name-only",
            ancestor,
            head,
            "--",
        ).strip():
            result["reason"] = "deleted or renamed paths; full assurance"
            return result
        changed = git(
            root, "diff", "--no-renames", "--name-only", "-z", ancestor, head, "--"
        ).split("\0")[:-1]
        if graph != old_graph or excluded != old_excluded:
            result["reason"] = "addon availability/dependency graph changed"
            return result
        if any(path.endswith("/__manifest__.py") for path in changed):
            result["reason"] = "manifest changed"
            return result
        impact = set()
        for path in changed:
            if documentation(path):
                continue
            parts = path.split("/")
            if len(parts) < 3 or parts[0] != "addons" or parts[1] not in graph:
                result["reason"] = f"shared or unknown impact: {path}"
                return result
            impact.add(parts[1])
        edges = import_edges(root, current, paths, graph)
        selected = dependents(edges, impact)
        result.update(
            mode="selected" if selected else "none",
            reason="changed addons and transitive manifest/import dependents"
            if selected
            else "no unit/runtime impact (documentation only)",
            selected=sorted(selected),
        )
    except (
        subprocess.CalledProcessError,
        ValueError,
        SyntaxError,
        UnicodeError,
    ) as error:
        result["reason"] = f"analysis unavailable; full fallback: {error}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pr", nargs=2, metavar=("BASE", "HEAD"))
    mode.add_argument("--addons", nargs="+", metavar="ADDON")
    parser.add_argument("--format", choices=("json", "lines"), default="json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    result = decide(root, *(args.pr or ()), addons=args.addons)
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    else:
        print(result["mode"])
        print(",".join(result["selected"]))
        print(",".join(result["install"]))
        print(result["reason"])
        print(",".join(result["excluded"]))


if __name__ == "__main__":
    main()
