#!/usr/bin/env python3
"""GAP-80 — the R5a arm that actually restarts.

The scored R5a path (`BatchedTrajectoryRunner`, used by
`tools/run_sota_2d_experiment.py`) never dispatches
`apply_restart_distribution` (0 calls over 3 rounds; see
``docs/audit/gap80-r5a-harness.md`` §2). This driver runs the same
two-moons adapter through the adapter protocol instead:

    solve_ode -> observe_endpoint -> apply_restart_distribution -> solve_ode ...

so the framework arm is a **restarted** population rather than the baseline
generator sampled again.

Pre-registration: ``docs/audit/gap80-r5a-harness.md`` §8.

Design decisions, all fixed before the first run
------------------------------------------------
* **Both arms go through this driver.** The baseline arm is the same loop with
  ``n_rounds = 1`` and no restart, so the comparison isolates the restart and
  nothing else. `_run_baseline` from ``tools/run_sota_2d_experiment`` is run
  alongside as a cross-check on the sampling path; it draws ``x0`` from
  ``generate_trajectory`` rather than ``build_initial_state``, so it is a
  distribution check, not a byte check.
* **β is the cosine schedule, applied exactly.** ``beta_r = 1 - n_cap_r`` from
  ``CosineAnnealScheduler(cycle_length=n_rounds)``, passed through
  ``beta_override`` with ``nfe = 0`` so the NFE-adaptive attenuation in
  ``_make_framework_policy`` does not rescale it a second time. Every other
  R5a number is reported at the nominal schedule; this arm matches that.
* **NFE is split evenly**, remainder into the last round, so the total equals
  the baseline's ``TWODIM_FM_NUM_STEPS``.
* **Seeds are the canonical ten** (42..51), the same set the published R5a
  table uses. No top-ups.
* **Three restart arms**, all diagnostic: ``convex_policy`` (the shipped
  operator with the shipped seeding), ``convex_record`` (same blend, fresh draw
  scoped to the record) and ``vp_record`` (same seeding, variance-preserving
  blend ``m*prior + sqrt(1-m^2)*fresh``). The shipped convention is unchanged;
  the record-scoped hash is a driver-local re-hash of the policy, which is
  enough because the adapter derives its draw from ``policy_hash`` alone.

Usage
-----
    python3 -m tools.r5a_restart_driver --out verification_outputs/gap80-r5a-restart
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from adaptive_reflow.adapters._adapter_common import (
    digest_state,
    make_ref,
    memory_fraction_for,
)
from adaptive_reflow.adapters.twodim_fm import (
    AUDIT_RESTART_BLEND,
    TwoDimFMAdapter,
)
from adaptive_reflow.contracts.authority import ArtifactHash
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    StateBundle,
)
from tools.eval.baseline import _build_initial_state_and_condition
from tools.eval.framework import _make_framework_policy
from tools.run_sota_2d_experiment import (
    _build_cosine_scheduler,
    _run_baseline,
    _wasserstein_2d,
)

DEFAULT_SEEDS = list(range(42, 52))
ARM_SPECS: dict[str, dict[str, Any]] = {
    # shipped operator + shipped (record-invariant) seeding
    "convex_policy": {"restart_mode": "convex", "seed_scope": "policy", "align_t0": False},
    # shipped operator, fresh draw scoped to the record
    "convex_record": {"restart_mode": "convex", "seed_scope": "record", "align_t0": False},
    # variance-preserving blend, record-scoped (GAP-80 §8.6)
    "vp_record": {"restart_mode": "vp", "seed_scope": "record", "align_t0": False},
    # shipped blend, record-scoped, integrated from t = memory (GAP-80 §8.7)
    "aligned_record": {"restart_mode": "convex", "seed_scope": "record", "align_t0": True},
    "aligned_policy": {"restart_mode": "convex", "seed_scope": "policy", "align_t0": True},
}
DEFAULT_ARMS = ("convex_policy", "convex_record", "aligned_record")
TARGET = "two_moons"
NFE = 150  # TWODIM_FM_NUM_STEPS — the baseline's budget
N_ROUNDS = 5
N_RECORDS = 1000


def _split_nfe(total: int, rounds: int) -> list[int]:
    """Even split with the remainder in the last round (sum == total)."""
    base = total // rounds
    out = [base] * rounds
    out[-1] += total - base * rounds
    return out


def _restart_point(
    adapter: TwoDimFMAdapter,
    state: StateBundle,
    policy: Any,
    *,
    mode: str,
    record_key: str = "",
) -> tuple[np.ndarray, float, float]:
    """Blend ``state``'s endpoint with a fresh prior draw.

    ``mode = "convex"`` is the shipped operator,
    ``m * prior + (1 - m) * fresh``; ``mode = "vp"`` is the
    variance-preserving variant, ``m * prior + sqrt(1 - m^2) * fresh``.
    The fresh draw is derived exactly as
    :meth:`TwoDimFMAdapter.apply_restart_distribution` does it, so
    ``convex`` reproduces that method byte-for-byte (pinned by
    ``tests/test_gap80_r5a_driver.py``).
    """
    beta, memory = memory_fraction_for(policy, ChannelName("xy"))
    prior = np.asarray(
        adapter._native_states[state.native_state_digest]["x0"], dtype=np.float64
    ).reshape(2)
    next_round = int(state.source_round) + 1
    blob_parts: tuple[Any, ...] = (
        (str(policy.policy_hash), next_round)
        if not record_key
        else (str(policy.policy_hash), record_key, next_round)
    )
    seed = int(
        hashlib.sha256(repr(blob_parts).encode("utf-8")).hexdigest()[:8], 16
    )
    fresh = np.random.default_rng(seed).standard_normal(2).astype(np.float64)
    m = max(0.0, min(1.0, float(memory)))
    if mode == "vp":
        blended = m * prior + math.sqrt(max(0.0, 1.0 - m * m)) * fresh
    else:
        blended = m * prior + (1.0 - m) * fresh
    return blended.reshape(2), float(beta), float(memory)


def _bundle_after_restart(
    adapter: TwoDimFMAdapter,
    state: StateBundle,
    policy: Any,
    blended: np.ndarray,
    *,
    beta: float,
    memory: float,
) -> StateBundle:
    """Mirror of the adapter's restart bundle for a caller-chosen blend."""
    next_round = int(state.source_round) + 1
    next_digest = digest_state(
        {
            "kind": "restart",
            "src_digest": state.native_state_digest,
            "policy_hash": str(policy.policy_hash),
            "source_round": next_round,
            "beta": float(beta),
            "memory_fraction": float(memory),
            "blended_x0": [float(blended[0]), float(blended[1])],
        }
    )
    adapter._put_native_state(
        next_digest,
        {
            "x0": np.asarray(blended, dtype=np.float64).reshape(2),
            "target": adapter._target,
            "source_round": next_round,
        },
    )
    return StateBundle(
        channels={
            ChannelName("xy"): make_ref(
                "twodim:xy",
                "restart",
                src_digest=str(state.native_state_digest),
                policy_hash=str(policy.policy_hash),
                source_round=int(next_round),
                x0=[float(blended[0]), float(blended[1])],
            )
        },
        masks=dict(state.masks),
        batch_id=str(state.batch_id),
        sample_id=str(state.sample_id),
        reference_frame=str(state.reference_frame),
        normalization=str(state.normalization),
        source_round=int(next_round),
        detach_proof=True,
        native_state_digest=str(next_digest),
        provenance=tuple(state.provenance)
        + (
            AUDIT_RESTART_BLEND,
            f"blender:{adapter._blender.blender_family()}",
            f"blender_hash:{adapter._blender.config_hash()}",
        ),
        capability_token=adapter.capabilities(),
    )


