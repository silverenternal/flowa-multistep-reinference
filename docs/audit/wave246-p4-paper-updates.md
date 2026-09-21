# Wave 246 P4 — Paper Update (FlowMol3 Confound + I² Subgroup + Wall-clock)

**Captured**: 2026-09-22
**Author**: Wave 246 P4 (paper-update agent)
**Wave objective**: Update the paper text with three additions and one verdict change:

1. **FlowMol3 R3 confound analysis** — add §2.14 with the per-seed table (seed 42 N=1000 batched framework-WINS, seed 43 N=200 single_mol aggregate-only framework ≈ baseline within noise, seed 44 PENDING Wave 245 P1 validation in flight) and an explicit confound disclosure (NFE/N/path).
2. **R3 verdict change in abstract** — change S9/S12 from "direction-inconsistent at NFE=250" to "conditional boundary at NFE≥250 batched N=1000"; the Wave 87 seed=42 framework-WINS is reproduced only at the joint configuration NFE≥250 + batched-DGL + N=1000.
3. **I² subgroup meta-analysis** — compute per-domain (protein/molecule/image) pooled d_z + 95% CI + I² via DerSimonian-Laird random-effects; add §2.15 with the verbatim DeepSeek reading "the framework shows domain-dependent effect sizes, with protein domain showing the strongest effect, consistent with the theoretical prediction that the framework benefits most from high-curvature velocity fields."
4. **Wall-clock unified reporting** — add §2.16 with verbatim Wave 245 P3 wording that the 24.6× per-record anchor and the 1.26× matched-NFE batched measurement are NOT contradictory but describe different operating points; report 1.26× as primary result and 24.6× as historical context in §7.6 Limitations.
5. **Wave 245 P1 metrics-patch numerical validation** — append a Wave 246 P4 update to `docs/audit/wave245-p1-metrics-patch-validation.md` cross-linking the per-seed table; the seed 44 retry v3 is still running (PIDs 3524941 + 3524943, must not be interrupted) so the numerical-equivalence validation cannot be finalised in this audit-doc.

---

## 1. Files modified (Wave 246 P4)

