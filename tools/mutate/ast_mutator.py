#!/usr/bin/env python
"""Stdlib-only AST point mutator — a Windows-compatible mutation tester.

``mutmut`` refuses to run on native Windows (upstream boxed/mutmut#397; see
``tools/mutate/WINDOWS_LIMITATION.md``). This module is the fallback: a
self-contained, stdlib-only mutation tester that parses a target module with
:mod:`ast`, enumerates single-point mutation sites, and re-runs the pytest
suite once per mutant to decide whether the suite *kills* the mutation.

**This is an AST-based point mutator, not full mutmut. Coverage is partial but
the S-tier threshold gating works the same.** Concretely, the differences are:

* mutmut mutates every expression it can reach, including string/bytes
  payloads, ``dict``/``set`` literals, slices, and keyword-argument names.
  This tool implements the seven operator families listed below.
* mutmut caches per-mutant coverage to skip provably-unreachable mutants.
  This tool has no coverage integration; it uses a two-phase test strategy
  (see :func:`_run_pytest`) to get the same verdict for less wall-clock.
* The *score* both tools emit is the same quantity — ``killed / total`` — so
  the thresholds enforced by ``.github/workflows/mutation-nightly.yml``
  (project >= 0.50, contracts/universal >= 0.75, frame >= 0.60) are directly
  comparable and gate identically.

Mutation operators
------------------

======  ====================================================================
 Op      Rewrite
======  ====================================================================
AOR     Arithmetic operator replacement: ``+``/``-``, ``*``/``/``, and the
        equality pair ``==``/``!=``.
UOR     Unary operator replacement: ``not x`` -> ``x``, ``-x`` -> ``+x``.
ROR     Relational operator replacement: ``<`` -> ``<=``, ``>`` -> ``>=``,
        ``<=`` -> ``<``, ``>=`` -> ``>``.
LOR     Logical operator replacement: ``and`` -> ``or``, ``or`` -> ``and``.
CRP     Constant replacement: ``True``/``False`` swap, ``0``/``1`` swap
        (applied to ``int`` and to the ``0.0``/``1.0`` float literals that
        carry this project's unit-interval bounds).
SDL     Statement deletion: the statement is wrapped in ``if False:`` so it
        becomes a no-op stub while remaining syntactically valid.
NSR     Name-swap replacement (the ``cap``/``floor`` envelope swap): an
        identifier containing ``cap`` becomes ``floor`` and vice versa,
        applied only when the swapped name is really bound in the same
        module. This is the ``frame/merge.py`` bound-confusion probe.
======  ====================================================================

Safety
------

Mutants are **never written into the working tree**. Each mutant is injected
into the pytest subprocess through a generated ``sitecustomize``-style plugin
(:data:`_INJECTOR_SOURCE`) that installs a :mod:`importlib` meta-path finder
overriding exactly one module name. A crash, a timeout, or a ``Ctrl-C`` can
therefore never leave a half-mutated source file on disk, and mutants can be
evaluated concurrently (``--jobs``) because they share no mutable state.

CLI
---

::

    python tools/mutate/ast_mutator.py run --target adaptive_reflow/frame/merge.py \
        --output mutmut_results.json
    python tools/mutate/ast_mutator.py summary mutmut_results.json

``--target`` accepts a file or a directory and may be repeated. ``run`` also
accepts ``--baseline`` to regenerate ``tools/mutate/mutation_baseline.json``.
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOL_NAME = "ast_mutator 1.0"
SCHEMA_VERSION = "1.0.0"

#: S-tier gate thresholds, mirrored into every results file so the workflow
#: and the baseline read the same numbers.
TARGETS: dict[str, float] = {
    "contracts": 0.75,
    "universal": 0.75,
    "frame": 0.60,
    "project": 0.50,
}

#: Package directories swept by the wrapper scripts.
DEFAULT_TARGET_DIRS: tuple[str, ...] = (
    "adaptive_reflow/contracts",
    "adaptive_reflow/universal",
    "adaptive_reflow/frame",
    "adaptive_reflow/eval",
    "adaptive_reflow/policy",
    "adaptive_reflow/schedule",
)

#: Per-mutant pytest timeout (seconds). The full suite runs in ~35 s, so a
#: mutant that exceeds this has almost certainly introduced a hot loop; like
#: mutmut, a timeout counts as *killed*.
DEFAULT_TIMEOUT = 300

#: Directories excluded from the fast phase: the benchmark/stress suites cost
#: minutes and never distinguish a mutant that the unit tests miss.
SLOW_TEST_DIRS: tuple[str, ...] = ("tests/perf",)


# ---------------------------------------------------------------------------
# Mutant injector (written to a temp dir, loaded via ``pytest -p``)
# ---------------------------------------------------------------------------

#: Source of the injector plugin. pytest loads ``-p`` plugins before conftest
#: collection and before the package under test is imported, so the meta-path
#: finder is in place by the time any test triggers the real import.
_INJECTOR_SOURCE = '''\
"""Generated by tools/mutate/ast_mutator.py — injects one mutated module."""

import importlib.abc
import importlib.util
import os
import sys

_TARGET = os.environ["AST_MUTANT_MODULE"]
_SOURCE = os.environ["AST_MUTANT_SOURCE"]
_ORIGIN = os.environ["AST_MUTANT_ORIGIN"]


class _MutantFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serve ``_TARGET`` from the mutated source file, everything else normally."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname != _TARGET:
            return None
        # ``_ORIGIN`` (the real path) is used as the spec origin so tracebacks,
        # ``__file__`` and any path-relative logic behave exactly as unmutated.
        return importlib.util.spec_from_file_location(fullname, _ORIGIN, loader=self)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        with open(_SOURCE, encoding="utf-8") as handle:
            source = handle.read()
        exec(compile(source, _ORIGIN, "exec"), module.__dict__)


# Drop any pre-existing import so the mutated definition is authoritative.
sys.modules.pop(_TARGET, None)
sys.meta_path.insert(0, _MutantFinder())


# Pin a deterministic Hypothesis profile for the duration of the mutation
# run. Without this the harness is unsound in three ways:
#
#   * The shared on-disk example database at ``.hypothesis/examples`` leaks
#     counterexamples between mutants, so whether mutant N dies depends on
#     which mutants ran before it. ``derandomize`` implies ``database=None``,
#     which isolates every run.
#   * ``deadline`` failures are wall-clock sensitive. Under ``--jobs`` the box
#     is loaded, so a slow-but-correct mutant raises DeadlineExceeded and is
#     scored as "killed" -- inflating the score with a timing artefact.
#   * Random example generation makes a borderline mutant's verdict a coin
#     flip; ``derandomize`` fixes the seed so a verdict is reproducible.
#
# Failures here are reported loudly. A silently non-deterministic harness
# produces numbers that look authoritative and are not, which is strictly
# worse than a harness that complains.
try:
    from hypothesis import settings as _hypothesis_settings
except ImportError:  # pragma: no cover - hypothesis is optional
    pass
else:
    _hypothesis_settings.register_profile(
        "ast_mutator",
        # NB: ``derandomize=True`` implies ``database=None``; passing an
        # explicit database alongside it raises InvalidArgument.
        derandomize=True,
        deadline=None,
        print_blob=False,
    )
    _hypothesis_settings.load_profile("ast_mutator")
    if not _hypothesis_settings.default.derandomize:
        raise RuntimeError(
            "ast_mutator: hypothesis profile did not take effect; mutation "
            "verdicts would be non-deterministic. Refusing to continue."
        )
'''


# ---------------------------------------------------------------------------
# Mutation site model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MutationSite:
    """One point mutation: node ``index`` in a deterministic DFS of the AST."""

    index: int
    line: int
    op: str
    detail: str

    def mutant_id(self, module_path: str) -> str:
        return f"{module_path}:{self.line}:{self.op}"


@dataclass
class MutantResult:
    """Verdict for a single mutant."""

    id: str
    killed: bool
    test_class: str | None
    op: str
    line: int
    detail: str
    seconds: float = 0.0
    note: str | None = None


@dataclass
class ModuleReport:
    """Aggregated verdicts for one module."""

    module_path: str
    mutants: list[MutantResult] = field(default_factory=list)
    #: False when the unmutated source fails its own fast-phase tests, which
    #: invalidates every verdict for the module.
    baseline_ok: bool = True
    baseline_note: str | None = None

    @property
    def total(self) -> int:
        return len(self.mutants)

    @property
    def killed(self) -> int:
        return sum(1 for m in self.mutants if m.killed)

    @property
    def survived(self) -> int:
        return self.total - self.killed

    @property
    def score(self) -> float:
        return (self.killed / self.total) if self.total else 0.0


# ---------------------------------------------------------------------------
# Deterministic AST indexing
# ---------------------------------------------------------------------------


def _index_nodes(tree: ast.AST) -> list[ast.AST]:
    """Return every node in a deterministic pre-order DFS.

    Both site collection and site application use this exact traversal, so a
    node's position is a stable identifier across re-parses of the same
    source. That is what lets a mutant be described by an integer instead of
    by a fragile source offset.
    """
    nodes: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        nodes.append(node)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return nodes


def _parent_map(tree: ast.AST) -> dict[int, ast.AST]:
    """Map ``id(child) -> parent`` for in-place node replacement."""
    parents: dict[int, ast.AST] = {}
    for node in _index_nodes(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _annotation_nodes(tree: ast.AST) -> set[int]:
    """Return ``id()`` of every node inside a type annotation.

    ``from __future__ import annotations`` makes annotations strings at
    runtime, so mutating them cannot change behaviour: every such mutant
    would be an unkillable *equivalent mutant* and would silently deflate the
    score. Excluding them is what keeps the reported number honest.
    """
    excluded: set[int] = set()

    def mark(node: ast.AST | None) -> None:
        if node is None:
            return
        for sub in _index_nodes(node):
            excluded.add(id(sub))

    for node in _index_nodes(tree):
        if isinstance(node, ast.AnnAssign):
            mark(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mark(node.returns)
            args = node.args
            for arg in (
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
                args.vararg,
                args.kwarg,
            ):
                if arg is not None:
                    mark(arg.annotation)
    return excluded


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Return ``id()`` of docstring expression statements (never mutated)."""
    excluded: set[int] = set()
    for node in _index_nodes(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            excluded.add(id(first))
            excluded.add(id(first.value))
    return excluded


# ---------------------------------------------------------------------------
# Operator tables
# ---------------------------------------------------------------------------

_AOR_BINOP: dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.Div,
    ast.Div: ast.Mult,
}

