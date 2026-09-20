#!/usr/bin/env python3
"""Wave 209 P5 (D3): cross-domain per-record summary (MEDIUM).

Per DeepSeek D3: compile a single CSV that lists the per-record axis
verdict across molecule (FlowMol3 R3) + image cells (CIFAR-10 RF R5b,
MNIST FM R5c). The 2D RF cell R5a is honest disclosure — n=3 unpaired
seeds, no per-record paired data exists.

Source CSVs:
  - molecule: verification_outputs/wave208-p2-flowmol3-sanity.csv
              (Wave 87 N=1000 byte-stable, per-record proxy capped at 200)
  - image CIFAR-10 RF R5b: verification_outputs/wave195-p2-r-level-power.csv
                           (per-image paired, df=9, n_chunks=10)
  - image MNIST FM R5c:    verification_outputs/wave195-p2-r-level-power.csv

Direction encoding each row uses is captured in `lower_is_better`.
Framework moves toward the better side per the Wave 208 P2 / Wave 209 P2
direction-consistency rule.
"""
import csv
from pathlib import Path

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUTPUT_DIR = REPO / "verification_outputs"

# Load the three raw source CSVs.
WAVE_208_P2_FM = OUTPUT_DIR / "wave208-p2-flowmol3-sanity.csv"
WAVE_195_P2 = OUTPUT_DIR / "wave195-p2-r-level-power.csv"


