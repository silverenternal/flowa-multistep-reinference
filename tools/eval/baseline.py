"""Baseline cold-restart arm (single-pass ODE solve).

OWNER: Wave 97 Agent B — tools/eval/ subpackage split (single responsibility:
baseline arm + paper-quantity-snapshot materialisation that BOTH the
baseline and framework arms consume for byte-stable Wave 86 / Wave 45
paper-quantity-driven scheduling).

Public surface (byte-stable against ``tools/run_real_ckpt_eval.py`` pre-split):

* :func:`_build_initial_state_and_condition` — build the per-cell
  ``StateBundle`` + ``ODEConditionDelta``.
* :func:`_solve_baseline` — single-pass ODE solve with the paper-default NFE.
* :func:`_parse_g_profile_source` — compile a textual ``g(x)`` expression.
* :func:`_compute_paper_quantities_for_model` — materialise a real
  ``PaperQuantitiesSnapshot`` for ``model``.

The framework arm (in ``eval.framework``) imports ``_build_initial_state_and_condition``
+ ``_compute_paper_quantities_for_model`` from here.
"""
from __future__ import annotations

import time
from typing import Any

# Wave 53 Agent C: per-model force_mode token translation table.
# Default identity: CLI token = adapter token. Legacy adapters that
## ship pre-Wave-50 use ``"torch"`` to mean "real ckpt loaded" and
# receive a per-model entry here. New adapters (flowmol3 v1 + v2)
# use the CLI-native ``"real"`` token directly and need no entry.
# If a future adapter author adds a new force_mode token, they
# extend this table; see docs/audit/wave53-eval-pipeline-wiring-review.md §3.
_ADAPTER_FORCE_MODE_ALIAS: dict[str, dict[str, str]] = {
    "kanzi": {"real": "torch"},
    "lineageflow": {"real": "torch"},
    "freqflow": {"real": "torch"},
    "hidream_i1": {"real": "torch"},
    "rectified_flow_cifar": {"real": "torch"},
    "graphbfn": {"real": "torch"},
    "self_flow": {"real": "torch"},
    # flowmol3 + flowmol3_v2 are identity — no entry needed.
}


def _build_initial_state_and_condition(
    adapter: Any, *, seed: int, nfe: int, batch_id: str = "eval", sample_id: str = "s0"
) -> tuple[Any, Any]:
    """Build the initial state + condition delta for one cell.

    Returns ``(bundle, condition_delta)``. Uses the adapter's
    ``build_initial_state`` for the StateBundle and constructs a
    minimal ``ODEConditionDelta`` carrying the per-cell NFE budget.
    The ``ODEConditionDelta`` requires 4 fields per
    ``adaptive_reflow/universal/state.py:157``: ``delta_spec``,
    ``source``, ``target_round``, ``calibration_artifact_hash``.
    """
    from adaptive_reflow.universal.state import ODEConditionDelta  # type: ignore

    bundle = adapter.build_initial_state(batch_id=batch_id, sample_id=sample_id)
    condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe), "sampler_id": "euler"},
        source="run_real_ckpt_eval",
        target_round=0,
        calibration_artifact_hash="run_real_ckpt_eval:default",
    )
    return bundle, condition


def _solve_baseline(adapter: Any, *, nfe: int, seed: int, n_molecules: int = 1) -> tuple[Any, float]:
    """Baseline single-pass ODE solve with the paper-default NFE.

    Returns (trace, wallclock_seconds). No framework glue: just the
    adapter's ``solve_ode`` invocation.

    ``n_molecules`` (Wave 74 F1) — when > 1, the adapter's
    :meth:`solve_ode` call generates ``n_molecules`` independent
    trajectories per cell. Currently only consumed by the FlowMol3
    v2 adapter; other adapters ignore the kwarg.
    """
    bundle, condition = _build_initial_state_and_condition(
        adapter, seed=seed, nfe=nfe
    )
    t0 = time.monotonic()
    try:
        trace = adapter.solve_ode(
            bundle, condition, seed=int(seed), n_molecules=int(n_molecules),
        )
    except TypeError:
        # Backward-compat: legacy adapters do not accept the
        # ``n_molecules`` kwarg.
        trace = adapter.solve_ode(bundle, condition, seed=int(seed))
    wall = time.monotonic() - t0
    return trace, wall


