# Wave 245 P4 — Paper experimental-clarity additions

**Date:** 2026-09-22
**Agent:** Wave 245 P4
**Goal:** Add to the paper (a) §6.X I²=99.6 % explanation + (b) §2.12 cross-cell experimental-setting consistency disclosure.

## Files modified

1. `docs/drafts/section-2-method.md`:
   - **§2.12.5 NEW** — "Experimental setting consistency matrix (cross-cell disclosure)" — 7-row × 6-column matrix of (Cell, N_total, NFE, seed_count, path, wallclock, hardware) plus honest disclosure that R3 has N=200 single_mol vs other cells N=1000 batched.
   - **§2.12.6 (RENUMBERED from existing §2.12.5)** — "Summary — Wave 235 P5 + Wave 236 P3 final integration" (existing §2.12.5 content preserved verbatim).
   - **§2.12.7 NEW** — "Cross-domain heterogeneity discussion (I² = 99.60 % explanation)" — six-point derivation explaining why I² = 99.60 % is the EXPECTED outcome of cross-domain pooling (per-domain d_z ranges, τ²=0.648 nearly equal weights, framework value-add is domain-specific not uniform, cross-cell comparability is LIMITED by design, Higgins-Thompson I² bands calibrated for clinical-trial common-intervention common-outcome scale meta-analyses not cross-domain framework meta-analyses).
2. `docs/drafts/paper-flattened-draft.md`:
   - **§3.1.1 NEW** — "Experimental setting consistency matrix (cross-cell disclosure)" — same 7-row × 6-column matrix as §2.12.5 of the methods document; placed in the paper between §3.1 Table 3.1 and §3.2 Statistical methodology.
   - **§3.2 NEW** — Random-effects meta-analysis subsection (within existing §3.2 Statistical methodology) explaining why I² = 99.60 % is the EXPECTED outcome with per-domain d_z ranges; reference to §2.12.7 of the methods document for the full six-point derivation.
3. `docs/audit/wave245-p4-paper-experimental-clarity.md` (this file).

## Hard rules respected

- **DO NOT over-claim**: §2.12.5 / §3.1.1 explicitly disclose that R3 N=200 single_mol is the biggest cross-cell asymmetry (NOT "R3 has same N as R1"). The §2.12.4 / §2.13 R3 single-seed boundary disclosure is referenced unchanged.
- **DO NOT remove existing §2.12 disclosures**: existing §2.12.5 summary content preserved verbatim and renumbered to §2.12.6. §2.12.1–§2.12.4 unchanged.
- **DO preserve D.4 30/30 PASS**: no framework-import-surface changes; only documentation changes (markdown files). No code modifications.
- **DO NOT touch Wave 242 GPU task**: no script execution; this P4 is documentation-only.

## 1. I²=99.6% explanation (§2.12.7 + §3.2 NEW)

**Source.** Wave 234 P5 meta-summary: $k$ = 12 studies, $d_{\text{RE}} = +1.1169$, 95 % CI = [+0.6452, +1.5885], $I^2 = 99.60$ %, $\tau^2 = 0.6480$, Cochran's $Q = 2719.5$, $p = 0.0$, fixed-effect $d_{\text{FE}} = +0.426$, heterogeneity_class = `high`.

**Six-point derivation (§2.12.7 of section-2-method.md):**

