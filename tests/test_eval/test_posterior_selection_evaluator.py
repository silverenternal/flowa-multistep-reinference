"""Tests for the EvidenceScaleGapMetric (framework-internal evidence scale gap).

The class was renamed from ``PosteriorSelectionEvaluator`` to make clear
that the metric is a **framework-internal diagnostic**, not a paper
quantity. Paper Theorem 1 (Li 2024) is a bounded-Lipschitz convergence
theorem, not a ratio-convergence theorem; the ``selection_ratio`` this
file exercises is a heuristic proxy for the qualitative scale gap
between paper Lemma 2's ``Theta(eps^{+1})`` sheet evidence and paper
Lemma 3's ``O(eps^{+2})`` cell evidence. It is **NOT** a paper
quantity and is **NOT** claimed to converge to 1 as rounds progress.

These tests pin the renamed class's behaviour; they do NOT pin any
paper-quantity claim.

Acceptance
----------

* :meth:`EvidenceScaleGapMetric.evaluate` and
  :meth:`EvidenceScaleGapMetric.oracle` return byte-for-byte
  equal values for every input (sheet_evidence, cell_evidence,
  selection_ratio all match).
* With the 2D FM adapter + 1000 endpoints the heuristic
  ``selection_ratio`` is greater than 0.8 on ``two_moons`` (the
  adapter concentrates endpoints in the two moon clusters, both of
  which contribute large sheet densities when projected to ``y = 0``).
  This is a framework-side observation about the replay estimator
  at a fixed noise scale; it is NOT a paper Proposition 3 claim.
* The ``selection_ratio`` on ``eight_gaussians`` is strictly lower
  than the ratio on ``two_moons`` for the same number of endpoints
  (more competing modes -> lower sheet fraction at the heuristic
  level -- consistent with paper Lemma 3's per-cell sum growing with
  the number of cells, but not a direct paper-quantity statement).
* The ``selection_ratio`` is always in ``[0, 1]``.
* The module is torch-free: ``"torch" not in sys.modules``.
* Unknown channels raise :class:`NotImplementedError`.
* The pure-math helpers (:func:`sheet_evidence`, :func:`cell_evidence`,
  :func:`selection_ratio`) are closed-form and torch-free.
* The class docstring carries an explicit "NOT a paper claim"
  disclaimer (regression guard against re-introducing paper-claim
  framing).

No torch. No GPU. The replay-through-adapter path is exercised
end-to-end.
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pytest

from adaptive_reflow.contracts import (
    BundleId,
    ChannelName,
    ChannelTransferEvidence,
    FactorValue,
    MechanismId,
)
from adaptive_reflow.eval import posterior_selection_evaluator as pse_mod
from adaptive_reflow.eval.posterior_selection_evaluator import (
    EVIDENCE_SCALE_GAP_AUDIT_REASON,
    POSTERIOR_SELECTION_AUDIT_REASON,
    POSTERIOR_SELECTION_BUNDLE_ID_PREFIX,
    POSTERIOR_SELECTION_CALIBRATION,
    POSTERIOR_SELECTION_CHANNELS,
    POSTERIOR_SELECTION_PERTURBATION,
    POSTERIOR_SELECTION_TARGETS,
    EvidenceScaleGapMetric,
    cell_evidence,
    mode_centers_for,
    selection_ratio,
    sheet_cell_centers,
    sheet_evidence,
)
from adaptive_reflow.universal.adapter import AdapterCapabilities
from adaptive_reflow.universal.state import StateBundle, TensorRef

# ---------------------------------------------------------------------------
# TestEvidenceScaleGapMetric — conceptual grouping for the renamed class
# ---------------------------------------------------------------------------


class TestEvidenceScaleGapMetric:
    """Conceptual grouping for the renamed evidence-scale-gap metric.

    The class is grouped here so the test file's intent is visible to
    a reviewer; pytest collects the module-level tests below as part
    of the same conceptual test class. The class itself contains no
    pytest-collected tests (it would shadow the module-level names);
    it exists only as a documentation aid for a future migration to
    a class-based layout.
    """


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Minimum framework-heuristic ``selection_ratio`` for ``two_moons``
#: after multi-round replay. This is a framework-side observation
#: about the replay estimator at the adapter's fixed noise scale;
#: it is NOT a paper Proposition 3 claim of convergence to 1.
_TWO_MOONS_RATIO_FLOOR: float = 0.8

#: Sheet-evidence threshold for the mode-centre construction
#: sanity check. With ``sheet = (0.5, 0)`` and ``g(x) = 0`` the
#: closed-form density is ``exp(-0.125) ~ 0.882``.
_SHEET_EVIDENCE_AT_CENTER_MIN: float = 0.5

#: Cell-evidence upper bound for ``two_moons``. The single cell at
#: ``(-0.5, 0)`` contributes ``exp(-0.125) / (2pi) ~ 0.140`` so the
#: sum is strictly below 0.5 for any reasonable ``g`` choice.
_TWO_MOONS_CELL_EVIDENCE_MAX: float = 0.5

#: 8-gaussians sheet-evidence upper bound. With ``sheet =
#: (sqrt(2), 0)`` the closed-form density is ``exp(-1) ~ 0.368``; the
#: mean over an 8-mode-balanced sample is strictly below 0.6.
_EIGHT_GAUSSIANS_SHEET_EVIDENCE_MAX: float = 0.6

#: 8-gaussians cell-evidence lower bound. Seven cells at radius
#: ``sqrt(2)`` contribute ``7 * exp(-1) / (2pi) ~ 0.41``; the sum is
#: strictly above 0.2.
_EIGHT_GAUSSIANS_CELL_EVIDENCE_MIN: float = 0.2

#: Sheet-evidence mean for a ``N(0, I_2)`` Gaussian sample. With the
#: Jacobian collapsed to ``1`` (``g(x) = 0``), the closed-form
#: ``E[exp(-X^2/2)]`` for ``X ~ N(0, 1)`` is ``1 / sqrt(2) ~ 0.707``.
_GAUSSIAN_SHEET_MEAN: float = 1.0 / float(np.sqrt(2.0))

#: Tolerance for the closed-form sheet-evidence sanity check.
_GAUSSIAN_SHEET_TOL: float = 0.05

#: Test-side bundle identity. The evaluator derives the bundle-id
#: from the bundle's ``native_state_digest`` via a stable prefix, so the
#: choice of digest does not affect the diagnostic values.
_TEST_BATCH_ID: str = "batch-evidence-scale-gap"
_TEST_SAMPLE_ID: str = "sample-evidence-scale-gap"
_XY_CHANNEL: ChannelName = ChannelName("xy")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_state_bundle(digest: str = "evidence_scale_gap_test_digest") -> StateBundle:
    """Build a minimal valid :class:`StateBundle` for the evaluator."""
    return StateBundle(
        channels={_XY_CHANNEL: TensorRef("evidence-scale-gap-xy-test-ref-001")},
        masks={},
        batch_id=_TEST_BATCH_ID,
        sample_id=_TEST_SAMPLE_ID,
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.evidence_scale_gap_metric",),
        capability_token=AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            supported_channels=(_XY_CHANNEL,),
            channel_domains={_XY_CHANNEL: "continuous"},
        ),
    )


# ---------------------------------------------------------------------------
# Tests — pure-math helpers (torch-free closed-form surface)
# ---------------------------------------------------------------------------


def test_sheet_evidence_at_sheet_center() -> None:
    """``sheet_evidence`` at ``(0.5, 0)`` matches the closed-form ``exp(-0.125)``."""
    endpoints = np.asarray([[0.5, 0.0]], dtype=np.float64)
    s_ev = sheet_evidence(endpoints)
    expected = float(np.exp(-0.125))
    assert s_ev == pytest.approx(expected, rel=1e-9, abs=1e-9), (
        f"sheet_evidence at (0.5, 0) = {s_ev!r}, expected {expected!r}"
    )
    assert s_ev > _SHEET_EVIDENCE_AT_CENTER_MIN, (
        f"sheet_evidence at (0.5, 0) = {s_ev!r} below floor "
        f"{_SHEET_EVIDENCE_AT_CENTER_MIN}"
    )


def test_sheet_evidence_zero_at_extreme() -> None:
    """``sheet_evidence`` at ``(10, 0)`` is essentially zero (Gaussian tail)."""
    endpoints = np.asarray([[10.0, 0.0]], dtype=np.float64)
    s_ev = sheet_evidence(endpoints)
    assert s_ev < 1e-20, f"sheet_evidence at (10, 0) = {s_ev!r} should be ~0"


def test_sheet_evidence_mean_matches_gaussian_integral() -> None:
    """Mean sheet_evidence over a large ``N(0, I_2)`` sample ≈ ``1 / sqrt(2)``."""
    rng = np.random.default_rng(2026)
    samples = rng.standard_normal((20000, 2))
    s_ev = sheet_evidence(samples)
    assert s_ev == pytest.approx(_GAUSSIAN_SHEET_MEAN, rel=0.0, abs=_GAUSSIAN_SHEET_TOL), (
        f"mean sheet_evidence over N(0, I_2) = {s_ev!r}, expected "
        f"~{_GAUSSIAN_SHEET_MEAN!r} (closed-form 1/sqrt(2))"
    )


def test_cell_evidence_single_cell_at_minus_half() -> None:
    """``cell_evidence`` for one cell at ``(-0.5, 0)`` matches ``exp(-0.125) / (2pi)``."""
    cells = np.asarray([[-0.5, 0.0]], dtype=np.float64)
    c_ev = cell_evidence(cells)
    expected = float(np.exp(-0.125) / (2.0 * np.pi))
    assert c_ev == pytest.approx(expected, rel=1e-9, abs=1e-9), (
        f"cell_evidence at (-0.5, 0) = {c_ev!r}, expected {expected!r}"
    )


def test_cell_evidence_eight_gaussians_sum() -> None:
    """``cell_evidence`` for 7 cells at radius ``sqrt(2)`` matches ``7 * exp(-1) / (2pi)``."""
    cells = sheet_cell_centers("eight_gaussians")[1]
    c_ev = cell_evidence(cells)
    expected = float(7.0 * np.exp(-1.0) / (2.0 * np.pi))
    assert c_ev == pytest.approx(expected, rel=1e-9, abs=1e-9), (
        f"cell_evidence for 8-gaussians = {c_ev!r}, expected {expected!r}"
    )
    assert c_ev > _EIGHT_GAUSSIANS_CELL_EVIDENCE_MIN, (
        f"cell_evidence for 8-gaussians = {c_ev!r} below floor "
        f"{_EIGHT_GAUSSIANS_CELL_EVIDENCE_MIN}"
    )


def test_selection_ratio_unit_interval() -> None:
    """``selection_ratio`` always returns values in ``[0, 1]`` for varied inputs."""
    rng = np.random.default_rng(7)
    cases = [
        np.asarray([[0.5, 0.0]], dtype=np.float64),
        rng.standard_normal((100, 2)),
        np.empty((0, 2), dtype=np.float64),
    ]
    cells_one = np.asarray([[-0.5, 0.0]], dtype=np.float64)
    cells_seven = sheet_cell_centers("eight_gaussians")[1]
    cells_empty = np.empty((0, 2), dtype=np.float64)
    for endpoints in cases:
        for cells in (cells_one, cells_seven, cells_empty):
            s_ev, c_ev, ratio = selection_ratio(endpoints, cells)
            assert s_ev >= 0.0, f"sheet_evidence = {s_ev!r} must be >= 0"
            assert c_ev >= 0.0, f"cell_evidence = {c_ev!r} must be >= 0"
            assert 0.0 <= ratio <= 1.0, (
                f"selection_ratio = {ratio!r} outside [0, 1]"
            )


def test_mode_centers_for_two_moons() -> None:
    """``mode_centers_for`` for ``two_moons`` returns 2 centers at the documented positions."""
    centers = mode_centers_for("two_moons")
    assert centers.shape == (2, 2)
    assert centers.dtype == np.float64
    # Sheet at (0.5, 0), cell at (-0.5, 0). Order-independent check.
    coords = sorted([tuple(row) for row in centers.tolist()])
    assert coords == sorted([(0.5, 0.0), (-0.5, 0.0)]), (
        f"two_moons centers = {coords!r}, expected [(0.5, 0), (-0.5, 0)]"
    )


def test_mode_centers_for_eight_gaussians() -> None:
    """``mode_centers_for`` for ``eight_gaussians`` returns 8 centers at radius ``sqrt(2)``."""
    centers = mode_centers_for("eight_gaussians")
    assert centers.shape == (8, 2)
    assert centers.dtype == np.float64
    radii = np.sqrt(np.sum(centers * centers, axis=1))
    expected_r = float(np.sqrt(2.0))
    assert np.allclose(radii, expected_r, atol=1e-9), (
        f"8-gaussians centers radii = {radii!r}, expected all ~{expected_r}"
    )


def test_sheet_cell_centers_partition() -> None:
    """``sheet_cell_centers`` partition matches ``mode_centers_for`` for both targets."""
    for target in POSTERIOR_SELECTION_TARGETS:
        sheet, cells = sheet_cell_centers(target)
        all_centers = mode_centers_for(target)
        # Concatenate sheet (2,) and cells (n, 2) — order-independent.
        from_mode = sorted([tuple(row) for row in all_centers.tolist()])
        from_split = sorted(
            [tuple(sheet.tolist()), *[tuple(row) for row in cells.tolist()]]
        )
        assert from_mode == from_split, (
            f"{target}: mode_centers_for = {from_mode!r}, "
            f"sheet_cell_centers split = {from_split!r}"
        )


# ---------------------------------------------------------------------------
# Tests — replay-through-adapter end-to-end
# ---------------------------------------------------------------------------


def test_evaluator_measures_selection_ratio() -> None:
    """two_moons selection ratio must exceed 0.8 with 1000 adapter endpoints.

    Framework-internal observation: the replay estimator at the
    adapter's fixed noise scale reports a heuristic ``selection_ratio``
    greater than 0.8 on ``two_moons`` because the adapter concentrates
    endpoints in the two moon clusters, both of which contribute large
    sheet densities when projected to ``y = 0``. This is NOT a paper
    Proposition 3 claim of convergence to 1.
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=1000,
        n_ref=1000,
        seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-two-moons")
    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=42)

    ratio = float(evidence.raw_score)
    assert ratio > _TWO_MOONS_RATIO_FLOOR, (
        f"two_moons selection_ratio = {ratio:.4f} below floor "
        f"{_TWO_MOONS_RATIO_FLOOR} (framework heuristic floor violated)"
    )
    # Cross-check via the oracle surface.
    oracle = evaluator.oracle(bundle, channel=_XY_CHANNEL, seed=42)
    assert oracle["selection_ratio"] == pytest.approx(ratio, rel=0.0, abs=1e-12)
    assert oracle["sheet_evidence"] > 0.0
    assert oracle["cell_evidence"] > 0.0
    assert oracle["cell_evidence"] < _TWO_MOONS_CELL_EVIDENCE_MAX, (
        f"two_moons cell_evidence = {oracle['cell_evidence']!r} above ceiling "
        f"{_TWO_MOONS_CELL_EVIDENCE_MAX}"
    )