def _solve_one(
    adapter: TwoDimFMAdapter,
    bundle: Any,
    *,
    seed: int,
    nfe: int,
    n_rounds: int,
    betas: list[float] | None,
    restart: bool,
    record_key: str = "",
    restart_mode: str = "convex",
    align_t0: bool = False,
) -> np.ndarray:
    """Run one record; return its final endpoint (shape ``(2,)``).

    ``align_t0`` makes every post-restart round integrate from
    ``t = memory_fraction``, the time at which the blend actually sits on the
    path ``x_t = (1-t) x_0 + t x_1``. Without it the round integrates a
    mid-path state from ``t = 0`` — the defect GAP-56 fixed for MNIST and
    that this adapter never had.
    """
    per_round = _split_nfe(nfe, n_rounds)
    t_start = 0.0
    for r in range(n_rounds):
        cond = ODEConditionDelta(
            delta_spec={
                "num_steps": int(per_round[r]),
                "sampler_id": "euler",
                "t0": float(t_start),
            },
            source="r5a_restart_driver",
            target_round=int(r),
            calibration_artifact_hash="r5a_restart_driver:default",
        )
        trace = adapter.solve_ode(bundle, cond, seed=int(seed))
        bundle = adapter.observe_endpoint(trace, bundle)
        if restart and r < n_rounds - 1:
            policy = _make_framework_policy(
                adapter,
                target_round=int(r),
                seed=int(seed),
                nfe=0,  # disable the NFE-adaptive rescale: beta is exact
                beta_override=float(betas[r]) if betas else None,
            )
            if not record_key and restart_mode == "convex":
                # The shipped path, called exactly as every other cell calls it.
                bundle = adapter.apply_restart_distribution(bundle, policy)
                if align_t0:
                    _, memory = memory_fraction_for(policy, ChannelName("xy"))
                    t_start = max(0.0, min(1.0, float(memory)))
                continue
            if record_key:
                # Diagnostic only: the adapter derives the fresh draw from
                # ``sha256((policy_hash, next_round))``, so a record-scoped
                # hash makes the draw record-scoped without touching the
                # adapter. See §3 (F2) and §8 of the GAP-80 audit.
                policy = replace(
                    policy,
                    policy_hash=ArtifactHash(
                        hashlib.sha256(
                            f"{policy.policy_hash}|{record_key}|r{r}".encode()
                        ).hexdigest()
                    ),
                )
            blended, beta, memory = _restart_point(
                adapter,
                bundle,
                policy,
                mode=restart_mode,
                record_key="",
            )
            bundle = _bundle_after_restart(
                adapter, bundle, policy, blended, beta=beta, memory=memory
            )
            if align_t0:
                t_start = max(0.0, min(1.0, float(memory)))
    # ``observe_endpoint`` stores the final point under ``x`` (and mirrors it
    # to ``x0`` so the next round starts there); the raw trajectory is keyed
    # by the *trace* digest, which the bundle no longer carries.
    return np.asarray(
        adapter._native_states[bundle.native_state_digest]["x"], dtype=np.float64
    ).reshape(2)


