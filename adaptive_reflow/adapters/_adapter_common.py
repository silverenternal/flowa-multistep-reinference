"""Shared, byte-stable helpers for concrete FlowMatchingODEAdapter impls.

P2-9: ``_seed_from_ids`` was typed 9 times, ``_digest_state`` 10, ``_make_ref``
13, the ``_native_states`` LRU 9, the ``kaiming`` closure 7 — all byte-identical
apart from one string or one size constant. Every function here reproduces the
prior per-adapter body EXACTLY; the digests they emit are load-bearing for
``native_config_hash`` and the ledger chain, so behaviour changes are forbidden
without a paired digest-migration shim.

Stdlib + numpy only. No torch at module level.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.universal.state import ChannelName, TensorRef

ArrayF64 = NDArray[np.float64]


def seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """Deterministic 32-bit seed from the sample identity triple."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def digest_state(payload: Mapping[str, Any]) -> str:
    """SHA-256 hex digest of a payload (sorted keys, repr'd)."""
    blob = repr((sorted(payload.items(), key=lambda kv: str(kv[0])),)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def make_ref(prefix: str, label: str, **parts: Any) -> TensorRef:
    """Build a deterministic ``TensorRef``.

    ``prefix`` reproduces each adapter's historical namespace verbatim
    (``"mnist:x"``, ``"rf_cifar:image"``, ``"twodim:xy"``, ...). Adapters whose
    prefix embedded the label (``"graphbfn:{label}"``) pass ``prefix=f"graphbfn:{label}"`.
    """
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"{prefix}:{hashlib.sha256(blob).hexdigest()[:16]}")


def kaiming_uniform(
    rng: np.random.Generator, fan_in: int, fan_out: int
) -> ArrayF64:
    """He-uniform init, matching the 7 in-adapter ``kaiming`` closures."""
    bound = np.sqrt(6.0 / float(fan_in))
    return np.asarray(
        rng.uniform(-bound, bound, size=(fan_in, fan_out)), dtype=np.float64
    )


def torch_is_available() -> bool:
    """True iff ``torch`` imports. Never raises."""
    try:
        import torch  # noqa: F401, PLC0415 — availability probe only.
    except Exception:  # noqa: BLE001 — any import failure means unavailable.
        return False
    return True


def memory_fraction_for(
    policy: Any,
    channel: ChannelName,
    *,
    exterior_gap_e_rho: float | None = None,
    audit_codes: list[str] | None = None,
) -> tuple[float, float]:
    """Return ``(beta, memory_fraction)`` for ``channel`` under ``policy``.

    Replaces the 9 copies of the same block (each carrying its own
    ``# type: ignore[arg-type]``). Missing channel defaults to
    ``beta = memory_fraction = 0.5``, matching every prior copy.

    Paper-uplift-27 (P0-A12 — Lemma 5)
    ----------------------------------

    When ``exterior_gap_e_rho`` is supplied, the memory-fraction floor is
    lifted to ``max(1 - beta, e_rho / 4)`` so the bounded-merge envelope
    respects the paper's physical-complement minimum. Emits the audit
    code ``merge_paper_quantity_floor_lifted`` whenever the lift fires.
    The audit emission is gated on ``audit_codes is not None`` so the
    8 existing call sites stay byte-identical (no audit_codes kwarg
    => no behaviour change). The audit code constant is imported lazily
    to avoid a circular import at module load.
    """
    beta_raw = policy.beta_by_channel.get(channel)
    if beta_raw is None:
        return (0.5, 0.5)
    beta = float(beta_raw)
    floor = 1.0 - beta
    if exterior_gap_e_rho is not None and float(exterior_gap_e_rho) > 0.0:
        paper_floor = float(exterior_gap_e_rho) / 4.0
        if floor < paper_floor:
            floor = paper_floor
            if audit_codes is not None:
                from adaptive_reflow.algorithm.merge_operator import (
                    MERGE_PAPER_QUANTITY_FLOOR_LIFTED,
                )
                audit_codes.append(
                    f"{MERGE_PAPER_QUANTITY_FLOOR_LIFTED}"
                    f":floor={floor:.6f}"
                    f":e_rho={float(exterior_gap_e_rho):.6f}"
                )
    return (beta, floor)


