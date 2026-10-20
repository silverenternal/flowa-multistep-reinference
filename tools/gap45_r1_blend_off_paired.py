"""GAP-45: pair the R1 blend-on and blend-off arms record by record.

R1's headline metric is ``hmmscan_total_hits``, a sum over records, so the
canonical comparison is an aggregate ratio with no sampling distribution
attached. This tool keeps the per-record hit counts that the upstream evaluator
already writes (``upstream_framework/family_validity_per_seq.jsonl``) and pairs
them by ``qid`` across the two arms, which gives:

* the per-record delta ``hits_on - hits_off`` and its paired bootstrap CI;
* the sign census and an exact two-sided sign test;
* the canonical aggregate totals, for continuity with the frozen R1 number.

The decision rule (``todo.json`` GAP-45) is: CI excludes 0 positive -> the blend
gets credit; CI includes 0 -> R1 stays init-attributed. The frozen R1 headline
is not changed either way.

Also checks that the freshly regenerated ``seed42`` blend-on FASTA is
byte-identical to the GAP-41b prefix, which is the same configuration.

Usage::

    python3 tools/gap45_r1_blend_off_paired.py \
        --root verification_outputs/gap45-r1-blend-off-150
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

DEFAULT_ROOT = Path("verification_outputs/gap45-r1-blend-off-150")
PREFIX = Path(
    "verification_outputs/legacy-gap40-42/gap41b-nfe150/premise/seed42_nfe150_legacy"
)
SEEDS = (42, 43, 44)
N_BOOT = 4000
BOOT_SEED = 20261020


def _per_seq(path: Path) -> dict[str, int]:
    """qid -> number of HMMER hits for that record."""
    out: dict[str, int] = {}
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out[str(rec["qid"])] = len(rec.get("hits") or [])
    return out


def _arm_hits(arm_dir: Path) -> dict[str, int]:
    path = arm_dir / "upstream_framework" / "family_validity_per_seq.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    return _per_seq(path)


def _bootstrap_mean_ci(deltas: list[float]) -> tuple[float, float, float]:
    import numpy as np

    arr = np.asarray(deltas, dtype=np.float64)
    if arr.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, arr.size, size=(N_BOOT, arr.size))
    means = arr[idx].mean(axis=1)
    return (
        float(arr.mean()),
        float(np.quantile(means, 0.025)),
        float(np.quantile(means, 0.975)),
    )


def _sign_test(n_pos: int, n_neg: int) -> float:
    """Exact two-sided binomial sign test, ties already dropped."""
    from math import comb

    n = n_pos + n_neg
    if n == 0:
        return float("nan")
    k = min(n_pos, n_neg)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return float(min(1.0, 2.0 * tail))


def _fasta_records(path: Path) -> list[tuple[str, str]]:
    recs: list[tuple[str, str]] = []
    name = None
    seq: list[str] = []
    with path.open() as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if name is not None:
                    recs.append((name, "".join(seq)))
                name, seq = line, []
            elif line:
                seq.append(line)
    if name is not None:
        recs.append((name, "".join(seq)))
    return recs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--prefix", type=Path, default=PREFIX)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    result: dict[str, object] = {"root": str(args.root), "per_seed": {}}

    print("| seed | n records | hits off | hits on | mean Δ/record | 95% CI | "
          "on>off | off>on | ties | sign p |")
    print("|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|")

    pooled_deltas: list[float] = []
    for seed in SEEDS:
        off_dir = args.root / f"seed{seed}_off"
        on_dir = args.root / f"seed{seed}_on"
        if not off_dir.exists() or not on_dir.exists():
            print(f"| {seed} | — | — | — | — | — | — | — | — | pending |")
            continue
        off = _arm_hits(off_dir)
        on = _arm_hits(on_dir)
        qids = sorted(set(off) & set(on))
        if not qids:
            print(f"| {seed} | 0 | — | — | — | — | — | — | — | no shared qid |")
            continue
        deltas = [float(on[q] - off[q]) for q in qids]
        pooled_deltas.extend(deltas)
        mean, lo, hi = _bootstrap_mean_ci(deltas)
        n_pos = sum(1 for d in deltas if d > 0)
        n_neg = sum(1 for d in deltas if d < 0)
        n_tie = len(deltas) - n_pos - n_neg
        p_sign = _sign_test(n_pos, n_neg)
        print(f"| {seed} | {len(qids)} | {sum(off[q] for q in qids)} | "
              f"{sum(on[q] for q in qids)} | {mean:+.4f} | [{lo:+.4f}, {hi:+.4f}] | "
              f"{n_pos} | {n_neg} | {n_tie} | {p_sign:.3g} |")
        result["per_seed"][str(seed)] = {  # type: ignore[index]
            "n_records": len(qids),
            "hits_off": int(sum(off[q] for q in qids)),
            "hits_on": int(sum(on[q] for q in qids)),
            "mean_delta_per_record": mean,
            "delta_ci95": [lo, hi],
            "n_on_gt_off": n_pos,
            "n_off_gt_on": n_neg,
            "n_ties": n_tie,
            "sign_test_p": p_sign,
        }

    if pooled_deltas:
        mean, lo, hi = _bootstrap_mean_ci(pooled_deltas)
        n_pos = sum(1 for d in pooled_deltas if d > 0)
        n_neg = sum(1 for d in pooled_deltas if d < 0)
        p_sign = _sign_test(n_pos, n_neg)
        print(f"\nPooled over {len(pooled_deltas)} records: mean Δ = {mean:+.4f} "
              f"per record, 95% CI [{lo:+.4f}, {hi:+.4f}], "
              f"on>off {n_pos}, off>on {n_neg}, ties {len(pooled_deltas)-n_pos-n_neg}, "
              f"sign p = {p_sign:.3g}.")
        if lo > 0:
            verdict = "blend gets credit (CI excludes 0, positive)"
        elif hi < 0:
            verdict = "blend hurts (CI excludes 0, negative)"
        else:
            verdict = "inconclusive: R1 stays init-attributed (CI includes 0)"
        print(f"Verdict: **{verdict}**.")
        result["pooled"] = {
            "n_records": len(pooled_deltas),
            "mean_delta_per_record": mean,
            "delta_ci95": [lo, hi],
            "n_on_gt_off": n_pos,
            "n_off_gt_on": n_neg,
            "sign_test_p": p_sign,
            "verdict": verdict,
        }

    # Reproducibility control: seed42 blend-on must reproduce the GAP-41b prefix.
    fresh = args.root / "seed42_on" / "framework.fasta"
    prefix = args.prefix / "framework.fasta"
    if fresh.exists() and prefix.exists():
        a = _fasta_records(prefix)
        b = _fasta_records(fresh)
        same = sum(1 for i in range(min(len(a), len(b))) if a[i] == b[i])
        ok = len(a) == len(b) and same == len(a)
        print(f"\nReproducibility control: seed42 blend-on vs GAP-41b prefix — "
              f"{same}/{len(a)} records byte-identical "
              f"({'PASS' if ok else 'MISMATCH'}).")
        result["reproducibility_seed42_on_vs_gap41b"] = {
            "n_prefix": len(a), "n_fresh": len(b), "n_identical": same, "pass": ok,
        }

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
