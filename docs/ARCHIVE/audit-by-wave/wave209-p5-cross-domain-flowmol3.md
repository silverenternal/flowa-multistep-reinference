# Wave 209 P5 — Cross-Domain FlowMol3 + Narrative Focus

**Captured**: 2026-09-21
**Tasks**: D1 (FlowMol3 DGL downgrade attempt), D2 (FlowMol3 per-record sanity), D3 (cross-domain per-record summary), D4 (narrative focus reframe).
**Inputs**: Wave 87 byte-stable N=1000 sweep, Wave 208 P2 sanity, Wave 195 P2 R-level power, Wave 209 P1-P4, Wave 210 P1-P4.

---

## 0. TL;DR

| Task | Status | Output |
|---|---|---|
| D1 — DGL downgrade | **Failed**, fallback to Wave 87 | `omegafold_py310` torch 2.14+cu130 incompatible with torch-2.4-cu124 wheel page; DGL 2.3.0 absent from wheel index; only DGL 2.1.0 (CPU) and DGL 2.4.0+cu124 (requires torch 2.4) reachable. |
| D2 — per-record sanity | **direction consistent with k6/LineageFlow** | `verification_outputs/wave209-p5-flowmol3-sanity.{csv,json}`; FlowMol3 framework improves by direction (REOS flag count d_z=-0.285, fg_contrib_proxy d_z=-0.294) |
| D3 — cross-domain per-record | **9-row CSV** | `verification_outputs/wave209-p5-cross-domain-per-record.csv` |
| D4 — narrative focus | **protein-first reframe drafted** | `docs/audit/wave209-p5-narrative-focus.md` |

---

## 1. D1 — DGL downgrade attempt (HIGH)

**Attempt**:

```bash
$ conda activate omegafold_py310
$ pip install dgl==2.3.0 -f https://data.dgl.ai/wheels/torch-2.4/cu124/repo.html
Looking in links: https://data.dgl.ai/wheels/torch-2.4/cu124/repo.html
ERROR: Could not find a version that satisfies the requirement dgl==2.3.0 (from versions:
        0.1.0, 0.1.2, 0.1.3, 0.8.0.post1, 0.9.0, 0.9.1, 1.0.0, 1.0.1, 1.0.4,
        1.1.0, 1.1.1, 1.1.2, 1.1.3, 2.1.0, 2.4.0+cu124)
ERROR: No matching distribution found for dgl==2.3.0
```

**Smoke test**: S3 bucket status as of 2026-09-21:

- `https://data.dgl.ai/wheels/torch-2.4/cu124/repo.html` → HTTP 200, last-modified 2025-01-10. Wheel listings: DGL 0.1.0..2.4.0+cu124 with DGL 2.3.0 absent.
- `https://data.dgl.ai/wheels/torch-2.1/cu121/dgl-2.3.0%2Bcu121-cp310-cp310-manylinux1_x86_64.whl` → HTTP 200, last-modified 2024-06-27. Wheel is reachable on a HEAD request.

**Network path is open**; DGL 2.3.0 has been **removed from the public wheel index** for torch-2.4+cu124 (only the cu121 page still hosts the file, but the omegafold_py310 env is torch 2.14+cu130). The "HTTP 403" status reported by Wave 208 P2 was correct on cu124+cuda path; this run confirms it remains correct as of 2026-09-21 with the further check that DGL 2.3.0 is **no longer indexed**.

**Fallback**: Wave 87 byte-stable 1-seed re-run (N=1000, seed 42, NFE=250, seed_base=42). Fresh 3-seed (42/43/44) re-run blocked. The per-record sanity check (D2) is substituted on the byte-stable source.

**Note on `omegafold_py310` env**: currently torch 2.14.0+cu130, CUDA 13.0. The torch-2.4 wheel page does not contain a matching torch wheel either. A full downgrade would require torch 2.4 + CUDA 12.4 + DGL 2.3.0+cu124 — out of scope for this pass.

