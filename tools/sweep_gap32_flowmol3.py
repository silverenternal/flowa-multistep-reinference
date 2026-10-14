#!/usr/bin/env python3
"""GAP-32 — FlowMol3 R3 external-method head-to-head driver.

Runs the five-arm roster on the **real molecular domain** (FlowMol3 R3):

* ``vanilla``  — stock Euler coordinate step (the reference).
* ``fastdllm`` — confidence-aware Euler + midpoint verifier.
* ``abcache``  — 2-step Adams-Bashforth velocity-cache reuse.
* ``lediflow`` — learned-prior-shifted Euler.
* ``flowa``    — the framework multi-round restart-blend loop.

All five arms share the coordinate-channel solver budget (``--nfe``) and
are **seed-matched**: every arm for a given ``seed`` is driven with the
same RNG seed, so the upstream prior (``x_0``/``a_0``/``c_0``/``e_0``) and
the native CTMC categorical draws are paired across arms. The metric is
the paper-parity FG-deviation (``paper_fg_deviation``, lower is better)
from :func:`tools.paper_metrics.compute_all_paper_metrics`.

The coordinate channel is driven by :class:`tools.gap32_flowmol3_sampler.
FlowMol3XChannelSampler`; the categorical channels always use the
vendored FlowMol3 CTMC rule, so the external-method comparison is exactly
the continuous-solver comparison the R6 head-to-head makes.

Statistics (R6-style, §7.8): unit of replication = seed (``--seeds``);
per-arm metric vs ``vanilla`` tested with a two-sided **paired** t-test and
Bonferroni-corrected across the four non-vanilla arms (``α = 0.05/4``); the
FlowA-vs-external contrasts are Bonferroni-corrected across the three
external arms (``α = 0.05/3``).

Evidence: ``verification_outputs/gap32-headtohead/flowmol3_r3/``. Audit:
``docs/audit/gap32-headtohead.md``.

Run as::

    .venvs/flowmol3_venv/bin/python tools/sweep_gap32_flowmol3.py \\
        --n-molecules 1000 --nfe 250 --seeds 42 43 44 --device cuda:0
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
_UPSTREAM_REPO = REPO_ROOT / "data" / "FlowMol3" / "repo"
if str(_UPSTREAM_REPO) not in sys.path:
    sys.path.insert(0, str(_UPSTREAM_REPO))

warnings.filterwarnings("ignore")

from tools.gap32_flowmol3_sampler import (  # noqa: E402
    ARM_ORDER,
    DEFAULT_NFE,
    EXTERNAL_ARMS,
    FlowMol3XChannelSampler,
    SolverConfig,
    config_fingerprint,
)

SCHEMA_VERSION: str = "gap32_flowmol3_v1"
CELL_NAME: str = "flowmol3_r3"
COMPARISON_ARMS: tuple[str, ...] = ("fastdllm", "abcache", "lediflow", "flowa")
DEFAULT_WEIGHTS: Path = (
    REPO_ROOT / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"
)
REFERENCE: str = "GEOM_DRUGS"


# ---------------------------------------------------------------------------
# Metric
# ---------------------------------------------------------------------------


def score_fg_dev(molecules: list[Any], *, pb_workers: int = 2) -> dict[str, float]:
    """Return the paper-parity FG-deviation (+ companions) for one arm."""
    from tools.paper_metrics import compute_all_paper_metrics

    pmr = compute_all_paper_metrics(
        molecules, reference=REFERENCE, pb_workers=int(pb_workers)
    )
    return {
        "fg_dev": float(pmr.paper_fg_deviation),
        "validity_pct": float(pmr.paper_validity_pct),
        "pb_validity_pct": float(pmr.paper_pb_validity_pct),
        "ood_ring_rate": float(pmr.paper_ood_ring_rate),
    }


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
# One (seed) run
# ---------------------------------------------------------------------------


def run_one_seed(
    *,
    sampler: FlowMol3XChannelSampler,
    model: Any,
    n_molecules: int,
    seed: int,
    cfg: SolverConfig,
    batch_size: int,
    out_dir: Path,
    verbose: bool,
    pb_workers: int,
) -> dict[str, Any]:
    """Generate all five arms for one seed and return the per-arm metrics."""
    import torch

    t0 = time.perf_counter()
    # Draw the molecule-size vector once per seed; every arm sees the same
    # sizes (paired), and the per-arm RNG seed is identical so the upstream
    # prior + CTMC draws are paired across arms.
    torch.manual_seed(int(seed))
    n_atoms_list = [
        int(x) for x in model.sample_n_atoms(int(n_molecules)).detach().cpu().tolist()
    ]
    # Chunk into fixed-size batches (the canonical R3 path batches at 100 to
    # bound the DGL graph / GVP memory). Every arm uses the same chunking.
    bs = max(1, int(batch_size))
    chunks = [
        n_atoms_list[i : i + bs] for i in range(0, len(n_atoms_list), bs)
    ]

    metrics: dict[str, dict[str, float]] = {}
    solver_stats: dict[str, dict[str, Any]] = {}
    seed_dir = out_dir / f"seed{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)

    for arm in ARM_ORDER:
        t_arm = time.perf_counter()
        molecules: list[Any] = []
        chunk_stats: list[dict[str, Any]] = []
        for ci, chunk in enumerate(chunks):
            res = sampler.sample_arm(
                arm=arm,
                n_atoms_list=chunk,
                seed=int(seed) + ci * 100_003,
                cfg=cfg,
            )
            molecules.extend(res["molecules"])
            chunk_stats.append(res["stats"])
        scores = score_fg_dev(molecules, pb_workers=int(pb_workers))
        metrics[arm] = scores
        solver_stats[arm] = {
            "arm": arm,
            "n_molecules": int(len(molecules)),
            "n_chunks": int(len(chunks)),
            "first_chunk_stats": chunk_stats[0] if chunk_stats else {},
            "wall_sec": float(time.perf_counter() - t_arm),
        }
        if verbose:
            print(
                f"[gap32-fm3] seed={seed} {arm:9s}: fg_dev={scores['fg_dev']:.6f} "
                f"validity={scores['validity_pct']:.4f} "
                f"({time.perf_counter() - t_arm:.1f}s)",
                flush=True,
            )

    result = {
        "seed": int(seed),
        "n_molecules": int(n_molecules),
        "nfe": int(cfg.nfe),
        "n_atoms_min": int(min(n_atoms_list)),
        "n_atoms_max": int(max(n_atoms_list)),
        "n_atoms_mean": float(np.mean(n_atoms_list)),
        "metrics": metrics,
        "solver_stats": solver_stats,
        "wall_sec": float(time.perf_counter() - t0),
    }
    (seed_dir / "seed_summary.json").write_text(json.dumps(result, indent=2))
    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool the per-seed FG-deviations into R6-style paired statistics."""
    n_seeds = len(per_seed)
    out: dict[str, Any] = {
        "n_seeds": n_seeds,
        "seeds": [int(r["seed"]) for r in per_seed],
        "arms": {},
        "flowa_vs_external": {},
    }
    vanilla = np.asarray([float(r["metrics"]["vanilla"]["fg_dev"]) for r in per_seed])
    for arm in ARM_ORDER:
        vals = np.asarray([float(r["metrics"][arm]["fg_dev"]) for r in per_seed])
        diff = vals - vanilla
        t, df, p = paired_ttest(diff)
        entry: dict[str, Any] = {
            "fg_dev_mean": float(vals.mean()),
            "fg_dev_std": float(vals.std(ddof=1)) if n_seeds > 1 else 0.0,
            "fg_dev_per_seed": [float(x) for x in vals],
            "delta_vs_vanilla_pct": float(
                (vals.mean() - vanilla.mean())
                / max(abs(float(vanilla.mean())), 1e-9)
                * 100.0
            ),
            "validity_mean": float(
                np.mean([float(r["metrics"][arm]["validity_pct"]) for r in per_seed])
            ),
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

    flowa = np.asarray([float(r["metrics"]["flowa"]["fg_dev"]) for r in per_seed])
    for arm in EXTERNAL_ARMS:
        ext_vals = np.asarray([float(r["metrics"][arm]["fg_dev"]) for r in per_seed])
        diff = flowa - ext_vals
        t, df, p = paired_ttest(diff)
        p_bonf = float(min(p * len(EXTERNAL_ARMS), 1.0))
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


def write_csv(path: Path, agg: dict[str, Any]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "cell",
                "arm",
                "n_seeds",
                "fg_dev_mean",
                "fg_dev_std",
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
                    CELL_NAME,
                    arm,
                    agg["n_seeds"],
                    f"{a['fg_dev_mean']:.6f}",
                    f"{a['fg_dev_std']:.6f}",
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


def _build_model(weights: Path, device: str, nfe: int) -> Any:
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter

    adapter = FlowMol3V2Adapter(
        backend="torch",
        num_steps=int(nfe),
        weights_path=str(weights),
        device=str(device),
        use_upstream=True,
        upstream_repo_dir=str(_UPSTREAM_REPO),
    )
    model = adapter._load_model()
    if adapter._loaded_model_kind() != "upstream_flowmol":
        raise SystemExit(
            f"expected_upstream_flowmol:got {adapter._loaded_model_kind()!r}"
        )
    return model


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-molecules", type=int, default=1000)
    p.add_argument("--nfe", type=int, default=DEFAULT_NFE)
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Molecules per DGL graph / GVP forward (canonical R3 batches at 100).",
    )
    p.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--pb-workers", type=int, default=2)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "verification_outputs" / "gap32-headtohead" / CELL_NAME,
    )
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    if args.smoke:
        # Smoke keeps the canonical NFE (250): the native CTMC categorical
        # channels only fully unmask over a full budget, so a short NFE would
        # leave ``Se`` mask tokens and crash the paper-metric analyzer.
        args.n_molecules = 8
        args.seeds = [42]

    if not args.weights.exists():
        raise SystemExit(f"weights_not_found:{args.weights}")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = SolverConfig(nfe=int(args.nfe))
    weights_sha256 = hashlib.sha256(args.weights.read_bytes()).hexdigest()

    if not args.quiet:
        print(
            f"[gap32-fm3] weights={args.weights} sha256={weights_sha256[:16]} "
            f"N={args.n_molecules} NFE={args.nfe} seeds={args.seeds} "
            f"device={args.device} cfg={config_fingerprint(cfg)[:16]}",
            flush=True,
        )

    t_load = time.perf_counter()
    model = _build_model(Path(args.weights), str(args.device), int(args.nfe))
    sampler = FlowMol3XChannelSampler(model, device=str(args.device))
    load_sec = float(time.perf_counter() - t_load)
    if not args.quiet:
        print(f"[gap32-fm3] model loaded in {load_sec:.1f}s", flush=True)

    per_seed: list[dict[str, Any]] = []
    t_all = time.perf_counter()
    for seed in args.seeds:
        per_seed.append(
            run_one_seed(
                sampler=sampler,
                model=model,
                n_molecules=int(args.n_molecules),
                seed=int(seed),
                cfg=cfg,
                batch_size=int(args.batch_size),
                out_dir=out_dir,
                verbose=not args.quiet,
                pb_workers=int(args.pb_workers),
            )
        )
    wall = time.perf_counter() - t_all

    agg = aggregate(per_seed)
    agg.update(
        {
            "schema_version": SCHEMA_VERSION,
            "cell": CELL_NAME,
            "weights": str(args.weights),
            "weights_sha256": weights_sha256,
            "n_molecules": int(args.n_molecules),
            "nfe": int(args.nfe),
            "metric": "paper_fg_deviation",
            "reference": REFERENCE,
            "solver_config": {
                "nfe": int(cfg.nfe),
                "fastdllm_threshold": float(cfg.fastdllm_threshold),
                "abcache_warmup": int(cfg.abcache_warmup),
                "abcache_interval": int(cfg.abcache_interval),
                "abcache_qlen": int(cfg.abcache_qlen),
                "lediflow_alpha": float(cfg.lediflow_alpha),
                "lediflow_seed": int(cfg.lediflow_seed),
                "lediflow_scale": float(cfg.lediflow_scale),
                "flowa_n_rounds": int(cfg.flowa_n_rounds),
                "flowa_beta": float(cfg.flowa_beta),
                "flowa_restart_from_round": int(cfg.flowa_restart_from_round),
                "config_fingerprint": config_fingerprint(cfg),
            },
            "alpha_bonferroni_vs_vanilla": float(0.05 / len(COMPARISON_ARMS)),
            "alpha_bonferroni_flowa_vs_external": float(0.05 / len(EXTERNAL_ARMS)),
            "load_sec": float(load_sec),
            "wall_min": float(round(wall / 60.0, 2)),
            "per_seed": per_seed,
        }
    )
    (out_dir / "aggregate.json").write_text(json.dumps(agg, indent=2))
    write_csv(out_dir / "aggregate.csv", agg)
    if not args.quiet:
        print(
            f"[gap32-fm3] wrote {out_dir / 'aggregate.json'} ({wall / 60:.1f} min)",
            flush=True,
        )
        for arm in ARM_ORDER:
            a = agg["arms"][arm]
            print(
                f"[gap32-fm3] {arm:9s}: fg_dev={a['fg_dev_mean']:.6f} "
                f"Δ%={a['delta_vs_vanilla_pct']:+.3f} ({a['direction']}) "
                f"p_bonf={a.get('p_value_bonferroni_vs_vanilla', float('nan')):.3g}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
