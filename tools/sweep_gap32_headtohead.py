#!/usr/bin/env python3
"""GAP-32 — external-method head-to-head on two additional cells.

The R6 cell (§7.8) is the only cell in the paper that compares FlowA against
*published external methods* rather than against its own vanilla baseline:
``vanilla`` + ``Fast-DLLM`` + ``AB-Cache`` + ``LeDiFlow`` at matched NFE.
GAP-32 extends that exact roster to two more cells so the "beats SOTA
accelerators" claim is not R6-only:

* **R5c** — MNIST FM (``adaptive_reflow.adapters.mnist_fm``), 784-dim pixels,
  the framework-internal Fréchet-projection FID metric. Checkpoint
  ``data/mnist_fm/w16e1_5k.ckpt.npz`` — the GAP-35 matched-architecture,
  **non-smoke** checkpoint that is framework-WINS vs a tuned baseline at
  matched NFE (``docs/audit/gap35-cross-domain.md``).
* **R4/R5** — 2D FM ``eight_gaussians``
  (``adaptive_reflow.adapters.twodim_fm``), the closed-form 2D Wasserstein-2
  metric. This is the 2D FM ablation cell that is framework-WINS
  (``docs/audit/sweep_eval/p1-restore-r4-r5.md``).

Design (one protocol, cell-parameterised)
-----------------------------------------

Five arms:

* ``vanilla``  — single-pass Euler at ``--nfe`` macro-steps (the reference).
* ``fastdllm`` — confidence-aware Euler + midpoint verifier
  (``arXiv:2505.22618``), continuous-FM analog.
* ``abcache``  — 2-step Adams-Bashforth cache reuse (``arXiv:2504.10540``).
* ``lediflow`` — learned-prior-shifted Euler (``arXiv:2505.20723``).
* ``flowa``    — the framework restart-blend loop (cell-canonical config:
  4 rounds / cosine ramp / β=0.5 / restart from round 1 — the same recipe as
  the R5c headline driver ``scripts/wave191_p3_mnist_sweep.py`` and the 2D
  ``multi_round_constant_beta_05`` ablation row).

**NFE accounting.** The three external arms each spend ``--nfe`` macro
velocity evaluations (plus their own verifier / cache overhead, reported in
``solver_stats``). The framework arm follows the canonical R5c recipe: the
per-round cap is ``--nfe // n_rounds`` and the cosine ramp then reduces the
later rounds, so its *total* evaluation count is roughly ``--nfe / 2``
(e.g. 50 -> ``[12, 9, 3, 1]`` = 25 for the 4-round MNIST cell). The
framework is therefore NFE-**efficient** relative to the single-pass
external arms, not NFE-matched; the per-arm ``total_nfe`` is recorded in
``solver_stats`` and the aggregate JSON.

The three external solvers are the generic batched ports in
:mod:`tools.gap32_external_solvers` (same algorithms as the R6
``tools/{fastdllm,abcache,lediflow}_solver.py``, minus the LineageFlow
simplex surface). The framework arm drives the real adapter through the
:class:`FlowMatchingODEAdapter` protocol (``build_initial_state`` →
``apply_restart_distribution`` → ``solve_ode`` → ``observe_endpoint``), and
all four adapters now expose an additive ``euler`` integrator so every arm
integrates in the same first-order family at matched NFE.

**Seed matching.** Every arm for sample ``i`` starts from the *same* ``x0``:
the adapter's own ``build_initial_state`` draw for ``(batch_id, "s{i:05d}")``
where ``batch_id`` encodes the run seed, so each seed is an independent draw
and the arms are paired by construction.

Statistics (R6-style, §7.8)
---------------------------

The unit of replication is the **seed** (``--seeds``, default 42/43/44 — the
R6 convention). For each ``(cell, seed, arm)`` the driver records one headline
metric value (FID / W² over all ``N`` samples). Across seeds the per-arm
difference vs ``vanilla`` is tested with a two-sided **paired** t-test (the
arms are seed-matched) and Bonferroni-corrected across the four non-vanilla
arms (``α = 0.05/4``). The FlowA-vs-external contrasts are additionally
Bonferroni-corrected across the three external arms (``α = 0.05/3``).

Evidence: ``verification_outputs/gap32-headtohead/`` (``aggregate.{json,csv}``
+ per-cell ``seed<NN>/`` artefacts). Audit: ``docs/audit/gap32-headtohead.md``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import gap32_external_solvers as ext  # noqa: E402

from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    ChannelName,
    FactorValue,
    LedgerRowId,
    PolicyId,
    RunId,
    hash_policy_hash,
)
from adaptive_reflow.contracts.authority import (  # noqa: E402
    FinalRestartPolicy,
    validate_final_restart_policy,
)
from adaptive_reflow.universal.state import ODEConditionDelta  # noqa: E402

SCHEMA_VERSION: str = "gap32_headtohead_v2"

#: Canonical arm order for tables / CSVs.
ARM_ORDER: tuple[str, ...] = ("vanilla", "fastdllm", "abcache", "lediflow", "flowa")
#: Non-vanilla arms (the Bonferroni family for the "vs vanilla" contrasts).
COMPARISON_ARMS: tuple[str, ...] = ("fastdllm", "abcache", "lediflow", "flowa")
#: External arms (the Bonferroni family for the "FlowA vs external" contrasts).
EXTERNAL_ONLY_ARMS: tuple[str, ...] = ("fastdllm", "abcache", "lediflow")


# ---------------------------------------------------------------------------
# Cell specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellSpec:
    """Everything the driver needs to run one cell."""

    name: str
    channel: str
    state_shape: tuple[int, ...]
    clamp: float
    default_ckpt: Path
    n_rounds: int
    restart_from_round: int  # 1 = blend rounds > 0 (the R5c/R5b recipe)
    framework_max_steps: int
    metric: str  # "frechet_projection" | "wasserstein2"
    default_n_samples: int
    reference: str


CELL_SPECS: dict[str, CellSpec] = {
    "mnist_fm": CellSpec(
        name="mnist_fm",
        channel="x",
        state_shape=(784,),
        clamp=1.0,
        # GAP-35 matched-architecture, NON-smoke, framework-WINS checkpoint.
        default_ckpt=REPO_ROOT / "data" / "mnist_fm" / "w16e1_5k.ckpt.npz",
        n_rounds=4,
        restart_from_round=1,
        framework_max_steps=12,  # 50 / 4 (wave191 matched-NFE anchor)
        metric="frechet_projection",
        default_n_samples=1000,
        reference="MNIST test (10K digits, framework-internal 784->128 projection)",
    ),
    "twodim_eight_gaussians": CellSpec(
        name="twodim_eight_gaussians",
        channel="xy",
        state_shape=(2,),
        clamp=5.0,
        default_ckpt=REPO_ROOT / "data" / "twodim_fm_eight_gaussians.npz",
        n_rounds=4,
        restart_from_round=1,
        framework_max_steps=12,  # 50 / 4 (matched-NFE anchor, mirrors R5c)
        metric="wasserstein2",
        default_n_samples=1000,
        reference="Analytic eight-gaussians 2D target (closed-form sampler)",
    ),
}


# ---------------------------------------------------------------------------
# Adapter + velocity-field construction
# ---------------------------------------------------------------------------


def build_adapter(cell: CellSpec, ckpt: Path, nfe: int, device: str) -> Any:
    """Construct the cell's adapter with an **Euler** integrator (matched NFE)."""
    if cell.name == "mnist_fm":
        from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter

        return MnistFmAdapter(
            weights_path=ckpt, integrator="euler", num_steps=int(nfe)
        )
    if cell.name == "twodim_eight_gaussians":
        from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

        return TwoDimFMAdapter(
            weights_path=ckpt,
            target="eight_gaussians",
            integrator="euler",
            num_steps=int(nfe),
        )
    raise ValueError(f"unknown_cell:{cell.name}")