# ---------------------------------------------------------------------------
# Per-model cell runners (real-ckpt forward pass; fail-closed on error)
# ---------------------------------------------------------------------------


#: Per-model default ``g : R -> R`` profiles for the paper-quantity
#: snapshot. These are the *F-side* profiles that
#: :class:`PaperQuantitiesSnapshot.for_profile` consumes to materialise
#: the four paper quantities ``(A_g, B_g, C_g, e_rho)``. The profiles
#: are stdlib-only (``math.sin`` / ``math.cos``), byte-stable across
#: (model, profile_source) and yield non-trivial ``A_g < 1`` so the
#: paper-quantity-aware scheduler / blender has a real signal to work
#: with. Pre-Wave-45 the eval tool hardcoded ``paper_quantities=None``
#: at every adapter call site, so the framework's paper-quantity-
#: driven scheduler had no signal at all (F-3 finding in
#: ``docs/audit/wave45-local-review.md``).
_PAPER_QUANTITY_PROFILES: dict[str, str] = {
    # Kanzi: protein-flow autoencoder, latent. Non-trivial profile
    # captures the non-monotonic sheet evidence that drives the
    # codimension-1 sheet integral.
    "kanzi": "0.5 * math.sin(x)",
    # LineageFlow: per-position categorical flow. Same profile
    # convention; the framework's per-position entropy headroom
    # surfaces differently than Kanzi's continuous latent but the
    # paper-quantity surface is identical.
    "lineageflow": "0.5 * math.sin(x)",
}

#: Module-level cache of ``(model, profile_source) -> PaperQuantitiesSnapshot``
#: so repeated (model, seed, nfe) cells don't re-pay the ~1 ms cost
#: of materialising the four paper quantities. Cache key uses the
#: textual profile source for transparency — switching the profile
# in ``_PAPER_QUANTITY_PROFILES`` invalidates the cache automatically.
_PAPER_QUANTITIES_CACHE: dict[str, Any] = {}


def _parse_g_profile_source(source: str) -> Any:
    """Compile a textual ``g(x)`` expression into a pure-Python callable.

    Mirrors :func:`tools.run_synthetic_image_eval.parse_g_profile_source`
    (stdlib-only, ast-parsed, restricted to ``math`` symbols + ``x``).
    Reimplemented locally so this tool does not gain a hard import
    edge on ``tools/run_synthetic_image_eval`` (which in turn imports
    a torch stack).
    """
    import ast as _ast
    import math as _math

    _allowed_math_names = set(dir(_math))
    try:
        tree = _ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"g profile source not parseable: {exc}") from exc
    compiled = compile(tree, filename="<g_profile>", mode="eval")

    def _callable(x: float) -> float:
        return float(
            eval(  # noqa: S307 — restricted scope below
                compiled,
                {"__builtins__": {}},
                {"math": _math, "x": float(x)},
            )
        )

    return _callable


