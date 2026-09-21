#!/usr/bin/env python3
"""Wave 246 P4 — I² subgroup meta-analysis (per-domain pooled d_z).

Reads the Wave 234 P5 12-study meta-analysis CSV and computes a separate
random-effects DerSimonian-Laird pooled effect + 95% CI + I² + Cochran's
Q for each of three domain subgroups: protein, molecule, image.

The §2.12.7 cross-domain heterogeneity discussion in
`docs/drafts/section-2-method.md` documents that the high overall I² =
99.60% is the EXPECTED outcome of cross-domain pooling; this script
quantifies the per-domain components of that heterogeneity.

Domain assignment (12 studies, see verification_outputs/wave234-p5-meta-analysis.csv):

  - protein (8 rows): R1 HMMER, R2 Kanzi inv-proj, R6 foldability pLDDT,
    R6 foldability scPerplexity, 4× 4-arm foldability cells (vanilla_NFE50,
    vanilla_NFE100, fastdllm_NFE50, lediflow_NFE50)
  - molecule (1 row): R3 FlowMol3 fg_dev REOS (single-seed, direction-INCONSISTENT)
  - image (3 rows): R5a 2D Two Moons W2, R5b CIFAR-10 RF matched-NFE=50 FID,
    R5c MNIST FM matched-NFE=50 FID

Output: verification_outputs/wave246-p4-subgroup-meta.json

DerSimonian-Laird random-effects meta-analysis:
  - Q = sum(w_i * (d_i - d_FE)^2), where w_i = 1 / SE_i^2
  - df = k - 1
  - tau^2 = max(0, (Q - df) / (sum(w_i) - sum(w_i^2) / sum(w_i)))
  - w_i_RE = 1 / (SE_i^2 + tau^2)
  - d_RE = sum(w_i_RE * d_i) / sum(w_i_RE)
  - var(d_RE) = 1 / sum(w_i_RE)
  - 95% CI = d_RE ± 1.96 * sqrt(var(d_RE))
  - I^2 = max(0, (Q - df) / Q) * 100 (percent)
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

META_CSV = Path(
    "/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave234-p5-meta-analysis.csv"
)
OUT_JSON = Path(
    "/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave246-p4-subgroup-meta.json"
)

# Domain assignment by `study` (CSV column 1).
# Keys are study identifiers (CSV column 1); values are domain labels.
PROTEIN_STUDIES = {
    "R1_lineageflow_hmmer",
    "R2_kanzi_inv_proj",
    "R6_lineageflow_pLDDT",
    "R6_lineageflow_scPerplexity",
    "4arm_vanilla_scPerplexity_NFE50",
    "4arm_vanilla_scPerplexity_NFE100",
    "4arm_fastdllm_scPerplexity_NFE50",
    "4arm_lediflow_scPerplexity_NFE50",
}
MOLECULE_STUDIES = {
    "R3_flowmol3_fg_dev_reos",
}
# Remaining 3 studies go to image: R5a_2D_two_moons_W2, R5b_CIFAR_matched_NFE50_FID,
# R5c_MNIST_fm_matched_NFE50_FID.

Z_95 = 1.959963984540054  # two-sided 95% normal


def dl_random_effects(d_values: list[float], se_values: list[float]) -> dict:
    """DerSimonian-Laird random-effects meta-analysis."""
    k = len(d_values)
    if k < 2:
        # k=1: no heterogeneity estimable; report d, SE and degenerate CI.
        if k == 1:
            return {
                "k_studies": 1,
                "pooled_d_z": d_values[0],
                "se_pooled": se_values[0],
                "ci_95_lower": d_values[0] - Z_95 * se_values[0],
                "ci_95_upper": d_values[0] + Z_95 * se_values[0],
                "I_squared_pct": None,
                "tau_squared": None,
                "cochran_q": None,
                "cochran_q_p": None,
                "fixed_effect_pooled_d_z": d_values[0],
                "heterogeneity_class": "single_study",
            }
        return {
            "k_studies": 0,
            "pooled_d_z": None,
            "se_pooled": None,
            "ci_95_lower": None,
            "ci_95_upper": None,
            "I_squared_pct": None,
            "tau_squared": None,
            "cochran_q": None,
            "cochran_q_p": None,
            "fixed_effect_pooled_d_z": None,
            "heterogeneity_class": "empty",
        }

    # Fixed-effect weights (inverse-variance).
    w_fixed = [1.0 / (se * se) for se in se_values]
    sum_w = sum(w_fixed)
    d_FE = sum(w * d for w, d in zip(w_fixed, d_values)) / sum_w

    # Cochran's Q and tau^2.
    Q = sum(w * (d - d_FE) ** 2 for w, d in zip(w_fixed, d_values))
    df = k - 1
    c = sum_w - (sum(w * w for w in w_fixed) / sum_w)
    tau_sq = max(0.0, (Q - df) / c) if c > 0 else 0.0

    # Random-effects weights.
    w_RE = [1.0 / (se * se + tau_sq) for se in se_values]
    sum_w_RE = sum(w_RE)
    d_RE = sum(w * d for w, d in zip(w_RE, d_values)) / sum_w_RE
    var_d_RE = 1.0 / sum_w_RE
    se_RE = math.sqrt(var_d_RE)

    # I^2 (Higgins & Thompson 2002).
    I_sq = max(0.0, (Q - df) / Q) * 100.0 if Q > 0 else 0.0

    # Heterogeneity class (Higgins-Thompson bands).
    if I_sq < 25.0:
        h_class = "low"
    elif I_sq < 75.0:
        h_class = "moderate"
    else:
        h_class = "high"

    # Cochran's Q p-value (chi-square df=k-1). No scipy available — use
    # Wilson-Hilferty normal approximation: ((Q/df)^(1/3) - (1 - 2/(9*df))) /
    # sqrt(2/(9*df)) ~ N(0,1).
    if df > 0:
        z_chi = ((Q / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(
            2.0 / (9.0 * df)
        )
        # Two-sided p-value via complementary error function approximation.
        # p = 2 * (1 - Phi(|z|)).
        # Phi(x) ≈ 1 - phi(x) * (b1*t + b2*t^2 + b3*t^3 + b4*t^4 + b5*t^5)
        # where t = 1 / (1 + p*x), p=0.2316419, b's from Abramowitz & Stegun.
        abs_z = abs(z_chi)
        p_coef = 0.2316419
        b1 = 0.319381530
        b2 = -0.356563782
        b3 = 1.781477937
        b4 = -1.821255978
        b5 = 1.330274429
        t = 1.0 / (1.0 + p_coef * abs_z)
        phi = math.exp(-0.5 * abs_z * abs_z) / math.sqrt(2.0 * math.pi)
        Phi = 1.0 - phi * (
            b1 * t + b2 * t * t + b3 * t ** 3 + b4 * t ** 4 + b5 * t ** 5
        )
        p_Q = 2.0 * (1.0 - Phi)
    else:
        p_Q = None

    return {
        "k_studies": k,
        "pooled_d_z": d_RE,
        "se_pooled": se_RE,
        "ci_95_lower": d_RE - Z_95 * se_RE,
        "ci_95_upper": d_RE + Z_95 * se_RE,
        "I_squared_pct": I_sq,
        "tau_squared": tau_sq,
        "cochran_q": Q,
        "cochran_q_p": p_Q,
        "fixed_effect_pooled_d_z": d_FE,
        "heterogeneity_class": h_class,
    }


def main() -> None:
    studies = []
    with META_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            studies.append(
                {
                    "study": row["study"],
                    "domain_csv": row["domain"],
                    "d": float(row["d"]),
                    "d_kind": row["d_kind"],
                    "n_pairs": int(row["n_pairs"]),
                    "SE": float(row["SE"]),
                }
            )

    # Assign domain label per study.
    by_domain = {"protein": [], "molecule": [], "image": []}
    for s in studies:
        if s["study"] in PROTEIN_STUDIES:
            by_domain["protein"].append(s)
        elif s["study"] in MOLECULE_STUDIES:
            by_domain["molecule"].append(s)
        else:
            by_domain["image"].append(s)

    output = {
        "schema_version": "1.0.0",
        "source": str(META_CSV),
        "method": (
            "Per-domain DerSimonian-Laird random-effects meta-analysis. "
            "Subgroups defined a priori by cell type: protein (R1, R2, R6 "
            "foldability pLDDT, R6 foldability scPerplexity, 4× 4-arm "
            "foldability cells = 8 rows); molecule (R3 FlowMol3 fg_dev "
            "REOS = 1 row); image (R5a 2D W2, R5b CIFAR-10 RF matched-NFE=50 "
            "FID, R5c MNIST FM matched-NFE=50 FID = 3 rows). Total = 12 rows."
        ),
        "alpha": 0.05,
        "sign_convention": (
            "POSITIVE d means the FRAMEWORK improves over the baseline on "
            "the per-metric direction (per Wave 234 P5)."
        ),
        "subgroups": {},
    }

    for domain, rows in by_domain.items():
        d_values = [r["d"] for r in rows]
        se_values = [r["SE"] for r in rows]
        result = dl_random_effects(d_values, se_values)
        result["studies"] = [r["study"] for r in rows]
        result["d_range"] = (
            [min(d_values), max(d_values)] if d_values else None
        )
        result["n_pairs_sum"] = sum(r["n_pairs"] for r in rows)
        output["subgroups"][domain] = result

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        import json

        json.dump(output, f, indent=2)
    print(f"Wrote {OUT_JSON}")
    print()
    for domain, result in output["subgroups"].items():
        d_re = result["pooled_d_z"]
        ci_lo = result["ci_95_lower"]
        ci_hi = result["ci_95_upper"]
        I_sq = result["I_squared_pct"]
        I_sq_str = "N/A" if I_sq is None else f"{I_sq:.2f}%"
        print(
            f"{domain:>9s} k={result['k_studies']:>2d}  "
            f"d_RE={d_re:+.4f}  95% CI=[{ci_lo:+.4f}, {ci_hi:+.4f}]  "
            f"I²={I_sq_str:>7s}  "
            f"class={result['heterogeneity_class']}"
        )


if __name__ == "__main__":
    main()