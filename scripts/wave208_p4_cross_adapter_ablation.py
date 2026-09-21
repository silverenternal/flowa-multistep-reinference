#!/usr/bin/env python3
"""Wave 208 P4 cross-adapter ablation.

Per DeepSeek P4 priority #4: extend CLM-057 (paper-quantity vs cosine-only
vs fixed-threshold) from kanzi synthetic n=30 to k6 + LineageFlow + FlowMol3.

Source data already in repo:
  * kanzi n=30 paper-vs-cosine:        verification_outputs/wave190-p2-kanzi-n30.json
  * lineageflow n=30 paper-vs-cosine:  verification_outputs/wave190-p3-lineageflow-n30.json
  * k6 per-record framework-vs-baseline (N=1000, no paper-vs-cosine split):
      verification_outputs/wave198-p2-per-record-paired.{csv,json}
      verification_outputs/wave203-p3-k6-cluster-robust.{csv,json}
  * flowmol3 per-record framework-vs-baseline (N=200, no paper-vs-cosine split):
      verification_outputs/wave208-p2-flowmol3-sanity.{csv,json}
  * LineageFlow per-record framework-vs-baseline (N=574, no paper-vs-cosine split):
      verification_outputs/wave202-p5-lineageflow-per-record.{csv,json}

The "fixed-threshold" arm maps to the Wave 52 `no_paper_quantity_scheduler` arm
(memory_fraction held constant at 0.5 = uniform n_cap). The Wave 72
`heuristic_ablation_memory_fraction` shows that the kanzi composite is
byte-stable across m in {0.056, 0.5} (range = 0.0) — so the paper-quantity
scheduler and the fixed-threshold arm are byte-equivalent on the kanzi
synthetic axis at the same NFE. For lineageflow + k6 + FlowMol3 no
fixed-threshold ablation sweep exists; we report it as NOT_RUN.

Outputs:
  * verification_outputs/wave208-p4-cross-adapter-ablation.csv
  * verification_outputs/wave208-p4-cross-adapter-ablation.json
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = ROOT / "verification_outputs"
CSV_PATH = OUT_DIR / "wave208-p4-cross-adapter-ablation.csv"
JSON_PATH = OUT_DIR / "wave208-p4-cross-adapter-ablation.json"

ALPHA_BONFERRONI_PAPER_VS_COSINE = 0.025  # two primary axes (L2, entropy)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r") as fh:
        return json.load(fh)


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r") as fh:
        return list(csv.DictReader(fh))


def _row(
    *,
    adapter: str,
    metric: str,
    n_paired: int,
    paper_quantity_d_z: float | None,
    cosine_only_d_z: float | None,
    fixed_threshold_d_z: float | None,
    paper_vs_cosine_d_z: float | None,
    paper_vs_cosine_p: float | None,
    paper_vs_cosine_cluster_robust_p: float | None,
    paper_vs_cosine_bonferroni_significant: bool | None,
    paper_vs_cosine_verdict: str,
    data_availability: str,
    nfe_per_pass: int,
    source: str,
) -> dict[str, Any]:
    return {
        "adapter": adapter,
        "metric": metric,
        "n_paired": n_paired,
        "paper_quantity_d_z": paper_quantity_d_z,
        "cosine_only_d_z": cosine_only_d_z,
        "fixed_threshold_d_z": fixed_threshold_d_z,
        "paper_vs_cosine_d_z": paper_vs_cosine_d_z,
        "paper_vs_cosine_p": paper_vs_cosine_p,
        "paper_vs_cosine_cluster_robust_p": paper_vs_cosine_cluster_robust_p,
        "paper_vs_cosine_bonferroni_significant": paper_vs_cosine_bonferroni_significant,
        "paper_vs_cosine_verdict": paper_vs_cosine_verdict,
        "data_availability": data_availability,
        "nfe_per_pass": nfe_per_pass,
        "source": source,
    }


def kanzi_row() -> dict[str, Any]:
    """kanzi synthetic n=30 (Wave 190 P2) — full paper-vs-cosine data exists.

    Note: per-arm vs-baseline d_z requires per-seed diff data which is not
    reported in the Wave 190 P2 JSON (the JSON aggregates mean/std across
    seeds). We report the paper-vs-cosine d_z (the load-bearing comparison)
    and leave per-arm d_z as None rather than fabricating within-subject
    statistics.
    """
    j = _load_json(OUT_DIR / "wave190-p2-kanzi-n30.json")
    cmp_ = j["comparisons"]["paper_quantities_vs_cosine"]
    return _row(
        adapter="kanzi",
        metric="endpoint_L2_paired_diff_paper_vs_cosine",
        n_paired=30,
        paper_quantity_d_z=None,
        cosine_only_d_z=None,
        fixed_threshold_d_z=None,  # Wave 72 memory_fraction ablation: byte-stable at kanzi NFE=1000
        paper_vs_cosine_d_z=cmp_["endpoint_l2_cohens_d"],
        paper_vs_cosine_p=cmp_["endpoint_l2_p_value"],
        paper_vs_cosine_cluster_robust_p=None,
        paper_vs_cosine_bonferroni_significant=cmp_["bonferroni_significant"],
        paper_vs_cosine_verdict=j["verdict"],
        data_availability="full",
        nfe_per_pass=j["nfe"],
        source="verification_outputs/wave190-p2-kanzi-n30.json",
    )


def kanzi_entropy_row() -> dict[str, Any]:
    j = _load_json(OUT_DIR / "wave190-p2-kanzi-n30.json")
    cmp_ = j["comparisons"]["paper_quantities_vs_cosine"]
    return _row(
        adapter="kanzi",
        metric="per_position_entropy_reduction_paired_diff_paper_vs_cosine",
        n_paired=30,
        paper_quantity_d_z=None,
        cosine_only_d_z=None,
        fixed_threshold_d_z=None,
        paper_vs_cosine_d_z=cmp_["entropy_cohens_d"],
        paper_vs_cosine_p=cmp_["entropy_p_value"],
        paper_vs_cosine_cluster_robust_p=None,
        paper_vs_cosine_bonferroni_significant=cmp_["bonferroni_significant_entropy"],
        paper_vs_cosine_verdict=j["verdict"],
        data_availability="full",
        nfe_per_pass=j["nfe"],
        source="verification_outputs/wave190-p2-kanzi-n30.json",
    )


def lineageflow_row() -> dict[str, Any]:
    """lineageflow synthetic n=30 (Wave 190 P3) — full paper-vs-cosine data exists."""
    j = _load_json(OUT_DIR / "wave190-p3-lineageflow-n30.json")
    cmp_ = j["comparisons"]["paper_quantities_vs_cosine"]
    return _row(
        adapter="lineageflow",
        metric="endpoint_L2_paired_diff_paper_vs_cosine",
        n_paired=30,
        paper_quantity_d_z=None,
        cosine_only_d_z=None,
        fixed_threshold_d_z=None,
        paper_vs_cosine_d_z=cmp_["endpoint_l2_cohens_d"],
        paper_vs_cosine_p=cmp_["endpoint_l2_p_value"],
        paper_vs_cosine_cluster_robust_p=None,
        paper_vs_cosine_bonferroni_significant=cmp_["bonferroni_significant"],
        paper_vs_cosine_verdict=j["verdict"],
        data_availability="full",
        nfe_per_pass=j["nfe"],
        source="verification_outputs/wave190-p3-lineageflow-n30.json",
    )


def lineageflow_entropy_row() -> dict[str, Any]:
    j = _load_json(OUT_DIR / "wave190-p3-lineageflow-n30.json")
    cmp_ = j["comparisons"]["paper_quantities_vs_cosine"]
    return _row(
        adapter="lineageflow",
        metric="per_position_entropy_reduction_paired_diff_paper_vs_cosine",
        n_paired=30,
        paper_quantity_d_z=None,
        cosine_only_d_z=None,
        fixed_threshold_d_z=None,
        paper_vs_cosine_d_z=cmp_["entropy_cohens_d"],
        paper_vs_cosine_p=cmp_["entropy_p_value"],
        paper_vs_cosine_cluster_robust_p=None,
        paper_vs_cosine_bonferroni_significant=cmp_["bonferroni_significant_entropy"],
        paper_vs_cosine_verdict=j["verdict"],
        data_availability="full",
        nfe_per_pass=j["nfe"],
        source="verification_outputs/wave190-p3-lineageflow-n30.json",
    )


def k6_rows() -> list[dict[str, Any]]:
    """k6 per-record framework-vs-baseline (N=1000). Paper-vs-cosine comparison NOT RUN."""
    rows_csv = _load_csv(OUT_DIR / "wave198-p2-per-record-paired.csv")
    rows_cluster = _load_csv(OUT_DIR / "wave203-p3-k6-cluster-robust.csv")
    cluster_by_metric = {
        r["metric"]: r for r in rows_cluster if r["tier"] == "overall"
    }
    out: list[dict[str, Any]] = []
    for r in rows_csv:
        if r["dataset"] != "k6_foldability_w161":
            continue  # the CSV also carries a tiny lineageflow_omegafold row
        metric = r["metric"]
        cluster = cluster_by_metric.get(metric)
        out.append(
            _row(
                adapter="k6_foldability_w161",
                metric=f"framework_vs_baseline_{metric}",
                n_paired=int(r["n_paired"]),
                paper_quantity_d_z=None,
                cosine_only_d_z=None,
                fixed_threshold_d_z=None,
                paper_vs_cosine_d_z=None,
                paper_vs_cosine_p=None,
                paper_vs_cosine_cluster_robust_p=(
                    float(cluster["cluster_p"]) if cluster else None
                ),
                paper_vs_cosine_bonferroni_significant=None,
                paper_vs_cosine_verdict="NOT_RUN_paper_vs_cosine_ablation_absent",
                data_availability="framework_vs_baseline_only",
                nfe_per_pass=50,
                source=(
                    "verification_outputs/wave198-p2-per-record-paired.csv "
                    "+ verification_outputs/wave203-p3-k6-cluster-robust.csv"
                ),
            )
        )
    return out


def lineageflow_per_record_row() -> dict[str, Any]:
    """LineageFlow per-record framework-vs-baseline (N=574). Paper-vs-cosine NOT RUN."""
    rows = _load_csv(OUT_DIR / "wave202-p5-lineageflow-per-record.csv")
    row = next(r for r in rows if r["metric"] == "sc_perplexity")
    return _row(
        adapter="lineageflow_real_fastas_w158",
        metric="framework_vs_baseline_sc_perplexity",
        n_paired=int(row["n_paired"]),
        paper_quantity_d_z=None,
        cosine_only_d_z=None,
        fixed_threshold_d_z=None,
        paper_vs_cosine_d_z=None,
        paper_vs_cosine_p=None,
        paper_vs_cosine_cluster_robust_p=None,
        paper_vs_cosine_bonferroni_significant=None,
        paper_vs_cosine_verdict="NOT_RUN_paper_vs_cosine_ablation_absent",
        data_availability="framework_vs_baseline_only",
        nfe_per_pass=50,
        source="verification_outputs/wave202-p5-lineageflow-per-record.csv",
    )


def flowmol3_rows() -> list[dict[str, Any]]:
    """FlowMol3 per-record framework-vs-baseline (N=200, 1-seed Wave 87 byte-stable).

    Paper-vs-cosine comparison NOT RUN: DGL 2.4.0 regression blocked fresh 3-seed
    re-run (per Wave 208 P2 audit). The Wave 87 byte-stable 1-seed data is
    reproducible but does not have a paired cosine-only arm.
    """
    rows = _load_csv(OUT_DIR / "wave208-p2-flowmol3-sanity.csv")
    out: list[dict[str, Any]] = []
    for r in rows:
        metric = r["metric"]
        if metric == "reos_n_flags":
            continue  # canonical direction proxy; aggregate reos rows
        out.append(
            _row(
                adapter="flowmol3_wave87_byte_stable",
                metric=f"framework_vs_baseline_{metric}",
                n_paired=int(r["n_eff"]),
                paper_quantity_d_z=None,
                cosine_only_d_z=None,
                fixed_threshold_d_z=None,
                paper_vs_cosine_d_z=None,
                paper_vs_cosine_p=None,
                paper_vs_cosine_cluster_robust_p=None,
                paper_vs_cosine_bonferroni_significant=None,
                paper_vs_cosine_verdict="NOT_RUN_paper_vs_cosine_ablation_absent",
                data_availability="framework_vs_baseline_only_DGL_blocked",
                nfe_per_pass=50,
                source="verification_outputs/wave208-p2-flowmol3-sanity.csv",
            )
        )
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    rows.append(kanzi_row())
    rows.append(kanzi_entropy_row())
    rows.append(lineageflow_row())
    rows.append(lineageflow_entropy_row())
    rows.extend(k6_rows())
    rows.append(lineageflow_per_record_row())
    rows.extend(flowmol3_rows())

    # CSV
    fieldnames = list(rows[0].keys())
    with CSV_PATH.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Aggregate summary
    n_paper_vs_cosine_present = sum(
        1 for r in rows if r["paper_vs_cosine_d_z"] is not None
    )
    paper_vs_cosine_per_adapter: dict[str, list[float]] = {}
    for r in rows:
        if r["paper_vs_cosine_d_z"] is None:
            continue
        adapter = r["adapter"]
        paper_vs_cosine_per_adapter.setdefault(adapter, []).append(
            r["paper_vs_cosine_d_z"]
        )

    monotone = None
    if paper_vs_cosine_per_adapter:
        # Across all available per-adapter L2-axis d_z, do we see monotone
        # paper-quantity > cosine direction (positive d_z, framework wins)?
        # Convention: paper-vs-cosine d_z > 0 means paper > cosine on the axis;
        # for L2 axis the regularisation story is paper < cosine (negative d_z).
        # Use raw signs as the monotone check across the available axes.
        all_d_z = [d for v in paper_vs_cosine_per_adapter.values() for d in v]
        signs = [1 if d > 0 else -1 for d in all_d_z]
        monotone = all(s == signs[0] for s in signs) if signs else None

    summary = {
        "schema_version": "1.0.0",
        "wave": "208 P4",
        "kind": "cross_adapter_paper_quantity_vs_cosine_vs_fixed_threshold_ablation",
        "task": "Per DeepSeek P4: extend CLM-057 (kanzi n=30) to k6 + LineageFlow + FlowMol3.",
        "clm_057_replication_status": (
            "kanzi synthetic n=30 paper-vs-cosine data PRESERVED (Wave 190 P2). "
            "LineageFlow synthetic n=30 paper-vs-cosine data PRESERVED (Wave 190 P3). "
            "k6 real foldability, LineageFlow real fastas, FlowMol3 real QM9: "
            "paper-vs-cosine ablation NOT RUN — only framework-vs-baseline direction "
            "available. FlowMol3 fresh 3-seed sweep BLOCKED by DGL 2.4.0 regression "
            "(Wave 208 P2 audit, see verification_outputs/wave208-p2-flowmol3-sanity.json)."
        ),
        "n_rows": len(rows),
        "n_adapters_with_paper_vs_cosine_data": len(paper_vs_cosine_per_adapter),
        "n_adapters_total_reported": 3,  # k6, lineageflow, flowmol3
        "per_adapter_paper_vs_cosine_d_z": {
            k: [float(d) for d in v] for k, v in paper_vs_cosine_per_adapter.items()
        },
        "monotone_pattern_across_adapters": (
            "yes_positive" if monotone is True
            else ("yes_negative" if monotone is False else "not_assessable_only_two_adapters_have_paper_vs_cosine_data")
        ),
        "alpha_bonferroni": ALPHA_BONFERRONI_PAPER_VS_COSINE,
        "rows": rows,
        "honest_disclosure": [
            {
                "adapter": "k6_foldability_w161",
                "issue": "Per-record framework-vs-baseline (N=1000) is available from Wave 198 P2 / Wave 203 P3 cluster-robust refresh. The paper-quantity vs cosine-only ablation was NOT run on this adapter — only the framework default (with paper-quantity scheduler) vs vanilla baseline.",
                "implication": "CLM-057 kanzi n=30 finding is the load-bearing anchor; k6 cannot independently confirm or refute the scheduler story on the protein axis without a paired paper-quantity vs cosine-only sweep.",
            },
            {
                "adapter": "lineageflow",
                "issue": "Per-record framework-vs-baseline (N=574) is available from Wave 202 P5. The paper-quantity vs cosine-only ablation was run on synthetic axis only (Wave 190 P3, n=30), where the L2 axis is NOT Bonferroni-significant (d_z = +0.09, p = 0.615) but the entropy axis IS (d_z = +0.64, p = 0.00293).",
                "implication": "On real fastas, the paper-quantity story reduces to framework-vs-baseline direction (d_z = -1.014 scPerplexity, p < 1e-90). The scheduler-ablation gap between synthetic and real adapters is documented in Wave 190 P3 §4 cross-adapter consistency.",
            },
            {
                "adapter": "flowmol3",
                "issue": "Per-record framework-vs-baseline (N=200, 1-seed Wave 87 byte-stable) is available from Wave 208 P2. The paper-quantity vs cosine-only ablation is NOT RUN on this adapter: DGL 2.4.0 regression blocked fresh 3-seed re-run; only the byte-stable 1-seed baseline vs framework comparison is reproducible.",
                "implication": "CLM-057 cannot be replicated on the molecular axis without DGL downgrade recovery. The framework-vs-baseline direction (reos_n_flags d_z = -0.285, p = 8e-5) is the honest disclosure. Wave 87 byte-stable data is reproducible per its commit SHA (per Wave 208 P2 audit).",
            },
            {
                "adapter": "fixed_threshold_arm",
                "issue": "No cross-adapter sweep ran the fixed-threshold (constant n_cap = 0.5 = uniform memory_fraction) arm at n=30 paired. The Wave 52 ablation_q4_2026.json includes this arm for twodim_fm only (paper-vs-uniform d_z ≈ -0.003 = byte-equivalent). The Wave 72 memory_fraction ablation shows the kanzi composite is byte-stable across m ∈ {0.056, 0.5} (range = 0.0).",
                "implication": "The 'paper-quantity scheduler strictly beats fixed-threshold' claim is NOT established by a paired cross-adapter sweep. On kanzi synthetic axis the two are byte-equivalent at the same NFE; on twodim_fm synthetic axis they differ by 0.003 (negligible). This is a coverage gap, not a contradiction: a follow-up paired sweep across {kanzi, k6, lineageflow, flowmol3} would close the gap.",
            },
        ],
    }

    with JSON_PATH.open("w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"Wrote {CSV_PATH} ({len(rows)} rows)")
    print(f"Wrote {JSON_PATH}")
    print(f"n_adapters_with_paper_vs_cosine_data = {summary['n_adapters_with_paper_vs_cosine_data']}")


if __name__ == "__main__":
    main()
