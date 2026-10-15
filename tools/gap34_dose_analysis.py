#!/usr/bin/env python3
"""GAP-34 — analyse the R1 init dose-response (``dose_response.json``).

Reads the sweep output and tests the mechanism claim:

* **Monotonicity** — Spearman rank correlation between init temperature ``tau``
  and HMMER hit count, computed per seed (5 ``tau`` points each) and averaged.
* **Collapse anchor** — ``tau = 0`` should reproduce the D-004 near-uniform
  collapse (≈ 0 hits).
* **Rise contrast** — paired t-test of ``tau = 0`` vs the canonical
  ``tau = 1`` across seeds (descriptive; n = 3 seeds).

CPU-only, stdlib. Writes ``dose_analysis.json`` next to the input.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = (REPO_ROOT / "verification_outputs" / "gap34-r1-init-dose"
               / "dose_response.json")


def _ranks(xs: list[float]) -> list[float]:
    """Average ranks (1-based), ties share the mean rank."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def spearman(xs: list[float], ys: list[float]) -> float:
    return _pearson(_ranks(xs), _ranks(ys))


def paired_t(a: list[float], b: list[float]) -> tuple[float, float]:
    """Paired t-stat and two-sided p (df = n-1), stdlib only."""
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    n = len(diffs)
    md = sum(diffs) / n
    var = sum((d - md) ** 2 for d in diffs) / (n - 1) if n > 1 else 0.0
    se = math.sqrt(var / n) if var > 0 else 0.0
    if se == 0:
        return (math.inf if md != 0 else 0.0), (0.0 if md != 0 else 1.0)
    t = md / se
    # two-sided p via the regularised incomplete beta (t distribution CDF)
    p = _t_sf_two_sided(abs(t), n - 1)
    return t, p


def _t_sf_two_sided(t: float, df: int) -> float:
    """Two-sided tail probability for Student-t, via the incomplete beta."""
    x = df / (df + t * t)
    return _betainc(df / 2.0, 0.5, x)


def _betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a,b) via a continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    # Lentz's continued fraction
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 200):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break
    return front * (f - 1.0)


def analyse(payload: dict) -> dict:
    taus = [float(t) for t in payload["taus"]]
    seeds = [int(s) for s in payload["seeds"]]
    rows = payload["rows"]
    by = {(r["tau"], r["seed"]): r for r in rows}

    # per-seed Spearman over the 5 tau points
    per_seed_rho = {}
    for s in seeds:
        xs = taus
        ys = [by[(t, s)]["hits"] for t in taus]
        per_seed_rho[s] = spearman(xs, ys)

    # per-tau mean ± sd over seeds
    per_tau = []
    for t in taus:
        hits = [by[(t, s)]["hits"] for s in seeds]
        mean = sum(hits) / len(hits)
        sd = (sum((h - mean) ** 2 for h in hits) / (len(hits) - 1)) ** 0.5 \
            if len(hits) > 1 else 0.0
        per_tau.append({"tau": t, "mean_hits": mean, "sd_hits": sd,
                        "per_seed_hits": {s: by[(t, s)]["hits"] for s in seeds}})

    # collapse anchor + rise contrast (tau=0 vs tau=1)
    t0 = [by[(0.0, s)]["hits"] for s in seeds] if (0.0, seeds[0]) in by else None
    t1 = [by[(1.0, s)]["hits"] for s in seeds] if (1.0, seeds[0]) in by else None
    contrast = None
    if t0 is not None and t1 is not None:
        tt, pp = paired_t(t1, t0)
        contrast = {
            "tau0_hits": t0, "tau1_hits": t1,
            "mean_rise": sum(t1) / len(t1) - sum(t0) / len(t0),
            "paired_t": tt, "paired_p": pp, "n_seeds": len(seeds),
        }

    # interior optimum: the tau with the most hits, and how far the extreme
    # (largest tau) falls below the peak (the dose-response is an inverted-U,
    # not monotone — both a too-uniform and a too-peaked init collapse).
    peak = max(per_tau, key=lambda r: r["mean_hits"])
    max_tau_row = max(per_tau, key=lambda r: r["tau"])
    peak_to_max = {
        "peak_tau": peak["tau"],
        "peak_mean_hits": peak["mean_hits"],
        "max_tau": max_tau_row["tau"],
        "max_tau_mean_hits": max_tau_row["mean_hits"],
        "max_over_peak": (max_tau_row["mean_hits"] / peak["mean_hits"]
                          if peak["mean_hits"] else 0.0),
    }

    return {
        "kind": "gap34_r1_init_dose_analysis",
        "taus": taus,
        "seeds": seeds,
        "per_tau": per_tau,
        "spearman_per_seed": per_seed_rho,
        "spearman_mean": sum(per_seed_rho.values()) / len(per_seed_rho),
        "peak": peak_to_max,
        "collapse_anchor": {"tau0_all_zero": bool(t0 is not None and all(h == 0 for h in t0))},
        "rise_contrast": contrast,
        "note": ("Spearman rho computed per seed over the tau points (rho=1.0 = "
                 "perfectly monotone; <1 indicates a non-monotone / inverted-U "
                 "dose-response). Rise contrast is tau=0 vs tau=1, paired over "
                 "seeds (descriptive). 'peak' locates the interior optimum and "
                 "how far the largest tau falls below it."),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    args = ap.parse_args(argv)
    if not args.src.exists():
        raise SystemExit(f"missing {args.src}; run tools/sweep_gap34_init_dose.py first")
    payload = json.loads(args.src.read_text())
    out = analyse(payload)
    (args.src.parent / "dose_analysis.json").write_text(json.dumps(out, indent=2))

    print("=== R1 init dose-response ===")
    for r in out["per_tau"]:
        print(f"  tau={r['tau']:<5g} mean_hits={r['mean_hits']:7.1f} "
              f"(sd {r['sd_hits']:6.1f})  per_seed={r['per_seed_hits']}")
    print(f"  Spearman rho (per seed) = {out['spearman_per_seed']}  "
          f"mean = {out['spearman_mean']:.3f}")
    pk = out["peak"]
    print(f"  peak: tau={pk['peak_tau']} ({pk['peak_mean_hits']:.1f} hits); "
          f"max tau={pk['max_tau']} is {pk['max_over_peak']*100:.1f}% of peak")
    print(f"  collapse anchor (tau=0 all zero) = {out['collapse_anchor']['tau0_all_zero']}")
    c = out["rise_contrast"]
    if c:
        print(f"  rise tau=0 -> tau=1: +{c['mean_rise']:.1f} hits "
              f"(paired t={c['paired_t']:.3f}, p={c['paired_p']:.4f}, n={c['n_seeds']})")
    print(f"\nwrote {args.src.parent / 'dose_analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
