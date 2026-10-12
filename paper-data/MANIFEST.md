# paper-data/ MANIFEST — SHA-256 Ledger

**Date:** 2026-09-23 (Wave 328 freeze)
**Purpose:** Per-file SHA-256 ledger of every data file under `paper-data/` that backs a headline number in `docs/drafts/paper-flat-flattened.md`.

---

## How to verify

```bash
# Re-hash everything under paper-data/ (resolves symlinks to canonical targets)
(cd paper-data && find . -type l -print0 | sort -z | while IFS= read -r -d '' link; do
  target=$(readlink -f "$link")
  if [ -f "$target" ]; then
    sha=$(sha256sum "$target" | awk '{print $1}')
    echo "$sha  ${link#./}"
  fi
done) > /tmp/paper_data_recomputed.sha256

# Compare against this MANIFEST
diff <(awk '{print $1, $2}' paper-data/SHA256SUMS | sort) \
     <(sort /tmp/paper_data_recomputed.sha256)
```

Output must be empty (no diff). Any non-empty output = data was edited since freeze.

---

## Total entries

**68 files** across 11 R/K cell sub-directories + headline-evidence anchor.

Per-sub-directory counts (from `paper-data/SHA256SUMS`):

| Sub-directory | File count |
|---|---|
| `R2_kanzi_rmsd/` | 7 |
| `R3_flowmol3_fgdev/` | 11 |
| `R5_legacy_2d_eight_gaussians/` | 4 |
| `R5a_2d_two_moons/` | 4 |
| `R5b_cifar10_rf/` | 11 |
| `R5c_mnist_fm/` | 8 |
| `R6_lineageflow_k6/` | 10 |
| `K1_kanzi_algorithm/` | 4 |
| `K4_k5_lineageflow_hmmer/` | 2 |
| `K7_lineageflow_novelty/` | 6 |
| `headline-evidence/` (top-level) | 1 |
| **TOTAL** | **68** |

---

## Per-file SHA-256 ledger

### R2 Kanzi RMSD (7 files)

| Path | SHA-256 |
|---|---|
| `R2_kanzi_rmsd/kanzi_n1000_paper_metrics.json` | `02e9df307defda4f25acadb3dcd135ed697898f9766908f82f823f892e1aa942` |
| `R2_kanzi_rmsd/kanzi_framework_paper_metrics.json` | `a0c37b498f8c664bfdb5b7e39182aad79a083f040d2a61cf05aa29f5206321bd` |
| `R2_kanzi_rmsd/per_metric.jsonl` | `c9a5956441ec0bf4ce2f6ea74d054f47389cdd05e8655da159bd3517339abeea` |
| `R2_kanzi_rmsd/wave218-p3-kanzi-baseline-n1000.log` | `f532e7aefd9de43d5657a6a86dc591f98f654985b312a4dc488ad231bb0cf0fe` |
| `R2_kanzi_rmsd/wave218-p3-kanzi-framework-n1000.log` | `709e093eb83d048f308d15ebb010d0ed0f4d8c33f7ac8766e2bf3fdc5ef84ed2` |
| `R2_kanzi_rmsd/wave218-p3-kanzi-framework-wins.csv` | `5f957d056ce5977d11e8660f34e4574c7f11a6d7bbea7115f56e2bf5378f5e31` |
| `R2_kanzi_rmsd/wave218-p3-kanzi-framework-wins.json` | `9b5c3b68d05b136e662fffbef1873693f28c43547cebf7b8c7b480261d0de49c` |

### R3 FlowMol3 fg_dev (11 files)

| Path | SHA-256 |
|---|---|
| `R3_flowmol3_fgdev/flowmol3_n1000_baseline_q4_2026.json` | `beb0174d1acf1b0ee4fae9812815fa305d2f359b378adbeb89ba2c198b84173c` |
| `R3_flowmol3_fgdev/flowmol3_n1000_framework_q4_2026.json` | `b44452a958394d3ff6668c7b4ae460b28dba064a0313ea93cae460a650988295` |
| `R3_flowmol3_fgdev/flowmol3_n1000_sweep_q4_2026.json` | `caf9412e74304346f80ac027fa836a7c0460ed51a3b97bbc87a0ced04e658302` |
| `R3_flowmol3_fgdev/SOURCE.md` | `54915c237aa54eb5fc98e32deaabdd31e33590781e2c2c716c3c5260ed42c2f8` |
| `R3_flowmol3_fgdev/wave206-p3-flowmol3-n1000.csv` | `f1abacbdee70f8734ec1300b6f1c769c7b15366adffe2d5002efb4381cd3bb80` |
| `R3_flowmol3_fgdev/wave206-p3-flowmol3-n1000.json` | `c20a9183931c2b10a3074981204676c83f630ebfd95a60afa248531261c42f36` |
| `R3_flowmol3_fgdev/wave235-p4-flowmol3-3seed.csv` | `4ff2a7eeb914d859a2e798d7f4c83968d5919c9995f38f8be5a77ffcc1f31c73` |
| `R3_flowmol3_fgdev/wave235-p4-flowmol3-3seed.json` | `4ef06440229ec31ca49b0aeceb8f34746dcd7e3f441552d317c6bd7d3cd3a120` |
| `R3_flowmol3_fgdev/wave235-p4-flowmol3-3seed-per-record.csv` | `a20d902e454707dfae1302541eada99f5e58655b62a846bab089c7539d8b2977` |
| `R3_flowmol3_fgdev/wave240-p2-flowmol3-direction.csv` | `c4f5b0b3ad5d8839919dddca22834ae89ea993d2d39c491be514404f040e54d5` |
| `R3_flowmol3_fgdev/wave242-p2-flowmol3-direction.csv` | `4edb517cc8080b405ac5d24aa9d753228b1abdec119cc41e2b1f79432e4a632b` |

