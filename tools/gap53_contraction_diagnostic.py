"""GAP-53 — measure the re-inference map's contraction, not seed significance.

Stage ``contraction`` (default, decisive):

For a fixed prior ``x`` and a small perturbation ``x' = x + eps * v``,
run the *same* map ``G = Phi o B_m`` (same restart policy, same upstream
seed, so the CTMC draws are identical) and measure

    D_r = RMS( G^r(x) - G^r(x') ),     D_0 = eps
    q_hat = (D_R / D_0) ** (1 / R)

Theory (``docs/audit/gap53-initial-condition-contraction.md`` §2):
``q = m * K`` where ``K`` is the flow map's Lipschitz constant. So
``K_eff = q_hat / m`` and the memory fraction that contracts is
``m* = 0.9 / K_eff``. This is a measurement of the map's stability
variable, not a hypothesis test over new seeds.

The discrete channels are held at ``m = 1`` during the probe so that the
paired runs differ **only** in the coordinate channel; otherwise the
categorical resample uses a different RNG stream for the two priors and
adds noise to the ratio.

Stage ``metric`` (optional, expensive): cross-prior dispersion of
``fg_dev`` / ``pb_validity`` at each ``R`` over the existing seed block.

Usage::

    .venvs/flowmol3_venv/bin/python tools/gap53_contraction_diagnostic.py \
        --stage contraction --rounds 1 2 3 4 --memory-fraction 0.5
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
warnings.filterwarnings("ignore")

# Re-use the existing GAP-43 seed block — no new seeds.
DEFAULT_PRIOR_SEEDS = (55, 105, 155, 205, 255, 305, 355, 405)
NFE = 250
N_PER_PRIOR = 100
NFE_BATCH = 100
WEIGHTS_PATH = REPO_ROOT / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"
UPSTREAM_REPO = REPO_ROOT / "data" / "FlowMol3" / "repo"
DEVICE = "cuda:0"


def _driver():
    import importlib

    return importlib.import_module("wave338_p5_r3_n1000_paired")


def _split_nfe(total: int, rounds: int) -> list[int]:
    base = int(total) // int(rounds)
    parts = [base] * int(rounds)
    parts[-1] += int(total) % int(rounds)
    return parts


def _adapter(device: str):
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter

    adapter = FlowMol3V2Adapter(
        backend="torch",
        num_steps=NFE,
        weights_path=str(WEIGHTS_PATH),
        device=str(device),
        use_upstream=True,
        upstream_repo_dir=str(UPSTREAM_REPO),
    )
    _ = adapter._load_model()
    if adapter._loaded_model_kind() != "upstream_flowmol":
        raise RuntimeError(
            f"expected upstream_flowmol, got {adapter._loaded_model_kind()!r}"
        )
    return adapter


def _policy(*, seed: int, m_coord: float, m_charge: float, m_pair: float):
    from adaptive_reflow.contracts import (
        ArtifactHash,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )
    from adaptive_reflow.universal.state import ChannelName

    coord = ChannelName("coordinate")
    charge = ChannelName("charge")
    pair = ChannelName("raw_pair")

    def beta(m: float) -> FactorValue:
        return FactorValue(1.0 - float(m))

    policy = FinalRestartPolicy(
        policy_id=PolicyId(f"gap53-probe-{seed}-{m_coord}"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(f"gap53-probe-{seed}"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={coord: beta(m_coord), charge: beta(m_charge), pair: beta(m_pair)},
        alpha_by_channel={coord: FactorValue(1.0), charge: FactorValue(1.0),
                          pair: FactorValue(1.0)},
        fresh_noise_floor_by_channel={coord: FactorValue(0.0),
                                      charge: FactorValue(0.0),
                                      pair: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={coord: True, charge: True, pair: True},
        ledger_row_id=LedgerRowId(f"gap53-probe-ledger-{seed}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    return dataclasses.replace(policy, policy_hash=hash_policy_hash(policy))


def _entry_x(adapter, bundle) -> np.ndarray:
    entry = adapter._native_states.get(bundle.native_state_digest)
    if entry is None:
        raise RuntimeError("missing_native_state")
    return np.asarray(entry["x"], dtype=np.float64)


def _perturb(adapter, bundle, direction: np.ndarray, eps: float):
    entry = adapter._native_states.get(bundle.native_state_digest)
    if entry is None:
        raise RuntimeError("missing_native_state")
    new_entry = dict(entry)
    new_entry["x"] = np.asarray(entry["x"], dtype=np.float64) + float(eps) * direction
    digest = hashlib.sha256(
        repr((
            "gap53_perturb",
            str(bundle.native_state_digest),
            float(eps),
            hashlib.sha256(np.ascontiguousarray(direction).tobytes()).hexdigest(),
        )).encode("utf-8")
    ).hexdigest()
    adapter._put_native_state(digest, new_entry)
    return dataclasses.replace(bundle, native_state_digest=digest)


def _rms_diff(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        return float("nan")
    return float(np.sqrt(np.mean((a - b) ** 2)))


def _rg(x: np.ndarray) -> float:
    """Mean radius of gyration — defined even when atom counts differ."""
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 2:
        arr = arr[None]
    vals = []
    for mol in arr:
        c = mol.mean(axis=0)
        vals.append(float(np.sqrt(np.mean(np.sum((mol - c) ** 2, axis=1)))))
    return float(np.mean(vals)) if vals else float("nan")


def _solve(adapter, bundle, *, nfe_r: int, seed: int, n_mol: int, round_idx: int):
    from adaptive_reflow.universal.state import ODEConditionDelta

    cond = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe_r)},
        source=f"gap53_probe_{seed}",
        target_round=int(round_idx),
        calibration_artifact_hash="gap53",
    )
    return adapter.solve_ode(bundle, cond, seed=int(seed), n_molecules=int(n_mol))


def contraction_probe(*, adapter, prior_seed: int, rounds: int, memory_fraction: float,
                      n_molecules: int, eps: float, n_dirs: int) -> dict:
    base = adapter.build_initial_state(
        batch_id=f"gap53-probe-{prior_seed}",
        sample_id=f"gap53-probe-{prior_seed}-prior",
    )
    x0 = _entry_x(adapter, base)
    n = int(x0.shape[0])
    rng = np.random.default_rng(int(prior_seed) * 7919 + 13)
    dirs = []
    for _ in range(int(n_dirs)):
        v = rng.standard_normal((n, 3))
        dirs.append(v / np.linalg.norm(v))
    policy = _policy(
        seed=int(prior_seed), m_coord=float(memory_fraction),
        m_charge=1.0, m_pair=1.0,
    )
    parts = _split_nfe(NFE, int(rounds))
    rows = []
    for dir_idx, v in enumerate(dirs):
        b0 = adapter.apply_restart_distribution(base, policy)
        bp = adapter.apply_restart_distribution(
            _perturb(adapter, base, v, float(eps)), policy,
        )
        d = [float(eps)]
        d_rg = [abs(_rg(_entry_x(adapter, b0)) - _rg(_entry_x(adapter, bp)))]
        dim_changes = 0
        t0 = time.perf_counter()
        for round_idx, nfe_r in enumerate(parts):
            tr0 = _solve(adapter, b0, nfe_r=nfe_r, seed=prior_seed,
                         n_mol=n_molecules, round_idx=round_idx)
            tr1 = _solve(adapter, bp, nfe_r=nfe_r, seed=prior_seed,
                         n_mol=n_molecules, round_idx=round_idx)
            e0 = adapter.observe_endpoint(tr0, b0)
            e1 = adapter.observe_endpoint(tr1, bp)
            xa, xb = _entry_x(adapter, e0), _entry_x(adapter, e1)
            if xa.shape != xb.shape:
                # The CTMC dropped a different number of atoms: the map
                # is not Lipschitz across discrete classes. Record it
                # and fall back to the dimension-invariant functional.
                dim_changes += 1
            d.append(_rms_diff(xa, xb))
            d_rg.append(abs(_rg(xa) - _rg(xb)))
            if round_idx < int(rounds) - 1:
                b0 = adapter.apply_restart_distribution(e0, policy)
                bp = adapter.apply_restart_distribution(e1, policy)
        q_hat = (d[-1] / d[0]) ** (1.0 / int(rounds)) if d[-1] > 0 else float("nan")
        q_hat_rg = (
            (d_rg[-1] / d_rg[0]) ** (1.0 / int(rounds))
            if d_rg[0] > 0 else float("nan")
        )
        rows.append({
            "direction": int(dir_idx),
            "D": [float(x) for x in d],
            "D_rg": [float(x) for x in d_rg],
            "per_round_ratio": [
                float(d[i + 1] / d[i]) if d[i] > 0 else float("nan")
                for i in range(len(d) - 1)
            ],
            "q_hat": float(q_hat),
            "q_hat_rg": float(q_hat_rg),
            "dim_changes": int(dim_changes),
            "wallclock_s": round(time.perf_counter() - t0, 3),
        })
        print(
            f"[prior={prior_seed} R={rounds} dir={dir_idx}] "
            f"q_hat={q_hat:.4f} q_rg={q_hat_rg:.4f} "
            f"dim_changes={dim_changes} D={[f'{x:.3e}' for x in d]}",
            flush=True,
        )
    qs = np.asarray([r["q_hat"] for r in rows], dtype=np.float64)
    qs_rg = np.asarray([r["q_hat_rg"] for r in rows], dtype=np.float64)
    pooled = np.asarray(
        [x for r in rows for x in r["per_round_ratio"]], dtype=np.float64,
    )
    pooled = pooled[np.isfinite(pooled)]
    return {
        "prior_seed": int(prior_seed),
        "rounds": int(rounds),
        "memory_fraction": float(memory_fraction),
        "nfe_total": int(NFE),
        "nfe_parts": [int(p) for p in parts],
        "n_molecules": int(n_molecules),
        "eps": float(eps),
        "q_hat_median": float(np.median(qs)),
        "q_hat_mean": float(np.mean(qs)),
        "q_hat_sd": float(np.std(qs, ddof=1)) if qs.size > 1 else float("nan"),
        # Dimension-invariant functional: the CTMC can change the atom
        # count, so the coordinate RMS is undefined across that event.
        "q_rg_median": float(np.nanmedian(qs_rg)) if np.any(np.isfinite(qs_rg)) else float("nan"),
        "n_dim_changes": int(sum(r["dim_changes"] for r in rows)),
        "n_directions": int(len(rows)),
        # The map is piecewise smooth: a tiny x perturbation can flip a
        # CTMC class, which is a genuine jump, not a Lipschitz failure.
        # The pooled per-round ratio is therefore summarised by its
        # median / IQR, plus the fraction of expanding steps.
        "ratio_median": float(np.median(pooled)) if pooled.size else float("nan"),
        "ratio_q25": float(np.quantile(pooled, 0.25)) if pooled.size else float("nan"),
        "ratio_q75": float(np.quantile(pooled, 0.75)) if pooled.size else float("nan"),
        "frac_ratio_gt1": float(np.mean(pooled > 1.0)) if pooled.size else float("nan"),
        "directions": rows,
    }


def _mean_pairwise(cents: np.ndarray) -> float:
    k = int(cents.shape[0])
    if k < 2:
        return float("nan")
    d = []
    for i in range(k):
        for j in range(i + 1, k):
            d.append(float(np.linalg.norm(cents[i] - cents[j])))
    return float(np.mean(d))


def _bootstrap_ratio_ci(a: np.ndarray, b: np.ndarray, *, n_boot: int = 4000,
                        seed: int = 0) -> tuple[float, float, float]:
    rng = np.random.default_rng(int(seed))
    k = int(a.shape[0])
    s_a, s_b = _mean_pairwise(a), _mean_pairwise(b)
    point = float(s_a / s_b) if s_b else float("nan")
    ratios = []
    for _ in range(int(n_boot)):
        idx = rng.integers(0, k, size=k)
        s0 = _mean_pairwise(b[idx])
        s1 = _mean_pairwise(a[idx])
        if s0 > 0.0 and math.isfinite(s0) and math.isfinite(s1):
            ratios.append(s1 / s0)
    if not ratios:
        return point, float("nan"), float("nan")
    return point, float(np.quantile(ratios, 0.025)), float(np.quantile(ratios, 0.975))


def _centroid(mols) -> list[float]:
    pts = []
    for mol in mols:
        pos = mol.positions
        if hasattr(pos, "detach"):
            pos = pos.detach().cpu().numpy()
        arr = np.asarray(pos, dtype=np.float64).reshape(-1, 3)
        if arr.size:
            pts.append(arr)
    if not pts:
        return [float("nan")] * 3
    return [float(v) for v in np.concatenate(pts, axis=0).mean(axis=0)]


def metric_cell(*, adapter, prior_seed: int, rounds: int, memory_fraction: float,
                n_per_prior: int) -> dict:
    from tools.paper_metrics import compute_all_paper_metrics

    bundle = adapter.build_initial_state(
        batch_id=f"gap53-prior-{prior_seed}",
        sample_id=f"gap53-prior-{prior_seed}-prior",
    )
    policy = _driver()._make_real_restart_policy(
        seed=int(prior_seed), memory_fraction=float(memory_fraction),
    )
    bundle = adapter.apply_restart_distribution(bundle, policy)
    parts = _split_nfe(NFE, int(rounds))
    trace = None
    t0 = time.perf_counter()
    for round_idx, nfe_r in enumerate(parts):
        trace = _solve(adapter, bundle, nfe_r=nfe_r, seed=prior_seed,
                       n_mol=n_per_prior, round_idx=round_idx)
        if round_idx < int(rounds) - 1:
            endpoint = adapter.observe_endpoint(trace, bundle)
            bundle = adapter.apply_restart_distribution(endpoint, policy)
    wallclock = round(time.perf_counter() - t0, 3)
    mols, meta = adapter.export_sampled_molecules(trace)
    pmr = compute_all_paper_metrics(mols, reference="GEOM_DRUGS")
    return {
        "prior_seed": int(prior_seed),
        "rounds": int(rounds),
        "memory_fraction": float(memory_fraction),
        "nfe_total": int(sum(parts)),
        "nfe_parts": [int(p) for p in parts],
        "n_sampled": int(len(mols)),
        "decode_marker": str(meta.get("marker")),
        "centroid": _centroid(mols),
        "fg_dev": float(pmr.paper_fg_deviation),
        "pb_validity_pct": float(pmr.paper_pb_validity_pct),
        "validity_pct": float(pmr.paper_validity_pct),
        "ood_ring_rate": float(pmr.paper_ood_ring_rate),
        "wallclock_s": float(wallclock),
    }


def metric_analysis(records: list[dict]) -> dict:
    by_r: dict[int, list[dict]] = {}
    for rec in records:
        by_r.setdefault(int(rec["rounds"]), []).append(rec)
    per_r = {}
    for r, rows in sorted(by_r.items()):
        cents = np.asarray([x["centroid"] for x in rows], dtype=np.float64)
        fg = np.asarray([x["fg_dev"] for x in rows], dtype=np.float64)
        pb = np.asarray([x["pb_validity_pct"] for x in rows], dtype=np.float64)
        per_r[int(r)] = {
            "k_priors": int(len(rows)),
            "S": _mean_pairwise(cents),
            "fg_dev_mean": float(fg.mean()),
            "fg_dev_sd": float(fg.std(ddof=1)) if len(rows) > 1 else float("nan"),
            "pb_validity_mean": float(pb.mean()),
            "pb_validity_sd": float(pb.std(ddof=1)) if len(rows) > 1 else float("nan"),
            "n_sampled_total": int(sum(x["n_sampled"] for x in rows)),
        }
    ratios = []
    rounds = sorted(per_r)
    for r0, r1 in zip(rounds, rounds[1:], strict=False):
        if r1 != r0 + 1:
            continue
        a = np.asarray([x["centroid"] for x in by_r[r1]], dtype=np.float64)
        b = np.asarray([x["centroid"] for x in by_r[r0]], dtype=np.float64)
        _, lo, hi = _bootstrap_ratio_ci(a, b)
        ratios.append({
            "from_rounds": int(r0), "to_rounds": int(r1),
            "ratio": float(per_r[r1]["S"] / per_r[r0]["S"]) if per_r[r0]["S"] else float("nan"),
            "ci_low": float(lo), "ci_high": float(hi),
        })
    return {"per_rounds": per_r, "ratios": ratios}


def _verdict(rows: list[dict], memory_fraction: float) -> dict:
    q_coord = np.asarray(
        [r["ratio_median"] for r in rows if math.isfinite(r["ratio_median"])],
        dtype=np.float64,
    )
    q_rg = np.asarray(
        [r["q_rg_median"] for r in rows if math.isfinite(r["q_rg_median"])],
        dtype=np.float64,
    )
    dim_rate = float(np.mean([
        r["n_dim_changes"] / max(1, r["n_directions"] * r["rounds"])
        for r in rows
    ])) if rows else float("nan")
    if q_rg.size == 0 and q_coord.size == 0:
        return {"verdict": "INCONCLUSIVE", "reason": "no finite ratios"}
    q = float(np.median(q_rg)) if q_rg.size else float(np.median(q_coord))
    k_eff = q / float(memory_fraction) if memory_fraction > 0 else float("inf")
    return {
        "q_coord_median": float(np.median(q_coord)) if q_coord.size else float("nan"),
        "q_rg_median": float(np.median(q_rg)) if q_rg.size else float("nan"),
        "dim_change_rate": dim_rate,
        "k_eff": float(k_eff),
        "m_star_for_q_0.9": float(0.9 / k_eff) if k_eff > 0 else float("nan"),
        "verdict": (
            "CONTRACTION AT THIS m" if q < 1.0 else "NO CONTRACTION AT THIS m"
        ),
        "note": (
            "q_coord is the median per-round coordinate RMS ratio; it is "
            "only defined within a fixed discrete class. The CTMC can "
            "change the atom count (dim_change_rate), so q_rg (mean radius "
            "of gyration, dimension-invariant) is the fallback and the "
            "metric stage is the decisive test."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--stage", choices=("contraction", "metric"), default="contraction")
    p.add_argument("--rounds", type=int, nargs="+", default=[1, 2, 3, 4])
    p.add_argument("--prior-seeds", type=int, nargs="+",
                   default=list(DEFAULT_PRIOR_SEEDS))
    p.add_argument("--memory-fraction", type=float, default=0.5)
    p.add_argument("--n-molecules", type=int, default=20,
                   help="Batch size for the contraction probe (default 20).")
    p.add_argument("--n-per-prior", type=int, default=N_PER_PRIOR,
                   help="Batch size for the metric stage (default 100).")
    p.add_argument("--eps", type=float, default=1e-2)
    p.add_argument("--n-dirs", type=int, default=4)
    p.add_argument("--device", default=DEVICE)
    p.add_argument("--output-dir", type=Path,
                   default=REPO_ROOT / "verification_outputs" / "gap53-contraction")
    args = p.parse_args(argv)

    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    adapter = _adapter(str(args.device))

    if args.stage == "contraction":
        rows = []
        for rounds in [int(r) for r in args.rounds]:
            for prior_seed in [int(s) for s in args.prior_seeds]:
                cell = out_dir / f"probe_r{rounds}_prior{prior_seed}.json"
                if cell.exists():
                    rows.append(json.loads(cell.read_text()))
                    print(f"[skip] {cell.name}", flush=True)
                    continue
                rec = contraction_probe(
                    adapter=adapter, prior_seed=int(prior_seed),
                    rounds=int(rounds), memory_fraction=float(args.memory_fraction),
                    n_molecules=int(args.n_molecules), eps=float(args.eps),
                    n_dirs=int(args.n_dirs),
                )
                cell.write_text(json.dumps(rec, indent=2))
                rows.append(rec)
        summary = {
            "schema_version": "1.0.0",
            "stage": "contraction",
            "memory_fraction": float(args.memory_fraction),
            "nfe_total": int(NFE),
            "eps": float(args.eps),
            "n_molecules": int(args.n_molecules),
            "n_dirs": int(args.n_dirs),
            "prior_seeds": [int(s) for s in args.prior_seeds],
            "cells": rows,
            "verdict": _verdict(rows, float(args.memory_fraction)),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
    else:
        rows = []
        for rounds in [int(r) for r in args.rounds]:
            for prior_seed in [int(s) for s in args.prior_seeds]:
                cell = out_dir / f"metric_r{rounds}_prior{prior_seed}.json"
                if cell.exists():
                    rows.append(json.loads(cell.read_text()))
                    print(f"[skip] {cell.name}", flush=True)
                    continue
                rec = metric_cell(
                    adapter=adapter, prior_seed=int(prior_seed),
                    rounds=int(rounds), memory_fraction=float(args.memory_fraction),
                    n_per_prior=int(args.n_per_prior),
                )
                cell.write_text(json.dumps(rec, indent=2))
                rows.append(rec)
                print(
                    f"[r{rounds} prior={prior_seed}] n={rec['n_sampled']} "
                    f"fg_dev={rec['fg_dev']:.6f} pb={rec['pb_validity_pct']:.3f} "
                    f"{rec['wallclock_s']}s", flush=True,
                )
        summary = {
            "schema_version": "1.0.0",
            "stage": "metric",
            "memory_fraction": float(args.memory_fraction),
            "nfe_total": int(NFE),
            "n_per_prior": int(args.n_per_prior),
            "prior_seeds": [int(s) for s in args.prior_seeds],
            "analysis": metric_analysis(rows),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary.get("verdict", summary.get("analysis")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
