"""Round-to-round paired evaluation protocol (CPU-only contract).

This module satisfies the CPU-only evaluation leg of ``DTB-R7``:

* :class:`PairedComparisonArm` — one paired arm (kind + hashes).
* :class:`PairedComparisonRegistry` — pre-registered arms; rejects late
  additions; carries a deterministic combined hash.
* :class:`EvaluatorProvenanceGuard` — frozen evaluator / materialization
  provenance guard; rejects missing required versions.
* :class:`RoundToRoundOscillationDetector` — deterministic oscillation
  counter that detects (a) round-to-round score inversion and (b) collapse
  of fresh-noise mass. Pure CPU, no torch.

GPU evaluation runs are *deferred* (see ``protocol_manifests.py``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NewType

from adaptive_reflow.contracts import (
    ArtifactHash,
    FactorValue,
    hash_artifact,
)

# ---------------------------------------------------------------------------
# Local NewType aliases
# ---------------------------------------------------------------------------

ArmName = NewType("ArmName", str)
PolicyHash = NewType("PolicyHash", str)
ConfigHash = NewType("ConfigHash", str)
EvaluatorVersion = NewType("EvaluatorVersion", str)
MaterializationRoute = NewType("MaterializationRoute", str)
TargetPocketHash = NewType("TargetPocketHash", str)


# ---------------------------------------------------------------------------
# Literal sets
# ---------------------------------------------------------------------------

PAIRED_ARM_KINDS: tuple[str, ...] = (
    "disabled",
    "fixed_scheduled",
    "dynamic_uncalibrated",
    "dynamic_calibrated",
    "linear_fresh_noise",
    "cosine_no_restart",
    "cosine_guarded_restart",
)


# ---------------------------------------------------------------------------
# Paired arms
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairedComparisonArm:
    """One arm of a round-to-round paired comparison run.

    ``kind`` is constrained to the closed literal set in
    :data:`PAIRED_ARM_KINDS`. The arm is registered with two hashes:

    * ``policy_hash`` — the dynamic / fixed policy content hash.
    * ``config_hash`` — the schedule / boundary config hash.

    Both are non-empty strings; empty hashes are rejected by the
    registry at registration time.
    """

    name: ArmName
    kind: Literal[
        "disabled",
        "fixed_scheduled",
        "dynamic_uncalibrated",
        "dynamic_calibrated",
        "linear_fresh_noise",
        "cosine_no_restart",
        "cosine_guarded_restart",
    ]
    policy_hash: PolicyHash
    config_hash: ConfigHash

    def __post_init__(self) -> None:
        if not str(self.name):
            raise ValueError("PairedComparisonArm.name must be non-empty")
        if self.kind not in PAIRED_ARM_KINDS:
            raise ValueError(
                f"PairedComparisonArm.kind must be one of {PAIRED_ARM_KINDS!r}, "
                f"got {self.kind!r}"
            )
        if not str(self.policy_hash):
            raise ValueError("PairedComparisonArm.policy_hash must be non-empty")
        if not str(self.config_hash):
            raise ValueError("PairedComparisonArm.config_hash must be non-empty")


@dataclass(frozen=True)
class _RegistryClosedMarker:
    """Sentinel that flips once the registry is sealed."""

    sealed: bool = False


class PairedComparisonRegistry:
    """Pre-registered paired comparison arms.

    The registry is constructed empty; arms are added via :meth:`register`
    until :meth:`seal` is called. After sealing, any further :meth:`register`
    attempt raises :class:`RuntimeError`. The combined arms hash is a
    deterministic digest over the sorted ``(name, kind, policy_hash,
    config_hash)`` tuples so downstream gates can detect drift.
    """

    def __init__(self) -> None:
        self._arms: dict[str, PairedComparisonArm] = {}
        self._sealed_marker = _RegistryClosedMarker(sealed=False)
        # The set of kinds that have been registered; duplicates are not
        # allowed (one arm per kind per registry). This enforces that the
        # canonical paired arms set is unique.
        self._kinds_seen: set[str] = set()

    @property
    def is_sealed(self) -> bool:
        """Return ``True`` iff :meth:`seal` has been called."""
        return bool(self._sealed_marker.sealed)

    @property
    def arms(self) -> tuple[PairedComparisonArm, ...]:
        """Return the registered arms in deterministic (insertion) order."""
        return tuple(self._arms.values())

    def register(self, arm: PairedComparisonArm) -> None:
        """Add ``arm`` to the registry.

        Rejects duplicate names, duplicate kinds, and any addition after the
        registry has been sealed.
        """
        if not isinstance(arm, PairedComparisonArm):
            raise TypeError(
                f"register() expects PairedComparisonArm, got {type(arm).__name__}"
            )
        if self._sealed_marker.sealed:
            raise RuntimeError(
                "PairedComparisonRegistry is sealed; arm addition is rejected "
                "(per DTB-R7, arms are pre-registered before evaluation runs)"
            )
        if str(arm.name) in self._arms:
            raise ValueError(
                f"duplicate arm name {arm.name!r}; registry rejects duplicate names"
            )
        if str(arm.kind) in self._kinds_seen:
            raise ValueError(
                f"duplicate arm kind {arm.kind!r}; registry enforces at most one "
                "arm per kind"
            )
        self._arms[str(arm.name)] = arm
        self._kinds_seen.add(str(arm.kind))

    def seal(self) -> ArtifactHash:
        """Seal the registry and return the combined arms hash.

        Subsequent ``register`` calls are rejected. The combined hash is
        deterministic over the sorted arm tuples.
        """
        if self._sealed_marker.sealed:
            raise RuntimeError("PairedComparisonRegistry is already sealed")
        # Replace the marker via object.__setattr__ because the dataclass
        # itself is frozen — but the registry is a regular class so a plain
        # attribute mutation suffices.
        self._sealed_marker = _RegistryClosedMarker(sealed=True)
        return self.combined_hash

    @property
    def combined_hash(self) -> ArtifactHash:
        """Deterministic sha256 over the sorted arm tuple.

        Independent of insertion order so re-registering arms in a
        different order produces the same digest.
        """
        payload = [
            {
                "name": str(arm.name),
                "kind": str(arm.kind),
                "policy_hash": str(arm.policy_hash),
                "config_hash": str(arm.config_hash),
            }
            for arm in sorted(self._arms.values(), key=lambda a: str(a.name))
        ]
        return hash_artifact({"arms": payload})

    def get_kind(self, kind: str) -> PairedComparisonArm | None:
        """Return the registered arm with the given kind, or ``None``."""
        for arm in self._arms.values():
            if str(arm.kind) == str(kind):
                return arm
        return None

    def has_all_kinds(self) -> bool:
        """Return ``True`` iff every canonical kind in ``PAIRED_ARM_KINDS``
        is registered (the canonical paired-arm set is the 7-element union)."""
        return set(PAIRED_ARM_KINDS).issubset(self._kinds_seen)


# ---------------------------------------------------------------------------
# Evaluator provenance guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluatorProvenanceGuard:
    """Frozen evaluator / materialization-route provenance guard.

    ``required_evaluator_versions`` is the closed tuple of versions that
    the downstream evaluation harness is permitted to consume; any other
    version is rejected. ``required_materialization_route`` is the
    canonical materialization route identifier (e.g. a content-addressable
    adapter route). The ``evaluator_hash`` is a deterministic digest
    binding the tuple of versions + the materialization route to a single
    content hash.
    """

    required_evaluator_versions: tuple[EvaluatorVersion, ...]
    required_materialization_route: MaterializationRoute
    evaluator_hash: ArtifactHash

    def __post_init__(self) -> None:
        if not self.required_evaluator_versions:
            raise ValueError(
                "required_evaluator_versions must be non-empty"
            )
        for v in self.required_evaluator_versions:
            if not isinstance(v, str) or not v:
                raise ValueError(
                    "required_evaluator_versions entries must be non-empty str"
                )
        if not str(self.required_materialization_route):
            raise ValueError(
                "required_materialization_route must be non-empty"
            )
        if not str(self.evaluator_hash):
            raise ValueError("evaluator_hash must be non-empty")

    def check_version(self, version: str) -> bool:
        """Return ``True`` iff ``version`` is in the required version tuple."""
        return str(version) in tuple(self.required_evaluator_versions)

    def check_route(self, route: str) -> bool:
        """Return ``True`` iff ``route`` matches the required materialization route."""
        return str(route) == str(self.required_materialization_route)


def evaluator_guard_digest(
    versions: tuple[str, ...],
    materialization_route: str,
) -> ArtifactHash:
    """Return the deterministic sha256 digest that binds versions + route."""
    if not versions:
        raise ValueError("versions must be non-empty")
    if not str(materialization_route):
        raise ValueError("materialization_route must be non-empty")
    payload = {
        "versions": sorted(str(v) for v in versions),
        "materialization_route": str(materialization_route),
    }
    return hash_artifact(payload)


# ---------------------------------------------------------------------------
# Round-to-round oscillation detector (deterministic, CPU)
# ---------------------------------------------------------------------------


@dataclass
class RoundToRoundOscillationDetector:
    """CPU-only oscillation / collapse detector over a round score trace.

    Tracks two failure modes:

    * **Oscillation count** — number of times the direction of
      ``score_t - score_{t-1}`` flips between consecutive rounds.
    * **Consecutive-identical runs** — length of the trailing run of
      identical scores; exceeds ``consecutive_identical_score_runs`` is
      flagged.
    * **Fresh-noise collapse** — number of consecutive rounds for which
      ``fresh_noise_t < fresh_noise_collapse_threshold`` is True.

    The detector is deterministic: identical inputs always yield identical
    state. ``reset()`` returns the detector to its empty state.
    """

    oscillation_count: int = 0
    consecutive_identical_score_runs: int = 0
    fresh_noise_collapse_threshold: float = 0.05
    consecutive_identical_score_threshold: int = 3

    def __post_init__(self) -> None:
        self._last_score: float | None = None
        self._last_sign: int = 0  # -1, 0, +1
        self._identical_run: int = 0
        self._fresh_noise_collapse_streak: int = 0
        self._max_fresh_noise_collapse_streak: int = 0

    def reset(self) -> None:
        """Reset the detector to its empty state (counters preserved)."""
        self._last_score = None
        self._last_sign = 0
        self._identical_run = 0
        self._fresh_noise_collapse_streak = 0
        self._max_fresh_noise_collapse_streak = 0
        # Reset the public fields too so callers see a clean slate.
        self.oscillation_count = 0
        self.consecutive_identical_score_runs = 0

    def update(
        self,
        score: float,
        fresh_noise_mass: FactorValue | float,
    ) -> None:
        """Fold one (round, score, fresh_noise) triple into the detector.

        Updates ``oscillation_count``, ``consecutive_identical_score_runs``,
        and the fresh-noise collapse streak in deterministic order.
        """
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError(f"score must be a real number, got {type(score).__name__}")
        if not math.isfinite(float(score)):
            raise ValueError(f"score must be finite, got {score!r}")

        if (
            not isinstance(fresh_noise_mass, (int, float))
            or isinstance(fresh_noise_mass, bool)
        ):
            raise ValueError(
                f"fresh_noise_mass must be a real number, got {type(fresh_noise_mass).__name__}"
            )
        if not (0.0 <= float(fresh_noise_mass) <= 1.0):
            raise ValueError(
                f"fresh_noise_mass must be in [0, 1], got {fresh_noise_mass!r}"
            )

        score_f = float(score)

        # First observation: initialize trailing run to 1 and skip
        # oscillation / delta comparisons (no prior delta is defined).
        if self._last_score is None:
            self._last_score = score_f
            self._identical_run = 1
            self.consecutive_identical_score_runs = self._identical_run
            # Fresh-noise collapse streak still applies to round 0.
            if score_f < 0.0:  # unreachable; kept for type-narrowing clarity
                pass
            self._update_fresh_noise_streak(float(fresh_noise_mass))
            return

        # Oscillation: sign flip of the consecutive-round score delta.
        delta = score_f - float(self._last_score)
        if delta > 0.0:
            sign = 1
        elif delta < 0.0:
            sign = -1
        else:
            sign = 0
        if sign != 0 and self._last_sign != 0 and sign != self._last_sign:
            self.oscillation_count += 1
        if sign != 0:
            self._last_sign = sign

        # Identical-score run length (trailing run; counts the current score).
        if score_f == float(self._last_score):
            self._identical_run += 1
        else:
            self._identical_run = 1
        self.consecutive_identical_score_runs = self._identical_run

        self._last_score = score_f
        self._update_fresh_noise_streak(float(fresh_noise_mass))

    def _update_fresh_noise_streak(self, fresh_noise_mass: float) -> None:
        """Maintain the fresh-noise collapse streak + the longest streak
        observed in the trace so far.
        """
        if float(fresh_noise_mass) < float(self.fresh_noise_collapse_threshold):
            self._fresh_noise_collapse_streak += 1
        else:
            self._fresh_noise_collapse_streak = 0
        self._max_fresh_noise_collapse_streak = max(self._max_fresh_noise_collapse_streak, self._fresh_noise_collapse_streak)

    @property
    def max_fresh_noise_collapse_streak(self) -> int:
        """Longest observed fresh-noise collapse streak in the trace so far."""
        return self._max_fresh_noise_collapse_streak

    def is_oscillating(self) -> bool:
        """Return ``True`` iff at least one sign flip has been observed."""
        return self.oscillation_count > 0

    def is_stuck(self) -> bool:
        """Return ``True`` iff the identical-score run exceeds the threshold."""
        return (
            self.consecutive_identical_score_runs
            >= int(self.consecutive_identical_score_threshold)
        )

    def has_fresh_noise_collapse(self) -> bool:
        """Return ``True`` iff the longest collapse streak >= threshold."""
        return (
            self._max_fresh_noise_collapse_streak
            >= int(self.consecutive_identical_score_threshold)
        )

    def snapshot(self) -> Mapping[str, int | float]:
        """Return a deterministic, JSON-friendly snapshot of the detector."""
        return {
            "oscillation_count": int(self.oscillation_count),
            "consecutive_identical_score_runs": int(
                self.consecutive_identical_score_runs
            ),
            "fresh_noise_collapse_threshold": float(
                self.fresh_noise_collapse_threshold
            ),
            "consecutive_identical_score_threshold": int(
                self.consecutive_identical_score_threshold
            ),
            "max_fresh_noise_collapse_streak": int(
                self._max_fresh_noise_collapse_streak
            ),
        }


# math was imported at module top; ``math.isfinite`` is consumed by
# ``RoundToRoundOscillationDetector.update``.


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    # Literal sets
    "PAIRED_ARM_KINDS",
    # NewType aliases
    "ArmName",
    "ConfigHash",
    # Evaluator guard
    "EvaluatorProvenanceGuard",
    "EvaluatorVersion",
    "MaterializationRoute",
    # Paired arms
    "PairedComparisonArm",
    "PairedComparisonRegistry",
    "PolicyHash",
    # Oscillation detector
    "RoundToRoundOscillationDetector",
    "TargetPocketHash",
    "evaluator_guard_digest",
]