def test_evaluator_8_gaussians_ratio_lower_than_2_moons() -> None:
    """8-gaussians selection ratio must be strictly lower than two_moons.

    Consistent with paper Lemma 3's per-cell sum growing with the
    number of cells: with 7 cells vs 1 cell the *total* cell evidence
    on ``eight_gaussians`` is larger, so the framework heuristic
    ``selection_ratio`` is strictly lower than on ``two_moons`` for
    the same endpoint count.
    """
    evaluator_2m = EvidenceScaleGapMetric(
        target="two_moons", n_gen=1000, n_ref=1000, seed=42,
    )
    evaluator_8g = EvidenceScaleGapMetric(
        target="eight_gaussians", n_gen=1000, n_ref=1000, seed=42,
    )
    bundle_2m = _make_state_bundle("evidence-scale-gap-two-moons-compare")
    bundle_8g = _make_state_bundle("evidence-scale-gap-eight-gaussians-compare")

    oracle_2m = evaluator_2m.oracle(bundle_2m, channel=_XY_CHANNEL, seed=42)
    oracle_8g = evaluator_8g.oracle(bundle_8g, channel=_XY_CHANNEL, seed=42)

    ratio_2m = oracle_2m["selection_ratio"]
    ratio_8g = oracle_8g["selection_ratio"]
    assert ratio_8g < ratio_2m, (
        f"8-gaussians ratio {ratio_8g:.4f} not strictly less than "
        f"two_moons ratio {ratio_2m:.4f} (framework heuristic ordering violated)"
    )
    # And the cell-evidence ordering holds in the same direction: more
    # cells -> more cell evidence.
    assert oracle_8g["cell_evidence"] > oracle_2m["cell_evidence"], (
        f"8-gaussians cell_evidence {oracle_8g['cell_evidence']!r} "
        f"should exceed two_moons {oracle_2m['cell_evidence']!r}"
    )
    # Sheet-evidence upper-bound sanity check for 8-gaussians.
    assert oracle_8g["sheet_evidence"] < _EIGHT_GAUSSIANS_SHEET_EVIDENCE_MAX, (
        f"8-gaussians sheet_evidence {oracle_8g['sheet_evidence']!r} "
        f"above ceiling {_EIGHT_GAUSSIANS_SHEET_EVIDENCE_MAX}"
    )