_AOR_COMPARE: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}

_ROR_COMPARE: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Lt: ast.LtE,
    ast.Gt: ast.GtE,
    ast.LtE: ast.Lt,
    ast.GtE: ast.Gt,
}

_SDL_STATEMENTS: tuple[type[ast.stmt], ...] = (
    ast.Assign,
    ast.AugAssign,
    ast.Expr,
    ast.Raise,
    ast.Return,
)


def _swap_cap_floor(name: str) -> str | None:
    """Return ``name`` with ``cap``/``floor`` swapped, or ``None`` if absent."""
    if "cap" in name:
        return name.replace("cap", "floor")
    if "floor" in name:
        return name.replace("floor", "cap")
    return None


# ---------------------------------------------------------------------------
# Site collection
# ---------------------------------------------------------------------------


def collect_sites(source: str) -> list[MutationSite]:
    """Enumerate every mutation site in ``source``, in deterministic order."""
    tree = ast.parse(source)
    nodes = _index_nodes(tree)
    skip = _annotation_nodes(tree) | _docstring_nodes(tree)
    # Names that are genuinely bound somewhere in this module. NSR consults
    # this so it never rewrites an identifier into one that nothing defines.
    # Function/class definitions bind a name without ever appearing as an
    # ``ast.Name``, so they have to be collected explicitly -- otherwise the
    # ``_cap_for_channel`` <-> ``_floor_for_channel`` swap is missed whenever
    # the counterpart helper is defined but not itself called.
    bound_names: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Name):
            bound_names.add(node.id)
        elif isinstance(node, ast.arg):
            bound_names.add(node.arg)
        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            bound_names.add(node.name)

    sites: list[MutationSite] = []

    for index, node in enumerate(nodes):
        if id(node) in skip:
            continue
        line = getattr(node, "lineno", 0)
        if not line:
            continue

        # --- AOR / ROR on binary arithmetic -----------------------------
        if isinstance(node, ast.BinOp) and type(node.op) in _AOR_BINOP:
            replacement = _AOR_BINOP[type(node.op)]
            sites.append(
                MutationSite(
                    index,
                    line,
                    "AOR",
                    f"{type(node.op).__name__}->{replacement.__name__}",
                )
            )

        # --- AOR (equality) / ROR (ordering) on comparisons -------------
        elif isinstance(node, ast.Compare):
            for pos, cmp_op in enumerate(node.ops):
                kind = type(cmp_op)
                if kind in _AOR_COMPARE:
                    sites.append(
                        MutationSite(
                            index,
                            line,
                            "AOR",
                            f"cmp{pos}:{kind.__name__}->"
                            f"{_AOR_COMPARE[kind].__name__}",
                        )
                    )
                elif kind in _ROR_COMPARE:
                    sites.append(
                        MutationSite(
                            index,
                            line,
                            "ROR",
                            f"cmp{pos}:{kind.__name__}->"
                            f"{_ROR_COMPARE[kind].__name__}",
                        )
                    )

        # --- UOR ---------------------------------------------------------
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                sites.append(MutationSite(index, line, "UOR", "Not->identity"))
            elif isinstance(node.op, ast.USub):
                sites.append(MutationSite(index, line, "UOR", "USub->UAdd"))

        # --- LOR ---------------------------------------------------------
        elif isinstance(node, ast.BoolOp):
            flip = "And->Or" if isinstance(node.op, ast.And) else "Or->And"
            sites.append(MutationSite(index, line, "LOR", flip))

        # --- CRP ---------------------------------------------------------
        elif isinstance(node, ast.Constant):
            value = node.value
            # ``isinstance(True, int)`` is True, so booleans come first.
            if isinstance(value, bool):
                sites.append(
                    MutationSite(index, line, "CRP", f"{value}->{not value}")
                )
            elif isinstance(value, int) and value in (0, 1):
                sites.append(
                    MutationSite(index, line, "CRP", f"{value}->{1 - value}")
                )
            elif isinstance(value, float) and value in (0.0, 1.0):
                # Float 0.0/1.0 carry the same 0<->1 swap. This matters a
                # great deal here: the ``[floor, cap]`` envelope bounds in
                # frame/merge.py are all float literals, so restricting CRP
                # to ``int`` would leave the load-bearing bound checks
                # unmutated and overstate the module's score.
                sites.append(
                    MutationSite(index, line, "CRP", f"{value}->{1.0 - value}")
                )

        # --- NSR (cap <-> floor envelope swap) ---------------------------
        if isinstance(node, ast.Name):
            swapped = _swap_cap_floor(node.id)
            # Only mutate to a name that is genuinely bound in this module;
            # otherwise the mutant dies of NameError for the wrong reason and
            # measures nothing about the test suite.
            if swapped is not None and swapped in bound_names:
                sites.append(
                    MutationSite(index, line, "NSR", f"{node.id}->{swapped}")
                )

        # --- SDL ---------------------------------------------------------
        if isinstance(node, _SDL_STATEMENTS) and _sdl_eligible(node):
            sites.append(
                MutationSite(index, line, "SDL", type(node).__name__)
            )

    return sites


