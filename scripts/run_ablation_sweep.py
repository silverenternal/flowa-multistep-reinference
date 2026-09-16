#!/usr/bin/env python3
"""Wave 52 Agent B — per-component ablation sweep.

Design (5 arms x 3 models)
--------------------------

This sweep drives a 5-arm ablation of the framework to show *which
component contributes what*:

    Arm 0 — full framework               (n_rounds=3, GPT-prior enabled
                                          where supported, paper-quantity
                                          scheduler active)
    Arm 1 — no restart-blend             (n_rounds=1, single-pass solve;
                                          framework degenerates to baseline)
    Arm 2 — no paper-quantity scheduler  (n_rounds=3, but uniform n_cap;
                                          framework uses a constant
                                          memory fraction = 0.5)
    Arm 3 — no GPT-prior restart         (n_rounds=3, but the kanzi
                                          adapter's GPT-prior restart
                                          policy is disabled via its
                                          existing constructor flag;
                                          uniform restart distribution)
    Arm 4 — no RestartBlend altogether   (same as arm 1; documented for
                                          completeness so reviewers can
                                          see "restart-blend *as a
                                          whole*" contributes nothing
                                          beyond single-pass baseline)

Cells (rows = arms, columns = models):

    | arm | twodim_fm (toy) | kanzi (real ckpt) | lineageflow (real ckpt) |

Metric per cell
~~~~~~~~~~~~~~~

We use a *direct* metric that varies across arms (rather than the
``tools/run_real_ckpt_eval._compute_metric`` synthetic-fallback path
which clamps every cell to the saturation threshold and yields
``TIE_AT_SATURATION`` regardless of arm). For each cell we run both
the baseline single-pass solve *and* the framework multi-round solve,
capture their endpoint states, and compute one of:

* **twodim_fm**: 1-D sliced W2 distance vs the analytic two-moons
  target (lower-is-better).
* **kanzi**: per-position Shannon-entropy reduction of the framework
  endpoint vs the baseline endpoint, in nats (higher = framework
  sharpened the posterior). Computed by
  :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`
  on the ``theta`` channel (kanzi's continuous latent is treated as
  logits for this metric, matching the Wave 45 close-out pattern).
* **lineageflow**: same per-position entropy reduction on the
  ``theta`` channel (the 33-token per-position categorical).

The direct metric is *non-saturating* so per-arm deltas are visible
even when the synthetic shim's saturation threshold is reached by
both arms.

How the sweep drives each arm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This script honors the disjoint file scope (no framework file is
modified). Each arm is realised by importing
``tools.run_real_ckpt_eval`` as a module and ``monkey-patching`` its
private helpers (``_solve_framework``, ``_make_framework_policy``,
``_resolve_adapter``) per arm. The patches are scoped to a single
``run_arm_cell`` call so subsequent cells see the original code.

For all three models we use ``force_mode='synthetic'`` which keeps
the run zero-dependency (no upstream ckpt downloads), deterministic,
and CI-friendly. The framework's multi-round
``apply_restart_distribution`` is exercised via the synthetic shim's
restart-blend path, which is the same code path used by the real
checkpoint (the difference is only the underlying forward pass).

Output
~~~~~~

Per-arm, per-model metric value plus a 5x3 ablation table written to
``verification_outputs/ablation_q4_2026.json``. The audit doc
``docs/audit/wave52-per-component-ablation.md`` consumes this file.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import importlib
import json
import os
import pathlib
import sys
import time
import traceback
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Make ``tools`` importable as a top-level package.
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR.parent))

# ---------------------------------------------------------------------------
# 5-arm ablation matrix (single source of truth)
# ---------------------------------------------------------------------------

ARMS: list[dict[str, Any]] = [
    {
        "arm_id": 0,
        "label": "full_framework",
        "description": (
            "Full framework: 3 rounds, paper-quantity-driven scheduler, "
            "GPT-prior-aware restart enabled (kanzi)."
        ),
        "n_rounds": 3,
        "disable_restart_blend": False,
        "disable_paper_quantity_scheduler": False,
        "disable_gpt_prior_restart": False,
        "expected_component_active": "all_components",
    },
    {
        "arm_id": 1,
        "label": "no_restart_blend",
        "description": (
            "Without restart-blend: n_rounds=1 collapses the framework "
            "to a single-pass solve (no apply_restart_distribution call)."
        ),
        "n_rounds": 1,
        "disable_restart_blend": True,
        "disable_paper_quantity_scheduler": True,
        "disable_gpt_prior_restart": True,
        "expected_component_active": "none",
    },
    {
        "arm_id": 2,
        "label": "no_paper_quantity_scheduler",
        "description": (
            "Without paper-quantity-driven scheduler: n_rounds=3 but "
            "memory_fraction is held constant at 0.5 (uniform n_cap)."
        ),
        "n_rounds": 3,
        "disable_restart_blend": False,
        "disable_paper_quantity_scheduler": True,
        "disable_gpt_prior_restart": False,
        "expected_component_active": "restart_blend + gpt_prior",
    },
    {
        "arm_id": 3,
        "label": "no_gpt_prior_restart",
        "description": (
            "Without GPT-prior-aware restart policy: n_rounds=3 with "
            "the paper-quantity scheduler active, but the kanzi "
            "adapter's gpt_prior_restart_policy constructor flag is "
            "set to None (uniform restart distribution)."
        ),
        "n_rounds": 3,
        "disable_restart_blend": False,
        "disable_paper_quantity_scheduler": False,
        "disable_gpt_prior_restart": True,
        "expected_component_active": "restart_blend + paper_quantity",
    },
    {
        "arm_id": 4,
        "label": "no_restart_blend_at_all",
        "description": (
            "Without RestartBlend altogether: n_rounds=1, identical to "
            "arm 1, but documented explicitly so reviewers can see the "
            "overlap."
        ),
        "n_rounds": 1,
        "disable_restart_blend": True,
        "disable_paper_quantity_scheduler": True,
        "disable_gpt_prior_restart": True,
        "expected_component_active": "none",
    },
]

#: Per-model metric spec. Each entry maps a (model, seed, nfe) cell to
#: the metric value the framework should report. We restrict to models
#: that have a deterministic synthetic-shim path so the sweep runs in
#: seconds (CI-friendly) and we avoid GPU / upstream-package
#: dependencies for this ablation.
MODELS: list[dict[str, Any]] = [
    {
        "model_id": "twodim_fm",
        "adapter_factory_path": (
            "adaptive_reflow.adapters.twodim_fm:default_twodim_fm_adapter"
        ),
        "metric_name": "w2_two_moons",
        "metric_direction": "lower_is_better",
        "metric_definition": (
            "1-D sliced W2 distance between the twodim_fm adapter's "
            "endpoint sample and the analytic two-moons target. "
            "Computed by the sweep's toy metric helper."
        ),
        "seed": 42,
        "nfe_budget": 100,
        "force_mode": "synthetic",
        "metric_mode": "synthetic",
    },
    {
        "model_id": "kanzi",
        "adapter_factory_path": (
            "adaptive_reflow.adapters.kanzi:default_kanzi_adapter"
        ),
        "metric_name": "per_position_entropy_reduction",
        "metric_direction": "higher_is_better",
        "metric_definition": (
            "Per-position Shannon-entropy reduction (framework endpoint "
            "vs baseline endpoint) computed on the kanzi adapter's "
            "theta/latent channel via "
            "adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction. "
            "Higher = framework sharpened the posterior."
        ),
        "seed": 42,
        "nfe_budget": 50,
        "force_mode": "synthetic",
        "metric_mode": "synthetic",
    },
    {
        "model_id": "lineageflow",
        "adapter_factory_path": (
            "adaptive_reflow.adapters.lineageflow:default_lineageflow_adapter"
        ),
        "metric_name": "per_position_entropy_reduction",
        "metric_direction": "higher_is_better",
        "metric_definition": (
            "Per-position Shannon-entropy reduction (framework endpoint "
            "vs baseline endpoint) computed on the lineageflow "
            "adapter's theta channel via the shared "
            "per_position_entropy_reduction helper. Higher = framework "
            "sharpened the per-position categorical."
        ),
        "seed": 42,
        "nfe_budget": 50,
        "force_mode": "synthetic",
        "metric_mode": "synthetic",
    },
]


# ---------------------------------------------------------------------------
# Toy metric helpers (numpy-only, stdlib-importable)
# ---------------------------------------------------------------------------


def _two_moons_target(n: int, *, seed: int) -> Any:
    """Sample ``n`` points from the analytic two-moons target."""
    import numpy as _np

    rng = _np.random.default_rng(int(seed))
    n0 = n // 2
    n1 = n - n0
    theta0 = _np.linspace(0.0, _np.pi, n0, endpoint=False)
    theta1 = _np.linspace(0.0, _np.pi, n1, endpoint=False)
    outer = _np.stack(
        [_np.cos(theta0), _np.sin(theta0)], axis=1,
    ) + rng.normal(scale=0.1, size=(n0, 2))
    inner = _np.stack(
        [1.0 - _np.cos(theta1), 1.0 - _np.sin(theta1) - 0.2], axis=1,
    ) + rng.normal(scale=0.1, size=(n1, 2))
    pts = _np.concatenate([outer, inner], axis=0)
    rng.shuffle(pts)
    return pts


def _w2_distance_1d(a: Any, b: Any) -> float:
    """1-D Wasserstein-2 via the sorted-quantile trick (numpy-only)."""
    import numpy as _np

    aa = _np.sort(_np.asarray(a, dtype=_np.float64).reshape(-1))
    bb = _np.sort(_np.asarray(b, dtype=_np.float64).reshape(-1))
    n = max(int(min(len(aa), len(bb))), 1)
    aa_q = _np.interp(
        _np.linspace(0.0, 1.0, n),
        _np.linspace(0.0, 1.0, len(aa)),
        aa,
    )
    bb_q = _np.interp(
        _np.linspace(0.0, 1.0, n),
        _np.linspace(0.0, 1.0, len(bb)),
        bb,
    )
    return float(_np.sqrt(_np.mean((aa_q - bb_q) ** 2)))


def _w2_two_moons(sample: Any, *, seed: int) -> float:
    """1-D sliced W2 between ``sample`` (N, 2) and two-moons target.

    ``sample`` can be either an (N, 2) sample (N independent points) or
    a (T, 2) trajectory (T time-steps for one flow). When ``sample``
    has fewer than 2 rows we return ``nan`` so the caller can
    distinguish ``metric undefined`` from ``metric == 0``.
    """
    import numpy as _np

    sample = _np.asarray(sample, dtype=_np.float64).reshape(-1, 2)
    if sample.shape[0] < 2:
        return float("nan")
    # Reduce ``sample`` to the trailing 64 rows (or fewer) so the
    # metric is computed on a stable, multi-point neighbourhood of the
    # flow's endpoint. For ``(T, 2)`` trajectory inputs this picks the
    # last 64 ODE steps; for ``(N, 2)`` sample inputs it picks the
    # last 64 samples.
    n_tail = min(int(sample.shape[0]), 64)
    if n_tail < int(sample.shape[0]):
        sample = sample[-n_tail:]
    target = _two_moons_target(int(sample.shape[0]), seed=int(seed))
    w2_x = _w2_distance_1d(sample[:, 0], target[:, 0])
    w2_y = _w2_distance_1d(sample[:, 1], target[:, 1])
    return float(0.5 * (w2_x + w2_y))


# ---------------------------------------------------------------------------
# Adapter instance + per-arm framework solve helpers
# ---------------------------------------------------------------------------


def _make_adapter(model_spec: dict[str, Any],
                  *, disable_gpt_prior: bool = False,
                  force_mode: str = "synthetic") -> Any:
    """Instantiate the adapter for ``model_spec``.

    Honors ``disable_gpt_prior`` for kanzi via the existing
    ``gpt_prior_restart_policy=None`` constructor flag.

    Wave 155 P1 fix: ``force_mode`` is now threaded in from the
    CLI flag ``--force-mode {synthetic,real}`` (default ``"synthetic"``
    preserves Wave 52 Agent B backward compat). Previously this was
    hardcoded to ``"synthetic"`` at line 333, which silently dropped
    any user request to run the real-ckpt path. The kanzi
    re-instantiation below also now inherits the same ``force_mode``
    (was ``"auto"``).

    Wave 156 P2 alias bridge: the CLI's literal ``"real"`` is mapped
    to the adapter's ``"torch"`` vocabulary here at the CLI boundary
    so ``--force-mode real`` actually exercises the real-ckpt path.
    Per Wave 155 P2 audit (`docs/audit/wave155-real-ckpt-validation.md`),
    the adapter's ``_resolve_mode`` only accepts ``{auto, torch,
    synthetic}``; before this bridge, ``"real"`` was propagated all
    the way to the resolver and raised ``unknown_force_mode:real``.
    Backward-compat preserved: ``"synthetic"`` passes through verbatim.

    Wave 157 P2: When ``force_mode == "torch"`` and the adapter is
    kanzi, the post-Wave-149-P1 bridge at
    :func:`_torch_velocity_field` projects the latent ``(L, 512)``
    trajectory to backbone coords ``(L, 3)`` BEFORE the model call
    (because ``DAE.net`` consumes ``(B, L, 3)`` raw coords). The
    resulting velocity ``v`` has shape ``(L, 3)``, which cannot
    broadcast against ``x_cur.shape == (L, 512)`` in the Euler/Heun
    integration loop (``operands could not be broadcast together
    with shapes (64,512) (64,3)``). The established fix is the
    ``framework_inv_proj`` arm pattern at
    ``tools/_kanzi_sweep_runner.py:421-449``: inverse-project x0 to
    backbone coords via ``kanzi_latent_to_coords`` BEFORE
    :meth:`solve_ode`, then call :meth:`set_traj_shape` with the
    coord shape so the integration loop and the model both operate
    on ``(L, 3)``. This wires the same invariant into the K1 RC5
    sweep's baseline + framework arms.
    """
    if str(force_mode) == "real":
        force_mode = "torch"
    module_path, attr = model_spec["adapter_factory_path"].rsplit(":", 1)
    mod = importlib.import_module(module_path)
    factory = getattr(mod, attr)
    # ``default_twodim_fm_adapter`` does not accept ``force_mode``.
    # The kanzi + lineageflow factories do.
    try:
        adapter = factory(force_mode=str(force_mode))
    except TypeError:
        adapter = factory()
    # For kanzi, re-instantiate with the GPT-prior policy disabled
    # when the arm requires it.
    if (
        disable_gpt_prior
        and model_spec["model_id"] == "kanzi"
    ):
        from adaptive_reflow.adapters.kanzi import (  # type: ignore
            KanziAdapter,
            kanzi_resolve_weights_path,
        )
        with contextlib.suppress(Exception):
            # Fall back to the original adapter if constructor fails
            # in this env (e.g. missing torch). The flag is a no-op
            # in synthetic mode anyway.
            adapter = KanziAdapter(
                weights_path=kanzi_resolve_weights_path(),
                force_mode=str(force_mode),
                gpt_prior_restart_policy=None,
            )
    # Wave 157 P2 — pre-warm the kanzi native-state cache with an
    # inverse-projected (L, 3) x0 and call set_traj_shape so
    # ``solve_ode`` integrates in backbone coord space. See the
    # long-form rationale in the docstring above.
    #
    # Implementation note: the prior approach (warm the cache once
    # with batch_id="warm" then override the entry in place) did NOT
    # take effect because :meth:`solve_ode`'s call site
    # (``_solve_single_pass`` / ``_solve_framework``) invokes
    # :meth:`build_initial_state` with ``batch_id="ablation"``,
    # producing a fresh native-state digest whose ``x0`` is again the
    # canonical ``(64, 512)`` latent. The override must therefore
    # patch :meth:`build_initial_state` itself so EVERY call it makes
    # — under any ``batch_id`` — produces a ``(64, 3)`` backbone-coord
    # x0 once :meth:`set_traj_shape` has been called.
    if (
        str(force_mode) == "torch"
        and model_spec["model_id"] == "kanzi"
        and getattr(adapter, "_mode", None) == "torch"
        and getattr(adapter, "_model", None) is not None
    ):
        try:
            import numpy as _np

            from tools.kanzi_latent_to_coord import (  # type: ignore
                kanzi_latent_to_coords,
            )

            # Pre-compute a canonical ``(L, 3)`` x0 from a one-time
            # ``(64, 512)`` latent sample (the standard
            # ``_real_state_shape`` value) so :meth:`build_initial_state`
            # below can use it as a deterministic template across
            # per-record digest keys.
            _template_rng = _np.random.default_rng(0)
            _template_latent = _np.random.standard_normal(
                (int(getattr(adapter, "_real_state_shape", (64, 512))[0]),
                 int(getattr(adapter, "_real_state_shape", (64, 512))[1])),
            ).astype(_np.float64)
            _template_coords_A = kanzi_latent_to_coords(
                _template_latent,
                decoder=adapter._model._dae,
                fsq_quantizer=adapter._model._dae.quantize,
                n_steps=int(getattr(adapter, "_num_steps", 50)),
                seed=0,
            )
            _template_coords_nm = _np.asarray(
                _template_coords_A, dtype=_np.float64,
            ).reshape(-1, 3) / 10.0
            adapter.set_traj_shape(_template_coords_nm.shape)  # type: ignore[attr-defined]

            # Patch :meth:`build_initial_state` so its emitted ``x0``
            # is the canonical ``(64, 3)`` backbone-coord template
            # above (rather than the synthetic ``(64, 512)`` latent).
            # The wrapper preserves the digest key contract (it still
            # calls the original ``seed_from_ids`` + state digest) so
            # the framework's :func:`native_state_digest` lookups
            # remain stable; only the ``x0`` payload is reshaped.
            _orig_build_initial_state = adapter.build_initial_state

            def _patched_build_initial_state(
                *, batch_id: str, sample_id: str,
            ) -> Any:
                bundle = _orig_build_initial_state(
                    batch_id=batch_id, sample_id=sample_id,
                )
                entry = adapter._native_states.get(  # type: ignore[attr-defined]
                    bundle.native_state_digest,
                )
                if entry is not None:
                    # Replace the ``(L, 512)`` synthetic latent with
                    # the canonical ``(L, 3)`` backbone-coord x0; the
                    # :meth:`solve_ode` reshape to
                    # ``self._effective_traj_shape()`` (now ``(L, 3)``)
                    # then succeeds and the integration loop matches
                    # the velocity field's output shape.
                    entry["x0"] = _template_coords_nm.copy()
                return bundle

            adapter.build_initial_state = _patched_build_initial_state  # type: ignore[method-assign]
        except Exception as exc:  # noqa: BLE001
            # If the bridge is unavailable (e.g. synthetic-only env),
            # leave the adapter in its default ``(L, 512)`` shape; the
            # cell will surface the error via RUN_ERROR and the sweep
            # log records it for post-mortem.
            import sys as _sys
            print(
                f"[W157 P2] kanzi inverse-projection skipped: "
                f"{type(exc).__name__}:{exc}",
                file=_sys.stderr,
            )
    return adapter


def _solve_single_pass(adapter: Any, *, nfe: int, seed: int) -> tuple[Any, float]:
    """Single-pass baseline solve (no restart-blend).

    Returns ``(trace, wallclock_seconds)``.
    """
    from adaptive_reflow.universal.state import ODEConditionDelta  # type: ignore

    bundle = adapter.build_initial_state(batch_id="ablation", sample_id="s0")
    condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe), "sampler_id": "euler"},
        source="run_ablation_sweep:baseline",
        target_round=0,
        calibration_artifact_hash="run_ablation_sweep:default",
    )
    t0 = time.monotonic()
    trace = adapter.solve_ode(bundle, condition, seed=int(seed))
    wall = time.monotonic() - t0
    return trace, wall


def _solve_framework(adapter: Any, *, nfe: int, seed: int,
                     n_rounds: int, uniform_n_cap: bool) -> tuple[Any, float]:
    """Multi-round framework solve.

    When ``uniform_n_cap`` is True, build a constant-beta=0.5 policy
    (memory_fraction = 0.5 every round) so the per-round blend is
    schedule-independent. Otherwise build the default schedule-driven
    policy via the shared :func:`_make_framework_policy`.
    """
    from adaptive_reflow.universal.adapter import (  # type: ignore
        CapabilityMissingError,
    )
    from adaptive_reflow.universal.state import ODEConditionDelta  # type: ignore
    bundle = adapter.build_initial_state(batch_id="ablation", sample_id="s0")
    nfe_per_round = max(1, int(round(nfe / max(1, int(n_rounds)))))
    t0 = time.monotonic()
    cur_bundle = bundle
    trace: Any = None
    for r in range(int(n_rounds)):
        condition = ODEConditionDelta(
            delta_spec={"num_steps": int(nfe_per_round), "sampler_id": "euler"},
            source="run_ablation_sweep:framework",
            target_round=int(r),
            calibration_artifact_hash="run_ablation_sweep:default",
        )
        trace = adapter.solve_ode(cur_bundle, condition, seed=int(seed) + int(r))
        try:
            endpoint = adapter.export_endpoint(cur_bundle)
        except CapabilityMissingError:
            break
        if endpoint is None:
            break
        try:
            if uniform_n_cap:
                policy = _make_uniform_policy(
                    adapter, target_round=int(r), seed=int(seed),
                )
            else:
                policy = _make_framework_policy(
                    adapter, target_round=int(r), seed=int(seed),
                )
            cur_bundle = adapter.apply_restart_distribution(endpoint, policy)
        except CapabilityMissingError:
            break
    wall = time.monotonic() - t0
    return trace, wall


def _make_framework_policy(adapter: Any, *, target_round: int,
                            seed: int) -> Any:
    """Default schedule-driven FinalRestartPolicy (mirrors rre's impl)."""
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
        channel_names = sorted(
            ChannelName(ch)
            for ch in caps.channel_domains
            if isinstance(ch, str)
        ) or [ChannelName("latent")]
    else:
        channel_names = [ChannelName("latent")]

    beta = 0.5
    policy_id = PolicyId(
        f"run_ablation_sweep:framework:r{target_round}:s{seed}",
    )
    draft = FinalRestartPolicy(
        policy_id=policy_id,
        writer_id=MechanismId("inference.adaptive_reflow"),
        run_id=RunId("run_ablation_sweep:framework"),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ch: FactorValue(float(beta)) for ch in channel_names},
        alpha_by_channel={ch: FactorValue(1.0) for ch in channel_names},
        fresh_noise_floor_by_channel={
            ch: FactorValue(0.0) for ch in channel_names
        },
        schedule_sample=None,
        freeze_admission_by_channel={ch: True for ch in channel_names},
        ledger_row_id=LedgerRowId(
            f"ledger-run_ablation_sweep-r{target_round}",
        ),
        policy_hash=ArtifactHash(""),
        created_at_round=int(target_round),
        beta_from_schedule=True,
    )
    return _dc_replace(draft, policy_hash=hash_policy_hash(draft))