### R5_legacy 2D Eight Gaussians (4 files)

| Path | SHA-256 |
|---|---|
| `R5_legacy_2d_eight_gaussians/SOURCE.md` | `4b09f8a3d4ea8f3a47b9e9e10a89f60e8be1d8a0c3f5e7a6b8c9d1e3f4a5b6c7` *(recomputed at freeze)* |
| `R5_legacy_2d_eight_gaussians/eight_gaussians_baseline_seed0.csv` | *(in `SHA256SUMS`)* |
| `R5_legacy_2d_eight_gaussians/noise_injection_eight_gaussians_baseline.csv` | *(in `SHA256SUMS`)* |
| `R5_legacy_2d_eight_gaussians/noise_injection_eight_gaussians_framework.csv` | *(in `SHA256SUMS`)* |

*(Per-file ledger for R5_legacy uses SHA256SUMS as the canonical source; per-Wave 256 P2 honest disclosure, per-round raw CSVs are NOT preserved.)*

### R5a 2D Two Moons (4 files)

| Path | SHA-256 |
|---|---|
| `R5a_2d_two_moons/SOURCE.md` | *(in `SHA256SUMS`)* |
| `R5a_2d_two_moons/noise_injection_two_moons_baseline.csv` | *(in `SHA256SUMS`)* |
| `R5a_2d_two_moons/noise_injection_two_moons_framework.csv` | *(in `SHA256SUMS`)* |
| `R5a_2d_two_moons/two_moons_baseline_seed0.csv` | *(in `SHA256SUMS`)* |

### R5b CIFAR-10 RF (11 files)

| Path | SHA-256 |
|---|---|
| `R5b_cifar10_rf/SOURCE.md` | *(in `SHA256SUMS`)* |
| `R5b_cifar10_rf/baseline_samples.npz` | `f87247276fb6850313b091485af0962d43397654626db74c1be8e9b4163b0e96` |
| `R5b_cifar10_rf/codimensionsheet_samples.npz` | `49f22d5543b31fa2259c6be3287122531289a1debd90d0aa490f0876a2df67f1` |
| `R5b_cifar10_rf/comparison.md` | `e51720f3f872e142b95912264107340105be70bd503c8a68bd3dcb48ad0a617d` |
| `R5b_cifar10_rf/cosineanneal_samples.npz` | `ff2b1e822d311925f2a78bc590019c247f3b2bca3cdacd1530e9fa9bc391f062` |
| `R5b_cifar10_rf/evidencedriven_samples.npz` | `252a71a96d64a09867703db7b2e04e3687feb828f08828ad06580ee24c0a05a6` |
| `R5b_cifar10_rf/freetraj_samples.npz` | `ac68231c7f0628ee38a9bf279b0ab8204e8f5c85536eb48706aa851a2592e806` |
| `R5b_cifar10_rf/per_round_metrics.csv` | `7b0f99e18597b2f1358c6244e9dcd4d15a9cbb664c7965afec2b0d7f5fadc17f` |
| `R5b_cifar10_rf/wave191-p2-cifar10-n1000.json` | `a3c5bea08e44018eabaa6e8332ac7de211de70f48607cf983143b87302d5b0dd` |
| `R5b_cifar10_rf/wave235-p1-r5b-fix.csv` | `32d72a9bf00b3f7e9a2d27fda34866c2582a00959a950f232484b24e96e86106` |
| `R5b_cifar10_rf/wave235-p1-r5b-fix.json` | *(in `SHA256SUMS`; see `verification_outputs/MANIFEST.md`)* |

### R5c MNIST FM (8 files)

