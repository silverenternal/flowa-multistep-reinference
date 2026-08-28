"""Extra P0/P1 restart blender implementations.

Provides two additional :class:`RestartBlenderProtocol` implementations
called out by the algorithm-deep-uplift plan:

* :class:`OTLinearBlender` — closed-form 1-D optimal-transport map
  between the prior and fresh endpoints, then convex blend along the
  OT path (P0; mirrors "Contrastive Blending in Latent Space",
  arXiv:2403.08624).
* :class:`MultiTemperatureDistanceDecayBlender` — per-channel
  temperature overrides for the distance-decay blender (P1).

Both follow the canonical surface from :class:`LinearBlender`:
``blend(prior, fresh, memory_fraction, channel, audit_codes) -> StateBundle``
plus ``config_hash`` / ``blender_family`` / ``to_config`` /
``from_config``.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O.
* Deterministic: identical inputs always yield identical outputs.
* Fail-closed: bad ``memory_fraction``, ``temperature``, or
  ``per_channel_temperatures`` arguments raise :class:`ValueError`.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, ClassVar

from adaptive_reflow.universal.state import StateBundle

from .blender import (
    BLENDER_MEMORY_FRACTION_CLIPPED,
    DistanceDecayBlender,
    LinearBlender,
    _as_tuple,
    _coerce_memory_fraction,
    _distance,
    _extract_channel_value,
    _linear_blend_arrays,
    _make_blend_bundle,
    _sigmoid,
)


class OTLinearBlender:
    """Closed-form 1-D OT-path linear blender (P0).

    The closed-form 1-D optimal-transport map between two 1-D point
    clouds is the sorted-coordinate map: sort ``prior`` and ``fresh``
    by coordinate value, then pair the ``k``-th sorted element of
    ``prior`` with the ``k``-th sorted element of ``fresh``. The
    convex blend along the OT path is

        ot_path[k] = m * sorted_prior[k] + (1 - m) * sorted_fresh[k]

    then we re-permute ``ot_path`` back into the prior's original
    index order so the returned tuple aligns with the input ordering.
    For multi-dimensional tuples the OT map is computed element-wise
    on each coordinate (a per-coordinate 1-D OT) which matches the
    closed-form 1-D OT in every coordinate simultaneously.

    Concretely: if ``prior = (p_0, p_1)`` and ``fresh = (f_0, f_1)``
    with ``p_0 < p_1`` and ``f_0 < f_1``, the OT map pairs
    ``p_0 -> f_0`` and ``p_1 -> f_1``. The convex blend returns
    ``(m*p_0 + (1-m)*f_0, m*p_1 + (1-m)*f_1)`` re-permuted back
    into the prior's index order.

    Module boundary: stdlib-only; the OT step is the canonical
    closed-form 1-D solution and is exact for arbitrary sample sizes
    (no iterative Sinkhorn loop).
    """

    FAMILY: ClassVar[str] = "ot_linear"

    def __init__(self) -> None:
        # No state; kept for symmetry with the LinearBlender and to
        # leave room for future per-instance knobs.
        pass

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        if len(prior_value) != len(fresh_value):
            raise ValueError(
                "prior_and_fresh_length_mismatch: prior="
                f"{len(prior_value)} fresh={len(fresh_value)}"
            )
        # Closed-form 1-D OT: sort both by value, blend along the OT
        # pair, then re-permute back into the prior's index order.
        prior_order = sorted(
            range(len(prior_value)), key=lambda k: prior_value[k]
        )
        fresh_order = sorted(
            range(len(fresh_value)), key=lambda k: fresh_value[k]
        )
        sorted_prior = [prior_value[k] for k in prior_order]
        sorted_fresh = [fresh_value[o] for o in fresh_order]
        ot_sorted = [
            m * p + (1.0 - m) * f
            for p, f in zip(sorted_prior, sorted_fresh, strict=True)
        ]
        # Invert prior_order: sorted position -> prior index.
        inverse = [0] * len(prior_order)
        for sorted_idx, original_idx in enumerate(prior_order):
            inverse[original_idx] = sorted_idx
        blended = tuple(ot_sorted[inverse[i]] for i in range(len(prior_value)))
        return _make_blend_bundle(
            prior_state,
            channel=channel,
            memory_fraction=m,
            blended_value=blended,
            blender_hash=self.config_hash(),
            blender_family=self.blender_family(),
            decay_factor=None,
        )

    def blender_family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        from .blender import _blender_config_hash

        return _blender_config_hash(
            family=self.FAMILY, qualname=type(self).__qualname__
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> OTLinearBlender:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls()


class MultiTemperatureDistanceDecayBlender:
    """Per-channel temperature overrides for distance-decay (P1).

    Wraps :class:`DistanceDecayBlender` and looks up the per-channel
    temperature in :attr:`per_channel_temperatures` before delegating
    the blend. Falls back to :attr:`default_temperature` for channels
    absent from the mapping. The ``per_channel_temperatures`` mapping
    is folded into ``config_hash`` so two blenders with different
    per-channel temperatures are distinguishable in the audit trail.
    """

    FAMILY: ClassVar[str] = "multi_temperature_distance_decay"

    def __init__(
        self,
        *,
        default_temperature: float = 1.0,
        per_channel_temperatures: Mapping[str, float] | None = None,
    ) -> None:
        if (
            not isinstance(default_temperature, (int, float))
            or isinstance(default_temperature, bool)
        ):
            raise ValueError(
                "default_temperature must be a real number, got "
                f"{type(default_temperature).__name__}"
            )
        t = float(default_temperature)
        if not math.isfinite(t) or t <= 0.0:
            raise ValueError(
                "default_temperature must be finite and > 0, got "
                f"{t!r}"
            )
        self._default_temperature = t
        cleaned: dict[str, float] = {}
        if per_channel_temperatures is not None:
            if not isinstance(per_channel_temperatures, Mapping):
                raise ValueError(
                    "per_channel_temperatures must be a Mapping, got "
                    f"{type(per_channel_temperatures).__name__}"
                )
            for k, v in dict(per_channel_temperatures).items():
                if (
                    not isinstance(v, (int, float))
                    or isinstance(v, bool)
                ):
                    raise ValueError(
                        f"per_channel_temperatures[{k!r}] must be a "
                        f"real number, got {v!r}"
                    )
                vf = float(v)
                if not math.isfinite(vf) or vf <= 0.0:
                    raise ValueError(
                        f"per_channel_temperatures[{k!r}] must be "
                        f"finite and > 0, got {vf!r}"
                    )
                cleaned[str(k)] = float(vf)
        self._per_channel: dict[str, float] = cleaned

    @property
    def default_temperature(self) -> float:
        return float(self._default_temperature)

    @property
    def per_channel_temperatures(self) -> dict[str, float]:
        return dict(self._per_channel)

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        d = _distance(prior_value, fresh_value)
        temperature = float(
            self._per_channel.get(str(channel), self._default_temperature)
        )
        decay = _sigmoid(-d / temperature)
        one_minus_m = 1.0 - m
        blended = tuple(
            m * float(p) + one_minus_m * float(f) * decay
            for p, f in zip(prior_value, fresh_value, strict=True)
        )
        return _make_blend_bundle(
            prior_state,
            channel=channel,
            memory_fraction=m,
            blended_value=blended,
            blender_hash=self.config_hash(),
            blender_family=self.blender_family(),
            decay_factor=decay,
        )

    def blender_family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        from .blender import _blender_config_hash

        extra: dict[str, Any] = {
            "default_temperature": float(self._default_temperature),
            "per_channel_temperatures": {
                str(k): float(v)
                for k, v in sorted(self._per_channel.items())
            },
        }
        return _blender_config_hash(
            family=self.FAMILY,
            qualname=type(self).__qualname__,
            extra=extra,
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "default_temperature": float(self._default_temperature),
            "per_channel_temperatures": {
                str(k): float(v)
                for k, v in sorted(self._per_channel.items())
            },
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> MultiTemperatureDistanceDecayBlender:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        raw = config.get("per_channel_temperatures") or {}
        return cls(
            default_temperature=float(config.get("default_temperature", 1.0)),
            per_channel_temperatures=dict(raw),
        )


__all__ = [
    "MultiTemperatureDistanceDecayBlender",
    "OTLinearBlender",
]