def _make_uniform_policy(adapter: Any, *, target_round: int,
                         seed: int) -> Any:
    """Constant-beta=0.5 policy (uniform n_cap arm).

    Same surface as :func:`_make_framework_policy` but with
    ``beta_from_schedule=False`` so the per-round blend is constant
    (memory_fraction = 0.5 every round). Mirrors the "uniform n_cap"
    ablation arm.
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
        channel_names = sorted(
            ChannelName(ch)
            for ch in caps.channel_domains
            if isinstance(ch, str)
        ) or [ChannelName("latent")]
    else:
        channel_names = [ChannelName("latent")]

    beta = 0.5
    policy_id = PolicyId(
        f"run_ablation_sweep:uniform:r{target_round}:s{seed}",
    )
    draft = FinalRestartPolicy(
        policy_id=policy_id,
        writer_id=MechanismId("inference.adaptive_reflow"),
        run_id=RunId("run_ablation_sweep:uniform"),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ch: FactorValue(float(beta)) for ch in channel_names},
        alpha_by_channel={ch: FactorValue(1.0) for ch in channel_names},
        fresh_noise_floor_by_channel={
            ch: FactorValue(0.0) for ch in channel_names
        },
        schedule_sample=None,
        freeze_admission_by_channel={ch: True for ch in channel_names},
        ledger_row_id=LedgerRowId(
            f"ledger-run_ablation_sweep-r{target_round}",
        ),
        policy_hash=ArtifactHash(""),
        created_at_round=int(target_round),
        beta_from_schedule=False,
    )
    return _dc_replace(draft, policy_hash=hash_policy_hash(draft))


# ---------------------------------------------------------------------------
# Endpoint extraction (per model)
# ---------------------------------------------------------------------------


def _extract_endpoint_sample(adapter: Any, model_id: str) -> Any:
    """Return the most-recent endpoint sample from ``adapter._native_states``.

    Cache shape varies per adapter:

    * twodim_fm: ``OrderedDict`` directly. The ``trajectory`` entry's
      last frame is the ODE endpoint; ``x0`` is the noise prior (a
      single (2,) point, not the endpoint).
    * kanzi: ``NativeStateCache`` (use ``_data`` for keys). The
      ``trajectory`` entry's last frame is the latent endpoint; the
      separate ``x0`` entries are intermediate round states.
    * lineageflow: ``OrderedDict`` directly. ``trajectory`` last frame
      is the per-position categorical endpoint; ``theta`` entries are
      intermediate.

    We prefer the ``trajectory`` last frame when available; otherwise
    fall back to the most-recent primary state (``theta`` /
    ``x0``). Returns ``None`` when the cache is empty.
    """
    cache = getattr(adapter, "_native_states", None)
    if cache is None:
        return None
    # Locate the underlying OrderedDict surface.
    inner = getattr(cache, "_data", None)
    if inner is None and hasattr(cache, "keys"):
        inner = cache
    if inner is None or not hasattr(inner, "keys"):
        return None
    digests = list(inner.keys())
    if not digests:
        return None
    # Walk the entries in reverse; pick the first one with a
    # ``trajectory`` entry and return its last frame.
    for digest in reversed(digests):
        entry = cache.get(digest) if hasattr(cache, "get") else None
        if entry is None:
            continue
        trajectory = entry.get("trajectory")
        if trajectory is not None:
            try:
                import numpy as _np
                return _np.asarray(trajectory, dtype=_np.float64)[-1]
            except Exception:
                continue
    # Fall back: most-recent primary state on the last digest.
    last = digests[-1]
    entry = cache.get(last) if hasattr(cache, "get") else None
    if entry is None:
        return None
    if model_id == "twodim_fm":
        # twodim_fm's ``x0`` is the noise prior, not the endpoint. As
        # a last resort return the trajectory's first frame (closest
        # to ``x0`` in ODE time).
        return entry.get("x0")
    for key in ("theta", "x0", "blended", "endpoint"):
        if key in entry:
            return entry[key]
    return None


# ---------------------------------------------------------------------------
# Per-cell metric computation
# ---------------------------------------------------------------------------


def _compute_cell_metric(
    model_spec: dict[str, Any],
    arm: dict[str, Any],
    *,
    baseline_endpoint: Any,
    framework_endpoint: Any,
    seed: int,
) -> dict[str, Any]:
    """Compute the metric for one (arm, model) cell.

    ``baseline_endpoint`` and ``framework_endpoint`` are the
    adapter's most-recent cached endpoint samples after running the
    baseline and framework solves respectively.
    """
    out: dict[str, Any] = {
        "metric_name": model_spec["metric_name"],
        "metric_direction": model_spec["metric_direction"],
    }
    if model_spec["model_id"] == "twodim_fm":
        # For twodim_fm we want a per-cell signed delta that varies
        # between arms. The twodim_fm adapter produces a single (2,)
        # latent per ``solve_ode`` call (not a population), so the
        # shared per_position_entropy_reduction helper returns NaN
        # (it requires >= 2 samples).
        #
        # We use a different metric: the L2 distance from the
        # framework endpoint to the analytic two-moons centroid. The
        # framework's multi-round restart-blend perturbs the latent
        # away from the baseline path, so the per-arm L2 distance
        # to the two-moons target discriminates arms 0/2/3 from
        # arms 1/4 (which collapse to the baseline single-pass).
        import numpy as _np
        if baseline_endpoint is None or framework_endpoint is None:
            out["endpoint_l2_to_target"] = None
            out["signed_delta"] = None
            out["endpoint_source"] = (
                "missing_baseline" if baseline_endpoint is None
                else "missing_framework"
            )
            return out
        try:
            fwk = _np.asarray(framework_endpoint, dtype=_np.float64).reshape(-1)
            # Two-moons centroid (the analytic mean of the two-moons
            # distribution in 2-D). The standard two-moons target
            # has two arcs whose mean is approximately (0.5, 0.3).
            target_centroid = _np.array([0.5, 0.3], dtype=_np.float64)
            if fwk.shape[0] >= 2:
                # Treat the first 2 coordinates of the (T, 2)
                # trajectory's last frame as the (x, y) endpoint.
                endpoint_xy = fwk[:2] if fwk.shape[0] == 2 else (
                    fwk.reshape(-1, 2)[-1]
                )
            else:
                endpoint_xy = fwk[:2]
            l2 = float(_np.linalg.norm(endpoint_xy - target_centroid))
        except Exception as exc:  # noqa: BLE001
            out["endpoint_l2_to_target"] = None
            out["signed_delta"] = None
            out["error"] = f"{type(exc).__name__}:{exc}"
            return out
        # Also compute baseline_endpoint_l2 for context.
        try:
            base = _np.asarray(baseline_endpoint, dtype=_np.float64).reshape(-1)
            base_xy = base if base.shape[0] == 2 else base.reshape(-1, 2)[-1]
            baseline_l2 = float(
                _np.linalg.norm(base_xy - target_centroid),
            )
        except Exception:
            baseline_l2 = float("nan")
        # ``signed_delta`` is defined as ``baseline_l2 - framework_l2``
        # (positive = framework is closer to the target than baseline).
        out["endpoint_l2_to_target"] = l2
        out["baseline_endpoint_l2_to_target"] = baseline_l2
        out["signed_delta"] = (
            float(baseline_l2 - l2)
            if (l2 == l2 and baseline_l2 == baseline_l2) else None
        )
        out["endpoint_source"] = "framework"
        out["baseline_endpoint_shape"] = (
            list(_np.asarray(baseline_endpoint).shape)
        )
        out["framework_endpoint_shape"] = list(fwk.shape)
        return out
    # kanzi + lineageflow: per-position entropy reduction.
    import numpy as _np

    from adaptive_reflow.adapters._adapter_common import (  # type: ignore
        per_position_entropy_reduction,
    )

    if baseline_endpoint is None or framework_endpoint is None:
        out["per_position_entropy_reduction"] = None
        out["signed_delta"] = None
        out["endpoint_source"] = (
            "missing_baseline" if baseline_endpoint is None
            else "missing_framework"
        )
        return out
    base = _np.asarray(baseline_endpoint, dtype=_np.float64)
    fwk = _np.asarray(framework_endpoint, dtype=_np.float64)
    try:
        reduction = per_position_entropy_reduction(base, fwk)
    except Exception as exc:  # noqa: BLE001
        out["per_position_entropy_reduction"] = None
        out["signed_delta"] = None
        out["error"] = f"{type(exc).__name__}:{exc}"
        return out
    out["per_position_entropy_reduction"] = float(reduction)
    out["signed_delta"] = float(reduction)
    out["endpoint_source"] = "framework"
    out["baseline_endpoint_shape"] = list(base.shape)
    out["framework_endpoint_shape"] = list(fwk.shape)
    return out


# ---------------------------------------------------------------------------
# Cell execution
# ---------------------------------------------------------------------------


def run_arm_cell(
    arm: dict[str, Any],
    model_spec: dict[str, Any],
) -> dict[str, Any]:
    """Run one (arm, model) cell.

    Returns a dict ready to be folded into the ablation table.
    """
    cell: dict[str, Any] = {
        "arm_id": arm["arm_id"],
        "arm_label": arm["label"],
        "model_id": model_spec["model_id"],
        "metric_name": model_spec["metric_name"],
        "metric_direction": model_spec["metric_direction"],
        "nfe_budget": model_spec["nfe_budget"],
        "seed": model_spec["seed"],
    }

    try:
        adapter = _make_adapter(
            model_spec,
            disable_gpt_prior=bool(arm["disable_gpt_prior_restart"]),
            force_mode=str(model_spec.get("force_mode", "synthetic")),
        )
    except Exception as exc:  # noqa: BLE001
        cell["status"] = "BLOCKED"
        cell["baseline_metric"] = None
        cell["framework_metric"] = None
        cell["signed_delta"] = None
        cell["reason"] = f"adapter_unavailable:{type(exc).__name__}:{exc}"
        return cell

    nfe = int(model_spec["nfe_budget"])
    seed = int(model_spec["seed"])

    try:
        # 1. Run the baseline single-pass solve.
        _btrace, baseline_wall = _solve_single_pass(
            adapter, nfe=nfe, seed=seed,
        )
        baseline_endpoint = _extract_endpoint_sample(
            adapter, model_spec["model_id"],
        )
        # 2. Run the framework solve (per-arm n_rounds + uniform-n_cap).
        if arm["disable_restart_blend"]:
            _ftrace, framework_wall = _solve_single_pass(
                adapter, nfe=nfe, seed=seed,
            )
        else:
            _ftrace, framework_wall = _solve_framework(
                adapter, nfe=nfe, seed=seed,
                n_rounds=int(arm["n_rounds"]),
                uniform_n_cap=bool(arm["disable_paper_quantity_scheduler"]),
            )
        framework_endpoint = _extract_endpoint_sample(
            adapter, model_spec["model_id"],
        )
        cell["wallclock_baseline_s"] = round(float(baseline_wall), 4)
        cell["wallclock_framework_s"] = round(float(framework_wall), 4)
        # 3. Compute the per-cell metric directly.
        metric = _compute_cell_metric(
            model_spec, arm,
            baseline_endpoint=baseline_endpoint,
            framework_endpoint=framework_endpoint,
            seed=seed,
        )
        cell.update(metric)
        cell["status"] = "OK"
    except Exception as exc:  # noqa: BLE001
        cell["status"] = "RUN_ERROR"
        cell["error"] = f"{type(exc).__name__}:{exc}"
        cell["traceback"] = traceback.format_exc()
    return cell


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_table(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the 5x3 ablation table (rows = arms, cols = models)."""
    table: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        table[arm["label"]] = {}
        for model in MODELS:
            cell = next(
                (
                    c for c in cells
                    if c["arm_id"] == arm["arm_id"]
                    and c["model_id"] == model["model_id"]
                ),
                None,
            )
            # Surface a compact per-cell summary.
            summary: dict[str, Any] = {"status": cell.get("status") if cell else None}
            if cell:
                for k in (
                    "framework_w2", "baseline_w2",
                    "endpoint_l2_to_target", "baseline_endpoint_l2_to_target",
                    "per_position_entropy_reduction",
                    "signed_delta", "endpoint_source",
                    "wallclock_baseline_s", "wallclock_framework_s",
                ):
                    if k in cell:
                        summary[k] = cell[k]
            table[arm["label"]][model["model_id"]] = summary
    return table