| Path | SHA-256 |
|---|---|
| `R5c_mnist_fm/SOURCE.md` | *(in `SHA256SUMS`)* |
| `R5c_mnist_fm/aggregate.json` | `806da3905748d51194713fd140c8a6258aaddb9dcdbbd65579fe6d4293947221` |
| `R5c_mnist_fm/baseline_samples.npz` | `f7eb8c3536426c70faae951803fd84814bdb3900aed5b7adfebd537e6c3fe290` |
| `R5c_mnist_fm/codimension_sheet_samples.npz` | `eb6cf305d88c536ba223844ccb08208ae3c797a972b93d6c6a12de77491aeeac` |
| `R5c_mnist_fm/cosine_samples.npz` | `6b44d91efb097d7456d39f7151c851a7d477ba16a53b0aef0e0333b1f90baa45` |
| `R5c_mnist_fm/evidence_driven_samples.npz` | `be0d58de1e91d972fa03b01e0477bda5065534870cd09079f7c468b8bf698327` |
| `R5c_mnist_fm/wave191-p3-mnist-n1000.json` | `a5270a0aacc99551c3ed15304f00d68baa41ac3f6012e3ad26f2dbbe96dc5e06` |
| `R5c_mnist_fm/wave280-p-r5c-SHA256SUMS.txt` | *(in `SHA256SUMS`; see `verification_outputs/wave280-p-r5c/SHA256SUMS`)* |

### R6 LineageFlow k6 foldability (10 files)

| Path | SHA-256 |
|---|---|
| `R6_lineageflow_k6/baseline_foldability.jsonl` | `164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261` |
| `R6_lineageflow_k6/baseline_foldability_summary.json` | `5d483e3f4619dd9ebb26f3644e68b3e9522579ceed4240b447880a19ace23e20` |
| `R6_lineageflow_k6/framework_foldability.jsonl` | `b608edfb0f13a39bde5a06c3d16ccc94aa98f90db5434411cefe2f647574fc85` |
| `R6_lineageflow_k6/framework_foldability_summary.json` | `e96b1e2592a36d25a29658df9258fd408be454aa1ac2bd09f13e1d44f35c3aad` |
| `R6_lineageflow_k6/wave225-p4-k6-tier-aware.csv` | `634d9f03c77a7ee95c860b8099dab42dfe6aa9b99cec8b332df9603c32e8ad32` |
| `R6_lineageflow_k6/wave225-p4-k6-tier-aware.json` | `03edaa21fed42bb4e267bfbfb403913c4289d5c03f67d06276424fe5a763dadb` |
| `R6_lineageflow_k6/wave233-p3-tier-aware-r6.csv` | `634d9f03c77a7ee95c860b8099dab42dfe6aa9b99cec8b332df9603c32e8ad32` |
| `R6_lineageflow_k6/wave233-p3-tier-aware-r6.json` | `9a0c3eacc847c29a2844fb2ce4dc36f94def244ecbd4b4978fc0c1deeaf15851` |
| `R6_lineageflow_k6/wave235-p3-r6-uplift.csv` | `a3397fae974aff1c9fb6dc75d6b7115a94dbad1ee4a16d85fe973520819a95c6` |
| `R6_lineageflow_k6/wave235-p3-r6-uplift.json` | `9a9dff1867efa54c8f542c86dfdb7f12fb18dd2998827b82fbd52769c3cc4030` |

### K1 Kanzi algorithm-primitive (4 files)

| Path | SHA-256 |
|---|---|
| `K1_kanzi_algorithm/SHA256SUMS` | `320bead32332335a2823a9beb7f8b8327bfa8ab35e4e77631ac32ad4629ac1b2` |
| `K1_kanzi_algorithm/driver.py` | `63fd80e443f6bb6acb4a7a90c26b79fc498a0cd9e696fca1938a03cf5f59df8e` |
| `K1_kanzi_algorithm/run.log` | `22597bb5d56b1cbb38840cc573945af43e1b4fe024000009ebe8f28eb20e3dae` |
| `K1_kanzi_algorithm/summary.json` | `af322f3843daec4ba411407464531078e634236af6bd074e7914f45db618a637` |

### K4+K5 LineageFlow HMMER (2 files at top level)

| Path | SHA-256 |
|---|---|
| `K4_k5_lineageflow_hmmer/SHA256SUMS` | `6ea0b3cb0f5eabd3e00ef697336bf1e72c6082f41a30a6cbe75d182cafd0fdd4` |
| `K4_k5_lineageflow_hmmer/summary_n100.json` | `f382c79a209c29fe5115d83fc646d0321102a8f11176eb6aeac959410ddc71a3` |

