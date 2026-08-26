"""RMS-preserving coordinate mixer — concrete ``RestartMixer`` implementation.

This module is the molecule-specific concrete implementation of the
universal :class:`adaptive_reflow.universal.mixer.RestartMixer` Protocol.
It is a verbatim port of the legacy
``adaptive_reflow.legacy.restart_mixer.adaptive_reflow_memory_restart_coords``
function onto the universal Protocol surface.

Module boundary
---------------

* Implements the ``RestartMixer`` Protocol by wrapping the existing
  RMS-preserving coordinate blender and re-shaping its return tuple.
* Provides a back-compat free function
  :func:`adaptive_reflow_memory_restart_coords` so legacy callers that
  import from ``legacy.restart_mixer`` keep working.
* The mixer is *torch-bound* (the molecule coordinate blender operates on
  ``(N, 3)`` torch tensors). The mixer raises :class:`RuntimeError` if
  torch is unavailable.

Public surface
--------------

Classes
    :class:`RMSPreservingCoordinateMixer`

Free functions
    :func:`adaptive_reflow_memory_restart_coords`
    :func:`require_torch`

Tasks satisfied
---------------

* ``DTB-L3`` — restart mixer protocol is universal; molecule RMS-preserving
  mixer lives here.
* ``DTB-L4`` — restart mixing is observable; the returned mapping carries
  the pre-/post-RMS diagnostics.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

try:
    import torch
except Exception:  # pragma: no cover - optional dependency
    torch = None


def require_torch() -> None:
    if torch is None:
        raise RuntimeError("torch is required for adaptive reflow restart memory")


@dataclass(frozen=True)
class RestartMemoryState:
    """Auditable stochastic-bridge state used between adaptive reflow rounds."""

    alpha_noise: float
    beta_memory: float
    prior_rms: float
    memory_rms: float
    restart_rms: float
    coords_bias_norm: float
    physical_jitter_fraction: float = 0.0
    physical_jitter_rms: float = 0.0
    source_round: int | None = None
    metric_confidence: float | None = None
    state_lock_is_detached: bool = True
    update_scope: str = "ode_restart_distribution_only"

    def as_ledger(self) -> dict[str, float | int | bool | str | None]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Free function: legacy verbatim
# ---------------------------------------------------------------------------


def adaptive_reflow_memory_restart_coords(
    prior_coords: Any,
    memory_coords: Any,
    *,
    memory_fraction: float,
    physical_jitter_fraction: float = 0.0,
    source_round: int | None = None,
    metric_confidence: float | None = None,
) -> tuple[Any, dict[str, float | int | bool | str | None | dict[str, float | int | bool | str | None]]]:
    """Mix a fresh prior state with a detached endpoint memory.

    The restart remains a t=0-like state by preserving the fresh prior RMS
    around its center.  This is not an SDF post-processing move: the next flow
    trajectory still owns coordinate evolution.
    """

    require_torch()
    fraction = float(memory_fraction)
    if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
        raise ValueError("adaptive reflow memory_fraction must be finite and in [0, 1]")
    jitter_fraction = float(physical_jitter_fraction)
    if not math.isfinite(jitter_fraction) or not 0.0 <= jitter_fraction <= 1.0:
        raise ValueError("adaptive reflow physical_jitter_fraction must be finite and in [0, 1]")
    prior = torch.as_tensor(prior_coords)
    memory = torch.as_tensor(memory_coords).to(device=prior.device, dtype=prior.dtype)
    if tuple(prior.shape) != tuple(memory.shape) or prior.dim() != 2 or int(prior.shape[-1]) != 3:
        raise ValueError("adaptive reflow memory coordinates must have shape (atoms, 3) matching the prior")
    if not bool(torch.isfinite(prior).all()) or not bool(torch.isfinite(memory).all()):
        raise ValueError("adaptive reflow restart coordinates must be finite")
    prior_offsets = prior - prior.mean(dim=0, keepdim=True)
    prior_rms = prior_offsets.square().sum(dim=-1).mean().sqrt() if prior.numel() else prior.new_tensor(0.0)
    if fraction <= 0.0:
        prior_rms_value = float(prior_rms.detach().cpu()) if prior.numel() else 0.0
        state = RestartMemoryState(
            alpha_noise=1.0,
            beta_memory=0.0,
            prior_rms=prior_rms_value,
            memory_rms=0.0,
            restart_rms=prior_rms_value,
            coords_bias_norm=0.0,
            physical_jitter_fraction=jitter_fraction,
            physical_jitter_rms=0.0,
            source_round=source_round,
            metric_confidence=metric_confidence,
        )
        return prior.clone(), {
            "adaptive_reflow_restart_enabled": 0.0,
            "adaptive_reflow_memory_fraction": 0.0,
            "adaptive_reflow_restart_alpha_noise": 1.0,
            "adaptive_reflow_restart_beta_memory": 0.0,
            "adaptive_reflow_prior_rms": prior_rms_value,
            "adaptive_reflow_memory_rms": 0.0,
            "adaptive_reflow_restart_rms": prior_rms_value,
            "adaptive_reflow_restart_coords_bias_norm": 0.0,
            "adaptive_reflow_restart_physical_jitter_fraction": jitter_fraction,
            "adaptive_reflow_restart_physical_jitter_rms": 0.0,
            "adaptive_reflow_restart_state_lock_is_detached": True,
            "adaptive_reflow_restart_state": state.as_ledger(),
        }
    center = prior.mean(dim=0, keepdim=True)
    memory_offsets = memory - memory.mean(dim=0, keepdim=True)
    memory_rms = memory_offsets.square().sum(dim=-1).mean().sqrt()
    if float(memory_rms.detach().cpu()) > 1.0e-8:
        memory_offsets = memory_offsets * (prior_rms / memory_rms.clamp_min(1.0e-8))
    blended_offsets = (1.0 - fraction) * prior_offsets + fraction * memory_offsets
    physical_jitter_rms = 0.0
    if jitter_fraction > 0.0 and prior.numel():
        jitter = torch.randn_like(prior_offsets)
        jitter = jitter - jitter.mean(dim=0, keepdim=True)
        jitter_rms = jitter.square().sum(dim=-1).mean().sqrt()
        if float(jitter_rms.detach().cpu()) > 1.0e-8:
            jitter = jitter * (prior_rms * jitter_fraction / jitter_rms.clamp_min(1.0e-8))
            blended_offsets = blended_offsets + jitter
            physical_jitter_rms = float(jitter.square().sum(dim=-1).mean().sqrt().detach().cpu())
    blended_rms = blended_offsets.square().sum(dim=-1).mean().sqrt()
    if float(blended_rms.detach().cpu()) > 1.0e-8:
        blended_offsets = blended_offsets * (prior_rms / blended_rms.clamp_min(1.0e-8))
    restart = center + blended_offsets
    restart_rms = blended_offsets.square().sum(dim=-1).mean().sqrt()
    coords_bias_norm = float((restart - prior).square().sum(dim=-1).mean().sqrt().detach().cpu()) if prior.numel() else 0.0
    state = RestartMemoryState(
        alpha_noise=float(1.0 - fraction),
        beta_memory=fraction,
        prior_rms=float(prior_rms.detach().cpu()),
        memory_rms=float(memory_rms.detach().cpu()),
        restart_rms=float(restart_rms.detach().cpu()),
        coords_bias_norm=coords_bias_norm,
        physical_jitter_fraction=jitter_fraction,
        physical_jitter_rms=physical_jitter_rms,
        source_round=source_round,
        metric_confidence=metric_confidence,
    )
    return restart, {
        "adaptive_reflow_restart_enabled": 1.0,
        "adaptive_reflow_memory_fraction": fraction,
        "adaptive_reflow_restart_alpha_noise": float(1.0 - fraction),
        "adaptive_reflow_restart_beta_memory": fraction,
        "adaptive_reflow_prior_rms": float(prior_rms.detach().cpu()),
        "adaptive_reflow_memory_rms": float(memory_rms.detach().cpu()),
        "adaptive_reflow_restart_rms": float(restart_rms.detach().cpu()),
        "adaptive_reflow_restart_coords_bias_norm": coords_bias_norm,
        "adaptive_reflow_restart_physical_jitter_fraction": jitter_fraction,
        "adaptive_reflow_restart_physical_jitter_rms": physical_jitter_rms,
        "adaptive_reflow_restart_state_lock_is_detached": True,
        "adaptive_reflow_restart_state": state.as_ledger(),
    }


# ---------------------------------------------------------------------------
# RMSPreservingCoordinateMixer — concrete RestartMixer Protocol impl
# ---------------------------------------------------------------------------


class RMSPreservingCoordinateMixer:
    """RMS-preserving coordinate blender for ``(N, 3)`` coordinate tensors.

    This is the molecule-specific concrete implementation of the
    :class:`adaptive_reflow.universal.mixer.RestartMixer` Protocol. It is
    a thin wrapper around :func:`adaptive_reflow_memory_restart_coords`
    that re-shapes its return tuple to the universal ``(state, ledger)``
    contract.
    """

    def mix(
        self,
        *,
        prior: Any,
        memory: Any,
        beta: float,
        jitter_fraction: float = 0.0,
        source_round: int | None = None,
        metric_confidence: float | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        """Mix ``prior`` with ``memory`` according to ``beta``.

        Parameters
        ----------
        prior:
            The fresh prior state (an ``(N, 3)`` coordinate tensor).
        memory:
            The detached endpoint / memory state. Must match ``prior``'s
            shape (``(N, 3)``) and dtype.
        beta:
            Memory fraction in ``[0, 1]``. ``0.0`` returns the prior
            unchanged; ``1.0`` returns the (RMS-rescaled) memory.
        jitter_fraction:
            Optional physical-jitter fraction in ``[0, 1]``. The jitter
            is centered Gaussian noise added in coordinate space.
        source_round:
            Optional source-round tag, propagated into the returned
            ledger.
        metric_confidence:
            Optional metric-confidence value, propagated into the
            returned ledger.

        Returns
        -------
        (restart_tensor, ledger):
            ``restart_tensor`` is the RMS-preserved blended state;
            ``ledger`` is a ``Mapping[str, Any]`` of numeric diagnostics
            keyed by the canonical ``adaptive_reflow_restart_*`` names.
        """
        return adaptive_reflow_memory_restart_coords(
            prior,
            memory,
            memory_fraction=float(beta),
            physical_jitter_fraction=float(jitter_fraction),
            source_round=source_round,
            metric_confidence=metric_confidence,
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "RMSPreservingCoordinateMixer",
    "RestartMemoryState",
    # Back-compat free function (legacy verbatim).
    "adaptive_reflow_memory_restart_coords",
    "require_torch",
]
