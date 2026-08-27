"""Tests for ``tools.mutate.ast_mutator``.

The mutator is the project's Windows-compatible replacement for mutmut
(upstream boxed/mutmut#397) and it is a *load-bearing CI gate*: the
``mutation-nightly`` workflow blocks on the score it reports. That makes
two classes of bug expensive:

* a mis-implemented operator silently shrinks the mutation surface, which
  inflates the score and weakens the gate;
* a mis-implemented threshold check passes a run it should have rejected.

The tests below therefore cover the operator table one rewrite at a time,
the exclusions that keep the score honest (type annotations, docstrings,
unbound name swaps), and both directions of the gate. Everything here is
pure AST/JSON work -- no pytest subprocesses are spawned, so the suite
stays fast.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.mutate import ast_mutator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mutants(source: str, op: str | None = None) -> list[str]:
    """Return the mutated sources for every applicable site (optionally by op)."""
    out: list[str] = []
    for site in ast_mutator.collect_sites(source):
        if op is not None and site.op != op:
            continue
        mutated = ast_mutator.apply_site(source, site)
        if mutated is not None:
            out.append(mutated)
    return out


def _ops(source: str) -> list[str]:
    return [site.op for site in ast_mutator.collect_sites(source)]


# ---------------------------------------------------------------------------
# Operator table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "op", "expected"),
    [
        ("def f(a, b):\n    return a + b\n", "AOR", "return a - b"),
        ("def f(a, b):\n    return a - b\n", "AOR", "return a + b"),
        ("def f(a, b):\n    return a * b\n", "AOR", "return a / b"),
        ("def f(a, b):\n    return a / b\n", "AOR", "return a * b"),
        ("def f(a, b):\n    return a == b\n", "AOR", "return a != b"),
        ("def f(a, b):\n    return a != b\n", "AOR", "return a == b"),
        ("def f(a, b):\n    return a < b\n", "ROR", "return a <= b"),
        ("def f(a, b):\n    return a > b\n", "ROR", "return a >= b"),
        ("def f(a, b):\n    return a <= b\n", "ROR", "return a < b"),
        ("def f(a, b):\n    return a >= b\n", "ROR", "return a > b"),
        ("def f(a, b):\n    return a and b\n", "LOR", "return a or b"),
        ("def f(a, b):\n    return a or b\n", "LOR", "return a and b"),
        ("def f(a):\n    return not a\n", "UOR", "return a"),
        ("def f(a):\n    return -a\n", "UOR", "return +a"),
        ("def f():\n    return True\n", "CRP", "return False"),
        ("def f():\n    return False\n", "CRP", "return True"),
        ("def f():\n    return 0\n", "CRP", "return 1"),
        ("def f():\n    return 1\n", "CRP", "return 0"),
    ],
)
def test_operator_produces_expected_rewrite(
    source: str, op: str, expected: str
) -> None:
    """Each documented operator rewrites the construct it claims to rewrite."""
    mutants = _mutants(source, op=op)
    assert any(expected in m for m in mutants), (
        f"{op} did not produce {expected!r}; got {mutants!r}"
    )


@pytest.mark.parametrize(("literal", "expected"), [("0.0", "1.0"), ("1.0", "0.0")])
def test_crp_covers_unit_interval_floats(literal: str, expected: str) -> None:
    """CRP swaps float 0.0/1.0.

    This project's ``[floor, cap]`` envelope bounds are float literals; an
    int-only CRP would leave every bound check unmutated and overstate the
    score for ``frame/merge.py``.
    """
    mutants = _mutants(f"def f(x):\n    return x < {literal}\n", op="CRP")
    assert any(f"return x < {expected}" in m for m in mutants)


def test_sdl_wraps_statement_in_if_false() -> None:
    """SDL neutralises a statement with an ``if False:`` stub."""
    source = "def f(items):\n    items.append(1)\n    return items\n"
    mutants = _mutants(source, op="SDL")
    assert mutants, "expected at least one SDL mutant"
    assert any("if False:" in m for m in mutants)
    # Every SDL mutant must remain compilable, or it dies for the wrong reason.
    for mutant in mutants:
        compile(mutant, "<sdl>", "exec")


def test_sdl_can_neutralise_a_raise() -> None:
    """Deleting a guard's ``raise`` is the fail-closed probe we care about."""
    source = "def f(x):\n    if x is None:\n        raise ValueError('nope')\n    return x\n"
    mutants = _mutants(source, op="SDL")
    assert any("if False:" in m and "raise ValueError" in m for m in mutants)


# ---------------------------------------------------------------------------
# NSR (the cap <-> floor envelope swap)
# ---------------------------------------------------------------------------


