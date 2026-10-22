#!/usr/bin/env python3
"""GAP-69 report — paired comparison of the profile-aware init against init-only.

Reads the per-record ``family_validity_per_seq.jsonl`` emitted by the upstream
evaluator for each arm and answers the pre-registered questions in
``docs/audit/gap69-lineageflow-profile.md`` §0.4:

* rule 1 (escalation) — ``H_C >= 1.15 * H_B`` with a paired 95 % bootstrap CI
  on ``H_C - H_B`` that excludes 0;
* primary mechanistic readout — ``intended_hit_rate_evalue`` (0.000 for both
  pre-GAP-69 arms);
* the pure-profile ceiling (arm D, no model).

Pairing is by ``qid``. The arms are record-paired only if the per-record
lengths agree, which the tool asserts (same ``(family, length)`` RNG stream).

Usage
-----
    PYTHONPATH=. python3 tools/gap69_report.py \
        --profile-run verification_outputs/gap69-lineageflow-profile/seed42 \
        --init-only-run verification_outputs/gap58-r1-beta1-n1000/seed42 \
        --hmm-draw-run verification_outputs/gap69-lineageflow-profile/seed42 \
        --out verification_outputs/gap69-lineageflow-profile/report.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ARMS = ("baseline", "framework")


def _load_per_seq(run_dir: Path, arm: str) -> dict[str, dict]:
    path = run_dir / f"upstream_{arm}" / "family_validity_per_seq.jsonl"
    if not path.exists():
        raise SystemExit(f"missing_per_seq:{path}")
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[str(rec["qid"])] = rec
    return out


def _load_summary(run_dir: Path, arm: str) -> dict:
    path = run_dir / f"upstream_{arm}" / "family_validity.json"
    return json.loads(path.read_text())


def _hits(rec: dict) -> int:
    return len(rec.get("hits") or [])


def _paired(a: list[float], b: list[float], *, n_boot: int = 20000, seed: int = 42) -> dict:
    """Paired difference statistics: mean, sd, t, p (normal approx), CI95."""
    if len(a) != len(b):
        raise SystemExit(f"pairing_length_mismatch:{len(a)}!={len(b)}")
    n = len(a)
    d = [x - y for x, y in zip(a, b, strict=True)]
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1) if n > 1 else float("nan")
    sd = math.sqrt(var) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t = mean / se if se and math.isfinite(se) and se > 0 else float("nan")
    p = 2.0 * (1.0 - _norm_cdf(abs(t))) if math.isfinite(t) else float("nan")

    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += d[rng.randrange(n)]
        boots.append(s / n)
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[int(0.975 * n_boot) - 1]
    return {
        "n": n,
        "mean_diff": mean,
        "sd_diff": sd,
        "se_diff": se,
        "t": t,
        "p_normal": p,
        "ci95_boot": [lo, hi],
        "ci_excludes_zero": bool(lo > 0.0 or hi < 0.0),
    }


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile-run", type=Path, required=True,
                    help="run dir of the GAP-69 arm C (init_profile=conservation)")
    ap.add_argument("--init-only-run", type=Path, required=True,
                    help="run dir of the D-004b init-only arm B (beta=1.0)")
    ap.add_argument("--hmm-draw-run", type=Path, default=None,
                    help="run dir holding arm D's hmm_draw.fasta + upstream_hmm_draw")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    seq_c = {a: _load_per_seq(args.profile_run, a) for a in ARMS}
    seq_b = {a: _load_per_seq(args.init_only_run, a) for a in ARMS}
    sum_c = {a: _load_summary(args.profile_run, a) for a in ARMS}
    sum_b = {a: _load_summary(args.init_only_run, a) for a in ARMS}

    # -- pairing guard: identical qid sets and identical per-record lengths ----
    for arm in ARMS:
        if set(seq_c[arm]) != set(seq_b[arm]):
            raise SystemExit(f"qid_set_mismatch:{arm}")
        for qid, rec in seq_c[arm].items():
            if int(rec["length"]) != int(seq_b[arm][qid]["length"]):
                raise SystemExit(f"length_mismatch:{arm}:{qid}")
            if str(rec["header"]) != str(seq_b[arm][qid]["header"]):
                raise SystemExit(f"header_mismatch:{arm}:{qid}")

    qids = sorted(seq_c["framework"], key=lambda q: int(q[1:]))

    def _vec(seq: dict[str, dict], key: str) -> list[float]:
        return [float(_hits(seq[q])) for q in qids]

    def _intended(seq: dict[str, dict]) -> list[float]:
        return [1.0 if seq[q].get("intended_hit_evalue") else 0.0 for q in qids]

    h_b = _vec(seq_b["framework"], "hits")
    h_c = _vec(seq_c["framework"], "hits")
    i_b = _intended(seq_b["framework"])
    i_c = _intended(seq_c["framework"])

    total_b = int(sum(h_b))
    total_c = int(sum(h_c))
    ratio = (total_c / total_b) if total_b else float("nan")
    stats_hits = _paired(h_c, h_b)
    stats_intended = _paired(i_c, i_b)

    rule1_ratio = bool(total_c >= 1.15 * total_b)
    rule1 = bool(rule1_ratio and stats_hits["ci_excludes_zero"])

    arm_d: dict | None = None
    if args.hmm_draw_run is not None:
        try:
            d_sum = _load_summary(args.hmm_draw_run, "hmm_draw")
            arm_d = {
                "hmmscan_total_hits": d_sum.get("hmmscan_total_hits"),
                "hmmscan_unique_queries": d_sum.get("hmmscan_unique_queries"),
                "intended_hit_rate_evalue": d_sum.get("intended_hit_rate_evalue"),
                "top1_family_accuracy": d_sum.get("top1_family_accuracy"),
                "topk_contains_intended": d_sum.get("topk_contains_intended"),
            }
        except (SystemExit, FileNotFoundError):
            arm_d = None

    i_c_rate = float(sum(i_c) / len(i_c)) if i_c else 0.0
    i_b_rate = float(sum(i_b) / len(i_b)) if i_b else 0.0

    if rule1 and i_c_rate > 0.0:
        verdict = "SUPPORTED_AT_ONE_SEED_ESCALATE"
    elif rule1:
        verdict = "HEADLINE_GAIN_NO_FAMILY_IDENTITY"
    elif i_c_rate > 0.0:
        verdict = "FAMILY_IDENTITY_ONLY"
    else:
        verdict = "NO_PROFILE_GAIN"
    if (
        arm_d is not None
        and arm_d.get("hmmscan_total_hits") is not None
        and float(arm_d["hmmscan_total_hits"]) >= float(total_c)
    ):
        verdict = "MODEL_REDUNDANT"

    report = {
        "pre_registration": "docs/audit/gap69-lineageflow-profile.md §0",
        "profile_run": str(args.profile_run),
        "init_only_run": str(args.init_only_run),
        "n_records": len(qids),
        "arms": {
            "A_baseline": {
                "hmmscan_total_hits": sum_b["baseline"].get("hmmscan_total_hits"),
                "intended_hit_rate_evalue": sum_b["baseline"].get("intended_hit_rate_evalue"),
            },
            "B_init_only": {
                "hmmscan_total_hits": total_b,
                "hmmscan_unique_queries": sum_b["framework"].get("hmmscan_unique_queries"),
                "intended_hit_rate_evalue": i_b_rate,
                "top1_family_accuracy": sum_b["framework"].get("top1_family_accuracy"),
                "topk_contains_intended": sum_b["framework"].get("topk_contains_intended"),
            },
            "C_conservation": {
                "hmmscan_total_hits": total_c,
                "hmmscan_unique_queries": sum_c["framework"].get("hmmscan_unique_queries"),
                "intended_hit_rate_evalue": i_c_rate,
                "top1_family_accuracy": sum_c["framework"].get("top1_family_accuracy"),
                "topk_contains_intended": sum_c["framework"].get("topk_contains_intended"),
            },
            "D_hmm_draw_no_model": arm_d,
        },
        "comparison_C_vs_B": {
            "total_hits_ratio": ratio,
            "rule1_ratio_ge_1.15": rule1_ratio,
            "rule1_ci_excludes_zero": stats_hits["ci_excludes_zero"],
            "rule1_fires": rule1,
            "hits_paired": stats_hits,
            "intended_rate_paired": stats_intended,
        },
        "verdict": verdict,
        "escalate_to_seeds_43_44": rule1,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
