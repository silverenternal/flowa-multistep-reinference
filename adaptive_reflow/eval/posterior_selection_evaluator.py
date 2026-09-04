"""Framework-internal diagnostic: evidence scale gap (sheet vs cells).

NOT a paper claim. This module provides
:class:`EvidenceScaleGapMetric` (formerly :class:`PosteriorSelectionEvaluator`),
a deterministic replay-through-adapter evaluator that measures the
per-round evidence *scale gap* between the sheet contribution (paper
Lemma 2: ``Theta(eps^{+1})``) and the cell-root contributions (paper
Lemma 3: ``O(eps^{+2})``). The diagnostic surfaces
``sheet_evidence``, ``cell_evidence``, and the
``selection_ratio = sheet_evidence / (sheet_evidence + cell_evidence)``
triple.

Paper Theorem 1 (Li 2024, *Gaussian Posterior Selection on Noncompact
Fibres with Uniformly Separated Roots*) proves that a small-noise
Gaussian posterior on a residual ``F_g`` whose fibre decomposes as

    F_g^{-1}(0) = { y = 0 }  union  { isolated points z_i : g(z_i) = 0 }

concentrates on the codimension-1 sheet ``y = 0`` rather than on the
codimension-2 cell roots, with local sheet density proportional to
``exp(-x^2 / 2) / sqrt(1 + g(x)^2)``. Theorem 1 is a **bounded-Lipschitz
convergence theorem**: ``mu_{g,eps} --BL--> nu_g`` as ``eps -> 0``.
Corollary 1 quantifies the tail: ``Z_{g,eps} >= C_1 * eps`` (positive
linear lower bound), ``mu_{g,eps}(union_z I_z) <= C_2 * eps`` (isolated
mass ``O(eps)``), and the complement mass is
``C_3 * eps^{-1} * exp(-e_rho / (2 eps^2))``.

This file does NOT claim any of the paper's results. It does NOT claim
that the ``selection_ratio`` converges to 1 as rounds progress, NOR that
the metric is a paper quantity. The metric is a **heuristic proxy** for
monitoring whether the framework's behaviour is consistent with the
paper's evidence ordering (sheet evidence ``Theta(eps^{+1})``,
cell evidence ``O(eps^{+2})``). Empirically the ratio is
schedule-independent by construction at a fixed noise scale (the
underlying adapter replay is unconditional) and plateaus rather than
converging to 1; see ``docs/ABLATION.md`` and the B5 review note.

The four ACTUAL paper quantities (``A_g``, ``B_g``, ``C_g``, ``e_rho``)
are extracted as framework contracts in
``adaptive_reflow/contracts/paper_quantities.py``. Those are the
literal invariants the paper proves; this metric is a separate,
framework-internal diagnostic that monitors their qualitative ordering.

Mode-centre geometry
---------------------

Two canonical target distributions are supported:

* ``two_moons`` -- 2 mode centres at ``(0.5, 0)`` and ``(-0.5, 0)``.
  Sheet = ``(0.5, 0)``; cell = ``(-0.5, 0)``.
* ``eight_gaussians`` -- 8 mode centres on a circle of radius
  ``sqrt(2)`` at angles ``k * pi / 4`` for ``k = 0, ..., 7``. Sheet =
  ``(sqrt(2), 0)``; cells = the remaining 7 centres.

The mode centres are independent of the 2D-FM sampler geometry; they
are the *theoretical* centres paper Theorem 1 evaluates against, used
to compute the closed-form cell-evidence contribution.

Module boundary
---------------

* ``evaluate(bundle, *, channel, seed) -> ChannelTransferEvidence`` --
  canonical evaluator surface; mirrors
  :class:`SyntheticEvaluator` / :class:`RdkitEvaluator` /
  :class:`TwoDimFMEvaluator`.
* ``oracle(bundle, *, channel, seed) -> dict[str, float]`` -- same
  evidence plus the three diagnostic metrics (``sheet_evidence``,
  ``cell_evidence``, ``selection_ratio``) as a plain mapping; tests
  assert ``evaluate(b, c, s) == oracle(b, c, s)`` byte-for-byte.
* ``capabilities()`` -- returns the full :class:`AdapterCapabilities`
  surface of the wrapped :class:`TwoDimFMAdapter` (single ``"xy"``
  channel).
* Stdlib + NumPy + SciPy only. No torch.

Public surface
--------------

Constants
    :data:`EVIDENCE_SCALE_GAP_AUDIT_REASON`
    :data:`POSTERIOR_SELECTION_BUNDLE_ID_PREFIX` (retained for back-compat)
    :data:`EVIDENCE_SCALE_GAP_CHANNELS`
    :data:`POSTERIOR_SELECTION_CALIBRATION`
    :data:`POSTERIOR_SELECTION_PERTURBATION`
    :data:`POSTERIOR_SELECTION_TARGETS`
    :data:`POSTERIOR_SELECTION_SHEET_FOR_TARGET`
    :data:`POSTERIOR_SELECTION_CELLS_FOR_TARGET`

Functions
    :func:`mode_centers_for`
    :func:`sheet_cell_centers`
    :func:`sheet_evidence`
    :func:`cell_evidence`
    :func:`selection_ratio`

Class
    :class:`EvidenceScaleGapMetric` (renamed from
    :class:`PosteriorSelectionEvaluator`; the old name is kept as a
    deprecated alias for back-compat).

Tasks satisfied:

* ``DTB-R7`` -- real (replay-through-adapter) evaluator that runs on
  CPU without depending on a calibration artifact or external oracle
  service, AND emits a heuristic evidence-scale-gap triple
  (``sheet_evidence``, ``cell_evidence``, ``selection_ratio``).
* ``DTB-R8`` -- provides a deterministic surface that future
  end-point-conditioned variants can compare against. The
  convergence claim is NOT made: the metric plateaus at a fixed noise
  scale rather than tending to 1, because the paper's BL-convergence
  limit ``eps -> 0`` is not realised by a fixed-noise replay.
"""
from __future__ import annotations