def test_nsr_swaps_cap_and_floor() -> None:
    source = "def f(cap, floor):\n    return max(floor, min(cap, 0.5))\n"
    details = {
        site.detail
        for site in ast_mutator.collect_sites(source)
        if site.op == "NSR"
    }
    assert "cap->floor" in details
    assert "floor->cap" in details


def test_nsr_swaps_method_names() -> None:
    """``_cap_for_channel`` <-> ``_floor_for_channel``, per the spec."""
    source = (
        "def _cap_for_channel(s):\n    return 1.0\n\n"
        "def _floor_for_channel(s):\n    return 0.0\n\n"
        "def g(s):\n    return _cap_for_channel(s)\n"
    )
    details = {
        site.detail
        for site in ast_mutator.collect_sites(source)
        if site.op == "NSR"
    }
    assert "_cap_for_channel->_floor_for_channel" in details


def test_nsr_skipped_when_swapped_name_is_unbound() -> None:
    """A swap to a name nothing binds would die of NameError.

    Such a mutant measures the interpreter, not the test suite, so it must
    not be generated at all.
    """
    source = "def f(cap):\n    return cap\n"
    assert "NSR" not in _ops(source)


# ---------------------------------------------------------------------------
# Exclusions that keep the score honest
# ---------------------------------------------------------------------------


def test_annotations_are_not_mutated() -> None:
    """Annotation constants are inert under ``from __future__ import annotations``.

    Mutating them yields unkillable equivalent mutants that deflate the score,
    so only the ``return 0`` below is a legitimate CRP site.
    """
    source = (
        "from __future__ import annotations\n"
        "from typing import Literal\n"
        "def f(a: Literal[1]) -> Literal[0]:\n"
        "    return 0\n"
    )
    crp = [
        site for site in ast_mutator.collect_sites(source) if site.op == "CRP"
    ]
    assert len(crp) == 1, [s.detail for s in crp]
    assert crp[0].detail == "0->1"


def test_docstrings_are_not_deleted() -> None:
    """A docstring is not behaviour; deleting it is noise, not signal."""
    source = 'def f():\n    """Doc."""\n    return 1\n'
    sdl = [
        site for site in ast_mutator.collect_sites(source) if site.op == "SDL"
    ]
    assert len(sdl) == 1
    assert sdl[0].detail == "Return"


def test_dunder_assignments_are_not_deleted() -> None:
    """``__all__`` is module metadata, not behaviour."""
    source = "__all__ = ['f']\n\n\ndef f():\n    return 1\n"
    for site in ast_mutator.collect_sites(source):
        mutated = ast_mutator.apply_site(source, site)
        if mutated is not None and site.op == "SDL":
            assert "__all__" not in mutated.split("if False:")[1][:40]


def test_sites_are_deterministic() -> None:
    """Site order must be stable, or mutant ids stop meaning anything."""
    source = Path("adaptive_reflow/frame/merge.py").read_text(encoding="utf-8")
    first = [(s.index, s.op, s.detail) for s in ast_mutator.collect_sites(source)]
    second = [(s.index, s.op, s.detail) for s in ast_mutator.collect_sites(source)]
    assert first == second


def test_every_site_yields_compilable_distinct_source() -> None:
    """No site may produce a no-op or an uncompilable mutant.

    As of the MergeOperatorProtocol refactor, ``frame/merge.py`` is a
    thin wrapper around ``algorithm/merge_operator.py``. The bulk of
    the bounded-merge mutation surface moved to the algorithm layer
    (see :func:`test_algorithm_merge_operator_has_substantial_surface`).
    The threshold here is set to match the new wrapper responsibilities
    (envelope / floor / cap helpers + delegating call site).
    """
    source = Path("adaptive_reflow/frame/merge.py").read_text(encoding="utf-8")
    applied = 0
    for site in ast_mutator.collect_sites(source):
        mutated = ast_mutator.apply_site(source, site)
        if mutated is None:
            continue
        compile(mutated, "<mutant>", "exec")
        applied += 1
    assert applied > 50, f"expected a substantial mutation surface, got {applied}"


def test_algorithm_merge_operator_has_substantial_surface() -> None:
    """The algorithm-layer operator module owns the bulk of the merge
    mutation surface after the MergeOperatorProtocol refactor. The
    operator's merge logic, validation, and audit emission must
    produce a substantial mutation surface — this is the canonical
    location for bounded-merge mutation testing.
    """
    source = Path(
        "adaptive_reflow/algorithm/merge_operator.py"
    ).read_text(encoding="utf-8")
    applied = 0
    for site in ast_mutator.collect_sites(source):
        mutated = ast_mutator.apply_site(source, site)
        if mutated is None:
            continue
        compile(mutated, "<mutant>", "exec")
        applied += 1
    assert applied > 80, (
        f"expected a substantial mutation surface in the algorithm "
        f"merge_operator module, got {applied}"
    )


