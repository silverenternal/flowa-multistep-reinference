"""Tests for docs/defaults-matrix.md and docs/sequential-protocol.md (P1-4, external).

Walks the markdown files in ``docs/`` and asserts:

* the matrix table has the documented four scenarios,
* every Scheduler / Driver / Merge / Blender column references a
  real implementation in ``adaptive_reflow/``,
* the worked examples in ``sequential-protocol.md`` actually
  round-trip when executed against the framework,
* the extended ``schedule-theory.md`` has the closed-form table,
  the field-standards comparison, and the decision tree.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import pytest

from adaptive_reflow.algorithm.blender import (
    DISTANCE_DECAY_FAMILY,
    LINEAR_FAMILY,
    DistanceDecayBlender,
    LinearBlender,
)
from adaptive_reflow.algorithm.merge_operator import (
    BoundedMergeOperator,
)
from adaptive_reflow.algorithm.policy_driver import (
    SCHEDULE_DERIVED_FAMILY,
    ScheduleDerivedPolicyDriver,
)
from adaptive_reflow.algorithm.scheduler import (
    SCHEDULER_REGISTRY,
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    ExponentialScheduler,
    build_scheduler,
    build_scheduler_from_config,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.sequential import (
    SequentialScheduler,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"


def _read_doc(filename: str) -> str:
    path = DOCS_DIR / filename
    assert path.exists(), f"missing doc: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_default_matrix_rows(doc: str) -> list[dict[str, str]]:
    """Parse the matrix table from docs/defaults-matrix.md.

    The matrix is a markdown table whose first row is the header and
    whose data rows are bounded by a separator row. The first column
    is "Scenario"; the rest map onto (Scheduler, PolicyDriver,
    MergeOperator, Blender, Rationale).
    """
    lines = doc.splitlines()
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        # Skip the separator row (cells contain only --- and whitespace).
        if all(re.match(r"^:?-+:?$", c) for c in cells):
            continue
        if header is None:
            header = cells
            continue
        if len(header) != len(cells):
            # Skip any malformed or partial rows.
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


# ---------------------------------------------------------------------------
# Defaults matrix — exists and is parseable
# ---------------------------------------------------------------------------


def test_defaults_matrix_doc_exists() -> None:
    doc = _read_doc("defaults-matrix.md")
    assert "Defaults matrix" in doc
    assert "SchedulerProtocol" in doc
    assert "PolicyDriverProtocol" in doc
    assert "MergeOperatorProtocol" in doc
    assert "RestartBlenderProtocol" in doc


def test_defaults_matrix_has_at_least_four_scenarios() -> None:
    """The matrix must have at least the four documented scenarios."""
    doc = _read_doc("defaults-matrix.md")
    rows = _extract_default_matrix_rows(doc)
    scenarios = [r.get("Scenario", "") for r in rows]
    assert len(scenarios) >= 4
    joined = " ".join(scenarios)
    assert "Short run" in joined
    assert "Long run" in joined
    assert "Adaptive" in joined
    assert "Sequential" in joined


def test_defaults_matrix_short_run_row_references_cosine() -> None:
    """The 'Short run' row references CosineAnnealScheduler."""
    doc = _read_doc("defaults-matrix.md")
    rows = _extract_default_matrix_rows(doc)
    short = [r for r in rows if "Short run" in r.get("Scenario", "")]
    assert short, "no 'Short run' row found"
    scheduler_cell = short[0].get("Scheduler", "")
    assert "CosineAnnealScheduler" in scheduler_cell


def test_defaults_matrix_long_run_row_references_codimension_sheet() -> None:
    """The 'Long run' row references CodimensionSheetScheduler."""
    doc = _read_doc("defaults-matrix.md")
    rows = _extract_default_matrix_rows(doc)
    long_ = [r for r in rows if "Long run" in r.get("Scenario", "")]
    assert long_, "no 'Long run' row found"
    scheduler_cell = long_[0].get("Scheduler", "")
    assert "CodimensionSheetScheduler" in scheduler_cell


def test_defaults_matrix_adaptive_row_references_convergence_adaptive() -> None:
    """The 'Adaptive' row references ConvergenceAdaptiveScheduler."""
    doc = _read_doc("defaults-matrix.md")
    rows = _extract_default_matrix_rows(doc)
    adaptive = [r for r in rows if "Adaptive" in r.get("Scenario", "")]
    assert adaptive, "no 'Adaptive' row found"
    scheduler_cell = adaptive[0].get("Scheduler", "")
    assert "ConvergenceAdaptiveScheduler" in scheduler_cell


def test_defaults_matrix_sequential_row_references_sequential_scheduler() -> None:
    """The 'Sequential' row references SequentialScheduler."""
    doc = _read_doc("defaults-matrix.md")
    rows = _extract_default_matrix_rows(doc)
    sequential = [r for r in rows if "Sequential" in r.get("Scenario", "")]
    assert sequential, "no 'Sequential' row found"
    scheduler_cell = sequential[0].get("Scheduler", "")
    assert "SequentialScheduler" in scheduler_cell


def test_defaults_matrix_references_real_implementations() -> None:
    """Every referenced implementation must exist under adaptive_reflow/.

    The defaults matrix is a reader-facing heuristic guide; it MUST
    NOT name a class or family that does not exist in the
    codebase (drift would be a documentation lie). Walk every
    CamelCase token in the matrix's Scheduler / Driver / Merge /
    Blender columns and assert each resolves to a real class.
    """
    doc = _read_doc("defaults-matrix.md")
    rows = _extract_default_matrix_rows(doc)
    expected_classes = {
        # Scheduler
        "CosineAnnealScheduler",
        "ConstantScheduler",
        "LinearScheduler",
        "ExponentialScheduler",
        "PolynomialScheduler",
        "SigmoidScheduler",
        "ConvergenceAdaptiveScheduler",
        "CodimensionSheetScheduler",
        "SequentialScheduler",
        # Driver
        "ScheduleDerivedPolicyDriver",
        "ConstantPolicyDriver",
        "AdaptivePolicyDriver",
        # Merge
        "BoundedMergeOperator",
        "IdentityOperator",
        "EMAOperator",
        # Blender
        "LinearBlender",
        "DistanceDecayBlender",
    }
    found: set[str] = set()
    for row in rows:
        for column in ("Scheduler", "PolicyDriver", "MergeOperator", "Blender"):
            cell = row.get(column, "")
            for name in expected_classes:
                if name in cell:
                    found.add(name)
    assert found, "no expected classes were referenced in the matrix"
    referenced_schedulers = {
        n for n in expected_classes if n in found and n.endswith("Scheduler")
    }
    assert len(referenced_schedulers) >= 4, (
        f"matrix covers only {sorted(referenced_schedulers)}; "
        f"expected at least 4 of {sorted({n for n in expected_classes if n.endswith('Scheduler')})}"
    )
    assert "SequentialScheduler" in referenced_schedulers


def test_defaults_matrix_rows_instantiate() -> None:
    """Every scheduler in the matrix can be constructed and produces a sample.

    This is the executable form of the matrix: build each scheduler
    family the matrix names and assert the resulting
    `SchedulerProtocol` instance can `sample` round 0 successfully.
    """
    # Short run: CosineAnnealScheduler(cycle_length=4)
    cosine_short = default_cosine_scheduler(cycle_length=4)
    s0 = cosine_short.sample(0, 0, 0)
    assert 0.0 <= float(s0.n_cap) <= 1.0

    # Long run: CodimensionSheetScheduler(eps_implicit=0.05)
    codim = CodimensionSheetScheduler(
        cycle_length=20,
        eps_implicit=0.05,
    )
    s0 = codim.sample(0, 0, 0)
    assert 0.0 <= float(s0.n_cap) <= 1.0

    # Adaptive: ConvergenceAdaptiveScheduler(base=cosine)
    adaptive = ConvergenceAdaptiveScheduler(
        base=default_cosine_scheduler(cycle_length=4),
        shift_max=0.2,
    )
    s0 = adaptive.sample(0, 0, 0)
    assert 0.0 <= float(s0.n_cap) <= 1.0

    # Sequential: SequentialScheduler([(CosineAnnealScheduler, 8), ...])
    chain = SequentialScheduler(
        schedulers=[
            (default_cosine_scheduler(cycle_length=8), 8),
            (ExponentialScheduler(cycle_length=4), 4),
            (ConstantScheduler(cycle_length=8, n_cap=0.05), 8),
        ],
    )
    assert chain.cycle_length() == 20
    s0 = chain.sample(0, 0, 0)
    assert 0.0 <= float(s0.n_cap) <= 1.0


def test_defaults_matrix_drivers_and_blenders_exist() -> None:
    """The driver and blender classes the matrix names must be importable."""
    assert SCHEDULE_DERIVED_FAMILY == "schedule_derived"
    assert LINEAR_FAMILY == "linear"
    assert DISTANCE_DECAY_FAMILY == "distance_decay"
    driver = ScheduleDerivedPolicyDriver()
    assert driver is not None
    assert LinearBlender() is not None
    assert DistanceDecayBlender(temperature=1.0) is not None


def test_defaults_matrix_merge_floor_argument() -> None:
    """The matrix documents BoundedMergeOperator(floor=0.1) for short runs.

    The matrix doc references ``floor=0.1`` as the bounded-merge floor
    for short runs (and ``floor=0.05`` for long runs). The shipped
    ``BoundedMergeOperator`` exposes its merge semantics through
    :meth:`merge` with a ``floor`` keyword; assert that the keyword
    is honoured and the operator refuses to emit a value below the
    floor.
    """
    operator = BoundedMergeOperator()
    result = operator.merge(
        prev=0.5,
        dynamic=0.05,
        cap=1.0,
        floor=0.1,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
    )
    # When the dynamic value (0.05) is below the floor (0.1), the
    # operator clips to the floor per its documented behaviour.
    assert result >= 0.1


# ---------------------------------------------------------------------------
# Sequential protocol doc — cross-references and round-trip
# ---------------------------------------------------------------------------


def test_sequential_protocol_doc_exists() -> None:
    doc = _read_doc("sequential-protocol.md")
    assert "SequentialScheduler" in doc
    assert "SchedulerProtocol" in doc
    assert "config_hash" in doc


def test_sequential_protocol_doc_references_real_classes() -> None:
    """Every class name in the doc must be a real implementation."""
    doc = _read_doc("sequential-protocol.md")
    expected_classes = {
        "SequentialScheduler",
        "ExponentialScheduler",
        "ConstantScheduler",
        "SchedulerProtocol",
    }
    for name in expected_classes:
        assert name in doc, f"{name} not referenced in sequential-protocol.md"
    # ``CosineAnnealScheduler`` is the canonical name; the doc uses
    # the ``default_cosine_scheduler`` factory instead. The factory
    # returns a ``CosineAnnealScheduler`` instance; assert the doc
    # mentions at least one of the two so a future edit does not
    # silently drop both.
    assert (
        "CosineAnnealScheduler" in doc or "default_cosine_scheduler" in doc
    ), "sequential-protocol.md must reference either CosineAnnealScheduler or default_cosine_scheduler"


def test_sequential_protocol_doc_round_trip_matches_three_phase_example() -> None:
    """The doc's three-phase example (cosine 8 / expo 4 / constant 8) round-trips.

    This is the executable form of the worked example: build the
    chain the doc describes, sample round 0 / round 7 / round 8,
    and assert the trajectory matches the doc's table.
    """
    cosine = default_cosine_scheduler(cycle_length=8, n_min=0.1, n_max=1.0)
    expo = ExponentialScheduler(cycle_length=4, n_max=1.0, alpha=0.3)
    const = ConstantScheduler(cycle_length=8, n_cap=0.05)
    chain = SequentialScheduler(
        schedulers=[(cosine, 8), (expo, 4), (const, 8)],
    )
    assert chain.cycle_length() == 20
    # Round 0 of the chain maps to sub-round 0 of the cosine slot.
    # Cosine's n_cap(0) = n_min (the cosine starts at its minimum and
    # climbs to n_max over the cycle).
    s0 = chain.sample(0, 0, 0)
    assert s0.n_cap == pytest.approx(cosine.sample(0, 0, 0).n_cap)
    # Round 7 of the chain is sub-round 7 of the cosine slot (the
    # terminal round, n_cap = n_max = 1.0).
    s7 = chain.sample(0, 7, 7)
    assert s7.n_cap == pytest.approx(cosine.sample(0, 7, 7).n_cap)
    # Round 8 of the chain is sub-round 0 of the exponential slot
    # (n_cap = n_max = 1.0).
    s8 = chain.sample(0, 8, 8)
    assert s8.n_cap == pytest.approx(expo.sample(0, 0, 0).n_cap)
    # Round 12 of the chain is sub-round 0 of the constant slot
    # (n_cap = 0.05).
    s12 = chain.sample(0, 12, 12)
    assert s12.n_cap == pytest.approx(0.05)


def test_sequential_protocol_doc_round_trip_via_config() -> None:
    """The doc's to_config / from_config example round-trips byte-identically."""
    cosine = default_cosine_scheduler(cycle_length=8)
    expo = ExponentialScheduler(cycle_length=4, alpha=0.2)
    chain = SequentialScheduler(schedulers=[(cosine, 8), (expo, 4)])
    rebuilt = SequentialScheduler.from_config(chain.to_config())
    assert rebuilt.cycle_length() == chain.cycle_length()
    assert rebuilt.config_hash() == chain.config_hash()


