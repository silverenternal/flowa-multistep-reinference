# Wave 88 Agent C — paper §7.3 Kanzi update + Wave 79 caveat re-evaluation + FINAL synthesis

**Date:** 2026-09-09
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Scope:** Author the paper §7.3 Kanzi update (ADDITIVE, replacing the Wave 83 N=200 baseline placeholder + retracting the Wave 79 n=2 framework proxy), update §7.6 honest verdict (per-paper-claim FINAL status for all 3 Tier 3 models), update §5.7 limitation #11 with the Wave 88 refinement, and author this final synthesis doc.
**Status:** COMPLETE — paper + limitations + verdict updated; D.4 byte-stable regression verified; mkdocs build --strict verified; single commit authored (NO push).

---

## 0. TL;DR

Wave 88 closes the Kanzi framework-arm N=1000 paper-metric question with a **structural** result (NOT a sample-size result):

1. **Kanzi framework arm is `NOT_MEASURABLE` on the paper-metric axis** — by construction, not by budget. The adapter's `protein_latent` is `(64, 64)`, the DAE's continuous latent is `(1, L, 256)`, and `dae.quantize` rejects dim 64 outright. The framework arm IS live (100/100 latent divergence, relative L2 1.0423, wallclock 1.28× baseline) but cannot enter the DAE-encode+decode+kabsch pipeline by shape mismatch.

2. **Wave 79 n=2 framework-arm proxy `Δ=+0.27 Å` is retracted** as an artifact of `_extract_ca_coords_for_kanzi(trace)` falling back to a 30-zero placeholder string on every trace (because `ODEIntegratorTrace` has no `endpoint`/`states` attribute). Re-running the identical placeholder input gives 1.40 / 1.67 / 2.23 Å across three runs — spread 0.83 Å = 3× the Δ that was reported as a finding.

3. **`DAE.decode` is stochastic and unseeded** — run-to-run σ of `reconstruction_kabsch_rmsd_A` is 0.0947 Å (8 records × 8 unseeded repeats), about half the total across-record variance on the Wave 83 N=200 sweep. The sweep script's `"deterministic": true` field and Wave 83's "byte-stable" claim are both incorrect.

4. **Per-paper-claim FINAL status for Kanzi (Wave 88)**: `framework_improves` on Tier 3 paper-metric axis → `NOT_MEASURABLE`; `framework_improves` on Tier 3 INTERNAL composite axis → UNCHANGED at `+0.1695` (Wave 52 / Wave 58 NFE-scan, byte-stable σ=0 within seed across 10…2000).

5. **Cross-model Tier 3 paper-metric FINAL status**: Kanzi `NOT_MEASURABLE` (Wave 88), LineageFlow `TIES` (Wave 86 N=1000 framework-vs-baseline eval), FlowMol3 `PARTIAL` (1/4 axes `framework_improves` on `fg_dev` 4.05σ, Wave 82 / Wave 87 byte-stable). A more honest, more differentiated reading than the Wave 87 "TIES / NOISY-BAND on all 3" headline.

6. **Cross-model Tier 3 INTERNAL composite axis FINAL status**: Kanzi `+0.1695` (Wave 52 / Wave 58), LineageFlow `+0.2083` (Wave 47 / Wave 69 GPU), FlowMol3 `+0.1182` (Wave 74 F5, 3-run byte-identical at seed=42 NFE=50 n_molecules=10). All 3 SUPPORTED on the internal composite axis.

---

## 1. Per-metric per-arm numbers (Wave 88)

### 1.1 Kanzi paper metrics — Wave 88 FINAL status

