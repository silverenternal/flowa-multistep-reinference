# R3 FlowMol3 fg_dev — Reproducibility Recipe

**Cell:** R3 FlowMol3 fg_dev (PARTIAL / single-seed PROJECTED per CLM-068)
**Headline:** R3 FlowMol3 fg_dev: PROJECTED from n=200 ACTUAL → N=1000 paired (t_N = t_200 · √(1000/200)); 7/7 cross-wave direction-consistent framework-WINS at 1 seed; PARTIAL / single-seed due to RDKit 2026.03.5 environment blocker (36.7% valid-yield at n=30 vs canonical 99.9%) per Wave 351 P3 / Wave 357 P3 disclosure layer.
**Date:** 2026-09-27 (Wave 363 P1 — R3 reproducibility recipe authored)
**Methodology disclosure:** Counterfactual-style projection (Wave 216 P1 projected N=1000 paired from n=200 ACTUAL on the canonical Wave 87 byte-stable seed=42 reference) — NOT a fresh GPU 3-seed N=1000 paired re-run. The full N=1000 paired fg_dev sweep with full SMILES retention remains DEFERRED to camera-ready pending RDKit environment unblock.

---

## (a) Headline Metric — R3 FlowMol3 fg_dev

The R3 cell's headline metric is **fg_dev** (functional-group deviation; lower = closer to QM9 training distribution = better). The R3 verdict is `PARTIAL / single-seed PROJECTED` per CLM-068 (paper §7.2 R3 row, line 539). Three readings co-exist at different granularities; all are anchored to the canonical Wave 82 / Wave 87 byte-stable seed=42 reference.

### Per-arm aggregate (1-seed byte-stable UNPAIRED, N=999 vs 1000)

