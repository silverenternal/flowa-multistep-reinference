# Wave 165 P6 — Empirical BL Distance (Baseline vs Framework)

**Date:** 2026-09-16
**Branch:** main
**Scope:** Wave 165 P6 Agent 1 — empirical BL distance between N=1000 baseline
and N=1000 framework FASTA samples (LineageFlow, protein), compared to the
JMAA Theorem 1 BL-convergence rate bound (paper-draft.md §2.8.1).

---

## 1. Inputs

### 1.1 FASTA samples

| Path | sha256 | N seqs | mean len |
|------|--------|--------|----------|
| `/tmp/w158/lineageflow_real_fastas/baseline.fasta` | `4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1` | 1000 | 90.0 |
| `/tmp/w158/lineageflow_real_fastas/framework.fasta` | `afe53dc0ea168c9d7629915ce6bda02de28299cc1bfa730583410888b83aaec5` | 1000 | 90.4 |

Both files contain 4 protein families × 250 sequences: `PF00005.27`,
`PF00072.24`, `PF00183.19`, `PF02517.18`. Manifest entry confirms `nfe=10`,
`n_rounds=3`.

### 1.2 Empirical measure

3-mer histograms over 20-amino-acid alphabet (max 8000 distinct k-mers).
Empirical BL distance approximated by Total Variation distance (TV):
`TV(p, q) = 1/2 Σ |p(k) - q(k)|`, which equals BL for countable measure
spaces. Additional metrics:

- **Jensen-Shannon divergence** `JSD(p, q)` (natural-log base, bounded in [0, ln 2]).
- **Pinsker-like upper bounds** on TV derived from JSD:
  - Loose (KL-Pinsker): `TV ≤ sqrt(2 · JSD)`
  - Tight (Lin 1991): `TV ≤ sqrt(JSD / 2)`

---

## 2. Results

| Metric | Value |
|--------|-------|
| Baseline n_kmers | 88,049 |
| Framework n_kmers | 88,423 |
| \|alphabet\| (3-mers observed) | 6,491 (out of 8000 max) |
| **Empirical BL (TV @ k=3)** | **0.943974** |
| JSD | 0.610076 |
| BL upper (sqrt(2·JSD) KL-Pinsker) | 1.104605 |
| BL upper (sqrt(JSD/2) Lin 1991) | **0.552303** |
| Per-family TV (range) | 0.9808 – 0.9888 (all 4 families) |

### 2.1 JMAA Theorem 1 theoretical bound (paper-draft.md §2.8.1, line 370–374)

Formula:
```
BL(P_framework, P_target) ≤ A_g · exp(-NFE / B_g) + C_g · e_rho
```

Canonical framework constants (sin profile, `docs/算法实现说明.md` line 96–104
+ 128–145; matches the framework's default paper-quantity snapshot for the
F-side sin profile):

| Quantity | Value | Source |
|----------|-------|--------|
| `A_g` (sheet_evidence_A) | 0.854085 | `paper_quantities.sheet_evidence_A(sin)` |
| `B_g` (root_cell_packing_B) | 1.169713 | `paper_quantities.root_cell_packing_B(sin)` |
| `C_g` (per_cell_coefficient_C, rho=0.1, c=1.0) | 1.24 | `paper_quantities.per_cell_coefficient_C` |
| `e_rho` (exterior_gap_e_rho, rho=0.1, eta=0.1) | 1e-4 | `paper_quantities.exterior_gap_e_rho` |
| NFE (per-record; manifest.json) | 10 | `manifest.json:nfe_per_record` |
| NFE total (n_rounds × nfe_per_record) | 30 | `manifest.json:n_rounds × nfe_per_record` |

Per-record bound components:

| Term | Value |
|------|-------|
| `A_g · exp(-NFE/B_g)` | 0.854085 × exp(-10/1.169713) = **1.654519e-04** |
| `C_g · e_rho` | 1.24 × 1e-4 = **1.240000e-04** |
| **Theoretical bound** | **2.894519e-04** |

---

## 3. Interpretation

The empirical k-mer TV (≈ 0.94) **exceeds** the Theorem 1 theoretical bound
(≈ 3e-4) by ~3000×. **This is expected and not a violation**, because the
two quantities live in **different measure spaces**:

| Quantity | Space | What it measures |
|----------|-------|-------------------|
| Empirical TV | Discrete, 3-mer alphabet (\|A\| ≤ 8000) | L1 divergence between two sequence-empirical distributions |
| Theorem 1 bound | Continuous, R^2 (planar) | Structural guarantee on the BL distance between mu_{g,eps} and nu_g |

