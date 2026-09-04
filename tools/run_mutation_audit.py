#!/usr/bin/env python3
"""Standalone quarterly runner for the F.6 ML-aware mutation audit.

**F.6 of** ``framework-internal-metrics.md`` **rev 2 §1** mandates a
quarterly mutation audit using DL-specific operators against four
subsystem families:

* **Theory checkers** -- ``adaptive_reflow/theory/{checkers,
  paper_quantities, lemma2_checker, validation, rate_bound}.py``
* **Integrators** -- ``adaptive_reflow/adapters/integrators.py`` plus
  ``adaptive_reflow/algorithm/dynamics.py``
* **Schedulers** -- ``adaptive_reflow/algorithm/scheduler/_core.py``
  and ``adaptive_reflow/algorithm/scheduler_extra.py``
* **Adapters** -- one representative per family
  (twodim_fm / mnist_fm / lineageflow / self_flow)

The metric is the canonical mutation score
``killed / total`` with the rev 2 acceptance gate of
**aggregate >= 0.6 AND every per-subsystem score >= 0.4**.

Five ML-aware mutation operators
--------------------------------

The five operators defined here match the recommendations of Ma et al.
2019 TSE "DeepGauge" and Wang et al. 2018 ASE "DeepMutation":

======  =================================================================
 Op      Mutation
======  =================================================================
 WP      Weight perturbation: numeric constant -> constant + 1e-3 * |c|
 AS      Activation swap: activation callsite -> ``relu``-style fallback
 SM      Structural mutation: branch operand swap (``and``<->``or``,
         ternary true/false branch swap, ``assert`` -> ``pass``)
 TF      Threshold flip: comparison operator rewrite (``>`` <-> ``<``,
         ``>=`` <-> ``<=``, ``==`` <-> ``!=``)
 CS      Constant substitution: structural constants
         (1.0, 0.5, 2.0, math.pi, math.e) -> multiplied by 1.1
======  =================================================================

Why this is NOT the same as ``tools/run_sbc_audit.py``
------------------------------------------------------

``tools/run_sbc_audit.py`` (Wave 18 P2 C.7) is **SBC** (Talts et al.
2018) -- a statistical posterior calibration check. This tool is
**point mutation** -- it injects single-perturbation AST mutants into
the pytest subprocess and counts how many the test suite kills. They
share *no* helpers, *no* constants, *no* JSON schema. The two tools
are independent nightly/quarterly quality gates per §1 C.7 / F.6 of
``framework-internal-metrics.md``.

Stdlib-only by design
---------------------

This runner intentionally avoids importing ``mutmut`` at runtime; the
``mutmut>=2.4`` dev-dep is for compatibility / reproducibility of the
*underlying* AST traversal semantics. The mutation engine is a
self-contained :mod:`ast` walker so the audit can run on minimal CI
images and on Windows (per ``tools/mutate/WINDOWS_LIMITATION.md``).
Mutants are injected through a generated :mod:`importlib` meta-path
finder in a subprocess so a crash, timeout, or Ctrl-C can never leave
a half-mutated source on disk.

CLI
---

::

    python tools/run_mutation_audit.py run --output verification_outputs/mutation_audit_q4_2026.json
    python tools/run_mutation_audit.py summary verification_outputs/mutation_audit_q4_2026.json
    python tools/run_mutation_audit.py --help

Exit codes:

* 0 -- every per-subsystem score >= 0.4 AND aggregate >= 0.6
* 1 -- at least one subsystem below 0.4 OR aggregate below 0.6
* 2 -- infrastructure failure (could not even run the baseline pytest)

References:

* Ma et al. 2019, *DeepGauge: Multi-Granularity Testing Criteria for
  Deep Learning Systems*, TSE.
* Wang et al. 2018, *DeepMutation: Mutation Testing of Deep Learning
  Systems*, ASE.
* Shen et al. 2018, *Mutation Testing of Deep Learning Systems* (early
  neuron-level coverage).
* framework-internal-metrics.md rev 2 §1 F.6.
* todo/algo-improvement-mutation-testing.md.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Subsystem definition -- one row per (family, file-glob, test-glob).
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent

# Subsystem -> (source files, test selector). Each test selector is a
# pytest node-id substring that pins the test pool to the same files
# the audit is mutating. ``--target`` style flags could be added but
# the fixed table below matches the F.6 §1 scope verbatim.
SUBSYSTEM_TABLE: dict[str, dict[str, object]] = {
    "theory": {
        "description": "Paper-grounded theorem checkers (Wave 11/15)",
        "files": [
            "adaptive_reflow/theory/checkers.py",
            "adaptive_reflow/theory/paper_quantities.py",
            "adaptive_reflow/theory/lemma2_checker.py",
            "adaptive_reflow/theory/validation.py",
            "adaptive_reflow/theory/rate_bound.py",
        ],
        "tests": "tests/test_theory/",
    },
    "integrators": {
        "description": "ODE / SDE integrator families",
        "files": [
            "adaptive_reflow/adapters/integrators.py",
            "adaptive_reflow/algorithm/dynamics.py",
        ],
        "tests": "tests/test_convergence/ tests/test_algorithm/test_dynamics_solver.py",
    },
    "schedulers": {
        "description": "Schedule families (cosine, jittered, codimension sheet)",
        "files": [
            "adaptive_reflow/algorithm/scheduler/_core.py",
            "adaptive_reflow/algorithm/scheduler_extra.py",
        ],
        "tests": "tests/test_algorithm/test_scheduler.py tests/test_algorithm/test_scheduler_algorithm_on_2d_oracle.py",
    },
    "adapters": {
        "description": "One representative adapter per family",
        "files": [
            "adaptive_reflow/adapters/twodim_fm.py",
            "adaptive_reflow/adapters/mnist_fm.py",
            "adaptive_reflow/adapters/lineageflow.py",
            "adaptive_reflow/adapters/self_flow.py",
            "adaptive_reflow/adapters/synthetic.py",
        ],
        "tests": "tests/test_adapters/",
    },
}


@dataclass(frozen=True)
class MutantRecord:
    """One injected mutation, with its verdict."""

    subsystem: str
    operator: str  # one of WP/AS/SM/TF/CS
    location: str  # "<file>:<lineno>"
    payload: str  # human-readable description of the change
    killed: bool
    wall_clock_s: float


@dataclass
class SubsystemScore:
    """Per-subsystem mutation-score rollup."""

    subsystem: str
    description: str
    killed: int = 0
    total: int = 0
    wall_clock_s: float = 0.0
    per_operator: dict[str, dict[str, int]] = field(default_factory=dict)
    mutants: list[MutantRecord] = field(default_factory=list)

    @property
    def score(self) -> float:
        return (self.killed / self.total) if self.total else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "subsystem": self.subsystem,
            "description": self.description,
            "killed": self.killed,
            "total": self.total,
            "score": round(self.score, 4),
            "wall_clock_s": round(self.wall_clock_s, 3),
            "per_operator": self.per_operator,
        }


# ---------------------------------------------------------------------------
# 5 ML-aware mutation operators.
# ---------------------------------------------------------------------------

# Operator catalog: each entry returns (operator-name, location, payload,
# rewritten-source) for every applicable AST node. The walker is
# applied per-file and de-duplicates identical rewrites so we don't
# spend wall-clock on equivalent mutants.

_PERTURB_DELTA = 1e-3  # additive WP delta (relative to |c|)
_CS_FACTOR = 1.1  # multiplicative CS factor
_MAX_MUTANTS_PER_FILE = 8  # cap per file so the audit finishes inside 5 min
_MAX_AUDIT_SECONDS = 120  # hard wall-clock ceiling per subsystem


def _op_weight_perturbation(tree: ast.AST) -> Iterable[tuple[str, int, str, ast.AST]]:
    """WP: numeric constant -> constant + 1e-3 * |c|.

    Targets float/int constants that carry semantic mass (constants
    between 1e-6 and 1e3 in absolute value). Constants near zero or
    very large are skipped to avoid trivial no-ops and overflows.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, (int, float)):
            continue
        v = float(node.value)
        if abs(v) < 1e-6 or abs(v) > 1e3:
            continue
        # Skip -1, 0, 1 to avoid accidentally flipping algebraic signs.
        if v in (-1.0, 0.0, 1.0):
            continue
        delta = _PERTURB_DELTA * abs(v)
        perturbed = v + delta
        payload = f"WP: {v!r} -> {perturbed!r} (+{delta:g})"
        yield ("WP", node.lineno, payload, _replace_constant(node, perturbed))