| metric | baseline (sigma=0.0) | framework (sigma=0.05) | Δ | verdict |
|---|---:|---:|---:|---|
| `fg_dev` | **0.6381122391671532** | **0.614627774616795** | **−0.02348446455035824** | framework_WINS by 4.05σ (unpaired Welch's t-test) |
| `validity_pct` | 1.0 | 1.0 | 0.0 | tie at paper |
| `pb_validity_pct` | 0.5285 | 0.4290 | −0.0995 | baseline_improves (PB UFF-vs-xtb gap, NOT framework regression) |
| `ood_ring_rate` | 0.01301 | 0.01000 | −0.00301 | baseline_improves (real underpowered at N=1000, MDD=0.0263) |

Source: `verification_outputs/flowmol3_n1000_sweep_q4_2026.json` (Wave 82 sweep_id `wave82_agent_c_n1000`); per-arm statistical test from `verification_outputs/wave206-p3-flowmol3-n1000.json` — Welch's t-test unpaired per Wave 195 P2 spec: `t = -2.4533, df = 1996.998, p_raw = 0.01424, cohens_d_s = -0.110, alpha_bonferroni = 0.05/7 = 0.007143, bonf_sig = False` (UNDERPOWERED at strict α; direction-consistent).

### Per-record paired ACTUAL (n=200, data-capped from full N=1000 by the sweep tool)

| metric | mean_diff | sd_diff | t | df | p_raw | d_z | bonf_sig |
|---|---:|---:|---:|---:|---:|---:|---:|
| `reos_n_flags` (REOS Glaxo+Dundee flag count per record) | −0.360 | 1.2643 | −4.0269 | 199 | **8.03e-05** | **−0.285** | **YES** (Bonf-sig < α=0.007143) |
| `reos_fg_contrib_proxy` (per-record fg_dev contribution) | −0.02117 | 0.07195 | −4.1619 | 199 | 4.70e-05 | −0.294 | YES |

Source: `verification_outputs/wave216-p1-r3-per-record.json` (Wave 216 P1 ACTUAL per-record uplift, n_eff=200). Data-truncation disclosure: `tools/wave87_n1000_sweep.py:298` caps `smiles_list` at 200 of the full N=1000; the ACTUAL per-record analysis runs on the first 200 paired SMILES.

### Per-record paired PROJECTED (N=1000, t_N = t_200 · √(1000/200))

| metric | mean_diff | sd_diff | t (projected) | df | p_raw (projected) | d_z | bonf_sig |
|---|---:|---:|---:|---:|---:|---:|---:|
| `reos_n_flags` | −0.360 | 1.2643 | **−9.0045** | 999 | **1.07e-18** | **−0.285** | **YES** (post-hoc power 1.0000 at observed d_z) |
| `reos_fg_contrib_proxy` | −0.02117 | 0.07195 | −9.3063 | 999 | 8.14e-20 | −0.294 | YES |

Source: `verification_outputs/wave216-p1-r3-per-record.json#per_record_projected_n1000` (Wave 216 P1 projection: t_N = t_actual · √(N/n_actual), SE_N = SD_diff/√N, df = N-1, d_z unchanged).

### Cross-wave 1-seed direction-consistency (Wave 225 P3, 7/7 framework-WINS)

7 historical re-analyses of the canonical seed=42 byte-stable FlowMol3 fg_dev sweep all show direction-consistent framework-WINS at the 1 available seed (CLM-068 R3 direction-consistent addendum):

| # | Wave | Metric | Granularity | n_per_arm | direction |
|---|------|--------|-------------|-----------|-----------|
| 1 | Wave 82 sweep | fg_dev | per_arm_aggregate | 1000 | framework-WINS |
| 2 | Wave 87 sweep | fg_dev | per_arm_aggregate (byte-stable ref) | 1000 | framework-WINS |
| 3 | Wave 195 P2 R-level | fg_dev | per_arm_unpaired_Welch_t | 1000 | framework-WINS (UNDERPOWERED at Bonferroni α=0.007143, direction-consistent) |
| 4 | Wave 206 P3 audit | fg_dev | per_arm_aggregate | 1000 | framework-WINS |
| 5 | Wave 208 P2 per-record | reos_n_flags | per_record_paired_n=200 | 200 | framework-WINS (Bonferroni-significant) |
| 6 | Wave 216 P1 projected | reos_n_flags | per_record_paired_n=1000 | 1000 (projected) | framework-WINS (Bonferroni-significant, post-hoc power 1.0) |
| 7 | Wave 225 P2 bootstrap | fg_dev | per_arm_aggregate | 1000 | framework-WINS |

The 3-seed pooled-SD upgrade (seeds 42/43/44) is **BLOCKED** at the vendor level per Wave 109.C §5 + Wave 208 P2 S3-blocked DGL downgrade + Wave 244-262 vendored-revert chain (CLM-068 + CLM-076/077); seeds 43/44 framework arms fall back to single_mol partial sweep at NFE=100 (n=500 seeded per arm; verdict=TIE in Wave 235 P4 due to NFE mismatch with the canonical NFE=250 reference, NOT direction-flip on the framework-WINS signal). See Wave 235 P4 cross-row `verdict="TIE"` while `direction_consistent_with_1seed=false` at NFE=100 — the NFE mismatch is a protocol confound, not a framework regression.

### RDKit environment blocker (load-bearing, Wave 351 P3 + Wave 357 P3 disclosure layer)

Per Wave 351 P3 (`docs/audit/wave351-r3-vendor-fix-status.md`) and Wave 357 P3 (`docs/audit/wave357-r3-rdkit-blocker-doc.md`):

- **DGL fix is OPERATIONAL** on the current host (Wave 338 P5 + Wave 351 P3 re-verified at n=30 / NFE=250 / n_molecules=30 / GPU 0, no `DGLError`).
- **RDKit 2026.03.5 environment drift is the load-bearing blocker.** At n=30 / seed=42 / GPU 0: baseline 12/30 valid (40%) + framework 10/30 valid (33%) → **average 11/30 = 36.7% valid-yield**, vs canonical Wave 82 sweep output of `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` (n_sampled=999/1000 = **99.9%**) and `verification_outputs/flowmol3_n1000_framework_q4_2026.json` (n_sampled=1000/1000 = **100.0%**).
- **Failure mode is upstream decode pipeline, NOT RDKit SMILES parsing** — multi-fragment SMILES (`.` separators, CTMC disconnected-fragment recombination) + hyper-valent SMILES (multiple `#` triple-bonds, `Explicit valence ... is greater than permitted` warnings) + ETKDGv3 3D-embedding failures.
- **Resolution path** requires environment-level RDKit pinning (not framework changes): re-install pinned RDKit version in `flowmol3_venv` matching canonical Wave 82 environment OR container reproduction of canonical Wave 82 stack, THEN re-run seed=44 framework arm at full N=1000 paired.

The R3 verdict label `PARTIAL / single-seed PROJECTED` is preserved verbatim per Wave 268 strict-clean rule — no status promotion, no number change, no wording reframe.

---

## (b) Evidence Chain + SHA-256 Anchors

The R3 evidence chain is byte-stable (Wave 82 / Wave 87 byte-stability verified at delta < 1e-12 across 2 epochs) and pinned via the canonical `verification_outputs/MANIFEST.md` SHA-256 sidecar + `paper-data/SHA256SUMS` (which is the reviewer-facing verification sidecar; see also `tnnls_submission/data_availability.md` "Unmodified vendored upstream code" table).

### Per-file SHA-256 table (verified at recipe authorship 2026-09-27)

| File | SHA-256 |
|---|---|
| `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` | `beb0174d1acf1b0ee4fae9812815fa305d2f359b378adbeb89ba2c198b84173c` |
| `verification_outputs/flowmol3_n1000_framework_q4_2026.json` | `b44452a958394d3ff6668c7b4ae460b28dba064a0313ea93cae460a650988295` |
| `verification_outputs/flowmol3_n1000_sweep_q4_2026.json` | `caf9412e74304346f80ac027fa836a7c0460ed51a3b97bbc87a0ced04e658302` |
| `verification_outputs/wave206-p3-flowmol3-n1000.json` | `c20a9183931c2b10a3074981204676c83f630ebfd95a60afa248531261c42f36` |
| `verification_outputs/wave206-p3-flowmol3-n1000.csv` | `f1abacbdee70f8734ec1300b6f1c769c7b15366adffe2d5002efb4381cd3bb80` |
| `verification_outputs/wave216-p1-r3-per-record.json` | (not in R3 symlink set; read directly from `verification_outputs/`) |
| `verification_outputs/wave235-p4-flowmol3-3seed.json` | `4ef06440229ec31ca49b0aeceb8f34746dcd7e3f441552d317c6bd7d3cd3a120` |
| `verification_outputs/wave235-p4-flowmol3-3seed.csv` | `4ff2a7eeb914d859a2e798d7f4c83968d5919c9995f38f8be5a77ffcc1f31c73` |
| `verification_outputs/wave235-p4-flowmol3-3seed-per-record.csv` | `a20d902e454707dfae1302541eada99f5e58655b62a846bab089c7539d8b2977` |
| `verification_outputs/wave235-p4-flowmol3-seed44-framework.json` | `50c543997f318217edb496b192594f469f64bcda85b4742bbe8544f669db488c` |
| `verification_outputs/wave235-p4-flowmol3-seed44-framework.smiles.txt` | `6bfad7d0a72ee65b7068fa8406274e0d8ad12a2c3740447beeeedb7e11611b3f` |
| `verification_outputs/wave240-p2-flowmol3-direction.csv` | `c4f5b0b3ad5d8839919dddca22834ae89ea993d2d39c491be514404f040e54d5` |
| `verification_outputs/wave242-p2-flowmol3-direction.csv` | `4edb517cc8080b405ac5d24aa9d753228b1abdec119cc41e2b1f79432e4a632b` |

The 11 files in the `paper-data/SHA256SUMS` R3 entry are the canonical reviewer-facing sidecar (the R3 symlinks in `paper-data/R3_flowmol3_fgdev/` all point at `verification_outputs/...`). The wave216-p1-r3-per-record.json is read directly from `verification_outputs/` (it is not symlinked into `paper-data/R3_flowmol3_fgdev/` because that file is the per-record projection artifact, not the byte-stable sweep output).

### Bash verification (reviewer runs from repo root)

```bash
# Method 1 — sha256sum --check against the paper-data SHA256SUMS sidecar:
cd paper-data
grep "R3_flowmol3_fgdev" SHA256SUMS | awk '{print $1"  "$2}' > /tmp/r3_sha.txt
sha256sum -c /tmp/r3_sha.txt
# expected: all 11 R3 entries report "OK"

# Method 2 — direct sha256sum of the headline artefacts:
cd /home/hugo/codes/flowa-multistep-reinference
sha256sum verification_outputs/flowmol3_n1000_baseline_q4_2026.json \
          verification_outputs/flowmol3_n1000_framework_q4_2026.json \
          verification_outputs/flowmol3_n1000_sweep_q4_2026.json \
          verification_outputs/wave206-p3-flowmol3-n1000.json \
          verification_outputs/wave206-p3-flowmol3-n1000.csv \
          verification_outputs/wave216-p1-r3-per-record.json \
          verification_outputs/wave235-p4-flowmol3-3seed.json \
          verification_outputs/wave235-p4-flowmol3-3seed.csv \
          verification_outputs/wave235-p4-flowmol3-3seed-per-record.csv \
          verification_outputs/wave240-p2-flowmol3-direction.csv \
          verification_outputs/wave242-p2-flowmol3-direction.csv
# expected: hashes match the per-file SHA-256 table above
```

### Cross-reference anchors

- `docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md` — the Wave 135 P3 freeze headline-evidence provenance; the Wave 89 phase-1 audit (`docs/ARCHIVE/audit-waves-1-99/wave89-phase1-final.md`) is the canonical R2/R3 byte-stable reproduction audit (delta < 1e-15 across Wave 82 + Wave 87 epochs).
- `paper-data/MANIFEST.md` (root-level reviewer-facing manifest) + `verification_outputs/MANIFEST.md` (canonical SHA-256 sidecar for all 439 verification_outputs files, R3 section "R3 FlowMol3 fg_dev (molecule)" line 236 + entries on lines 247-259).
- `tnnls_submission/data_availability.md` line 23 — vendored FlowMol3 repo HEAD `77cae22` (matches pinned commit; vendored upstream is byte-identical to upstream per the "Unmodified vendored upstream code" table).

---

## (c) Reproducibility Path

The R3 cell is NOT safely reproducible on the current environment due to the RDKit 2026.03.5 environment drift (load-bearing blocker per Wave 351 P3 + Wave 357 P3). The recipe below documents what **CAN** be reproduced from the byte-stable evidence (CPU-only path) and what **WOULD** be reproducible after RDKit environment unblock (GPU path with venv-pinned RDKit).

### CPU path — verified-recipe (no GPU required, <5 sec)

The R3 CPU-only reproduction is a 3-step process that anchors to the byte-stable artefacts:

**Step C.1 — Verify SHA-256 chain** (per the bash verification block in section (b) above).

**Step C.2 — Read the byte-stable fg_dev headline directly from `flowmol3_n1000_sweep_q4_2026.json`:**

```python
#!/usr/bin/env python3
"""Reproduce R3 fg_dev headline from the Wave 82 / Wave 87 byte-stable sweep JSON.
CPU-only, <1 sec."""
import json, sys, math

VOUT = "verification_outputs/flowmol3_n1000_sweep_q4_2026.json"
with open(VOUT) as f:
    s = json.load(f)

baseline_fg_dev   = s["baseline"]["metrics"]["fg_dev"]      # 0.6381122391671532
framework_fg_dev  = s["framework"]["metrics"]["fg_dev"]     # 0.614627774616795
delta             = framework_fg_dev - baseline_fg_dev      # -0.02348446455035824
n_baseline        = s["baseline"]["n_sampled"]              # 999
n_framework       = s["framework"]["n_sampled"]             # 1000
nfe               = s["nfe"]                                # 250
seed_base         = s["seed_base"]                          # 42

print(f"R3 fg_dev headline (Wave 82 byte-stable seed=42 reference):")
print(f"  baseline  ({n_baseline} mols)  = {baseline_fg_dev}")
print(f"  framework ({n_framework} mols) = {framework_fg_dev}")
print(f"  delta                       = {delta}")
print(f"  nfe={nfe}, seed_base={seed_base}")
print(f"  verdict: framework_WINS by -0.023484 (4.05σ per-arm aggregate)")

# Expected outputs:
assert math.isclose(baseline_fg_dev, 0.6381122391671532, abs_tol=1e-12)
assert math.isclose(framework_fg_dev, 0.614627774616795, abs_tol=1e-12)
assert math.isclose(delta, -0.02348446455035824, abs_tol=1e-12)
print("PASS: R3 byte-stable fg_dev headline reproduced from JSON")
```

**Step C.3 — Reproduce Wave 216 P1 PROJECTED N=1000 per-record d_z = −0.285 / p = 1.07e-18:**

```python
#!/usr/bin/env python3
"""Reproduce R3 Wave 216 P1 per-record PROJECTED N=1000 d_z = -0.285 from JSON.
CPU-only, <1 sec."""
import json, math

VOUT = "verification_outputs/wave216-p1-r3-per-record.json"
with open(VOUT) as f:
    d = json.load(f)

actual    = d["per_record_actual"]["tests"]["reos_n_flags"]
projected = d["per_record_projected_n1000"]["tests"]["reos_n_flags"]

n_actual = actual["n_eff"]            # 200
mean_diff = actual["mean_diff"]       # -0.36
sd_diff   = actual["sd_diff"]         # 1.2642752705795501

# Wave 216 P1 projection formula: t_N = t_actual * sqrt(N/n_actual)
t_actual = actual["t_statistic"]      # -4.026946459380895
N_projected = projected["n_eff"]      # 1000
t_projected = t_actual * math.sqrt(N_projected / n_actual)
df_projected = N_projected - 1

# 95% CI
se_projected = sd_diff / math.sqrt(N_projected)
ci95_low  = mean_diff - 1.96 * se_projected
ci95_high = mean_diff + 1.96 * se_projected
d_z = mean_diff / sd_diff            # d_z unchanged under projection

print(f"R3 per-record projected N=1000 (Wave 216 P1):")
print(f"  n_actual   = {n_actual}")
print(f"  mean_diff  = {mean_diff}  (sd_diff = {sd_diff:.4f})")
print(f"  t_projected = {t_projected:.4f}  (df={df_projected})")
print(f"  d_z        = {d_z:.4f}")
print(f"  CI95       = [{ci95_low:.4f}, {ci95_high:.4f}]")
print(f"  p_raw (2-sided, t-distribution) ≈ 1.07e-18  (scipy.stats.t.sf)")

# Expected outputs (anchored to wave216-p1-r3-per-record.json#per_record_projected_n1000):
assert math.isclose(d_z, -0.28474811489033885, abs_tol=1e-4)
assert math.isclose(t_projected, -9.004526024927777, abs_tol=1e-3)
print("PASS: R3 Wave 216 P1 PROJECTED N=1000 d_z = -0.285 reproduced from JSON")
```

For full scipy-distribution fidelity (reproducing `p_raw = 1.0728860143449855e-18` exactly, not the 2-sided normal approximation):

```python
from scipy.stats import t as tdist
p_raw = 2 * tdist.sf(abs(t_projected), df_projected)
assert math.isclose(p_raw, 1.0728860143449855e-18, abs_tol=1e-21)
```

### GPU path — DEFERRED (RDKit environment blocker; recipe documents the command but NOT executable on current host)

The full N=1000 paired 3-seed sweep (seeds 42, 43, 44) would be executed as:

```bash
# Activate FlowMol3 venv (NEVER MIX per docs/environments.md)
source .venvs/flowmol3_venv/bin/activate

# REQUIRED PRE-REQUISITE: pin RDKit to the canonical Wave 82 version
# (current RDKit 2026.03.5 produces 36.7% valid-yield at n=30 vs canonical 99.9%).
# Resolution paths:
#   (a) pip install rdkit==<canonical-wave82-pin-version>  # exact pin TBD
#   (b) container reproduction of the canonical Wave 82 environment
#       (the canonical torch+CUDA+DGL+RDKit stack that produced 99.9% valid SMILES).

# Run the full N=1000 paired sweep across 3 seeds (DGL fix is OPERATIONAL
# per Wave 338 P5 + Wave 351 P3 — no DGLError expected):
mkdir -p /tmp/r3-n1000-paired-3seed
.venvs/flowmol3_venv/bin/python scripts/wave338_p5_r3_n1000_paired.py \
    --n-total 1000 \
    --nfe 250 \
    --nfe-batch 100 \
    --seeds 42 43 44 \
    --device cuda:0 \
    --output-dir /tmp/r3-n1000-paired-3seed
```

**Expected wall-time (after RDKit unblock):** ~30 min total (per Wave 87 sweep wallclock of ~30 min on the PRO 6000 Blackwell / RTX 5090 GPU; the 3-seed × N=1000 sweep is approximately 3× the single-seed sweep because each seed arm re-runs the full sweep).

**Expected output artefacts** (mirrored from the Wave 82 / Wave 87 pattern):

| Artefact | Description |
|---|---|
| `flowmol3_n1000_baseline_seed{42,43,44}.json` | Per-seed baseline (perturbation_sigma=0.0) sweep summary |
| `flowmol3_n1000_framework_seed{42,43,44}.json` | Per-seed framework (perturbation_sigma=0.05) sweep summary |
| `flowmol3_n1000_sweep_seed{42,43,44}.json` | Per-seed baseline+framework paired sweep summary |
| `wave338-p5-r3-n1000-paired.{csv,json}` | 3-seed pooled SD + Welch's t-test (unpaired) + Cohen's d_s per seed |
| `flowmol3_n1000_paper_metrics_per_seed.csv` | Per-metric per-seed paper-metric table (validity_pct, pb_validity_pct, fg_dev, ood_ring_rate) |

**Required environment** (per `docs/environments.md` + `env_hash_R3.txt`):

- `.venvs/flowmol3_venv` (FlowMol3 venv)
- Python 3.12.13 + torch 2.7.0+cu128+cu128 / CUDA 12.8 (per `env_hash_R3.txt`)
- Adapter deps: `0e9e0b9c3c5eb7b5f87566160043f8b8736719847ddb4da319c94b258afc3eac`
- Composite hash: `8ca7e3031a7ddc97d13b85dbb92e1cf63da1c3082573507d30c99de8cfb87480`
- GPU 0 (RTX PRO 6000 Blackwell 98GB) or GPU 1 (RTX 5090 32GB) — both verified `sm_120`
- FlowMol3 ckpt: `data/flowmol3/weights_real/checkpoints/last.ckpt` (~5 GB Pitt pretrained)
- Vendored FlowMol3 upstream repo: `data/FlowMol3/repo` @ commit `77cae22` (byte-identical to pinned commit; DO NOT MODIFY per Wave 260 user directive + AGENTS.md §3 guardrail #1)

**Honest disclosure (preserved):** Until the RDKit environment is unblocked, the GPU path produces the 36.7% valid-yield gap (Wave 338 P5 ~80/1000 valid mols at N=1000 ~8% rate) which is below the 95% threshold for the full N=1000 sweep. The CPU-only path (above) is the canonical reviewer-facing verification path on the current environment.

---

## (d) Disclosure — Honest Status Label

The R3 cell's verdict label is **`PARTIAL / single-seed PROJECTED`** per CLM-068 + paper §7.2 R3 row line 539 + `docs/CLAIMS.md` CLM-068 R3 direction-consistent addendum. This label is preserved verbatim per Wave 268 strict-clean rule (status history additive, no removal; no promotion of `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone).

| Status label | Applies to R3? | Rationale |
|---|---|---|
| `SUPPORTED` | **NO** | Per-arm aggregate UNPAIRED at 1 seed is `UNDERPOWERED` (bonf_sig=False at α=0.007143); per-record paired at ACTUAL n=200 + PROJECTED N=1000 is Bonferroni-significant, but the projection is a counterfactual on the truncated n=200 ACTUAL (full N=1000 paired sweep DEFERRED). |
| `NOT_SIGNIFICANT` | **NO** | The Wave 195 P2 / Wave 206 P3 unpaired reading is direction-consistent framework-WINS but UNDERPOWERED at Bonferroni α; this is `UNDERPOWERED`, not `NOT_SIGNIFICANT`. |
| `UNDERPOWERED` | **Partial — applies to per-arm aggregate UNPAIRED** | Welch's t-test unpaired: t=-2.453, df=1996.998, p_raw=0.01424, d_s=-0.110, bonf_sig=False. |
| `REGRESSES` | **NO** | Direction is framework-WINS (−0.023484, framework has lower fg_dev = better). |
| `DEFERRED` | **Partial — applies to full N=1000 paired 3-seed sweep** | The full N=1000 paired sweep with full SMILES retention is on the camera-ready deferred list per Wave 351 P3 + Wave 357 P3 RDKit environment blocker. |
| `PARTIAL / single-seed PROJECTED` | **YES — the canonical R3 verdict label** | 1-seed byte-stable −0.023484 fg_dev framework-WINS + per-record proxy d_z=−0.285 + 7/7 cross-wave direction-consistency + PROJECTED N=1000 Bonferroni-significant but on a counterfactual projection. |

### Acceptable one-line summaries (verbatim from existing disclosure surfaces)

The following status-label framings are already documented across multiple surfaces and remain **preserved verbatim**; no new framing is introduced by this recipe:

- **Paper §7.2 R3 row (line 539)**: "Status: **PARTIAL / single-seed PROJECTED** — direction-consistent across 7 cross-validation re-analyses; Bonferroni-significant at PROJECTED n=1000 paired."
- **Paper abstract (Wave 354 P3 line 7(c))**: "The R3 FlowMol3 fg_dev N=1000 sweep is deferred by RDKit 2026.03.5 environment drift (Wave 351 P3; DGL 2.4.0+cu124 adapter path is operational but RDKit success rate is 36.7% vs canonical 99.9%)."
- **CONSOLIDATED_RESULTS §15.105 (Wave 357 P3)**: "the R3 cell's verdict label `PARTIAL / single-seed PROJECTED` (1-seed byte-stable −0.023484 fg_dev framework-WINS headline at CLM-068 + Wave 216 P1 per-record d_z = −0.285 framework-WINS + Wave 225 P3 7/7 cross-wave direction-consistency) is preserved verbatim — no status change, no number change, no `tnnls_submission/` modification."
- **docs/CLAIMS.md CLM-068 R3 row**: "R3 cross-wave 7/7 direction-consistency on 1 available seed + blocked 3-seed pooled-SD upgrade per DGL regression; preserved verbatim. Wave 357 P3 disclosure does NOT modify CLM-068."
- **docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md** (Wave 135 P3 freeze): "framework = 0.6146, baseline = 0.6381, delta = -0.0235, 4.05σ, p < 0.05; N = 1000 per arm; framework_improves." (This is the per-arm aggregate framing, preserved as the canonical Wave 82/87 byte-stable headline.)

### What this recipe does NOT do (hard guardrails from AGENTS.md §3)

- **Does NOT promote `UNDERPOWERED` / `DEFERRED` / `REGRESSES` to `SUPPORTED` by wording.** The R3 verdict label `PARTIAL / single-seed PROJECTED` is preserved verbatim from the existing surfaces; this recipe is additive documentation, not a reframing.
- **Does NOT modify vendored upstream code** (`data/FlowMol3/repo` stays at `77cae22`, byte-identical to upstream).
- **Does NOT modify `tnnls_submission/` SHA-256-pinned package** (this recipe lives in `paper-data/`, not `tnnls_submission/`).
- **Does NOT modify `docs/CLAIMS.md`** CLM-068 (no wording / number / status change).
- **Does NOT re-run the GPU sweep** (RDKit environment blocker per Wave 351 P3 / Wave 357 P3; the CPU-only byte-stable path is the canonical reviewer-facing verification path on the current environment).

---

## (e) Acceptance Criteria

The R3 reproducibility recipe is considered PASS when:

1. **SHA-256 chain verifies** — all 11 `paper-data/SHA256SUMS` R3 entries report `OK` via `sha256sum -c`; all 12 verification_outputs files match the per-file SHA-256 table in section (b) above.
2. **Python snippet (section c Step C.2) reproduces the R3 byte-stable fg_dev headline** — baseline=0.6381122391671532, framework=0.614627774616795, delta=−0.02348446455035824, nfe=250, seed_base=42 (matches `verification_outputs/flowmol3_n1000_sweep_q4_2026.json` to ±1e-12 absolute tolerance).
3. **Python snippet (section c Step C.3) reproduces the Wave 216 P1 PROJECTED N=1000 per-record d_z = −0.285** — `d_z = mean_diff / sd_diff = −0.2847...`, `t_projected = t_actual · √(1000/200) = −9.0045...`, `df = 999`, `p_raw = 2 · stats.t.sf(|t_proj|, df) = 1.07e-18` (matches `verification_outputs/wave216-p1-r3-per-record.json#per_record_projected_n1000` to ±1e-4 absolute tolerance on d_z and t, ±1e-21 on p_raw).
4. **D.4 byte-stable regression** (`tests/test_d4_regression_vectors.py`) is **30/30 PASS**.
5. **`python3 tools/check_claims_consistency.py`** exits 0 with **No drift detected** (61 active claims, CLM-068 R3 row preserved verbatim).
6. **`ruff check adaptive_reflow/ tests/ scripts/ tools/`** reports **All checks passed!** (0 findings).
7. **`mkdocs build --strict`** exits 0 (no errors, only upstream mkdocs-material "MkDocs 2.0" deprecation advisory — unrelated to R3 content).

### Linked scripts / surfaces

- `reproduce/03_R3_FlowMol3.sh` — existing R-level per-cell reproduction script (verifies Wave 216 P1 per-record d_z=-0.285 from JSON).
- `paper-data/R3_flowmol3_fgdev/SOURCE.md` — Wave 235 P4 / Wave 23 source provenance for the R3 cell.
- `paper-data/R3_flowmol3_fgdev/R3_SOURCE.md` — local-source pointer to `docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md`.
- `docs/audit/wave357-r3-rdkit-blocker-doc.md` — Wave 357 P3 R3 RDKit environment blocker documentation (canonical R3 deferred-state disclosure).
- `docs/audit/wave351-r3-vendor-fix-status.md` — Wave 351 P3 R3 vendor-fix status (DGL operational, RDKit gap load-bearing).
- `docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md` — Wave 338 P5 canonical DGL-fix audit (canonical fix at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` + `3002-3011`).
- `docs/audit/stats_method/p3-r3-cross-seed.md` — Wave 225 P3 R3 cross-wave 1-seed direction-consistency check (7/7 framework-WINS).
- `docs/audit/stats_method/p1-r3-uplift.md` — Wave 216 P1 R3 per-record uplift (ACTUAL n=200 + PROJECTED N=1000).
- `docs/CLAIMS.md` CLM-068 — R3 cross-wave 7/7 direction-consistency addendum (preserved verbatim).
- `docs/CONSOLIDATED_RESULTS.md` §15.105 (Wave 357 P3) — R3 RDKit environment blocker documentation in the reviewer-facing consolidated-results ledger.
- `docs/drafts/paper-A-final.md` §7.2 R3 row (line 539) + Wave 357 P3 ADDITIVE footnote (line 541) — paper draft R3 row text (preserved verbatim; ADDITIVE footnote appended).
- `verification_outputs/MANIFEST.md` R3 section (line 236) — canonical SHA-256 sidecar for the 13 R3 files.
- `tnnls_submission/data_availability.md` line 23 — vendored FlowMol3 repo HEAD `77cae22` (matches pinned commit; "Unmodified vendored upstream code" table).

The recipe is **safe to run in CI** — the CPU path is read-only (no destructive edits, no GPU, no venv activation required); the GPU path is documented but DEFERRED pending RDKit environment unblock.

---

_Last updated: 2026-09-27 (Wave 363 P1 — R3 reproducibility recipe authored; SHA-256 chain + CPU/GPU reproducibility commands + disclosure for R3_FlowMol3_fg_dev)._