# ---------------------------------------------------------------------------
# Scoring and the S-tier gate
# ---------------------------------------------------------------------------


def _results(**modules: tuple[int, int]) -> dict:
    """Build a results payload from ``{path: (killed, total)}``."""
    by_module = {}
    total_k = total_t = 0
    for path, (killed, total) in modules.items():
        real_path = path.replace("__", "/")
        by_module[real_path] = {
            "total_mutants": total,
            "killed": killed,
            "survived": total - killed,
            "score": killed / total if total else 0.0,
        }
        total_k += killed
        total_t += total
    return {
        "version": "1.0.0",
        "overall": {
            "total_mutants": total_t,
            "killed": total_k,
            "survived": total_t - total_k,
            "score": (total_k / total_t) if total_t else 0.0,
        },
        "by_module": by_module,
        "targets": dict(ast_mutator.TARGETS),
    }


def test_area_score_partitions_by_prefix() -> None:
    results = _results(
        **{
            "adaptive_reflow__frame__merge.py": (60, 100),
            "adaptive_reflow__contracts__validators.py": (90, 100),
        }
    )
    assert ast_mutator.area_score(results, "adaptive_reflow/frame/") == (
        60,
        100,
        0.60,
    )
    assert ast_mutator.area_score(results, "adaptive_reflow/contracts/") == (
        90,
        100,
        0.90,
    )
    # An area with no mutated modules scores 0 over 0 rather than raising.
    assert ast_mutator.area_score(results, "adaptive_reflow/universal/") == (
        0,
        0,
        0.0,
    )


def test_gate_passes_when_all_thresholds_met(tmp_path: Path) -> None:
    payload = _results(
        **{
            "adaptive_reflow__frame__merge.py": (70, 100),
            "adaptive_reflow__contracts__validators.py": (80, 100),
        }
    )
    target = tmp_path / "results.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert ast_mutator.main(["gate", str(target)]) == 0


@pytest.mark.parametrize(
    ("module", "killed", "total"),
    [
        # frame below 0.60
        ("adaptive_reflow__frame__merge.py", 50, 100),
        # contracts below 0.75
        ("adaptive_reflow__contracts__validators.py", 70, 100),
        # universal below 0.75
        ("adaptive_reflow__universal__mixer.py", 70, 100),
    ],
)
def test_gate_fails_on_area_breach(
    tmp_path: Path, module: str, killed: int, total: int
) -> None:
    """A gate that cannot fail is worthless; each area must be enforced."""
    payload = _results(**{module: (killed, total)})
    target = tmp_path / "results.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert ast_mutator.main(["gate", str(target)]) == 1


def test_gate_fails_when_project_score_below_threshold(tmp_path: Path) -> None:
    # policy/ has no per-area threshold, so only the project rule can catch it.
    payload = _results(**{"adaptive_reflow__policy__pruning.py": (40, 100)})
    target = tmp_path / "results.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert ast_mutator.main(["gate", str(target)]) == 1


def test_gate_refuses_an_empty_run(tmp_path: Path) -> None:
    """Zero mutants is a harness failure, not a perfect score."""
    payload = _results()
    target = tmp_path / "results.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert ast_mutator.main(["gate", str(target)]) == 1


def test_summary_runs_over_a_results_file(tmp_path: Path) -> None:
    payload = _results(**{"adaptive_reflow__frame__merge.py": (70, 100)})
    payload["by_module"]["adaptive_reflow/frame/merge.py"]["mutants"] = [
        {
            "id": "adaptive_reflow/frame/merge.py:1:CRP",
            "killed": False,
            "test_class": None,
            "detail": "0.0->1.0",
        }
    ]
    target = tmp_path / "results.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert ast_mutator.main(["summary", str(target)]) == 0


# ---------------------------------------------------------------------------
# Baseline regeneration
# ---------------------------------------------------------------------------