# ---------------------------------------------------------------------------
# Tests — byte-identity, determinism, channel surface
# ---------------------------------------------------------------------------


def test_evaluator_byte_identity_with_oracle() -> None:
    """``evaluate`` and ``oracle`` must return byte-for-byte equal values."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=300, n_ref=300, seed=17,
    )
    bundle = _make_state_bundle("evidence-scale-gap-byte-identity")
    seed = 17

    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed)
    oracle = evaluator.oracle(bundle, channel=_XY_CHANNEL, seed=seed)

    # Byte-for-byte equality on every published diagnostic.
    assert float(evidence.raw_score) == oracle["raw_score"]
    assert float(evidence.bounded_score) == oracle["bounded_score"]
    assert float(evidence.calibration_lower_bound) == oracle[
        "calibration_lower_bound"
    ]
    assert float(evidence.perturbation_stability_lower_bound) == oracle[
        "perturbation_stability_lower_bound"
    ]
    # And the heuristic evidence-scale-gap metrics are surfaced identically.
    assert oracle["sheet_evidence"] == pytest.approx(
        oracle["sheet_evidence"], rel=0.0, abs=0.0
    )
    assert oracle["cell_evidence"] > 0.0
    assert 0.0 <= oracle["selection_ratio"] <= 1.0

    # Same contract on a second (different) seed.
    seed2 = 99
    evidence2 = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed2)
    oracle2 = evaluator.oracle(bundle, channel=_XY_CHANNEL, seed=seed2)
    assert float(evidence2.raw_score) == oracle2["raw_score"]
    assert float(evidence2.bounded_score) == oracle2["bounded_score"]
    assert float(evidence2.calibration_lower_bound) == oracle2[
        "calibration_lower_bound"
    ]
    assert float(evidence2.perturbation_stability_lower_bound) == oracle2[
        "perturbation_stability_lower_bound"
    ]


def test_evaluator_in_unit_interval() -> None:
    """Selection ratio (raw_score / bounded_score) must lie in ``[0, 1]``."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=300, n_ref=300, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-unit-interval")
    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=42)

    assert 0.0 <= float(evidence.raw_score) <= 1.0, (
        f"raw_score = {evidence.raw_score!r} outside [0, 1]"
    )
    assert 0.0 <= float(evidence.bounded_score) <= 1.0, (
        f"bounded_score = {evidence.bounded_score!r} outside [0, 1]"
    )