def _sdl_eligible(node: ast.stmt) -> bool:
    """Return whether ``node`` may be replaced by an ``if False:`` stub.

    ``__all__`` and dunder assignments are module metadata rather than
    behaviour; deleting them produces noise, not signal.
    """
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.startswith("__"):
                return False
    return True


# ---------------------------------------------------------------------------
# Site application
# ---------------------------------------------------------------------------


def apply_site(source: str, site: MutationSite) -> str | None:
    """Return ``source`` with exactly one mutation applied, or ``None``.

    ``None`` means the rewrite produced source identical to the original (an
    equivalent mutant, which is not worth a pytest run).
    """
    tree = ast.parse(source)
    nodes = _index_nodes(tree)
    if site.index >= len(nodes):
        return None
    node = nodes[site.index]
    original = ast.unparse(tree)

    if site.op == "AOR" and isinstance(node, ast.BinOp):
        node.op = _AOR_BINOP[type(node.op)]()
    elif site.op in {"AOR", "ROR"} and isinstance(node, ast.Compare):
        pos = int(site.detail.split(":", 1)[0].removeprefix("cmp"))
        table = _AOR_COMPARE if site.op == "AOR" else _ROR_COMPARE
        node.ops[pos] = table[type(node.ops[pos])]()
    elif site.op == "UOR" and isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            # ``not x`` -> ``x``: the node itself is replaced by its operand.
            if not _replace_node(tree, node, node.operand):
                return None
        else:
            node.op = ast.UAdd()
    elif site.op == "LOR" and isinstance(node, ast.BoolOp):
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
    elif site.op == "CRP" and isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            node.value = not node.value
        elif isinstance(node.value, float):
            node.value = 1.0 - float(node.value)
        else:
            node.value = 1 - int(node.value)
    elif site.op == "NSR" and isinstance(node, ast.Name):
        swapped = _swap_cap_floor(node.id)
        if swapped is None:
            return None
        node.id = swapped
    elif site.op == "SDL" and isinstance(node, ast.stmt):
        stub = ast.If(
            test=ast.Constant(value=False),
            body=[node],
            orelse=[],
        )
        if not _replace_node(tree, node, stub):
            return None
    else:
        return None

    ast.fix_missing_locations(tree)
    mutated = ast.unparse(tree)
    if mutated == original:
        return None
    return mutated


