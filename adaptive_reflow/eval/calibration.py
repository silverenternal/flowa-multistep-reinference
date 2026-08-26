"""Frozen calibration protocol: lower-bound constructors + manifest dataclasses.

This module satisfies the CPU-only protocol leg of ``DTB-R7`` ("frozen
calibration + round-to-round paired evaluation protocol"). It exposes:

* :func:`wilson_lower_bound` — pure Wilson score lower bound.
* :func:`beta_lower_bound` — pure Beta-posterior lower quantile.
* :class:`CalibrationBucket` / :class:`CalibrationManifest` — frozen
  per-metric lower-bound buckets and the parent manifest, with
  ``frozen_before_evaluation=True`` enforced.
* :class:`StabilityPerturbationProtocol` — frozen perturbation protocol
  used to derive ``perturbation_stability_lower_bound``.

No ``torch``, no GPU, no real model load. Pure stdlib math + JSON-friendly
frozen dataclasses. Real calibration artifact generation is *deferred*
(see ``protocol_manifests.py`` for the deferred GPU provenance fields).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, NewType

from adaptive_reflow.contracts import (
    ArtifactHash,
    FactorValue,
    ManifestId,
    hash_artifact,
)

# ---------------------------------------------------------------------------
# Local NewType aliases
# ---------------------------------------------------------------------------

CalibrationDatasetId = NewType("CalibrationDatasetId", str)
BucketKey = NewType("BucketKey", str)
IsoTimestamp = NewType("IsoTimestamp", str)
SampleCount = NewType("SampleCount", int)
ConfidenceLevel = NewType("ConfidenceLevel", float)


# ---------------------------------------------------------------------------
# Literal sets
# ---------------------------------------------------------------------------

LOWER_BOUND_METHODS: tuple[str, ...] = ("wilson", "beta")

# ---------------------------------------------------------------------------
# Molecule-specific calibration target + channel literal sets
# ---------------------------------------------------------------------------
# The literal sets ``PREDECLARED_SAFETY_METRICS`` and
# ``CHANNEL_NAMES_FOR_CALIBRATION`` are 100% molecule vocabulary. The
# canonical home is :mod:`adaptive_reflow.molecular.calibration_protocols`
# (``MOLECULE_CALIBRATION_TARGETS`` + ``MOLECULE_CHANNEL_TO_METRIC``).
# We re-export them under the historical names here so existing imports
# (``from adaptive_reflow.eval.calibration import PREDECLARED_SAFETY_METRICS``)
# keep working. The mappings expose ``.keys()`` as the canonical literal
# tuple (sorted for determinism).
from adaptive_reflow.molecular.calibration_protocols import (  # noqa: E402
    MOLECULE_CALIBRATION_TARGETS,
    MOLECULE_CHANNEL_TO_METRIC,
)

PREDECLARED_SAFETY_METRICS: tuple[str, ...] = tuple(sorted(MOLECULE_CALIBRATION_TARGETS.keys()))
CHANNEL_NAMES_FOR_CALIBRATION: tuple[str, ...] = tuple(sorted(MOLECULE_CHANNEL_TO_METRIC.keys()))


# ---------------------------------------------------------------------------
# Pure lower-bound constructors
# ---------------------------------------------------------------------------

# Acklam (1996) rational approximation of the inverse standard-normal CDF.
# Domain split into low/middle/high regions; constants are unchanged from the
# reference. We re-implement rather than depend on scipy / numpy.
_A1 = -3.969683028665376e+01
_A2 = 2.209460984245205e+02
_A3 = -2.759285104469687e+02
_A4 = 1.383577518672690e+02
_A5 = -3.066479806614716e+01
_A6 = 2.506628277459239e+00
_B1 = -5.447609879822406e+01
_B2 = 1.615858368580409e+02
_B3 = -1.556989798598866e+02
_B4 = 6.680131188771972e+01
_B5 = -1.328068155288572e+01
_C1 = -7.784894002430293e-03
_C2 = -3.223964580411365e-01
_C3 = -2.400758277161838e+00
_C4 = -2.549732539343734e+00
_C5 = 4.374664141464968e+00
_C6 = 2.938163982698783e+00
_D1 = 7.784695709041462e-03
_D2 = 3.224671290700398e-01
_D3 = 2.445134137142996e+00
_D4 = 3.754408661907416e+00


def _norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF, p in (0, 1). Acklam's approximation."""
    if not math.isfinite(p) or not (0.0 < p < 1.0):
        raise ValueError(f"p must be in (0, 1), got {p!r}")
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            ((((_C1 * q + _C2) * q + _C3) * q + _C4) * q + _C5) * q + _C6
        ) / ((((_D1 * q + _D2) * q + _D3) * q + _D4) * q + 1.0)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        num = (
            ((((_A1 * r + _A2) * r + _A3) * r + _A4) * r + _A5) * r + _A6
        ) * q
        den = (((((_B1 * r + _B2) * r + _B3) * r + _B4) * r + _B5) * r + 1.0)
        return num / den
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(
        ((((_C1 * q + _C2) * q + _C3) * q + _C4) * q + _C5) * q + _C6
    ) / ((((_D1 * q + _D2) * q + _D3) * q + _D4) * q + 1.0)


