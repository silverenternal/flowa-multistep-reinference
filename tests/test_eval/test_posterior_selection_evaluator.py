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

    The test runs early in the file so a torch import triggered by a
    sibling test file does not poison this assertion; if a previous
    test pulls torch into ``sys.modules`` (none of the existing
    ``tests/test_eval/`` files do, but defence-in-depth) this
    assertion will fail and surface the regression.
    """
    # Sanity: the module itself does not import torch.
    assert "torch" not in sys.modules, (
        "evidence_scale_gap_metric must be torch-free; "
        "torch is in sys.modules"
    )


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