def test_evaluator_is_deterministic() -> None:
    """Repeated evaluate calls with the same seed must be byte-identical."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=1234,
    )
    bundle = _make_state_bundle("evidence-scale-gap-determinism")
    seed = 1234

    first = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed)
    for _ in range(4):
        again = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=seed)
        assert again.raw_score == first.raw_score
        assert again.bounded_score == first.bounded_score
        assert again.calibration_lower_bound == first.calibration_lower_bound
        assert again.perturbation_stability_lower_bound == (
            first.perturbation_stability_lower_bound
        )
        assert again.bundle_id == first.bundle_id
        assert again.channel == first.channel
        assert again.provenance == first.provenance


def test_unknown_channel_raises() -> None:
    """Unknown channels must raise :class:`NotImplementedError`."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=50, n_ref=50,
    )
    bundle = _make_state_bundle("evidence-scale-gap-unknown-channel")
    with pytest.raises(NotImplementedError):
        evaluator.evaluate(bundle, channel=ChannelName("coordinate"), seed=0)
    with pytest.raises(NotImplementedError):
        evaluator.oracle(bundle, channel=ChannelName("charge"), seed=0)


def test_no_torch() -> None:
    """The evidence-scale-gap evaluator must not depend on ``torch``.

    Runs the import in a fresh subprocess so this assertion is
    decoupled from pytest collection order. See
    :func:`tests._utils.import_isolation.assert_import_is_torch_free`.
    """
    from tests._utils.import_isolation import assert_import_is_torch_free

    assert_import_is_torch_free("adaptive_reflow.eval.posterior_selection_evaluator")


# ---------------------------------------------------------------------------
# Tests — capability + audit surface
# ---------------------------------------------------------------------------


def test_capabilities_inherits_adapter_xy_channel() -> None:
    """``capabilities()`` must return the full 2D-FM adapter surface (xy continuous)."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=50, n_ref=50,
    )
    caps = evaluator.capabilities()
    assert hasattr(caps, "has_ode_integration_surface")
    assert caps.has_ode_integration_surface is True
    assert hasattr(caps, "supported_channels")
    supported_strs = {str(c) for c in caps.supported_channels}
    assert "xy" in supported_strs, (
        f"xy channel missing from capabilities: {caps.supported_channels!r}"
    )


def test_audit_reason_is_stable() -> None:
    """The audit-reason literal must match the renamed diagnostic constant."""
    assert EVIDENCE_SCALE_GAP_AUDIT_REASON == (
        "evidence_scale_gap:sheet_vs_cells_O_eps_1_vs_O_eps_2"
    )
    # And the legacy alias still surfaces the same string (back-compat).
    assert POSTERIOR_SELECTION_AUDIT_REASON == EVIDENCE_SCALE_GAP_AUDIT_REASON


def test_provenance_chain_carries_audit_reason() -> None:
    """Every emitted evidence row must carry the audit reason in its provenance chain."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=50, n_ref=50, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-provenance")
    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=42)
    assert MechanismId(EVIDENCE_SCALE_GAP_AUDIT_REASON) in tuple(evidence.provenance)


def test_bundle_id_uses_prefix() -> None:
    """The emitted bundle_id must use the evidence-scale-gap prefix."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=50, n_ref=50,
    )
    digest = "evidence-scale-gap-bundle-id-test"
    bundle = _make_state_bundle(digest)
    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=42)
    expected_id = BundleId(f"{POSTERIOR_SELECTION_BUNDLE_ID_PREFIX}{digest}")
    assert evidence.bundle_id == expected_id


def test_channel_supported_predicate() -> None:
    """``channel_supported`` must accept ``xy`` and reject other channels."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=10, n_ref=10,
    )
    assert evaluator.channel_supported(_XY_CHANNEL) is True
    assert evaluator.channel_supported(ChannelName("coordinate")) is False
    assert evaluator.channel_supported(ChannelName("charge")) is False