def _replace_node(tree: ast.AST, old: ast.AST, new: ast.AST) -> bool:
    """Swap ``old`` for ``new`` inside its parent. Return success."""
    parents = _parent_map(tree)
    parent = parents.get(id(old))
    if parent is None:
        return False
    for field_name, value in ast.iter_fields(parent):
        if value is old:
            setattr(parent, field_name, new)
            return True
        if isinstance(value, list):
            for i, item in enumerate(value):
                if item is old:
                    value[i] = new
                    return True
    return False


# ---------------------------------------------------------------------------
# Test-suite execution
# ---------------------------------------------------------------------------


def module_dotted_path(module_path: Path, repo_root: Path) -> str:
    """Convert ``adaptive_reflow/frame/merge.py`` -> ``adaptive_reflow.frame.merge``."""
    rel = module_path.resolve().relative_to(repo_root.resolve())
    return ".".join(rel.with_suffix("").parts)


def related_tests(module_path: Path, repo_root: Path) -> list[str]:
    """Best-effort guess at the test files that exercise ``module_path``.

    Used only for the *fast phase*. Correctness never depends on this being
    complete: a mutant that the fast phase fails to kill is escalated to the
    full suite before it is recorded as a survivor.
    """
    rel = module_path.resolve().relative_to(repo_root.resolve())
    stem = rel.stem
    package = rel.parent.name
    dotted = module_dotted_path(module_path, repo_root)
    tests_root = repo_root / "tests"
    if not tests_root.is_dir():
        return []

    selected: set[Path] = set()
    for candidate in sorted(tests_root.rglob("test_*.py")):
        posix = candidate.relative_to(repo_root).as_posix()
        if any(posix.startswith(slow) for slow in SLOW_TEST_DIRS):
            continue
        # Name-based match (``merge`` -> ``test_bounded_merge_invariants.py``).
        if stem in candidate.stem:
            selected.add(candidate)
            continue
        # Sibling suite directory (``frame`` -> ``tests/test_frame/``).
        if candidate.parent.name == f"test_{package}":
            selected.add(candidate)
            continue
        # Import-based match on the dotted module path.
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if dotted in text:
            selected.add(candidate)

    return [p.relative_to(repo_root).as_posix() for p in sorted(selected)]


