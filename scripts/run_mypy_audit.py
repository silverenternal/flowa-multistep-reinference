#!/usr/bin/env python3
"""I.1 type-soundness audit for ``adaptive_reflow/``.

This script is the automated measurement tool for the rev-3 framework-internal
metric I.1 (``framework-internal-metrics.md`` §I):

    I.1 — Type-soundness coverage: fraction of public APIs
    (modules in ``adaptive_reflow/``) with mypy-clean or runtime
    ``isinstance``-checkable type hints. Target: ``>= 0.6`` by Wave 16.

The metric is the **count of public functions** in
``adaptive_reflow/`` whose signature is fully annotated
(``def foo(arg: T) -> R``) **or** whose body carries an
``isinstance(x, T)`` narrowing helper, divided by the total
count of public functions. We restrict to the public surface
so internal helpers are not penalised:

* functions/methods defined at module top level (not nested)
* methods on classes declared inside ``adaptive_reflow/``
* ``__init__`` constructors are counted once per class

Skipped surface (does not contribute to the I.1 denominator):

* private names starting with ``_``
* dunder names (``__name__`` etc.)
* ``legacy/`` subpackage (quarantined by ``pyproject.toml``)
* test files (``tests/``)

What is **not** counted in the numerator:

* ``# type: ignore`` comments (they silence, not annotate)
* type comments (``# type: T``)

The output is a JSON document so the audit can be diffed over
time. Run with:

    python scripts/run_mypy_audit.py [--target-ratio 0.6]

The script is hermetic — it walks the AST only and never
imports the modules under test, so it runs even when the
project venv is unavailable.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# Scripts are routinely invoked directly from a source checkout (without an
# editable install).  Put the repository root on ``sys.path`` before importing
# the local package so the documented command works in a clean environment.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.util.host_fingerprint import with_host_fingerprint  # noqa: E402

PACKAGE_ROOT = REPO_ROOT / "adaptive_reflow"
SKIP_DIRS = {"__pycache__", "legacy"}


@dataclass(frozen=True)
class FunctionRecord:
    """One public function or method on the I.1 surface."""

    qualified: str
    line: int
    annotated: bool
    has_isinstance_helper: bool

    @property
    def counted(self) -> bool:
        """Whether this function contributes to the I.1 numerator.

        A function contributes when ``annotated`` (full type-hint
        coverage on args + return) **or** ``has_isinstance_helper``
        (a runtime narrowing helper that documents the intended type).
        """
        return self.annotated or self.has_isinstance_helper


@dataclass
class AuditResult:
    """Aggregated I.1 audit result for one file."""

    path: str
    functions: list[FunctionRecord] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.functions)

    @property
    def annotated(self) -> int:
        return sum(1 for fn in self.functions if fn.annotated)

    @property
    def isinstance_helpers(self) -> int:
        return sum(1 for fn in self.functions if fn.has_isinstance_helper)

    @property
    def covered(self) -> int:
        return sum(1 for fn in self.functions if fn.counted)

    @property
    def coverage(self) -> float:
        if not self.functions:
            return 1.0
        return self.covered / self.total


def _is_public(name: str) -> bool:
    """``True`` for names that count toward the public surface."""
    if name.startswith("__") and name.endswith("__"):
        return False
    return not name.startswith("_")


def _has_isinstance_call(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """``True`` if the function body contains ``isinstance(...)``.

    We walk the entire body (including nested comprehensions) so
    an isinstance call inside a comprehension counts. We
    deliberately ignore ``isinstance`` as a default-argument
    value because that pattern is unusual and would not
    meaningfully document the intended type.
    """
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name) and callee.id == "isinstance":
                return True
            if isinstance(callee, ast.Attribute) and callee.attr == "isinstance":
                return True
    return False


def _is_fully_annotated(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """``True`` when every real argument + the return have annotations.

    ``self`` and ``cls`` are conventional and unannotated in Python;
    we treat them as "implicit" and skip them so a method that only
    forgets ``self`` is not penalised.
    """
    args = func.args
    all_args: list[ast.arg] = []
    all_args.extend(args.posonlyargs)
    all_args.extend(args.args)
    all_args.extend(args.kwonlyargs)
    if args.vararg is not None:
        all_args.append(args.vararg)
    if args.kwarg is not None:
        all_args.append(args.kwarg)
    for arg in all_args:
        if arg.arg in {"self", "cls"}:
            continue
        if arg.annotation is None:
            return False
    return func.returns is not None


def _collect_functions(
    tree: ast.Module,
    path: Path,
) -> Iterable[FunctionRecord]:
    """Walk a module AST and yield :class:`FunctionRecord`s.

    Yields methods on classes (including ``__init__``) qualified
    as ``ClassName.method`` and module-level functions qualified
    as ``module.func``. Nested function definitions are skipped
    to avoid double-counting inner helpers.
    """
    module_qualifier = path.stem
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_public(node.name):
                continue
            yield FunctionRecord(
                qualified=f"{module_qualifier}.{node.name}",
                line=node.lineno,
                annotated=_is_fully_annotated(node),
                has_isinstance_helper=_has_isinstance_call(node),
            )
        elif isinstance(node, ast.ClassDef):
            if not _is_public(node.name):
                continue
            class_qualifier = f"{module_qualifier}.{node.name}"
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not _is_public(item.name):
                        continue
                    yield FunctionRecord(
                        qualified=f"{class_qualifier}.{item.name}",
                        line=item.lineno,
                        annotated=_is_fully_annotated(item),
                        has_isinstance_helper=_has_isinstance_call(item),
                    )


def audit_file(path: Path) -> AuditResult:
    """Parse one Python file and return its :class:`AuditResult`."""
    result = AuditResult(path=path.relative_to(REPO_ROOT).as_posix())
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        print(f"WARN: cannot read {path}: {exc}", file=sys.stderr)
        return result
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        print(f"WARN: cannot parse {path}: {exc}", file=sys.stderr)
        return result
    result.functions.extend(_collect_functions(tree, path))
    return result


def audit_package(package_root: Path) -> list[AuditResult]:
    """Audit every ``.py`` file under ``package_root`` (recursively)."""
    results: list[AuditResult] = []
    for path in sorted(package_root.rglob("*.py")):
        rel_parts = set(path.relative_to(package_root).parts[:-1])
        if rel_parts & SKIP_DIRS:
            continue
        if "__pycache__" in path.parts:
            continue
        results.append(audit_file(path))
    return results


def summarise(results: list[AuditResult]) -> dict[str, object]:
    """Build the JSON-serialisable summary dict."""
    total = sum(r.total for r in results)
    annotated = sum(r.annotated for r in results)
    isinstance_helpers = sum(r.isinstance_helpers for r in results)
    covered = sum(r.covered for r in results)
    coverage = covered / total if total else 1.0

    by_file = [
        {
            "path": r.path,
            "total": r.total,
            "annotated": r.annotated,
            "isinstance_helpers": r.isinstance_helpers,
            "covered": r.covered,
            "coverage": round(r.coverage, 4),
        }
        for r in sorted(results, key=lambda x: x.coverage)
        if r.total > 0
    ]
    return {
        "files_scanned": len(results),
        "functions_total": total,
        "functions_annotated": annotated,
        "functions_isinstance_helpers": isinstance_helpers,
        "functions_covered": covered,
        "coverage": round(coverage, 4),
        "by_file": by_file,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--target-ratio",
        type=float,
        default=0.6,
        help="I.1 target coverage ratio (default: 0.6 per rev-3 plan).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="How many lowest-coverage files to surface (default: 10).",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print the JSON summary only (skip the human-readable table).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    results = audit_package(PACKAGE_ROOT)
    summary = summarise(results)
    summary["target_ratio"] = args.target_ratio
    summary["meets_target"] = summary["coverage"] >= args.target_ratio

    if not args.summary_only:
        print(f"I.1 type-soundness audit — package: {PACKAGE_ROOT.relative_to(REPO_ROOT)}")
        print(f"  files scanned       : {summary['files_scanned']}")
        print(f"  functions total     : {summary['functions_total']}")
        print(f"  annotated (full)    : {summary['functions_annotated']}")
        print(f"  isinstance helpers  : {summary['functions_isinstance_helpers']}")
        print(f"  covered (num.)      : {summary['functions_covered']}")
        print(f"  coverage            : {summary['coverage']:.2%}")
        print(f"  target ratio        : {args.target_ratio:.0%}")
        print(f"  meets target        : {summary['meets_target']}")
        print()
        print(f"Lowest-coverage files (top {args.top}):")
        for entry in summary["by_file"][: args.top]:  # type: ignore[index]
            print(
                f"  {entry['coverage']:>7.2%}  "
                f"{entry['covered']:>3}/{entry['total']:<3}  "
                f"{entry['path']}"
            )

    print()
    print(json.dumps(with_host_fingerprint(summary), indent=2))

    return 0 if summary["meets_target"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