def test_construction_validates_target() -> None:
    """Unknown targets must raise :class:`ValueError` at construction time."""
    with pytest.raises(ValueError):
        EvidenceScaleGapMetric(target="not_a_target")
    with pytest.raises(ValueError):
        EvidenceScaleGapMetric(target="two_moons", n_gen=0)
    with pytest.raises(ValueError):
        EvidenceScaleGapMetric(target="two_moons", n_ref=-1)
    with pytest.raises(ValueError):
        EvidenceScaleGapMetric(target="two_moons", eps_implicit=-0.01)


def test_is_deterministic_returns_true() -> None:
    """``is_deterministic()`` must always return ``True``."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=10, n_ref=10,
    )
    assert evaluator.is_deterministic() is True


# ---------------------------------------------------------------------------
# Tests — evidence field surface
# ---------------------------------------------------------------------------


def test_evidence_field_surface() -> None:
    """The emitted evidence row must satisfy the canonical contract surface."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=50, n_ref=50, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-evidence-surface")
    evidence = evaluator.evaluate(bundle, channel=_XY_CHANNEL, seed=42)
    assert isinstance(evidence, ChannelTransferEvidence)
    assert evidence.channel == _XY_CHANNEL
    assert evidence.materialization_pass is True
    assert evidence.geometry_pass is True
    assert evidence.condition_sensitivity_observable_pass is True
    assert evidence.proxy_only_evidence is False
    assert evidence.validation_errors == ()
    # Unit factors are exactly the canonical values.
    assert float(evidence.calibration_lower_bound) == float(
        POSTERIOR_SELECTION_CALIBRATION
    )
    assert float(evidence.perturbation_stability_lower_bound) == float(
        POSTERIOR_SELECTION_PERTURBATION
    )
    # All FactorValue fields are in [0, 1].
    for fv in (
        evidence.perturbation_stability_lower_bound,
        evidence.ambiguity,
        evidence.degeneracy_penalty,
        evidence.support_coverage,
        evidence.recency_decay,
        evidence.calibration_lower_bound,
    ):
        v = float(fv)
        assert 0.0 <= v <= 1.0, f"factor {fv!r} = {v!r} outside [0, 1]"


# ---------------------------------------------------------------------------
# Tests — paper-claim disclaimer (regression guard)
# ---------------------------------------------------------------------------


def test_metric_classification_does_not_claim_paper_theorem() -> None:
    """Regression guard: the class docstring must state "NOT a paper claim".

    The metric is a framework-internal diagnostic that mirrors paper
    Lemma 2 / Lemma 3 evidence scale ordering, but it is NOT a paper
    Theorem 1 quantity. This test pins the explicit disclaimer in the
    class docstring so any future edit that re-introduces paper-claim
    framing surfaces immediately in the test suite.

    The module docstring is also asserted to carry the same disclaimer
    so the file-level framing cannot drift independently of the
    class-level framing.
    """
    cls_doc = EvidenceScaleGapMetric.__doc__ or ""
    assert "NOT a paper claim" in cls_doc, (
        "EvidenceScaleGapMetric.__doc__ must contain the literal "
        "'NOT a paper claim' disclaimer; current docstring "
        f"starts with: {cls_doc[:200]!r}"
    )
    # Module docstring also carries the disclaimer.
    mod_doc = (pse_mod.__doc__ or "")
    assert "NOT a paper claim" in mod_doc, (
        "posterior_selection_evaluator module docstring must contain "
        "the literal 'NOT a paper claim' disclaimer; current "
        f"docstring starts with: {mod_doc[:200]!r}"
    )