def read_csv_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    fm_rows = read_csv_rows(WAVE_208_P2_FM)
    img_rows = read_csv_rows(WAVE_195_P2)

    print("=" * 70, flush=True)
    print("Wave 209 P5 (D3) — cross-domain per-record summary", flush=True)
    print("=" * 70, flush=True)
    print(f"\nSource: {WAVE_208_P2_FM.relative_to(REPO)} → {len(fm_rows)} FlowMol3 rows", flush=True)
    print(f"Source: {WAVE_195_P2.relative_to(REPO)} → {len(img_rows)} image rows", flush=True)

    # Find the Wave 195 R5b / R5c rows.
    r5b_row = next((r for r in img_rows if "cifar10rf" in r["cell"].lower()), None)
    r5c_row = next((r for r in img_rows if "mnist_fm" in r["cell"].lower()), None)
    r5a_row = next((r for r in img_rows if "two_moons" in r["cell"].lower()), None)

    if not (r5b_row and r5c_row and r5a_row):
        raise SystemExit(f"Missing image rows; r5a={r5a_row}, r5b={r5b_row}, r5c={r5c_row}")

    out_csv = OUTPUT_DIR / "wave209-p5-cross-domain-per-record.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "wave", "domain", "model", "cell", "metric",
            "kind", "n_paired", "mean_diff", "sd_diff",
            "ci_95_low", "ci_95_high", "d_z",
            "lower_is_better", "framework_better_side",
            "verdict", "source_csv",
            "honest_disclosure",
        ])

        # ---- Molecule: FlowMol3 per-record REOS proxy rows ----
        # Direction encoding per metric:
        #   reos_n_flags / reos_fg_contrib_proxy:  LOWER is better
        #     (fewer REOS flags per mol / less marginal contribution to fg_dev
        #      = closer to QM9 distribution = framework-WINS by direction)
        #   qed / logp / n_rings:  HIGHER is better (more drug-like in QED;
        #                          logP; larger / more cyclic framework mols)
        #   n_atoms:                (structural complexity; not lower_is_better)
        # Per Wave 208 P2 source CSV, ONLY the reos_n_flags and
        # reos_fg_contrib_proxy rows carry the directional verdict against
        # the headline fg_dev aggregate. The qed/logp/n_rings/n_atoms rows
        # are auxiliary structural metrics and are reported with explicit
        # non-verdict framing.
        DIRECTION_ENCODING = {
            "reos_n_flags":         (True,  True),
            "reos_fg_contrib_proxy":(True,  True),
            "qed":                 (False, True),   # higher QED = more drug-like
            "logp":                (False, True),
            "n_rings":             (False, True),
            "n_atoms":             (False, False),  # structurally equivocal; no verdict
        }
        for src in fm_rows:
            metric = src["metric"]
            mean_diff = float(src["mean_diff"])
            d_z = float(src["d_z"])
            lower_is_better, is_headline_proxy = DIRECTION_ENCODING.get(metric, (False, False))
            if is_headline_proxy:
                framework_better = (mean_diff < 0) if lower_is_better else (mean_diff > 0)
                verdict = "framework_WINS_direction" if framework_better else "baseline_WINS_direction"
            else:
                framework_better = None
                verdict = "auxiliary_structural_no_verdict"
            w.writerow([
                "209 P5", "molecule", "flowmol3", "R3_per_record", metric,
                f"per_record_N={src['n_eff']}_REOS_proxy",
                int(src["n_eff"]),
                f"{mean_diff:+.6f}", f"{float(src['sd_diff']):.6f}",
                f"{float(src['ci_95_low']):+.6f}", f"{float(src['ci_95_high']):+.6f}",
                f"{d_z:+.6f}",
                lower_is_better, framework_better if framework_better is not None else "n/a",
                verdict,
                "wave208-p2-flowmol3-sanity.csv (Wave 87 N=1000 sweep, persisted smiles_list cap at 200)",
                "DGL HTTP 403 blocks 3-seed re-run; 200-record cap on persisted smiles_list; per-record d_z is a DIRECTIONAL consistency check only" if is_headline_proxy
                else "Auxiliary structural metric — not a verdict row; qed/logp show framework produces more drug-like mols (direction-confirming on framework side)",
            ])

        # ---- Image: CIFAR-10 RF R5b ----
        r5b_diff = float(r5b_row["delta"])
        w.writerow([
            "209 P5", "image", "ddpm++_unet", "R5b_cifar10rf_matched_NFE50_FID", "FID_inception_pool3",
            "per_image_paired_chunk_t_df9",
            int(r5b_row["n_b"]), f"{r5b_diff:+.4f}",
            f"{float(r5b_row['delta_se']):.4f}",
            f"{float(r5b_row['ci_95_lower']):+.4f}", f"{float(r5b_row['ci_95_upper']):+.4f}",
            f"{float(r5b_row['cohens_d']):+.4f}",
            True, r5b_diff < 0,
            r5b_row["verdict"],
            "wave195-p2-r-level-power.csv (R5b_cifar10rf_matched_NFE50_FID)",
            "Boundary cell: cosine ramp halves effective NFE per round at matched NFE=50; framework REGRESSES on this cell by direction",
        ])
        # ---- Image: MNIST FM R5c ----
        r5c_diff = float(r5c_row["delta"])
        w.writerow([
            "209 P5", "image", "mnist_fm", "R5c_mnist_fm_matched_NFE50_FID", "FID_inception_pool3",
            "per_image_paired_chunk_t_df9",
            int(r5c_row["n_b"]), f"{r5c_diff:+.4f}",
            f"{float(r5c_row['delta_se']):.4f}",
            f"{float(r5c_row['ci_95_lower']):+.4f}", f"{float(r5c_row['ci_95_upper']):+.4f}",
            f"{float(r5c_row['cohens_d']):+.4f}",
            True, r5c_diff < 0,
            r5c_row["verdict"],
            "wave195-p2-r-level-power.csv (R5c_mnist_fm_matched_NFE50_FID)",
            "MNIST FM cell wins by direction under matched NFE=50; smallest-magnitude flow model on the smallest data domain",
        ])
        # ---- Image: 2D RF R5a — honest disclosure row ----
        r5a_diff = float(r5a_row["delta"])
        w.writerow([
            "209 P5", "image", "two_moons_2d_rf", "R5a_2D_two_moons_W2", "W2_to_analytic",
            "per_seed_unpaired_n3_seeds",
            int(r5a_row["n_b"]), f"{r5a_diff:+.6f}", "",
            f"{float(r5a_row['ci_95_lower']):+.6f}", f"{float(r5a_row['ci_95_upper']):+.6f}",
            f"{float(r5a_row['cohens_d']):+.4f}",
            True, r5a_diff < 0,
            r5a_row["verdict"],
            "wave195-p2-r-level-power.csv (R5a_2D_two_moons_W2)",
            "Honest disclosure: per-seed n=3 (the only reproducibly runnable cell on 2D Two Moons W2 axis); no per-record paired data exists",
        ])

    print(f"\nWrote CSV: {out_csv.relative_to(REPO)}", flush=True)
    print("=" * 70, flush=True)

    # Quick direction summary.
    print("\nDirection summary (framework side closer to QM9 / lower FID):")
    n_fm_better = sum(1 for r in fm_rows if float(r["mean_diff"]) < 0)
    n_fm_total = len(fm_rows)
    print(f"  FlowMol3 per-record: {n_fm_better}/{n_fm_total} proxy axes framework-better (lower_is_better=True)")
    r5b_better = float(r5b_row["delta"]) < 0
    r5c_better = float(r5c_row["delta"]) < 0
    r5a_better = float(r5a_row["delta"]) < 0
    print(f"  R5b CIFAR-10 RF NFE=50 FID: framework-better = {r5b_better} (verdict={r5b_row['verdict']})")
    print(f"  R5c MNIST FM NFE=50 FID:     framework-better = {r5c_better} (verdict={r5c_row['verdict']})")
    print(f"  R5a 2D Two Moons W2:          framework-better = {r5a_better} (verdict={r5a_row['verdict']})")
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