def run_protocol_arm(
    *,
    seed: int,
    n_records: int,
    nfe: int,
    n_rounds: int,
    restart: bool,
    seed_scope: str = "policy",
    restart_mode: str = "convex",
    align_t0: bool = False,
) -> np.ndarray:
    """One arm, ``n_records`` endpoints, all through the adapter protocol."""
    adapter = TwoDimFMAdapter(target=TARGET)
    betas = [0.0] * n_rounds
    if restart:
        sched = _build_cosine_scheduler(n_rounds)
        for r in range(n_rounds):
            sample = sched.sample(
                outer_cycle_id=0, round_in_cycle=r, target_round=r
            )
            betas[r] = float(1.0 - float(sample.n_cap))

    out = np.empty((n_records, 2), dtype=np.float64)
    for i in range(n_records):
        bundle, _ = _build_initial_state_and_condition(
            adapter,
            seed=int(seed),
            nfe=int(nfe),
            batch_id=f"r5a-batch-{seed}",
            sample_id=f"r5a-{seed}-{i}",
        )
        # ``_solve_one`` consumes one beta per restart; the last round has
        # none, so index r is used for the restart that follows round r.
        out[i] = _solve_one(
            adapter,
            bundle,
            seed=int(seed),
            nfe=int(nfe),
            n_rounds=int(n_rounds),
            betas=betas if restart else None,
            restart=restart,
            record_key=(
                f"{seed}-{i}" if (restart and seed_scope == "record") else ""
            ),
            restart_mode=restart_mode,
            align_t0=align_t0,
        )
    return out


def _trace_cov(x: np.ndarray) -> float:
    """``Tr(Cov)`` of a ``(n, 2)`` endpoint cloud."""
    return float(np.asarray(x, dtype=np.float64).var(axis=0, ddof=1).sum())


