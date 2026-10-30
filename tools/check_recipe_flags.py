#!/usr/bin/env python3
"""Check that every ``python tools/X.py ...`` line in a shell recipe names
flags that ``X.py`` actually accepts.

The recipe scripts under ``reproduce/`` and ``scripts/`` are reviewer-facing:
they are what a reader copies to re-run a cell.  Their command blocks are
commented out by default (the live sweeps cost GPU-hours), so nothing executes
them and nothing notices when a flag is renamed.  On 2026-10-30 a scan found
seven such commands -- ``--n-seeds`` on a driver that threads its seed through
``WAVE247_SEED``, ``--output-dir`` on a driver that spells it ``--outdir``,
``--ckpt``/``--arm`` on a driver that has neither, and a whole nine-flag
``tools/run_real_ckpt_eval.py`` call whose real CLI is six flags.

Two of those seven were invisible to a naive ``add_argument`` scan because the
``tools/run_sota_*.py`` family registers ``--output-dir`` and ``--seed``
through :func:`tools._sota_common.add_sota_common_args`.  This checker resolves
that call too.

Usage::

    python3 tools/check_recipe_flags.py            # report, exit 1 on problems
    python3 tools/check_recipe_flags.py --verbose  # also list every command

Scope: shell scripts only (``*.sh``).  Python drivers that shell out are not
scanned; the recipe scripts are the surface a reviewer reads.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Directories whose ``*.sh`` files are scanned.
SHELL_DIRS: tuple[str, ...] = ("reproduce", "scripts")

#: ``python tools/foo.py ...`` optionally behind a venv path or a leading
#: ``#`` (the recipe commands are commented out until the reader uncomments).
_INVOCATION = re.compile(
    r"^\s*#?\s*(?:\S*python\S*\s+)((?:tools|scripts)/[\w/]+\.py)\b(.*)$"
)
_FLAG = re.compile(r"--[A-Za-z0-9][\w-]*")

#: Flags registered by ``tools._sota_common.add_sota_common_args``.  ``--seed``
#: is suppressed by the three callers that pass ``include_seed=False``; the
#: checker is permissive about it rather than re-deriving each call site.
_SOTA_COMMON_FLAGS = frozenset({"--output-dir", "--seed"})


def _accepted_flags(path: pathlib.Path) -> set[str]:
    """Every long flag ``path`` registers with argparse."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    flags: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            for arg in node.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and arg.value.startswith("--")
                ):
                    flags.add(arg.value)
    if "add_sota_common_args(" in source:
        flags |= _SOTA_COMMON_FLAGS
    return flags


def _invocations(script: pathlib.Path) -> list[tuple[int, str, list[str]]]:
    """``(line_no, target, flags)`` for each ``python ...`` line in ``script``.

    A trailing backslash continues the command onto the next line; the flags on
    those continuation lines belong to the same invocation.
    """
    lines = script.read_text(encoding="utf-8").splitlines()
    out: list[tuple[int, str, list[str]]] = []
    for index, line in enumerate(lines):
        match = _INVOCATION.match(line)
        if match is None:
            continue
        target, tail = match.group(1), match.group(2)
        flags: list[str] = []
        cursor = index
        while True:
            # Continuation lines of a commented-out recipe start with ``#``;
            # strip that marker (and any prose after it) before parsing flags.
            body = re.sub(r"^\s*#\s?", "", tail).split("#", 1)[0]
            flags.extend(_FLAG.findall(body))
            if body.rstrip().endswith("\\") and cursor + 1 < len(lines):
                cursor += 1
                tail = lines[cursor]
            else:
                break
        out.append((index + 1, target, flags))
    return out


def check(repo_root: pathlib.Path = REPO_ROOT) -> list[str]:
    """Return one message per problem; an empty list means the recipes are clean."""
    problems: list[str] = []
    cache: dict[pathlib.Path, set[str]] = {}
    for directory in SHELL_DIRS:
        for script in sorted((repo_root / directory).glob("*.sh")):
            for line_no, target, flags in _invocations(script):
                target_path = repo_root / target
                if not target_path.is_file():
                    problems.append(
                        f"{script.relative_to(repo_root)}:{line_no}: "
                        f"no such driver {target}"
                    )
                    continue
                if target_path not in cache:
                    cache[target_path] = _accepted_flags(target_path)
                unknown = [f for f in flags if f not in cache[target_path]]
                if unknown:
                    problems.append(
                        f"{script.relative_to(repo_root)}:{line_no}: "
                        f"{target} does not accept {sorted(set(unknown))}"
                    )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose", action="store_true", help="list every scanned invocation"
    )
    args = parser.parse_args(argv)

    if args.verbose:
        for directory in SHELL_DIRS:
            for script in sorted((REPO_ROOT / directory).glob("*.sh")):
                for line_no, target, flags in _invocations(script):
                    print(f"{script.relative_to(REPO_ROOT)}:{line_no}  {target}  {flags}")

    problems = check()
    for problem in problems:
        print(problem)
    print(f"recipe-flag check: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1:]))
