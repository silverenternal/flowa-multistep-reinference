#!/usr/bin/env python3
"""GAP-48 — K7 two-arm novelty, paired per record.

The K7 headline (``baseline 466/1000 vs framework 37/1000`` novel at
``pctid < 30``) is two marginal counts from one seed. This tool turns
them into a **paired per-record** comparison over the same frozen
``mmseqs2`` m8 files and reports:

* the paired 2x2 table (both novel / framework-only / baseline-only /
  neither) at each threshold;
* the paired risk difference ``p_fw - p_bl`` with a Newcombe hybrid
  score 95% CI (the correct interval for paired proportions);
* the exact McNemar binomial p-value;
* the paired t on the per-record binary delta (for continuity with the
  repo's other cells);
* the paired difference in ``mean_max_pctid`` among records that have
  a hit in both arms (the "framework recapitulates known Pfam
  structure" signal).

Pairing key: the m8 query ids are ``baseline_seed<I>|family=<F>`` and
``framework_seed<I>|family=<F>``. The record index ``I`` is the same
record in both arms (the generator emits both arms from one record
loop), and the tool asserts that the family at every shared index
matches before computing anything.

Usage:
    python tools/gap48_k7_two_arm_novelty.py \
        --baseline-m8 verification_outputs/novelty_pctid_w166_q3_2026/baseline/n1000_full_loose.m8 \
        --framework-m8 verification_outputs/novelty_pctid_w166_q3_2026/framework/n1000_full_loose.m8 \
        --n-total 1000 --out verification_outputs/gap48-k7-two-arm/paired.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

_Z95 = 1.959963984540054
_QID_RE = re.compile(r"^(?:baseline|framework)_seed(\d+)\|family=(\S+)$")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _wilson(p: float, n: int) -> tuple[float, float]:
    """Wilson score interval for a single binomial proportion."""
    if n <= 0:
        return (0.0, 1.0)
    denom = 1.0 + _Z95 * _Z95 / n
    centre = (p + _Z95 * _Z95 / (2.0 * n)) / denom
    half = (
        _Z95
        * math.sqrt(p * (1.0 - p) / n + _Z95 * _Z95 / (4.0 * n * n))
        / denom
    )
    return (max(0.0, centre - half), min(1.0, centre + half))


def _newcombe_paired(
    a: int, b: int, c: int, d: int,
) -> tuple[float, float, float, float, float]:
    """Paired risk difference ``p_fw - p_bl`` with a Newcombe 95% CI.

    ``a`` both novel, ``b`` framework-only novel, ``c`` baseline-only
    novel, ``d`` neither. Method 10 of Newcombe (1998), which keeps
    the interval inside ``[-1, 1]`` and accounts for the pairing via
    the phi coefficient.
    """
    n = a + b + c + d
    if n <= 0:
        return (0.0, 0.0, -1.0, 1.0, 0.0)
    p_fw = (a + b) / n
    p_bl = (a + c) / n
    delta = p_fw - p_bl
    l1, u1 = _wilson(p_fw, n)
    l2, u2 = _wilson(p_bl, n)
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    phi = (a * d - b * c) / denom if denom > 0 else 0.0
    lower = delta - math.sqrt(
        max(0.0, (p_fw - l1) ** 2
            - 2.0 * phi * (p_fw - l1) * (p_bl - u2)
            + (u2 - p_bl) ** 2)
    )
    upper = delta + math.sqrt(
        max(0.0, (u1 - p_fw) ** 2
            - 2.0 * phi * (u1 - p_fw) * (p_bl - l2)
            + (p_bl - l2) ** 2)
    )
    return (delta, max(-1.0, lower), min(1.0, upper), phi, p_fw - p_bl)


def _mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value (binomial on the discordant pairs)."""
    from scipy.stats import binomtest  # local import: optional dependency

    n = b + c
    if n == 0:
        return 1.0
    return float(binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue)


def _paired_t(deltas: list[float]) -> dict[str, float]:
    """Mean / sd / SE / t / two-sided p for a paired-difference sample."""
    from scipy.stats import t as t_dist  # local import

    n = len(deltas)
    if n < 2:
        return {"n": float(n), "mean": 0.0, "sd": 0.0, "se": 0.0,
                "t": 0.0, "df": 0.0, "p": 1.0}
    mean = sum(deltas) / n
    var = sum((x - mean) ** 2 for x in deltas) / (n - 1)
    sd = math.sqrt(var)
    se = sd / math.sqrt(n)
    if se == 0.0:
        return {"n": float(n), "mean": mean, "sd": sd, "se": 0.0,
                "t": 0.0, "df": float(n - 1), "p": 1.0}
    t_stat = mean / se
    p = float(2.0 * t_dist.sf(abs(t_stat), df=n - 1))
    return {"n": float(n), "mean": mean, "sd": sd, "se": se,
            "t": t_stat, "df": float(n - 1), "p": p}