def build_velocity_field(cell: CellSpec, adapter: Any) -> ext.VelocityField:
    """Return a batched ``velocity_field(x, t)`` over the cell's surface."""
    if cell.name == "mnist_fm":
        from adaptive_reflow.adapters.mnist_fm import _unet_evaluate

        weights = adapter._weights  # noqa: SLF001

        def _vf(x: np.ndarray, t: float) -> np.ndarray:
            return np.asarray(_unet_evaluate(weights, x, float(t)), dtype=np.float64)

        return _vf

    if cell.name == "twodim_eight_gaussians":
        from adaptive_reflow.adapters.twodim_fm import _velocity_field

        weights = adapter._weights  # noqa: SLF001

        def _vf(x: np.ndarray, t: float) -> np.ndarray:
            return np.asarray(_velocity_field(weights, x, float(t)), dtype=np.float64)

        return _vf

    raise ValueError(f"unknown_cell:{cell.name}")


def make_project(cell: CellSpec) -> ext.Project:
    """Return the cell's domain projection (coordinate clamp)."""
    lo, hi = -float(cell.clamp), float(cell.clamp)

    def _project(x: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(x, dtype=np.float64), lo, hi)

    return _project


# ---------------------------------------------------------------------------
# Shared x0 (seed matching)
# ---------------------------------------------------------------------------


