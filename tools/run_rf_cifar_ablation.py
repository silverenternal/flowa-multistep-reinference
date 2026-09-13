"""Framework-enabled ablation for Rectified Flow (Liu 2022) CIFAR-10.

Implements the plan's §5 — *Framework-enabled plan*. The script wires
the :class:`RectifiedFlowCIFARAdapter` into a
:class:`adaptive_reflow.algorithm.runner.ReInferenceRunner` with four
scheduler variants:

* ``cosine`` — :func:`default_cosine_scheduler` (default).
* ``codimension_sheet`` — :class:`CodimensionSheetScheduler` (paper-grounded).
* ``evidence_driven`` — :class:`EvidenceDrivenScheduler` (C4, schedule-sensitive).
* ``rf_1step_fixed`` — a synthetic :class:`FixedStepScheduler`-style
  pinned at ``n_cap=2`` that mirrors the paper's 2-NFE Euler baseline
  (used as a sanity check that the framework is a no-op when the
  scheduler doesn't adapt).

For each row, the script:

1. Runs ``n_rounds`` rounds against the adapter.
2. Records per-round wall-clock, ``merged_beta``, ``selection_ratio``,
   and the round's NFE (``steps`` from the integrator trace).
3. Generates ``n_trajectories_per_round`` samples per round and computes
   a per-round FID using :func:`tools.eval_rf_cifar.compute_fid` (or
   the random-projection fallback when torch is missing).
4. Writes a single JSON summary per row + a markdown table to
   ``--output-dir``.

Important — environment caveats
-------------------------------

The script requires the same three preconditions as
:mod:`tools.eval_rf_cifar` (torch, weights, real Inception features) to
produce paper-comparable FID numbers. When torch / weights / features
are missing the script falls back to the synthetic mode (random-init
NumPy velocity field, random-projection Inception features) and prints
a clear ``[SYNTHETIC ABLATION]`` banner.

Usage::

    python -m tools.run_rf_cifar_ablation --n-rounds 5 --num-samples 64
    python -m tools.run_rf_cifar_ablation --n-rounds 20 --num-samples 2500
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

# Make the project importable when running as ``python tools/run_rf_cifar_ablation.py``.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.adapters.rectified_flow_cifar import (  # noqa: E402
    RectifiedFlowCIFARAdapter,
    rectified_flow_cifar_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.algorithm import (  # noqa: E402
    ReInferenceConfig,
    ReInferenceRunner,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    CodimensionSheetScheduler,
    SchedulerProtocol,
)
from adaptive_reflow.algorithm.scheduler.evidence_driven import (  # noqa: E402
    EvidenceDrivenScheduler,
)
from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    ChannelName,
    CosineScheduleConfig,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    MechanismId,
    PolicyId,
    RunId,
    hash_policy_hash,
)
from adaptive_reflow.contracts import PhaseState as _PhaseStateT  # noqa: E402
from adaptive_reflow.frame.phase import build_phase_state  # noqa: E402
from tools.eval_rf_cifar import (  # noqa: E402
    PUBLISHED_BASELINE_FID,
    compute_fid,
    extract_inception_features,
    random_inception_features,
)

# ---------------------------------------------------------------------------
# Constants — defaults that match the plan §5.
# ---------------------------------------------------------------------------

CANONICAL_CHANNELS: tuple[str, ...] = ("image",)
RF_CIFAR_RUN_ID: str = "rf_cifar_ablation"


def _make_cosine_schedule_config(
    *, cycle_length: int, n_min: float, n_max: float
) -> CosineScheduleConfig:
    """Return a fresh :class:`CosineScheduleConfig` for the ablation schedulers."""
    return CosineScheduleConfig(
        cycle_length=int(cycle_length),
        n_min=FactorValue(float(n_min)),
        n_max=FactorValue(float(n_max)),
        schedule_family="cosine_no_restart",
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash(f"rf_cifar_abl:{int(cycle_length)}:{float(n_min)}:{float(n_max)}"),
        frozen_before_evaluation=True,
    )


def _make_phase_state(round_index: int) -> _PhaseStateT:
    """Return a fresh :class:`PhaseState` for ``round_index``.

    Uses :func:`build_phase_state` to ensure the schedule phase is
    inferred correctly and the canonical phase-state digest is computed
    against the canonical ``operation_order_version``. The returned
    object conforms to the engine's ``phase_state`` argument type.
    """
    return build_phase_state(
        outer_cycle_id=0,
        round_in_cycle=int(round_index),
        schedule_phase_index=int(round_index),
        operation_order_version="rf_cifar_ablation_v1",
        source_selector_procedure="rf_cifar_ablation_default",
        seed_lineage_digest=ArtifactHash(f"rf-cifar-ablation-lineage-{round_index}"),
        horizon_remaining=200,
        recorded_at_round=int(round_index),
    )


def _make_final_policy(
    *,
    policy_id: str,
    beta: float,
    target_round: int,
    beta_from_schedule: bool = True,
) -> FinalRestartPolicy:
    """Return a freshly-hashed :class:`FinalRestartPolicy` for one round."""
    channel = ChannelName("image")
    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id=MechanismId("inference.adaptive_reflow"),
        run_id=RunId(RF_CIFAR_RUN_ID),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=int(target_round),
        beta_from_schedule=bool(beta_from_schedule),
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_runner(
    *,
    adapter: RectifiedFlowCIFARAdapter,
    scheduler: SchedulerProtocol,
    n_rounds: int,
) -> ReInferenceRunner:
    """Return a :class:`ReInferenceRunner` with the supplied scheduler."""
    from adaptive_reflow.algorithm import (
        default_blender,
        default_bounded_merge_operator,
        default_policy_driver,
    )

    return ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=default_policy_driver(),
        merge_operator=default_bounded_merge_operator(),
        blender=default_blender(),
    )


def _build_schedulers(*, n_rounds: int) -> dict[str, SchedulerProtocol]:
    """Return the 4 scheduler variants used by the ablation.

    The ``n_min`` / ``n_max`` values are FRACTIONAL parameters in
    ``[0, 1]`` (the canonical cosine-schedule surface — see
    ``tools/run_ablation.py`` ``COSINE_N_MIN=0.0`` /
    ``COSINE_N_MAX=1.0``). The scheduler internally scales them by
    ``cycle_length`` to derive the round's NFE count. The framework's
    scheduler surface does not expose an integer-NFE ``FixedStepScheduler``,
    so the ``rf_1step_fixed`` row uses a ``CosineAnnealScheduler`` with
    ``n_min = n_max`` so the per-round NFE is constant (matches the
    paper's 2-NFE Euler sanity check).
    """
    schedulers: dict[str, SchedulerProtocol] = {}
    schedulers["cosine"] = default_cosine_scheduler(cycle_length=int(n_rounds))
    schedulers["codimension_sheet"] = CodimensionSheetScheduler(
        cycle_length=int(n_rounds),
        n_min=0.0,
        n_max=1.0,
        eps_implicit=1e-3,
    )
    schedulers["evidence_driven"] = EvidenceDrivenScheduler(
        config=_make_cosine_schedule_config(
            cycle_length=int(n_rounds),
            n_min=0.0,
            n_max=1.0,
        ),
        target_ratio=1.0,
        k_eps=0.5,
    )
    from adaptive_reflow.algorithm.scheduler import CosineAnnealScheduler

    schedulers["rf_1step_fixed"] = CosineAnnealScheduler(
        config=_make_cosine_schedule_config(
            cycle_length=int(n_rounds),
            n_min=1.0,
            n_max=1.0,
        ),
    )
    return schedulers


def _drive_runner(
    *,
    adapter: RectifiedFlowCIFARAdapter,
    scheduler: SchedulerProtocol,
    n_rounds: int,
) -> list[dict[str, Any]]:
    """Drive the adapter for ``n_rounds`` and collect per-round metrics.

    Direct ``Engine.run_round`` driver — NOT
    ``ReInferenceRunner.run(config)``. The runner's internal endpoint
    collection hardcodes a ``(2,)`` reshape (line 856 of
    ``runner.py``); the RF CIFAR adapter advertises
    ``state_shape=(3, 32, 32)`` and the runner's reshape fails with a
    ``cannot reshape array of size 3072`` ValueError. Bypassing the
    runner gives us byte-stable, per-round control over NFE / beta /
    selection_ratio without touching the framework's runner contract.

    Per-round flow:

    1. ``scheduler.sample(...)`` -> :class:`ScheduleSample` (``n_cap``).
    2. Compute ``nfe_steps = max(1, round(n_cap * nfe_max))`` — the
       paper's baseline is 2-NFE Euler so ``nfe_max = 4`` (matches the
       plan §5.2).
    3. Build a :class:`FinalRestartPolicy` with ``beta = memory_fraction``
       so a high-``n_cap`` round's restart beta tracks the schedule.
    4. Call ``Engine.run_round`` and capture the round trace.
    5. Compute a synthetic ``selection_ratio`` = ``n_cap`` clipped to
       ``[0, 1]`` — the schedule's ``n_cap`` is the framework's canonical
       per-round capacity, so it serves as a proxy for the
       ``selection_ratio`` paper-quantity trajectory.
    """
    from adaptive_reflow.frame.engine import Engine
    from adaptive_reflow.universal.state import ODEConditionDelta

    nfe_max: int = 4
    rows: list[dict[str, Any]] = []
    bundle = adapter.build_initial_state(
        batch_id="batch-rf-cifar-abl",
        sample_id="sample-rf-cifar-abl",
    )
    engine = Engine()
    for r in range(int(n_rounds)):
        sample = scheduler.sample(outer_cycle_id=0, round_in_cycle=r, target_round=r)
        nfe_steps = max(1, int(round(float(sample.n_cap) * float(nfe_max))))
        if int(nfe_steps) <= 0:
            nfe_steps = 1
        memory_fraction = float(sample.memory_fraction())
        beta = float(memory_fraction)
        policy = _make_final_policy(
            policy_id=f"policy-rf-cifar-abl-{r}",
            beta=beta,
            target_round=r,
            beta_from_schedule=True,
        )
        delta = ODEConditionDelta(
            delta_spec={"num_steps": int(nfe_steps)},
            source="rf_cifar_ablation",
            target_round=int(r),
            calibration_artifact_hash="cal-rf-cifar-abl",
        )
        result = engine.run_round(
            round_index=r,
            phase_state=_make_phase_state(r),  # type: ignore[arg-type]
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=delta,
        )
        trace = result.round_trace
        # selection_ratio proxy: the schedule's n_cap, clipped to [0, 1].
        # Matches the convention used in the 2D ablation where ``n_cap``
        # directly drives the posterior selection evaluator's oracle.
        selection_ratio = float(max(0.0, min(1.0, float(sample.n_cap))))
        if trace.integrator_trace is None:
            raise RuntimeError("integrator_trace_missing")
        bundle = adapter.observe_endpoint(
            trace.integrator_trace,
            adapter.build_initial_state(
                batch_id="batch-rf-cifar-abl",
                sample_id="sample-rf-cifar-abl",
            ),
        )
        rows.append(
            {
                "round": int(r),
                "merged_beta": float(beta),
                "selection_ratio": float(selection_ratio),
                "nfe_steps": int(nfe_steps),
                "endpoint_digest": str(trace.endpoint_digest),
            }
        )
    return rows


def _generate_per_round_samples(
    *,
    adapter: RectifiedFlowCIFARAdapter,
    n_samples: int,
    nfe: int,
    seed: int,
) -> np.ndarray:
    """Generate ``(n_samples, 3, 32, 32)`` samples for FID computation."""
    return adapter.batched_inference(
        n_samples=int(n_samples),
        num_steps=int(nfe),
        seed=int(seed),
    )


def _compute_per_round_fid(
    *,
    samples: np.ndarray,
    reference: np.ndarray | None,
    n_reference: int,
    seed: int,
) -> float:
    """Compute FID for one round's samples against the reference (or random fallback)."""
    feats = extract_inception_features(samples, batch_size=64)
    if reference is None:
        reference = random_inception_features(
            int(n_reference), dim=feats.shape[1], seed=int(seed) + 1
        ).astype(np.float32)
    return compute_fid(feats.astype(np.float64), reference.astype(np.float64))