def wilson_lower_bound(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> FactorValue:
    """Return the Wilson score interval lower bound.

    Two-sided Wilson interval; ``confidence`` is interpreted as the coverage
    probability (so ``confidence=0.95`` produces the 95 % Wilson LB). Returns
    ``0.0`` for ``trials == 0`` to remain fail-closed against empty buckets.
    """
    if isinstance(successes, bool) or not isinstance(successes, int):
        raise ValueError(f"successes must be int, got {type(successes).__name__}")
    if isinstance(trials, bool) or not isinstance(trials, int):
        raise ValueError(f"trials must be int, got {type(trials).__name__}")
    if successes < 0 or trials < 0 or successes > trials:
        raise ValueError(
            f"require 0 <= successes <= trials, got successes={successes}, trials={trials}"
        )
    if not (0.0 < confidence < 1.0):
        raise ValueError(f"confidence must be in (0, 1), got {confidence!r}")

    if trials == 0:
        return FactorValue(0.0)

    z = _norm_ppf((1.0 + confidence) / 2.0)
    z2 = z * z
    n = float(trials)
    p_hat = float(successes) / n
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denom
    radius = z * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n)) / denom
    lower = center - radius
    if lower < 0.0:
        lower = 0.0
    elif lower > 1.0:
        lower = 1.0
    return FactorValue(float(lower))


# ---------------------------------------------------------------------------
# Beta posterior lower quantile (regularized incomplete beta inverse)
# ---------------------------------------------------------------------------