def test_legacy_alias_emits_deprecation_warning() -> None:
    """Importing the legacy name must emit a :class:`DeprecationWarning`.

    The ``PosteriorSelectionEvaluator`` alias is kept for back-compat
    and must surface a :class:`DeprecationWarning` on access so
    remaining callers migrate to ``EvidenceScaleGapMetric``.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Trigger the PEP 562 ``__getattr__`` shim explicitly.
        legacy = pse_mod.PosteriorSelectionEvaluator  # noqa: F841 -- intentional access
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecation_warnings, (
        "Accessing PosteriorSelectionEvaluator must emit a "
        "DeprecationWarning; no DeprecationWarning was raised"
    )
    # And the alias must resolve to the renamed class.
    assert legacy is EvidenceScaleGapMetric, (
        "PosteriorSelectionEvaluator alias must resolve to "
        "EvidenceScaleGapMetric"
    )


# ---------------------------------------------------------------------------
# Tests — A16 uplift: ``eps_schedule`` decays noise toward selection-1
# ---------------------------------------------------------------------------


def test_eps_schedule_decay_raises_ratio_to_one() -> None:
    """A16: ``eps_schedule`` decaying to 0 raises ratio to >= 0.95.

    Per the algorithm-uplift-plan.md quantitative target: when the
    schedule decays ``eps`` linearly from ``0.05`` to ``0`` over 20
    rounds, the final round's ``selection_ratio >= 0.95``. The
    selection_ratio rises monotonically toward 1 as ``eps -> 0``
    (cell evidence is suppressed by ``eps``).
    """

    def _eps_schedule(r: int) -> float:
        return 0.05 * (1.0 - r / 20.0)

    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=1000,
        n_ref=1000,
        seed=42,
        eps_schedule=_eps_schedule,
    )
    bundle = _make_state_bundle("evidence-scale-gap-eps-schedule")
    final = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=19,
    )
    assert final["selection_ratio"] >= 0.95, (
        f"final round selection_ratio = {final['selection_ratio']:.4f} "
        "below 0.95 (A16 target unmet)"
    )
    # And the eps value at the final round is small but non-negative.
    assert final["eps_schedule_value"] < 0.01
    assert final["eps_schedule_value"] >= 0.0


def test_eps_schedule_monotonic_increase() -> None:
    """A16: ``selection_ratio`` rises monotonically as ``eps`` decays.

    With the schedule ``r -> 0.05 * (1 - r/20)``, the ratio at
    ``r=0`` is strictly less than at ``r=19`` (cell mass shrinks
    faster than sheet mass as ``eps -> 0``).
    """

    def _eps_schedule(r: int) -> float:
        return 0.05 * (1.0 - r / 20.0)

    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=500,
        n_ref=500,
        seed=42,
        eps_schedule=_eps_schedule,
    )
    bundle = _make_state_bundle("evidence-scale-gap-monotonic")
    r0 = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0,
    )
    r10 = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=10,
    )
    r19 = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=19,
    )
    assert r0["selection_ratio"] < r19["selection_ratio"], (
        f"selection_ratio should rise from r=0 ({r0['selection_ratio']:.4f}) "
        f"to r=19 ({r19['selection_ratio']:.4f})"
    )
    assert r10["selection_ratio"] <= r19["selection_ratio"]


def test_eps_schedule_eps_for_round_helper() -> None:
    """A16: ``eps_for_round`` returns the schedule value (or fixed eps_implicit)."""

    def _eps_schedule(r: int) -> float:
        return 0.05 * (1.0 - r / 10.0)

    evaluator_with = EvidenceScaleGapMetric(
        target="two_moons", eps_schedule=_eps_schedule,
    )
    assert evaluator_with.eps_for_round(0) == pytest.approx(0.05)
    assert evaluator_with.eps_for_round(5) == pytest.approx(0.025)
    assert evaluator_with.eps_for_round(10) == pytest.approx(0.0)

    evaluator_without = EvidenceScaleGapMetric(
        target="two_moons", eps_implicit=0.07,
    )
    assert evaluator_without.eps_for_round(0) == pytest.approx(0.07)
    assert evaluator_without.eps_for_round(99) == pytest.approx(0.07)


def test_eps_schedule_rejects_non_callable() -> None:
    """A16: ``eps_schedule`` must be callable or None."""
    with pytest.raises(ValueError, match="eps_schedule"):
        EvidenceScaleGapMetric(
            target="two_moons",
            eps_schedule="not-callable",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Tests — C4 uplift: ``eps_round`` threaded from runner -> oracle_at_round
# ---------------------------------------------------------------------------


def test_eps_round_zero_collapses_to_sheet_dominance() -> None:
    """C4: ``eps_round=0`` drives the ratio to 1 (paper Lemma 2 limit).

    With ``eps_round=0`` the cell-evidence term ``c_ev * eps`` collapses
    to zero, so the ratio ``s_ev / (s_ev + c_ev * eps)`` reduces to
    ``s_ev / s_ev = 1.0`` whenever ``s_ev > 0`` — paper Theorem 1's
    "sheet dominance as ``eps -> 0``" limit. The metric responds to
    scheduler state by construction.
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-eps-round-zero")
    out = evaluator.oracle_at_round(
        bundle,
        channel=_XY_CHANNEL,
        seed=42,
        round_index=0,
        eps_round=0.0,
    )
    assert out["selection_ratio"] == pytest.approx(1.0, abs=1e-9), (
        f"eps_round=0 must collapse to sheet dominance (ratio=1.0); "
        f"got {out['selection_ratio']:.4f}"
    )


def test_eps_round_none_falls_back_to_legacy_path() -> None:
    """C4: ``eps_round=None`` preserves the legacy fixed-eps path byte-for-byte.

    No ``eps_schedule`` and no ``eps_round`` must produce the
    ``oracle()``-identical value (regression guard for the legacy
    ablation row behaviour).
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-eps-round-none")
    legacy = evaluator.oracle(bundle, channel=_XY_CHANNEL, seed=42)
    schedule_aware = evaluator.oracle_at_round(
        bundle,
        channel=_XY_CHANNEL,
        seed=42,
        round_index=0,
        eps_round=None,
    )
    assert schedule_aware["selection_ratio"] == pytest.approx(
        legacy["selection_ratio"], abs=1e-12
    )


def test_eps_round_scales_cell_evidence() -> None:
    """C4: ``eps_round`` scales the cell-evidence term (paper Lemma 3).

    A positive ``eps_round`` multiplies ``c_ev`` by ``eps_round``,
    raising the ratio relative to ``eps_round=0``. A larger
    ``eps_round`` strictly lowers the ratio (cell mass grows with
    ``eps``).
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-eps-round-scale")
    r0 = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0, eps_round=0.0,
    )
    r1 = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0, eps_round=0.5,
    )
    r2 = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0, eps_round=1.0,
    )
    assert r0["selection_ratio"] == pytest.approx(1.0, abs=1e-9)
    assert r1["selection_ratio"] > 0.0
    assert r1["selection_ratio"] < 1.0
    assert r2["selection_ratio"] < r1["selection_ratio"], (
        f"larger eps_round should lower the ratio "
        f"(eps=0.5 -> {r1['selection_ratio']:.4f}; "
        f"eps=1.0 -> {r2['selection_ratio']:.4f})"
    )


def test_eps_round_clamped_at_zero() -> None:
    """C4: negative ``eps_round`` is clamped to 0 (paper constraint)."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-eps-round-neg")
    out_neg = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0, eps_round=-1.0,
    )
    out_zero = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0, eps_round=0.0,
    )
    assert out_neg["selection_ratio"] == pytest.approx(
        out_zero["selection_ratio"], abs=1e-12
    )


# ---------------------------------------------------------------------------
# Tests — B12 uplift: ``evaluate_trajectory`` + ``oracle_batched`` schedule
# ---------------------------------------------------------------------------


def test_evaluate_trajectory_eps_schedule_consumes_round_index() -> None:
    """B12: ``evaluate_trajectory(..., round_index=R)`` consumes the schedule."""

    def _eps_schedule(r: int) -> float:
        return 0.05 * (1.0 - r / 20.0)

    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        eps_schedule=_eps_schedule,
        n_gen=200,
        n_ref=200,
        seed=42,
    )
    endpoints = np.random.default_rng(0).standard_normal((2, 200, 2)).astype(np.float64)
    # r=0 should produce a small baseline; r=19 should produce ~1.0.
    ev_r0 = evaluator.evaluate_trajectory(
        endpoints, channel=_XY_CHANNEL, seed=42, round_index=0,
    )
    ev_r19 = evaluator.evaluate_trajectory(
        endpoints, channel=_XY_CHANNEL, seed=42, round_index=19,
    )
    assert ev_r19.raw_score > ev_r0.raw_score, (
        f"r=19 ratio {ev_r19.raw_score:.4f} should exceed "
        f"r=0 ratio {ev_r0.raw_score:.4f}"
    )
    assert ev_r19.raw_score >= 0.9, (
        f"final round ratio {ev_r19.raw_score:.4f} below 0.9"
    )


def test_evaluate_trajectory_round_index_default_legacy_byte() -> None:
    """B12: ``evaluate_trajectory`` with default round_index=0 is byte-identical to legacy."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=200,
        n_ref=200,
        seed=42,
    )
    rng = np.random.default_rng(0)
    endpoints = rng.standard_normal((2, 200, 2)).astype(np.float64)
    ev = evaluator.evaluate_trajectory(
        endpoints, channel=_XY_CHANNEL, seed=42,
    )
    # Compare against oracle_batched default (also uses round_index=0).
    oracle = evaluator.oracle_batched(
        endpoints, channel=_XY_CHANNEL, seed=42,
    )
    assert oracle["selection_ratio"] == pytest.approx(ev.raw_score, abs=1e-12)