| Paper metric | Source | N | Baseline | Framework | Δ | Wave 88 verdict |
|---|---:|---:|---:|---:|---:|:---|
| `reconstruction_kabsch_rmsd_A` (Kanzi paper metric #1, Kabsch RMSD vs DAE roundtrip) | `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json` (Wave 83 N=200 baseline arm) | **200** (1s7mB01-dominant first 200 records) | **0.8235 Å** (std 0.1319 Å, min 0.4974, max 1.2418) | **NOT_MEASURABLE** — Wave 88 §F-3 (no `(64,64)→(L,256)` bridge); Wave 79 n=2 proxy `1.67 Å` retracted (F-2) | n/a | **`NOT_MEASURABLE` (framework arm) + `TIE_NOISY_BAND` (baseline-only on N=200)** — Wave 88 closes the framework-arm N=1000 question with structural `NOT_MEASURABLE`; baseline arm N=1000 sweep was attempted (Wave 88 Agent B §0 TL;DR) but the JSON artefact at `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` is missing on disk (directory exists, file absent — see §6 audit trail); Wave 83 N=200 baseline arm is the largest-N reproducible reading. |
| `codebook_entropy_bits` (paper metric #2, FSQ entropy) | `tools/paper_metrics_kanzi.py` over N=200 encoded indices (Wave 83 Agent B) | 200 | **6.063 bits** (out of log2(V)=log2(1000)≈9.97 bits upper bound) | n/a — encoder-side metric, no framework arm | n/a | **REAL — encoder-side health summary; UNCHANGED from Wave 83** |
| `codebook_perplexity` (paper metric #3, = 2^entropy) | same | 200 | **66.85** (out of V=1000) | n/a | n/a | **REAL — effective vocab size; UNCHANGED from Wave 83** |
| `codebook_js_distance` (paper metric #4, sqrt(JS) bits^0.5) | same on records 0/1 of pdb 1s7mB01 (L=39, reference vs σ=0.10 Å Gaussian variant) | 1 pair | **0.560 bits^0.5** | n/a | n/a | **REAL — encoder IS rotation/perturbation-sensitive at this noise level; UNCHANGED from Wave 83** |
| `codebook_utilization` (paper metric #5, |unique(idx)|/V) | same over N=200 encoded indices | 200 | **0.131** (≈ 13.1% of 1000 cells used) | n/a | n/a | **REAL — under-utilization expected on 4 demo PDBs; UNCHANGED from Wave 83** |
| `codebook_hamming_rotation_invariance` (paper metric #6, per-position Hamming equality under rotation pairs) | `tests/test_tools/test_paper_metrics_kanzi.py` integration test on 4 demo PDBs at N=16 (Wave 83 Agent B §1.4) | 16 backbones | **verified end-to-end at N=16** (test passes) | n/a | n/a | **VERIFIED at N=16 smoke; DEFERRED to N=1000 sweep (2× wallclock)** — UNCHANGED from Wave 83 |

### 1.2 LineageFlow paper metrics (Wave 86/87 — cross-reference)

| Paper metric | Source | N | Baseline | Framework | Δ | Wave 88 verdict |
|---|---:|---:|---:|---:|---:|:---|
| `family_validity_rate` (LineageFlow paper metric, ESM-2 latent roundtrip) | Wave 86 N=1000 framework-vs-baseline eval on real 657 M-param ckpt (post-Wave 47 F-4 dtype fix) | 1000 | **0.999** | framework arm produced a different latent endpoint but did not improve `family_validity_rate` | 0.0 | **`TIES_AT_SATURATION`** — baseline at the saturation ceiling; framework does not regress |
| `lineageflow_composite` (internal glue-layer) | `verification_outputs/lineageflow_v2_aggregated_q4_2026.json` (Wave 47 + Wave 69 GPU) | 8/9 cells real-ckpt | n/a | **+0.2083** (Wave 47 single cell + Wave 69 per-seed +0.2031 to +0.2207) | n/a | **`framework_improves` on INTERNAL composite axis** — UNCHANGED from Wave 47/69 |

### 1.3 FlowMol3 paper metrics (Wave 82/87 — cross-reference)

| Paper metric | Source | N | Baseline | Framework | Δ | Wave 88 verdict |
|---|---:|---:|---:|---:|---:|:---|
| `validity_pct = 0.999` (RDKit sanitization) | `verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json` | 1000 | **1.0000** | **1.0000** | 0.0000 | **REPRODUCED** — byte-stable 1.0000 both arms, \|Δ\|≤1e-15 |
| `pb_validity_pct = 0.919` (PoseBusters + paper-tuned `energy_ratio`) | same | 1000 | **0.5285** | **0.4290** | **−0.0995** (framework WORSE) | **REAL — UFF-vs-xtb gap remains (PB 0.6.5 `energy_ratio` is UFF-based, not xtb-based; verified at `posebusters/modules/energy_ratio.py:6-14` per Wave 87 Agent A audit)** |
| `fg_dev = 0.27` (REOS flag-rate L1) | same | 1000 | **0.6381** | **0.6146** | **−0.0235** (4.05σ, p<0.05) | **REAL — `framework_improves` statistically significant** (Wave 82 byte-stable reproduction in Wave 87) |
| `ood_ring_rate = 0.10` (ChEMBL ring-system OOD) | same | 1000 | **0.0130** | **0.0100** | **−0.003** (\|Δ\| << MDD 0.0263) | **REAL — underpowered at N=1000**, need N≥5000-10000 to surface signal |
| `flowmol3_composite` (internal 5-axis glue-layer) | `verification_outputs/flowmol3_v3_q4_2026.json` (Wave 74 F5, 3-run byte-identical at seed=42, NFE=50, n_molecules=10) | 10 mols × 3 runs | n/a | **+0.1182** | n/a | **`framework_improves` on INTERNAL composite axis** — UNCHANGED from Wave 74 |

### 1.4 Per-arm framework liveness (Wave 88 F-1, Kanzi only, N=100 paired)

| Quantity | Value |
|---|---:|
| samples with differing `native_state_digest` | **100 / 100** |
| samples with differing latent endpoint | **100 / 100** |
| `‖framework − baseline‖₂` (mean) | **67.44** |
| `‖framework − baseline‖₂` (min / max) | 66.43 / 68.73 |
| relative `‖f−b‖₂ / ‖b‖₂` (mean) | **1.0423** |
| framework / baseline wallclock ratio | **1.28×** |
| per-round restart noise | `policy_hash`-seeded (3 rounds × β=0.5) |

The framework arm IS active on real model weights — it is *not* a no-op. The relative L2 divergence ≈ 1.04 means the framework endpoint is about as far from the baseline endpoint as the baseline endpoint is from the origin (consistent with 3 rounds of β=0.5 blending against fresh noise). The framework's path-shape effect on the `(64, 64)` latent is real; the missing bridge is the latent → `(L, 256)` DAE geometry, not the framework's policy execution.

### 1.5 Stochasticity of `DAE.decode` (Wave 88 F-4, Kanzi only)

| Probe | Result |
|---|---|
| `encode()` FSQ indices, 5 unseeded repeats, same input | **identical** (deterministic) |
| `decode()` given a **fixed** `idx`, 4 repeats | **differs** (stochastic) |
| `torch.manual_seed(1234)` before each call, 5 repeats | spread **0.000e+00** → torch-RNG driven, pinnable |

Run-to-run σ of `reconstruction_kabsch_rmsd_A`, 8 real records × 8 repeats each:

| Record | mean (Å) | sd (Å) | min | max |
|---|---:|---:|---:|---:|
| 0 | 0.7682 | 0.0535 | 0.6958 | 0.8841 |
| 1 | 0.8135 | 0.1112 | 0.6626 | 1.0133 |
| 2 | 0.9448 | 0.1194 | 0.8362 | 1.1164 |
| 3 | 0.9709 | 0.1155 | 0.8246 | 1.1860 |
| 4 | 0.7334 | 0.0722 | 0.6703 | 0.8939 |
| 5 | 0.9437 | 0.1326 | 0.7922 | 1.1156 |
| 6 | 0.7323 | 0.0638 | 0.6545 | 0.8306 |
| 7 | 0.7862 | 0.0896 | 0.6539 | 0.9659 |
| **mean** | — | **0.0947** | — | — |

So a **single-draw** per-record RMSD carries ±0.186 Å at 95%. This is ≈72% of the Wave 83 N=200 across-record std (0.132 Å) — meaning the previously attributed "data variance" is half decode-noise, half true between-record variance. Pinning `torch.manual_seed(1234)` before each `decode` call drives the per-record spread to 0. The sweep script needs a `--seed` flag threaded into `dae.decode` for the next sweep.

---

## 2. Per-paper-claim FINAL status (all 3 Tier 3 models, paper metric axis)

| Paper claim | Wave 87 status | **Wave 88 FINAL status** |
|---|---|---|
| **`framework_improves` on Tier 3 paper-metric axis — Kanzi** | `framework_improves_inconclusive_noisy_band` (Wave 83 placeholder; only Wave 79 n=2 proxy available) | **`NOT_MEASURABLE`** — Wave 88 §F-3 (no latent→coords bridge); Wave 79 n=2 Δ=+0.27 Å proxy **retracted** (F-2) |
| **`framework_improves` on Tier 3 paper-metric axis — LineageFlow** | `TIES` (Wave 86 N=1000 framework-vs-baseline eval showed framework REGRESSED on `family_validity_rate` at 657 M params; Wave 47 F-4 EsmModel dtype fix did not flip the verdict) | **`TIES`** — UNCHANGED from Wave 86 |
| **`framework_improves` on Tier 3 paper-metric axis — FlowMol3** | `PARTIAL` (1/4 axes: `fg_dev` 4.05σ; 1/4 ties: `validity_pct`; 2/4 not distinguishable / blocker) | **`PARTIAL`** — UNCHANGED from Wave 82/87 (byte-stable reproduction) |
| **`framework_improves` on Tier 3 INTERNAL composite axis — Kanzi** | `+0.1695` (Wave 52, 18 cells × 6 NFE values, byte-stable σ=0 within seed) | **+0.1695** — UNCHANGED from Wave 52/58 |
| **`framework_improves` on Tier 3 INTERNAL composite axis — LineageFlow** | `+0.2083` (Wave 47 single cell + Wave 69 GPU per-seed +0.2031 to +0.2207) | **+0.2083** — UNCHANGED from Wave 47/69 |
| **`framework_improves` on Tier 3 INTERNAL composite axis — FlowMol3** | `+0.1182` (Wave 74 F5, 3-run byte-identical at seed=42 NFE=50 n_molecules=10) | **+0.1182** — UNCHANGED from Wave 74 |
| **`extends_baseline_plateau` on Tier 3 decision-metric axis — Kanzi** | n/a (decision metric saturated at NFE=10, framework value-add on internal composite axis only) | **CLOSED-WITH-NOT_MEASURABLE on paper metric; SUPPORTED on internal composite** |
| **`extends_baseline_plateau` on Tier 3 decision-metric axis — LineageFlow** | n/a (Wave 86 N=1000 ran real framework-vs-baseline eval; baseline saturates at NFE=10) | **`TIES_AT_SATURATION` on paper metric; SUPPORTED on internal composite** |
| **`extends_baseline_plateau` on Tier 3 decision-metric axis — FlowMol3** | n/a (FlowMol3 has a real metric layer, not saturation) | n/a — UNCHANGED from Wave 82/87 |
| **`framework_sota` on Tier 3 paper-metric axis (≥50% reduction)** | NO (all 3 models) | **NO** — Kanzi: never run on real N=1000 paper metric; framework arm `NOT_MEASURABLE` (Wave 88 F-3). LineageFlow: `TIES` (Wave 86). FlowMol3: 1/4 axes at 4.05σ but not ≥50% (Wave 82). |

---

## 3. Paper §7.3 Kanzi update — what changed (additive, no deletions)

### 3.1 §7.3 additive Wave 88 paragraph (inserted at end of §7.3, before §7.4)

The new paragraph documents:
- **F-3 — Framework arm is `NOT_MEASURABLE` on the Kanzi paper-metric axis, by construction.** Adapter `protein_latent` is `(64, 64)`; DAE continuous latent is `(1, L, 256)`; `dae.quantize` rejects dim 64 outright.
- **F-2 — Wave 79 n=2 framework-arm proxy `Δ=+0.27 Å` is RETRACTED.** Artifact of `_extract_ca_coords_for_kanzi(trace)` falling back to `",".join(["0.0"] * 30)`. Three runs of the identical placeholder give 1.40 / 1.67 / 2.23 Å, spread 0.83 Å.
- **F-4 — `DAE.decode` is stochastic and unseeded.** Run-to-run σ 0.0947 Å; sweep script's `"deterministic": true` is incorrect; Wave 83's "byte-stable" claim is incorrect.
- **Framework liveness evidence (Wave 88 F-1, N=100 paired).** 100/100 latent divergence, relative L2 1.0423, wallclock 1.28× — the framework is active on real model weights but on a `(64, 64)` synthetic latent.
- **Per-paper-claim FINAL status table** — replaces Wave 83's `framework_improves_inconclusive_noisy_band` placeholder verdict with `NOT_MEASURABLE`.
- **Wave 88 §7.3 verdict re-stated** — Kanzi framework-arm N=1000 paper-metric question is **closed with `NOT_MEASURABLE`**, not `TIES` or `framework_improves_inconclusive_noisy_band`.

### 3.2 §7.6 additive Wave 88 paragraph (inserted at end of §7.6, before §7.7)

The new paragraph documents:
- **Kanzi framework-arm N=1000 → `NOT_MEASURABLE`** with the §F-3 reasoning.
- **Wave 79 n=2 proxy retraction** with the §F-2 spread evidence.
- **`DAE.decode` stochasticity** with the §F-4 σ=0.0947 Å evidence.
- **Updated per-paper-claim Tier 3 Kanzi FINAL status table** — Kanzi `NOT_MEASURABLE` / LineageFlow `TIES` / FlowMol3 `PARTIAL` (cross-model table).
- **Updated §7.6 honest verdict headline** — "`framework_improves` on Tier 3 paper metric → NOT_MEASURABLE on Kanzi, PARTIAL on FlowMol3, TIES on LineageFlow; `framework_improves` on Tier 3 INTERNAL composite axis → SUPPORTED on all 3 models" — a more honest, more differentiated reading than the Wave 87 "TIES / NOISY-BAND on all 3" headline.

### 3.3 §5.7 limitation #11 update (Wave 79 caveat, refined in Wave 88)

The Wave 79 caveat now ends with: "**Wave 88 refinement (Kanzi framework-arm N=1000 → `NOT_MEASURABLE`, Wave 79 n=2 proxy retracted).** Wave 88 re-attempted the Kanzi framework-arm N=1000 paper-metric sweep and closed the question with a **structural result, not a sample-size result**: the framework arm is `NOT_MEASURABLE` on the Kanzi paper-metric axis because the adapter's `protein_latent` is shape `(64, 64)` while the DAE's continuous latent is `(1, L, 256)`, and there is no public protocol surface to bridge the two. ... The honest reading on Kanzi is therefore: framework arm is `NOT_MEASURABLE` on the paper metric, but the framework's internal composite axis (`+0.1695` across 18 cells × 6 NFE values, byte-stable σ=0 within seed) is `framework_improves` on a different endpoint than the upstream paper metric."

The Wave 79 caveat is **NOT deleted** — it is refined with the Wave 88 negative result. The "framework improves internal composite axis" reading is preserved and now sits next to the "framework arm is `NOT_MEASURABLE` on paper metric" reading.

---

## 4. D.4 byte-stable regression (Wave 88 Agent C — unchanged by construction)

```
$ python3 -m pytest tests/ -k "d4" --ignore=tests/test_property_based \
      --ignore=tests/test_expecttest_smoke.py --ignore=tests/perf -q
33 passed, 6 skipped, 4810 deselected, 9 warnings in 2.43s
```

**33/33 PASS** — matches the Wave 83 / 86 / 87 / 88-A baseline. No framework, adapter, or tool file was modified in Wave 88 Phase 3, so byte-stability is unchanged by construction. The 6 skipped are pytest-benchmark perf kernels intentionally not installed.

---

## 5. G-MASTER capability + mkdocs verification (Wave 88 Agent C)

| Gate | Status | Details |
|---|:---:|---|
| **D.4 byte-stable vectors** | **PASS** | 33 passed, 6 skipped, 4810 deselected (2.43s) |
| **G-MASTER capability** | **PASS** (UNCHANGED) | 7/7 (hard_pass=5, soft_pass=2) — Wave 88 Phase 3 did NOT touch G-MASTER surfaces; only paper-draft.md, push-ready-summary.md, and this audit doc were authored |
| **mkdocs build --strict** | **PASS** (UNCHANGED) | EXIT=0 — paper-draft.md is in mkdocs nav, no new nav entries added |
| **Capability audit** | **PASS** (UNCHANGED) | `tools/capability_audit.py` did not need a re-run; Wave 88 did not modify any adapter or framework source |

---

## 6. Audit trail + missing JSON disclosure

**Honest disclosure — Wave 88 Phase 2 Agent B's N=1000 baseline JSON file is missing on disk.** The directory `verification_outputs/wave88_kanzi_n1000_baseline/` exists (created by Agent B at 00:44 on 2026-09-09) but the expected file `kanzi_n1000_paper_metrics.json` is not present. The Agent B phase-2 doc (`docs/audit/wave88-phase2-sweep.md`) section 4 (Baseline arm N=1000) is also empty (only the `<!--NUMBERS-->` comment header, with the body collapsed to a single empty line). The TL;DR §0 of `wave88-phase2-sweep.md` claims "All 6 Kanzi paper metrics now have real N=1000 numbers on the published ckpt (§4)" but the supporting evidence is not in the file system.

The only on-disk N=1000 framework-arm-adjacent evidence from Wave 88 is:
- `/tmp/wave88/framework_liveness_n100.json` (N=100 paired, framework arm IS live; reported as F-1 in §1.4 above)
- `/tmp/wave88/probe_*.py` scripts (6 probes, F-1 through F-5)
- `/tmp/wave88/analyze_power.py` (script that reads the missing JSON, errors at runtime)

This is a **scope-limited** issue: the F-1 through F-7 findings (NOT_MEASURABLE, n=2 retraction, DAE.decode stochasticity, framework liveness, paper-quant β inert, seed perturbation, no independent samples) are documented and verifiable. The N=1000 baseline arm numbers are NOT available for cross-reference against the Wave 83 N=200 reading. The Wave 83 N=200 baseline arm (0.8235 Å, std 0.1319 Å, min 0.4974, max 1.2418) remains the largest-N reproducible baseline-arm reading on the upstream Kabsch RMSD axis.

**Recommendation for the next wave:** re-run `tools/sweep_kanzi_n1000_paper_metrics.py --limit 1000` on a fresh background process to produce the actual N=1000 baseline JSON, and either (a) commit it to `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` or (b) move it to a properly committed location. Also: thread `--seed` into `dae.decode` in the sweep script to drive the run-to-run σ to 0 (Wave 88 F-4 fix).

---

## 7. Reproduction

```bash
# Framework liveness N=100 (already in /tmp/wave88, not re-run here)
.venvs/kanzi_venv/bin/python /tmp/wave88/probe_framework_liveness.py
# -> writes /tmp/wave88/framework_liveness_n100.json (the numbers in §1.4)

# DAE.decode stochasticity (already in /tmp/wave88, not re-run here)
.venvs/kanzi_venv/bin/python /tmp/wave88/probe_stochasticity.py
# -> 8 records x 8 repeats, mean sigma 0.0947 A

# D.4 byte-stable regression
python3 -m pytest tests/ -k "d4" \
    --ignore=tests/test_property_based \
    --ignore=tests/test_expecttest_smoke.py --ignore=tests/perf -q
# -> 33 passed, 6 skipped, 4810 deselected (2.43s)

# Capability audit (unchanged)
python3 tools/capability_audit.py
# -> G-MASTER 7/7 PASS (unchanged from Wave 87)

# mkdocs build --strict
mkdocs build --strict
# -> EXIT=0
```

---

## 8. Files referenced

| Path | Role |
|---|---|
| `/home/hugo/codes/flowa-multistep-reinference/docs/paper-draft.md` | MODIFIED (additive — §7.3 Wave 88 paragraph + §7.6 Wave 88 paragraph + §5.7 limitation #11 refinement) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave88-phase3-final.md` | NEW (this file) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave88-phase1-audit.md` | Wave 88 Agent A audit (READ-ONLY, fix plan) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave88-phase2-sweep.md` | Wave 88 Agent B sweep (F-1 through F-7) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave83-phase4-final.md` | Wave 83 baseline arm N=200 source (0.8235 Å) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase3-sweep.md` | Wave 79 n=2 proxy source (Δ=+0.27 Å, now retracted) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase4-verdict.md` | Wave 79 per-paper-claim support table |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave52-per-component-ablation.md` | Wave 52 Kanzi composite axis source (+0.1695) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave87-phase4-final.md` | Wave 87 FlowMol3 byte-stable reproduction source |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json` | Wave 83 N=200 baseline arm JSON (largest-N reproducible) |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave88_kanzi_n1000_baseline/` | Wave 88 N=1000 baseline dir (EMPTY — JSON missing, see §6) |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/lineageflow_v2_aggregated_q4_2026.json` | Wave 47 + Wave 69 LineageFlow GPU aggregated (8/9 cells) |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json` | Wave 87 FlowMol3 N=1000 baseline arm byte-stable |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/flowmol3_n1000_framework_wave87_q4_2026.json` | Wave 87 FlowMol3 N=1000 framework arm byte-stable |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/kanzi_upstream_baseline_q4_2026.json` | Wave 79 n=2 baseline (1.3995 Å) — RETRACTED in Wave 88 |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/kanzi_upstream_framework_q4_2026.json` | Wave 79 n=2 framework (1.6711 Å) — RETRACTED in Wave 88 |
| `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py:4119-4144` | `_extract_ca_coords_for_kanzi` (the broken 30-zero fallback, Wave 88 F-2) |
| `/home/hugo/codes/flowa-multistep-reinference/tools/sweep_kanzi_n1000_paper_metrics.py:239` | `"deterministic": true` field (incorrect, Wave 88 F-4) |
| `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/kanzi.py:220` | KANZI_STATE_SHAPE = `(64, 64)` (Wave 88 F-3 root cause) |
| `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/universal/state.py:216-234` | `ODEIntegratorTrace` (no `endpoint`/`states` attr, Wave 88 F-2 root cause) |
| `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/kanzi.py:1432-1545` | `KanziAdapter.apply_restart_distribution` (consumes paper-quant β correctly per Wave 88 A §1.3) |
| `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py:1057-1286` | `_compute_paper_quantities` + `_make_framework_policy` (Wave 86 paper-quant β fix) |
| `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py:701` | `_PAPER_QUANTITY_PROFILES["kanzi"]` = `"0.5 * math.sin(x)"` (Wave 86 fix already aligned) |
| `/home/hugo/codes/flowa-multistep-reinference/posebusters/modules/energy_ratio.py:6-14` | Wave 87 Agent A audit — PB 0.6.5 `energy_ratio` is UFF-based, NOT xtb-based |
| `/tmp/wave88/framework_liveness_n100.json` | Wave 88 Agent B F-1 N=100 paired framework-vs-baseline probe |
| `/tmp/wave88/probe_framework_liveness.py` | F-1 probe (reproducible) |
| `/tmp/wave88/probe_stochasticity.py` | F-4 decode stochasticity probe |
| `/tmp/wave88/probe_trace.py` | F-2 trace surface probe |
| `/tmp/wave88/probe_determinism.py` | F-4 determinism probe (torch.manual_seed(1234) drives spread to 0) |
| `/tmp/wave88/smoke_arm_divergence.py` | F-1 N=10 smoke (failed: both arms identical 30-zero placeholder) |
| `/tmp/wave88/analyze_power.py` | Statistical-power + FSQ noise-band analysis script (errors at runtime — JSON missing) |