def _log_beta(a: float, b: float) -> float:
    """Return ``log(Beta(a, b))`` via ``lgamma``."""
    if a <= 0.0 or b <= 0.0:
        raise ValueError(f"beta arguments must be > 0, got a={a!r}, b={b!r}")
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _betacf(a: float, b: float, x: float, max_iter: int = 300, eps: float = 3e-12) -> float:
    """Continued-fraction form of the incomplete beta (Lentz's method)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        # even step
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        # odd step
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta ``I_x(a, b)``."""
    if x < 0.0 or x > 1.0:
        raise ValueError(f"x must be in [0, 1], got {x!r}")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    bt = math.exp(
        -_log_beta(a, b) + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _inv_betai(
    a: float,
    b: float,
    p: float,
    tol: float = 1e-10,
    max_iter: int = 200,
) -> float:
    """Inverse regularized incomplete beta via bisection (robust)."""
    if not (0.0 < p < 1.0):
        raise ValueError(f"p must be in (0, 1), got {p!r}")
    if a <= 0.0 or b <= 0.0:
        raise ValueError(f"a, b must be > 0, got a={a!r}, b={b!r}")

    lo, hi = 0.0, 1.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        val = _betai(a, b, mid) - p
        if abs(val) < tol or (hi - lo) < tol:
            return mid
        if val < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def beta_lower_bound(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> FactorValue:
    """Lower-quantile of the Beta(``successes+1``, ``trials-successes+1``) posterior.

    The quantile is at probability ``(1 - confidence) / 2`` (two-sided
    convention). Empty buckets (``trials == 0``) return ``0.0`` so the
    downstream gate stays fail-closed.
    """
    if isinstance(successes, bool) or not isinstance(successes, int):
        raise ValueError(f"successes must be int, got {type(successes).__name__}")
    if isinstance(trials, bool) or not isinstance(trials, int):
        raise ValueError(f"trials must be int, got {type(trials).__name__}")
    if successes < 0 or trials < 0 or successes > trials:
        raise ValueError(
            f"require 0 <= successes <= trials, got successes={successes}, trials={trials}"
        )
    if not (0.0 < confidence < 1.0):
        raise ValueError(f"confidence must be in (0, 1), got {confidence!r}")

    if trials == 0:
        return FactorValue(0.0)

    a = float(successes) + 1.0
    b = float(trials - successes) + 1.0
    q = (1.0 - confidence) / 2.0
    lower = _inv_betai(a, b, q)
    if lower < 0.0:
        lower = 0.0
    elif lower > 1.0:
        lower = 1.0
    return FactorValue(float(lower))


# ---------------------------------------------------------------------------
# Frozen manifest dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationTimeSplit:
    """Frozen time-split: train, frozen, eval periods + a round ceiling.

    ``frozen_until_round`` is the absolute round index beyond which this
    manifest is no longer authorized for evaluation; any evaluation past
    that round must fail closed.
    """

    train_period: tuple[IsoTimestamp, IsoTimestamp]
    frozen_period: tuple[IsoTimestamp, IsoTimestamp]
    eval_period: tuple[IsoTimestamp, IsoTimestamp]
    frozen_until_round: int


@dataclass(frozen=True)
class CalibrationBucket:
    """One per-(metric, channel) frozen calibration bucket.

    ``lower_bound_value`` is the canonical lower bound on the success rate
    for that bucket, computed at ``lower_bound_confidence``. The
    ``source_stats_hash`` is a deterministic hash of the underlying raw
    statistics so that downstream gates can verify the bucket provenance.
    """

    metric_name: str
    channel: str
    sample_count: int
    lower_bound_value: FactorValue
    lower_bound_confidence: float
    computed_at: IsoTimestamp
    source_stats_hash: ArtifactHash

    def __post_init__(self) -> None:
        # Type / range invariants are enforced here because the dataclass is
        # frozen: __post_init__ runs exactly once and ``object.__setattr__``
        # is the only safe mutation surface. The validators in
        # ``protocol_manifests`` re-check these and add cross-field rules.
        if not str(self.metric_name):
            raise ValueError("CalibrationBucket.metric_name must be non-empty")
        if not str(self.channel):
            raise ValueError("CalibrationBucket.channel must be non-empty")
        if (
            isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or self.sample_count < 0
        ):
            raise ValueError(
                f"sample_count must be a non-negative int, got {self.sample_count!r}"
            )
        lb = float(self.lower_bound_value)
        if not (math.isfinite(lb) and 0.0 <= lb <= 1.0):
            raise ValueError(
                f"lower_bound_value must be a finite real in [0, 1], got {lb!r}"
            )
        if not (0.0 < float(self.lower_bound_confidence) < 1.0):
            raise ValueError(
                f"lower_bound_confidence must be in (0, 1), got {self.lower_bound_confidence!r}"
            )
        if not str(self.computed_at):
            raise ValueError("CalibrationBucket.computed_at must be non-empty")
        if not str(self.source_stats_hash):
            raise ValueError("CalibrationBucket.source_stats_hash must be non-empty")


@dataclass(frozen=True)
class CalibrationManifest:
    """Frozen per-(metric, channel) calibration artifact.

    ``frozen_before_evaluation`` is a literal ``True`` so any post-creation
    mutation attempt is structurally impossible (the dataclass is also
    ``frozen=True``; the literal type is the second fail-closed backstop).
    """

    manifest_id: ManifestId
    calibration_dataset: CalibrationDatasetId
    time_split: CalibrationTimeSplit
    per_metric_buckets: Mapping[str, tuple[CalibrationBucket, ...]]
    min_sample_count: int
    lower_bound_method: Literal["wilson", "beta"]
    artifact_hash: ArtifactHash
    frozen_before_evaluation: Literal[True] = True

    def __post_init__(self) -> None:
        if not str(self.manifest_id):
            raise ValueError("CalibrationManifest.manifest_id must be non-empty")
        if not str(self.calibration_dataset):
            raise ValueError(
                "CalibrationManifest.calibration_dataset must be non-empty"
            )
        if (
            isinstance(self.min_sample_count, bool)
            or not isinstance(self.min_sample_count, int)
            or self.min_sample_count < 0
        ):
            raise ValueError(
                f"min_sample_count must be a non-negative int, got {self.min_sample_count!r}"
            )
        if self.lower_bound_method not in LOWER_BOUND_METHODS:
            raise ValueError(
                f"lower_bound_method must be one of {LOWER_BOUND_METHODS!r}, "
                f"got {self.lower_bound_method!r}"
            )
        if not str(self.artifact_hash):
            raise ValueError("CalibrationManifest.artifact_hash must be non-empty")


@dataclass(frozen=True)
class StabilityPerturbationProtocol:
    """Frozen perturbation protocol used to derive stability lower bounds.

    The protocol is consumed by the stability test: it enumerates the
    deterministic ``seed_perturbations`` (int seeds) and the
    ``condition_perturbations`` (string labels) that must be applied
    per-target, and the minimum number of perturbed samples per target
    before the bucket is admitted into calibration.
    """

    seed_perturbations: tuple[int, ...]
    condition_perturbations: tuple[str, ...]
    per_target_min_samples: int = field(default=8)

    def __post_init__(self) -> None:
        if not self.seed_perturbations:
            raise ValueError("seed_perturbations must be non-empty")
        for s in self.seed_perturbations:
            if isinstance(s, bool) or not isinstance(s, int):
                raise ValueError(
                    f"seed_perturbations entries must be int, got {type(s).__name__}"
                )
        if not self.condition_perturbations:
            raise ValueError("condition_perturbations must be non-empty")
        for s_str in self.condition_perturbations:
            if not isinstance(s_str, str) or not s_str:
                raise ValueError(
                    "condition_perturbations entries must be non-empty str"
                )
        if (
            isinstance(self.per_target_min_samples, bool)
            or not isinstance(self.per_target_min_samples, int)
            or self.per_target_min_samples < 1
        ):
            raise ValueError(
                "per_target_min_samples must be a positive int, got "
                f"{self.per_target_min_samples!r}"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def classify_bucket(
    bucket: CalibrationBucket,
    *,
    min_sample_count: int,
) -> Literal["admit", "reject_low_sample", "reject_missing_provenance"]:
    """Classify ``bucket`` against the manifest's admission policy.

    Returned codes are mutually exclusive in the listed priority order. The
    third code, ``reject_missing_provenance``, is currently unreachable
    because the bucket constructor rejects empty ``source_stats_hash``; it
    is provided so future schema additions don't silently admit buckets
    with empty provenance.
    """
    if not str(bucket.source_stats_hash):
        return "reject_missing_provenance"
    if bucket.sample_count < int(min_sample_count):
        return "reject_low_sample"
    return "admit"


def manifest_digest(
    manifest: CalibrationManifest,
) -> ArtifactHash:
    """Deterministic sha256 digest over the canonical manifest payload.

    The digest is independent of the stored ``artifact_hash``; it lets
    downstream gates re-verify the manifest payload even if the manifest's
    own ``artifact_hash`` is missing or stale.
    """
    payload = {
        "manifest_id": str(manifest.manifest_id),
        "calibration_dataset": str(manifest.calibration_dataset),
        "time_split": {
            "train_period": [
                str(manifest.time_split.train_period[0]),
                str(manifest.time_split.train_period[1]),
            ],
            "frozen_period": [
                str(manifest.time_split.frozen_period[0]),
                str(manifest.time_split.frozen_period[1]),
            ],
            "eval_period": [
                str(manifest.time_split.eval_period[0]),
                str(manifest.time_split.eval_period[1]),
            ],
            "frozen_until_round": int(manifest.time_split.frozen_until_round),
        },
        "per_metric_buckets": {
            metric: [
                {
                    "metric_name": str(b.metric_name),
                    "channel": str(b.channel),
                    "sample_count": int(b.sample_count),
                    "lower_bound_value": float(b.lower_bound_value),
                    "lower_bound_confidence": float(b.lower_bound_confidence),
                    "computed_at": str(b.computed_at),
                    "source_stats_hash": str(b.source_stats_hash),
                }
                for b in buckets
            ]
            for metric, buckets in sorted(manifest.per_metric_buckets.items())
        },
        "min_sample_count": int(manifest.min_sample_count),
        "lower_bound_method": str(manifest.lower_bound_method),
    }
    return hash_artifact(payload)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "CHANNEL_NAMES_FOR_CALIBRATION",
    # Literal sets
    "LOWER_BOUND_METHODS",
    "PREDECLARED_SAFETY_METRICS",
    "BucketKey",
    "CalibrationBucket",
    # NewType aliases
    "CalibrationDatasetId",
    "CalibrationManifest",
    # Frozen dataclasses
    "CalibrationTimeSplit",
    "ConfidenceLevel",
    "IsoTimestamp",
    "SampleCount",
    "StabilityPerturbationProtocol",
    "beta_lower_bound",
    # Helpers
    "classify_bucket",
    "manifest_digest",
    # Lower bound constructors
    "wilson_lower_bound",
]