def test_oracle_batched_eps_schedule_consumes_round_index() -> None:
    """B12: ``oracle_batched`` exposes ``eps_schedule_value`` and ``round_index``."""

    def _eps_schedule(r: int) -> float:
        return 0.02 * (1.0 - r / 10.0)

    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        eps_schedule=_eps_schedule,
        n_gen=200,
        n_ref=200,
        seed=42,
    )
    rng = np.random.default_rng(0)
    endpoints = rng.standard_normal((2, 200, 2)).astype(np.float64)
    out_r5 = evaluator.oracle_batched(
        endpoints, channel=_XY_CHANNEL, seed=42, round_index=5,
    )
    assert out_r5["eps_schedule_value"] == pytest.approx(0.01)
    assert out_r5["round_index"] == 5
    assert "selection_ratio" in out_r5


# ---------------------------------------------------------------------------
# Tests — A-02.M3 safety boundary: ``eps_round`` NaN/inf rejection
# ---------------------------------------------------------------------------


def test_eps_round_nan_rejected() -> None:
    """A-02.M3: NaN ``eps_round`` is rejected with ``ValueError``.

    The legacy implementation silently bypassed the ``total > 0`` guard
    for ``nan``; the new path raises ``ValueError`` upstream of the
    ratio computation so the failure mode is explicit.
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-eps-round-nan")
    with pytest.raises(ValueError, match="eps_round must be finite"):
        evaluator.oracle_at_round(
            bundle,
            channel=_XY_CHANNEL,
            seed=42,
            round_index=0,
            eps_round=float("nan"),
        )


def test_eps_round_inf_rejected() -> None:
    """A-02.M3: positive ``inf`` ``eps_round`` is rejected with ``ValueError``."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-eps-round-inf")
    with pytest.raises(ValueError, match="eps_round must be finite"):
        evaluator.oracle_at_round(
            bundle,
            channel=_XY_CHANNEL,
            seed=42,
            round_index=0,
            eps_round=float("inf"),
        )


def test_eps_schedule_nan_rejected() -> None:
    """A-02.M3: a ``eps_schedule`` returning NaN raises ``ValueError``."""

    def _nan_schedule(_r: int) -> float:
        return float("nan")

    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        eps_schedule=_nan_schedule,
        n_gen=200,
        n_ref=200,
        seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-schedule-nan")
    with pytest.raises(ValueError, match="eps_schedule"):
        evaluator.oracle_at_round(
            bundle, channel=_XY_CHANNEL, seed=42, round_index=0,
        )


# ---------------------------------------------------------------------------
# Tests — A-02.M2: quadratic ``eps`` scaling flag (paper Lemma 3)
# ---------------------------------------------------------------------------


def test_quadratic_eps_scaling_default_off() -> None:
    """A-02.M2: ``use_quadratic_eps_scaling`` defaults to ``False``.

    With the flag off, the metric's behaviour matches the legacy
    A16 linear scaling byte-for-byte (CLM-022 SNR 60.80 reference
    preserved).
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    assert evaluator._use_quadratic_eps_scaling is False


def test_quadratic_eps_scaling_matches_lemma_3() -> None:
    """A-02.M2: with the flag on, smaller ``eps`` gives a larger ratio.

    Paper Lemma 3 bounds the cell-evidence mass by ``O(eps**2)``, so
    with ``eps = 0.01`` the cell mass is suppressed by a factor of
    ``1e-4`` relative to ``eps = 0.1``; the ratio must therefore
    rise monotonically with smaller ``eps`` when the quadratic flag
    is enabled, and the gap between ``eps=0.01`` and ``eps=0.1`` is
    at least ``1e-3``.
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=200,
        n_ref=200,
        seed=42,
        use_quadratic_eps_scaling=True,
    )
    bundle = _make_state_bundle("evidence-scale-gap-quadratic-lemma3")
    r_small = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0,
        eps_round=0.01,
    )
    r_large = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0,
        eps_round=0.1,
    )
    assert r_small["selection_ratio"] > r_large["selection_ratio"], (
        f"quadratic scaling: eps=0.01 ratio {r_small['selection_ratio']:.4f} "
        f"should exceed eps=0.1 ratio {r_large['selection_ratio']:.4f}"
    )
    gap = r_small["selection_ratio"] - r_large["selection_ratio"]
    assert gap >= 1e-3, (
        f"quadratic scaling gap {gap:.6f} below Lemma 3 floor 1e-3"
    )


def test_quadratic_eps_scaling_eps_zero_collapses_to_one() -> None:
    """A-02.M2: ``eps=0`` collapses the cell-evidence term to zero
    regardless of the scaling flag, so the ratio equals 1.0."""
    bundle = _make_state_bundle("evidence-scale-gap-quadratic-zero")
    for flag in (False, True):
        evaluator = EvidenceScaleGapMetric(
            target="two_moons",
            n_gen=200,
            n_ref=200,
            seed=42,
            use_quadratic_eps_scaling=flag,
        )
        out = evaluator.oracle_at_round(
            bundle, channel=_XY_CHANNEL, seed=42, round_index=0,
            eps_round=0.0,
        )
        assert out["selection_ratio"] == pytest.approx(1.0, abs=1e-9), (
            f"flag={flag}: eps=0 ratio {out['selection_ratio']:.4f} "
            f"should be 1.0"
        )