def shared_x0(
    cell: CellSpec, adapter: Any, *, batch_id: str, n_samples: int
) -> np.ndarray:
    """Draw the per-sample ``x0`` all arms share.

    Reads the adapter's own ``build_initial_state`` native state so the
    framework arm (which calls ``build_initial_state`` internally) and the
    external arms start from the *identical* ``x0``.
    """
    draws: list[np.ndarray] = []
    for i in range(int(n_samples)):
        bundle = adapter.build_initial_state(
            batch_id=str(batch_id), sample_id=f"s{i:05d}"
        )
        entry = adapter._native_states.get(bundle.native_state_digest, {})  # noqa: SLF001
        value = entry.get("x0", entry.get("x"))
        if value is None:
            raise RuntimeError(f"initial_state_missing_x0:sample={i}")
        draws.append(np.asarray(value, dtype=np.float64).reshape(cell.state_shape))
    return np.stack(draws, axis=0)


# ---------------------------------------------------------------------------
# Framework arm (restart-blend chaining via the adapter protocol)
# ---------------------------------------------------------------------------


def _cosine_per_round_steps(n_rounds: int, max_steps: int) -> list[int]:
    """Cosine-ramp per-round Euler step counts (mirrors wave191's helper)."""
    from adaptive_reflow.algorithm.scheduler import (
        CosineAnnealScheduler,
        CosineScheduleConfig,
    )

    config_hash = ArtifactHash(
        hashlib.sha256(
            repr(("cosine_no_restart", int(n_rounds), 0.0, 1.0)).encode("utf-8")
        ).hexdigest()
    )
    config = CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=int(n_rounds),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=config_hash,
        frozen_before_evaluation=True,
    )
    sched = CosineAnnealScheduler(config)
    out: list[int] = []
    for r in range(int(n_rounds)):
        sample = sched.sample(0, int(r), int(r))
        ns = int(round(float(sample.n_cap) * float(max_steps)))
        out.append(max(1, min(int(max_steps), ns)))
    return out


def _make_policy(
    *, cell: CellSpec, beta: float, round_idx: int, sample_index: int
) -> FinalRestartPolicy:
    """Build a hash-valid :class:`FinalRestartPolicy` for one round."""
    channel = ChannelName(cell.channel)
    policy_id = f"gap32-{cell.name}-s{sample_index}-r{round_idx}-b{beta:.2f}"
    draft = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(f"run-gap32-{cell.name}"),
        target_round=int(round_idx),
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=int(round_idx),
        beta_from_schedule=False,
    )
    sealed = replace(draft, policy_hash=hash_policy_hash(draft))
    ok, errors = validate_final_restart_policy(sealed)
    if not ok:
        raise AssertionError(f"invalid_policy:{errors!r}")
    return sealed