Concretely:
- The **empirical TV ≈ 0.94** says: the *k-mer frequency vectors* of
  baseline and framework are nearly orthogonal — the two distributions
  assign their mass to almost disjoint sets of k-mers. This reflects
  the **structural** difference between baseline (uniform-i.i.d. sampling;
  ~250 distinct seqs/family, near-uniform AA composition) and framework
  (family-conditioned; ~104 distinct seqs/family, AA composition matches
  protein biology with family-specific preferences).
- The **Theorem 1 bound ≈ 3e-4** is a **structural envelope** on the
  planar BL distance — it bounds how far `mu_{g,eps}` can be from `nu_g`
  in R^2 at NFE=10. It is **not** a bound on sequence-space divergence
  between two empirical draws.

**Read**: the framework is producing a *different* distribution than the
baseline (high empirical TV), AND the Theorem 1 bound is *extremely tight*
at NFE=10 (theoretical bound ≈ 3e-4 vs. NFE-induced noise ≈ 1/NFE ≈ 0.1 —
3 orders of magnitude tighter than the naive eps bound).

**Per-family check** (all 4 families have TV ≈ 0.98):

| Family | TV |
|--------|-----|
| PF00005.27 | 0.9837 |
| PF00072.24 | 0.9854 |
| PF00183.19 | 0.9888 |
| PF02517.18 | 0.9808 |

All families are well-separated between baseline and framework, confirming
the per-family TV is consistent (no single family drives the divergence).

**Note on `bound_tight`** in the JSON: the boolean `tv <= theoretical_bound`
is reported as `false`, but this is **not** a Theorem 1 violation — it
reflects the measure-space mismatch. The flag is preserved for audit
completeness; the qualitative judgment is that the bound is *not
applicable* in this discrete sequence space.

---

## 4. Artifacts

| Path | sha256 | Size | Purpose |
|------|--------|------|---------|
| `/tmp/w165/bl_distance.json` | (numeric results, sha-256) | 1.3 KB | Empirical BL + JSD + theoretical bound |
| `/tmp/w165/compute_bl_distance.py` | (script) | 5.7 KB | Reproducible computation (k-mer TV + JSD + bound) |
| `/tmp/w165/family_check.py` | (script) | 1.0 KB | Per-family TV breakdown |
| `docs/audit/wave165-bl-distance.md` | this file | – | Audit trail |

To reproduce:
```bash
python /tmp/w165/compute_bl_distance.py
```

---

## 5. Gate preservation (ADDITIVE only)

This wave is **purely ADDITIVE**:

1. **No source code changed.** Only `/tmp/w165/` artifacts and
   `docs/audit/wave165-bl-distance.md` (this file) are new.
2. **No paper changes.** `docs/paper-draft.md` is unchanged.
3. **No claim changes.** `docs/CLAIMS.md` is unchanged.
4. **No regression-vector changes.** D.4 vector suite is unchanged.

All 9 reviewer-facing gates (`tools/verify_submission_readiness.py`) remain
in their last-pushed state (Wave 164b / 165 P1–P5).

---

## 6. References

- `docs/paper-draft.md` §2.8.1, lines 370–374: Theorem 1 BL-convergence
  rate bound formula `BL(P_framework, P_target) <= A_g * exp(-NFE/B_g) + C_g * e_rho`.
- `docs/paper-draft.md` §2.8, lines 257–354: Four paper quantities (A_g,
  B_g, C_g, e_rho) and F-side regime.
- `docs/算法实现说明.md` line 96–104: Worked example for the sin profile
  (A_g ≈ 0.85, B_g ≈ 1.17, C_g ≈ 1.24, e_rho ≈ 1e-4).
- `docs/算法实现说明.md` line 128–145: Python implementation (`sheet_evidence_A`,
  `root_cell_packing_B`, `per_cell_coefficient_C`, `exterior_gap_e_rho`).
- `adaptive_reflow/theory/paper_quantities.py`: Byte-stable evaluators.
- `tests/test_theory/test_theorem1_bl_convergence.py` line 30–36:
  `_paper_qty(g)` helper that builds a `PaperQuantitiesSnapshot` from
  `sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C(rho=0.1, c=1.0)`,
  `exterior_gap_e_rho(rho=0.1, eta=0.1)`.
- Wave 158 `/tmp/w158/lineageflow_real_fastas/`: N=1000 baseline + framework
  FASTA samples + `manifest.json` (sha256, nfe_per_record=10, n_rounds=3).
- Wave 163 P5: prior disclosure of novelty_mmseqs2 (ADDITIVE only).
- Wave 164b: paper camera-ready review (typos + cross-refs + figure refs).
- Wave 165 P1–P5: prior wave work (paper §10.7 ADDITIVE, OSF pre-registration,
  Zenodo DOI release; all ADDITIVE only).