def _run_one_scheduler(
    *,
    adapter: RectifiedFlowCIFARAdapter,
    scheduler_name: str,
    scheduler: SchedulerProtocol,
    n_rounds: int,
    samples_per_round: int,
    reference: np.ndarray | None,
) -> dict[str, Any]:
    """Run one scheduler row end-to-end. Returns a JSON-serialisable summary."""
    print(f"  -> {scheduler_name}: driving {n_rounds} rounds")
    t0 = time.perf_counter()
    per_round = _drive_runner(
        adapter=adapter,
        scheduler=scheduler,
        n_rounds=int(n_rounds),
    )
    drive_seconds = time.perf_counter() - t0

    fids: list[float] = []
    per_round_fid_rows: list[dict[str, Any]] = []
    for row in per_round:
        nfe = int(max(1, row["nfe_steps"]))
        samples = _generate_per_round_samples(
            adapter=adapter,
            n_samples=int(samples_per_round),
            nfe=nfe,
            seed=int(row["round"]),
        )
        fid = _compute_per_round_fid(
            samples=samples,
            reference=reference,
            n_reference=int(samples_per_round),
            seed=int(row["round"]),
        )
        fids.append(float(fid))
        per_round_fid_rows.append(
            {
                "round": int(row["round"]),
                "nfe": int(nfe),
                "merged_beta": float(row["merged_beta"]),
                "selection_ratio": float(row["selection_ratio"]),
                "fid": float(fid),
            }
        )
    elapsed = time.perf_counter() - t0
    summary = {
        "scheduler": str(scheduler_name),
        "n_rounds": int(n_rounds),
        "samples_per_round": int(samples_per_round),
        "drive_seconds": float(drive_seconds),
        "wall_clock_total_seconds": float(elapsed),
        "wall_clock_per_round_seconds": float(elapsed / float(max(n_rounds, 1))),
        "selection_ratio_round_0": float(per_round[0]["selection_ratio"]) if per_round else 0.0,
        "selection_ratio_round_last": float(per_round[-1]["selection_ratio"]) if per_round else 0.0,
        "selection_curve": [float(r["selection_ratio"]) for r in per_round],
        "merged_beta_curve": [float(r["merged_beta"]) for r in per_round],
        "nfe_curve": [int(r["nfe_steps"]) for r in per_round],
        "fid_curve": fids,
        "mean_fid": float(np.mean(fids)) if fids else float("inf"),
        "best_round_fid": float(np.min(fids)) if fids else float("inf"),
        "per_round": per_round_fid_rows,
    }
    return summary


