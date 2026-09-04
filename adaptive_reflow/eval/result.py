"""Typed result shape for the unified eval orchestrator (P1-6).

Mirrors :class:`adaptive_reflow.eval.fid.FIDResult` (single-result
shape with optional marker vocabulary for the mol path).

The new ``EvalResult`` / ``MetricResult`` datatypes are the **single
canonical return shape** for ``adaptive_reflow.eval.run_eval.run_eval``.
A frozen dataclass, a closed marker vocabulary, and a ``to_dict()``
round-trip method back the additive ``eval_report.v1.0.0`` JSON
block emitted by every caller that opts in via the
``--emit-eval-report`` flag (or by setting ``output_dir``).

These classes do NOT replace the legacy ``FIDResult`` /
``CLIPScoreResult`` shapes used by their respective evaluators;
they wrap them.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Any, Literal

__all__ = [
    "EvalResult",
    "MetricResult",
    "MetricKind",
    "SCHEMA_VERSION",
    # Marker vocabulary (additive only; matches ``tools.run_mol_eval``
    # lines 264–272 and the synthetic-image fid paths).
    "MARKER_COMPUTED",
    "MARKER_COMPUTED_MMFF",
    "MARKER_COMPUTED_ETKDG_V3_ONLY",
    "MARKER_NOT_INSTALLED",
    "MARKER_STUB_UNAVAILABLE",
    "MARKER_EXTERNAL",
]


# ---------------------------------------------------------------------------
# Marker vocabulary
# ---------------------------------------------------------------------------
#
# Mirrors the marker strings already emitted by
# :func:`tools.run_mol_eval.evaluate` (lines 264-272):
#   - "computed": metric computed without fallback.
#   - "computed_mmff": computed after MMFF optimisation.
#   - "computed_etkdg_v3_only": computed but conformer is ETKDGv3
#     only (no MMFF step).
#   - "not_installed": required dependency missing.
#   - "stub_unavailable": stubbed metric, no real computation.
#   - "external": computation lives in an out-of-process binary.
MARKER_COMPUTED: str = "computed"
MARKER_COMPUTED_MMFF: str = "computed_mmff"
MARKER_COMPUTED_ETKDG_V3_ONLY: str = "computed_etkdg_v3_only"
MARKER_NOT_INSTALLED: str = "not_installed"
MARKER_STUB_UNAVAILABLE: str = "stub_unavailable"
MARKER_EXTERNAL: str = "external"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricResult:
    """Single metric value + marker + diagnostics.

    Attributes
    ----------
    name
        Canonical metric name (e.g. ``"fid"``, ``"qed"``,
        ``"pb_validity"``).
    value
        Float value (``float('nan')`` for undefined).
    is_finite
        Convenience boolean ``math.isfinite(value)``.
    marker
        Closed-set marker from the vocabulary above. ``None`` when
        no marker is applicable (the value is the canonical answer).
    diagnostics
        Optional diagnostics (per-round block, stderr notes, etc.).
    n_samples
        Number of samples that fed the computation.
    feature_dim
        Feature space dimensionality (``2048`` for canonical
        InceptionV3 pool3; ``0`` for scalar metrics like QED).
    """

    name: str
    value: float
    is_finite: bool
    marker: str | None
    diagnostics: Mapping[str, Any]
    n_samples: int
    feature_dim: int

    def __post_init__(self) -> None:
        v = self.value
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(
                f"MetricResult.value must be a real number, got {type(v).__name__}"
            )
        if not isinstance(self.n_samples, int) or self.n_samples < 0:
            raise ValueError(
                f"MetricResult.n_samples must be a non-negative int, got {self.n_samples!r}"
            )
        if not isinstance(self.feature_dim, int) or self.feature_dim < 0:
            raise ValueError(
                f"MetricResult.feature_dim must be a non-negative int, got {self.feature_dim!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-friendly dict."""
        return {
            "name": str(self.name),
            "value": float(self.value),
            "is_finite": bool(self.is_finite),
            "marker": (None if self.marker is None else str(self.marker)),
            "diagnostics": dict(self.diagnostics),
            "n_samples": int(self.n_samples),
            "feature_dim": int(self.feature_dim),
        }


# Discriminator kind -- implicit in the metrics keys; this literal
# is purely documentary.
MetricKind = Literal["mol", "image_2d", "image_3d", "protein"]


@dataclass(frozen=True)
class EvalResult:
    """Top-level eval result.

    Attributes
    ----------
    adapter_id
        Canonical adapter identifier (e.g. ``"rectified_flow_cifar"``).
    dataset_id
        Canonical dataset identifier (e.g. ``"cifar10"``).
    metrics
        ``metric_name -> MetricResult`` mapping.
    missing_dependencies
        Tuple of dependency names that are unavailable for the
        requested metric set. Each entry is a ``"name:reason"``
        string for human consumption.
    stderr_notes
        Free-form notes captured during evaluation.
    wall_clock_s
        Total wall-clock seconds.
    schema_version
        ``"eval_report.v1.0.0"``.
    """

    adapter_id: str
    dataset_id: str
    metrics: Mapping[str, MetricResult]
    missing_dependencies: tuple[str, ...]
    stderr_notes: tuple[str, ...]
    wall_clock_s: float
    schema_version: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-friendly dict."""
        return {
            "adapter_id": str(self.adapter_id),
            "dataset_id": str(self.dataset_id),
            "metrics": {
                k: v.to_dict() for k, v in self.metrics.items()
            },
            "missing_dependencies": list(self.missing_dependencies),
            "stderr_notes": list(self.stderr_notes),
            "wall_clock_s": float(self.wall_clock_s),
            "schema_version": str(self.schema_version),
        }


SCHEMA_VERSION: str = "eval_report.v1.0.0"