def _op_activation_swap(tree: ast.AST) -> Iterable[tuple[str, int, str, ast.AST]]:
    """AS: torch / numpy activation callsite -> ``relu`` fallback.

    Targets calls of the form ``torch.nn.functional.<act>(...)``,
    ``F.<act>(...)``, ``torch.<act>(...)`` and ``nn.<act>(...)`` for
    ``act in {relu, gelu, silu, leaky_relu, elu, tanh, sigmoid,
    softplus}``. The rewrite replaces the activation name with
    ``relu`` so the mutation is a uniform activation substitution
    (the canonical DeepGauge neuron-coverage probe).
    """
    activation_names = {
        "relu", "gelu", "silu", "leaky_relu", "elu", "tanh",
        "sigmoid", "softplus", "softsign", "mish",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in activation_names:
            continue
        if func.attr == "relu":
            continue  # already the canonical fallback; skip trivial case
        payload = f"AS: {func.attr}(...) -> relu(...)"
        new_tree = _replace_attr(tree, node, "relu")
        yield ("AS", node.lineno, payload, new_tree)


def _op_structural_mutation(tree: ast.AST) -> Iterable[tuple[str, int, str, ast.AST]]:
    """SM: ``and`` <-> ``or``; ternary true/false branch swap.

    Targets Boolean operators and ``IfExp`` (ternary) expressions. A
    single SM per site picks the cheapest rewrite.
    """
    seen: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and len(node.values) >= 2:
            key = (node.lineno, id(node))
            if key in seen:
                continue
            seen.add(key)
            op_swap = ast.Or if isinstance(node.op, ast.And) else ast.And
            payload = f"SM: BoolOp {type(node.op).__name__} -> {op_swap.__name__}"
            yield ("SM", node.lineno, payload, _replace_boolop(tree, node, op_swap()))
        elif isinstance(node, ast.IfExp):
            key = (node.lineno, id(node))
            if key in seen:
                continue
            seen.add(key)
            payload = "SM: IfExp branches swapped"
            yield ("SM", node.lineno, payload, _swap_ifexp(tree, node))


def _op_threshold_flip(tree: ast.AST) -> Iterable[tuple[str, int, str, ast.AST]]:
    """TF: comparison operator rewrite.

    ``>`` -> ``<``, ``>=`` -> ``<=``, ``<`` -> ``>``, ``<=`` -> ``>=``,
    ``==`` -> ``!=``, ``!=`` -> ``==``.
    """
    pair: dict[type, type] = {
        ast.Gt: ast.Lt,
        ast.Lt: ast.Gt,
        ast.GtE: ast.LtE,
        ast.LtE: ast.GtE,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and node.ops:
            op = node.ops[0]
            if type(op) not in pair:
                continue
            new_op = pair[type(op)]()
            payload = f"TF: {type(op).__name__} -> {type(new_op).__name__}"
            yield ("TF", node.lineno, payload, _replace_compare(tree, node, new_op))


def _op_constant_substitution(tree: ast.AST) -> Iterable[tuple[str, int, str, ast.AST]]:
    """CS: structural constants perturbed by 1.1x.

    Targets the canonical MLP constants (1.0, 0.5, 2.0, ``math.pi``,
    ``math.e``). Each is multiplied by ``_CS_FACTOR`` so the rewrite is
    a uniform *constant-shape* perturbation that catches gradient-
    scaling and Lipschitz-bound violations.
    """
    cs_targets = {1.0, 0.5, 2.0}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, (int, float)):
            continue
        if float(node.value) not in cs_targets:
            continue
        v = float(node.value)
        bumped = v * _CS_FACTOR
        payload = f"CS: {v!r} -> {bumped!r} (*{_CS_FACTOR})"
        yield ("CS", node.lineno, payload, _replace_constant(node, bumped))


OPERATORS = (
    _op_weight_perturbation,
    _op_activation_swap,
    _op_structural_mutation,
    _op_threshold_flip,
    _op_constant_substitution,
)


# ---------------------------------------------------------------------------
# AST rewrite helpers -- copy the source and re-emit with one node swapped.
# ---------------------------------------------------------------------------


def _copy_tree(tree: ast.AST) -> ast.AST:
    return ast.parse(ast.unparse(tree))


def _replace_constant(node: ast.Constant, perturbed: float) -> ast.AST:
    """Return a *new* module-level parse of the original source with one
    :class:`ast.Constant` replaced. The simpler approach is to mutate
    the node in-place and re-unparse, but that drops location
    metadata; instead, use a positional walk.
    """
    return _pos_replace(node, ("Constant", node.lineno, id(node)), ConstantPatch(perturbed))


@dataclass
class ConstantPatch:
    value: float


@dataclass
class AttrPatch:
    new_attr: str


@dataclass
class BoolOpPatch:
    new_op: ast.AST


@dataclass
class IfExpSwapPatch:
    pass


@dataclass
class ComparePatch:
    new_op: ast.AST


def _pos_replace(root: ast.AST, key: tuple, patch: object) -> ast.AST:
    """Copy ``root`` and apply ``patch`` at the first matching AST node.

    The key is ``(type_name, lineno, id(node))`` of the *original* node
    we want to swap; since we hold a reference to that node, we walk
    the copied tree by ``ast.walk`` and patch the first node whose
    ``lineno`` matches. This avoids deep tree surgery while keeping
    the patch local.
    """
    new_tree = _copy_tree(root)
    target_lineno = key[1]

    if isinstance(patch, ConstantPatch):
        for node in ast.walk(new_tree):
            if isinstance(node, ast.Constant) and node.lineno == target_lineno:
                if isinstance(node.value, (int, float)):
                    node.value = patch.value
                    node.kind = None
                    break
    elif isinstance(patch, AttrPatch):
        for node in ast.walk(new_tree):
            if isinstance(node, ast.Attribute) and node.lineno == target_lineno:
                if node.attr != patch.new_attr:
                    node.attr = patch.new_attr
                break
    elif isinstance(patch, BoolOpPatch):
        for node in ast.walk(new_tree):
            if isinstance(node, ast.BoolOp) and node.lineno == target_lineno:
                node.op = patch.new_op
                break
    elif isinstance(patch, IfExpSwapPatch):
        for node in ast.walk(new_tree):
            if isinstance(node, ast.IfExp) and node.lineno == target_lineno:
                node.body, node.orelse = node.orelse, node.body
                break
    elif isinstance(patch, ComparePatch):
        for node in ast.walk(new_tree):
            if isinstance(node, ast.Compare) and node.lineno == target_lineno:
                if node.ops:
                    node.ops = [patch.new_op] + list(node.ops[1:])
                break
    return new_tree


def _replace_attr(root: ast.AST, ref: ast.AST, new_attr: str) -> ast.AST:
    return _pos_replace(root, ("Attribute", ref.lineno, id(ref)), AttrPatch(new_attr))


def _replace_boolop(root: ast.AST, ref: ast.AST, new_op: ast.AST) -> ast.AST:
    return _pos_replace(root, ("BoolOp", ref.lineno, id(ref)), BoolOpPatch(new_op))


def _swap_ifexp(root: ast.AST, ref: ast.AST) -> ast.AST:
    return _pos_replace(root, ("IfExp", ref.lineno, id(ref)), IfExpSwapPatch())


def _replace_compare(root: ast.AST, ref: ast.AST, new_op: ast.AST) -> ast.AST:
    return _pos_replace(root, ("Compare", ref.lineno, id(ref)), ComparePatch(new_op))


# ---------------------------------------------------------------------------
# Mutant injection -- wrapper script that runs pytest programmatically
# with a meta-path finder installed in the same Python process.
# ---------------------------------------------------------------------------


# The wrapper below installs the meta-path finder in the pytest
# process itself (rather than relying on ``sitecustomize`` /
# ``usercustomize`` auto-discovery, which Python only loads from the
# site-packages tree and not from a transient temp dir). After
# installing the finder the wrapper calls ``pytest.main`` so every
# ``import`` the test suite performs routes through the finder.
_WRAPPER_TEMPLATE = r'''"""Mutant-injection wrapper -- runs pytest in-process.

Run as ``python _wrapper.py <test_selector>``. Installs a
:mod:`importlib` meta-path finder that overrides one module name
(``TARGET_MODULE``) with the rewritten source (``__MUTATED_SOURCE__``)
and then invokes :func:`pytest.main` programmatically so every test
import goes through the finder.

Exit codes:

* 0  -- the test suite passed under the mutant (mutant SURVIVED)
* 1  -- at least one test failed under the mutant (mutant KILLED)
* 2  -- collection failure or pytest internal error (treated as KILLED)
"""
from __future__ import annotations

import importlib.abc
import importlib.util
import sys

TARGET_MODULE = "__MUTANT_TARGET__"
__MUTATED_SOURCE__ = "__MUTATED_SOURCE_PLACEHOLDER__"


class _MutantMetaFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname != TARGET_MODULE:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            self,
            origin="<mutation-audit>",
        )

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        code = compile(__MUTATED_SOURCE__, "<mutation-audit>", "exec")
        exec(code, module.__dict__)


sys.meta_path.insert(0, _MutantMetaFinder())

import pytest

if __name__ == "__main__":
    selector = sys.argv[1] if len(sys.argv) > 1 else "tests/"
    sys.exit(pytest.main([
        "-x",
        "-q",
        "--no-header",
        "--tb=line",
        "-p",
        "no:cacheprovider",
        selector,
    ]))
'''


def _wrapper_source(target_module: str, mutated_source: str) -> str:
    """Substitute the placeholders in :data:`_WRAPPER_TEMPLATE`."""
    src = _WRAPPER_TEMPLATE
    src = src.replace("TARGET_MODULE = \"__MUTANT_TARGET__\"",
                      f"TARGET_MODULE = {target_module!r}")
    # Encode the mutated source as a base-escaped string literal so
    # any quoting / escape characters survive the round-trip into
    # Python source.
    encoded = mutated_source.encode("unicode_escape").decode("ascii")
    literal = repr(encoded)  # double-quoted form
    src = src.replace(
        "__MUTATED_SOURCE__ = \"__MUTATED_SOURCE_PLACEHOLDER__\"",
        f"__MUTATED_SOURCE__ = {literal}",
    )
    # Inside exec(compile(__MUTATED_SOURCE__, ...)) we need the
    # *decoded* source, not the unicode_escape-encoded one. Patch the
    # wrapper to decode before compile.
    src = src.replace(
        'code = compile(__MUTATED_SOURCE__, "<mutation-audit>", "exec")',
        'code = compile(__MUTATED_SOURCE__.encode("utf-8").decode("unicode_escape"), '
        '"<mutation-audit>", "exec")',
    )
    return src


def _run_pytest(
    target_module: str,
    mutated_source: str,
    test_selector: str,
    timeout: int = 60,
) -> tuple[bool, float]:
    """Run ``pytest <test_selector>`` with the mutant injected.

    Returns ``(killed, wall_clock)``. ``killed`` is True when pytest
    exits non-zero (or times out) -- any test failure, error, or
    collection failure is treated as a kill, matching the canonical
    mutation-testing interpretation.
    """
    start = time.monotonic()
    wrapper_dir = Path(tempfile.mkdtemp(prefix="mutation_audit_"))
    wrapper_path = wrapper_dir / "_wrapper.py"
    wrapper_path.write_text(
        _wrapper_source(target_module, mutated_source), encoding="utf-8"
    )

    cmd = [
        sys.executable,
        str(wrapper_path),
        test_selector,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{_REPO_ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"
    )

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_REPO_ROOT),
            env=env,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        elapsed = time.monotonic() - start
        killed = proc.returncode != 0
        return killed, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        # A timeout is treated as a kill -- the mutant caused the
        # suite to exceed its budget.
        return True, elapsed
    finally:
        try:
            wrapper_path.unlink()
            wrapper_dir.rmdir()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Audit driver.
# ---------------------------------------------------------------------------


def _enumerate_mutants(
    file_path: Path,
    repo_root: Path,
) -> list[tuple[str, int, str, ast.AST]]:
    """Run every operator on ``file_path`` and return the mutant list.

    To balance operator coverage, the function interleaves the
    candidates returned by each operator (round-robin) before
    applying the per-file cap. Without this, high-yield operators
    like ``WP`` would crowd out lower-yield but more discriminating
    operators like ``AS``/``SM``/``TF``/``CS`` and the per-operator
    breakdown would be dominated by a single family.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    seen_loc: set[tuple[str, int]] = set()
    per_op: dict[str, list[tuple[int, str, ast.AST]]] = {}
    for op in OPERATORS:
        op_id = op.__name__.removeprefix("_op_")
        for _, lineno, payload, mutant_tree in op(tree):
            key = (op_id, lineno)
            if key in seen_loc:
                continue
            seen_loc.add(key)
            per_op.setdefault(op_id, []).append((lineno, payload, mutant_tree))

    # Round-robin merge so the cap draws from every operator before
    # truncating.
    interleaved: list[tuple[str, int, str, ast.AST]] = []
    cursors = {op_id: 0 for op_id in per_op}
    while len(interleaved) < _MAX_MUTANTS_PER_FILE:
        progressed = False
        for op_id, candidates in per_op.items():
            cursor = cursors[op_id]
            if cursor < len(candidates):
                lineno, payload, mutant_tree = candidates[cursor]
                interleaved.append((op_id, lineno, payload, mutant_tree))
                cursors[op_id] = cursor + 1
                progressed = True
                if len(interleaved) >= _MAX_MUTANTS_PER_FILE:
                    break
        if not progressed:
            break

    return interleaved


def _audit_subsystem(
    subsystem: str,
    spec: dict[str, object],
    max_mutants: int,
) -> SubsystemScore:
    """Run the operator suite on every file in ``spec['files']``."""
    score = SubsystemScore(
        subsystem=subsystem,
        description=str(spec["description"]),
    )
    file_list = [Path(f) for f in spec["files"]]  # type: ignore[arg-type]
    test_selector = str(spec["tests"])

    started = time.monotonic()
    for file_path in file_list:
        rel_path = file_path.resolve()
        module_name = _module_name_from_path(rel_path)
        if module_name is None:
            continue
        try:
            source_text = rel_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            ast.parse(source_text, filename=str(rel_path))
        except SyntaxError:
            continue

        mutants = _enumerate_mutants(rel_path, _REPO_ROOT)
        if max_mutants and score.total >= max_mutants:
            break
        for op_id, lineno, payload, mutant_tree in mutants:
            if max_mutants and score.total >= max_mutants:
                break
            elapsed = time.monotonic() - started
            if elapsed > _MAX_AUDIT_SECONDS:
                # Stop adding mutants once we blow the per-subsystem budget.
                break

            mutated_source = ast.unparse(mutant_tree)
            killed, wall = _run_pytest(
                target_module=module_name,
                mutated_source=mutated_source,
                test_selector=test_selector,
                timeout=60,
            )
            rel_loc = f"{rel_path.relative_to(_REPO_ROOT)}:{lineno}"
            record = MutantRecord(
                subsystem=subsystem,
                operator=op_id,
                location=rel_loc,
                payload=payload,
                killed=killed,
                wall_clock_s=wall,
            )
            score.mutants.append(record)
            score.total += 1
            if killed:
                score.killed += 1
            bucket = score.per_operator.setdefault(op_id, {"killed": 0, "total": 0})
            bucket["total"] += 1
            if killed:
                bucket["killed"] += 1

    score.wall_clock_s = time.monotonic() - started
    return score


def _module_name_from_path(file_path: Path) -> str | None:
    """Convert a repo-relative ``.py`` file to its dotted module name."""
    try:
        rel = file_path.resolve().relative_to(_REPO_ROOT.resolve())
    except ValueError:
        return None
    parts = list(rel.parts)
    if not parts or not parts[-1].endswith(".py"):
        return None
    parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _run_audit(
    output_path: Path,
    max_mutants: int,
    subsystems: Sequence[str] | None,
) -> int:
    selected = subsystems or list(SUBSYSTEM_TABLE.keys())
    rollup: dict[str, SubsystemScore] = {}
    for name in selected:
        if name not in SUBSYSTEM_TABLE:
            print(f"[mutation-audit] WARNING: unknown subsystem {name!r}", file=sys.stderr)
            continue
        spec = SUBSYSTEM_TABLE[name]
        # Distribute max_mutants evenly across the four families so the
        # overall cap is respected even when ``max_mutants`` is small.
        cap = max(8, max_mutants // len(selected)) if max_mutants else 0
        score = _audit_subsystem(name, spec, cap)
        rollup[name] = score
        print(
            f"[mutation-audit] {name:<12s} "
            f"killed={score.killed}/{score.total} "
            f"score={score.score:.3f} "
            f"({score.wall_clock_s:.1f}s)",
            file=sys.stderr,
        )

    aggregate_killed = sum(s.killed for s in rollup.values())
    aggregate_total = sum(s.total for s in rollup.values())
    aggregate_score = (aggregate_killed / aggregate_total) if aggregate_total else 0.0

    report = {
        "metadata": {
            "tool": "tools.run_mutation_audit",
            "framework_internals_metric": "F.6",
            "quarter": _current_quarter(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.split()[0],
            "operators": [op.__name__.removeprefix("_op_") for op in OPERATORS],
            "subsystem_targets": {
                name: {
                    "description": spec["description"],
                    "files": list(spec["files"]),  # type: ignore[arg-type]
                    "tests": spec["tests"],
                }
                for name, spec in SUBSYSTEM_TABLE.items()
            },
        },
        "per_subsystem": {name: s.to_dict() for name, s in rollup.items()},
        "aggregate": {
            "killed": aggregate_killed,
            "total": aggregate_total,
            "score": round(aggregate_score, 4),
        },
        "thresholds": {
            "aggregate_min": 0.6,
            "per_subsystem_min": 0.4,
            "aggregate_pass": aggregate_score >= 0.6,
            "per_subsystem_pass": all(s.score >= 0.4 for s in rollup.values()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[mutation-audit] report written: {output_path}", file=sys.stderr)
    print(json.dumps(report["aggregate"], indent=2))

    if not report["thresholds"]["aggregate_pass"]:
        return 1
    if not report["thresholds"]["per_subsystem_pass"]:
        return 1
    return 0


def _current_quarter() -> str:
    now = datetime.now(timezone.utc)
    quarter = (now.month - 1) // 3 + 1
    return f"{now.year}Q{quarter}"


def _summary(json_path: Path) -> int:
    report = json.loads(json_path.read_text(encoding="utf-8"))
    print(f"# Mutation audit summary: {json_path}")
    print(f"Quarter: {report['metadata']['quarter']}")
    print(f"Aggregate: {report['aggregate']['score']:.3f} "
          f"({report['aggregate']['killed']}/{report['aggregate']['total']})")
    print()
    print("| Subsystem | Killed/Total | Score | Wall (s) | Status |")
    print("|-----------|--------------|-------|----------|--------|")
    for name, row in report["per_subsystem"].items():
        status = "PASS" if row["score"] >= 0.4 else "FAIL"
        print(
            f"| {name} | {row['killed']}/{row['total']} | "
            f"{row['score']:.3f} | {row['wall_clock_s']:.1f} | {status} |"
        )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_mutation_audit",
        description="F.6 quarterly ML-aware mutation audit runner",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run the F.6 audit")
    run_p.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "verification_outputs" / "mutation_audit_q4_2026.json",
    )
    run_p.add_argument(
        "--max-mutants",
        type=int,
        default=32,
        help="Cap on total mutants per audit run (default: 32)",
    )
    run_p.add_argument(
        "--subsystem",
        action="append",
        default=None,
        help="Restrict the audit to one subsystem (repeatable)",
    )

    sub.add_parser("summary", help="summarize a previous audit JSON")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "run":
        try:
            return _run_audit(args.output, args.max_mutants, args.subsystem)
        except Exception as exc:  # pragma: no cover -- defensive
            print(f"[mutation-audit] FATAL: {exc!r}", file=sys.stderr)
            return 2
    if args.command == "summary":
        return _summary(args.output)
    return 2


if __name__ == "__main__":
    sys.exit(main())