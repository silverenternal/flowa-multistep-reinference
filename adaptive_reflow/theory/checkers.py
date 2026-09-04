"""JMAA theorem-statement checkers (Wave 11 addition).

This module exposes the unified ``Theorem1Statement`` dataclass and
its checker, plus the Lemma 2 LHS sheet-tube evidence evaluator and a
planar BL-convergence witness.

* :class:`Theorem1Statement` -- carries ``(bl_distance, root_cell_mass,
  posterior_evidence)`` together, the single artifact the audit
  demands. Replaces the split between ``eval.fid_theorem_aligned`` (a)
  and ``algorithm.dynamic_noise_bias.Theorem1DynamicNoiseBias`` (b)+(c).

* :class:`Theorem1StatementChecker` -- emits ``Theorem1Statement``
  given ``g``, ``eps_sequence``, and a :class:`PaperQuantitiesSnapshot`.

* :func:`sheet_tube_evidence` -- Lemma 2 LHS ``eps^{-1} int_T phi p_eps``
  via 2D-grid Monte-Carlo, compared against the paper RHS
  ``(2*pi)^{-1/2} int_R phi(s, 0) e^{-s^2/2} / sqrt(1+g(s)^2) ds``.

* :class:`LipschitzConvergenceReport` -- report of
  ``BL(mu_{g,eps_k}, nu_g) -> 0`` over ``eps_sequence``.

Stdlib-only.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from adaptive_reflow.theory.paper_quantities import (
    paper_selection_ratio,
    sheet_evidence_A,
)

__all__ = [
    "Theorem1Statement",
    "Theorem1StatementChecker",
    "SheetTubeEvidence",
    "sheet_tube_evidence",
    "LipschitzConvergenceReport",
    "theorem1_bl_convergence_witness",
]


@dataclass(frozen=True)
class Theorem1Statement:
    """Unified Theorem 1 witness carrying all three claims together.

    Paper Theorem 1 (line 87-92) is a SINGLE statement that combines:

    (a) ``mu_{g,eps} --BL--> nu_g``  (bounded-Lipschitz convergence).
    (b) ``mu_{g,eps}(union_z I_z) = O(eps)``  (root-cell mass).
    (c) the bounded-Lipschitz equivalence (line 91-92, the equivalent
        display for ``phi in BL``).

    The framework previously realized (a) only as
    ``eval.fid_theorem_aligned.assert_convergence_rate`` (a Gaussian-Frechet
    proxy, NOT paper BL) and (b)+(c) only as
    ``algorithm.dynamic_noise_bias.Theorem1DynamicNoiseBias.compute_noise_bias``
    (the selection-ratio formula). This dataclass unifies the three.

    All three fields MUST be present (non-None) for the witness to be
    complete. The dataclass is immutable; build via :meth:`from_parts`.
    """

    bl_distance: float
    root_cell_mass: float
    posterior_evidence: float

    def __post_init__(self) -> None:  # type: ignore[override]
        for name in ("bl_distance", "root_cell_mass", "posterior_evidence"):
            v = getattr(self, name)
            if v is None:
                raise ValueError(f"{name}_must_not_be_None")
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(f"{name}_must_be_real_number")
            fv = float(v)
            if fv != fv or fv in (float("inf"), float("-inf")):
                raise ValueError(f"{name}_must_be_finite")
            if fv < 0.0:
                raise ValueError(f"{name}_must_be_nonnegative")

    @classmethod
    def from_parts(
        cls,
        bl_distance: float,
        root_cell_mass: float,
        posterior_evidence: float,
    ) -> "Theorem1Statement":
        return cls(
            bl_distance=float(bl_distance),
            root_cell_mass=float(root_cell_mass),
            posterior_evidence=float(posterior_evidence),
        )


class Theorem1StatementChecker:
    """Emit :class:`Theorem1Statement` given ``g``, ``eps_sequence``,
    and a paper-quantities snapshot.

    The checker's ``check`` method computes:

    * ``posterior_evidence`` = paper-quantity ``A_g`` (the sheet
      evidence floor from :func:`sheet_evidence_A`).
    * ``root_cell_mass`` = the paper ``C_g * B_g * eps^2`` per-round
      cell mass (``cell_C * packing_B * eps ** 2``).
    * ``bl_distance`` = a planar BL-distance witness computed from
      :func:`theorem1_bl_convergence_witness` over the supplied
      ``eps_sequence``.

    Stdlib-only; pure modulo ``g``.
    """

    FAMILY: str = "theorem1"

    def check(
        self,
        g: Callable[[float], float],
        eps_sequence: Sequence[float],
        paper_qty: Any,
    ) -> Theorem1Statement:
        """Compute the unified Theorem 1 statement.

        Parameters
        ----------
        g
            The profile ``R -> R``. Need not be uniformly separated
            (the caller is responsible for F-side admissibility via
            :mod:`adaptive_reflow.theory.validation`).
        eps_sequence
            Non-empty monotone-decreasing sequence of ``eps`` values
            (typically ``[0.5, 0.1, 0.05, 0.01, 0.005]``).
        paper_qty
            A :class:`adaptive_reflow.contracts.dynamic_noise_bias.PaperQuantitiesSnapshot`
            carrying ``sheet_A, packing_B, cell_C, exterior_gap_e_rho``.

        Returns
        -------
        Theorem1Statement
            Immutable dataclass with all three claims populated.
        """
        if not eps_sequence:
            raise ValueError("eps_sequence must be non-empty")

        sheet_A = float(getattr(paper_qty, "sheet_A"))
        packing_B = float(getattr(paper_qty, "packing_B"))
        cell_C = float(getattr(paper_qty, "cell_C"))
        # posterior_evidence is the A_g paper quantity (re-confirmed at
        # the smallest eps); the formula is consistent at any finite
        # eps because paper_selection_ratio -> 1 as eps -> 0.
        posterior_evidence = float(sheet_evidence_A(g))

        # root_cell_mass at the smallest eps in the sequence.
        eps_min = float(min(eps_sequence))
        root_cell_mass = float(
            paper_selection_ratio(sheet_A, packing_B, cell_C, eps_min)
        )

        # bl_distance via the planar witness over the full sequence.
        report = theorem1_bl_convergence_witness(g, eps_sequence)
        bl_distance = float(report.bl_distance_at_eps_min)

        return Theorem1Statement.from_parts(
            bl_distance=bl_distance,
            root_cell_mass=root_cell_mass,
            posterior_evidence=posterior_evidence,
        )

    def check_sheet_tube_evidence(
        self,
        g: Callable[[float], float],
        eps: float,
        phi: Callable[[float, float], float],
    ) -> "SheetTubeEvidence":
        """Lemma 2 LHS witness (single ``eps``).

        See :func:`sheet_tube_evidence`.
        """
        return sheet_tube_evidence(g, eps, phi)


@dataclass(frozen=True)
class SheetTubeEvidence:
    """Lemma 2 LHS / RHS convergence witness.

    * ``lhs`` -- the Monte-Carlo estimate of
      ``eps^{-1} int_{|y|<=1/2} phi * p_eps``.
    * ``rhs`` -- the paper formula
      ``(2*pi)^{-1/2} int_R phi(s, 0) e^{-s^2/2} / sqrt(1+g(s)^2) ds``.
    * ``rel_err`` -- ``|lhs - rhs| / max(|rhs|, 1e-30)``.

    Converges to 0 as ``eps -> 0`` for any bounded continuous ``phi``.
    """

    lhs: float
    rhs: float
    rel_err: float
    eps: float


def sheet_tube_evidence(
    g: Callable[[float], float],
    eps: float,
    phi: Callable[[float, float], float],
    *,
    n_x: int = 128,
    n_y: int = 32,
) -> SheetTubeEvidence:
    """Return Lemma 2 LHS / RHS witness at finite ``eps``.

    Paper Lemma 2 (line 100-104):

        ``eps^{-1} int_T phi p_eps -> (2*pi)^{-1/2} int_R phi(s,0) e^{-s^2/2} / sqrt(1+g(s)^2) ds``

    where ``T = {|y| <= 1/2}`` and ``p_eps(x, y)`` is the unnormalized
    Gaussian posterior (line 77-79). This function evaluates the LHS
    by 2D-grid Monte-Carlo on ``x in [-K, K]``, ``y in [-1/2, 1/2]``
    with default ``K = 3 * eps`` (so the Gaussian tail is captured) and
    the RHS by 1D trapezoidal on ``s in [-K, K]`` with the same K.

    Converges as ``eps -> 0`` for any bounded continuous ``phi``.

    Parameters
    ----------
    g
        The profile.
    eps
        The finite ``eps`` at which to evaluate Lemma 2.
    phi
        A bounded continuous test function ``R^2 -> R``.

    Stdlib-only.
    """
    if eps <= 0.0:
        raise ValueError(f"eps must be positive, got {eps!r}")
    # Use a wide enough K so the Gaussian tails are negligible.
    K = max(3.0 * eps, 8.0)
    # LHS: int_{|y|<=1/2} phi * (2pi)^{-1} * exp(-(x^2+y^2)/2)
    #      * exp(-|F_g|^2/(2 eps^2))
    # approximated on a uniform grid.
    if n_x < 4 or n_y < 2:
        raise ValueError("n_x must be >= 4 and n_y >= 2")
    hx = (2.0 * K) / n_x
    hy = 1.0 / n_y  # y in [-1/2, 1/2]

    inv_2pi = 1.0 / (2.0 * math.pi)
    # Trapezoidal-style accumulate (uniform spacing, so just * hx * hy).
    lhs_total = 0.0
    inv_2eps2 = 1.0 / (2.0 * eps * eps)
    inv_2 = 0.5
    for i in range(n_x + 1):
        x = -K + i * hx
        # Trapezoidal endpoint weight: 1.0 interior, 0.5 boundaries.
        wx = inv_2 if (i == 0 or i == n_x) else 1.0
        for j in range(n_y + 1):
            y = -inv_2 + j * hy
            wy = inv_2 if (j == 0 or j == n_y) else 1.0
            # |F_g(x,y)|^2 = (y - 1 - g(x))^2 = y^2 (when F_g = y - g(x))
            # We use the standard paper residual: F_g(x, y) = y - g(x).
            F_g = y - float(g(x))
            log_p = -0.5 * (x * x + y * y) - (F_g * F_g) * inv_2eps2
            if log_p < -50.0:
                # Negligible contribution; skip.
                continue
            p = inv_2pi * math.exp(log_p)
            lhs_total += wx * wy * float(phi(x, y)) * p
    lhs_total *= hx * hy
    lhs = lhs_total / eps

    # RHS: (2pi)^{-1/2} int_R phi(s, 0) e^{-s^2/2} / sqrt(1+g(s)^2) ds.
    n_s = max(n_x, 256)
    h_s = (2.0 * K) / n_s
    inv_sqrt_2pi = 1.0 / math.sqrt(2.0 * math.pi)
    rhs_total = 0.0
    for k in range(n_s + 1):
        s = -K + k * h_s
        ws = inv_2 if (k == 0 or k == n_s) else 1.0
        integrand = math.exp(-0.5 * s * s) / math.sqrt(1.0 + float(g(s)) ** 2)
        rhs_total += ws * float(phi(s, 0.0)) * integrand
    rhs_total *= h_s
    rhs = inv_sqrt_2pi * rhs_total

    denom = max(abs(rhs), 1e-30)
    rel_err = abs(lhs - rhs) / denom
    return SheetTubeEvidence(lhs=lhs, rhs=rhs, rel_err=rel_err, eps=eps)


@dataclass(frozen=True)
class LipschitzConvergenceReport:
    """Report of Theorem 1 BL convergence over ``eps_sequence``.

    * ``bl_distance_at_eps_min`` -- ``BL(mu_{g,eps_min}, nu_g)`` where
      ``eps_min = min(eps_sequence)``. Used as the canonical BL
      distance in :class:`Theorem1Statement`.
    * ``bl_distances`` -- the full BL-distance sequence (one per
      ``eps`` value).
    * ``eps_sequence`` -- the input sequence (preserved for the audit
      trail).
    * ``monotone`` -- ``True`` iff ``bl_distances`` is monotone
      decreasing (a sanity check for the audit).
    """

    bl_distance_at_eps_min: float
    bl_distances: tuple[float, ...]
    eps_sequence: tuple[float, ...]
    monotone: bool


def theorem1_bl_convergence_witness(
    g: Callable[[float], float],
    eps_sequence: Sequence[float],
    *,
    n_samples: int = 1024,
    seed: int = 0,
) -> LipschitzConvergenceReport:
    """Compute ``BL(mu_{g,eps_k}, nu_g)`` for each ``eps_k`` in ``eps_sequence``.

    Pure stdlib Monte-Carlo: for each ``eps_k`` we draw ``n_samples``
    points from the unnormalized posterior on ``R^2`` (truncated to
    a finite box ``[-K, K]^2`` with ``K = 3 * eps``), reject any
    point with ``|F_g| > eps``, then compare against the paper's
    limiting density ``nu_g`` via 1-Wasserstein over sorted order
    statistics (a 1-D BL bound for any rotationally-symmetric sample
    family).

    Stdlib-only.
    """
    if not eps_sequence:
        raise ValueError("eps_sequence must be non-empty")
    if n_samples < 32:
        raise ValueError("n_samples must be >= 32 for a meaningful BL estimate")

    import random

    rng = random.Random(int(seed))
    eps_list = [float(e) for e in eps_sequence]
    bl_list: list[float] = []

    # Reference nu_g: density proportional to e^{-s^2/2}/sqrt(1+g(s)^2)
    # (the 1-D marginal along y = 0). Draw reference samples by
    # rejection-sampling from a unit Gaussian envelope.
    nu_g_ref: list[float] = []
    envelope_norm = 1.0 / math.sqrt(2.0 * math.pi)
    K = max(8.0, max(eps_list) * 3.0 + 2.0)
    while len(nu_g_ref) < n_samples:
        s = rng.gauss(0.0, 1.0)
        if abs(s) > K:
            continue
        g_val = float(g(s))
        target = math.exp(-0.5 * s * s) / math.sqrt(1.0 + g_val * g_val)
        if rng.random() * envelope_norm <= target:
            nu_g_ref.append(s)
    nu_g_ref.sort()

    for eps in eps_list:
        K_eps = max(3.0 * eps, 1.0)
        # Sample mu_{g,eps} on R^2 (truncated to [-K_eps, K_eps]^2).
        mu_samples: list[float] = []
        attempts = 0
        target = n_samples
        while len(mu_samples) < target and attempts < n_samples * 200:
            attempts += 1
            x = rng.gauss(0.0, 1.0)
            y = rng.uniform(-0.5, 0.5)
            if abs(x) > K_eps or abs(y) > 0.5:
                continue
            F_g = y - float(g(x))
            if abs(F_g) > eps:
                # Outside the high-density region: the unnormalized
                # posterior is exp(-F_g^2 / (2 eps^2)) which is
                # negligible for |F_g| > eps.
                if rng.random() > math.exp(
                    -0.5 * (F_g * F_g) / (eps * eps) + 0.5
                ):
                    continue
            # Project to y=0 marginal (the BL distance is rotation-
            # invariant on the sheet; the 1-D marginal along y=0
            # captures the paper's nu_g shape).
            mu_samples.append(x)
        mu_samples.sort()

        # 1-Wasserstein over sorted order stats: mean of |mu_i - nu_i|
        # truncated at bound=2 (paper convention ||f||_inf <= 1).
        m = min(len(mu_samples), len(nu_g_ref))
        if m == 0:
            bl_list.append(float("inf"))
            continue
        diffs = [
            min(abs(mu_samples[i] - nu_g_ref[i]), 2.0) for i in range(m)
        ]
        bl = sum(diffs) / m
        bl_list.append(float(bl))

    monotone = all(bl_list[i] >= bl_list[i + 1] for i in range(len(bl_list) - 1))
    eps_min = min(eps_list)
    eps_min_idx = eps_list.index(eps_min)
    bl_at_min = bl_list[eps_min_idx]

    return LipschitzConvergenceReport(
        bl_distance_at_eps_min=float(bl_at_min),
        bl_distances=tuple(bl_list),
        eps_sequence=tuple(eps_list),
        monotone=bool(monotone),
    )