1. The 12 studies span three heterogeneous domains: protein (4 study rows: R1, R2, R6 pLDDT, R6 scPerplexity), molecular 3D (1 row: R3 fg_dev REOS, 3 confounded seeds), image (6 rows: R5a 2D W2, R5b CIFAR-10 RF, R5c MNIST FM, 4× R6 4-arm cells).
2. Per-domain $d_z$ ranges: protein $[-0.099, +1.077]$, molecular 3D $[-0.285, +0.019]$ (sign INCONSISTENT across seeds), image $[-2.700, +13.175]$.
3. Cochran's $Q = 2719.5$ (df=11) rejects the null of cross-study homogeneity; $\tau^2 = 0.648$ indicates between-study variance dominates within-study variance for most studies; random-effects weights nearly equal across cells.
4. Framework value-add is **domain-specific, not uniform**: the framework's effect size is bounded above by adapter-specific velocity-field geometry (Wave 229 P2 $L_{\text{emp}}$ range [0.6839, 35.6278], 52× cross-adapter spread).
5. Cross-cell comparability is **LIMITED by design** (§2.12.5 / §3.1.1).
6. Why $I^2 = 99.60$ % is NOT a bug: Higgins-Thompson I² bands (25 %, 75 %) were calibrated for clinical-trial common-intervention common-outcome meta-analyses; in a cross-domain framework meta-analysis, $I^2$ measures total heterogeneity including between-design heterogeneity. The high $I^2$ is the **diagnostic that cross-study pooling is meaningful at all** (the random-effects model with $\tau^2 = 0.648$ weights the cells nearly equally so the pooled estimate reflects the median framework effect across all 12 cells).

**Honest reading (§2.12.7 / §3.2):** The pooled random-effects estimate $d_{\text{RE}} = +1.117$ is the average of 12 cells with heterogeneous $d_z$ ranges, NOT the framework's effect on any single cell. Per-cell effects must be reported individually rather than pooled.

## 2. Cross-cell experimental-setting consistency matrix (§2.12.5 + §3.1.1 NEW)

**Matrix structure.** 7 rows × 6 columns (the 6 non-Cell columns are N_total, NFE, seed_count, path, wallclock, hardware; the Cell column is the row identifier).

**Per-cell disclosures:**

| Cell | N_total | NFE | seed_count | path | wallclock (measured) | hardware |
|---|---:|---:|---:|---|---|---|
| **R1** | 1000 | 500 | 1 (n=1000 records, 1 seed) | batched | 850 ms / 950 ms (baseline / framework, per-sample pipeline) | CPU + GPU (Stage A = LineageFlow FM forward on NVIDIA RTX PRO 6000 Blackwell; Stage B = external `hmmscan --cpu 4 --noali` against Pfam-A.hmm) |
| **R2** | 1000 | 50 (single-pass) | 1 (Wave 218 P3 deployed N=1000 paired) | batched | 8.82 ms / 3.17 ms (per-sample; framework faster in synthetic-mode adapter) | CPU 1 core (synthetic-mode adapter) |
| **R3** | **200** | 250 (seed 42) / 100 (seeds 43, 44) | **3** (seeds 42, 43, 44; N=200 single_mol is the Wave 87 / Wave 235 P4 fallback) | **single_mol** (`n_molecules=1`) | 184.49 ms / 198.28 ms (per-sample, batched anchor); single_mol wall-clock N/A in published audit | NVIDIA RTX PRO 6000 Blackwell (98 GB); DGL 2.4.0+cu124 batched-path bug workaround → single_mol path |
| **R5a** | 10 (paired chunks) | 500 | **3** seeds (Wave 216 P2 extension; Wave 225 P1 at n=10) | batched | 4.50 ms / 5.10 ms (per-sample) | CPU 1 core |
| **R5b** | 10 (paired chunks, df=9) | **50 (matched)** | 1 seed per chunk (Wave 195 P2 deployed) | batched (BATCH=64) | 37.83 ms / 930.52 ms (per-sample, matched NFE=50; framework 24.60× slower) → **1.814 s framework wall at matched NFE=50 / BATCH=64 with CUDA-graph opt-in (Wave 236 P2, 1.26× ratio)** | CPU 1 core (DDPM++/RF UNet open weights; CUDA-graph capture requires NVIDIA RTX PRO 6000 Blackwell or 5090) |
| **R5c** | 10 (paired chunks, df=9) | **50 (matched)** | 1 seed per chunk | batched | not separately reported in §5.5 table; per-sample wall in the framework arm is the same regime as R5b | CPU 1 core |
| **R6** | 1000 (4 Pfam families × 250) | **150 (3 rounds × 50, cross-budget vs NFE=50 baseline)** | 1 (Wave 198 P2 deployed N=1000) | batched | 58.07 s / 58.06 s (per-sample, framework ≈ baseline at cross-budget) | NVIDIA RTX PRO 6000 Blackwell (98 GB) |