def run_framework_arm(
    *,
    cell: CellSpec,
    adapter: Any,
    n_samples: int,
    batch_id: str,
    run_seed: int,
    beta: float,
    num_steps_per_round: list[int],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Restart-blend chaining arm over the real adapter protocol.

    Each sample starts from the adapter's ``build_initial_state`` (the shared
    ``x0``). For round ``r``: if ``r >= cell.restart_from_round`` the previous
    endpoint is re-blended with fresh noise via ``apply_restart_distribution``;
    then ``solve_ode`` runs ``num_steps_per_round[r]`` Euler steps and
    ``observe_endpoint`` folds the trajectory into the next round's endpoint.
    """
    samples = np.empty((int(n_samples), *cell.state_shape), dtype=np.float64)
    t0 = time.perf_counter()
    for i in range(int(n_samples)):
        bundle = adapter.build_initial_state(
            batch_id=str(batch_id), sample_id=f"s{i:05d}"
        )
        for r, ns in enumerate(num_steps_per_round):
            if r >= int(cell.restart_from_round):
                policy = _make_policy(
                    cell=cell, beta=float(beta), round_idx=int(r), sample_index=int(i)
                )
                bundle = adapter.apply_restart_distribution(bundle, policy)
            condition = ODEConditionDelta(
                delta_spec={"t0": 0.0, "t1": 1.0, "num_steps": int(ns)},
                source=f"gap32_{cell.name}",
                target_round=int(r),
                calibration_artifact_hash="cal-gap32",
            )
            trace = adapter.solve_ode(
                bundle,
                condition,
                seed=int(run_seed) + int(i) + int(r) * 1_000_003,
            )
            bundle = adapter.observe_endpoint(trace, bundle)
        entry = adapter._native_states.get(bundle.native_state_digest, {})  # noqa: SLF001
        value = entry.get("x0", entry.get("x"))
        if value is None:
            raise RuntimeError(f"framework_endpoint_missing:sample={i}")
        samples[i] = np.asarray(value, dtype=np.float64).reshape(cell.state_shape)
    elapsed = time.perf_counter() - t0
    telemetry = {
        "num_steps_per_round": [int(x) for x in num_steps_per_round],
        "total_nfe_per_sample": int(sum(int(x) for x in num_steps_per_round)),
        "beta": float(beta),
        "n_rounds": int(len(num_steps_per_round)),
        "restart_from_round": int(cell.restart_from_round),
        "wall_sec": float(elapsed),
    }
    return samples, telemetry


# ---------------------------------------------------------------------------
# Metrics (lower is better)
# ---------------------------------------------------------------------------


class FrechetProjectionMetric:
    """MNIST framework-internal Fréchet-projection FID (784 -> 128)."""

    def __init__(self, cache_dir: Path) -> None:
        from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator

        evaluator = MnistFrechetProjectionEvaluator(cache_dir=Path(cache_dir))
        self.ref_features = np.asarray(evaluator._ref_features, dtype=np.float64)  # noqa: SLF001
        self.projection = np.asarray(evaluator._projection, dtype=np.float64)  # noqa: SLF001

    def score(self, samples: np.ndarray) -> float:
        from adaptive_reflow.eval.mnist_fid import _frechet_distance

        feats = np.asarray(samples, dtype=np.float64) @ self.projection
        return float(_frechet_distance(feats, self.ref_features))


class Wasserstein2Metric:
    """Closed-form 2D Wasserstein-2 ``sqrt(W2_x^2 + W2_y^2)`` vs the target."""

    def __init__(self, target: str, *, n_ref: int = 10000, seed: int = 0) -> None:
        from adaptive_reflow.eval.twodim_fm_evaluator import analytic_samples

        rng = np.random.default_rng(int(seed))
        self.ref = np.asarray(analytic_samples(target, int(n_ref), rng), dtype=np.float64)

    def score(self, samples: np.ndarray) -> float:
        from scipy.stats import wasserstein_distance

        arr = np.asarray(samples, dtype=np.float64)
        wx = float(wasserstein_distance(arr[:, 0], self.ref[:, 0]))
        wy = float(wasserstein_distance(arr[:, 1], self.ref[:, 1]))
        return float(math.sqrt(wx * wx + wy * wy))


def build_metric(cell: CellSpec, cache_dir: Path) -> Any:
    if cell.metric == "frechet_projection":
        return FrechetProjectionMetric(cache_dir)
    if cell.metric == "wasserstein2":
        return Wasserstein2Metric("eight_gaussians")
    raise ValueError(f"unknown_metric:{cell.metric}")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def paired_ttest(diff: np.ndarray) -> tuple[float, int, float]:
    """Two-sided paired t-test on the per-seed differences."""
    from scipy import stats

    n = int(diff.shape[0])
    if n < 2:
        return float("nan"), 0, float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return (float("inf") if mean != 0 else 0.0), n - 1, (0.0 if mean != 0 else 1.0)
    t = mean / (std / math.sqrt(n))
    p = float(2.0 * (1.0 - stats.t.cdf(abs(t), df=n - 1)))
    return float(t), n - 1, p


def cohens_dz(diff: np.ndarray) -> float:
    n = int(diff.shape[0])
    if n < 2:
        return float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return float("inf") if mean != 0 else 0.0
    return mean / std


# ---------------------------------------------------------------------------
# One (cell, seed) run
# ---------------------------------------------------------------------------


def run_one_seed(
    *,
    cell: CellSpec,
    metric: Any,
    adapter: Any,
    velocity_field: ext.VelocityField,
    project: ext.Project,
    n_samples: int,
    nfe: int,
    beta: float,
    seed: int,
    framework_max_steps: int,
    out_dir: Path,
    verbose: bool,
) -> dict[str, Any]:
    """Generate all five arms for one seed and return the per-arm metrics."""
    t0 = time.perf_counter()
    batch_id = f"gap32-{cell.name}-seed{seed}"
    x0 = shared_x0(cell, adapter, batch_id=batch_id, n_samples=n_samples)

    arm_samples: dict[str, np.ndarray] = {}
    arm_stats: dict[str, dict[str, Any]] = {}

    # External arms (vanilla + 3 published accelerators), matched NFE.
    for arm in ("vanilla", *EXTERNAL_ONLY_ARMS):
        t_arm = time.perf_counter()
        samples, stats = ext.run_external_arm(
            arm=arm,
            velocity_field=velocity_field,
            x0=x0,
            nfe=int(nfe),
            t_end=1.0,
            project=project,
        )
        arm_samples[arm] = np.asarray(samples, dtype=np.float64)
        arm_stats[arm] = {**stats, "wall_sec": float(time.perf_counter() - t_arm)}
        if verbose:
            print(
                f"[gap32] {cell.name} seed={seed} {arm}: {samples.shape} "
                f"eff_nfe={stats.get('effective_nfe')} "
                f"{time.perf_counter() - t_arm:.1f}s",
                flush=True,
            )

    # Framework arm (matched macro-NFE: n_rounds rounds x (nfe / n_rounds) steps).
    num_steps_per_round = _cosine_per_round_steps(cell.n_rounds, int(framework_max_steps))
    fw_samples, fw_stats = run_framework_arm(
        cell=cell,
        adapter=adapter,
        n_samples=int(n_samples),
        batch_id=batch_id,
        run_seed=int(seed),
        beta=float(beta),
        num_steps_per_round=num_steps_per_round,
    )
    arm_samples["flowa"] = fw_samples
    arm_stats["flowa"] = fw_stats
    if verbose:
        print(
            f"[gap32] {cell.name} seed={seed} flowa: {fw_samples.shape} "
            f"steps={num_steps_per_round} total_nfe={fw_stats['total_nfe_per_sample']} "
            f"{fw_stats['wall_sec']:.1f}s",
            flush=True,
        )

    # Save per-arm samples (local reproduction).
    seed_dir = out_dir / f"seed{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    for arm in ARM_ORDER:
        np.savez_compressed(seed_dir / f"{arm}_samples.npz", samples=arm_samples[arm])

    # Headline metric per arm (R6-style seed-level aggregate).
    metrics = {arm: float(metric.score(arm_samples[arm])) for arm in ARM_ORDER}

    result = {
        "seed": int(seed),
        "n_samples": int(n_samples),
        "nfe": int(nfe),
        "beta": float(beta),
        "metrics": metrics,
        "solver_stats": arm_stats,
        "wall_sec": float(time.perf_counter() - t0),
    }
    (seed_dir / "seed_summary.json").write_text(json.dumps(result, indent=2))
    if verbose:
        for arm in ARM_ORDER:
            print(
                f"[gap32] {cell.name} seed={seed} {arm}: {cell.metric}={metrics[arm]:.6f}",
                flush=True,
            )
    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool the per-seed metrics into R6-style paired statistics vs vanilla."""
    n_seeds = len(per_seed)
    out: dict[str, Any] = {
        "n_seeds": n_seeds,
        "seeds": [int(r["seed"]) for r in per_seed],
        "arms": {},
        "flowa_vs_external": {},
    }
    vanilla = np.asarray([float(r["metrics"]["vanilla"]) for r in per_seed])
    for arm in ARM_ORDER:
        vals = np.asarray([float(r["metrics"][arm]) for r in per_seed])
        diff = vals - vanilla
        t, df, p = paired_ttest(diff)
        delta_pct = float(
            (vals.mean() - vanilla.mean()) / max(abs(float(vanilla.mean())), 1e-9) * 100.0
        )
        entry: dict[str, Any] = {
            "metric_mean": float(vals.mean()),
            "metric_std": float(vals.std(ddof=1)) if n_seeds > 1 else 0.0,
            "metric_per_seed": [float(x) for x in vals],
            "delta_vs_vanilla_pct": delta_pct,
            "p_value_raw": float(p),
            "cohens_dz": float(cohens_dz(diff)),
            "t_stat": float(t),
            "df": int(df),
            "direction": (
                "framework_wins"
                if float(vals.mean()) < float(vanilla.mean())
                else ("framework_loses" if float(vals.mean()) > float(vanilla.mean()) else "tie")
            ),
        }
        if arm in COMPARISON_ARMS:
            p_bonf = float(min(p * len(COMPARISON_ARMS), 1.0))
            entry["p_value_bonferroni_vs_vanilla"] = p_bonf
            entry["bonferroni_significant_vs_vanilla"] = bool(p_bonf < 0.05)
        out["arms"][arm] = entry

    flowa = np.asarray([float(r["metrics"]["flowa"]) for r in per_seed])
    for arm in EXTERNAL_ONLY_ARMS:
        ext_vals = np.asarray([float(r["metrics"][arm]) for r in per_seed])
        diff = flowa - ext_vals
        t, df, p = paired_ttest(diff)
        p_bonf = float(min(p * len(EXTERNAL_ONLY_ARMS), 1.0))
        out["flowa_vs_external"][arm] = {
            "delta_flowa_minus_arm_pct": float(
                (flowa.mean() - ext_vals.mean())
                / max(abs(float(ext_vals.mean())), 1e-9)
                * 100.0
            ),
            "p_value_raw": float(p),
            "p_value_bonferroni": p_bonf,
            "bonferroni_significant": bool(p_bonf < 0.05),
            "cohens_dz": float(cohens_dz(diff)),
            "t_stat": float(t),
            "df": int(df),
            "flowa_wins_all_seeds": bool(np.all(diff < 0)),
        }
    return out