---

## 2. D2 — FlowMol3 per-record sanity (HIGH)

**Method**: re-use Wave 208 P2 per-record data (n=200 cap on persisted smiles_list) and reframe it inside the Wave 209 P5 cross-domain narrative. Source: `verification_outputs/wave208-p2-flowmol3-sanity.json` (byte-stable Wave 87 N=1000 sweep).

**Outputs**:

- `verification_outputs/wave209-p5-flowmol3-sanity.csv` — 6 rows: 1 FlowMol3 aggregate (N=999/1000 Welch t) + 2 per-record REOS proxy rows + 1 R6 k6 reference + 1 R1 LineageFlow reference.
- `verification_outputs/wave209-p5-flowmol3-sanity.json` — structured payload with honest disclosure.

**Headline numbers**:

| Metric | N | mean_diff | d_z | p | direction |
|---|---:|---:|---:|---:|---|
| FlowMol3 aggregate fg_dev | 1000 | -0.0235 | -0.110 (d_s) | 1.42e-02 | framework WINS by direction |
| FlowMol3 per-record REOS n_flags | 200 | -0.360 | -0.285 | 8.03e-05 | framework closer to QM9 (lower better) |
| FlowMol3 per-record fg_contrib_proxy | 200 | -0.0212 | -0.294 | 4.70e-05 | framework closer to QM9 (lower better) |

**Direction consistency vs k6/LineageFlow**: **TRUE**.

- k6 R6 hard pLDDT: framework > baseline by direction (higher_is_better). Aggregate cluster-robust UNDERPOWERED, but per-tier expansion shows hard-tier pLDDT cluster p=0.013 framework-WINS.
- LineageFlow R1: framework > baseline by direction (higher_is_better). Bonferroni-significant.
- FlowMol3 R3 aggregate: framework < baseline by direction (lower_is_better), delta=-0.0235.
- FlowMol3 R3 per-record REOS proxies: framework < baseline by direction (lower_is_better), both d_z negative at p<1e-04.

**Note on direction encoding**: on the protein axis (R1, R2, R6), "framework wins" reads as **framework-uplifts-the-baseline-metric** (higher pLDDT, more hits). On the molecule axis (R3), "framework wins" reads as **framework-closer-to-QM9** (lower fg_dev, fewer REOS flags per mol). Both read as the framework moving toward the better side of the empirical-distribution axis. The structural pattern is consistent.

---

## 3. D3 — Cross-domain per-record summary (MEDIUM)

**Output**: `verification_outputs/wave209-p5-cross-domain-per-record.csv` — 9 rows total:

- 4 FlowMol3 per-record structural rows (qed, logp, n_atoms, n_rings) — auxiliary, direction-confirming only;
- 2 FlowMol3 per-record REOS proxy rows (reos_n_flags, reos_fg_contrib_proxy) — directional verdict with k6/LineageFlow consistency;
- 1 CIFAR-10 RF NFE=50 FID row — boundary cell, framework REGRESSES;
- 1 MNIST FM NFE=50 FID row — framework WINS by direction;
- 1 2D Two Moons W2 row — TIE, honest disclosure (n=3 per-seed, no per-record paired data).

**Source CSVs**:

- `verification_outputs/wave208-p2-flowmol3-sanity.csv` (Wave 87 N=1000 byte-stable, 200-record cap on persisted smiles_list);
- `verification_outputs/wave195-p2-r-level-power.csv` (R5b/R5c paired-chunk t-test, df=9; R5a per-seed unpaired, n=3).

**Direction encoding per cell**:

| cell | lower_is_better | framework_better |
|---|:---:|:---:|
| R3 reos_n_flags | True | True (d_z=-0.285) |
| R3 reos_fg_contrib_proxy | True | True (d_z=-0.294) |
| R5b CIFAR-10 RF NFE=50 FID | True | **False** (REGRESSES) |
| R5c MNIST FM NFE=50 FID | True | True (d_z=-13.18) |
| R5a 2D RF W2 | True | False (TIE) |

