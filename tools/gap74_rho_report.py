#!/usr/bin/env python3
"""GAP-74 — rho(m) at fixed t0, per checkpoint, with paired bootstrap CIs.

Pre-registration: ``docs/audit/gap74-conditional-mean-bound.md`` §0 (including
the §0.3 amendment that fixes the arm policy before any cell exists).

The quantity is the marginal dispersion ratio

    rho(m) = Tr(Cov(endpoint at restart m, started at t0)) / Tr(Cov(baseline))

computed on the endpoint samples the sweep already writes. Records are pooled
across the pre-registered seeds (independent draws), and the adjacent-m pairs
are compared with a **paired** bootstrap over record indices — the initial noise
is seed-keyed, so record `i` at `m` and record `i` at `m'` are the same draw.

This tool deliberately does not compute Theorem 5's deviation term. Per §0.2
that is a different object, and mixing them is the error gap67 §6.4 flagged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_MS = [0.9, 0.7, 0.5, 0.3, 0.1]
DEFAULT_CKPTS = ["production", "w16e1_5k"]
DEFAULT_ARMS = ["CosineAnnealScheduler", "CodimensionSheetScheduler",
                "EvidenceDrivenScheduler"]


def _cell_dir(root: Path, ckpt: str, m: float, seed: int) -> Path:
    return root / f"{ckpt}_m{m}_s{seed}"


def _load(path: Path) -> np.ndarray:
    with np.load(path) as data:
        arr = np.asarray(data["samples"], dtype=np.float64)
    return arr.reshape(arr.shape[0], -1)


def _pool(root: Path, ckpt: str, m: float, seeds: list[int],
          name: str) -> np.ndarray | None:
    """Concatenate the arm's samples across seeds; ``None`` if any is missing."""
    chunks = []
    for seed in seeds:
        path = _cell_dir(root, ckpt, m, seed) / f"{name}_samples.npz"
        if not path.is_file():
            return None
        chunks.append(_load(path))
    shapes = {c.shape[1] for c in chunks}
    if len(shapes) != 1:
        raise ValueError(f"{ckpt} m={m} {name}: inconsistent sample width")
    return np.concatenate(chunks, axis=0)


def _trace_cov(x: np.ndarray) -> float:
    return float(x.var(axis=0, ddof=1).sum())


def _rho(x: np.ndarray, base: np.ndarray) -> float:
    denom = _trace_cov(base)
    if denom <= 0.0:
        raise ValueError("baseline trace-covariance is zero")
    return _trace_cov(x) / denom


def _paired_bootstrap(
    x_a: np.ndarray, x_b: np.ndarray, base: np.ndarray,
    *, n_boot: int, rng: np.random.Generator,
) -> dict[str, float]:
    """CI on ``rho_b - rho_a`` resampling the same records in both arms."""
    n = x_a.shape[0]
    if x_b.shape[0] != n or base.shape[0] != n:
        raise ValueError("paired bootstrap needs equal record counts")
    deltas = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        deltas[i] = _rho(x_b[idx], base[idx]) - _rho(x_a[idx], base[idx])
    return {
        "mean": float(deltas.mean()),
        "ci95_low": float(np.percentile(deltas, 2.5)),
        "ci95_high": float(np.percentile(deltas, 97.5)),
    }


def _bootstrap_rho(
    x: np.ndarray, base: np.ndarray,
    *, n_boot: int, rng: np.random.Generator,
) -> dict[str, float]:
    n = x.shape[0]
    vals = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        vals[i] = _rho(x[idx], base[idx])
    return {
        "mean": float(vals.mean()),
        "ci95_low": float(np.percentile(vals, 2.5)),
        "ci95_high": float(np.percentile(vals, 97.5)),
    }


def _pair_state(diff: dict[str, float]) -> str:
    """``PASS`` (increasing, CI excludes 0), ``TIE`` (CI contains 0), ``FAIL``."""
    if diff["ci95_low"] > 0.0:
        return "PASS"
    if diff["ci95_high"] < 0.0:
        return "FAIL"
    return "TIE"


