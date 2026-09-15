"""Framework arm (multi-round + restart-blend + paper-quantity-driven β).

OWNER: Wave 97 Agent B — tools/eval/ subpackage split (single responsibility:
framework multi-round ODE solve + per-round policy construction + adapter
factory dispatch with the per-model ``force_mode`` token translation table).

This module is byte-stable against `tools/run_real_ckpt_eval.py` pre-split.
Every exported symbol + every public function (resolve, solve, policy,
compute_paper_quantities) matches the pre-Wave-97 contract.

Public surface:

* :data:`_ADAPTER_FORCE_MODE_ALIAS` — also re-exported by ``eval.baseline`` for
  the legacy test surface (the test file imports it from
  ``tools.run_real_ckpt_eval``).
* :func:`_resolve_adapter` — adapter factory dispatch (Wave 50 / 53 / 66 / 73
  / 95 changes all in here).
* :func:`_compute_paper_quantities` — Wave 86 Agent B paper-quantity helper.
* :func:`_make_framework_policy` — Wave 45 + Wave 86 per-round policy build.
* :func:`_solve_framework` — multi-round solve + Wave 64 / Wave 86 byte-stable
  trace re-anchor.
"""
from __future__ import annotations

import inspect
import time
from typing import Any

from tools.eval.baseline import (  # type: ignore
    _ADAPTER_FORCE_MODE_ALIAS,
    _build_initial_state_and_condition,
)
from tools.eval.io import DOWNSTREAM_METRICS, FLOWMOL3_REAL_CKPT  # type: ignore

# Wave 53 Agent C: per-model force_mode token translation table.
# Default identity: CLI token = adapter token. Legacy adapters that
# ship pre-Wave-50 use ``"torch"`` to mean "real ckpt loaded" and
# receive a per-model entry here. New adapters (flowmol3 v1 + v2)
# use the CLI-native ``"real"`` token directly and need no entry.
# Re-exported from ``eval.baseline`` so legacy
# ``tools.run_real_ckpt_eval._ADAPTER_FORCE_MODE_ALIAS`` imports keep working.
__all_force_mode_alias = _ADAPTER_FORCE_MODE_ALIAS