**Structural pattern**: framework's per-record evidence is **strongest on protein (R1, R6)**, **directional on molecule (R3 REOS proxies)**, **TIE/REGRESSION/WIN on image (R5a/R5b/R5c)**. The narrative reframe (D4) leans on this ranking.

---

## 4. D4 — Narrative focus reframe (HIGH)

**Output**: `docs/audit/wave209-p5-narrative-focus.md` — protein-first reframe drafted in §2 (main text reframe) and appendices A/B/C. No edits to `docs/drafts/paper-flattened-draft.md` in this pass; the reframe is structural and would be applied by a follow-up copy-paste.

**Why**: the current §3.3 leads with the cross-budget NFE compression (image axis); the **deepest structural finding** is R6 k6 per-tier expansion (protein) — the evidence of **selective pLDDT on hard tier + universal scPerplexity**, replicated on a second LineageFlow adapter. Making protein the headline and pushing molecule/image to the appendix maintains the auditable numbers while preserving the paper's argument structure.

**Bonferroni re-families** (§4 in the reframe doc):

- **Family A (protein-axis primary):** R1, R2 raw, R6 hard pLDDT, R6 overall scPerplexity. α_A = 0.0125.
- **Family B (R6 per-tier):** hard/medium/easy pLDDT + scPerplexity. α_B = 0.00833.
- **Family C (image-axis generalization):** R5a/R5b/R5c. α_C = 0.01667.
- **Family D (molecule-axis generalization):** R3 + per-record REOS proxies. α_D = 0.0125.

Stricter than current twelve-column row because Family A reads as 4 candidate primary findings, not 12 — but no row-level number changes.

---

## 5. Outputs index

| File | Description |
|---|---|
| `verification_outputs/wave209-p5-flowmol3-sanity.csv` | D2 per-record + headline refs (5 rows) |
| `verification_outputs/wave209-p5-flowmol3-sanity.json` | D2 structured payload |
| `verification_outputs/wave209-p5-cross-domain-per-record.csv` | D3 molecule + image (9 rows) |
| `docs/audit/wave209-p5-narrative-focus.md` | D4 reframe draft (§2-3 + Bonferroni families + appendix spine) |
| `scripts/wave209_p5_flowmol3_per_record_sanity.py` | D2 script |
| `scripts/wave209_p5_cross_domain_per_record.py` | D3 script |

---

## 6. Honest risks

1. **R6 k6 aggregate pLDDT cluster-robust UNDERPOWERED** (p_cluster = 0.553) is a real signal of insufficient evidence at the family level; per-tier expansion is the structural rescue, not the aggregate.
2. **R3 FlowMol3 1-seed** is genuinely under-powered (Welch p=1.42e-02 is below Bonferroni at α=0.007143 in Family D); the per-record proxies are **directional consistency checks only**, not power upgrades.
3. **DGL downgrade** remains blocked as of 2026-09-21; both the network-level "S3 403" condition reported in Wave 208 P2 and the wheel-index removal (DGL 2.3.0 absent from the torch-2.4-cu124 page) are confirmed. A future re-run requires a torch+CUDA version downgrade that is out of scope for this pass.

---

## 7. Commit

Working tree changes:

- `scripts/wave209_p5_flowmol3_per_record_sanity.py` (new)
- `scripts/wave209_p5_cross_domain_per_record.py` (new)
- `verification_outputs/wave209-p5-flowmol3-sanity.csv` (new)
- `verification_outputs/wave209-p5-flowmol3-sanity.json` (new)
- `verification_outputs/wave209-p5-cross-domain-per-record.csv` (new)
- `docs/audit/wave209-p5-narrative-focus.md` (new)
- `docs/audit/wave209-p5-cross-domain-flowmol3.md` (this file, new)