def write_csv(path: Path, cell: str, agg: dict[str, Any]) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "cell",
                "arm",
                "n_seeds",
                "metric_mean",
                "metric_std",
                "delta_vs_vanilla_pct",
                "cohens_dz",
                "t_stat",
                "df",
                "p_value_raw",
                "p_value_bonferroni",
                "bonferroni_significant",
                "direction",
            ]
        )
        for arm in ARM_ORDER:
            a = agg["arms"][arm]
            w.writerow(
                [
                    cell,
                    arm,
                    agg["n_seeds"],
                    f"{a['metric_mean']:.6f}",
                    f"{a['metric_std']:.6f}",
                    f"{a['delta_vs_vanilla_pct']:.6f}",
                    f"{a['cohens_dz']:.6f}",
                    f"{a['t_stat']:.6f}",
                    a["df"],
                    f"{a['p_value_raw']:.6g}",
                    f"{a.get('p_value_bonferroni_vs_vanilla', float('nan')):.6g}",
                    a.get("bonferroni_significant_vs_vanilla", ""),
                    a["direction"],
                ]
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cell", choices=sorted(CELL_SPECS), required=True)
    p.add_argument("--n-samples", type=int, default=None)
    p.add_argument("--nfe", type=int, default=50)
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument("--beta", type=float, default=0.5)
    p.add_argument("--ckpt", type=Path, default=None)
    p.add_argument("--device", default="cuda")
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=REPO_ROOT / "data" / "mnist_fm_train_cache",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "verification_outputs" / "gap32-headtohead",
    )
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    cell = CELL_SPECS[args.cell]
    n_samples = (
        int(args.n_samples)
        if args.n_samples is not None
        else int(cell.default_n_samples)
    )
    ckpt = Path(args.ckpt) if args.ckpt is not None else cell.default_ckpt
    if not ckpt.exists():
        raise SystemExit(f"checkpoint_not_found:{ckpt}")

    out_dir = Path(args.output_dir) / cell.name
    out_dir.mkdir(parents=True, exist_ok=True)

    ckpt_sha256 = hashlib.sha256(ckpt.read_bytes()).hexdigest()
    if not args.quiet:
        print(
            f"[gap32] cell={cell.name} ckpt={ckpt} sha256={ckpt_sha256[:16]} "
            f"N={n_samples} NFE={args.nfe} seeds={args.seeds} "
            f"rounds={cell.n_rounds} beta={args.beta}",
            flush=True,
        )

    adapter = build_adapter(cell, ckpt, int(args.nfe), args.device)
    velocity_field = build_velocity_field(cell, adapter)
    project = make_project(cell)
    metric = build_metric(cell, Path(args.cache_dir))

    # Matched macro-NFE: the framework spreads the baseline's ``nfe`` steps
    # across ``n_rounds`` cosine-ramped rounds (floor; the ramp is applied
    # inside ``_cosine_per_round_steps``).
    framework_max_steps = max(1, int(args.nfe) // int(cell.n_rounds))

    per_seed: list[dict[str, Any]] = []
    t_all = time.perf_counter()
    for seed in args.seeds:
        per_seed.append(
            run_one_seed(
                cell=cell,
                metric=metric,
                adapter=adapter,
                velocity_field=velocity_field,
                project=project,
                n_samples=n_samples,
                nfe=int(args.nfe),
                beta=float(args.beta),
                seed=int(seed),
                framework_max_steps=int(framework_max_steps),
                out_dir=out_dir,
                verbose=not args.quiet,
            )
        )
    wall = time.perf_counter() - t_all

    agg = aggregate(per_seed)
    agg.update(
        {
            "schema_version": SCHEMA_VERSION,
            "cell": cell.name,
            "checkpoint": str(ckpt.relative_to(REPO_ROOT))
            if ckpt.is_relative_to(REPO_ROOT)
            else str(ckpt),
            "checkpoint_sha256": ckpt_sha256,
            "n_samples": int(n_samples),
            "nfe": int(args.nfe),
            "beta": float(args.beta),
            "metric": cell.metric,
            "reference": cell.reference,
            "framework_config": {
                "n_rounds": int(cell.n_rounds),
                "restart_from_round": int(cell.restart_from_round),
                "framework_max_steps": int(framework_max_steps),
                "num_steps_per_round": _cosine_per_round_steps(
                    cell.n_rounds, int(framework_max_steps)
                ),
            },
            "integrator": "euler",
            "alpha_bonferroni_vs_vanilla": float(0.05 / len(COMPARISON_ARMS)),
            "alpha_bonferroni_flowa_vs_external": float(0.05 / len(EXTERNAL_ONLY_ARMS)),
            "wall_min": float(round(wall / 60.0, 2)),
            "per_seed": per_seed,
        }
    )
    (out_dir / "aggregate.json").write_text(json.dumps(agg, indent=2))
    write_csv(out_dir / "aggregate.csv", cell.name, agg)
    if not args.quiet:
        print(f"[gap32] wrote {out_dir / 'aggregate.json'} ({wall / 60:.1f} min)", flush=True)
        for arm in ARM_ORDER:
            a = agg["arms"][arm]
            print(
                f"[gap32] {cell.name} {arm}: {cell.metric}={a['metric_mean']:.6f} "
                f"Δ%={a['delta_vs_vanilla_pct']:+.3f} ({a['direction']}) "
                f"p_bonf={a.get('p_value_bonferroni_vs_vanilla', float('nan')):.3g}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