def _resolve_adapter(
    model: str,
    force_mode: str = "synthetic",
    restart_min_nfe: int | None = None,
    nfe_budget: int | None = None,
) -> tuple[Any, str]:
    """Resolve the adapter factory for ``model``.

    ``force_mode`` selects the adapter operating mode:

    * ``"synthetic"`` — always use the synthetic-shim path (default,
      zero-dependency, deterministic). Works without GPU or upstream
      packages.
    * ``"real"`` — load real checkpoint weights. Requires the upstream
      package (e.g. ``kanzi``) to be installed in the active interpreter
      and the checkpoint file to exist on disk; both fail loudly.
    * ``"auto"`` — try real ckpt first, fall back to synthetic on
      ``ImportError`` / missing weights (so the same script works in
      both the framework pytest env and the sidecar venv).

    The CLI value ``"real"`` is translated to the adapter's native
    ``"torch"`` token via the per-model :data:`_ADAPTER_FORCE_MODE_ALIAS`
    table (Wave 53 Agent C — closes the Wave 50 Agent B Phase-4
    flowmol3 block). Returns ``(adapter_instance, mode_string)``.
    When the model is BLOCKED (no shipped adapter), returns
    ``(None, "BLOCKED")``.

    ``restart_min_nfe`` and ``nfe_budget`` (Wave 61 Agent 1) are
    forwarded to the adapter factory only when the factory signature
    accepts them. The FlowMol3 v1 factory ``default_flowmol3_adapter``
    is the only consumer as of Wave 58; the other 13 adapters do not
    take either kwarg, and ``inspect.signature`` filtering keeps
    this one-liner backward compatible with every other model.
    ``None`` means "do not pass" — the pre-Wave-61 behaviour. Both
    are required for the NFE-adaptive restart gate to actually
    fire: ``restart_min_nfe`` is the threshold, ``nfe_budget`` is
    the *effective* NFE that the gate compares against it.

    ``weights_path`` (Wave 73 Agent 3 — GAP-4) is threaded from
    :data:`FLOWMOL3_REAL_CKPT` for the ``flowmol3`` / ``flowmol3_v2``
    models when ``force_mode in {"real", "auto"}``, the factory accepts
    the kwarg, and the ckpt exists on disk. Without it the v2 factory
    defaults to ``weights_path=None`` and ``_load_model()`` returns
    ``kind=synthetic`` — no real upstream forward, no SMILES cache,
    chemistry composite pinned to 0
    (docs/audit/wave71-phase3-sweep.md §4).
    """
    spec = DOWNSTREAM_METRICS[model]
    factory_path = spec["adapter_factory"]
    if factory_path is None:
        return None, "BLOCKED"
    # Wave 66 Agent 1 — wire v2 FlowMol3 adapter for real integration.
    # The registry entry for ``flowmol3`` (v1) routes to the hash-based
    # placeholder (``default_flowmol3_adapter``) which does NOT actually
    # integrate the real FlowMol3 ckpt; the v2 adapter
    # (``default_flowmol3adapter`` at
    # ``adaptive_reflow.adapters.flowmol3_v2_adapter``) does. Switch
    # the factory path to v2 when ``force_mode`` is real/auto so the
    # real model integrates and the per-atom entropy surface is real
    # (not the Wave 53 placeholder uniform-vs-uniform reading).
    if (
        model == "flowmol3"
        and factory_path.endswith(":default_flowmol3_adapter")
        and force_mode in {"real", "auto"}
    ):
        factory_path = (
            "adaptive_reflow.adapters.flowmol3_v2_adapter:default_flowmol3adapter"
        )
    module_path, attr = factory_path.rsplit(":", 1)
    # Wave 53 Agent C: per-model force-mode token translation.
    # Legacy adapters (kanzi, lineageflow, freqflow, hidream, lumina,
    # rectified_flow_cifar, graphbfn, self_flow, wan2_2_video,
    # protbfn_abbfn) accept ``"torch"`` to mean "real checkpoint
    # loaded". The flowmol3 v1 factory (Wave 50 Agent A) and the
    # flowmol3_v2 factory (Wave 50 / Wave 53 Agent B fix) accept the
    # CLI-native ``"real"`` token. The mapping table lives next to
    # :data:`DOWNSTREAM_METRICS` so future adapter authors see both
    # surfaces in one place.
    adapter_force_mode = _ADAPTER_FORCE_MODE_ALIAS.get(
        model, {},
    ).get(force_mode, force_mode)
    try:
        import importlib

        mod = importlib.import_module(module_path)
        factory = getattr(mod, attr)
        kwargs: dict[str, Any] = {"force_mode": adapter_force_mode}
        # Wave 61 Agent 1: thread the NFE-adaptive restart gate inputs
        # into the factory only when the factory signature accepts
        # them. Other adapter factories (kanzi, lineageflow, freqflow,
        # etc.) do not take either kwarg; this branch keeps them
        # byte-identical to the pre-Wave-61 call shape.
        sig_params = inspect.signature(factory).parameters
        if restart_min_nfe is not None and "restart_min_nfe" in sig_params:
            kwargs["restart_min_nfe"] = int(restart_min_nfe)
        if nfe_budget is not None and "nfe_budget" in sig_params:
            kwargs["nfe_budget"] = int(nfe_budget)
        # Wave 73 Agent 3 — close GAP-4 (docs/audit/wave71-phase3-sweep.md §4).
        # The v2 FlowMol3 factory sets ``use_upstream=True`` for
        # real/auto (Wave 71 GAP-1) but defaults ``weights_path=None``,
        # so ``_load_model()`` returns ``kind=synthetic``: no real
        # upstream forward, no SMILES cache, chemistry composite = 0.
        # Thread the published ckpt path when it exists on disk. Scoped
        # to the two flowmol3 model tokens + real/auto so every other
        # model (and ``force_mode='synthetic'``) keeps the byte-stable
        # pre-Wave-73 call shape.
        if (
            model in {"flowmol3", "flowmol3_v2"}
            and force_mode in {"real", "auto"}
            and "weights_path" in sig_params
            and FLOWMOL3_REAL_CKPT.is_file()
        ):
            kwargs["weights_path"] = str(FLOWMOL3_REAL_CKPT)
        # Wave 95 Phase 1.D — symmetrically thread ``weights_path`` into
        # the kanzi / lineageflow / hidream_i1 SOTA factories so the
        # per-cell framework-vs-baseline eval can exercise real
        # checkpoints instead of the synthetic field. Each entry is
        # gated by ``weights_path in sig_params`` (mirror line 977) so
        # pre-existing factories whose signature does NOT accept the
        # kwarg keep their byte-stable call shape. The kanzi /
        # lineageflow resolvers take no arguments; hidream_i1 needs the
        # ``variant`` token to match the published HF sub-repo names.
        if (
            model == "kanzi"
            and force_mode in {"real", "auto"}
            and "weights_path" in sig_params
        ):
            from adaptive_reflow.adapters import kanzi_resolve_weights_path

            kanzi_ckpt = kanzi_resolve_weights_path()
            if kanzi_ckpt is not None:
                kwargs["weights_path"] = str(kanzi_ckpt)
        if (
            model == "lineageflow"
            and force_mode in {"real", "auto"}
            and "weights_path" in sig_params
        ):
            from adaptive_reflow.adapters import lineageflow_resolve_weights_path

            lineageflow_ckpt = lineageflow_resolve_weights_path()
            if lineageflow_ckpt is not None:
                kwargs["weights_path"] = str(lineageflow_ckpt)
        if (
            model == "hidream_i1"
            and force_mode in {"real", "auto"}
            and "weights_path" in sig_params
        ):
            from adaptive_reflow.adapters import hidream_i1_resolve_weights_path

            hidream_ckpt = hidream_i1_resolve_weights_path("full")
            if hidream_ckpt is not None:
                kwargs["weights_path"] = str(hidream_ckpt)
        adapter = factory(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return None, f"IMPORT_FAILED:{type(exc).__name__}:{exc}"
    return adapter, adapter_force_mode


def _compute_paper_quantities(
    adapter: Any,
    trace: Any,
    *,
    round_index: int,
) -> dict[str, float] | None:
    """Derive the per-round paper quantities dict from the just-completed trace.

    Wave 86 Agent B — Pitfall #1 fix companion to
    :func:`_make_framework_policy`. When the adapter exposes a
    ``profile_residual_fn`` (either via :meth:`capabilities` or as a
    direct attribute), compute the three paper-quantity primitives
    the :class:`PaperRatioAdaptiveScheduler` consumes:

        ``{"sheet_A": float, "packing_B": float,
           "exterior_gap": float}``

    Returns ``None`` when no ``profile_residual_fn`` is exposed (the
    legacy constant-β path is then preserved **byte-identically**).
    Defensive: any exception in the paper-quantity oracle falls back
    to ``None`` so a broken oracle can NEVER poison the framework arm.

    Parameters
    ----------
    adapter
        The adapter whose profile residual we consult. May or may not
        expose ``profile_residual_fn``; the helper is the single
        canonical place where this lookup happens.
    trace
        The :class:`ODEIntegratorTrace` returned by the most recent
        :meth:`solve_ode` call. Carried for symmetry with future
        per-trace paper-quantity derivations; the current helper does
        NOT consume it (the paper quantities come from the
        adapter-level ``profile_residual_fn``).
    round_index
        Zero-based index of the round that just finished. Currently
        informational; future revisions may condition the EMA
        smoothing on round parity.
    """
    # Look up the profile-residual-fn via two defensive paths.
    profile_residual_fn: Any = None
    try:
        caps = adapter.capabilities() if hasattr(adapter, "capabilities") else None
    except Exception:
        caps = None
    if caps is not None:
        profile_residual_fn = getattr(caps, "profile_residual_fn", None)
    if profile_residual_fn is None:
        profile_residual_fn = getattr(adapter, "profile_residual_fn", None)
    if profile_residual_fn is None:
        return None
    if not callable(profile_residual_fn):
        return None
    try:
        from adaptive_reflow.contracts import paper_quantities as _pq  # type: ignore
    except Exception:
        return None
    try:
        sheet_A = float(_pq.sheet_evidence_A(profile_residual_fn))
    except Exception:
        return None
    try:
        packing_B = float(_pq.root_cell_packing_B(profile_residual_fn))
    except Exception:
        return None
    try:
        exterior_gap = float(_pq.exterior_gap_e_rho())
    except Exception:
        return None
    if (
        sheet_A != sheet_A  # NaN guard
        or packing_B != packing_B
        or exterior_gap != exterior_gap
    ):
        return None
    return {
        "sheet_A": float(sheet_A),
        "packing_B": float(packing_B),
        "exterior_gap": float(exterior_gap),
    }


def _make_framework_policy(
    adapter: Any,
    *,
    target_round: int,
    seed: int,
    paper_quantities: dict[str, float] | None = None,
) -> Any:
    """Build a fresh ``FinalRestartPolicy`` for one framework round.

    The policy's ``beta_by_channel`` covers every channel declared in
    ``adapter.capabilities().channel_domains`` (NOT a hard-coded list
    per model) so this works for kanzi, lineageflow, freqflow, and any
    future adapter that ships a per-channel `` `` declaration. Per
    ``docs/audit/wave45-local-review.md`` §F-2, the previous version
    passed ``policy=None`` and the bare ``except`` swallowed the
    resulting `` so the framework arm silently fell
    back to baseline. Building a real policy restores the multi-round
    restart-blend signal that Wave 31 / Wave 34 paper-quantity-aware
    schedulers were meant to drive.

    Wave 86 Agent B — Pitfall #1 fix: when ``paper_quantities`` is
    supplied, the per-round β is driven by the Wave 31
    :class:`PaperRatioAdaptiveScheduler` (paper Lemma 2 / Lemma 3 /
    Lemma 5 ground truth). When ``paper_quantities`` is ``None``
    (legacy adapter without ``profile_residual_fn``), the
    constant-0.5 fallback is preserved **byte-identically** to the
    pre-Wave-86 contract. The two paths share the same
    :class:`FinalRestartPolicy` constructor so the only
    output-byte-impacting change is the ``beta_by_channel`` payload.

    Sign convention
    ---------------

    The :class:`PaperRatioAdaptiveScheduler` exposes ``n_cap`` (the
    fresh-noise capacity). The framework's restart-blend convention
    is ``memory_fraction = 1 - β`` and ``β = 1 - n_cap`` — so a
    high paper-ratio (sheet-dominant, low codimension) → high β →
    more fresh noise → more exploration, and a low paper-ratio
    (cell-dominant, high codimension) → low β → more memory →
    exploitation. This matches the Wave 45 restart-blend convention
    that the framework-side metric layer already keys off.
    """
    from dataclasses import replace as _dc_replace

    from adaptive_reflow.contracts import (  # type: ignore
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        MechanismId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    caps = adapter.capabilities() if hasattr(adapter, "capabilities") else None
    if caps is not None and getattr(caps, "channel_domains", None):
        # ``ChannelName`` is a ``typing.NewType`` (not a class) so
        # ``isinstance(ch, ChannelName)`` raises TypeError. Filter via
        # ``isinstance(ch, str)`` (NewType is str at runtime) and cast
        # back into a ``ChannelName`` for the policy payload. Sort the
        # channel list so the policy_hash is deterministic across
        # adapters with the same channel set.
        channel_names = sorted(
            ChannelName(ch)
            for ch in caps.channel_domains
            if isinstance(ch, str)
        ) or [ChannelName("latent")]
    else:
        # Fallback when the adapter does not declare capabilities
        # (e.g. a non-flow adapter). Single anonymous channel is enough
        # for the contract hash.
        channel_names = [ChannelName("latent")]

    if paper_quantities is not None:
        # ---- Pitfall #1 fix: paper-quantity-driven per-round β --------
        # Build a fresh :class:`PaperRatioAdaptiveScheduler` per call
        # (the scheduler's EMA + PID shift are mutable state; sharing
        # across cells would couple unrelated framework passes). The
        # cycle_length is anchored to a fixed canonical length of 20
        # (the Wave 34 default) so the per-round n_cap varies
        # naturally across rounds under the codimension-sheet
        # scheduler's coarse-to-fine convention. A short cycle_length
        # would collapse every round to the same n_cap value (the
        # scheduler's cosine / sheet ratio saturates), masking the
        # paper-quantity PID shift.
        from adaptive_reflow.algorithm.scheduler import (  # type: ignore
            CodimensionSheetScheduler,
            PaperRatioAdaptiveScheduler,
        )
        scheduler = PaperRatioAdaptiveScheduler(
            base=CodimensionSheetScheduler(
                cycle_length=20,
                n_min=0.0,
                n_max=1.0,
                eps_implicit=0.05,
                eps_direction="decreasing",
                seed=int(seed),
            ),
        )
        # Push the per-round paper quantities into the EMA, then sample
        # the per-round capacity. For round 0 (no prior history) the
        # PID shift is zero and ``n_cap = n_cap_base(r=0)`` — the
        # framework's coarse-to-fine base schedule — so β_round0 ≠ 1.0
        # even on the first round. From the second round onwards the
        # PID shift accumulates a per-paper-quantity correction.
        scheduler.record_round_feedback(
            round_in_cycle=int(target_round),
            paper_quantities=dict(paper_quantities),
        )
        sample = scheduler.sample(
            outer_cycle_id=0,
            round_in_cycle=int(target_round),
            target_round=int(target_round),
        )
        beta = float(1.0 - float(sample.n_cap))
    else:
        beta = 0.5  # legacy constant — preserved byte-identical for
                    # adapters that don't expose paper_quantities.
                    # Wave 45 / Wave 64 / Wave 82 hardcoded this value
                    # per round; the framework's scheduler drives the
                    # per-round β in production only via this entry
                    # point, so byte-stability of the legacy path is
                    # load-bearing for the D.4 vector suite.
    policy_id = PolicyId(
        f"run_real_ckpt_eval:framework:r{target_round}:s{seed}"
    )
    draft = FinalRestartPolicy(
        policy_id=policy_id,
        writer_id=MechanismId("inference.adaptive_reflow"),
        run_id=RunId("run_real_ckpt_eval:framework"),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ch: FactorValue(float(beta)) for ch in channel_names},
        alpha_by_channel={ch: FactorValue(1.0) for ch in channel_names},
        fresh_noise_floor_by_channel={
            ch: FactorValue(0.0) for ch in channel_names
        },
        schedule_sample=None,
        freeze_admission_by_channel={ch: True for ch in channel_names},
        ledger_row_id=LedgerRowId(f"ledger-run_real_ckpt_eval-r{target_round}"),
        policy_hash=ArtifactHash(""),
        created_at_round=int(target_round),
        beta_from_schedule=True,
    )
    return _dc_replace(draft, policy_hash=hash_policy_hash(draft))


def _solve_framework(adapter: Any, *, nfe: int, seed: int, n_rounds: int = 3, n_molecules: int = 1) -> tuple[Any, float]:
    """Framework multi-round ODE solve with the same total NFE budget.

    Splits the total NFE across ``n_rounds`` and chains the adapter's
    ``solve_ode`` + ``export_endpoint`` + ``apply_restart_distribution``
    in a paper-quantity-driven loop. Total The is matched to the
    baseline (so the per-cell delta isolates scheduler / restart-blend
    / paper-quantity value-add).

    F-2 fix (Wave 45 Agent B): the previous version called
    ``export_endpoint(trace)`` and
    ``apply_restart_distribution(bundle=..., trace=..., policy=None, ...)``
    — both signatures were wrong (export_endpoint wants a
    :class:`StateBundle`, not an :class:`ODEIntegratorTrace`;
    apply_restart_distribution wants ``(state, policy)`` not keyword
    arguments). The bare ``except`` swallowed both errors so the
    framework arm executed exactly ONE ``solve_ode`` and was
    byte-identical to baseline. This implementation:

    * passes ``cur_bundle`` to ``export_endpoint`` (identity
      pass-through — see ``kanzi.py:1108`` / ``lineageflow.py:989``);
    * builds a real per-round :class:`FinalRestartPolicy` (above) and
      passes it positionally to ``apply_restart_distribution``;
    * narrows both bare ``except`` blocks to the specific exception
      types we expect to handle (the framework's own
      :class:`CapabilityMissingError`); all other exceptions
      propagate so signature regressions fail closed rather than
      silently degrade to baseline.

    ``n_molecules`` (Wave 74 F1) — when > 1, threaded into the
    per-round :meth:`solve_ode` call so each round generates
    ``n_molecules`` independent trajectories. Currently only
    consumed by the FlowMol3 v2 adapter; others ignore it.
    """
    # NB: legacy tests monkey-patch ``tools._compute_paper_quantities``
    # and ``tools._make_framework_policy``. Look them up via the shim so
    # the patches take effect.
    import importlib as _il

    from adaptive_reflow.universal.state import ODEConditionDelta  # type: ignore
    _shim = _il.import_module("tools.run_real_ckpt_eval")
    _compute_paper_quantities = _shim._compute_paper_quantities
    _make_framework_policy = _shim._make_framework_policy

    bundle, _ = _build_initial_state_and_condition(adapter, seed=seed, nfe=nfe)
    # Wave 64 Agent 1 fix (Bug A.3): distribute the total NFE across
    # rounds so the per-round sum equals ``nfe`` exactly. The previous
    # ``round(nfe / n_rounds)`` formula gave 9 / 51 / 201 for
    # 10 / 50 / 200 — a 1-step excess in 2 of 3 cells. The new formula
    # puts the remainder in the LAST round so the per-round NFE list is
    # ``[base, base, ..., base+remainder]`` with sum equal to ``nfe``.
    n_rounds_int = max(1, int(n_rounds))
    base_per_round = max(1, int(nfe) // n_rounds_int)
    remainder_per_round = max(0, int(nfe) - base_per_round * n_rounds_int)
    nfe_per_round_list: list[int] = [base_per_round] * n_rounds_int
    if remainder_per_round > 0:
        nfe_per_round_list[-1] += remainder_per_round
    t0 = time.monotonic()
    cur_bundle = bundle
    trace: Any = None
    # Lazy imports to avoid the import cost on cold clone and to keep
    # the eval tool's import surface tight.
    from adaptive_reflow.universal.adapter import (  # type: ignore
        CapabilityMissingError,
    )

    for r in range(int(n_rounds)):
        per_round_nfe = int(nfe_per_round_list[r])
        condition = ODEConditionDelta(
            delta_spec={"num_steps": per_round_nfe, "sampler_id": "euler"},
            source="run_real_ckpt_eval",
            target_round=int(r),
            calibration_artifact_hash="run_real_ckpt_eval:default",
        )
        try:
            trace = adapter.solve_ode(
                cur_bundle, condition, seed=int(seed) + int(r),
                n_molecules=int(n_molecules),
            )
        except TypeError:
            # Backward-compat: legacy adapters do not accept the
            # ``n_molecules`` kwarg.
            trace = adapter.solve_ode(
                cur_bundle, condition, seed=int(seed) + int(r),
            )
        # Restart distribution step: blend the current round's bundle
        # (the prior round's endpoint, identity-passed through
        # ``export_endpoint``) with the per-round restart policy to
        # produce the next round's initial state.
        try:
            # F-2: was ``adapter.export_endpoint(trace)`` — AttributeError
            # because :class:`ODEIntegratorTrace` has no
            # ``native_state_digest`` accessor matching the
            # :class:`StateBundle` that ``export_endpoint`` expects.
            endpoint = adapter.export_endpoint(cur_bundle)
        except CapabilityMissingError:
            # Framework has no restart-blend surface for this adapter —
            # the honest reading is "framework degenerates to baseline".
            break
        if endpoint is None:
            break
        try:
            # F-2: was
            #   ``adapter.apply_restart_distribution(
            #       bundle=cur_bundle, trace=trace, policy=None,
            #       round_index=int(r))``
            # — TypeError because the Protocol expects
            # ``apply_restart_distribution(state, policy)``.
            # Wave 86 Agent B — Pitfall #1 fix: derive per-round
            # paper quantities from the just-completed trace's
            # adapter-level profile_residual_fn (when available)
            # and thread them into _make_framework_policy so the
            # per-round β is paper-quantity-driven, NOT the legacy
            # constant-0.5. When the adapter does not expose
            # profile_residual_fn (legacy adapters / cold clones),
            # the helper returns None and _make_framework_policy
            # takes the byte-identical constant-β path.
            pq = _compute_paper_quantities(
                adapter, trace, round_index=int(r),
            )
            policy = _make_framework_policy(
                adapter,
                target_round=int(r),
                seed=int(seed),
                paper_quantities=pq,
            )
            cur_bundle = adapter.apply_restart_distribution(endpoint, policy)
        except CapabilityMissingError:
            # Restart path unavailable; degenerate to baseline.
            break
    wall = time.monotonic() - t0
    # Wave 64 Agent 1 fix (Bug A.1 + Bug A.2 — root cause in
    # docs/audit/wave63-root-cause.md §2): the trace returned above is
    # from the LAST per-round solve_ode call, which carries
    # ``(seed=seed+r, steps=nfe_per_round)`` — a DIFFERENT (seed, steps)
    # axis than baseline's ``(seed=seed, steps=nfe)``. The metric layer
    # reads ``trace.native_state_digest`` and ``trace.steps`` to
    # dispatch its chemistry dict, so the framework arm differs from
    # baseline at the digest level EVEN when the restart-blend was a
    # no-op (m=0 at NFE=10 below the gate threshold).
    #
    # The contract between ``_solve_framework`` (returns last-round
    # trace) and ``_compute_metric`` (treats that trace as the
    # integrated endpoint) is the load-bearing mismatch. We re-anchor
    # the returned trace to the integrated endpoint by running a final
    # ``solve_ode`` with the TOTAL NFE budget on the framework's
    # integrated endpoint state, keyed on the ORIGINAL seed. The result
    # has the same ``(seed=seed, steps=nfe)`` axis as the baseline trace
    # so the metric layer compares framework vs baseline on the the
    # axis. When the gate fires (low NFE), the integrated endpoint
    # equals the original bundle, so the framework trace is
    # byte-identical to the baseline trace — which is the honest
    # reading for the gate-skipped path.
    final_condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe), "sampler_id": "euler"},
        source="run_real_ckpt_eval",
        target_round=int(n_rounds),
        calibration_artifact_hash="run_real_ckpt_eval:default",
    )
    integrated_trace = adapter.solve_ode(
        cur_bundle, final_condition, seed=int(seed)
    )
    return integrated_trace, wall


__all__ = [
    "_compute_paper_quantities",
    "_make_framework_policy",
    "_resolve_adapter",
    "_solve_framework",
]