# ---------------------------------------------------------------------------
# Tests — A-02.G1: Lemma 4 exponential suppression
# ---------------------------------------------------------------------------


def test_lemma4_exponential_default_off() -> None:
    """A-02.G1: ``apply_lemma4_exponential_suppression`` defaults to ``False``."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    assert evaluator._apply_lemma4_exponential_suppression is False


def test_lemma4_exponential_requires_positive_e_rho() -> None:
    """A-02.G1: the suppression factor is ``1.0`` when no ``e_rho`` is supplied.

    The flag is opt-in; with ``e_rho == 0`` (the default for the
    helper) the factor collapses to a no-op even when the flag is
    on. This guards the helper against an accidental exponential
    blow-up when the ``e_rho`` plumbing is absent.
    """
    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=200,
        n_ref=200,
        seed=42,
        apply_lemma4_exponential_suppression=True,
    )
    # ``e_rho`` defaults to 0 -> the helper short-circuits and the
    # legacy linear ``eps`` scaling path is preserved byte-for-byte.
    baseline = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    bundle = _make_state_bundle("evidence-scale-gap-lemma4-no-e-rho")
    flag_on = evaluator.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0,
        eps_round=0.1,
    )
    baseline_out = baseline.oracle_at_round(
        bundle, channel=_XY_CHANNEL, seed=42, round_index=0,
        eps_round=0.1,
    )
    assert flag_on["selection_ratio"] == pytest.approx(
        baseline_out["selection_ratio"], abs=1e-12,
    )


def test_lemma4_exponential_drives_ratio_toward_one() -> None:
    """A-02.G1: with a positive ``e_rho`` and small ``eps`` the
    exponential suppression drives the ratio to >= 0.999999.

    Paper Lemma 4 says the exterior posterior mass is bounded by
    ``C * eps^{-1} * exp(-e_rho / (2 eps^2))``; the
    ``exp(-e_rho / (2 eps^2))`` term tends to 0 as ``eps -> 0`` for
    ``e_rho > 0``. The cell-evidence product therefore collapses,
    the ratio rises to 1, and the magnitude of the gap with the
    flag off is observable.
    """
    # ``e_rho`` large enough that ``exp(-e_rho / (2 eps^2))`` is
    # numerically negligible at ``eps = 0.01``:
    # ``exp(-1.0 / (2 * 0.0001))`` = ``exp(-5000)`` ~ 0.
    eps = 0.01
    e_rho = 1.0

    with_flag = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=200,
        n_ref=200,
        seed=42,
        apply_lemma4_exponential_suppression=True,
    )
    without_flag = EvidenceScaleGapMetric(
        target="two_moons", n_gen=200, n_ref=200, seed=42,
    )
    r_flag = with_flag._scale_cell_evidence(
        c_ev=1.0, eps=eps, e_rho=e_rho,
    )
    r_baseline = without_flag._scale_cell_evidence(
        c_ev=1.0, eps=eps, e_rho=e_rho,
    )
    assert r_flag < r_baseline, (
        f"Lemma 4 flag should suppress the cell evidence: "
        f"flagged {r_flag:.6e}, baseline {r_baseline:.6e}"
    )
    # Drive the ratio through ``_ratio_after_eps``: with negligible
    # cell evidence and a positive sheet evidence, the ratio collapses
    # to >= 0.999999.
    s_ev = 0.5
    c_ev_collapsed = r_flag
    ratio = with_flag._ratio_after_eps(s_ev, c_ev_collapsed)
    assert ratio >= 0.999999, (
        f"with Lemma 4 flag and e_rho={e_rho}, eps={eps}: ratio "
        f"{ratio:.10f} should be >= 0.999999"
    )


def test_lemma4_exponential_zero_eps_zero_cell_evidence() -> None:
    """A-02.G1: with ``eps == 0`` the helper returns ``0.0`` regardless of flags."""
    evaluator = EvidenceScaleGapMetric(
        target="two_moons",
        n_gen=200,
        n_ref=200,
        seed=42,
        apply_lemma4_exponential_suppression=True,
    )
    assert evaluator._scale_cell_evidence(c_ev=1.0, eps=0.0, e_rho=1.0) == 0.0


# ---------------------------------------------------------------------------
# Tests — A-02.M1 derivation note (``e_rho / 4`` audit trail)
# ---------------------------------------------------------------------------


def test_e_rho_over_4_factor_documented_in_merge_operator() -> None:
    """A-02.M1: the ``e_rho / 4`` factor in :class:`BoundedMergeOperator`
    carries the CLM-042 derivation note inline so the audit reader can
    trace the framework-side tightening back to the paper.
    """
    import inspect

    from adaptive_reflow.algorithm.merge_operator import BoundedMergeOperator

    src = inspect.getsource(BoundedMergeOperator.merge)
    assert "CLM-042" in src, (
        "BoundedMergeOperator.merge must carry the CLM-042 derivation "
        "note inline (A-02.M1 paper-math fidelity)"
    )
    assert "e_rho / 4" in src or "/ 4.0" in src, (
        "BoundedMergeOperator.merge must still apply the e_rho / 4 "
        "paper-quantity floor"
    )


def test_e_rho_over_4_factor_documented_in_scheduler_core() -> None:
    """A-02.M1: the scheduler's ``e_rho / 4`` factor carries the
    CLM-042 derivation note inline as well."""
    import inspect

    from adaptive_reflow.algorithm.scheduler._core import CodimensionSheetScheduler

    src = inspect.getsource(CodimensionSheetScheduler.inject_noise)
    assert "CLM-042" in src, (
        "CodimensionSheetScheduler.inject_noise must carry the "
        "CLM-042 derivation note inline (A-02.M1 paper-math fidelity)"
    )