class NativeStateCache:
    """Insertion-ordered LRU for ``_native_states`` (audit A-3).

    Exposes the ``OrderedDict`` surface that
    ``adapters/_inject_forward_noise.py:118,186`` reaches through
    (``.get`` / ``__setitem__`` / ``__contains__`` / ``__len__``), so the
    existing helper keeps working unchanged.
    """

    __slots__ = ("_data", "_maxsize")

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("native_state_cache_maxsize_must_be_positive")
        self._maxsize = int(maxsize)
        self._data: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def put(self, digest: str, entry: dict[str, Any]) -> None:
        if digest in self._data:
            self._data[digest] = entry
            self._data.move_to_end(digest)
            return
        self._data[digest] = entry
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def evict(self, digest: str) -> None:
        self._data.pop(digest, None)

    # -- OrderedDict-compatible surface (_inject_forward_noise.py) ----------
    def get(self, digest: str, default: Any = None) -> Any:
        return self._data.get(digest, default)

    def __getitem__(self, digest: str) -> dict[str, Any]:
        return self._data[digest]

    def __setitem__(self, digest: str, entry: dict[str, Any]) -> None:
        self.put(digest, entry)

    def __contains__(self, digest: object) -> bool:
        return digest in self._data

    def __len__(self) -> int:
        return len(self._data)

    def pop(self, digest: str, default: Any = None) -> Any:
        return self._data.pop(digest, default)


def make_adapter_capabilities(
    *,
    state_shape: tuple[int, ...],
    supported_channels: tuple[Any, ...],
    channel_domains: Mapping[Any, Any],
    native_config_hash: str,
    native_config_version: str,
    required_mixer: type | None = None,
    has_continuous_channels: bool = True,
    has_discrete_channels: bool = False,
    has_trajectory_digest: bool = True,
    has_materialization_route: bool = True,
    exposed_envelope_criteria: tuple[type, ...] = (),
    exposed_evaluators: tuple[type, ...] = (),
    **extra: Any,
) -> dict[str, Any]:
    """Kwargs for ``AdapterCapabilities.__init__``, with the shared defaults.

    The five always-True flags (ode surface / prior / state export /
    condition injection / restart boundary) hold for all 10 concrete
    capability classes; override via ``extra`` if a future adapter differs.
    """
    kwargs: dict[str, Any] = {
        "has_ode_integration_surface": True,
        "has_prior_export": True,
        "has_state_export": True,
        "has_condition_injection": True,
        "has_restart_boundary": True,
        "has_continuous_channels": has_continuous_channels,
        "has_discrete_channels": has_discrete_channels,
        "has_trajectory_digest": has_trajectory_digest,
        "has_deterministic_seed": True,
        "has_materialization_route": has_materialization_route,
        "state_shape": state_shape,
        "supported_channels": supported_channels,
        "channel_domains": channel_domains,
        "required_mixer": required_mixer,
        "exposed_envelope_criteria": exposed_envelope_criteria,
        "exposed_evaluators": exposed_evaluators,
        "native_config_hash": native_config_hash,
        "native_config_version": native_config_version,
    }
    kwargs.update(extra)
    return kwargs