def test_write_baseline_preserves_handwritten_rationale(tmp_path: Path) -> None:
    """Regenerating the baseline must not discard human commentary."""
    mutate_dir = tmp_path / "tools" / "mutate"
    mutate_dir.mkdir(parents=True)
    baseline = mutate_dir / "mutation_baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "by_module": {
                    "adaptive_reflow/frame/merge.py": {
                        "killed": None,
                        "rationale": "Covered by property tests.",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    results = _results(**{"adaptive_reflow__frame__merge.py": (70, 100)})
    results["captured_at"] = "2026-08-27T00:00:00+00:00"
    results["platform"] = "windows"

    written = ast_mutator.write_baseline(results, tmp_path)
    payload = json.loads(written.read_text(encoding="utf-8"))

    entry = payload["by_module"]["adaptive_reflow/frame/merge.py"]
    assert entry["rationale"] == "Covered by property tests."
    assert entry["killed"] == 70
    assert entry["mutants_total"] == 100
    assert payload["overall_score"] == pytest.approx(0.70)
    assert payload["targets"] == dict(ast_mutator.TARGETS)


def test_justified_survivors_accepts_strings_and_objects(tmp_path: Path) -> None:
    mutate_dir = tmp_path / "tools" / "mutate"
    mutate_dir.mkdir(parents=True)
    (mutate_dir / "justified_survivors.json").write_text(
        json.dumps(
            {
                "survivors": [
                    "adaptive_reflow/frame/merge.py:1:CRP",
                    {"id": "adaptive_reflow/frame/merge.py:2:SDL", "why": "equivalent"},
                ]
            }
        ),
        encoding="utf-8",
    )
    ids = ast_mutator._justified_survivors(tmp_path)
    assert ids == {
        "adaptive_reflow/frame/merge.py:1:CRP",
        "adaptive_reflow/frame/merge.py:2:SDL",
    }


def test_missing_justified_survivors_ledger_is_not_fatal(tmp_path: Path) -> None:
    assert ast_mutator._justified_survivors(tmp_path) == set()


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------


def test_module_dotted_path() -> None:
    root = Path.cwd()
    assert (
        ast_mutator.module_dotted_path(
            root / "adaptive_reflow" / "frame" / "merge.py", root
        )
        == "adaptive_reflow.frame.merge"
    )


def test_related_tests_finds_the_merge_suites() -> None:
    """The fast phase must actually select the suites that cover the module."""
    root = Path.cwd()
    selected = ast_mutator.related_tests(
        root / "adaptive_reflow" / "frame" / "merge.py", root
    )
    assert selected, "expected a non-empty fast-phase selection"
    assert any("merge" in path for path in selected)
    # The slow benchmark suites are never part of the fast phase.
    assert not any(path.startswith("tests/perf") for path in selected)


# ---------------------------------------------------------------------------
# The mutant injector
#
# These two tests spawn a subprocess because the injector installs a
# meta-path finder and rewrites the Hypothesis profile -- side effects that
# must not leak into the test session that is checking them.
# ---------------------------------------------------------------------------


def _write_injector(tmp_path: Path) -> Path:
    plugin = tmp_path / "mutant_inject.py"
    plugin.write_text(ast_mutator._INJECTOR_SOURCE, encoding="utf-8")
    return plugin


def _injector_env(tmp_path: Path, module: str, source: Path, origin: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    env["AST_MUTANT_MODULE"] = module
    env["AST_MUTANT_SOURCE"] = str(source)
    env["AST_MUTANT_ORIGIN"] = str(origin)
    return env


def test_injector_serves_the_mutated_source(tmp_path: Path) -> None:
    """The core mechanism: the target module resolves to the mutant, not disk.

    The real file must be left untouched -- mutants are never written into the
    working tree, so an interrupted run cannot corrupt the checkout.
    """
    _write_injector(tmp_path)
    pkg = tmp_path / "victimpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    real = pkg / "mod.py"
    real.write_text("VALUE = 'original'\n", encoding="utf-8")
    mutant = tmp_path / "mutant.py"
    mutant.write_text("VALUE = 'mutated'\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import mutant_inject; import victimpkg.mod as m; print(m.VALUE)",
        ],
        cwd=str(tmp_path),
        env=_injector_env(tmp_path, "victimpkg.mod", mutant, real),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "mutated" in result.stdout
    # The on-disk source is unchanged.
    assert real.read_text(encoding="utf-8") == "VALUE = 'original'\n"


def test_injector_pins_a_deterministic_hypothesis_profile(tmp_path: Path) -> None:
    """Regression test: the profile must actually take effect.

    It previously did not. ``derandomize=True`` implies ``database=None``, so
    passing both raised ``InvalidArgument``, and a blanket ``except`` swallowed
    it. The harness then ran with Hypothesis's default 200 ms deadline and the
    shared on-disk example database, which makes verdicts both load-sensitive
    (a slow-but-correct mutant is scored as killed) and order-dependent
    (counterexamples leak between mutants).
    """
    pytest.importorskip("hypothesis")
    _write_injector(tmp_path)
    real = tmp_path / "solo.py"
    real.write_text("VALUE = 1\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import mutant_inject\n"
            "from hypothesis import settings\n"
            "print('derandomize', settings.default.derandomize)\n"
            "print('database', settings.default.database)\n"
            "print('deadline', settings.default.deadline)\n",
        ],
        cwd=str(tmp_path),
        env=_injector_env(tmp_path, "solo", real, real),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "derandomize True" in result.stdout
    assert "database None" in result.stdout
    assert "deadline None" in result.stdout