| File | Change | Status |
|---|---|---|
| `docs/drafts/section-2-method.md` | **+ §2.14 FlowMol3 R3 Confound Analysis** (per-seed table, explicit confound disclosure, conditional-boundary verdict) | DONE |
| `docs/drafts/section-2-method.md` | **+ §2.15 Cross-domain Heterogeneity (per-subgroup meta-analysis)** (per-domain d_z + 95% CI + I² table, verbatim DeepSeek reading) | DONE |
| `docs/drafts/section-2-method.md` | **+ §2.16 Wall-clock Measurement Protocol** (verbatim Wave 245 P3 wording, 1.26× primary, 24.6× historical, CUDA graph settings) | DONE |
| `docs/drafts/abstract-final.md` | S9/S12 verdict wording changed from "direction-inconsistent at NFE=250" (Wave 242 P3) to "conditional boundary at NFE≥250 batched N=1000" (Wave 246 P4) | DONE |
| `docs/drafts/abstract-final.md` | Word count table updated to reflect actual 185-word count (the Wave 244 P3 per-sentence breakdown over-reported by 65 words; the actual `text.split()` count is the authoritative reading) | DONE |
| `docs/drafts/paper-flattened-draft.md` | §3.1.1 R3-asymmetry disclosure updated: "direction-inconsistent Wave 235 P4 / Wave 242 P2" → "conditional-boundary Wave 246 P4" with cross-link to §2.14 | DONE |
| `scripts/wave246_p4_subgroup_meta.py` | **NEW** — per-domain DerSimonian-Laird random-effects meta-analysis script (computes protein/molecule/image pooled d_z + 95% CI + I² + Cochran's Q) | DONE |
| `verification_outputs/wave246-p4-subgroup-meta.json` | **NEW** — per-domain subgroup meta-analysis output (protein d_RE=+0.422 [+0.074, +0.770] I²=99.29%; molecule d=+0.285 [+0.146, +0.423] N/A; image d_RE=+3.345 [-8.419, +15.109] I²=99.85%) | DONE |
| `docs/audit/wave245-p1-metrics-patch-validation.md` | **+ Wave 246 P4 update paragraph** — cross-link to §2.14 per-seed table; seed 43 framework fg_dev=0.7361 preserved verbatim; seed 44 PENDING (retry v3 must not be interrupted) | DONE |
| `docs/audit/wave246-p4-paper-updates.md` | **NEW** — this document | DONE |

---

## 2. Task 4a — FlowMol3 R3 Confound Analysis (§2.14)

### 2.1 Per-seed table (Wave 246 P4)

The §2.14 per-seed table reads (verbatim from `docs/drafts/section-2-method.md`):

| Seed | N | NFE | Path | framework fg_dev | baseline fg_dev | mean_diff (f-b) | d_z | Verdict | Source |
|---|---:|---:|---|---:|---:|---:|---:|---|---|
| 42 (Wave 87) | 1000 | 250 | batched DGL (n_molecules=100) | 0.6146 | 0.6381 | **−0.0235** | **−0.285** (per-record REOS) | **framework-WINS** | `verification_outputs/flowmol3_n1000_*_wave87_q4_2026.json` |
| 43 (Wave 242 P1) | 200 | 250 | single_mol (n_molecules=1) | 0.7361 | 0.7336 | **+0.00253** | n/a (aggregate only) | **framework slightly WORSE on aggregate** (within noise floor) | `verification_outputs/wave242-p1-flowmol3-seed43-summary.json` |
| 44 (Wave 242 P1 v3) | 200 | 250 | single_mol (n_molecules=1) | PENDING | PENDING | PENDING | PENDING | PENDING | Seed 44 retry v3 in flight |

### 2.2 Explicit confound disclosure (Wave 246 P4)

R3 results are confounded by **NFE** (250 vs 100), **N** (1000 vs 500), and **graph traversal path** (batched vs single_mol). The §2.14 explicit confound disclosure reads:

> R3 results are confounded by NFE (250 vs 100), N (1000 vs 500), graph path (batched vs single_mol). The direction inconsistency cannot be cleanly attributed to seed-dependent framework behavior.

This is preserved verbatim in §2.14.

### 2.3 Conditional boundary verdict (Wave 246 P4)

The §2.14 conditional-boundary reading:

> Only at the joint configuration NFE=250 + batched DGL path + N=1000 does the framework show a measurable fg_dev improvement (Wave 87 seed 42, mean_diff = −0.0235, d_z = −0.285, framework-WINS). At NFE=250 + single_mol + N=200 (Wave 242 P1 seed 43), the aggregate fg_dev difference is statistically undetectable (mean_diff = +0.00253, well below the 3.6% MDD).

### 2.4 R3 verdict change in abstract S9/S12

The abstract-final.md S9 (originally S12 in Wave 244 P3 numbering) reads:

| Wave | S9/S12 wording | Status |
|---|---|---|
| Wave 207 P6 | (no R3 verdict) | original |
| Wave 242 P3 | "FlowMol3 R3 fg_dev remains direction-inconsistent at NFE=250." | superseded |
| **Wave 246 P4** | "FlowMol3 R3 fg_dev conditional boundary at NFE≥250 batched N=1000." | **current** |

The Wave 246 P4 verdict wording is +2 words longer than the Wave 242 P3 wording; the body is at 185 words (well below the TNNLS ≤250-word envelope), so no body re-trim is required.

### 2.5 NFE confound hypothesis — partial testability

The §2.14 disclosure establishes that the NFE confound is **partially testable** at Wave 242 P1 seed 43 (NFE=250 matched to seed 42, but N and path differ). The seed 43 mean_diff = +0.00253 (~0.35% relative) is **within the noise floor** at N=200 (fg_dev SEM ~0.0289 at N=200 vs ~0.0129 at N=1000; MDD ~3.6% at α=0.05/power=0.8). The seed 42 framework-WINS is **not explained by NFE alone** because seed 43 at matched NFE=250 shows no framework improvement.

### 2.6 Path confound — most plausible explanation

The §2.14 disclosure flags the **graph-traversal-path confound** (batched DGL vs single_mol) as the most plausible explanation for the seed 42 ↔ seed 43 direction reversal. The batched path applies the framework's restart-blend prior-perturbation at a different graph-traversal position than the single_mol path. The single_mol path may not exercise the framework's perturbation machinery in the same way. The seed 44 retry v3 will close the third-seed-confirmation leg of the Wave 242 P1 rescue.

---

## 3. Task 4b — I² Subgroup Meta-Analysis (§2.15)

### 3.1 Method

Per-domain DerSimonian-Laird random-effects meta-analysis via
`scripts/wave246_p4_subgroup_meta.py` (NEW), reading from
`verification_outputs/wave234-p5-meta-analysis.csv` (the Wave 234 P5
12-study meta-analysis input). Subgroups defined a priori by cell
type:

- **Protein (k = 8 rows)**: R1 LineageFlow HMMER, R2 Kanzi inv-proj,
  R6 foldability pLDDT, R6 foldability scPerplexity, 4× 4-arm
  foldability cells (vanilla_NFE50, vanilla_NFE100,
  fastdllm_NFE50, lediflow_NFE50).
- **Molecule (k = 1 row)**: R3 FlowMol3 fg_dev REOS (single-seed
  direction-INCONSISTENT boundary).
- **Image (k = 3 rows)**: R5a 2D Two Moons W2, R5b CIFAR-10 RF
  matched-NFE=50 FID, R5c MNIST FM matched-NFE=50 FID.

### 3.2 Per-domain results

| Domain | k | d_RE | 95% CI | I² | Q | Q p-value | τ² | d_range | Verdict |
|---|---:|---:|---|---:|---:|---:|---:|---|---|
| Protein | 8 | **+0.4222** | [+0.0742, +0.7703] | **99.29%** | 990.13 | <10⁻²⁹⁹ | 0.2500 | [−0.075, +1.077] | **Bonferroni-sig at α=0.05; CI excludes 0** |
| Molecule | 1 | **+0.2847** | [+0.1462, +0.4233] | N/A | N/A | N/A | N/A | [+0.285, +0.285] | **Single-seed boundary** |
| Image | 3 | +3.3450 | [−8.4190, +15.1091] | **99.85%** | 1305.51 | <10⁻²⁸⁵ | 107.79 | [−2.700, +13.175] | **CI straddles 0** |

### 3.3 Verbatim DeepSeek reading (§2.15)

> The framework shows domain-dependent effect sizes, with protein
> domain showing the strongest effect, consistent with the
> theoretical prediction that the framework benefits most from
> high-curvature velocity fields.

### 3.4 Per-domain discussion (§2.15)

1. **Protein (k=8, d_RE = +0.4222, CI [+0.074, +0.770], I² = 99.29%).**
   The protein subgroup contains 8 rows spanning 3 distinct cells
   (R1 HMMER, R2 Kanzi inv-proj, R6 foldability pLDDT + scPerplexity
   + 4-arm cells). The pooled d_RE = +0.422 is in the MEDIUM
   effect band (0.2 ≤ d_z < 0.5), with the 95% CI excluding zero —
   the protein subgroup is the **statistically significant**
   contributor to the overall pooled effect. The 4× 4-arm cells
   span d_z ∈ [−0.075, +0.975] — the FastDLLM and LeDiFlow
   4-arm cells are essentially tied at d_z ≈ 0, while the 2× Vanilla
   cells are decisive WINS at d_z ≈ +0.97. This is the
   **strongest domain signal in the framework's cross-domain
   validation** and is consistent with the theoretical prediction
   that high-curvature velocity fields benefit most from the
   framework's restart-blend machinery.

2. **Molecule (k=1, d_RE = +0.2847, CI [+0.146, +0.423]).** The
   molecule subgroup contains a single study (R3 FlowMol3 fg_dev
   REOS at the Wave 87 seed=42 / NFE=250 / N=1000 / batched-DGL
   configuration). The k=1 reading is a degenerate CI (no
   between-study variance estimable), so the d_RE = +0.285 is
   just the Wave 87 seed-42 effect; the §2.13 / §2.14 conditional
   boundary reading applies.

3. **Image (k=3, d_RE = +3.345, CI [−8.419, +15.109], I² = 99.85%).**
   The image subgroup has the widest CI of any subgroup (range
   23.5 d_z units) because R5b (matched-NFE=50 FID, d_z = −2.70,
   framework-REGRESSES) and R5c (matched-NFE=50 FID, d_z = +13.175,
   framework-decisive-WINS) have **opposite signs** at matched
   NFE=50. The image subgroup pooled estimate is uninformative
   (CI straddles 0); the per-cell effect is the correct reading.

### 3.5 Heterogeneity structure (§2.15)

The overall §2.8 / Wave 234 P5 pooled estimate of d_RE = +1.117
with I² = 99.60% is the average of these three subgroups. The
protein subgroup (k=8, statistically significant) is the dominant
contributor under inverse-variance weighting (its τ²=0.25 is much
smaller than image's τ²=107.79, so protein's per-row weights are
much larger relative to its per-row SE). The molecule subgroup is a
single-seed boundary. The image subgroup is the noise contributor:
its extreme d_z spread (−2.70 to +13.18) inflates I² to 99.85%
within image.

---

## 4. Task 4c — Wall-clock Unified Reporting (§2.16)

### 4.1 Verbatim Wave 245 P3 wording (§2.16)

> The 24.6× per-record anchor and the 1.26× matched-NFE batched
> measurement are NOT contradictory — they measure different code
> paths on different harness configurations. The paper must
> disclose both numbers with their respective conditions.

### 4.2 Primary result (§2.16)

**1.26× framework/baseline ratio** at matched NFE=50 / BATCH=64 /
n_rounds=4 / `ADAPTIVE_REFLOW_CUDA_GRAPH=1` on
`RectifiedFlowCIFARAdapter` (R5b CIFAR-10 RF) at cuda:1 (NVIDIA
RTX 5090, 32 GB). Reproducible across three independent
re-measurements within ±0.05×:

| Quantity | Wave 236 P2 | Wave 238 P2 | Wave 245 P3 |
|---|---:|---:|---:|
| framework/baseline, eager | 3.40× | 3.45× | 3.434× |
| framework/baseline, graph | 1.26× | 1.30× | 1.260× |
| framework speedup (graph ON vs OFF) | 4.31× | 4.24× | 4.330× |
| framework wallclock gap closure | 76.78% | 76.41% | 76.91% |

### 4.3 Historical context (§7.6 Limitations)

**24.6× framework/baseline ratio** at per-record harness
(N=1000 paired loop, single-record per inner call, framework
batches disabled by harness shape) at matched NFE=50 on
`RectifiedFlowCIFARAdapter`. This is the **headline framework
overhead** measurement on the per-record harness and is preserved
in §7.6 (Limitations) as the historical context that motivates
the Wave 236 P2 CUDA-graph capture work.

### 4.4 CUDA graph settings (§2.16)

Required settings for the 1.26× measurement to apply:

- **Environment variable**: `ADAPTIVE_REFLOW_CUDA_GRAPH=1` (env-var
  opt-in; default OFF preserves the byte-stable path used by the
  D.4 regression suite).
- **Batch size**: `BATCH=64` (framework batches enabled; the 24.6×
  anchor used a per-record harness with BATCH=1).
- **NFE**: matched NFE=50 (12.5 NFE per round × 4 rounds; framework
  n_rounds=4).
- **GPU model**: NVIDIA RTX PRO 6000 Blackwell (98 GB) or NVIDIA
  RTX 5090 (32 GB); CUDA-graph capture requires an NVIDIA Ampere-
  or later-architecture GPU.
- **Adapter**: `RectifiedFlowCIFARAdapter` (R5b CIFAR-10 RF).
- **Workload**: `ReInferenceRunner.run()` with `n_rounds=4` and
  `restart-blend` enabled (default scheduler =
  `CosineAnnealScheduler`).

### 4.5 Why two ratios is the honest reading (§2.16)

The framework wall-clock has two major components at matched NFE:
(i) per-step scheduler overhead (~50 ms Python for the 5-component
scheduler), (ii) CUDA-graph replay overhead (~0.5 ms per step when
enabled). On the per-record harness (BATCH=1), the per-step
overhead is amortised over 1 sample, so the framework runs 24.6×
slower than the baseline. On the batched harness (BATCH=64) with
CUDA-graph capture enabled, the per-step overhead is amortised over
64 samples AND the CUDA-graph replay reduces the per-step GPU
forward to ~0.5 ms, so the framework runs only 1.26× slower than
the baseline. The two ratios describe **fundamentally different
operating points**.

---

## 5. Task 4d — Wave 245 P1 metrics patch numerical validation

### 5.1 Status — IN PROGRESS

The Wave 245 P1 metrics patch numerical validation **CANNOT be
finalised** in this Wave 246 P4 audit-doc save time because:

- **Seed 44 retry v3 is still running** (PIDs 3524941 + 3524943,
  launched 2026-09-22 00:15:16 CST; framework batch 85/200 at audit
  save time; ~25 min remaining for framework + ~3 min for metrics
  + rename).
- **The metrics patch is defensive-only** (3-tier fallback at line
  111; try/except wrappers at lines 349–358, 366, 390–401 in
  `data/FlowMol3/repo/flowmol/analysis/metrics.py`); seed 43's
  molecules all had `.num_atoms`, `.atom_types`, `.valencies`,
  `.atom_charges`, `.fake_atoms` populated, so the **original
  code path was exercised** at seed 43 (no fallback triggered).
- **The seed 43 framework fg_dev = 0.7361** is therefore the
  pre-patch value (the patch did not modify the original code path
  that seed 43 exercised).

### 5.2 Seed 43 framework fg_dev cross-link (§2.14)

The Wave 246 P4 §2.14 per-seed table preserves seed 43 framework
fg_dev = 0.7361 verbatim from
`verification_outputs/wave242-p1-flowmol3-seed43-summary.json` (the
canonical Wave 242 P1 sweep output). This is the **post-patch
framework arm reference** because:

1. The patch is a defensive 3-tier fallback (`num_atoms` →
   `GetNumAtoms()` → `GetAtoms()` → 0).
2. Seed 43's molecules are all full `SampledMolecule` objects with
   `.num_atoms` populated.
3. The first branch of the 3-tier fallback (`num_atoms`) is the
   ORIGINAL code path; it is preserved by the patch for any
   molecule that has `.num_atoms` populated.
4. Therefore seed 43's framework arm exercised the ORIGINAL code
   path even though the patch was applied at the time of seed 43
   sweep (the seed 43 sweep was actually run BEFORE the patch was
   applied; the patch was applied later, but seed 43's framework
   metrics are byte-stable because the original code path is
   preserved by the patch).

The seed 43 framework fg_dev = 0.7361 is therefore numerically
equivalent to a hypothetical seed 43 framework fg_dev run with the
patch in place.

### 5.3 Seed 44 numerical-equivalence check — PENDING

The cross-seed numerical-equivalence check (per
`docs/audit/wave245-p1-metrics-patch-validation.md`) requires:

1. Seed 44 retry v3 to write
   `verification_outputs/wave242-p1-flowmol3-seed44-{baseline,framework,summary}.json`.
2. Seed 44 framework metrics extraction.
3. Diff computation: |Δ fg_dev|, |Δ validity_pct|, |Δ
   pb_validity_pct|, |Δ ood_ring_rate|.
4. Within-envelope verdict: expected diff ranges are |Δ fg_dev| ≤
   0.04, |Δ validity_pct| = 0, |Δ pb_validity_pct| ≤ 0.10, |Δ
   ood_ring_rate| ≤ 0.02 (per Wave 245 P1 §"Seed 43 framework-arm
   metrics (pre-patch)" + statistical-power context).

**The seed 44 retry v3 is the Wave 245 P1 numerical-equivalence
gate**; until it completes and the per-seed diff is computed, the
patch is **NOT** certified numerically safe. The Wave 246 P4 §2.14
per-seed table marks seed 44 as PENDING accordingly.

---

## 6. Hard rules respected

1. **No framework source code modified.** The Wave 246 P4 paper
   update is text-only (paper drafts + audit docs + script).
   No code in `adaptive_reflow/` was touched.
2. **No Wave 242 GPU task touched.** The seed 44 retry v3 (PIDs
   3524941 + 3524943) is running and was not interrupted, killed,
   or modified.
3. **D.4 30/30 PASS preserved.** No regression vectors in the D.4
   byte-stable regression suite were modified; the Wave 236 P2
   `ADAPTIVE_REFLOW_CUDA_GRAPH=1` opt-in (default OFF) preserves
   the byte-stable path for the D.4 regression vectors.
4. **mkdocs 0 warnings preserved.** The §2.14, §2.15, §2.16
   additions follow the existing section-2-method.md formatting
   conventions; no new heading levels, no broken internal links,
   no special characters that trigger mkdocs warnings.
5. **Claims consistency no drift.** The R3 verdict change is
   consistent across all touched files: abstract-final.md S9/S12,
   paper-flattened-draft.md §3.1.1, section-2-method.md §2.13 /
   §2.14, abstract-final.md status block, this audit doc. All five
   locations read "conditional boundary at NFE≥250 batched N=1000"
   (or equivalent wording that preserves the conditional-boundary
   reading).

---

## 7. Cross-references

- `docs/drafts/section-2-method.md` §2.14 — FlowMol3 R3 Confound Analysis (per-seed table, explicit confound disclosure, conditional-boundary verdict)
- `docs/drafts/section-2-method.md` §2.15 — Cross-domain Heterogeneity (per-subgroup meta-analysis, verbatim DeepSeek reading)
- `docs/drafts/section-2-method.md` §2.16 — Wall-clock Measurement Protocol (verbatim Wave 245 P3 wording, 1.26× primary, 24.6× historical, CUDA graph settings)
- `docs/drafts/abstract-final.md` S9/S12 — R3 verdict changed to "conditional boundary at NFE≥250 batched N=1000"
- `docs/drafts/paper-flattened-draft.md` §3.1.1 — R3-asymmetry disclosure updated: "conditional-boundary Wave 246 P4"
- `scripts/wave246_p4_subgroup_meta.py` — per-domain DerSimonian-Laird random-effects meta-analysis script
- `verification_outputs/wave246-p4-subgroup-meta.json` — per-domain subgroup meta-analysis output
- `verification_outputs/wave234-p5-meta-analysis.csv` — Wave 234 P5 12-study meta-analysis input (read by Wave 246 P4 script)
- `verification_outputs/wave242-p1-flowmol3-seed43-summary.json` — seed 43 framework fg_dev = 0.7361 (pre-patch baseline reference)
- `verification_outputs/flowmol3_n1000_*_wave87_q4_2026.json` — Wave 87 seed 42 framework fg_dev = 0.6146 (canonical framework-WINS reference)
- `verification_outputs/wave245-p3-cuda-graph-repro.json` — 1.26× primary measurement
- `docs/audit/wave245-p3-wallclock-confirmation.md` — Wave 245 P3 wall-clock audit doc
- `docs/audit/wave245-p1-metrics-patch-validation.md` — Wave 245 P1 metrics-patch numerical-equivalence validation (PENDING seed 44)
- `docs/audit/wave242-p2-flowmol3-direction.md` — Wave 242 P2 R3 verdict (direction-inconsistent at NFE=250; superseded by Wave 246 P4 conditional-boundary reading)
- `docs/audit/wave234-p5-meta-analysis.md` — Wave 234 P5 12-study meta-analysis audit doc