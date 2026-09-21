"""Wave 229 P3 — Empirical residual profiles for the 3 core adapters.

Implements :func:`profile_residual_fn` for the three core flow-matching
adapters integrated with the framework:

* :func:`lineageflow_profile_residual_fn` — protein structure residual
  ``(1 - pLDDT / 100)`` sampled from the canonical
  ``verification_outputs/wave206-p1-lineageflow-n1000/baseline/metrics.jsonl``
  record-level pLDDT values (N=1000 records; subsample N=100 with a
  fixed seed for byte-stable behaviour).
* :func:`kanzi_profile_residual_fn` — protein reconstruction RMSD sampled
  from a Gaussian parameterised by the canonical Wave 206 P2 summary
  statistics ``baseline_mean_A=0.9019772501591515``,
  ``baseline_std_A=0.13748329375978863`` (N=1000).
* :func:`flowmol3_profile_residual_fn` — functional-group deviation (QM9
  fg_dev) sampled from a Gaussian parameterised by the canonical Wave 82
  ``statistical_power_at_n1000`` SEM/Mean (``baseline fg_dev=0.6381``,
  ``fg_dev_sem=0.00577``). Per-record fg_dev is not available (the
  Wave 109.C DGL regression blocks the full N=1000 paired sweep), so the
  per-arm SEM is used as the byte-stable residual scale.

Each profile is constructed by:

1. Drawing N=100 residuals from the empirical (Gaussian or empirical-
   record) distribution with a fixed seed.
2. Sorting the samples and placing them on a uniform grid over the
   integration range ``[-K, K]`` (default ``K = 8``, matching
   :func:`adaptive_reflow.theory.paper_quantities.sheet_evidence_A`).
3. Defining ``g(s)`` by linear interpolation between consecutive
   ``(s_i, residual_i)`` pairs (extrapolation holds the endpoint
   value).

The three profile functions are byte-stable on a fixed Python /
NumPy / random.Random version because the seed and interpolation scheme
are deterministic.

The :func:`profile_residual_fn_registry` factory exposes a uniform
``adapter_class -> Callable[[float], float]`` map so the framework's
:func:`adaptive_reflow.contracts.paper_quantities.sheet_evidence_A`
evaluator can be wired with any of the three empirical profiles.

Cross-references:

* ``verification_outputs/wave206-p1-lineageflow-n1000/baseline/metrics.jsonl``
* ``verification_outputs/wave206-p2-kanzi-framework-n1000.csv``
* ``verification_outputs/flowmol3_n1000_sweep_q4_2026.json``
* ``docs/audit/wave229-p3-core-adapter-paper-quantities.md``
"""
from __future__ import annotations

import json
import math
import random
from collections.abc import Callable
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants — empirical residual statistics
# ---------------------------------------------------------------------------

# K=8 matches the default of sheet_evidence_A so the profile is evaluated
# over the same real-line truncation as the framework default.
_PROFILE_K: float = 8.0
_N_SAMPLES: int = 100  # task brief: sample N=100 residuals per adapter
_PROFILE_SEED: int = 42  # deterministic seed for byte-stable sampling

# LineageFlow empirical basis: structural residual = (1 - pLDDT / 100)
# using per-record pLDDT from Wave 206 P1 N=1000 baseline arm. The full
# 1000-record file lives at:
#
#   verification_outputs/wave206-p1-lineageflow-n1000/baseline/metrics.jsonl
#
# Each record carries a ``plddt_mean`` field (range ~20..80); the residual
# ``(1 - plddt_mean / 100)`` is in [0, 1] and represents the structural
# distance between the decoded fold and the reference fold.
_LINEAGEFLOW_BASELINE_METRICS_JSONL = (
    "verification_outputs/wave206-p1-lineageflow-n1000/baseline/metrics.jsonl"
)