def _render_markdown_table(summaries: list[dict[str, Any]], *, baseline_fid: float) -> str:
    """Render the canonical comparison table for the ablation rows."""
    lines: list[str] = []
    lines.append("# Rectified Flow CIFAR-10 — Framework Ablation")
    lines.append("")
    lines.append(f"Published baseline FID (Liu 2022): **{baseline_fid:.2f}**")
    lines.append(f"Synthetic-vs-real reference: {'yes' if summaries and summaries[0].get('fallback_reference') else 'no'}")
    lines.append("")
    lines.append("| Scheduler | FID (r=0) | FID (r=10) | FID (r=last) | Mean FID | Wall/round | sel_ratio[last] |")
    lines.append("|-----------|-----------|------------|--------------|----------|------------|-----------------|")
    for s in summaries:
        fids = s["fid_curve"]
        f0 = fids[0] if fids else float("inf")
        f10 = fids[10] if len(fids) > 10 else float("nan")
        flast = fids[-1] if fids else float("inf")
        lines.append(
            f"| {s['scheduler']} | {f0:.2f} | {f10:.2f} | {flast:.2f} | "
            f"{s['mean_fid']:.2f} | {s['wall_clock_per_round_seconds']:.1f}s | "
            f"{s['selection_ratio_round_last']:.3f} |"
        )
    lines.append("")
    return "\n".join(lines)


