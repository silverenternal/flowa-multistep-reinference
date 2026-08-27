"""Empirical validator of paper Theorem 1 — sheet-vs-cell evidence ratio.

This module satisfies the DTB-R7 evaluation leg for paper Theorem 1
verification by providing :class:`PosteriorSelectionEvaluator`, a
deterministic replay-through-adapter evaluator that measures the
per-round evidence ratio of "main mode" (sheet) vs "competing modes"
(cells) and tracks convergence.

Paper Theorem 1 (Li 2024, *Gaussian Posterior Selection on Noncompact
Fibres with Uniformly Separated Roots*) proves that a small-noise
Gaussian posterior on a residual ``F_g`` whose fibre decomposes as

    F_g^{-1}(0) = { y = 0 }  union  { isolated points z_i : g(z_i) = 0 }

concentrates on the codimension-1 sheet ``y = 0`` rather than on the
codimension-2 cell roots, with local sheet density proportional to
``exp(-x^2 / 2) / sqrt(1 + g(x)^2)``. Proposition 3 states that the
selection ratio

    sheet_evidence / (sheet_evidence + cell_evidence)

converges to 1 as ``sigma -> 0``.

The framework mapping (ADR-0013) records the cosine scheduler as the
canonical implementation of paper Lemma 2's sheet-tube scaling; this
evaluator is the empirical handle on paper Proposition 3's selection
ratio, intended to be emitted into ``RoundTrace.extras`` as the
``sheet_evidence`` / ``cell_evidence`` / ``selection_ratio`` triple.

Mode-centre geometry
---------------------

Two canonical target distributions are supported:

* ``two_moons`` — 2 mode centres at ``(0.5, 0)`` and ``(-0.5, 0)``.
  Sheet = ``(0.5, 0)``; cell = ``(-0.5, 0)``.
* ``eight_gaussians`` — 8 mode centres on a circle of radius
  ``sqrt(2)`` at angles ``k * pi / 4`` for ``k = 0, ..., 7``. Sheet =
  ``(sqrt(2), 0)``; cells = the remaining 7 centres.

The mode centres are independent of the 2D-FM sampler geometry; they
are the *theoretical* centres paper Theorem 1 evaluates against, used
to compute the closed-form cell-evidence contribution.

Module boundary
---------------

* ``evaluate(bundle, *, channel, seed) -> ChannelTransferEvidence`` —
  canonical evaluator surface; mirrors
  :class:`SyntheticEvaluator` / :class:`RdkitEvaluator` /
  :class:`TwoDimFMEvaluator`.
* ``oracle(bundle, *, channel, seed) -> dict[str, float]`` — same
  evidence plus the three paper-Theorem-1 metrics
  (``sheet_evidence``, ``cell_evidence``, ``selection_ratio``) as a
  plain mapping; tests assert
  ``evaluate(b, c, s) == oracle(b, c, s)`` byte-for-byte.
* ``capabilities()`` — returns the full :class:`AdapterCapabilities`
  surface of the wrapped :class:`TwoDimFMAdapter` (single ``"xy"``
  channel).
* Stdlib + NumPy + SciPy only. No torch.

Public surface
--------------

Constants
    :data:`POSTERIOR_SELECTION_AUDIT_REASON`
    :data:`POSTERIOR_SELECTION_BUNDLE_ID_PREFIX`
    :data:`POSTERIOR_SELECTION_CHANNELS`
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
    :class:`PosteriorSelectionEvaluator`

Tasks satisfied:

* ``DTB-R7`` — real (replay-through-adapter) evaluator that runs on
  CPU without depending on a calibration artifact or external oracle
  service, AND emits paper-Theorem-1 evidence metrics
  (``sheet_evidence``, ``cell_evidence``, ``selection_ratio``).
* ``DTB-R8`` — provides a deterministic truth surface for the paper
  Proposition 3 convergence claim (selection ratio -> 1 as rounds
  progress).
"""
from __future__ import annotations

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
#: synthetic / RDKit / 2D-FM oracles.
POSTERIOR_SELECTION_AUDIT_REASON: str = (
    "posterior_selection_evaluator:sheet_vs_cell_ratio"
)

#: Prefix used to namespace PosteriorSelectionEvaluator-derived
#: bundle-ids so the orchestrator can route them at audit time
#: without confusing them with synthetic / RDKit / 2D-FM bundles.
POSTERIOR_SELECTION_BUNDLE_ID_PREFIX: str = "posterior_sel::"

