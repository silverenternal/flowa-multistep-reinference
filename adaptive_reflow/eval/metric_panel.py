"""Layered metric panel with enforced tier separation (DTB-R8).

This module implements the structural half of the DTB-R8 metric
reporting contract. It exposes:

* :data:`LayeredEvidenceTiers` — ``Literal`` tuple of the three
  evidence tiers: ``"raw_generation"``, ``"adaptive_reflow"``,
  ``"postprocess_assisted"``. These are the canonical labels for the
  three layers that the panel must keep separated.
* :class:`LayeredMetricPanel` — frozen dataclass carrying the three
  per-tier metric mappings and the ``separation_enforced`` flag
  (which always defaults to ``True``; the constructor rejects any
  value other than ``True``).
* :func:`enforce_separation` — pure validator that returns a
  ``(ok, overlapping_keys)`` tuple. When the three tiers share any
  key the function returns ``(False, sorted_overlapping_keys)``;
  otherwise ``(True, ())``. The function is the single source of
  truth for tier separation; the constructor invokes it as a
  validation gate.

Module boundary:

* stdlib-only. **No** ``torch``. No I/O. No mutation of inputs.
* All dataclasses are ``frozen=True``.
* Tier separation is enforced at construction time. The
  ``separation_enforced`` flag cannot be set to ``False``.

Tasks satisfied:

* ``DTB-R8`` — structural promotion / rollback / claim gate
  (skeleton). The layered metric panel is a structural accounting
  device, not an actual metric-aggregation implementation.

Notes on tier semantics
------------------------
* ``raw_generation`` carries metrics from the raw first-pass model
  output (e.g. baseline GNINA binding, raw QED/ADMET).
* ``adaptive_reflow`` carries metrics that arise from the
  ``adaptive_reflow`` policy — i.e. from the executable writer.
* ``postprocess_assisted`` carries metrics derived from
  post-processing or downstream assistance (e.g. calibration
  re-scoring, sanitisation re-evaluations).

The three tiers **must not** share key names. This is the structural
rule enforced by :func:`enforce_separation` — it guarantees that
callers cannot accidentally double-count a metric across tiers when
constructing a promotion report.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any, Literal

__all__ = [
    "TIER_LABELS",
    "LayeredEvidenceTiers",
    "LayeredMetricPanel",
    "LayeredMetricPanelArgumentError",
    "build_default_layered_metric_panel",
    "enforce_separation",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


#: Canonical tier labels, in the order they appear in
#: :class:`LayeredMetricPanel`. Used by
#: :func:`enforce_separation` for deterministic iteration.
TIER_LABELS: tuple[str, ...] = (
    "raw_generation",
    "adaptive_reflow",
    "postprocess_assisted",
)

#: ``Literal`` alias accepted by :class:`LayeredMetricPanel` field
#: annotations and exposed via :data:`__all__` for callers that want
#: to refer to it symbolically.
LayeredEvidenceTiers = Literal[
    "raw_generation",
    "adaptive_reflow",
    "postprocess_assisted",
]


# ---------------------------------------------------------------------------
# Canonical error codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

ERR_PANEL_NONE: str = "layered_metric_panel_must_not_be_none"
ERR_TIER_MAPPING_NONE: str = (
    "layered_metric_panel_tier_mapping_must_not_be_none"
)
ERR_SEPARATION_FLAG: str = (
    "layered_metric_panel_separation_enforced_must_be_true"
)
ERR_TIER_KEY_OVERLAP: str = (
    "layered_metric_panel_tier_key_overlap"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LayeredMetricPanelArgumentError(ValueError):
    """Raised when layered-metric-panel construction fails validation.

    Inherits from :class:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns keep working; the subclass
    is exposed via :data:`__all__` for callers that want to narrow
    their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class LayeredMetricPanel:
    """Frozen panel of per-tier metric mappings.

    Attributes
    ----------
    raw_generation_metrics:
        Mapping of metric name -> value for the
        ``raw_generation`` tier.
    adaptive_reflow_metrics:
        Mapping of metric name -> value for the
        ``adaptive_reflow`` tier.
    postprocess_assisted_metrics:
        Mapping of metric name -> value for the
        ``postprocess_assisted`` tier.
    separation_enforced:
        Structural invariant — always ``True``. Construction rejects
        any value other than ``True``.
    """

    raw_generation_metrics: Mapping[str, Any]
    adaptive_reflow_metrics: Mapping[str, Any]
    postprocess_assisted_metrics: Mapping[str, Any]
    separation_enforced: bool = True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tier_keys(mapping: Mapping[str, Any]) -> set[str]:
    """Return the stringified key set of ``mapping``."""
    return {str(k) for k in mapping}


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------