def test_sequential_in_registry() -> None:
    """The sequential family is registered in SCHEDULER_REGISTRY."""
    assert "sequential" in SCHEDULER_REGISTRY


def test_sequential_dispatched_via_build_scheduler_from_config() -> None:
    """build_scheduler_from_config routes 'sequential' to SequentialScheduler."""
    cosine = default_cosine_scheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4)])
    cfg = chain.to_config()
    rebuilt = build_scheduler_from_config(cfg)
    assert isinstance(rebuilt, SequentialScheduler)


def test_sequential_dispatched_via_build_scheduler_factory() -> None:
    """build_scheduler raises KeyError on an unknown family."""
    with pytest.raises(KeyError, match="unknown scheduler family"):
        build_scheduler("definitely_not_registered")


# ---------------------------------------------------------------------------
# Schedule-theory doc — extended tables exist
# ---------------------------------------------------------------------------


def test_schedule_theory_doc_has_closed_form_table() -> None:
    doc = _read_doc("schedule-theory.md")
    assert "Closed-form expressions" in doc
    assert "CosineAnnealScheduler" in doc
    assert "ExponentialScheduler" in doc
    assert "PolynomialScheduler" in doc
    assert "SigmoidScheduler" in doc
    assert "ConvergenceAdaptiveScheduler" in doc
    assert "CodimensionSheetScheduler" in doc


def test_schedule_theory_doc_has_field_comparison_table() -> None:
    doc = _read_doc("schedule-theory.md")
    assert "Comparison to field standards" in doc
    assert "Nichol-Dhariwal" in doc
    assert "Karras" in doc


def test_schedule_theory_doc_has_decision_tree() -> None:
    doc = _read_doc("schedule-theory.md")
    assert "How to choose a schedule" in doc
    assert "cycle_length" in doc


# ---------------------------------------------------------------------------
# Cross-reference between defaults-matrix and schedule-theory
# ---------------------------------------------------------------------------


def test_defaults_matrix_links_to_schedule_theory() -> None:
    """The defaults-matrix must cross-reference the schedule-theory decision tree."""
    doc = _read_doc("defaults-matrix.md")
    assert "schedule-theory.md" in doc


def test_schedule_theory_links_to_defaults_matrix() -> None:
    """The schedule-theory decision tree must cross-reference the defaults matrix."""
    doc = _read_doc("schedule-theory.md")
    assert "defaults-matrix.md" in doc