def _paired_t(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    """Paired t on ``a - b`` over seeds (two-sided)."""
    from scipy import stats

    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    n = int(d.size)
    mean = float(d.mean()) if n else 0.0
    sd = float(d.std(ddof=1)) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    if se > 0:
        t = mean / se
        p = float(2.0 * stats.t.sf(abs(t), df=n - 1))
    else:
        t, p = float("nan"), 1.0
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "se": se,
        "t": float(t),
        "df": float(n - 1),
        "p": p,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    ap.add_argument("--n-records", type=int, default=N_RECORDS)
    ap.add_argument("--nfe", type=int, default=NFE)
    ap.add_argument("--n-rounds", type=int, default=N_ROUNDS)
    ap.add_argument(
        "--skip-published-baseline",
        action="store_true",
        help="skip the _run_baseline cross-check (saves ~half the wall clock)",
    )
    ap.add_argument(
        "--arms",
        nargs="+",
        default=list(DEFAULT_ARMS),
        choices=list(ARM_SPECS),
        help=(
            "restart arms to run (see ARM_SPECS). 'convex_policy' is the "
            "shipped operator with the shipped seeding (record-invariant "
            "fresh draw, GAP-80 §3); 'convex_record' scopes the draw to the "
            "record; 'vp_record' makes the blend variance-preserving; "
            "'aligned_record' integrates each post-restart round from "
            "t = memory instead of t = 0. All are diagnostics: the shipped "
            "convention is unchanged."
        ),
    )
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    arms = list(args.arms)
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []

    for seed in args.seeds:
        t0 = time.perf_counter()
        base = run_protocol_arm(
            seed=seed,
            n_records=args.n_records,
            nfe=args.nfe,
            n_rounds=1,
            restart=False,
        )
        w2_base = _wasserstein_2d(base, TARGET, seed)
        cov_base = _trace_cov(base)
        row: dict[str, Any] = {
            "seed": int(seed),
            "n_records": int(args.n_records),
            "w2_baseline_protocol": w2_base,
            "trace_cov_baseline": cov_base,
            "wall_s": 0.0,
        }
        for label in arms:
            spec = ARM_SPECS[label]
            rest = run_protocol_arm(
                seed=seed,
                n_records=args.n_records,
                nfe=args.nfe,
                n_rounds=args.n_rounds,
                restart=True,
                seed_scope=spec["seed_scope"],
                restart_mode=spec["restart_mode"],
                align_t0=spec["align_t0"],
            )
            w2_rest = _wasserstein_2d(rest, TARGET, seed)
            row[f"w2_{label}"] = w2_rest
            row[f"delta_{label}"] = w2_rest - w2_base
            row[f"delta_rel_{label}"] = (
                (w2_rest - w2_base) / w2_base if w2_base else float("nan")
            )
            row[f"var_ratio_{label}"] = (
                _trace_cov(rest) / cov_base if cov_base > 0 else float("nan")
            )
        row["wall_s"] = float(time.perf_counter() - t0)
        if not args.skip_published_baseline:
            metrics, wall = _run_baseline(
                target=TARGET,
                weights_path=Path("data/twodim_fm_two_moons.npz"),
                seed=int(seed),
                n_samples=int(args.n_records),
                trajectories_per_round=50,
                endpoints_per_trajectory=max(1, args.n_records // 50),
            )
            # `_run_baseline` returns the single round's metrics; that W2 is
            # the cell's published baseline value.
            row["w2_baseline_published"] = float(metrics[-1]["w2"])
            row["wall_published_s"] = float(wall)
        rows.append(row)
        bits = " ".join(
            f"{label} {100 * row[f'delta_rel_{label}']:+.2f} %"
            for label in arms
        )
        print(
            f"[r5a] seed {seed}: baseline {w2_base:.5f} | {bits} "
            f"({row['wall_s']:.1f}s)",
            flush=True,
        )

    w2b = np.array([r["w2_baseline_protocol"] for r in rows], dtype=np.float64)
    published = [r["w2_baseline_published"] for r in rows if "w2_baseline_published" in r]
    summary = {
        "spec": "docs/audit/gap80-r5a-harness.md §8",
        "target": TARGET,
        "nfe": int(args.nfe),
        "n_rounds": int(args.n_rounds),
        "n_records": int(args.n_records),
        "seeds": [int(s) for s in args.seeds],
        "w2_baseline_mean": float(w2b.mean()),
        "arms": {},
        "rows": rows,
        "wall_s": float(time.perf_counter() - started),
    }
    for label in arms:
        w2r = np.array([r[f"w2_{label}"] for r in rows], dtype=np.float64)
        vr = np.array([r[f"var_ratio_{label}"] for r in rows], dtype=np.float64)
        summary["arms"][label] = {
            "w2_mean": float(w2r.mean()),
            "paired": _paired_t(w2r, w2b),
            "var_ratio_mean": float(vr.mean()),
        }
    if published:
        pub = np.asarray(published, dtype=np.float64)
        summary["w2_baseline_published_mean"] = float(pub.mean())
        # The protocol baseline must land on the published baseline's scale,
        # otherwise the restart arm is being compared to a different sampler.
        summary["protocol_vs_published"] = _paired_t(w2b, pub)
    out = args.out / "r5a_restart.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    for label in arms:
        arm = summary["arms"][label]
        print(
            f"[r5a] restart/{label}: {arm['w2_mean']:.5f} vs baseline "
            f"{summary['w2_baseline_mean']:.5f}; t={arm['paired']['t']:.3f} "
            f"p={arm['paired']['p']:.4f}; var_ratio={arm['var_ratio_mean']:.3f}"
        )
    print(f"[r5a] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
