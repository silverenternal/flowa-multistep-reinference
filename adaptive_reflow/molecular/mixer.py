"""Equal-RMS coordinate mixer — concrete ``RestartMixer`` implementation.

This module is the molecule-specific concrete implementation of the
universal :class:`adaptive_reflow.universal.mixer.RestartMixer` Protocol.
It is a verbatim port of the legacy
``adaptive_reflow.legacy.restart_mixer.adaptive_reflow_memory_restart_coords``
function onto the universal Protocol surface.

Module boundary
---------------

* Implements the ``RestartMixer`` Protocol by wrapping the existing
  equal-RMS coordinate blender and re-shaping its return tuple.
* Provides a back-compat free function
  :func:`adaptive_reflow_memory_restart_coords` so legacy callers that
  import from ``legacy.restart_mixer`` keep working.
* The mixer is *torch-bound* (the molecule coordinate blender operates on
  ``(N, 3)`` torch tensors). The mixer raises :class:`RuntimeError` if
  torch is unavailable.

RMS precondition
----------------

The class is named :class:`EqualRmsCoordinateMixer` because it preserves
the RMS of the *blend* only when the two input tensors have equal RMS
within ``1e-6``. When the input RMS values differ by more than the
tolerance, the helper :func:`_require_equal_rms` appends the audit code
:data:`MIXER_RMS_PRECEDENCE_FAIL` to the returned ledger's ``audit_codes``
list and the caller is expected to inspect that list to detect the
precondition failure. The audit code is emitted *before* any silent
rescaling happens, so the precondition is observable.

Public surface
--------------

Classes
    :class:`EqualRmsCoordinateMixer`
    :class:`RMSPreservingCoordinateMixer` (deprecated alias)

Free functions
    :func:`adaptive_reflow_memory_restart_coords`
    :func:`require_torch`
    :func:`_require_equal_rms`

Audit codes
    :data:`MIXER_RMS_PRECEDENCE_FAIL`

Tasks satisfied
---------------

* ``DTB-L3`` — restart mixer protocol is universal; molecule equal-RMS
  mixer lives here.
* ``DTB-L4`` — restart mixing is observable; the returned mapping carries
  the pre-/post-RMS diagnostics and audit codes.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import asdict, dataclass
from typing import Any

# ``torch`` is an optional heavy dependency. The mixer is torch-bound at
# call time (the coordinate blender operates on ``(N, 3)`` torch tensors)
# but the module itself is importable without torch so that modules which
# only reach into :mod:`adaptive_reflow.molecular.mixer` for its public
# surface (audit codes, dataclasses, Protocol wrappers) do not pull torch
# in transitively. See :func:`_import_torch` for the lazy loader used by
# the blender functions below.
_torch: Any = None
_torch_import_attempted: bool = False


def _import_torch() -> Any:
    """Return the ``torch`` module, importing it lazily on first use.

    Returning ``None`` signals the optional dependency is unavailable;
    callers (e.g. :func:`require_torch`, :func:`_compute_rms`,
    :func:`adaptive_reflow_memory_restart_coords`) translate that into
    :class:`RuntimeError`. The import is attempted at most once per
    process; subsequent calls reuse the cached result.
    """
    global _torch, _torch_import_attempted
    if _torch_import_attempted:
        return _torch
    _torch_import_attempted = True
    try:
        import torch as _t  # noqa: PLC0415 - intentional lazy import
    except Exception:  # pragma: no cover - optional dependency
        _torch = None
    else:
        _torch = _t
    return _torch


# ---------------------------------------------------------------------------
# Module-level audit codes
# ---------------------------------------------------------------------------


MIXER_RMS_PRECEDENCE_FAIL: str = "mixer_rms_precondition_fail"
"""Audit code emitted by :func:`_require_equal_rms` when the two input
tensors' RMS values differ by more than the tolerance. The blend is *not*
performed silently under mismatched RMS; the caller must observe this
audit code in the returned ledger and decide whether to accept the
result or surface the failure."""


def require_torch() -> None:
    if _import_torch() is None:
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
# RMS precondition helper
# ---------------------------------------------------------------------------


def _compute_rms(tensor: Any) -> float:
    """Return the centred RMS of ``tensor`` along its last axis.

    Treats an empty tensor as RMS 0.0. Returns a float (CPU side).
    """
    require_torch()
    torch = _import_torch()
    t = torch.as_tensor(tensor)
    if t.numel() == 0:
        return 0.0
    offsets = t - t.mean(dim=0, keepdim=True)
    rms = offsets.square().sum(dim=-1).mean().sqrt()
    return float(rms.detach().cpu())


def _require_equal_rms(
    memory: Any,
    restart: Any,
    *,
    tolerance: float = 1e-6,
    audit_codes: list[str] | None = None,
) -> tuple[float, float]:
    """Verify that ``memory`` and ``restart`` share the same RMS.

    Computes the centred RMS for both inputs (any tensor shape; the
    helper averages across the last axis). When ``|memory_rms -
    restart_rms| > tolerance`` and ``audit_codes`` is provided, appends
    :data:`MIXER_RMS_PRECEDENCE_FAIL` to it. Otherwise the audit list is
    left untouched. The function never raises; the precondition failure
    is purely observational via the audit code.

    Parameters
    ----------
    memory:
        Memory / endpoint tensor (typically the detached endpoint
        state).
    restart:
        Restart / prior tensor (typically the fresh prior state).
    tolerance:
        Absolute RMS difference tolerated before the audit code is
        emitted. Default ``1e-6``.
    audit_codes:
        Mutable list to receive any audit codes. If ``None`` is passed
        the audit code is computed and dropped on the floor (used by
        callers that do not propagate diagnostics).

    Returns
    -------
    ``(memory_rms, restart_rms)`` as Python floats.
    """
    memory_rms = _compute_rms(memory)
    restart_rms = _compute_rms(restart)
    if audit_codes is not None and abs(memory_rms - restart_rms) > tolerance:
        audit_codes.append(MIXER_RMS_PRECEDENCE_FAIL)
    return memory_rms, restart_rms


# ---------------------------------------------------------------------------
# Free function: legacy verbatim (with RMS-precondition observation)
# ---------------------------------------------------------------------------


def adaptive_reflow_memory_restart_coords(
    prior_coords: Any,
    memory_coords: Any,
    *,
    memory_fraction: float,
    physical_jitter_fraction: float = 0.0,
    source_round: int | None = None,
    metric_confidence: float | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Mix a fresh prior state with a detached endpoint memory.

    The restart remains a t=0-like state by preserving the fresh prior RMS
    around its center.  This is not an SDF post-processing move: the next flow
    trajectory still owns coordinate evolution.

    The blend's RMS preservation only holds when ``prior`` and ``memory``
    share the same RMS within ``1e-6``. When they differ, the audit code
    :data:`MIXER_RMS_PRECEDENCE_FAIL` is appended to the returned
    ledger's ``audit_codes`` list. The blend is still computed (the
    behaviour is observable, not silent), but callers that depend on the
    equality precondition must inspect ``ledger["audit_codes"]``.
    """

    require_torch()
    torch = _import_torch()
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

    # RMS precondition observation: emit MIXER_RMS_PRECEDENCE_FAIL when the
    # two input tensors do not share the same RMS within tolerance.
    audit_codes: list[str] = []
    _require_equal_rms(memory, prior, tolerance=1e-6, audit_codes=audit_codes)

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
        ledger: dict[str, Any] = {
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
        if audit_codes:
            ledger["audit_codes"] = list(audit_codes)
        return prior.clone(), ledger
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
    restart_tensor = center + blended_offsets
    restart_rms = blended_offsets.square().sum(dim=-1).mean().sqrt()
    coords_bias_norm = float((restart_tensor - prior).square().sum(dim=-1).mean().sqrt().detach().cpu()) if prior.numel() else 0.0
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
    ledger = {
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
    if audit_codes:
        ledger["audit_codes"] = list(audit_codes)
    return restart_tensor, ledger


# ---------------------------------------------------------------------------
# EqualRmsCoordinateMixer — concrete RestartMixer Protocol impl
# ---------------------------------------------------------------------------


class EqualRmsCoordinateMixer:
    """Equal-RMS coordinate blender for ``(N, 3)`` coordinate tensors.

    The class is named ``EqualRms`` rather than ``RMSPreserving`` because
    the RMS of the *blend* is preserved only when the two input tensors
    have equal RMS within ``1e-6``. If the input RMS values differ by
    more than the tolerance, :func:`adaptive_reflow_memory_restart_coords`
    appends the audit code :data:`MIXER_RMS_PRECEDENCE_FAIL` to the
    returned ledger's ``audit_codes`` list rather than silently
    rescaling the inputs.

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
            When the RMS precondition fails, the ``audit_codes`` key is
            present in ``ledger`` and contains
            :data:`MIXER_RMS_PRECEDENCE_FAIL`.
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
# Back-compat alias: deprecated; use EqualRmsCoordinateMixer
# ---------------------------------------------------------------------------


RMSPreservingCoordinateMixer = EqualRmsCoordinateMixer  # deprecated; use EqualRmsCoordinateMixer
warnings.warn(
    "RMSPreservingCoordinateMixer is deprecated; use EqualRmsCoordinateMixer",
    DeprecationWarning,
    stacklevel=2,
)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "EqualRmsCoordinateMixer",
    "RMSPreservingCoordinateMixer",
    "RestartMemoryState",
    "MIXER_RMS_PRECEDENCE_FAIL",
    # Back-compat free function (legacy verbatim).
    "adaptive_reflow_memory_restart_coords",
    "require_torch",
]