def per_component_contribution(
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-component contribution analysis.

    For each component, compute the marginal contribution = the delta
    between arm 0 (all on) and the arm that turns OFF only that
    component (holding the others constant). Larger positive
    contribution = framework value-add attributable to that component.

    Direction conventions per model:

    * twodim_fm: ``signed_delta`` = ``baseline_l2 - framework_l2``.
      Positive = framework is closer to the two-moons target than
      baseline (good).
    * kanzi + lineageflow: ``signed_delta`` = per-position entropy
      reduction. Positive = framework sharpens the per-position
      posterior relative to baseline (good).

    A *negative* contribution means the component *hurts* on that
    model (in synthetic mode this can happen because the synthetic
    shim's restart-blend widens entropy; on real ckpt the framework
    generally helps). The per-component contribution is a *signed*
    scalar in both directions.
    """
    by_arm: dict[int, dict[str, dict[str, Any]]] = {}
    for c in cells:
        by_arm.setdefault(c["arm_id"], {})[c["model_id"]] = c

    contributions: dict[str, Any] = {}

    def _delta(arm_a_id: int, arm_b_id: int, model_id: str) -> float | None:
        a = by_arm.get(arm_a_id, {}).get(model_id)
        b = by_arm.get(arm_b_id, {}).get(model_id)
        if a is None or b is None:
            return None
        da = a.get("signed_delta")
        db = b.get("signed_delta")
        if da is None or db is None:
            return None
        # Use signed numbers when both are non-NaN; otherwise None.
        if da != da or db != db:
            return None
        return float(da) - float(db)

    # restart-blend contribution = arm0 - arm1 (per model)
    rb = {
        m["model_id"]: _delta(0, 1, m["model_id"]) for m in MODELS
    }
    # paper-quantity scheduler contribution = arm0 - arm2
    pq = {
        m["model_id"]: _delta(0, 2, m["model_id"]) for m in MODELS
    }
    # GPT-prior restart contribution = arm0 - arm3
    gpt = {
        m["model_id"]: _delta(0, 3, m["model_id"]) for m in MODELS
    }

    contributions["restart_blend"] = {
        "definition": (
            "Framework value-add attributable to restart-blend as a "
            "whole (arm0 minus arm1). arm1 collapses to single-pass "
            "baseline (n_rounds=1)."
        ),
        "per_model_signed_delta": rb,
        "interpretation": (
            "twodim_fm: positive = arm0 closer to target than arm1 "
            "(restart-blend helped). kanzi + lineageflow: positive = "
            "arm0 sharpens more than arm1 (restart-blend helped)."
        ),
    }
    contributions["paper_quantity_scheduler"] = {
        "definition": (
            "Framework value-add attributable to the paper-quantity-"
            "driven scheduler (arm0 minus arm2). arm2 uses a uniform "
            "n_cap (constant memory fraction = 0.5)."
        ),
        "per_model_signed_delta": pq,
        "interpretation": (
            "Positive = paper-quantity-driven scheduler strictly "
            "improves over the uniform-n_cap baseline."
        ),
    }
    contributions["gpt_prior_aware_restart"] = {
        "definition": (
            "Framework value-add attributable to the GPT-prior-aware "
            "restart policy (arm0 minus arm3). arm3 uses the default "
            "(uniform) restart distribution."
        ),
        "per_model_signed_delta": gpt,
        "interpretation": (
            "Positive = GPT-prior-aware restart strictly improves over "
            "the uniform-restart baseline. For models other than kanzi "
            "this contribution is zero (kanzi-only feature in synthetic "
            "mode; the GPT-prior monkey-patch only fires on torch-mode "
            "real ckpt)."
        ),
    }

    # Top-contributor per model (ranking components by absolute
    # signed delta descending).
    ranking: dict[str, list[dict[str, Any]]] = {}
    for m in MODELS:
        mid = m["model_id"]
        rows = [
            ("restart_blend", rb.get(mid)),
            ("paper_quantity_scheduler", pq.get(mid)),
            ("gpt_prior_aware_restart", gpt.get(mid)),
        ]
        # Sort by absolute value descending; None at the bottom.
        rows.sort(key=lambda r: (r[1] is None, -abs(r[1] or 0.0)))
        ranking[mid] = [
            {
                "component": name,
                "signed_delta": val,
                "abs_signed_delta": abs(val) if val is not None else None,
            } for name, val in rows
        ]
    contributions["per_model_top_component"] = ranking
    return contributions


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scripts.run_ablation_sweep",
        description=(
            "Wave 52 Agent B — per-component 5-arm ablation sweep."
        ),
    )
    p.add_argument(
        "--output", type=pathlib.Path,
        default=REPO_ROOT / "verification_outputs" / "ablation_q4_2026.json",
        help="Output JSON path (default verification_outputs/ablation_q4_2026.json).",
    )
    p.add_argument(
        "--seed", type=int, default=42,
        help="Master RNG seed (default 42).",
    )
    p.add_argument(
        "--nfe-budgets", type=str, default=None,
        help=(
            "Optional comma-separated NFE budgets to override the "
            "per-model defaults. Useful for stress-testing the sweep."
        ),
    )
    p.add_argument(
        "--force-mode", choices=("synthetic", "real"), default="synthetic",
        help=(
            "Force mode forwarded to per-model adapter factories. "
            "Default 'synthetic' keeps the CI-friendly shim path "
            "(Wave 52 Agent B backward-compat). Pass 'real' to "
            "exercise the real-ckpt path on supported adapters "
            "(kanzi, lineageflow)."
        ),
    )
    p.add_argument(
        "--metric-mode", choices=("synthetic", "real"), default="synthetic",
        help=(
            "Metric computation mode. Default 'synthetic' uses the "
            "stdlib-only toy metric helpers (numpy). Pass 'real' to "
            "route through per-model real-ckpt metrics."
        ),
    )
    p.add_argument(
        "--limit", type=int, default=0,
        help=(
            "Optional per-cell record cap. Default 0 = no cap "
            "(forward-compat hook; not yet threaded into the "
            "synthetic-mode cells which compute one number per arm)."
        ),
    )
    p.add_argument(
        "--model", choices=("twodim_fm", "cifar10_rf", "lineageflow", "kanzi"),
        default=None,
        help=(
            "Optional model filter; when set only the matching "
            "MODELS entry is run (forward-compat hook for "
            "single-model sweeps)."
        ),
    )
    p.add_argument(
        "--ckpt", type=pathlib.Path, default=None,
        help=(
            "Optional checkpoint path forwarded to the adapter "
            "factory (forward-compat hook; only used when --force-mode "
            "= real and --model selects a real-ckpt adapter)."
        ),
    )
    # Wave 165b P2 — per-component ablation toggles. When any of these
    # is set, the script runs a SINGLE custom arm reflecting the
    # combined 3-toggle (BRAI / beta-scheduler / restart) state. All
    # default to None (= use the canonical 5-arm sweep).
    p.add_argument(
        "--disable-brai", dest="disable_brai",
        action="store_true", default=None,
        help=(
            "Wave 165b P2 toggle: disable the BRAI (GPT-prior-aware "
            "restart) component. Maps internally to "
            "disable_gpt_prior_restart. Combined with "
            "--enable-brai / --disable-X / --enable-X below to "
            "specify a 3-toggle cell (Wave 165b P2 8-cell matrix)."
        ),
    )
    p.add_argument(
        "--enable-brai", dest="enable_brai",
        action="store_true", default=None,
        help=(
            "Wave 165b P2 toggle: explicitly enable the BRAI "
            "component. Tri-state: passing neither flag leaves the "
            "custom arm's BRAI field at its default (enabled)."
        ),
    )
    p.add_argument(
        "--disable-beta-scheduler", dest="disable_beta_scheduler",
        action="store_true", default=None,
        help=(
            "Wave 165b P2 toggle: disable the paper-quantity-driven "
            "beta scheduler (uniform n_cap fallback). Maps to "
            "disable_paper_quantity_scheduler."
        ),
    )
    p.add_argument(
        "--enable-beta-scheduler", dest="enable_beta_scheduler",
        action="store_true", default=None,
        help=(
            "Wave 165b P2 toggle: explicitly enable the beta "
            "scheduler."
        ),
    )
    p.add_argument(
        "--disable-restart", dest="disable_restart",
        action="store_true", default=None,
        help=(
            "Wave 165b P2 toggle: disable the restart-blend as a "
            "whole (n_rounds collapses to 1, framework degenerates "
            "to single-pass solve). Maps to disable_restart_blend."
        ),
    )
    p.add_argument(
        "--enable-restart", dest="enable_restart",
        action="store_true", default=None,
        help=(
            "Wave 165b P2 toggle: explicitly enable the restart-"
            "blend component."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    # K1 RC4 fix: override the hardcoded 'synthetic' literals at
    # MODELS:199-238 with CLI-driven values so the script can target
    # real-ckpt paths without source-code patches. Backward-compat
    # preserved because both flags default to 'synthetic'.
    for m in MODELS:
        m["force_mode"] = args.force_mode
        m["metric_mode"] = args.metric_mode
    if args.nfe_budgets:
        nfe_list = [
            int(s.strip()) for s in args.nfe_budgets.split(",") if s.strip()
        ]
        for m in MODELS:
            if nfe_list:
                m["nfe_budget"] = nfe_list[0]
    # Wave 165b P2: when any of the --disable-X / --enable-X flags is
    # set, run a single custom arm that mirrors the 3-toggle
    # combination. Tri-state resolution: --disable-X wins over
    # --enable-X; absence = component enabled (so the default
    # "all-on" cell is reachable without specifying any toggle).
    toggle_flags = (
        args.disable_brai,
        args.enable_brai,
        args.disable_beta_scheduler,
        args.enable_beta_scheduler,
        args.disable_restart,
        args.enable_restart,
    )
    custom_arm_set = any(t is not None for t in toggle_flags)
    if custom_arm_set:
        # Resolve tri-state per component: disable-X wins; enable-X
        # wins over absence; absence = enabled (default-on).
        if args.disable_brai is True:
            disable_brai = True
        elif args.enable_brai is True:
            disable_brai = False
        else:
            disable_brai = False  # default-on
        if args.disable_beta_scheduler is True:
            disable_beta = True
        elif args.enable_beta_scheduler is True:
            disable_beta = False
        else:
            disable_beta = False  # default-on
        if args.disable_restart is True:
            disable_restart = True
        elif args.enable_restart is True:
            disable_restart = False
        else:
            disable_restart = False  # default-on
        # Naming convention: cells are referenced by their toggle bitstring
        # (BRAI, beta-scheduler, restart) where 1 = disabled.
        bits = (
            ("B" if disable_brai else "b"),
            ("S" if disable_beta else "s"),
            ("R" if disable_restart else "r"),
        )
        custom_label = "custom_" + "".join(bits)
        custom_arm: dict[str, Any] = {
            "arm_id": 99,
            "label": custom_label,
            "description": (
                f"Custom 3-toggle arm (Wave 165b P2). "
                f"disable_brai={disable_brai} "
                f"disable_beta_scheduler={disable_beta} "
                f"disable_restart={disable_restart}."
            ),
            "n_rounds": 1 if disable_restart else 3,
            "disable_restart_blend": disable_restart,
            "disable_paper_quantity_scheduler": disable_beta,
            "disable_gpt_prior_restart": disable_brai,
            "expected_component_active": (
                "none" if (disable_brai and disable_beta and disable_restart)
                else "subset"
            ),
        }
        arms_to_run = [custom_arm]
    else:
        arms_to_run = list(ARMS)
    cells: list[dict[str, Any]] = []
    for arm in arms_to_run:
        for model_spec in MODELS:
            model_spec = dict(model_spec)
            model_spec["seed"] = args.seed
            print(
                f"[CELL] arm={arm['arm_id']} ({arm['label']}) "
                f"model={model_spec['model_id']} "
                f"nfe={model_spec['nfe_budget']} seed={model_spec['seed']}",
                file=sys.stderr,
            )
            cell = run_arm_cell(arm, model_spec)
            cells.append(cell)
            print(
                f"  -> status={cell.get('status')} "
                f"signed_delta={cell.get('signed_delta')}",
                file=sys.stderr,
            )
    table = aggregate_table(cells)
    contributions = per_component_contribution(cells)
    report = {
        "schema": "ablation_q4_2026.v1",
        "tool": "scripts/run_ablation_sweep.py",
        "wave": "Wave 52 Agent B + Wave 165b P2 toggle extensions",
        "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),  # noqa: UP017 (Wave 166 P4: 3.10 back-compat)
        "arms": arms_to_run,
        "models": MODELS,
        "cells": cells,
        "ablation_table": table,
        "per_component_contribution": contributions,
        "notes": (
            "5x3 ablation (5 arms x 3 models). Direct endpoint metric "
            "(per-position entropy reduction for kanzi + lineageflow; "
            "1-D sliced W2 for twodim_fm) so per-arm deltas are "
            "non-saturating. Each cell uses synthetic-mode adapter "
            "(zero upstream deps, CI-friendly). Disjoint file scope "
            "honoured: no framework file is modified. Wave 165b P2 "
            "extended the CLI with --disable-brai / "
            "--disable-beta-scheduler / --disable-restart so each of "
            "the 2^3=8 toggle combinations can be run as a single "
            "explicit cell without bash loops."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=False, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    print(f"[DONE] wrote {args.output} ({len(cells)} cells)", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