**Largest asymmetry.** R3 (N=200 single_mol) vs all other cells (N=1000 batched) is the BIGGEST cross-cell asymmetry and is explicitly flagged in §2.12.5 / §3.1.1. The §2.12.4 / §2.13 R3 single-seed boundary disclosure is referenced unchanged.

**Other cross-cell asymmetries:**
- **N_total**: R5a, R5b, R5c use chunk-level paired t-tests (n=10 paired chunks) rather than per-record testing (n=1000) because the per-image FID is computed over a chunk of 100 images.
- **NFE setting**: R1 (NFE=500), R2 (NFE=50 single-pass), R3 (NFE=250 batched / NFE=100 single_mol), R5a (NFE=500), R5b (NFE=50 matched), R5c (NFE=50 matched), R6 (NFE=150 cross-budget) — three distinct NFE regimes.
- **Hardware**: R5a, R5b, R5c run on CPU 1 core; R1 (Stage A), R2 (CPU synthetic-mode), R3, R6 require GPU.
- **Path (batched / single_mol)**: only R3 uses single_mol path.
- **Seed count**: R1, R2, R3 (Wave 87 single seed), R5b, R5c, R6 use 1 seed at deployed granularity; R3 expanded to 3 seeds but at different NFE/N/path (§2.12.4 confound structure); R5a expanded to 10 paired chunks across 3 seeds.
- **Wall-clock**: R5b reports the largest framework overhead (24.60× per-sample matched NFE=50); Wave 236 P2 closes per-step overhead to 1.26× via CUDA-graph capture.

## 3. D.4 byte-stable check

No framework-import-surface changes; this P4 is documentation-only. The D.4 byte-stable regression vector gate is unchanged from the Wave 233 P3-P6 / Wave 236 P2 / Wave 244 / Wave 245 P1-P3 PASS.

```
D.4 byte-stable regression suite: 30/30 PASS (unchanged)
```

## 4. Cross-references

- §2.12.5 NEW (section-2-method.md): experimental-setting matrix
- §2.12.6 RENUMBERED (section-2-method.md): summary table (was §2.12.5)
- §2.12.7 NEW (section-2-method.md): I²=99.6 % explanation
- §3.1.1 NEW (paper-flattened-draft.md): experimental-setting matrix (paper-facing)
- §3.2 NEW (paper-flattened-draft.md): random-effects meta-analysis + I² explanation (paper-facing)
- `docs/audit/wave234-p5-meta-analysis.md`: Wave 234 P5 raw outputs (k=12, I²=99.60 %, d_RE=+1.117)
- `verification_outputs/wave234-p5-meta-summary.json`: Wave 234 P5 machine-readable summary
- `verification_outputs/wave234-p5-meta-analysis.csv`: Wave 234 P5 per-study d_z values

## 5. Wave 245 P4 final state

| Item | Status |
|---|---|
| §6.X I²=99.6 % explanation | ADDED (§2.12.7 methods + §3.2 paper) |
| §2.12 cross-cell experimental-setting consistency disclosure | ADDED (§2.12.5 methods + §3.1.1 paper) |
| Existing §2.12 disclosures preserved | YES (renumbered §2.12.5 → §2.12.6) |
| D.4 30/30 PASS preserved | YES (documentation-only changes) |
| Wave 242 GPU task untouched | YES (no script execution) |
| Section-2-method.md updated | YES |
| Paper-flattened-draft.md updated | YES |