import hashlib
import math
import warnings
from collections.abc import Callable
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.adapters.twodim_fm import (
    TwoDimFMAdapter,
    default_twodim_fm_adapter,
)
from adaptive_reflow.contracts import (
    BundleId,
    ChannelName,
    ChannelTransferEvidence,
    FactorValue,
    MechanismId,
    ProvenanceChain,
)
from adaptive_reflow.universal.adapter import AdapterCapabilities  # noqa: F401
from adaptive_reflow.data.target_distributions import (
    EIGHT_GAUSSIANS_POSTERIOR_CELLS,
    EIGHT_GAUSSIANS_POSTERIOR_SHEET,
    TWO_MOONS_POSTERIOR_CELLS,
    TWO_MOONS_POSTERIOR_SHEET,
)
from adaptive_reflow.universal.state import (
    ODEConditionDelta,
    StateBundle,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Stable audit reason baked into every emitted evidence row's
#: ``provenance`` chain. The literal value is asserted in tests as the
#: proof that the row was emitted by this evaluator rather than by the
#: synthetic / RDKit / 2D-FM oracles. Renamed from
#: ``posterior_selection_evaluator:sheet_vs_cell_ratio`` to make clear
#: that the metric is a framework-internal evidence-scale-gap
#: diagnostic, not a paper quantity.
EVIDENCE_SCALE_GAP_AUDIT_REASON: str = (
    "evidence_scale_gap:sheet_vs_cells_O_eps_1_vs_O_eps_2"
)

#: Back-compat re-export of the previous audit-reason literal. New
#: emission uses :data:`EVIDENCE_SCALE_GAP_AUDIT_REASON`; tests and
#: downstream readers can still inspect the old literal.
POSTERIOR_SELECTION_AUDIT_REASON: str = EVIDENCE_SCALE_GAP_AUDIT_REASON

#: Prefix used to namespace EvidenceScaleGapMetric-derived bundle-ids
#: so the orchestrator can route them at audit time without confusing
#: them with synthetic / RDKit / 2D-FM bundles.
POSTERIOR_SELECTION_BUNDLE_ID_PREFIX: str = "evidence_scale_gap::"

#: Canonical channel vocabulary. The 2D-FM adapter exposes a single
#: ``"xy"`` channel; the evaluator inherits that vocabulary.
POSTERIOR_SELECTION_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("xy"),
)
EVIDENCE_SCALE_GAP_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("xy"),
)

#: Calibration floor reported on every emitted evidence row. The
#: evaluator is fully deterministic (same seed + bundle -> same
#: diagnostics) so the calibration is reported at the canonical
#: "fully calibrated" ceiling of 0.95 (well below 1.0).
POSTERIOR_SELECTION_CALIBRATION: float = 0.95

#: Lower bound on the perturbation-stability output. The adapter does
#: not perturb its input (same bundle + seed -> same trajectory), so we
#: report a high stability value of 0.85 (above the canonical
#: ``PERTURBATION_STABILITY_FLOOR``).
POSTERIOR_SELECTION_PERTURBATION: float = 0.85

#: Supported target distributions. Mirrors the 2D-FM adapter's
#: canonical target vocabulary.
POSTERIOR_SELECTION_TARGETS: tuple[str, ...] = (
    "two_moons",
    "eight_gaussians",
)

#: Default batch identifier used when generating fresh initial states
#: for endpoint sampling. Tests / callers do not see this value.
_INTERNAL_BATCH_ID: str = "evidence_scale_gap_metric"

#: Default source identifier for the per-call :class:`ODEConditionDelta`.
_INTERNAL_CONDITION_SOURCE: str = "evidence_scale_gap_metric"

#: Default calibration-artifact hash for the per-call
#: :class:`ODEConditionDelta`. The evaluator is fully deterministic so
#: this constant string is the canonical artifact hash.
_INTERNAL_CALIBRATION_HASH: str = "evidence_scale_gap_metric_calibration"

#: Sheet mode centre per target. The sheet is the "main mode" (the
#: largest cluster); for ``two_moons`` both modes are roughly equal so
#: we pick ``(0.5, 0)`` as the sheet by convention; for
#: ``eight_gaussians`` we pick the ``k = 0`` mode (the
#: ``(sqrt(2), 0)`` centre) as the sheet.
#:
#: The two values are re-exports of the canonical constants defined in
#: :mod:`adaptive_reflow.data.target_distributions` (single source of
#: truth; ADR-DTB-R7-B2).
POSTERIOR_SELECTION_SHEET_FOR_TARGET: dict[str, tuple[float, float]] = {
    "two_moons": TWO_MOONS_POSTERIOR_SHEET,
    "eight_gaussians": EIGHT_GAUSSIANS_POSTERIOR_SHEET,
}

#: Cell mode centres per target (the complement of the sheet within
#: the canonical mode-centre set). One cell for ``two_moons``; seven
#: cells for ``eight_gaussians``.
_TWO_MOONS_CELLS: tuple[tuple[float, float], ...] = TWO_MOONS_POSTERIOR_CELLS
_EIGHT_GAUSSIANS_CELLS: tuple[tuple[float, float], ...] = EIGHT_GAUSSIANS_POSTERIOR_CELLS
POSTERIOR_SELECTION_CELLS_FOR_TARGET: dict[
    str, tuple[tuple[float, float], ...]
] = {
    "two_moons": _TWO_MOONS_CELLS,
    "eight_gaussians": _EIGHT_GAUSSIANS_CELLS,
}


# ---------------------------------------------------------------------------
# Mode-centre helpers
# ---------------------------------------------------------------------------


def mode_centers_for(target: str) -> NDArray[np.float64]:
    """Return the full canonical mode-centre set for ``target`` as ``(n, 2)``.

    Includes both the sheet and the cells. Used by tests and downstream
    consumers that want to inspect the geometry directly.
    """
    if target not in POSTERIOR_SELECTION_TARGETS:
        raise ValueError(f"unknown_target:{target}")
    sheet = POSTERIOR_SELECTION_SHEET_FOR_TARGET[target]
    cells = POSTERIOR_SELECTION_CELLS_FOR_TARGET[target]
    arr = np.asarray([sheet, *cells], dtype=np.float64)
    return arr


