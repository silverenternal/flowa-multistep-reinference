"""GAP-41 canonical N=1000 3-seed analysis: R6 tier-aware n_cap applied to R1.

Statistics protocol mirrors GAP-40 (docs/audit/gap40-lineageflow-classifier-aware-restart.md
§4b.2 / §4b.3) so the two sweeps are directly comparable:

  Seed-level (n=3, df=2), canonical R1 protocol
  (docs/audit/wave280-p-r1-sweep-result.md §2.3):
    mean_diff    = mean of per-seed (armA_total - armB_total)
    std_paired   = sample std (ddof=1) of the 3 per-seed diffs
    d_z          = mean_diff / std_paired
    t            = mean_diff / (std_paired / sqrt(3))
    p_two_sided  = 2 * t.sf(|t|, df=2)
    p_bonf_rlevel = min(1, p_two_sided * 16)
    STRONG iff d_z > 0.8 AND p_bonf_rlevel < 0.003125 AND 3/3 dir-consistent

  Per-record paired t (df=999) per seed -> DerSimonian-Laird random-effects meta.

Arms:
  tier      = /home/hugo/gap41-n1000/seed{seed}_tier   (NEW, this sweep)
  baseline  = /home/hugo/gap40-n1000-work/seed{seed}_legacy/baseline.*
  legacy    = /home/hugo/gap40-n1000-work/seed{seed}_legacy/framework.*
  car       = /home/hugo/gap40-n1000-work/seed{seed}_car/framework.*
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import scipy.stats as st

TIER = Path("/home/hugo/gap41-n1000")
REF = Path("/home/hugo/gap40-n1000-work")
SEEDS = (42, 43, 44)


def per_record(fasta: Path, tblout: Path) -> np.ndarray:
    names = [
        ln[1:].strip()
        for ln in fasta.read_text().splitlines()
        if ln.startswith(">")
    ]
    c: Counter = Counter()
    for line in tblout.read_text().splitlines():
        if line and not line.startswith("#"):
            c[line.split()[2]] += 1
    return np.array([c.get(n, 0) for n in names], dtype=float)


def load() -> dict:
    data: dict = {}
    for seed in SEEDS:
        arm = {}
        arm["tier"] = per_record(
            TIER / f"seed{seed}_tier" / "framework.fasta",
            TIER / f"seed{seed}_tier" / "framework.tblout",
        )
        arm["baseline"] = per_record(
            REF / f"seed{seed}_legacy" / "baseline.fasta",
            REF / f"seed{seed}_legacy" / "baseline.tblout",
        )
        arm["legacy"] = per_record(
            REF / f"seed{seed}_legacy" / "framework.fasta",
            REF / f"seed{seed}_legacy" / "framework.tblout",
        )
        arm["car"] = per_record(
            REF / f"seed{seed}_car" / "framework.fasta",
            REF / f"seed{seed}_car" / "framework.tblout",
        )
        data[seed] = arm
    return data


def seed_stats(diffs: list[float]) -> dict:
    a = np.asarray(diffs, dtype=float)
    mean = float(a.mean())
    sd = float(a.std(ddof=1)) if len(a) > 1 else 0.0
    d_z = mean / sd if sd > 0 else float("inf") * np.sign(mean)
    if sd > 0:
        t = mean / (sd / np.sqrt(len(a)))
        p = float(2 * st.t.sf(abs(t), df=len(a) - 1))
    else:
        t = float("inf") * np.sign(mean)
        p = 0.0 if mean != 0 else 1.0
    return {
        "per_seed_diffs": [float(x) for x in a],
        "mean_diff": mean,
        "std_paired": sd,
        "d_z": float(d_z),
        "t": float(t),
        "p_two_sided": p,
        "p_bonf_rlevel": min(1.0, p * 16),
        "direction_consistent": bool(all(x > 0 for x in a) or all(x < 0 for x in a)),
    }


def paired_dz(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Per-record paired Cohen's d_z and its two-sided p (df = n-1)."""
    d = a - b
    n = d.size
    sd = d.std(ddof=1)
    if sd == 0:
        return 0.0, 1.0
    dz = d.mean() / sd
    t = d.mean() / (sd / np.sqrt(n))
    p = float(2 * st.t.sf(abs(t), df=n - 1))
    return float(dz), p


def dl_meta(dzs: list[float], ns: list[int]) -> dict:
    """DerSimonian-Laird random-effects meta of per-seed d_z (paired).

    SE(d_z) = sqrt(1/n + d^2 / (2n)).
    """
    d = np.asarray(dzs, dtype=float)
    se = np.sqrt(1.0 / np.asarray(ns, dtype=float) + d**2 / (2.0 * np.asarray(ns, dtype=float)))
    v = se**2
    w = 1.0 / v
    fe = float((w * d).sum() / w.sum())
    q = float((w * (d - fe) ** 2).sum())
    k = d.size
    c = float(w.sum() - (w**2).sum() / w.sum())
    tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
    wstar = 1.0 / (v + tau2)
    pooled = float((wstar * d).sum() / wstar.sum())
    se_pooled = float(np.sqrt(1.0 / wstar.sum()))
    z = pooled / se_pooled if se_pooled > 0 else 0.0
    p = float(2 * st.norm.sf(abs(z)))
    return {
        "d_pooled": pooled,
        "se": se_pooled,
        "z": float(z),
        "p_two": p,
        "p_bonf_k7": min(1.0, p * 7),
        "tau2": tau2,
        "q": q,
    }


def main() -> int:
    data = load()
    result: dict = {"per_seed": {}, "seed_level": {}, "per_record_dl": {}}
    arms = ("baseline", "legacy", "car", "tier")
    totals = {a: {} for a in arms}

    for seed in SEEDS:
        result["per_seed"][str(seed)] = {}
        for arm in arms:
            v = data[seed][arm]
            totals[arm][seed] = float(v.sum())
            result["per_seed"][str(seed)][arm] = {
                "total_hits": int(v.sum()),
                "records_ge1": int((v > 0).sum()),
                "hits_per_record": float(v.mean()),
            }

    comparisons = (
        ("tier_vs_legacy", "tier", "legacy"),
        ("tier_vs_baseline", "tier", "baseline"),
        ("tier_vs_car", "tier", "car"),
        ("legacy_vs_baseline", "legacy", "baseline"),
        ("car_vs_legacy", "car", "legacy"),
    )
    for label, a_arm, b_arm in comparisons:
        diffs = [totals[a_arm][s] - totals[b_arm][s] for s in SEEDS]
        result["seed_level"][label] = seed_stats(diffs)

    for label, a_arm, b_arm in comparisons:
        dzs, ps = [], []
        for seed in SEEDS:
            dz, p = paired_dz(data[seed][a_arm], data[seed][b_arm])
            dzs.append(dz)
            ps.append(p)
        meta = dl_meta(dzs, [data[s][a_arm].size for s in SEEDS])
        meta["per_seed_dz"] = dzs
        meta["per_seed_p"] = ps
        result["per_record_dl"][label] = meta

    result["totals"] = {k: {str(s): v for s, v in d.items()} for k, d in totals.items()}
    out = TIER / "analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