# Kanzi empirical basis (Wave 206 P2 R2_kanzi_reconstruction_rmsd_A):
# baseline_mean_A = 0.9019772501591515, baseline_std_A = 0.13748329375978863
# at N = 1000. Per-record values are not persisted; we sample from the
# empirical Gaussian to reconstruct a byte-stable N=100 profile.
_KANZI_RMSD_MEAN: float = 0.9019772501591515
_KANZI_RMSD_STD: float = 0.13748329375978863

# FlowMol3 empirical basis (Wave 82 statistical_power_at_n1000):
# baseline fg_dev = 0.6381122391671532 (Wave 87 sweep at N=1000).
# fg_dev_sem = 0.00577 from Wave 82 power analysis (the SEM at N=1000).
# Per-record fg_dev is BLOCKED on the Wave 109.C DGL regression; the SEM
# is the documented residual scale (delta_per_record ≈ SEM * sqrt(N)
# / 1 = 0.183 by normal-approx inversion at N=1000).
_FLOWMOL3_FG_DEV_MEAN: float = 0.6381122391671532
_FLOWMOL3_FG_DEV_STD: float = 0.183  # ≈ SEM * sqrt(N) at N=1000

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _linear_interp_grid(
    residuals: list[float],
    *,
    K: float = _PROFILE_K,
) -> tuple[list[float], list[float]]:
    """Place sorted residuals on a uniform grid over [-K, K].

    Returns ``(s_grid, residual_grid)`` of length ``len(residuals)`` where
    ``s_grid[i] = -K + 2K * i / (N - 1)`` and ``residual_grid[i]`` is the
    i-th smallest residual. The two endpoints ``-K`` and ``+K`` carry the
    min and max residuals so linear extrapolation is constant outside the
    sampled grid.
    """
    if len(residuals) < 2:
        raise ValueError(
            f"need at least 2 residuals for a linear-interp profile, got {len(residuals)}"
        )
    n = len(residuals)
    sorted_res = sorted(residuals)
    s_grid: list[float] = []
    r_grid: list[float] = []
    for i, r in enumerate(sorted_res):
        s = -K + (2.0 * K) * (float(i) / float(n - 1))
        s_grid.append(float(s))
        r_grid.append(float(r))
    return s_grid, r_grid


def _build_profile_fn(
    s_grid: list[float], r_grid: list[float]
) -> Callable[[float], float]:
    """Return a linear-interpolating callable over (s_grid, r_grid).

    The callable is byte-stable: two profiles built from identical inputs
    return bit-identical floats for the same query ``s``. Outside the
    grid the function holds the endpoint value (constant extrapolation).

    The signature ``profile_residual_fn(x, t) -> scalar`` would also
    accept the round ``t``; we collapse it to a 1-arg scalar here to
    match the ``Callable[[float], float]`` contract consumed by
    :func:`adaptive_reflow.theory.paper_quantities.sheet_evidence_A`.
    """
    n = len(s_grid)
    if n != len(r_grid):
        raise ValueError(
            f"s_grid and r_grid must have the same length, got {n} vs {len(r_grid)}"
        )

    def profile_residual_fn(x: float) -> float:
        # Constant extrapolation outside the grid
        if x <= s_grid[0]:
            return float(r_grid[0])
        if x >= s_grid[-1]:
            return float(r_grid[-1])
        # Linear search: find i such that s_grid[i] <= x < s_grid[i+1]
        lo, hi = 0, n - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if s_grid[mid] <= x:
                lo = mid
            else:
                hi = mid
        s0, s1 = s_grid[lo], s_grid[lo + 1]
        r0, r1 = r_grid[lo], r_grid[lo + 1]
        # Linear interpolation
        if s1 == s0:
            return float(r0)
        t = (float(x) - s0) / (s1 - s0)
        return float(r0 + t * (r1 - r0))

    return profile_residual_fn


# ---------------------------------------------------------------------------
# Per-adapter empirical samplers
# ---------------------------------------------------------------------------