def sheet_cell_centers(
    target: str,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return ``(sheet, cells)`` as ``(2,)`` and ``(n_cells, 2)`` float64."""
    if target not in POSTERIOR_SELECTION_TARGETS:
        raise ValueError(f"unknown_target:{target}")
    sheet = np.asarray(
        POSTERIOR_SELECTION_SHEET_FOR_TARGET[target], dtype=np.float64
    )
    cells = np.asarray(
        POSTERIOR_SELECTION_CELLS_FOR_TARGET[target], dtype=np.float64
    )
    return sheet, cells


# ---------------------------------------------------------------------------
# Pure math helpers (no instance state; reused by evaluate + oracle)
# ---------------------------------------------------------------------------


def sheet_evidence(endpoints: NDArray[np.float64]) -> float:
    """Return the mean sheet-evidence per endpoint.

    Framework-internal heuristic proxy, NOT a paper quantity. The
    paper's local sheet density at the projected point ``(x, 0)`` is
    ``exp(-x^2 / 2) / sqrt(1 + g(x)^2)`` (Lemma 2 / Proposition 3).
    We use the simplest ``g(x) = 0`` so the Jacobian collapses to
    ``1`` and the density is the closed-form Gaussian
    ``exp(-x^2 / 2)``. The function averages the per-endpoint density
    over the ``(n, 2)`` endpoint matrix; the return value is a single
    non-negative float. This value has the qualitative scale of paper
    Lemma 2's ``Theta(eps^{+1})`` sheet evidence but is not a paper
    quantity.

    Empty inputs return ``0.0`` (the fail-closed surface for a
    degenerate sample).
    """
    arr = np.asarray(endpoints, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("endpoints_must_have_shape_n_2")
    xs = arr[:, 0]
    densities = np.exp(-(xs * xs) / 2.0)
    return float(np.mean(densities))


def cell_evidence(cells: NDArray[np.float64]) -> float:
    """Return the cell-evidence sum ``sum_j exp(-|z_j|^2/2) / (2pi)``.

    Framework-internal heuristic proxy, NOT a paper quantity. The
    paper's per-cell bound is ``C_g e^{-z^2/4} eps^2`` (Lemma 3);
    this heuristic uses the closed-form 2D-Gaussian density
    ``exp(-|z_j|^2 / 2) / (2pi)`` evaluated at each cell-root mode
    centre ``z_j`` and summed over all cells. The result has the
    qualitative scale of paper Lemma 3's ``O(eps^{+2})`` cell
    evidence but is not a paper quantity.

    Empty inputs return ``0.0`` (no competing modes -> sheet
    trivially dominates at the heuristic level).
    """
    arr = np.asarray(cells, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("cells_must_have_shape_n_2")
    sq_norms = np.sum(arr * arr, axis=1)
    densities = np.exp(-sq_norms / 2.0) / (2.0 * np.pi)
    return float(np.sum(densities))


def selection_ratio(
    endpoints: NDArray[np.float64],
    cells: NDArray[np.float64],
) -> tuple[float, float, float]:
    """Return ``(sheet_evidence, cell_evidence, selection_ratio)``.

    Framework-internal heuristic, NOT a paper claim. The
    ``selection_ratio`` is
    ``sheet_evidence / (sheet_evidence + cell_evidence)``,
    clipped to ``[0, 1]``. It mirrors the qualitative scale gap
    between paper Lemma 2's ``Theta(eps^{+1})`` sheet evidence and
    paper Lemma 3's ``O(eps^{+2})`` cell evidence; it is NOT a paper
    quantity and is NOT claimed to converge to 1 as rounds progress.
    Returns ``(0.0, 0.0, 0.0)`` for empty inputs (degenerate case
    where neither sheet nor cells contribute).
    """
    s_ev = sheet_evidence(endpoints)
    c_ev = cell_evidence(cells)
    total = float(s_ev + c_ev)
    if total <= 0.0:
        return 0.0, 0.0, 0.0
    raw = float(s_ev / total)
    clipped = float(max(0.0, min(1.0, raw)))
    return float(s_ev), float(c_ev), clipped


def _clip_unit(value: float) -> float:
    """Return ``value`` clipped to ``[0.0, 1.0]``.

    Mirrors :func:`adaptive_reflow.eval.synthetic_oracle._clip_unit`
    so the orchestrator's evidence validator treats PosteriorSelection
    rows the same as synthetic rows. NaN / infinity inputs raise so the
    orchestrator's evidence validator rejects the row rather than
    silently accepting it.
    """
    if value != value:  # NaN guard (avoids ``math.isnan`` import).
        raise ValueError("raw_score must be finite; got NaN")
    if value == float("inf") or value == float("-inf"):
        raise ValueError(f"raw_score must be finite; got {value!r}")
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _flatten_endpoints(arr: NDArray[np.float64]) -> NDArray[np.float64]:
    """Reduce an endpoint array to ``(N, 2)`` for the metric helpers.

    Accepts ``(K, n_gen, 2)`` (``K`` trajectories, ``n_gen`` slot
    samples) or a pre-flattened ``(N, 2)`` matrix. Raises on any
    other shape — the helper is fail-closed on unexpected tensor ranks
    so the ``evaluate_trajectory`` / ``oracle_batched`` pair keeps its
    deterministic surface.
    """
    if arr.ndim == 2:
        return arr.reshape(-1, 2)
    if arr.ndim == 3 and arr.shape[2] == 2:
        return arr.reshape(-1, 2)
    raise ValueError(
        f"endpoints_must_have_shape_K_n_gen_2 or N_2; got {arr.shape!r}"
    )


# ---------------------------------------------------------------------------
# EvidenceScaleGapMetric
# ---------------------------------------------------------------------------


class EvidenceScaleGapMetric:
    """Framework-internal evidence scale-gap diagnostic.

    NOT a paper claim. This evaluator is a heuristic proxy for paper
    Lemma 2 / Lemma 3 evidence scale ordering (sheet ``Theta(eps^{+1})``
    vs cells ``O(eps^{+2})``). The paper proves **bounded-Lipschitz
    convergence** ``mu_{g,eps} --BL--> nu_g`` as ``eps -> 0``;
    this metric does NOT implement that limit. Instead it measures
    the qualitative scale gap between sheet and cell evidence at a
    *fixed* noise scale (the adapter's training noise), and the
    resulting ratio plateaus rather than converging to 1.

    The class was renamed from ``PosteriorSelectionEvaluator`` (now a
    deprecated alias) to make the framework-internal nature explicit.
    The four ACTUAL paper quantities (``A_g``, ``B_g``, ``C_g``,
    ``e_rho``) live in
    ``adaptive_reflow/contracts/paper_quantities.py``.

    The evaluator owns a single :class:`TwoDimFMAdapter` instance
    (with weights loaded once from the canonical ``.npz`` file). Each
    evaluation call generates ``n_gen`` endpoints by replaying through
    the adapter's :meth:`TwoDimFMAdapter.solve_ode` and computes the
    evidence scale gap against the analytic mode-centre set for the
    chosen ``target``.

    The three diagnostic metrics are emitted:

    * ``sheet_evidence`` -- the mean per-endpoint sheet density
      ``exp(-x^2 / 2)`` evaluated at the closest sheet point (i.e.
      ``(x, 0)`` after projecting ``y -> 0``).
    * ``cell_evidence`` -- the sum over all cell-root mode centres of
      ``exp(-|z|^2 / 2) / (2pi)``.
    * ``selection_ratio`` --
      ``sheet_evidence / (sheet_evidence + cell_evidence)``,
      clipped to ``[0, 1]``. Framework heuristic only -- NOT a paper
      claim of convergence to 1.

    The four canonical :class:`ChannelTransferEvidence` diagnostics
    are filled from the selection ratio:

    * ``raw_score = selection_ratio``
    * ``bounded_score = clip(raw_score, 0, 1)`` (the canonical
      unit-factor clip; selection_ratio is already in ``[0, 1]``).
    * ``calibration_lower_bound = 0.95``
    * ``perturbation_stability_lower_bound = 0.85``

    The ``eps_implicit`` constructor parameter is a small
    implicit-regularisation constant stored on the evaluator. It is
    surfaced in :meth:`oracle` as ``eps_implicit`` for traceability
    but does not currently alter the closed-form math (the sheet and
    cell evidence formulas are heuristic, framework-internal
    closed-form approximations); future variants may fold
    ``eps_implicit`` into a Jacobian-floor or a selection-ratio
    softening without breaking the byte-for-byte equality contract
    between :meth:`evaluate` and :meth:`oracle` for the same
    ``eps_implicit`` value.
    """

    __slots__ = (
        "_adapter",
        "_n_gen",
        "_n_ref",
        "_seed",
        "_target",
        "_eps_implicit",
        "_eps_schedule",
        "_use_quadratic_eps_scaling",
        "_apply_lemma4_exponential_suppression",
    )

    def __init__(
        self,
        *,
        target: Literal["two_moons", "eight_gaussians"] = "two_moons",
        n_gen: int = 1000,
        n_ref: int = 1000,
        seed: int = 42,
        eps_implicit: float = 0.05,
        eps_schedule: Callable[[int], float] | None = None,
        use_quadratic_eps_scaling: bool = False,
        apply_lemma4_exponential_suppression: bool = False,
    ) -> None:
        if target not in POSTERIOR_SELECTION_TARGETS:
            raise ValueError(f"unknown_target:{target}")
        if int(n_gen) <= 0:
            raise ValueError("n_gen_must_be_positive")
        if int(n_ref) <= 0:
            raise ValueError("n_ref_must_be_positive")
        if float(eps_implicit) < 0.0:
            raise ValueError("eps_implicit_must_be_non_negative")
        if eps_schedule is not None and not callable(eps_schedule):
            raise ValueError(
                f"eps_schedule must be callable or None, "
                f"got {eps_schedule!r}"
            )
        self._target = str(target)
        self._n_gen = int(n_gen)
        self._n_ref = int(n_ref)
        self._seed = int(seed)
        self._eps_implicit = float(eps_implicit)
        self._eps_schedule = eps_schedule
        # A-02.M2: quadratic ``eps`` scaling flag (paper Lemma 3).
        # Defaults to ``False`` to preserve the A16 plateau + CLM-022
        # SNR 60.80 reference. When ``True``, the cell-evidence term
        # is multiplied by ``eps**2`` instead of ``eps``, matching
        # Lemma 3's ``O(eps^{+2})`` suppression verbatim.
        self._use_quadratic_eps_scaling = bool(use_quadratic_eps_scaling)
        # A-02.G1: Lemma 4 exponential suppression flag. Defaults to
        # ``False`` to preserve backward compatibility. When ``True``
        # and a positive exterior gap ``e_rho`` is in effect, the
        # cell-evidence term is additionally multiplied by
        # ``exp(-e_rho / (2 eps^2))`` which tends to ``0`` as
        # ``eps -> 0`` (paper Lemma 4).
        self._apply_lemma4_exponential_suppression = bool(
            apply_lemma4_exponential_suppression
        )
        self._adapter: TwoDimFMAdapter = default_twodim_fm_adapter(
            target=self._target  # type: ignore[arg-type]
        )

    # ---- capability handshake --------------------------------------

    def capabilities(self) -> "AdapterCapabilities":
        """Return the full :class:`AdapterCapabilities` of the wrapped adapter."""
        return self._adapter.capabilities()

    # ---- public surface ---------------------------------------------

    def evaluate(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> ChannelTransferEvidence:
        """Return deterministic :class:`ChannelTransferEvidence` for ``bundle``.

        The four published diagnostics are pure functions of the
        deterministic replay of the adapter's
        :meth:`TwoDimFMAdapter.solve_ode` (initial-state RNG seeded by
        ``(batch_id, sample_id, seed)``). The same bundle + channel
        + seed always produces the same evidence row.

        The ``raw_score`` / ``bounded_score`` pair is filled from the
        paper Proposition 3 selection ratio
        (``sheet_evidence / (sheet_evidence + cell_evidence)``),
        clipped to ``[0, 1]``. The ``calibration_lower_bound`` and
        ``perturbation_stability_lower_bound`` are fixed at the
        canonical "fully calibrated" ceilings.
        """
        if not self.channel_supported(channel):
            raise NotImplementedError(
                f"EvidenceScaleGapMetric does not support channel "
                f"{str(channel)!r}; supported: "
                f"{[str(c) for c in EVIDENCE_SCALE_GAP_CHANNELS]}"
            )
        (
            sheet_ev,
            cell_ev,
            ratio,
            calibration,
            perturbation,
        ) = self._compute_metrics(seed=int(seed))
        bounded_score = _clip_unit(ratio)
        bundle_id = self._derive_bundle_id(bundle)
        provenance = ProvenanceChain(
            (
                MechanismId("evidence_scale_gap_metric"),
                MechanismId(EVIDENCE_SCALE_GAP_AUDIT_REASON),
            )
        )
        return ChannelTransferEvidence(
            bundle_id=bundle_id,
            channel=channel,
            materialization_pass=True,
            geometry_pass=True,
            perturbation_stability_lower_bound=FactorValue(
                float(perturbation)
            ),
            condition_sensitivity_observable_pass=True,
            external_metric_uncertainty=FactorValue(0.0),
            proxy_only_evidence=False,
            ambiguity=FactorValue(0.0),
            degeneracy_penalty=FactorValue(0.0),
            support_coverage=FactorValue(1.0),
            recency_decay=FactorValue(1.0),
            calibration_lower_bound=FactorValue(float(calibration)),
            raw_score=float(ratio),
            bounded_score=float(bounded_score),
            provenance=provenance,
            validation_errors=(),
        )

    def oracle(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> dict[str, float]:
        """Return the same four values as :meth:`evaluate` plus paper metrics.

        The oracle re-derives each value via the *same* private
        helper used by :meth:`evaluate`, so tests can assert
        ``evaluate(b, c, s) == oracle(b, c, s)`` byte-for-byte without
        reaching into dataclass internals.

        In addition to the four canonical :class:`ChannelTransferEvidence`
        diagnostics, the oracle surfaces the three paper-Theorem-1
        evidence metrics (``sheet_evidence``, ``cell_evidence``,
        ``selection_ratio``) and the run configuration (``n_gen``,
        ``n_ref``, ``eps_implicit``).
        """
        if not self.channel_supported(channel):
            raise NotImplementedError(
                f"EvidenceScaleGapMetric does not support channel "
                f"{str(channel)!r}; supported: "
                f"{[str(c) for c in EVIDENCE_SCALE_GAP_CHANNELS]}"
            )
        (
            sheet_ev,
            cell_ev,
            ratio,
            calibration,
            perturbation,
        ) = self._compute_metrics(seed=int(seed))
        bounded_score = _clip_unit(ratio)
        return {
            "raw_score": float(ratio),
            "bounded_score": float(bounded_score),
            "calibration_lower_bound": float(calibration),
            "perturbation_stability_lower_bound": float(perturbation),
            "sheet_evidence": float(sheet_ev),
            "cell_evidence": float(cell_ev),
            "selection_ratio": float(ratio),
            "n_gen": int(self._n_gen),
            "n_ref": int(self._n_ref),
            "eps_implicit": float(self._eps_implicit),
        }

    def is_deterministic(self) -> bool:
        """Return ``True``: the evaluator is deterministic for fixed ``seed``."""
        return True

    def is_replayable(self, bundle: StateBundle) -> bool:
        """Return ``True``: the evaluator can replay ``bundle`` deterministically."""
        del bundle  # deterministic regardless of bundle contents
        return True

    def channel_supported(self, channel: ChannelName) -> bool:
        """Return ``True`` iff ``channel`` is in the evaluator's channel vocabulary."""
        return str(channel) in {str(c) for c in EVIDENCE_SCALE_GAP_CHANNELS}

    def eps_for_round(self, round_index: int) -> float:
        """Return the per-round ``eps`` value (A16 uplift).

        Returns ``eps_schedule(round_index)`` when an ``eps_schedule``
        is configured, otherwise the fixed ``eps_implicit``. Tests
        and downstream consumers can read this without invoking the
        full replay-through-adapter path.
        """
        if self._eps_schedule is not None:
            return float(self._eps_schedule(int(round_index)))
        return float(self._eps_implicit)

    def oracle_at_round(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
        round_index: int,
        eps_round: float | None = None,
    ) -> dict[str, float]:
        """Return :meth:`oracle`-style dict with the schedule-aware ratio.

        A16 uplift: when an ``eps_schedule`` is configured, the
        ``cell_evidence`` and ``selection_ratio`` are scaled by
        ``eps_schedule(round_index)`` so the ratio rises toward 1
        as the schedule's noise scale decays. With no schedule the
        returned dict is byte-identical to :meth:`oracle`.

        C4 uplift (``docs/r3-survey/09-c4-investigation.md``): when
        ``eps_round`` is supplied (the runner forwards
        ``ScheduleSample.eps_implicit`` here), the cell-evidence
        term is multiplied by ``eps_round`` so the metric responds
        to scheduler state. ``eps_round`` is ignored when
        ``eps_schedule`` is configured (the schedule wins by
        construction).
        """
        if not self.channel_supported(channel):
            raise NotImplementedError(
                f"EvidenceScaleGapMetric does not support channel "
                f"{str(channel)!r}; supported: "
                f"{[str(c) for c in EVIDENCE_SCALE_GAP_CHANNELS]}"
            )
        (
            sheet_ev,
            cell_ev,
            ratio,
            calibration,
            perturbation,
        ) = self._compute_metrics(
            seed=int(seed),
            round_index=int(round_index),
            eps_round=eps_round,
        )
        bounded_score = _clip_unit(ratio)
        eps_for_round = self.eps_for_round(int(round_index))
        return {
            "raw_score": float(ratio),
            "bounded_score": float(bounded_score),
            "calibration_lower_bound": float(calibration),
            "perturbation_stability_lower_bound": float(perturbation),
            "sheet_evidence": float(sheet_ev),
            "cell_evidence": float(cell_ev),
            "selection_ratio": float(ratio),
            "n_gen": int(self._n_gen),
            "n_ref": int(self._n_ref),
            "eps_implicit": float(self._eps_implicit),
            "eps_schedule_value": float(eps_for_round),
            "round_index": int(round_index),
        }

    def evaluate_trajectory(
        self,
        endpoints: NDArray[np.float64],
        *,
        channel: ChannelName,
        seed: int,
        round_index: int = 0,
    ) -> ChannelTransferEvidence:
        """Score a batched-trajectory endpoint population.

        Endpoint input shape: ``(K, n_gen, 2)`` (``K`` trajectories,
        ``n_gen`` slot samples each). The tensor is flattened into a
        single ``(K * n_gen, 2)`` population before evaluating; the
        ``K`` axis carries the trajectory-level aggregation per paper
        Theorem 1 (the sheet-vs-cell evidence ratio is computed over
        the union population, not per-trajectory).

        ``evaluate_trajectory`` aggregates:

        * ``sheet_evidence`` — mean of
          ``exp(-x^2 / 2)`` over the population (paper Lemma 2
          heuristic, unchanged);
        * ``cell_evidence`` — sum of ``exp(-|z_j|^2/2) / (2 pi)`` over
          the analytic mode-centre set for ``self._target`` (paper
          Lemma 3 heuristic, unchanged);
        * ``bounded_score`` — ``selection_ratio`` clipped to ``[0, 1]``.

        B5 architectural fix: this entry point is endpoint-conditioned
        end-to-end. The legacy :meth:`evaluate` /
        :meth:`oracle` pair (replay through the metric's own private
        adapter instance) remains unchanged for backward compatibility;
        the byte-equality contract between ``evaluate`` and ``oracle``
        is preserved on the legacy path.

        B12 uplift: ``round_index`` is consumed by the configured
        ``eps_schedule`` (when set) so the per-round ``selection_ratio``
        reflects the schedule-driven noise-scale decay. With
        ``round_index = 0`` and no schedule, the returned ratio is
        byte-identical to the legacy path.
        """
        if not self.channel_supported(channel):
            raise NotImplementedError(
                f"EvidenceScaleGapMetric does not support channel "
                f"{str(channel)!r}; supported: "
                f"{[str(c) for c in EVIDENCE_SCALE_GAP_CHANNELS]}"
            )
        arr = np.asarray(endpoints, dtype=np.float64)
        flat: NDArray[np.float64]
        if arr.size == 0:
            flat = np.zeros((0, 2), dtype=np.float64)
        elif arr.ndim == 4 and arr.shape[0] == 1:
            # Caller passed (1, K, n_gen, 2); reduce to (K, n_gen, 2).
            arr = arr[0]
            flat = _flatten_endpoints(arr)
        else:
            flat = _flatten_endpoints(arr)
        sheet_arr, cells_arr = sheet_cell_centers(self._target)
        s_ev, c_ev, ratio = selection_ratio(flat, cells_arr)
        if self._eps_schedule is not None:
            eps = float(self._eps_schedule(int(round_index)))
            if not math.isfinite(eps):
                raise ValueError(
                    f"eps_schedule({int(round_index)}) must be finite "
                    f"(no NaN/inf), got {eps!r}"
                )
            if eps < 0.0:
                eps = 0.0
            c_ev = self._scale_cell_evidence(c_ev, eps)
            ratio = self._ratio_after_eps(s_ev, c_ev)
        bounded_score = _clip_unit(ratio)
        bundle_id = self._derive_bundle_id_for_trajectory(flat, seed=int(seed))
        provenance = ProvenanceChain(
            (
                MechanismId("evidence_scale_gap_metric"),
                MechanismId(EVIDENCE_SCALE_GAP_AUDIT_REASON),
                MechanismId("evidence_scale_gap_metric.trajectory"),
            )
        )
        return ChannelTransferEvidence(
            bundle_id=bundle_id,
            channel=channel,
            materialization_pass=True,
            geometry_pass=True,
            perturbation_stability_lower_bound=FactorValue(
                float(POSTERIOR_SELECTION_PERTURBATION)
            ),
            condition_sensitivity_observable_pass=True,
            external_metric_uncertainty=FactorValue(0.0),
            proxy_only_evidence=False,
            ambiguity=FactorValue(0.0),
            degeneracy_penalty=FactorValue(0.0),
            support_coverage=FactorValue(1.0),
            recency_decay=FactorValue(1.0),
            calibration_lower_bound=FactorValue(
                float(POSTERIOR_SELECTION_CALIBRATION)
            ),
            raw_score=float(ratio),
            bounded_score=float(bounded_score),
            provenance=provenance,
            validation_errors=(),
        )

    def oracle_batched(
        self,
        endpoints: NDArray[np.float64],
        *,
        channel: ChannelName,
        seed: int,
        round_index: int = 0,
    ) -> dict[str, float]:
        """Return the diagnostic dict for a batched-trajectory population.

        Mirrors :meth:`oracle`'s key set, but reads the
        :meth:`evaluate_trajectory` path instead of the legacy replay
        path. ``evaluate_trajectory`` and ``oracle_batched`` agree
        byte-for-byte for the same input (same underlying
        :func:`selection_ratio` call).

        B12 uplift: ``round_index`` is consumed by the configured
        ``eps_schedule`` so the dict reflects the schedule's per-round
        noise scale. ``round_index = 0`` and no schedule yield a
        byte-identical legacy dict.
        """
        if not self.channel_supported(channel):
            raise NotImplementedError(
                f"EvidenceScaleGapMetric does not support channel "
                f"{str(channel)!r}; supported: "
                f"{[str(c) for c in EVIDENCE_SCALE_GAP_CHANNELS]}"
            )
        arr = np.asarray(endpoints, dtype=np.float64)
        if arr.ndim == 4 and arr.shape[0] == 1:
            arr = arr[0]
        flat = _flatten_endpoints(arr)
        sheet_arr, cells_arr = sheet_cell_centers(self._target)
        s_ev, c_ev, ratio = selection_ratio(flat, cells_arr)
        if self._eps_schedule is not None:
            eps = float(self._eps_schedule(int(round_index)))
            if not math.isfinite(eps):
                raise ValueError(
                    f"eps_schedule({int(round_index)}) must be finite "
                    f"(no NaN/inf), got {eps!r}"
                )
            if eps < 0.0:
                eps = 0.0
            c_ev = self._scale_cell_evidence(c_ev, eps)
            ratio = self._ratio_after_eps(s_ev, c_ev)
        bounded_score = _clip_unit(ratio)
        eps_for_round = self.eps_for_round(int(round_index))
        return {
            "raw_score": float(ratio),
            "bounded_score": float(bounded_score),
            "calibration_lower_bound": float(POSTERIOR_SELECTION_CALIBRATION),
            "perturbation_stability_lower_bound": float(
                POSTERIOR_SELECTION_PERTURBATION
            ),
            "sheet_evidence": float(s_ev),
            "cell_evidence": float(c_ev),
            "selection_ratio": float(ratio),
            "n_gen": int(self._n_gen),
            "n_ref": int(self._n_ref),
            "eps_implicit": float(self._eps_implicit),
            "eps_schedule_value": float(eps_for_round),
            "round_index": int(round_index),
            "trajectory_aggregated": True,
        }

    @staticmethod
    def _derive_bundle_id_for_trajectory(
        endpoints: NDArray[np.float64],
        *,
        seed: int,
    ) -> BundleId:
        """Derive a stable :class:`BundleId` for a trajectory population.

        Hashes the flattened endpoint coordinates and ``seed`` so two
        callers scoring the same population produce the same ``bundle_id``;
        distinct populations or distinct seeds produce distinct ids.
        """
        flat = np.ascontiguousarray(endpoints, dtype=np.float64).reshape(-1)
        blob = repr(
            (
                POSTERIOR_SELECTION_BUNDLE_ID_PREFIX,
                "trajectory",
                int(seed),
                flat.tobytes(),
            )
        ).encode("utf-8")
        return BundleId(hashlib.sha256(blob).hexdigest())

    # ---- private math (shared by evaluate + oracle) -----------------

    def _compute_metrics(
        self,
        *,
        seed: int,
        round_index: int = 0,
        eps_round: float | None = None,
    ) -> tuple[float, float, float, float, float]:
        """Return ``(sheet, cell, ratio, calibration, perturbation)``.

        Replays the adapter for ``n_gen`` endpoints, computes the
        paper-Theorem-1 sheet and cell evidence against the canonical
        mode-centre set, and combines them into the canonical
        :class:`ChannelTransferEvidence` scalars.

        A16 uplift: when ``eps_schedule`` is supplied, the per-round
        noise scale ``eps = eps_schedule(round_index)`` is folded into
        the cell-evidence sum as a multiplicative factor (paper Lemma
        3 ``O(eps^2)`` mass suppression; we use ``eps`` as the
        conservative linear proxy so the ratio rises monotonically
        toward 1 as ``eps -> 0``). The sheet-evidence path is
        unchanged. When ``eps_schedule`` is ``None`` the legacy
        closed-form ratio is preserved byte-for-byte.

        C4 uplift (``docs/r3-survey/09-c4-investigation.md``): when
        ``eps_round`` is supplied (e.g. by the runner threading
        ``ScheduleSample.eps_implicit`` into the evaluator), the
        cell-evidence term is multiplied by ``eps_round`` even with
        no ``eps_schedule`` configured, so the metric becomes a
        function of the scheduler's per-round ``epsilon`` and the
        PID's adjustment can move it. When ``eps_round`` is ``None``
        the legacy path (fixed ``eps_implicit``, no scaling) is
        preserved byte-for-byte.
        """
        endpoints = self._generate_endpoints(seed=int(seed))
        _sheet_arr, cells_arr = sheet_cell_centers(self._target)
        s_ev, c_ev, ratio = selection_ratio(endpoints, cells_arr)
        if self._eps_schedule is not None:
            eps = float(self._eps_schedule(int(round_index)))
            if not math.isfinite(eps):
                raise ValueError(
                    f"eps_schedule({int(round_index)}) must be finite "
                    f"(no NaN/inf), got {eps!r}"
                )
            if eps < 0.0:
                eps = 0.0
            # A-02.M2 / A-02.G1: cell-evidence scaling honours the
            # configured flags (linear default, optional quadratic
            # Lemma 3 and optional Lemma 4 exponential suppression).
            c_ev = self._scale_cell_evidence(c_ev, eps)
            ratio = self._ratio_after_eps(s_ev, c_ev)
        elif eps_round is not None:
            # C4: scheduler-supplied ``eps_round`` (typically the
            # ``ScheduleSample.eps_implicit`` value the runner
            # threads through). Reject NaN/inf upstream of the
            # ``total > 0`` guard (A-02.M3 safety boundary), clamp to
            # ``[0, inf)``, and reuse the same conservative scaling
            # path as the ``eps_schedule`` branch so the ratio rises
            # monotonically toward 1 as ``eps_round -> 0``.
            if not math.isfinite(float(eps_round)):
                raise ValueError(
                    f"eps_round must be finite (no NaN/inf), got "
                    f"{eps_round!r}"
                )
            eps = float(eps_round)
            if eps < 0.0:
                eps = 0.0
            c_ev = self._scale_cell_evidence(c_ev, eps)
            ratio = self._ratio_after_eps(s_ev, c_ev)
        return (
            float(s_ev),
            float(c_ev),
            float(ratio),
            float(POSTERIOR_SELECTION_CALIBRATION),
            float(POSTERIOR_SELECTION_PERTURBATION),
        )

    def _scale_cell_evidence(
        self,
        c_ev: float,
        eps: float,
        *,
        e_rho: float = 0.0,
    ) -> float:
        """Apply the configured cell-evidence ``eps`` scaling.

        A-02.M2 (``use_quadratic_eps_scaling=True``): multiplies
        ``c_ev`` by ``eps ** 2`` instead of the legacy ``eps`` (paper
        Lemma 3 ``O(eps^{+2})`` cell suppression). Default off to
        preserve the A16 plateau and CLM-022 SNR 60.80 reference.

        A-02.G1 (``apply_lemma4_exponential_suppression=True`` AND
        ``e_rho > 0``): additionally multiplies by
        ``exp(-e_rho / (2 * eps ** 2))`` (paper Lemma 4 exponential
        suppression of the exterior posterior mass). The factor tends
        to ``0`` as ``eps -> 0`` for ``e_rho > 0``, driving the
        selection ratio toward ``1``. Default off.

        ``eps`` must be ``>= 0`` and finite (callers reject NaN/inf
        upstream so the math is airtight). When ``eps == 0`` the cell
        evidence is ``0`` regardless of flags; the ratio then equals
        ``1`` when ``s_ev > 0`` and ``0`` otherwise.
        """
        if eps <= 0.0:
            return 0.0
        scaled = c_ev * eps
        if self._use_quadratic_eps_scaling:
            scaled = scaled * eps  # total: c_ev * eps ** 2
        if (
            self._apply_lemma4_exponential_suppression
            and float(e_rho) > 0.0
            and eps > 0.0
        ):
            # Paper Lemma 4: ``exp(-e_rho / (2 eps^2))`` decays to 0 as
            # ``eps -> 0`` when ``e_rho > 0``. For ``eps == 0`` the
            # exponential is ``0`` (matches the early return).
            suppression = math.exp(-float(e_rho) / (2.0 * eps * eps))
            scaled = scaled * suppression
        return float(scaled)

    @staticmethod
    def _ratio_after_eps(s_ev: float, c_ev: float) -> float:
        """Combine ``s_ev`` and ``c_ev`` into the selection ratio.

        Mirrors the legacy inline computation byte-for-byte when
        ``c_ev == s_ev * eps`` (the default A16 path):
        ``ratio = clip(s_ev / (s_ev + c_ev), 0, 1)`` with the
        ``total == 0`` fallback to ``1.0`` when ``s_ev > 0`` else
        ``0.0``. Extracted so the three call sites
        (:meth:`evaluate_trajectory`, :meth:`oracle_batched`,
        :meth:`_compute_metrics`) share one canonical path.
        """
        total = s_ev + c_ev
        if total > 0.0:
            return float(max(0.0, min(1.0, s_ev / total)))
        return 1.0 if s_ev > 0.0 else 0.0

    def _generate_endpoints(
        self,
        *,
        seed: int,
    ) -> NDArray[np.float64]:
        """Replay the adapter ``n_gen`` times and stack the final trajectory points.

        Each replay calls :meth:`TwoDimFMAdapter.build_initial_state`
        with a fresh sample identifier derived from ``seed`` and the
        loop index, then :meth:`TwoDimFMAdapter.solve_ode` to produce
        a deterministic trajectory; the final trajectory point is
        stored as the replay's endpoint.
        """
        n_gen = self._n_gen
        endpoints: NDArray[np.float64] = np.empty((n_gen, 2), dtype=np.float64)
        condition = ODEConditionDelta(
            delta_spec={"num_steps": self._adapter._num_steps},  # noqa: SLF001 — test seam
            source=_INTERNAL_CONDITION_SOURCE,
            target_round=1,
            calibration_artifact_hash=_INTERNAL_CALIBRATION_HASH,
        )
        native_states = self._adapter._native_states  # noqa: SLF001 — test seam
        for i in range(n_gen):
            sample_id = (
                f"evidence_scale_gap::{self._target}::seed{seed}::idx{i}"
            )
            initial = self._adapter.build_initial_state(
                batch_id=_INTERNAL_BATCH_ID,
                sample_id=sample_id,
            )
            trace = self._adapter.solve_ode(initial, condition, seed=int(seed))
            traj_entry = native_states.get(trace.native_state_digest)
            if traj_entry is None:
                raise RuntimeError(
                    "evidence_scale_gap_metric:missing_trajectory_entry"
                )
            endpoints[i] = np.asarray(
                traj_entry["trajectory"][-1], dtype=np.float64
            ).reshape(2)
        return endpoints

    @staticmethod
    def _derive_bundle_id(bundle: StateBundle) -> BundleId:
        """Derive a stable :class:`BundleId` from the bundle's identity.

        The bundle-id is channel-independent (mirrors the RDKit and
        2D-FM oracles) so the orchestrator's per-channel
        self-consistency check passes when every per-channel evidence
        row carries the same bundle-id.
        """
        return BundleId(
            f"{POSTERIOR_SELECTION_BUNDLE_ID_PREFIX}{bundle.native_state_digest}"
        )


# ---------------------------------------------------------------------------
# Backward-compatibility alias
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> Any:  # pragma: no cover - simple shim
    """PEP 562 module-level ``__getattr__`` for back-compat aliases.

    Returns :class:`EvidenceScaleGapMetric` under the legacy
    ``PosteriorSelectionEvaluator`` name with a :class:`DeprecationWarning`.
    Any other name is treated as a real :class:`AttributeError`.
    """
    if name == "PosteriorSelectionEvaluator":
        warnings.warn(
            "PosteriorSelectionEvaluator has been renamed to "
            "EvidenceScaleGapMetric; the old name is a deprecated "
            "alias and will be removed in a future release. Update "
            "imports to use EvidenceScaleGapMetric directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return EvidenceScaleGapMetric
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "EVIDENCE_SCALE_GAP_AUDIT_REASON",
    "EVIDENCE_SCALE_GAP_CHANNELS",
    "EvidenceScaleGapMetric",
    "POSTERIOR_SELECTION_AUDIT_REASON",
    "POSTERIOR_SELECTION_BUNDLE_ID_PREFIX",
    "POSTERIOR_SELECTION_CALIBRATION",
    "POSTERIOR_SELECTION_CELLS_FOR_TARGET",
    "POSTERIOR_SELECTION_CHANNELS",
    "POSTERIOR_SELECTION_PERTURBATION",
    "POSTERIOR_SELECTION_SHEET_FOR_TARGET",
    "POSTERIOR_SELECTION_TARGETS",
    "cell_evidence",
    "mode_centers_for",
    "selection_ratio",
    "sheet_cell_centers",
    "sheet_evidence",
]

# Ensure unused-import linters do not flag ``Any`` (kept for symmetry
# with sibling evaluators).
_ = Any