def _curve(
    root: Path, ckpt: str, ms: list[float], seeds: list[int],
    arms: list[str], *, n_boot: int, rng: np.random.Generator,
) -> dict[str, Any]:
    # Work in ascending m so "increasing rho" is a positive difference; the
    # pre-registered grid is written descending, which would invert the sign of
    # every adjacent pair.
    ms = sorted(ms)
    out: dict[str, Any] = {"points": {}, "pairs": {}, "rule1": {}, "rule2": {}}
    for arm in arms:
        points: dict[str, Any] = {}
        for m in ms:
            x = _pool(root, ckpt, m, seeds, arm)
            base = _pool(root, ckpt, m, seeds, "baseline")
            if x is None or base is None:
                points[f"{m}"] = None
                continue
            points[f"{m}"] = _bootstrap_rho(x, base, n_boot=n_boot, rng=rng)
        out["points"][arm] = points

        pairs: dict[str, Any] = {}
        for a, b in zip(ms[:-1], ms[1:], strict=True):
            x_a = _pool(root, ckpt, a, seeds, arm)
            x_b = _pool(root, ckpt, b, seeds, arm)
            base_a = _pool(root, ckpt, a, seeds, "baseline")
            base_b = _pool(root, ckpt, b, seeds, "baseline")
            if any(v is None for v in (x_a, x_b, base_a, base_b)):
                pairs[f"{a}->{b}"] = None
                continue
            # Baseline is the same arm-independent reference in both cells, so
            # the two cells must carry byte-identical baseline samples; if they
            # do not, the allocation moved with m and L3 is violated.
            assert x_a is not None and x_b is not None and base_a is not None
            assert base_b is not None
            if not np.array_equal(base_a, base_b):
                raise ValueError(
                    f"{ckpt} {arm} {a}->{b}: baseline samples differ across m — "
                    "the equal-budget allocation moved with m (L3)"
                )
            diff = _paired_bootstrap(x_a, x_b, base_a, n_boot=n_boot, rng=rng)
            diff["state"] = _pair_state(diff)
            pairs[f"{a}->{b}"] = diff
        out["pairs"][arm] = pairs

        states = [p["state"] for p in pairs.values() if p]
        out["rule1"][arm] = {
            "passes": states.count("PASS"),
            "ties": states.count("TIE"),
            "fails": states.count("FAIL"),
            "holds": bool(states) and "FAIL" not in states
            and states.count("PASS") >= 3,
        }
        top = points.get(f"{ms[-1]}")
        out["rule2"][arm] = {
            "rho_at_m_max": None if top is None else top["mean"],
            "ci95_high": None if top is None else top["ci95_high"],
            # "not significantly below 1": the two-sided 95 % CI must reach 1.
            "holds": bool(top is not None and top["ci95_high"] >= 1.0),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--ckpts", nargs="+", default=DEFAULT_CKPTS)
    ap.add_argument("--ms", nargs="+", type=float, default=DEFAULT_MS)
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--arms", nargs="+", default=DEFAULT_ARMS)
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--rng-seed", type=int, default=20261023)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    rng = np.random.default_rng(args.rng_seed)
    curves: dict[str, Any] = {}
    for ckpt in args.ckpts:
        curves[ckpt] = _curve(
            args.root, ckpt, args.ms, args.seeds, args.arms,
            n_boot=args.bootstrap, rng=rng,
        )

    summary: dict[str, Any] = {}
    for ckpt, curve in curves.items():
        arms = list(curve["rule1"])
        missing = [
            f"{arm}@{m}"
            for arm in arms
            for m, point in curve["points"][arm].items()
            if point is None
        ]
        rule1 = [curve["rule1"][a]["holds"] for a in arms]
        rule2 = [curve["rule2"][a]["holds"] for a in arms]
        summary[ckpt] = {
            "complete": not missing,
            "missing_cells": missing,
            "rule1_all_arms": all(rule1) and not missing,
            "rule2_all_arms": all(rule2) and not missing,
            "arms_failing_rule1": [a for a in arms
                                   if not curve["rule1"][a]["holds"]],
            "arms_failing_rule2": [a for a in arms
                                   if not curve["rule2"][a]["holds"]],
        }

    incomplete = [c for c, s in summary.items() if not s["complete"]]
    ok = [c for c, s in summary.items()
          if s["rule1_all_arms"] and s["rule2_all_arms"]]
    falsified = [c for c, s in summary.items() if not s["rule1_all_arms"]]
    if incomplete:
        verdict = "INCONCLUSIVE"
    elif len(ok) == len(summary) and ok:
        verdict = "CONDITIONAL_MEAN_BOUND_SUPPORTED"
    elif ok:
        verdict = "PARTIAL_ONE_REGIME"
    elif len(falsified) == len(summary):
        verdict = "FALSIFIED"
    else:
        verdict = "MIXED"

    payload = {
        "spec": "docs/audit/gap74-conditional-mean-bound.md §0.4",
        "root": str(args.root),
        "seeds": list(args.seeds),
        "ms": list(args.ms),
        "arms": list(args.arms),
        "bootstrap": int(args.bootstrap),
        "rng_seed": int(args.rng_seed),
        "curves": curves,
        "per_checkpoint": summary,
        "verdict": verdict,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"verdict": verdict, "per_checkpoint": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