def _pytest_command(targets: Sequence[str]) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        *targets,
        "-x",
        "--tb=no",
        "-q",
        "-p",
        "mutant_inject",
        "-p",
        "no:cacheprovider",
    ]


def _extract_test_class(stdout: str) -> str | None:
    """Pull the killing test's class (or test name) out of pytest output."""
    for line in stdout.splitlines():
        stripped = line.strip()
        for marker in ("FAILED ", "ERROR "):
            if not stripped.startswith(marker):
                continue
            nodeid = stripped[len(marker) :].split(" ", 1)[0]
            parts = nodeid.split("::")
            if len(parts) >= 3:
                return parts[1]  # class name
            if len(parts) == 2:
                return parts[1]  # bare test function
            return nodeid
    return None


def _run_pytest(
    targets: Sequence[str],
    repo_root: Path,
    env: dict[str, str],
    timeout: int,
) -> tuple[bool, str | None, str]:
    """Run pytest once. Return ``(killed, test_class, note)``.

    Exit-code contract: ``0`` -> every test passed -> the mutant *survived*.
    Any non-zero code (failures, collection errors, an import-time explosion
    from the mutant) -> *killed*. Exit code ``5`` ("no tests collected") is
    the one exception: it means the selection was empty, which is a harness
    problem rather than evidence about the mutant, so it is reported as an
    error rather than counted as a kill.
    """
    try:
        proc = subprocess.run(
            _pytest_command(targets),
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        # A mutant that hangs the suite is killed (matches mutmut semantics).
        return True, "<timeout>", "timeout"

    if proc.returncode == 5:
        return False, None, "no-tests-collected"
    if proc.returncode == 0:
        return False, None, ""
    return True, _extract_test_class(proc.stdout + proc.stderr), ""


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _iter_target_files(targets: Iterable[str], repo_root: Path) -> Iterator[Path]:
    """Expand file/directory targets into concrete ``.py`` module paths."""
    for raw in targets:
        path = (repo_root / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if path.is_dir():
            for candidate in sorted(path.rglob("*.py")):
                if candidate.name == "__init__.py":
                    continue
                if "__pycache__" in candidate.parts:
                    continue
                yield candidate
        elif path.is_file() and path.suffix == ".py":
            yield path
        else:
            print(f"[ast_mutator] skipping unreadable target: {raw}", file=sys.stderr)


def run_module(
    module_path: Path,
    repo_root: Path,
    workdir: Path,
    *,
    full_tests: Sequence[str],
    timeout: int,
    jobs: int,
    quiet: bool = False,
) -> ModuleReport:
    """Mutate ``module_path`` and evaluate every mutant against the suite."""
    rel_posix = module_path.resolve().relative_to(repo_root.resolve()).as_posix()
    report = ModuleReport(module_path=rel_posix)
    source = module_path.read_text(encoding="utf-8")

    try:
        sites = collect_sites(source)
    except SyntaxError as exc:
        print(f"[ast_mutator] cannot parse {rel_posix}: {exc}", file=sys.stderr)
        return report

    dotted = module_dotted_path(module_path, repo_root)
    fast_tests = related_tests(module_path, repo_root) or list(full_tests)

    if not quiet:
        print(
            f"[ast_mutator] {rel_posix}: {len(sites)} candidate sites; "
            f"fast phase = {len(fast_tests)} test file(s)"
        )

    def build_env(mutant_file: Path) -> dict[str, str]:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{workdir}{os.pathsep}{existing}" if existing else str(workdir)
        )
        env["AST_MUTANT_MODULE"] = dotted
        env["AST_MUTANT_SOURCE"] = str(mutant_file)
        env["AST_MUTANT_ORIGIN"] = str(module_path.resolve())
        return env

    # ------------------------------------------------------------------
    # Baseline sanity check. Inject the *unmutated* source and require the
    # fast phase to pass. If it does not, every mutant would be recorded as
    # "killed" and the module would report a bogus 1.000 score. Failing loudly
    # here is the difference between a measurement and a rubber stamp.
    # ------------------------------------------------------------------
    baseline_file = workdir / f"baseline_{abs(hash(rel_posix))}.py"
    baseline_file.write_text(source, encoding="utf-8")
    base_killed, base_class, base_note = _run_pytest(
        fast_tests, repo_root, build_env(baseline_file), timeout
    )
    baseline_file.unlink(missing_ok=True)
    if base_killed or base_note == "no-tests-collected":
        report.baseline_ok = False
        report.baseline_note = base_note or f"failing test: {base_class}"
        print(
            f"[ast_mutator] {rel_posix}: BASELINE FAILED "
            f"({report.baseline_note}) — refusing to score this module",
            file=sys.stderr,
        )
        return report

    # Materialise every mutant's source up front so the parallel workers do
    # no AST work and cannot interfere with one another.
    prepared: list[tuple[MutationSite, str]] = []
    for site in sites:
        mutated = apply_site(source, site)
        if mutated is None:
            continue  # equivalent mutant; nothing to test
        prepared.append((site, mutated))

    def evaluate(item: tuple[int, tuple[MutationSite, str]]) -> MutantResult:
        slot, (site, mutated) = item
        mutant_file = workdir / f"mutant_{slot}.py"
        mutant_file.write_text(mutated, encoding="utf-8")
        env = build_env(mutant_file)

        started = time.monotonic()
        # Phase 1 — cheap, targeted subset. A failure here is conclusive:
        # the subset is a subset of the full suite, so the full suite would
        # fail too.
        killed, test_class, note = _run_pytest(fast_tests, repo_root, env, timeout)
        if not killed and note != "no-tests-collected":
            # Phase 2 — the subset let it through, so pay for the full suite
            # before declaring a survivor.
            killed, test_class, note = _run_pytest(
                full_tests, repo_root, env, timeout
            )
        elapsed = time.monotonic() - started

        mutant_file.unlink(missing_ok=True)
        return MutantResult(
            id=site.mutant_id(rel_posix),
            killed=killed,
            test_class=test_class,
            op=site.op,
            line=site.line,
            detail=site.detail,
            seconds=round(elapsed, 3),
            note=note or None,
        )

    indexed = list(enumerate(prepared))
    if jobs > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            results = list(pool.map(evaluate, indexed))
    else:
        results = [evaluate(item) for item in indexed]

    report.mutants = results
    if not quiet:
        print(
            f"[ast_mutator] {rel_posix}: killed={report.killed} "
            f"survived={report.survived} score={report.score:.3f}"
        )
    return report


def build_results(reports: Sequence[ModuleReport]) -> dict[str, Any]:
    """Assemble the ``mutmut_results.json`` payload."""
    total = sum(r.total for r in reports)
    killed = sum(r.killed for r in reports)
    survived = total - killed
    return {
        "version": SCHEMA_VERSION,
        "captured_at": datetime.now(UTC).isoformat(),
        "platform": "windows" if os.name == "nt" else sys.platform,
        "tool": TOOL_NAME,
        "overall": {
            "total_mutants": total,
            "killed": killed,
            "survived": survived,
            "score": round(killed / total, 6) if total else 0.0,
        },
        "by_module": {
            r.module_path: {
                "total_mutants": r.total,
                "killed": r.killed,
                "survived": r.survived,
                "score": round(r.score, 6),
                **(
                    {}
                    if r.baseline_ok
                    else {"baseline_ok": False, "baseline_note": r.baseline_note}
                ),
                "mutants": [
                    {
                        "id": m.id,
                        "killed": m.killed,
                        "test_class": m.test_class,
                        "op": m.op,
                        "line": m.line,
                        "detail": m.detail,
                        "seconds": m.seconds,
                        **({"note": m.note} if m.note else {}),
                    }
                    for m in r.mutants
                ],
            }
            for r in reports
        },
        "targets": dict(TARGETS),
    }


# ---------------------------------------------------------------------------
# Area scoring (shared with the CI gate)
# ---------------------------------------------------------------------------


def area_score(results: dict[str, Any], prefix: str) -> tuple[int, int, float]:
    """Return ``(killed, total, score)`` for modules under ``prefix``."""
    killed = total = 0
    for path, payload in (results.get("by_module") or {}).items():
        if not isinstance(payload, dict):
            continue
        if path.replace("\\", "/").startswith(prefix):
            killed += int(payload.get("killed", 0) or 0)
            total += int(payload.get("total_mutants", 0) or 0)
    return killed, total, (killed / total) if total else 0.0


def _justified_survivors(repo_root: Path) -> set[str]:
    """Mutant ids the ledger says are acceptable survivors."""
    ledger = repo_root / "tools" / "mutate" / "justified_survivors.json"
    if not ledger.is_file():
        return set()
    try:
        payload = json.loads(ledger.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    entries = payload.get("survivors") or []
    ids: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            ids.add(entry)
        elif isinstance(entry, dict) and isinstance(entry.get("id"), str):
            ids.add(entry["id"])
    return ids


# ---------------------------------------------------------------------------
# Baseline regeneration
# ---------------------------------------------------------------------------


def write_baseline(results: dict[str, Any], repo_root: Path) -> Path:
    """Regenerate ``tools/mutate/mutation_baseline.json`` from ``results``."""
    baseline_path = repo_root / "tools" / "mutate" / "mutation_baseline.json"
    previous: dict[str, Any] = {}
    if baseline_path.is_file():
        try:
            previous = json.loads(baseline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
    previous_modules = previous.get("by_module") or {}

    by_module: dict[str, Any] = {}
    for path, payload in (results.get("by_module") or {}).items():
        entry: dict[str, Any] = {
            "killed": payload.get("killed"),
            "survived": payload.get("survived"),
            "score": payload.get("score"),
            "mutants_total": payload.get("total_mutants"),
        }
        # Preserve the hand-written rationale from the placeholder baseline.
        prior = previous_modules.get(path)
        if isinstance(prior, dict) and prior.get("rationale"):
            entry["rationale"] = prior["rationale"]
        by_module[path] = entry

    overall = results.get("overall") or {}
    baseline = {
        "version": SCHEMA_VERSION,
        "captured_at": results.get("captured_at"),
        "platform": results.get("platform"),
        "tool": results.get("tool", TOOL_NAME),
        "overall_score": overall.get("score"),
        "_note": (
            "Generated by tools/mutate/ast_mutator.py. This is an AST-based "
            "point mutator, not full mutmut: coverage is partial (seven "
            "operator families; see the module docstring) but the S-tier "
            "threshold gating works the same, because both tools report "
            "killed/total. mutmut itself cannot run on Windows (upstream "
            "boxed/mutmut#397), so this file is reproducible on both "
            "Windows and the Linux CI runner."
        ),
        "targets": dict(TARGETS),
        "by_module": by_module,
        "thresholds_enforced": {
            "project_wide_min_score": TARGETS["project"],
            "contracts_min_score": TARGETS["contracts"],
            "universal_min_score": TARGETS["universal"],
            "frame_min_score": TARGETS["frame"],
        },
    }
    baseline_path.write_text(
        json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return baseline_path


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    targets = list(args.target) or list(DEFAULT_TARGET_DIRS)
    module_paths = list(_iter_target_files(targets, repo_root))
    if not module_paths:
        print("[ast_mutator] no target modules resolved", file=sys.stderr)
        return 1

    full_tests = list(args.tests)
    started = time.monotonic()
    reports: list[ModuleReport] = []

    with tempfile.TemporaryDirectory(prefix="ast_mutator_") as tmp:
        workdir = Path(tmp)
        (workdir / "mutant_inject.py").write_text(
            _INJECTOR_SOURCE, encoding="utf-8"
        )
        for module_path in module_paths:
            reports.append(
                run_module(
                    module_path,
                    repo_root,
                    workdir,
                    full_tests=full_tests,
                    timeout=args.timeout,
                    jobs=args.jobs,
                    quiet=args.quiet,
                )
            )

    results = build_results(reports)
    results["elapsed_seconds"] = round(time.monotonic() - started, 2)

    output = Path(args.output)
    if not output.is_absolute():
        output = repo_root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"[ast_mutator] wrote {output}")

    if args.baseline:
        print(f"[ast_mutator] wrote {write_baseline(results, repo_root)}")

    overall = results["overall"]
    print(
        f"[ast_mutator] overall: {overall['killed']}/{overall['total_mutants']} "
        f"killed, score={overall['score']:.3f} "
        f"({results['elapsed_seconds']}s)"
    )

    broken = [r.module_path for r in reports if not r.baseline_ok]
    if broken:
        print(
            "[ast_mutator] ERROR: unmutated baseline failed for "
            f"{len(broken)} module(s): {', '.join(broken)}",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    path = Path(args.results)
    if not path.is_file():
        print(f"[ast_mutator] results file not found: {path}", file=sys.stderr)
        return 1
    results = json.loads(path.read_text(encoding="utf-8"))
    repo_root = Path(args.repo_root).resolve()

    overall = results.get("overall") or {}
    total = int(overall.get("total_mutants", 0) or 0)
    killed = int(overall.get("killed", 0) or 0)
    survived = int(overall.get("survived", 0) or 0)
    score = float(overall.get("score", 0.0) or 0.0)
    targets = results.get("targets") or TARGETS

    print(f"tool:        {results.get('tool', TOOL_NAME)}")
    print(f"captured_at: {results.get('captured_at')}")
    print(f"platform:    {results.get('platform')}")
    print("")
    print(f"{'module':<48} {'killed':>7} {'total':>7} {'score':>7}")
    print("-" * 72)
    for module_path, payload in sorted((results.get("by_module") or {}).items()):
        print(
            f"{module_path:<48} {payload.get('killed', 0):>7} "
            f"{payload.get('total_mutants', 0):>7} "
            f"{float(payload.get('score', 0.0)):>7.3f}"
        )
    print("-" * 72)
    print(f"{'OVERALL':<48} {killed:>7} {total:>7} {score:>7.3f}")
    print("")

    # Per-area breakdown, using the same helper the CI gate calls.
    for area in ("contracts", "universal", "frame"):
        a_killed, a_total, a_score = area_score(
            results, f"adaptive_reflow/{area}/"
        )
        if not a_total:
            continue
        threshold = float(targets.get(area, 0.0))
        verdict = "PASS" if a_score >= threshold else "FAIL"
        print(
            f"{area:<12} killed={a_killed}/{a_total} score={a_score:.3f} "
            f"(threshold {threshold:.2f}) {verdict}"
        )
    project_threshold = float(targets.get("project", TARGETS["project"]))
    print(
        f"{'project':<12} killed={killed}/{total} score={score:.3f} "
        f"(threshold {project_threshold:.2f}) "
        f"{'PASS' if score >= project_threshold else 'FAIL'}"
    )

    if survived:
        justified = _justified_survivors(repo_root)
        print("")
        print(f"surviving mutants ({survived}):")
        for _module_path, payload in sorted((results.get("by_module") or {}).items()):
            for mutant in payload.get("mutants") or []:
                if mutant.get("killed"):
                    continue
                tag = " [justified]" if mutant.get("id") in justified else ""
                print(
                    f"  {mutant.get('id')}  {mutant.get('detail', '')}{tag}"
                )
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    """Enforce the S-tier thresholds. Exits non-zero on a breach."""
    path = Path(args.results)
    if not path.is_file():
        print(f"::error::results file not found: {path}", file=sys.stderr)
        return 1
    results = json.loads(path.read_text(encoding="utf-8"))
    targets = {**TARGETS, **(results.get("targets") or {})}
    overall = results.get("overall") or {}
    total = int(overall.get("total_mutants", 0) or 0)
    score = float(overall.get("score", 0.0) or 0.0)

    if total == 0:
        print("::error::no mutants were evaluated; refusing to pass the gate")
        return 1

    failed = False
    project_threshold = float(targets["project"])
    print(
        f"project    killed={overall.get('killed')}/{total} score={score:.3f} "
        f"(threshold {project_threshold:.2f})"
    )
    if score < project_threshold:
        print(
            f"::error::whole-project mutation score {score:.3f} below "
            f"threshold {project_threshold:.2f}"
        )
        failed = True

    for area in ("contracts", "universal", "frame"):
        a_killed, a_total, a_score = area_score(
            results, f"adaptive_reflow/{area}/"
        )
        if not a_total:
            continue
        threshold = float(targets[area])
        print(
            f"{area:<10} killed={a_killed}/{a_total} score={a_score:.3f} "
            f"(threshold {threshold:.2f})"
        )
        if a_score < threshold:
            print(
                f"::error::{area} mutation score {a_score:.3f} below "
                f"threshold {threshold:.2f}"
            )
            failed = True

    if failed:
        return 1
    print("[ast_mutator] mutation-score gate PASS")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ast_mutator",
        description=(
            "Stdlib-only AST point mutator. A Windows-compatible fallback "
            "for mutmut (upstream boxed/mutmut#397)."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="repository root (default: inferred from this file's location)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="generate and evaluate mutants")
    run_parser.add_argument(
        "--target",
        action="append",
        default=[],
        help=(
            "module file or package directory to mutate; repeatable "
            f"(default: {' '.join(DEFAULT_TARGET_DIRS)})"
        ),
    )
    run_parser.add_argument(
        "--output",
        default="mutmut_results.json",
        help="results JSON path (default: mutmut_results.json)",
    )
    run_parser.add_argument(
        "--tests",
        action="append",
        default=None,
        help="pytest target for the confirmation phase (default: tests/)",
    )
    run_parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"per-mutant pytest timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    run_parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="mutants to evaluate concurrently (default: 1)",
    )
    run_parser.add_argument(
        "--baseline",
        action="store_true",
        help="also regenerate tools/mutate/mutation_baseline.json",
    )
    run_parser.add_argument(
        "--quiet", action="store_true", help="suppress per-module progress"
    )
    run_parser.set_defaults(func=cmd_run)

    summary_parser = sub.add_parser("summary", help="print a results summary")
    summary_parser.add_argument("results", help="path to the results JSON")
    summary_parser.set_defaults(func=cmd_summary)

    gate_parser = sub.add_parser("gate", help="enforce the S-tier thresholds")
    gate_parser.add_argument("results", help="path to the results JSON")
    gate_parser.set_defaults(func=cmd_gate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "tests", None) is None:
        args.tests = ["tests/"]
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