def coerce_nfe_budget(value: Any) -> int | None:
    """Return ``value`` as a usable integer NFE budget, or ``None``.

    Wave 58: shared coercion for the NFE-adaptive restart gate (see
    :func:`low_nfe_restart_gate`). ``None`` means "this candidate does
    not carry a usable NFE budget" — it is **not** an error, because
    the gate reads its inputs off duck-typed restart policies where the
    attribute is frequently absent or unrelated.

    Rejected (⇒ ``None``): ``None``, ``bool`` (``True`` is an ``int``
    subclass but is never a budget), non-finite floats, non-integral
    floats, anything not coercible via ``int()``, and any value ``<= 1``
    (a one-step "budget" cannot be split across restart rounds).
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and not np.isfinite(value):
        return None
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return None
    # Guard against a silently-truncating float (``17.5`` is not a
    # step count; treating it as ``17`` would hide a caller bug).
    if isinstance(value, float) and float(coerced) != value:
        return None
    return coerced if coerced > 1 else None


def low_nfe_restart_gate(
    *candidates: Any,
    min_nfe: int,
) -> tuple[int | None, bool]:
    """Resolve the effective NFE budget and decide whether to skip restart.

    Wave 58 (FlowMol3 NFE-adaptive gate; see
    ``docs/audit/wave58-nfe-adaptive-gate-impl.md``). Returns
    ``(effective_nfe, skip_restart)`` where ``effective_nfe`` is the
    first entry of ``candidates`` that :func:`coerce_nfe_budget` accepts
    — so callers pass their candidates in **priority order** (explicit
    call argument, then policy attribute, then adapter default) — and
    ``skip_restart`` is ``effective_nfe < min_nfe``.

    Two contract points, both load-bearing:

    * **Unknown budget fails open.** When no candidate resolves,
      ``effective_nfe`` is ``None`` and ``skip_restart`` is ``False``:
      the caller applies its normal restart blend. This is what keeps
      the gate byte-stable for every existing caller that does not yet
      thread an NFE budget (the pinned D.4 regression vectors included).
    * **The budget is the TOTAL, not the per-round, NFE.** A caller
      that splits ``nfe`` across ``n_rounds`` must pass the total, not
      ``nfe // n_rounds``: at the FlowMol3 paper default (``nfe=50``,
      ``n_rounds=3``) the per-round count is 17, which would trip a
      threshold of 20 and silently disable restart in exactly the
      stratum where it currently helps.

    ``min_nfe <= 0`` disables the gate (no positive budget is below it).
    """
    for candidate in candidates:
        effective = coerce_nfe_budget(candidate)
        if effective is not None:
            return (effective, effective < int(min_nfe))
    return (None, False)


def per_position_entropy_reduction(
    theta_before: NDArray[np.float64],
    theta_after: NDArray[np.float64],
    eps: float = 1e-12,
) -> float:
    """Continuous, non-saturating framework-vs-baseline gap metric (P2-W33-C, Wave 45).

    Returns the per-position Shannon-entropy *reduction* from a baseline
    endpoint ``theta_before`` to a framework endpoint ``theta_after``::

        reduction = H(theta_before) - H(theta_after)

    A **positive** reduction means the framework ``sharpened`` the
    posterior relative to the baseline (entropy went down); a **negative**
    reduction means the framework widened it. The metric is bounded in
    ``[-log K, log K]`` where ``K`` is the cardinality of the last axis
    (e.g. ``K = 33`` for Pfam, ``K = 64`` for Kanzi's discrete vocab).

    The math is ported verbatim from
    ``tools/run_controlled_audit.py:702 _per_position_entropy`` (Wave 33
    P2-W33-C) and is the only place in the tree where this computation
    lives. Numerically-stable softmax along the last axis; the ``eps``
    floor is added *inside* the log (not on the entropy denominator) so
    the metric stays finite on a delta-spike input.

    Shape contract: ``theta_before`` and ``theta_after`` must broadcast on
    leading axes (samples, positions) and share the trailing ``K`` axis.
    Either may have an arbitrary number of leading axes; both are treated
    as logits over the trailing axis. The returned scalar is the mean of
    ``-sum(p * log(p + eps), axis=-1)`` across **all** leading axes.

    Degenerate inputs (empty or fewer than two samples in either argument)
    return ``float("nan")`` so callers can distinguish ``metric
    undefined`` from ``metric == 0`` (which would be the
    delta-spike-on-both-arms case).

    Stdlib + numpy only. No torch at module level (Wave 45 / P2-9
    contract).
    """
    def _entropy(endpoints: NDArray[np.float64]) -> float:
        if endpoints.size == 0 or endpoints.shape[0] < 2:
            return float("nan")
        # numerically-stable softmax along the K axis (last axis).
        z = endpoints - np.max(endpoints, axis=-1, keepdims=True)
        exp_z = np.exp(z)
        p = exp_z / np.sum(exp_z, axis=-1, keepdims=True)
        # Per-position Shannon entropy; mean across all leading axes
        # (samples, positions, ...) yields the batch-level scalar.
        per_position = -np.sum(p * np.log(p + eps), axis=-1)
        return float(np.mean(per_position))

    return _entropy(theta_before) - _entropy(theta_after)


def load_real_weights(
    weights_path: Any,
    *,
    builder: Any,
    stub_factory: Any = None,
    upstream_label: str,
    compat_shim: Any = None,
    map_location: str = "cpu",
) -> Any:
    """Shared loader trait for SOTA adapters (Wave 103 P2-A).

    Loads a checkpoint from ``weights_path`` and returns a model
    instance via the canonical ``builder`` callable. If ``compat_shim``
    is provided it is invoked BEFORE ``torch.load`` so adapters can
    install pickle-safe-globals shims (e.g. LineageFlow's
    ``_install_checkpoint_compat``).

    On any exception raised by ``builder``:
    - if ``stub_factory`` is ``None`` (default), surface as
      :class:`CapabilityMissingError` with ``upstream_label`` and the
      original exception's repr (``context=``).
    - if ``stub_factory`` is provided, return ``stub_factory()``.

    Directory-shaped weights (HiDream-I1 diffusers pipeline layout)
    are detected via :func:`Path.is_file` — ``torch.load`` is skipped
    for directories because it would raise ``IsADirectoryError`` on
    Linux. The builder is then responsible for its own per-component
    loading.

    Module-private (``_`` prefix): not exported via ``__all__``.

    Stdlib + numpy only at module level. ``torch`` is imported lazily so
    the framework does not require it at import time. ``CapabilityMissingError``
    is imported lazily from :mod:`adaptive_reflow.universal.adapter`
    because that module pulls in protocol surfaces the adapter-common
    module does not otherwise depend on.
    """
    import torch  # noqa: PLC0415 — lazy: torch is optional at the framework layer.

    if compat_shim is not None:
        compat_shim()

    weights_path_p = Path(weights_path)
    # torch.load is only meaningful for file-shaped checkpoints (kanzi
    # .pt, lineageflow .ckpt). Directory-shaped weights (hidream_i1
    # diffusers layout) must skip torch.load because the builder is
    # the one that knows how to load per-component sub-dirs.
    if weights_path_p.is_file():
        torch.load(
            str(weights_path_p),
            map_location=map_location,
            weights_only=False,
        )

    try:
        return builder(weights_path_p)
    except Exception as exc:
        if stub_factory is None:
            # Lazy import — keeps _adapter_common stdlib+numpy only at module level.
            from adaptive_reflow.universal.adapter import CapabilityMissingError  # noqa: PLC0415

            raise CapabilityMissingError(
                upstream_label,
                context=f"{type(exc).__name__}:{exc}",
            ) from exc
        return stub_factory()


# Wave 113.A.6 Phase 2: opt-out + shape-declaration class-level
# defaults. Adapters that do NOT want the construction-time shape
# guard flip ``_SKIP_CONSTRUCTION_SHAPE_GUARD = True`` on their
# class; each adapter that DOES want the guard declares its own
# ``_SHIM_INPUT_SHAPE`` as a tuple of ints on the class (the helper
# reads ``type(adapter)._SHIM_INPUT_SHAPE`` when ``shim_input_shape``
# is omitted, and uses the explicit argument otherwise).
_SKIP_CONSTRUCTION_SHAPE_GUARD: bool = False
_SHIM_INPUT_SHAPE: tuple[int, ...] | None = None


def _run_construction_shape_guard(
    adapter: Any,
    shim_input_shape: tuple[int, ...],
    time_scalar: float = 0.5,
) -> None:
    """Wave 113.A.6 Phase 2: shared N=1 forward-shape assert.

    Industry standard (Diffusers Triton strict-config, BentoML
    input_spec): catch a wrong-shape or all-zeros shim BEFORE the
    sweep runs N=1000 cells. Mirrors the 8 inline Wave 113.A.5 Fix 0
    copies exactly: same skip-guards, same shape-vs-expected compare,
    same ``abs().max() <= 0.0`` all-zeros check, same
    RuntimeError-only re-raise vs. RuntimeError-wrapping for any
    other exception.

    Skip-guards (returns ``None`` silently):
    - ``torch`` is not importable,
    - ``adapter._mode != "torch"``,
    - ``adapter._real_ckpt_path`` is ``None``,
    - ``adapter._weights_path`` is ``None`` or
      ``str(adapter._weights_path) == "synthetic"``,
    - the weights path does not exist on disk.

    When the guards pass, builds ``x = torch.randn(1, *shim_input_shape,
    device=adapter._device)`` and ``t = torch.tensor([time_scalar],
    device=adapter._device)``. If ``type(adapter)`` declares a
    ``_FAMILY_DIM`` class attribute (Kanzi: ``1152``), passes
    ``family=torch.zeros(1, _FAMILY_DIM, device=...)`` to the shim.
    Then calls ``adapter._model(x, t, family=...)`` under
    ``torch.no_grad()`` and asserts:

    1. ``tuple(v.shape) == tuple(x.shape)`` — otherwise RuntimeError
       naming the adapter class + expected + actual shape.
    2. ``float(v.abs().max()) > 0.0`` — otherwise RuntimeError
       naming the adapter class and ``"all-zeros velocity"``.

    RuntimeError fires re-raise directly; any other exception is
    wrapped as ``RuntimeError(repr(exc))`` so the failure mode is
    uniform across the 8 call sites. ``torch`` is imported lazily so
    the helper does not introduce a torch dependency at module
    import time (the module's contract is stdlib + numpy only at
    module level).

    Module-private (``_`` prefix): not exported via ``__all__``.
    """
    # Wave 113.A.6 Phase 3 fix — check torch availability BEFORE the
    # ``import torch`` so synthetic-mode test paths that construct
    # adapters on a torch-less interpreter don't crash with
    # ``ModuleNotFoundError``. ``torch_is_available()`` returns False
    # on any import failure, so this is a safe no-op gate.
    if not torch_is_available():
        return None
    import torch  # noqa: PLC0415 — lazy; module contract is numpy-only.

    weights_path = getattr(adapter, "_weights_path", None)
    if (
        not torch_is_available()
        or getattr(adapter, "_mode", None) != "torch"
        or getattr(adapter, "_real_ckpt_path", None) is None
        or weights_path is None
        or str(weights_path) == "synthetic"
        or not Path(weights_path).exists()
    ):
        return None

    class_name = type(adapter).__name__
    device = getattr(adapter, "_device", None)
    try:
        x = torch.randn(1, *shim_input_shape, device=device)
        t = torch.tensor([time_scalar], device=device)
        call_kwargs: dict[str, Any] = {}
        family_dim = getattr(type(adapter), "_FAMILY_DIM", None)
        if family_dim is not None:
            call_kwargs["family"] = torch.zeros(1, int(family_dim), device=device)
        model = getattr(adapter, "_model", None)
        if model is None:
            return None
        with torch.no_grad():
            v = model(x, t, **call_kwargs)
        if tuple(v.shape) != tuple(x.shape):
            raise RuntimeError(
                "Wave 113.A.6: "
                + class_name
                + " shim returned shape "
                + str(tuple(v.shape))
                + " but contract is "
                + str(tuple(x.shape))
                + "; shim likely broken. "
                + "See docs/audit/wave113-final-synthesis.md"
            )
        if float(v.abs().max()) <= 0.0:
            raise RuntimeError(
                "Wave 113.A.6: "
                + class_name
                + " shim returned all-zeros velocity "
                + "— stub or broken forward. "
                + "See docs/audit/wave113-final-synthesis.md"
            )
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001 — fail-closed gate
        raise RuntimeError(repr(exc)) from exc
    return None


def _resolve_mode(
    force_mode: str,
    weights_path: Path,
    *,
    weights_missing_err: str,
    ckpt_exists: bool | None = None,
    torch_available: bool | None = None,
) -> Literal["torch", "synthetic"]:
    """Map ``force_mode`` + environment onto ``"torch"`` / ``"synthetic"``.

    Wave 103 P1-B: this body is the byte-identical extraction of the
    ``if force_mode == "auto": ... elif ...`` ladder that was typed
    verbatim in kanzi / lineageflow / hidream_i1. Same branch order, same
    exception classes, same message strings — only the per-family
    ``weights_missing_err`` sentinel differs.

    ``ckpt_exists`` / ``torch_available`` default to
    ``weights_path.exists()`` / :func:`torch_is_available` and exist so
    callers with a cheaper probe can pass it in.

    Module-private (``_`` prefix): not exported via ``__all__``.
    """
    exists = weights_path.exists() if ckpt_exists is None else bool(ckpt_exists)
    has_torch = (
        torch_is_available() if torch_available is None else bool(torch_available)
    )
    if force_mode == "auto":
        return "torch" if (exists and has_torch) else "synthetic"
    if force_mode == "torch":
        if not has_torch:
            raise RuntimeError("torch requested but not installed")
        if not exists:
            raise FileNotFoundError(f"{weights_missing_err}:{weights_path}")
        return "torch"
    if force_mode == "synthetic":
        return "synthetic"
    raise ValueError(f"unknown_force_mode:{force_mode}")


__all__ = [
    "NativeStateCache",
    "coerce_nfe_budget",
    "digest_state",
    "kaiming_uniform",
    "low_nfe_restart_gate",
    "make_adapter_capabilities",
    "make_ref",
    "memory_fraction_for",
    "per_position_entropy_reduction",
    "seed_from_ids",
    "torch_is_available",
]