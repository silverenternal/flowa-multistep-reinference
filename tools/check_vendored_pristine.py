#!/usr/bin/env python3
"""Verify that every vendored upstream tree is still pristine.

AGENTS.md guardrail 1 says the nine vendored repositories under ``data/`` must
stay byte-identical to their upstream commits, and ``data_availability.md``
tells the reviewer the same thing in a table of nine files that were patched
during internal development and reverted.  Nothing checked it: ``data/`` is
gitignored, so no CI job can see the trees, and the rule lived only in prose.

This gate reads the trees where they exist:

* every discovered vendored repository must have **no modifications to tracked
  files** (untracked additions -- weights, caches, generated configs -- are
  expected and allowed);
* the three repositories whose commit AGENTS.md pins must be **at that commit**;
* the nine files named in ``data_availability.md`` must be **byte-identical to
  their pinned commit**.

On a clone there is no ``data/`` tree, so the gate prints ``SKIP`` and exits 0.
That is deliberate: the rule is about the authoring machine's inputs, and a
clone is told how to re-fetch them by ``data_availability.md``.

Usage::

    python3 tools/check_vendored_pristine.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"

#: The eight vendored *code* trees.  The ``data/*/weights`` directories are
#: also git repositories (model hubs), but they hold downloaded weights rather
#: than vendored source, so a local change there is not a guardrail breach.
CODE_REPOS: tuple[str, ...] = (
    "data/FlowMol3/repo",
    "data/lineageflow_upstream",
    "data/kanzi_upstream",
    "data/HiDream-I1/repo",
    "data/graphbfn/repo",
    "data/lumina_image_2_0/repo",
    "data/protbfn_abbfn/repo",
    "data/wan2_2/repo",
)

#: ``(relative path, pinned commit)`` -- the three AGENTS.md names explicitly.
PINNED: tuple[tuple[str, str], ...] = (
    ("data/FlowMol3/repo", "77cae22"),
    ("data/lineageflow_upstream", "ccef84a"),
    ("data/kanzi_upstream", "cfed9cf"),
)

#: The nine files ``tnnls_submission/data_availability.md`` discloses as
#: patched-then-reverted, with the commit each must match.
REVERTED_FILES: tuple[tuple[str, str, str], ...] = (
    ("data/FlowMol3/repo", "77cae22", "flowmol/analysis/molecule_builder.py"),
    ("data/FlowMol3/repo", "77cae22", "flowmol/models/flowmol.py"),
    ("data/FlowMol3/repo", "77cae22", "flowmol/utils/ctmc_utils.py"),
    ("data/FlowMol3/repo", "77cae22", "flowmol/analysis/metrics.py"),
    ("data/lineageflow_upstream", "ccef84a", "evaluation/evaluate_all.py"),
    ("data/lineageflow_upstream", "ccef84a", "evaluation/foldability_omegafold.py"),
    ("data/lineageflow_upstream", "ccef84a", "evaluation/novelty_mmseqs2.py"),
    ("data/lineageflow_upstream", "ccef84a", "evaluation/run_foldability.py"),
    ("data/lineageflow_upstream", "ccef84a", "evaluation/self_consistency_esmif.py"),
)


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.rstrip("\n")


def _repos() -> list[pathlib.Path]:
    """The vendored code trees that exist on this machine."""
    return [REPO_ROOT / rel for rel in CODE_REPOS if (REPO_ROOT / rel / ".git").exists()]


def _discovered() -> list[pathlib.Path]:
    """Every git tree under ``data/``, so an unlisted one is at least reported."""
    if not DATA.is_dir():
        return []
    return [
        candidate
        for candidate in sorted(DATA.glob("*")) + sorted(DATA.glob("*/*"))
        if (candidate / ".git").exists()
    ]


def check() -> tuple[int, list[str]]:
    """Return (number of checks run, failure messages)."""
    repos = _repos()
    if not repos:
        return 0, []

    problems: list[str] = []
    checks = 0

    for repo in repos:
        checks += 1
        dirty = _git(repo, "status", "--porcelain", "--untracked-files=no")
        if dirty:
            # Porcelain is "XY <path>"; do not strip, the leading space is XY.
            files = ", ".join(line[3:] for line in dirty.splitlines())
            problems.append(f"{repo.relative_to(REPO_ROOT)}: modified tracked files: {files}")

    for rel, pin in PINNED:
        repo = REPO_ROOT / rel
        if not repo.is_dir():
            continue
        checks += 1
        head = _git(repo, "rev-parse", "--short=7", "HEAD")
        if not head.startswith(pin):
            problems.append(f"{rel}: HEAD is {head or '<unknown>'}, pinned to {pin}")

    for rel, pin, path in REVERTED_FILES:
        repo = REPO_ROOT / rel
        if not repo.is_dir():
            continue
        checks += 1
        diff = _git(repo, "diff", pin, "--", path)
        if diff:
            problems.append(f"{rel}/{path}: differs from {pin}")

    return checks, problems


def main() -> int:
    checks, problems = check()
    if checks == 0:
        print("SKIP: no vendored git tree under data/ (a clone has none; see "
              "tnnls_submission/data_availability.md for the pinned commits)")
        return 0
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        return 1
    print(f"OK: {checks} checks across {len(_repos())} vendored repositories, all pristine")
    known = {str(REPO_ROOT / rel) for rel in CODE_REPOS}
    for extra in _discovered():
        if str(extra) not in known:
            print(f"NOTE: {extra.relative_to(REPO_ROOT)} is a git tree that is not a "
                  "vendored code repo; not checked")
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    if len(sys.argv) > 1:
        print(
            f"{sys.argv[0]}: this driver takes no arguments; "
            f"got {sys.argv[1:]}. Its parameters are fixed in the source.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    sys.exit(main())