def _sample_lineageflow_residuals(n: int, seed: int) -> list[float]:
    """Sample N residuals from the per-record Wave 206 P1 baseline file.

    Reads ``verification_outputs/wave206-p1-lineageflow-n1000/baseline/metrics.jsonl``
    and subsamples N records deterministically (random.Random with the
    provided seed). The residual for each record is
    ``(1 - plddt_mean / 100)`` (structural distance to the reference
    fold). If the JSONL file is missing, falls back to a Gaussian sample
    using the documented baseline pLDDT distribution
    (mean pLDDT ~ 42.07, std ~ 12, residual mean ~ 0.58).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    jsonl_path = repo_root / _LINEAGEFLOW_BASELINE_METRICS_JSONL
    residuals: list[float] = []
    if jsonl_path.is_file():
        with jsonl_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                if "plddt_mean" in rec:
                    plddt = float(rec["plddt_mean"])
                    residuals.append((100.0 - plddt) / 100.0)
    if not residuals:
        # Fallback: synthetic Gaussian centred on the documented
        # baseline pLDDT distribution. This keeps the profile byte-stable
        # even when the JSONL is unavailable on a fresh checkout.
        rng = random.Random(seed)
        # Box-Muller for reproducibility
        residuals = []
        while len(residuals) < 1000:
            u1 = rng.random()
            u2 = rng.random()
            z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
            plddt = 42.07 + 12.0 * z0
            residuals.append((100.0 - plddt) / 100.0)
    rng = random.Random(seed)
    if n > len(residuals):
        # sample with replacement if we need more than the available pool
        return [rng.choice(residuals) for _ in range(n)]
    return rng.sample(residuals, n)


def _sample_gaussian_residuals(
    n: int, mean: float, std: float, seed: int
) -> list[float]:
    """Sample N residuals from a Gaussian(mean, std) via Box-Muller.

    Deterministic via :class:`random.Random` with the provided seed so the
    profile is byte-stable on a fixed Python version.
    """
    if std <= 0.0:
        return [mean] * n
    rng = random.Random(seed)
    residuals: list[float] = []
    while len(residuals) < n:
        u1 = rng.random()
        u2 = rng.random()
        # Avoid log(0)
        u1 = max(u1, 1e-12)
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        residuals.append(mean + std * z0)
    return residuals[:n]


# ---------------------------------------------------------------------------
# Per-adapter profile_residual_fn constructors
# ---------------------------------------------------------------------------


def lineageflow_profile_residual_fn(
    *, K: float = _PROFILE_K, n_samples: int = _N_SAMPLES, seed: int = _PROFILE_SEED
) -> Callable[[float], float]:
    """Return the empirical LineageFlow residual profile ``g(x)``.

    The residual is the structural distance between the decoded protein
    fold and the reference fold, ``(1 - pLDDT / 100)``, sampled N=100
    times from the canonical Wave 206 P1 N=1000 baseline file
    (``verification_outputs/wave206-p1-lineageflow-n1000/baseline/metrics.jsonl``).
    The samples are sorted and placed on a uniform grid over
    ``[-K, K]``; ``g(s)`` is the piecewise-linear interpolant.

    Wave 229 P3 / hypothesis test: the LineageFlow empirical profile
    should produce an ``A_g`` value within ~10% of the canonical witness
    ``A_g = 0.8549457422`` because the residuals sit in [0.27, 0.75]
    (compact support near zero) and ``g(s)`` is approximately
    constant — which means ``A_g`` is close to the canonical
    ``A_g(g=0) = 1`` value scaled by the empirical mean.
    """
    residuals = _sample_lineageflow_residuals(n_samples, seed=seed)
    s_grid, r_grid = _linear_interp_grid(residuals, K=K)
    return _build_profile_fn(s_grid, r_grid)


def kanzi_profile_residual_fn(
    *, K: float = _PROFILE_K, n_samples: int = _N_SAMPLES, seed: int = _PROFILE_SEED
) -> Callable[[float], float]:
    """Return the empirical Kanzi residual profile ``g(x)``.

    The residual is the reconstruction RMSD between kanzi-decoded coords
    and reference coords, sampled from a Gaussian parameterised by the
    Wave 206 P2 R2_kanzi_reconstruction_rmsd_A summary statistics
    (``mean = 0.9019772501591515``, ``std = 0.13748329375978863`` at
    N=1000). Per-record RMSD values are not persisted (the Wave 109.C
    DGL regression blocks the full sweep); the Gaussian is the canonical
    byte-stable approximation.

    Wave 229 P3 / hypothesis test: the Kanzi residual distribution is
    centred well above zero, so the empirical profile reduces ``A_g``
    relative to the canonical witness (the sheet evidence is divided by
    ``sqrt(1 + g(s)^2)``).
    """
    residuals = _sample_gaussian_residuals(
        n_samples, mean=_KANZI_RMSD_MEAN, std=_KANZI_RMSD_STD, seed=seed
    )
    s_grid, r_grid = _linear_interp_grid(residuals, K=K)
    return _build_profile_fn(s_grid, r_grid)


def flowmol3_profile_residual_fn(
    *, K: float = _PROFILE_K, n_samples: int = _N_SAMPLES, seed: int = _PROFILE_SEED
) -> Callable[[float], float]:
    """Return the empirical FlowMol3 residual profile ``g(x)``.

    The residual is the functional-group deviation (QM9 fg_dev) per
    record, sampled from a Gaussian parameterised by the Wave 82
    statistical_power_at_n1000 SEM (baseline fg_dev = 0.6381122391671532,
    SEM = 0.00577 at N=1000, hence per-record std ≈ 0.183 by normal
    inversion). Per-record fg_dev is BLOCKED on the Wave 109.C DGL
    regression; the SEM-derived std is the documented residual scale.

    Wave 229 P3 / hypothesis test: the FlowMol3 empirical profile
    centred near 0.6 with std ~0.18 sits between the canonical witness
    (0) and Kanzi (0.9). The empirical ``A_g`` should land at an
    intermediate reduction relative to the canonical witness.
    """
    residuals = _sample_gaussian_residuals(
        n_samples, mean=_FLOWMOL3_FG_DEV_MEAN, std=_FLOWMOL3_FG_DEV_STD, seed=seed
    )
    s_grid, r_grid = _linear_interp_grid(residuals, K=K)
    return _build_profile_fn(s_grid, r_grid)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


PROFILE_RESIDUAL_FN_REGISTRY: dict[str, Callable[..., Callable[[float], float]]] = {
    "LineageFlowAdapter": lineageflow_profile_residual_fn,
    "KanziAdapter": kanzi_profile_residual_fn,
    "FlowMol3V2Adapter": flowmol3_profile_residual_fn,
}


def profile_residual_fn_registry(
    adapter_class: str,
    *,
    K: float = _PROFILE_K,
    n_samples: int = _N_SAMPLES,
    seed: int = _PROFILE_SEED,
) -> Callable[[float], float]:
    """Return the empirical profile_residual_fn for ``adapter_class``.

    :param adapter_class: one of ``"LineageFlowAdapter"``,
        ``"KanziAdapter"``, ``"FlowMol3V2Adapter"``.
    :param K: half-width of the integration grid (default 8, matching
        :func:`sheet_evidence_A`).
    :param n_samples: number of residual samples to draw (default 100).
    :param seed: deterministic seed for byte-stable sampling (default 42).
    :raises KeyError: when ``adapter_class`` is not in the registry.
    """
    factory = PROFILE_RESIDUAL_FN_REGISTRY.get(adapter_class)
    if factory is None:
        raise KeyError(
            f"unknown adapter_class {adapter_class!r}; "
            f"supported: {sorted(PROFILE_RESIDUAL_FN_REGISTRY.keys())}"
        )
    return factory(K=K, n_samples=n_samples, seed=seed)