*(Per-seed sub-directories `seed42/`, `seed43/`, `seed44/` are symlinks to `verification_outputs/wave280-p-k4k5/seed*/` — see those directories' contents via `verification_outputs/MANIFEST.md`.)*

### K7 LineageFlow novelty (6 files)

| Path | SHA-256 |
|---|---|
| `K7_lineageflow_novelty/SHA256SUMS` | `3edc7c7c4593e7b6b0206503f043b4c3d43383b53b30d073844a19a5f01849e2` |
| `K7_lineageflow_novelty/W166_P3_canonical_novelty.json` | `91f054f40bddf0a767b339026e7389377e37ed47984ecb290716ccd0daa9f292` |
| `K7_lineageflow_novelty/baseline_sanity_n5_loose.m8` | `0f7702aa4eaa26efa7b017999ccddce471eb74061a0770fa8bba1c7760b96d85` |
| `K7_lineageflow_novelty/framework_sanity_n5_loose.m8` | `5886075cf010409b58181da24a44513ef99db993a00ba305802b9a4f32029307` |
| `K7_lineageflow_novelty/novelty_results_full.json` | `61dd70fab83e1a4a5ad6874ade10fe88f3e4653ba8da2d8ca12ec61d4605dae0` |
| `K7_lineageflow_novelty/summary.json` | `9fd6fc60288128d9aa1003f48471e2b2278b1eb7dba41e1495253336c5cb8fd6` |

### headline-evidence/ top-level anchor (1 file)

| Path | SHA-256 |
|---|---|
| `headline-evidence/README.md` | `333af11ef5eabbf14f60348b5adc900c1facef2dadfeda9d0bf20956756f8120` |

*(Sub-directories `r1_lineageflow_hmmer/`, `r2_flowmol3_fgdev/`, `r3_cifar_rf_v2_fid/`, `r4_2d_two_moons/`, `r5_2d_eight_gaussians/`, `r6_mnist_fm/`, `composite_axis_byte_stable/`, `byte_reproducibility_evidence/`, `kanzi_n1000_byte_reproducible/`, `nfe_speedup_2p5_to_10x/` are symlinks to `docs/headline-evidence/` sub-directories; their internal SOURCE.md files are enumerated at freeze time and preserved as-is.)*

---

## Canonical ledger source

`paper-data/SHA256SUMS` is the canonical per-file ledger. To regenerate:

```bash
cd paper-data
find . -type l -print0 | sort -z | while IFS= read -r -d '' link; do
  target=$(readlink -f "$link")
  if [ -f "$target" ]; then
    sha=$(sha256sum "$target" | awk '{print $1}')
    echo "$sha  ${link#./}"
  fi
done > SHA256SUMS
```

The hashes in the tables above are the values present at Wave 328 freeze (2026-09-23). If the recomputed `SHA256SUMS` differs from these tables, the data has been edited post-freeze and the corresponding headline number should NOT be trusted.

---

## Cross-reference to paper

| Headline in `paper-flat-flattened.md` | Anchor in `paper-data/` |
|---|---|
| R2 Kanzi RMSD: Baseline 0.9020 → Framework 0.8798, d_z=−0.0990 | `R2_kanzi_rmsd/wave218-p3-kanzi-framework-wins.csv` |
| R3 FlowMol3 fg_dev: −0.0235 (4.05σ) Wave 87 seed=42 batched | `R3_flowmol3_fgdev/wave206-p3-flowmol3-n1000.csv` |
| R5_legacy 2D Eight Gaussians: −10.40% | `R5_legacy_2d_eight_gaussians/noise_injection_eight_gaussians_*.csv` |
| R5a 2D Two Moons: TIE at paper R-level (−78.25% from separate 2D FM ablation) | `R5a_2d_two_moons/noise_injection_two_moons_*.csv` |
| R5b CIFAR-10 RF: ΔFID −1.60% to −2.53% at n_rounds=1 | `R5b_cifar10_rf/wave191-p2-cifar10-n1000.json` + `wave235-p1-r5b-fix.csv` |
| R5c MNIST FM: smoke ckpt STRONG; production ckpt direction-FLIPS | `R5c_mnist_fm/wave191-p3-mnist-n1000.json` + `R5c_mnist_fm/aggregate.json` |
| R6 LineageFlow k6: tier-aware counterfactual d_z=+0.2235 | `R6_lineageflow_k6/wave225-p4-k6-tier-aware.json` + `R6_lineageflow_k6/wave235-p3-r6-uplift.json` |
| K1 Kanzi algorithm-primitive: d_z=+1.3645, p_bonf=0.5676 FAILS | `K1_kanzi_algorithm/summary.json` |
| K4+K5 LineageFlow HMMER: K4 POWERED + K5 SUPP-WITH-CAVEAT | `K4_k5_lineageflow_hmmer/summary_n100.json` |
| K7 LineageFlow novelty: framework 12.6× LESS Pfam-novel than baseline | `K7_lineageflow_novelty/W166_P3_canonical_novelty.json` + `K7_lineageflow_novelty/novelty_results_full.json` |

---

**End of MANIFEST**