def _compute_paper_quantities_for_model(
    model: str,
    *,
    seed: int,
    nfe: int,
) -> tuple[Any, dict[str, Any]]:
    """Materialise a real :class:`PaperQuantitiesSnapshot` for ``model``.

    Returns ``(snapshot_or_None, debug_dict)``. The snapshot is the
    frozen carrier of the four paper quantities ``(A_g, B_g, C_g,
    e_rho)`` consumed by the framework's paper-quantity-driven
    scheduler. The debug dict always carries a
    ``paper_quantities_status`` field (``"computed"``,
    ``"degraded_to_none"``, or ``"blocked"``) so the eval JSON can
    surface whether the thread succeeded per cell.

    The materialisation is:

    1. Look up the per-model default profile ``g`` from
       :data:`_PAPER_QUANTITY_PROFILES`.
    2. Compile the profile to a pure-Python callable.
    3. Call :meth:`PaperQuantitiesSnapshot.for_profile` with the
       default paper knobs (matches :data:`fid_theorem_aligned`
       default constants).
    4. Return the snapshot + a debug dict with the four paper
       quantities, the profile source, the (model, seed, nfe) cell
       key, and the cache key.

    Failure modes (any return ``(None, debug)`` with a non-``computed``
    status):

    * ``adaptive_reflow.eval.fid_theorem_aligned.PaperQuantitiesSnapshot``
      not importable (CPU-only / synthetic-only env) → status
      ``"degraded_to_none"``.
    * Profile compilation failure → status ``"degraded_to_none"``
      with the syntax error captured.
    * Any other exception during materialisation → status
      ``"degraded_to_none"`` with the exception captured.
    """
    debug: dict[str, Any] = {
        "model": str(model),
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    profile_source = _PAPER_QUANTITY_PROFILES.get(model)
    if profile_source is None:
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"no _PAPER_QUANTITY_PROFILES entry for model={model!r}"
        )
        return None, debug

    cache_key = f"{model}|{profile_source}"
    if cache_key in _PAPER_QUANTITIES_CACHE:
        snap = _PAPER_QUANTITIES_CACHE[cache_key]
        debug["paper_quantities_status"] = "computed"
        debug["paper_quantities_cache_hit"] = True
        debug["paper_quantities_cache_key"] = cache_key
        debug["paper_quantities_profile_source"] = profile_source
        debug["paper_quantities_values"] = {
            "A_g": float(snap.A_g),
            "B_g": float(snap.B_g),
            "C_g": float(snap.C_g),
            "e_rho": float(snap.e_rho),
            "rho": float(snap.rho),
            "c": float(snap.c),
            "eta": float(snap.eta),
            "K": float(snap.K),
            "h": float(snap.h),
        }
        return snap, debug

    try:
        from adaptive_reflow.eval.fid_theorem_aligned import (  # type: ignore
            PaperQuantitiesSnapshot as _PaperQuantitiesSnapshot,
        )
    except Exception as exc:  # noqa: BLE001
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"import failed: {type(exc).__name__}:{exc}"
        )
        return None, debug

    try:
        g_callable = _parse_g_profile_source(profile_source)
    except Exception as exc:  # noqa: BLE001
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"profile compile failed: {type(exc).__name__}:{exc}"
        )
        return None, debug

    try:
        snap = _PaperQuantitiesSnapshot.for_profile(g_callable)
    except Exception as exc:  # noqa: BLE001
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"for_profile raised: {type(exc).__name__}:{exc}"
        )
        return None, debug

    _PAPER_QUANTITIES_CACHE[cache_key] = snap
    debug["paper_quantities_status"] = "computed"
    debug["paper_quantities_cache_hit"] = False
    debug["paper_quantities_cache_key"] = cache_key
    debug["paper_quantities_profile_source"] = profile_source
    debug["paper_quantities_values"] = {
        "A_g": float(snap.A_g),
        "B_g": float(snap.B_g),
        "C_g": float(snap.C_g),
        "e_rho": float(snap.e_rho),
        "rho": float(snap.rho),
        "c": float(snap.c),
        "eta": float(snap.eta),
        "K": float(snap.K),
        "h": float(snap.h),
    }
    return snap, debug


__all__ = [
    "_ADAPTER_FORCE_MODE_ALIAS",
    "_PAPER_QUANTITIES_CACHE",
    "_PAPER_QUANTITY_PROFILES",
    "_build_initial_state_and_condition",
    "_compute_paper_quantities_for_model",
    "_parse_g_profile_source",
    "_solve_baseline",
]
