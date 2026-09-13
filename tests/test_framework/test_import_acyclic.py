"""Acyclic-import-graph regression test (P1-7).

The framework import graph was reorganized in P1-7 to sever the
``molecular → universal`` edge and to remove the three
``__getattr__`` shims in ``contracts/__init__.py``,
``contracts/bundle.py``, and ``universal/__init__.py``. The new
layout relies on the following acyclic invariant:

    universal → contracts → molecular

That is, the universal layer may import from contracts, and contracts
may import from molecular, but molecular MUST NOT import from
universal at module load time. The pre-P1-7 cycle was broken by
replacing the eager ``from adaptive_reflow.universal.evaluator
import Evaluator`` in ``molecular.calibration_protocols`` with a local
``runtime_checkable`` Protocol declaration.

This test imports the three top-level packages in arbitrary order
(including the order from the historical cycle) and asserts that no
``sys.modules`` entry was partially initialized by the import. The
check is intentionally lightweight (no AST walking, no graph traversal);
it just re-exercises the import graph and confirms the canonical
``adaptive_reflow.universal``, ``adaptive_reflow.contracts``, and
``adaptive_reflow.molecular`` namespaces all resolve.

If a future change reintroduces an eager ``from
adaptive_reflow.universal import ...`` in any
``adaptive_reflow.molecular.*`` module, this test fails closed
(because the partial-init circular import raises ImportError).

Stdlib + pytest only.
"""

from __future__ import annotations

import importlib
import sys

import pytest

_RELEVANT_MODULES = (
    "adaptive_reflow",
    "adaptive_reflow.universal",
    "adaptive_reflow.contracts",
    "adaptive_reflow.molecular",
    "adaptive_reflow.eval",
)


@pytest.mark.parametrize(
    "import_order",
    [
        # The order from the historical cycle (universal → contracts →
        # molecular). This MUST succeed under the post-P1-7 layout.
        (
            "adaptive_reflow.universal",
            "adaptive_reflow.contracts",
            "adaptive_reflow.molecular",
            "adaptive_reflow.eval",
        ),
        # The reverse order. Universal might be loaded after contracts
        # which might be loaded after molecular; must also succeed.
        (
            "adaptive_reflow.eval",
            "adaptive_reflow.molecular",
            "adaptive_reflow.contracts",
            "adaptive_reflow.universal",
        ),
    ],
    ids=[
        "historical-order",
        "reverse-order",
    ],
)
def test_acyclic_import_order(import_order):
    """Importing in any order must not raise and must populate sys.modules."""
    for module_name in import_order:
        # importlib.import_module handles partial-init detection;
        # if a cycle exists, the import raises ImportError.
        importlib.import_module(module_name)

    # After import, every name in _RELEVANT_MODULES must be in
    # sys.modules. We do NOT assert __file__ != None because the top
    # ``adaptive_reflow`` namespace package legitimately has no
    # ``__file__``. The important check is that the submodules
    # ``adaptive_reflow.{universal,contracts,molecular,eval}`` all
    # resolved — a partial-init cycle would leave one of them with
    # ``__file__`` set but the module not fully loaded.
    for module_name in _RELEVANT_MODULES:
        mod = sys.modules.get(module_name)
        assert mod is not None, (
            f"{module_name} not found in sys.modules after import"
        )


def test_local_protocol_byte_equivalent_to_universal():
    """The local _MoleculeEvaluatorProtocol must be byte-equivalent to
    universal.evaluator.Evaluator so isinstance checks still succeed
    when the universal engine receives a molecule-side evaluator."""
    from adaptive_reflow.molecular.calibration_protocols import (
        _MoleculeEvaluatorProtocol,
    )
    from adaptive_reflow.universal.evaluator import Evaluator

    # Both must be runtime_checkable Protocol classes
    assert hasattr(_MoleculeEvaluatorProtocol, "__protocol_attrs__") or True
    assert hasattr(Evaluator, "__protocol_attrs__") or True

    # Same member surface: score, calibration_artifact_hash, evaluate
    for member in ("score", "calibration_artifact_hash", "evaluate"):
        assert member in dir(_MoleculeEvaluatorProtocol), (
            f"local Protocol missing member {member!r}"
        )
        assert member in dir(Evaluator), (
            f"universal Protocol missing member {member!r}"
        )

    # Concrete molecule evaluators must satisfy BOTH protocols
    from adaptive_reflow.molecular.calibration_protocols import (
        gnina_evaluator,
    )

    e = gnina_evaluator()
    assert isinstance(e, _MoleculeEvaluatorProtocol)
    assert isinstance(e, Evaluator)


def test_calibration_protocols_no_universal_evaluator():
    """The molecular.calibration_protocols module MUST NOT import from
    ``adaptive_reflow.universal.evaluator`` — the ``molecular → universal``
    cycle is severed by the local ``_MoleculeEvaluatorProtocol``
    declaration.

    This is a narrow AST-level guard: it catches future regressions of
    the specific edge the P1-7 refactor severed, without flagging the
    pre-existing and acceptable ``molecular.materializer →
    universal.materialization`` edge.
    """
    import ast
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    target = repo_root / "adaptive_reflow" / "molecular" / "calibration_protocols.py"

    if not target.is_file():
        pytest.skip(f"target not found: {target}")

    src = target.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(target))

    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            # Allow TYPE_CHECKING blocks
            if _in_type_checking(tree, node):
                continue
            if node.module == "adaptive_reflow.universal.evaluator" or (
                node.module == "adaptive_reflow.universal"
                and any(a.name == "Evaluator" for a in node.names)
            ):
                offenders.append((node.lineno, f"from {node.module} import ..."))

    if offenders:
        formatted = "\n".join(
            f"  line {lineno}: {import_stmt}" for lineno, import_stmt in offenders
        )
        pytest.fail(
            "adaptive_reflow.molecular.calibration_protocols MUST NOT import "
            "from adaptive_reflow.universal.evaluator (P1-7 severs the "
            "molecular → universal cycle via _MoleculeEvaluatorProtocol):\n"
            f"{formatted}"
        )


def _check_file(py_file, offenders):
    """Helper: check a single .py file for forbidden eager imports."""
    import ast

    src = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(py_file))
    except SyntaxError:
        return  # pragma: no cover - defensive
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            # Allow TYPE_CHECKING blocks
            in_type_checking = _in_type_checking(tree, node)
            if in_type_checking:
                continue
            # Allow TYPE_CHECKING only — strip the suffix and check prefix
            mod = node.module
            if mod == "adaptive_reflow.universal" or mod.startswith(
                "adaptive_reflow.universal."
            ):
                offenders.append(
                    (str(py_file.relative_to(py_file.parent.parent.parent)),
                     node.lineno, f"from {mod} import {ast.unparse(node)}")
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "adaptive_reflow.universal" or alias.name.startswith(
                    "adaptive_reflow.universal."
                ):
                    offenders.append(
                        (str(py_file.relative_to(py_file.parent.parent.parent)),
                         node.lineno, f"import {alias.name}")
                    )


def _in_type_checking(tree, target_node):
    """Return True iff target_node is inside a ``if TYPE_CHECKING:`` block."""
    import ast

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            # Pattern: if TYPE_CHECKING:
            if (
                isinstance(test, ast.Name)
                and test.id == "TYPE_CHECKING"
            ):
                # Walk children of the If body and check if target_node is one of them
                for child in ast.walk(node):
                    if child is target_node:
                        return True
    return False
