#!/usr/bin/env python3
"""Verify that every git-tracked symlink resolves on a fresh clone.

The repository ships its evidence as symlinks: ``paper-data/<cell>/<file>``
points at ``../../verification_outputs/<file>`` and
``docs/headline-evidence/<cell>/<file>`` does the same.  Git stores a symlink
as its target string, so the link survives a clone but the *target* only does
if that path is itself tracked.

``verification_outputs/`` is listed in ``.gitignore`` (line 64) and its
contents are force-added file by file, with no written rule for which files
get added.  The result was 29 links that dangled on every clone while
resolving on the machine that produced them — invisible to every existing
gate, because each gate ran in the working tree.

This checker walks ``git ls-files --stage`` for mode ``120000`` entries and
resolves each one.  A dangling link is a failure unless it matches one of the
documented exemptions below.

Usage
-----
    python3 tools/check_clone_integrity.py
    python3 tools/check_clone_integrity.py --json
    python3 tools/check_clone_integrity.py --quiet
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: ``(link, target)`` pairs allowed to dangle, with the reason recorded in
#: the accompanying comment.  Delete an entry once the target ships.
KNOWN_DANGLING: frozenset[tuple[str, str]] = frozenset()

#: Target prefixes that are rebuilt rather than committed.  ``paper-figures/``
#: links into ``site/figures/``, which ``mkdocs build`` populates by copying
#: ``docs/figures/``; the source of truth is tracked, the copy is not.  The
#: checker still requires the source file to exist, so a renamed figure is
#: caught here rather than at build time.
BUILD_OUTPUT_PREFIXES: tuple[str, ...] = ("site/",)


def tracked_symlinks() -> list[tuple[str, str]]:
    """Return ``(link, target)`` for every tracked symlink, repo-relative."""
    raw = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    links: list[tuple[str, str]] = []
    for entry in raw.split("\0"):
        if not entry or not entry.startswith("120000 "):
            continue
        meta, _, path = entry.partition("\t")
        mode, sha, stage = meta.split()
        del mode, stage
        blob = subprocess.run(
            ["git", "cat-file", "-p", sha],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout
        links.append((path, blob))
    return links


def _build_source(target: str) -> Path | None:
    """Map a build-output target back to the file the build copies it from."""
    name = os.path.basename(target)
    for candidate in (
        REPO_ROOT / "docs" / "figures" / name,
        REPO_ROOT / "docs" / "drafts" / name,
        REPO_ROOT / "verification_outputs" / name,
    ):
        if candidate.exists():
            return candidate
    return None


def check() -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    counts = {"ok": 0, "build-output": 0, "exempt": 0, "broken": 0}
    for link, target in tracked_symlinks():
        resolved = os.path.normpath(
            os.path.join(str(Path(link).parent), target)
        )
        if (REPO_ROOT / resolved).exists() or (REPO_ROOT / link).exists():
            status = "ok"
        elif (link, resolved) in KNOWN_DANGLING:
            status = "exempt"
        elif resolved.startswith(BUILD_OUTPUT_PREFIXES):
            status = "build-output" if _build_source(resolved) else "broken"
        else:
            status = "broken"
        counts[status] += 1
        rows.append({"link": link, "target": resolved, "status": status})
    return rows, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--quiet", action="store_true", help="summary line only")
    args = parser.parse_args(argv)

    rows, counts = check()
    if args.json:
        print(json.dumps({"rows": rows, "counts": counts}, indent=1))
        return 0 if counts["broken"] == 0 else 1

    if not args.quiet:
        for row in rows:
            if row["status"] in ("broken", "exempt"):
                print(f"{row['status']:12s} {row['link']}  ->  {row['target']}")
        print()
    print(" ".join(f"{k}={v}" for k, v in counts.items()))
    if counts["broken"]:
        print(f"FAIL: {counts['broken']} tracked symlink(s) dangle on a clone",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