def enforce_separation(
    panel: LayeredMetricPanel,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(ok, overlapping_keys)`` for ``panel``.

    Iterates the three tier mappings in deterministic order
    (:data:`TIER_LABELS`) and accumulates the set of key strings that
    appear in **two or more** tiers. The returned tuple is:

    * ``(True, ())`` when no tier shares any key.
    * ``(False, sorted_overlapping_keys)`` when at least one key is
      shared.

    The function is pure: it does not mutate ``panel``.

    Parameters
    ----------
    panel:
        The :class:`LayeredMetricPanel` to inspect. Must not be
        ``None``.
    """
    if panel is None:
        raise LayeredMetricPanelArgumentError(ERR_PANEL_NONE)
    if not isinstance(panel, LayeredMetricPanel):
        raise LayeredMetricPanelArgumentError(
            f"panel must be a LayeredMetricPanel, got "
            f"{type(panel).__name__}"
        )

    raw_keys = _tier_keys(panel.raw_generation_metrics)
    adaptive_keys = _tier_keys(panel.adaptive_reflow_metrics)
    post_keys = _tier_keys(panel.postprocess_assisted_metrics)

    overlap: set[str] = set()
    # raw_generation vs adaptive_reflow
    overlap.update(raw_keys.intersection(adaptive_keys))
    # raw_generation vs postprocess_assisted
    overlap.update(raw_keys.intersection(post_keys))
    # adaptive_reflow vs postprocess_assisted
    overlap.update(adaptive_keys.intersection(post_keys))

    if not overlap:
        return (True, ())
    return (False, tuple(sorted(overlap)))


# ---------------------------------------------------------------------------
# Construction helper
# ---------------------------------------------------------------------------


def build_default_layered_metric_panel(
    *,
    raw_generation_metrics: Mapping[str, Any],
    adaptive_reflow_metrics: Mapping[str, Any],
    postprocess_assisted_metrics: Mapping[str, Any],
    separation_enforced: bool = True,
) -> LayeredMetricPanel:
    """Build a :class:`LayeredMetricPanel` with separation enforced.

    Validates inputs, enforces the ``separation_enforced`` invariant,
    and rejects any overlapping tier keys by raising
    :class:`LayeredMetricPanelArgumentError`.

    Parameters
    ----------
    raw_generation_metrics, adaptive_reflow_metrics, postprocess_assisted_metrics:
        Per-tier metric mappings. Must be ``Mapping`` instances; keys
        must not overlap across tiers.
    separation_enforced:
        Must be ``True``. Defaults to ``True``.
    """
    if raw_generation_metrics is None:
        raise LayeredMetricPanelArgumentError(
            f"{ERR_TIER_MAPPING_NONE}: raw_generation_metrics"
        )
    if adaptive_reflow_metrics is None:
        raise LayeredMetricPanelArgumentError(
            f"{ERR_TIER_MAPPING_NONE}: adaptive_reflow_metrics"
        )
    if postprocess_assisted_metrics is None:
        raise LayeredMetricPanelArgumentError(
            f"{ERR_TIER_MAPPING_NONE}: postprocess_assisted_metrics"
        )
    if not isinstance(raw_generation_metrics, Mapping):
        raise LayeredMetricPanelArgumentError(
            f"raw_generation_metrics must be a Mapping, got "
            f"{type(raw_generation_metrics).__name__}"
        )
    if not isinstance(adaptive_reflow_metrics, Mapping):
        raise LayeredMetricPanelArgumentError(
            f"adaptive_reflow_metrics must be a Mapping, got "
            f"{type(adaptive_reflow_metrics).__name__}"
        )
    if not isinstance(postprocess_assisted_metrics, Mapping):
        raise LayeredMetricPanelArgumentError(
            f"postprocess_assisted_metrics must be a Mapping, got "
            f"{type(postprocess_assisted_metrics).__name__}"
        )
    if not bool(separation_enforced):
        raise LayeredMetricPanelArgumentError(ERR_SEPARATION_FLAG)

    panel = LayeredMetricPanel(
        raw_generation_metrics=raw_generation_metrics,
        adaptive_reflow_metrics=adaptive_reflow_metrics,
        postprocess_assisted_metrics=postprocess_assisted_metrics,
        separation_enforced=True,
    )
    ok, overlapping = enforce_separation(panel)
    if not ok:
        raise LayeredMetricPanelArgumentError(
            f"{ERR_TIER_KEY_OVERLAP}: keys {list(overlapping)} appear in "
            f"more than one tier; tier separation is required"
        )
    return panel
