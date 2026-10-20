"""GAP-45: R1 attribution across the beta endpoints.

R1's headline metric is ``hmmscan_total_hits``, a sum over records, so the
canonical comparison is an aggregate ratio with no sampling distribution
attached. This tool keeps the per-record hit counts that the upstream evaluator
already writes (``upstream_*/family_validity_per_seq.jsonl``) and pairs them by
``qid``, which gives a per-record delta, a paired bootstrap CI and an exact
two-sided sign test.

Arms
----
With ``blended = m * prior + (1 - m) * fresh`` and ``m = 1 - beta``:

===========================  =====  ==========================================
arm                          beta   restart state
===========================  =====  ==========================================
baseline                     --     no restart, 150 NFE single pass
beta = 0.1667 (default)      1/6    memory of the previous sample + fresh noise
beta = 0                      0     memory only, no fresh perturbation
beta = 1                      1     fresh perturbation only, no memory
===========================  =====  ==========================================

``beta = 0`` is the pre-registered "blend off" control. ``beta = 1`` was added
after that control turned out to be degenerate (see the audit note): it is the
only non-degenerate endpoint of the same axis.

The tool also reports sequence degeneracy (unique fraction, median Shannon
entropy, top-3 residue fraction), because an arm that collapses to a
low-complexity repeat scores 0 hits for a reason that is not about Pfam
families.

Usage::

    python3 tools/gap45_r1_blend_off_paired.py \
        --root verification_outputs/gap45-r1-blend-off-150 \
        --beta1-root verification_outputs/gap45-r1-beta1-150
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

DEFAULT_ROOT = Path("verification_outputs/gap45-r1-blend-off-150")
DEFAULT_BETA1_ROOT = Path("verification_outputs/gap45-r1-beta1-150")
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


def _hits(run_dir: Path, arm: str) -> dict[str, int] | None:
    path = run_dir / f"upstream_{arm}" / "family_validity_per_seq.jsonl"
    if not path.exists():
        return None
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


def _entropy(seq: str) -> float:
    counts = Counter(seq)
    n = len(seq)
    if n == 0:
        return float("nan")
    return -sum(v / n * math.log2(v / n) for v in counts.values())


def _top3_fraction(seq: str) -> float:
    counts = Counter(seq)
    n = len(seq)
    if n == 0:
        return float("nan")
    return sum(v for _, v in counts.most_common(3)) / n


def _median(values: list[float]) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    m = len(s) // 2
    return float(s[m]) if len(s) % 2 else float((s[m - 1] + s[m]) / 2)


def _degeneracy(path: Path) -> dict[str, float] | None:
    if not path.exists():
        return None
    recs = [seq for _, seq in _fasta_records(path)]
    if not recs:
        return None
    ents = [_entropy(s) for s in recs]
    tops = [_top3_fraction(s) for s in recs]
    return {
        "n": len(recs),
        "n_unique": len(set(recs)),
        "unique_fraction": len(set(recs)) / len(recs),
        "median_entropy_bits": _median(ents),
        "median_top3_fraction": _median(tops),
    }


def _paired(
    label: str, a: dict[str, int], b: dict[str, int], a_name: str, b_name: str,
) -> dict[str, object] | None:
    qids = sorted(set(a) & set(b))
    if not qids:
        return None
    deltas = [float(a[q] - b[q]) for q in qids]
    mean, lo, hi = _bootstrap_mean_ci(deltas)
    n_pos = sum(1 for d in deltas if d > 0)
    n_neg = sum(1 for d in deltas if d < 0)
    n_tie = len(deltas) - n_pos - n_neg
    if lo > 0:
        verdict = f"{a_name} wins (CI excludes 0)"
    elif hi < 0:
        verdict = f"{b_name} wins (CI excludes 0)"
    else:
        verdict = "tie (CI includes 0)"
    print(f"| {label} | {len(qids)} | {sum(a[q] for q in qids)} | "
          f"{sum(b[q] for q in qids)} | {mean:+.4f} | [{lo:+.4f}, {hi:+.4f}] | "
          f"{n_pos} | {n_neg} | {n_tie} | {_sign_test(n_pos, n_neg):.3g} | {verdict} |")
    return {
        "n_records": len(qids),
        "hits_a": int(sum(a[q] for q in qids)),
        "hits_b": int(sum(b[q] for q in qids)),
        "mean_delta_per_record": mean,
        "delta_ci95": [lo, hi],
        "n_a_gt_b": n_pos,
        "n_b_gt_a": n_neg,
        "n_ties": n_tie,
        "sign_test_p": _sign_test(n_pos, n_neg),
        "verdict": verdict,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--beta1-root", type=Path, default=DEFAULT_BETA1_ROOT)
    ap.add_argument("--prefix", type=Path, default=PREFIX)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    result: dict[str, object] = {"root": str(args.root), "per_seed": {}}

    print("## Per-seed totals\n")
    print("| seed | baseline | beta=0 | beta=1/6 | beta=1 |")
    print("|---:|---:|---:|---:|---:|")
    loaded: dict[int, dict[str, dict[str, int]]] = {}
    for seed in SEEDS:
        on_dir = args.root / f"seed{seed}_on"
        off_dir = args.root / f"seed{seed}_off"
        b1_dir = args.beta1_root / f"seed{seed}"
        arms = {
            "baseline": _hits(on_dir, "baseline"),
            "beta0": _hits(off_dir, "framework"),
            "beta1_6": _hits(on_dir, "framework"),
            "beta1": _hits(b1_dir, "framework"),
        }
        cells = []
        for key in ("baseline", "beta0", "beta1_6", "beta1"):
            v = arms[key]
            cells.append("—" if v is None else str(sum(v.values())))
        print(f"| {seed} | " + " | ".join(cells) + " |")
        loaded[seed] = {k: v for k, v in arms.items() if v is not None}

    print("\n## Sequence degeneracy (the beta=0 arm is not just unlucky)\n")
    print("| seed | arm | n | unique | median entropy (bits) | median top-3 residue fraction |")
    print("|---:|---|---:|---:|---:|---:|")
    for seed in SEEDS:
        paths = {
            "baseline": args.root / f"seed{seed}_on" / "baseline.fasta",
            "beta=0": args.root / f"seed{seed}_off" / "framework.fasta",
            "beta=1/6": args.root / f"seed{seed}_on" / "framework.fasta",
            "beta=1": args.beta1_root / f"seed{seed}" / "framework.fasta",
        }
        for name, p in paths.items():
            d = _degeneracy(p)
            if d is None:
                print(f"| {seed} | {name} | — | — | — | — |")
                continue
            print(f"| {seed} | {name} | {d['n']} | {d['n_unique']} | "
                  f"{d['median_entropy_bits']:.2f} | {d['median_top3_fraction']:.2f} |")
            result.setdefault("degeneracy", {}).setdefault(str(seed), {})[name] = d  # type: ignore[union-attr]

    print("\n## Paired contrasts (record level, paired by qid)\n")
    print("| contrast | n | hits A | hits B | mean Δ/record | 95% CI | A>B | B>A | ties | sign p | verdict |")
    print("|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|")
    for seed in SEEDS:
        arms = loaded.get(seed, {})
        if {"beta1_6", "baseline"} <= set(arms):
            r = _paired(f"seed {seed}: beta=1/6 vs baseline",
                        arms["beta1_6"], arms["baseline"], "beta=1/6", "baseline")
            if r:
                result["per_seed"].setdefault(str(seed), {})["beta1_6_vs_baseline"] = r  # type: ignore[index]
        if {"beta1", "baseline"} <= set(arms):
            r = _paired(f"seed {seed}: beta=1 vs baseline",
                        arms["beta1"], arms["baseline"], "beta=1", "baseline")
            if r:
                result["per_seed"].setdefault(str(seed), {})["beta1_vs_baseline"] = r  # type: ignore[index]
        if {"beta1_6", "beta1"} <= set(arms):
            r = _paired(f"seed {seed}: beta=1/6 vs beta=1",
                        arms["beta1_6"], arms["beta1"], "beta=1/6", "beta=1")
            if r:
                result["per_seed"].setdefault(str(seed), {})["beta1_6_vs_beta1"] = r  # type: ignore[index]
        if {"beta1_6", "beta0"} <= set(arms):
            r = _paired(f"seed {seed}: beta=1/6 vs beta=0",
                        arms["beta1_6"], arms["beta0"], "beta=1/6", "beta=0")
            if r:
                result["per_seed"].setdefault(str(seed), {})["beta1_6_vs_beta0"] = r  # type: ignore[index]

    # Paired-design control: within a seed the baseline arm does not see beta,
    # so the run dirs must contain byte-identical baseline FASTA. If they
    # differ the seed axis is not doing what the design assumes.
    print("\nBaseline identity control (the baseline must not depend on beta):")
    for seed in SEEDS:
        a = args.root / f"seed{seed}_on" / "baseline.fasta"
        b = args.root / f"seed{seed}_off" / "baseline.fasta"
        if not (a.exists() and b.exists()):
            print(f"- seed {seed}: pending")
            continue
        ra, rb = _fasta_records(a), _fasta_records(b)
        same = sum(1 for i in range(min(len(ra), len(rb))) if ra[i] == rb[i])
        ok = len(ra) == len(rb) and same == len(ra)
        print(f"- seed {seed}: {same}/{len(ra)} records identical "
              f"({'PASS' if ok else 'MISMATCH'})")
        result.setdefault("baseline_identity", {})[str(seed)] = {  # type: ignore[union-attr]
            "n_on": len(ra), "n_off": len(rb), "n_identical": same, "pass": ok,
        }

    # Reproducibility control: seed42 blend-on must reproduce the GAP-41b prefix.
    fresh = args.root / "seed42_on" / "framework.fasta"
    prefix = args.prefix / "framework.fasta"
    if fresh.exists() and prefix.exists():
        a = _fasta_records(prefix)
        b = _fasta_records(fresh)
        same = sum(1 for i in range(min(len(a), len(b))) if a[i] == b[i])
        ok = len(a) == len(b) and same == len(a)
        print(f"\nReproducibility control: seed42 beta=1/6 vs GAP-41b prefix — "
              f"{same}/{len(a)} records byte-identical "
              f"({'PASS' if ok else 'MISMATCH'}).")
        result["reproducibility_seed42_vs_gap41b"] = {
            "n_prefix": len(a), "n_fresh": len(b), "n_identical": same, "pass": ok,
        }

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