def _index_map(
    per_qid: dict[str, float], arm: str,
) -> dict[int, tuple[str, float]]:
    out: dict[int, tuple[str, float]] = {}
    bad: list[str] = []
    for qid, pct in per_qid.items():
        m = _QID_RE.match(qid)
        if m is None:
            bad.append(qid)
            continue
        idx = int(m.group(1))
        if idx in out:
            raise ValueError(f"{arm}: duplicate record index {idx}")
        out[idx] = (m.group(2), float(pct))
    if bad:
        raise ValueError(
            f"{arm}: {len(bad)} query ids do not match the "
            f"'{{arm}}_seed<I>|family=<F>' pattern, e.g. {bad[:3]}"
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-m8", type=Path, required=True)
    ap.add_argument("--framework-m8", type=Path, required=True)
    ap.add_argument("--n-total", type=int, default=1000)
    ap.add_argument("--thresholds", type=str, default="20,30,50")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent / "lineageflow"))
    from novelty_metric_pctid import parse_m8_max_pctid  # type: ignore

    bl = _index_map(parse_m8_max_pctid(str(args.baseline_m8)), "baseline")
    fw = _index_map(parse_m8_max_pctid(str(args.framework_m8)), "framework")

    shared = sorted(set(bl) & set(fw))
    family_mismatch = [i for i in shared if bl[i][0] != fw[i][0]]
    if family_mismatch:
        raise ValueError(
            f"{len(family_mismatch)} record indices disagree on family "
            f"between arms, e.g. {family_mismatch[:5]}"
        )
    out_of_range = [i for i in set(bl) | set(fw)
                    if i < 0 or i >= int(args.n_total)]
    if out_of_range:
        raise ValueError(
            f"{len(out_of_range)} record indices outside [0, {args.n_total})"
        )

    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]

    def _max_pctid(m: dict[int, tuple[str, float]], i: int) -> float | None:
        return m[i][1] if i in m else None

    per_threshold: dict[str, Any] = {}
    for th in thresholds:
        a = b = c = d = 0
        deltas: list[float] = []
        for i in range(int(args.n_total)):
            mb = _max_pctid(bl, i)
            mf = _max_pctid(fw, i)
            nb = 1 if (mb is None or mb < th) else 0
            nf = 1 if (mf is None or mf < th) else 0
            deltas.append(float(nf - nb))
            if nb and nf:
                a += 1
            elif nf and not nb:
                b += 1
            elif nb and not nf:
                c += 1
            else:
                d += 1
        delta, lo, hi, phi, _ = _newcombe_paired(a, b, c, d)
        tt = _paired_t(deltas)
        per_threshold[f"pctid_{th:g}"] = {
            "threshold": th,
            "both_novel": a,
            "framework_only_novel": b,
            "baseline_only_novel": c,
            "neither_novel": d,
            "n_baseline_novel": a + c,
            "n_framework_novel": a + b,
            "baseline_novel_rate": (a + c) / int(args.n_total),
            "framework_novel_rate": (a + b) / int(args.n_total),
            "delta_rate_fw_minus_bl": delta,
            "delta_ci95_newcombe": [lo, hi],
            "phi": phi,
            "mcnemar_exact_p": _mcnemar_exact(b, c),
            "paired_t": tt,
        }

    # "Recapitulates known structure": paired max-pctid among records
    # that have a hit in both arms.
    both_hits = [i for i in shared]
    pct_deltas = [fw[i][1] - bl[i][1] for i in both_hits]
    pct_stats = _paired_t(pct_deltas)

    family_counts: dict[str, dict[str, int]] = {}
    for i in shared:
        fam = bl[i][0]
        row = family_counts.setdefault(fam, {"n_both_hit": 0})
        row["n_both_hit"] += 1

    payload: dict[str, Any] = {
        "analysis": "gap48-k7-two-arm-novelty",
        "date_utc": "2026-10-18",
        "inputs": {
            "baseline_m8": str(args.baseline_m8),
            "baseline_m8_sha256": _sha256(args.baseline_m8),
            "framework_m8": str(args.framework_m8),
            "framework_m8_sha256": _sha256(args.framework_m8),
        },
        "n_total": int(args.n_total),
        "n_baseline_with_hits": len(bl),
        "n_framework_with_hits": len(fw),
        "n_both_with_hits": len(shared),
        "n_baseline_only_hits": len(set(bl) - set(fw)),
        "n_framework_only_hits": len(set(fw) - set(bl)),
        "pairing": "record index (arm prefix stripped); family agreement asserted",
        "per_threshold": per_threshold,
        "mean_max_pctid_paired_both_hits": pct_stats,
        "family_counts_both_hits": family_counts,
    }

    print(json.dumps({k: v for k, v in payload.items()
                      if k not in ("per_threshold",)}, indent=2))
    print("\nthreshold  n_bl  n_fw   delta   95% CI (Newcombe)      "
          "McNemar p")
    for row in per_threshold.values():
        lo, hi = row["delta_ci95_newcombe"]
        print(
            f"{row['threshold']:>8.0f}  {row['n_baseline_novel']:>4d}  "
            f"{row['n_framework_novel']:>4d}  {row['delta_rate_fw_minus_bl']:>+7.4f}  "
            f"[{lo:+.4f}, {hi:+.4f}]  {row['mcnemar_exact_p']:.3e}"
        )

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