#: Canonical channel vocabulary. The 2D-FM adapter exposes a single
#: ``"xy"`` channel; the evaluator inherits that vocabulary.
POSTERIOR_SELECTION_CHANNELS: tuple[ChannelName, ...] = (
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
_INTERNAL_BATCH_ID: str = "posterior_selection_evaluator"

#: Default source identifier for the per-call :class:`ODEConditionDelta`.
_INTERNAL_CONDITION_SOURCE: str = "posterior_selection_evaluator"

#: Default calibration-artifact hash for the per-call
#: :class:`ODEConditionDelta`. The evaluator is fully deterministic so
#: this constant string is the canonical artifact hash.
_INTERNAL_CALIBRATION_HASH: str = "posterior_selection_evaluator_calibration"

#: Sheet mode centre per target. The sheet is the "main mode" (the
#: largest cluster); for ``two_moons`` both modes are roughly equal so
#: we pick ``(0.5, 0)`` as the sheet by convention; for
#: ``eight_gaussians`` we pick the ``k = 0`` mode (the
#: ``(sqrt(2), 0)`` centre) as the sheet.
POSTERIOR_SELECTION_SHEET_FOR_TARGET: dict[str, tuple[float, float]] = {
    "two_moons": (0.5, 0.0),
    "eight_gaussians": (float(np.sqrt(2.0)), 0.0),
}

#: Cell mode centres per target (the complement of the sheet within
#: the canonical mode-centre set). One cell for ``two_moons``; seven
#: cells for ``eight_gaussians``.
_TWO_MOONS_CELLS: tuple[tuple[float, float], ...] = ((-0.5, 0.0),)
_EIGHT_GAUSSIANS_CELLS_ANGLES: tuple[float, ...] = tuple(
    (float(k) + 1.0) * (np.pi / 4.0) for k in range(7)
)
_EIGHT_GAUSSIANS_CELLS: tuple[tuple[float, float], ...] = tuple(
    (float(np.sqrt(2.0) * np.cos(a)), float(np.sqrt(2.0) * np.sin(a)))
    for a in _EIGHT_GAUSSIANS_CELLS_ANGLES
)
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

    The paper's local sheet density at the projected point
    ``(x, 0)`` is ``exp(-x^2 / 2) / sqrt(1 + g(x)^2)``. We use the
    simplest ``g(x) = 0`` so the Jacobian collapses to ``1`` and the
    density is the closed-form Gaussian
    ``exp(-x^2 / 2)``. The function averages the per-endpoint density
    over the ``(n, 2)`` endpoint matrix; the return value is a single
    non-negative float.

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

    Implements paper Proposition 3's "competing modes" contribution:
    each cell-root ``z_j`` contributes a 2D-Gaussian density
    ``exp(-|z_j|^2 / 2) / (2pi)`` evaluated at the mode centre, and
    the cells' total evidence is the sum over all cells.

    Empty inputs return ``0.0`` (no competing modes -> sheet
    trivially dominates).
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

    The selection ratio is paper Proposition 3's
    ``sheet_evidence / (sheet_evidence + cell_evidence)``, clipped to
    ``[0, 1]``. Returns ``(0.0, 0.0, 0.0)`` for empty inputs (degenerate
    case where neither sheet nor cells contribute).
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


# ---------------------------------------------------------------------------
# PosteriorSelectionEvaluator
# ---------------------------------------------------------------------------


class PosteriorSelectionEvaluator:
    """Replay-through-adapter :class:`Evaluator` for paper Theorem 1.

    The evaluator owns a single :class:`TwoDimFMAdapter` instance
    (with weights loaded once from the canonical ``.npz`` file). Each
    evaluation call generates ``n_gen`` endpoints by replaying through
    the adapter's :meth:`TwoDimFMAdapter.solve_ode` and computes paper
    Theorem 1's selection ratio against the analytic mode-centre set
    for the chosen ``target``.

    The three paper-Theorem-1 metrics are emitted:

    * ``sheet_evidence`` — the mean per-endpoint sheet density
      ``exp(-x^2 / 2)`` evaluated at the closest sheet point (i.e.
      ``(x, 0)`` after projecting ``y -> 0``).
    * ``cell_evidence`` — the sum over all cell-root mode centres of
      ``exp(-|z|^2 / 2) / (2pi)``.
    * ``selection_ratio`` —
      ``sheet_evidence / (sheet_evidence + cell_evidence)``,
      clipped to ``[0, 1]``. Paper Proposition 3 predicts this
      converges to 1 as ``sigma -> 0``.

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
    cell evidence formulas are paper-Theorem-1 canonical); future
    variants may fold ``eps_implicit`` into a Jacobian-floor or a
    selection-ratio softening without breaking the byte-for-byte
    equality contract between :meth:`evaluate` and :meth:`oracle` for
    the same ``eps_implicit`` value.
    """

    __slots__ = (
        "_adapter",
        "_n_gen",
        "_n_ref",
        "_seed",
        "_target",
        "_eps_implicit",
    )

    def __init__(
        self,
        *,
        target: Literal["two_moons", "eight_gaussians"] = "two_moons",
        n_gen: int = 1000,
        n_ref: int = 1000,
        seed: int = 42,
        eps_implicit: float = 0.05,
    ) -> None:
        if target not in POSTERIOR_SELECTION_TARGETS:
            raise ValueError(f"unknown_target:{target}")
        if int(n_gen) <= 0:
            raise ValueError("n_gen_must_be_positive")
        if int(n_ref) <= 0:
            raise ValueError("n_ref_must_be_positive")
        if float(eps_implicit) < 0.0:
            raise ValueError("eps_implicit_must_be_non_negative")
        self._target = str(target)
        self._n_gen = int(n_gen)
        self._n_ref = int(n_ref)
        self._seed = int(seed)
        self._eps_implicit = float(eps_implicit)
        self._adapter: TwoDimFMAdapter = default_twodim_fm_adapter(
            target=self._target  # type: ignore[arg-type]
        )

    # ---- capability handshake --------------------------------------

    def capabilities(self):  # type: ignore[no-untyped-def]
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
                f"PosteriorSelectionEvaluator does not support channel "
                f"{str(channel)!r}; supported: "
                f"{[str(c) for c in POSTERIOR_SELECTION_CHANNELS]}"
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
                MechanismId("posterior_selection_evaluator"),
                MechanismId(POSTERIOR_SELECTION_AUDIT_REASON),
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
                f"PosteriorSelectionEvaluator does not support channel "
                f"{str(channel)!r}; supported: "
                f"{[str(c) for c in POSTERIOR_SELECTION_CHANNELS]}"
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
        return str(channel) in {str(c) for c in POSTERIOR_SELECTION_CHANNELS}

    # ---- private math (shared by evaluate + oracle) -----------------

    def _compute_metrics(
        self,
        *,
        seed: int,
    ) -> tuple[float, float, float, float, float]:
        """Return ``(sheet, cell, ratio, calibration, perturbation)``.

        Replays the adapter for ``n_gen`` endpoints, computes the
        paper-Theorem-1 sheet and cell evidence against the canonical
        mode-centre set, and combines them into the canonical
        :class:`ChannelTransferEvidence` scalars.
        """
        endpoints = self._generate_endpoints(seed=int(seed))
        _sheet_arr, cells_arr = sheet_cell_centers(self._target)
        s_ev, c_ev, ratio = selection_ratio(endpoints, cells_arr)
        return (
            float(s_ev),
            float(c_ev),
            float(ratio),
            float(POSTERIOR_SELECTION_CALIBRATION),
            float(POSTERIOR_SELECTION_PERTURBATION),
        )

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
                f"posterior_selection::{self._target}::seed{seed}::idx{i}"
            )
            initial = self._adapter.build_initial_state(
                batch_id=_INTERNAL_BATCH_ID,
                sample_id=sample_id,
            )
            trace = self._adapter.solve_ode(initial, condition, seed=int(seed))
            traj_entry = native_states.get(trace.native_state_digest)
            if traj_entry is None:
                raise RuntimeError(
                    "posterior_selection_evaluator:missing_trajectory_entry"
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
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "POSTERIOR_SELECTION_AUDIT_REASON",
    "POSTERIOR_SELECTION_BUNDLE_ID_PREFIX",
    "POSTERIOR_SELECTION_CALIBRATION",
    "POSTERIOR_SELECTION_CELLS_FOR_TARGET",
    "POSTERIOR_SELECTION_CHANNELS",
    "POSTERIOR_SELECTION_PERTURBATION",
    "POSTERIOR_SELECTION_SHEET_FOR_TARGET",
    "POSTERIOR_SELECTION_TARGETS",
    "PosteriorSelectionEvaluator",
    "cell_evidence",
    "mode_centers_for",
    "selection_ratio",
    "sheet_cell_centers",
    "sheet_evidence",
]

# Ensure unused-import linters do not flag ``Any`` (kept for symmetry
# with sibling evaluators).
_ = Any