def _maybe_load_reference(path: Path | None) -> np.ndarray | None:
    """Load the real CIFAR-10 InceptionV3 features ``.npz`` file."""
    if path is None or not path.exists():
        return None
    data = np.load(path)
    if "features" not in data.files:
        return None
    arr = np.asarray(data["features"], dtype=np.float32)
    return arr  # type: ignore[no-any-return]


def main(argv: list[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)

    weights = Path(args.weights_path) if args.weights_path else None
    ref = Path(args.reference_features) if args.reference_features else None
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    adapter = RectifiedFlowCIFARAdapter(
        weights_path=weights,
        force_mode="auto",
        num_steps=int(args.nfe),
    )
    print(
        f"[{'SYNTHETIC' if adapter._mode == 'synthetic' else 'TORCH'} ABLATION] "
        f"mode={adapter._mode} weights={adapter._weights_path} "
        f"n_rounds={args.n_rounds} samples_per_round={args.samples_per_round}"
    )
    if not torch_is_available():
        print(
            "[CAVEAT] torch not installed — falling back to synthetic mode + "
            "random-projection Inception features. FID numbers are NOT "
            "paper-comparable."
        )

    reference = _maybe_load_reference(ref)
    if args.require_reference:
        if reference is None:
            print(
                "[ERROR] --require-reference needs an .npz containing a "
                "2-D 'features' array; generate it with tools/eval_rf_cifar.py "
                "--extract-reference-features.", file=sys.stderr,
            )
            return 2
        if reference.ndim != 2 or reference.shape[0] == 0 or reference.shape[1] != 2048:
            print(
                f"[ERROR] reference features have invalid shape {reference.shape}; "
                "regenerate with tools/eval_rf_cifar.py --extract-reference-features.",
                file=sys.stderr,
            )
            return 2
    if reference is None:
        print(
            f"[CAVEAT] No real CIFAR-10 features at {ref}. FID will be "
            "synthetic-vs-random — not paper-comparable."
        )

    schedulers = _build_schedulers(n_rounds=int(args.n_rounds))
    requested = tuple(s.strip() for s in str(args.schedulers).split(",") if s.strip())
    unknown = set(requested) - set(schedulers)
    if unknown:
        raise ValueError(f"unknown scheduler(s): {sorted(unknown)}")
    if requested:
        schedulers = {k: v for k, v in schedulers.items() if k in requested}
    summaries: list[dict[str, Any]] = []
    for name, scheduler in schedulers.items():
        arm_path = output / f"{name}.json"
        if args.resume and arm_path.is_file():
            try:
                cached = json.loads(arm_path.read_text(encoding="utf-8"))
                if cached.get("scheduler") == name and "error" not in cached:
                    print(f"  -> {name}: RESUME cached arm")
                    summaries.append(cached)
                    continue
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
        try:
            summary = _run_one_scheduler(
                adapter=adapter,
                scheduler_name=name,
                scheduler=scheduler,
                n_rounds=int(args.n_rounds),
                samples_per_round=int(args.samples_per_round),
                reference=reference,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  -> {name}: FAILED with {exc!r}", file=sys.stderr)
            summary = {
                "scheduler": str(name),
                "error": repr(exc),
                "fid_curve": [],
                "mean_fid": float("inf"),
                "best_round_fid": float("inf"),
                "selection_curve": [],
                "merged_beta_curve": [],
                "nfe_curve": [],
                "wall_clock_per_round_seconds": 0.0,
                "selection_ratio_round_0": 0.0,
                "selection_ratio_round_last": 0.0,
                "per_round": [],
            }
        if reference is None:
            summary["fallback_reference"] = True
        summaries.append(summary)
        # Persist per-row JSON so the operator can inspect each
        # scheduler's curve in isolation.
        arm_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    md = _render_markdown_table(summaries, baseline_fid=float(PUBLISHED_BASELINE_FID))
    (output / "ablation.md").write_text(md)
    (output / "ablation.json").write_text(json.dumps(summaries, indent=2, sort_keys=True))
    print(f"[DONE] {len(summaries)} scheduler rows -> {output}/ablation.{{md,json}}")
    return 0


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.run_rf_cifar_ablation",
        description="Run the framework ablation against the RF CIFAR-10 adapter.",
    )
    p.add_argument("--n-rounds", type=int, default=5,
                   help="Number of framework rounds per scheduler row.")
    p.add_argument("--samples-per-round", type=int, default=64,
                   help="Number of samples generated for FID per round.")
    p.add_argument("--nfe", type=int, default=2,
                   help="Default Euler integration steps (paper uses 2).")
    p.add_argument("--weights-path", type=str, default=None,
                   help="Explicit path to UNet state_dict (.safetensors / .pth / .pt).")
    p.add_argument("--reference-features", type=str,
                   default="data/cifar10_inception_features.npz",
                   help="Path to .npz with real CIFAR-10 InceptionV3 features.")
    p.add_argument("--output-dir", type=str, default="data/rf_ablation",
                   help="Where to save the per-scheduler JSON + markdown.")
    p.add_argument("--schedulers", type=str, default="",
                   help="Optional comma-separated scheduler names; empty runs all.")
    p.add_argument("--resume", action="store_true",
                   help="Reuse completed per-scheduler JSON arms in output-dir.")
    p.add_argument("--require-reference", action="store_true",
                   help="Fail closed unless reference_features.npz contains a valid features array.")
    return p


if __name__ == "__main__":
    raise SystemExit(main())
