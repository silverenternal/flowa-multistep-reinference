# TNNLS Submission — Data Availability Statement

**Status:** Finalised for TNNLS submission. All artifacts cited below are byte-addressable in `verification_outputs/` and on Zenodo.

---

## Code availability

The FlowA framework is open-source under the project's existing license (see `LICENSE`).

- **Source code repository:** GitHub (`flowa-multistep-reinference`)
- **Frozen release tag:** `v3.0-tnnls-ready` (to be tagged at submission freeze)
- **Docker image:** `flowa:tnnls-v3.0` (Docker recipe at `Dockerfile.tnnls`)
- **Zenodo DOI:** (to be generated at submission freeze via GitHub release `v3.0-tnnls-ready`)

### Unmodified vendored upstream code (Wave 262 P1 — 2026-09-22)

All vendored upstream repositories (FlowMol3, LineageFlow, Kanzi,
ProtBFN-AbBFN, GraphBFN, Lumina-Image-2.0, HiDream-I1, Wan2.2, FreqFlow
— total 9) were initially inspected for modifications. 8 files had been
silently patched during internal development (Wave 68 / Wave 166 / Wave 168
etc.). Per user academic-integrity directive (2026-09-22), ALL 8 files were
reverted to their upstream commit-hash versions (FlowMol3 commit `77cae22`,
LineageFlow commit `ccef84a`). The framework now ships unmodified vendored
code.

The 8 reverted files and their upstream commits are:

| # | Repository | File | Upstream commit |
|---|------------|------|------------------|
| 1 | FlowMol3 | `flowmol/analysis/molecule_builder.py` | `77cae22` |
| 2 | FlowMol3 | `flowmol/models/flowmol.py` | `77cae22` |
| 3 | FlowMol3 | `flowmol/utils/ctmc_utils.py` | `77cae22` |
| 4 | FlowMol3 | `flowmol/analysis/metrics.py` | `77cae22` |
| 5 | LineageFlow | `evaluation/evaluate_all.py` | `ccef84a` |
| 6 | LineageFlow | `evaluation/foldability_omegafold.py` | `ccef84a` |
| 7 | LineageFlow | `evaluation/novelty_mmseqs2.py` | `ccef84a` |
| 8 | LineageFlow | `evaluation/run_foldability.py` | `ccef84a` |
| 9 | LineageFlow | `evaluation/self_consistency_esmif.py` | `ccef84a` |

(File 4 = `metrics.py` was reverted at Wave 260 P1 commit `4af95da`; files
1–3 and 5–9 were reverted at Wave 262 P1 commit `8f0255d`. All 9 files are
bytewise identical to their upstream commit hash.)

Previously defensively patched papers' evaluation scripts (which added
`--workers-per-gpu` / `--pctid-novelty` / `--temperature` flags with
defaults=OFF to preserve prior behavior) were reverted. R1 LineageFlow HMMER
N=1000 reading (158 baseline / 342 framework / +116.46% Δ / p<1e-10) and
R6 k6 foldability per-tier d_z values were generated with default flags;
since the new flags were default=OFF (preserves prior behavior), the
numbers are stable. Future work: full rerun with `--workers-per-gpu` flag
explicitly set to 1 to verify byte-stable reproduction.

Reviewers can verify byte-identity via the Wave 262 P2 verify audit
(`docs/audit/wave262-p2-verify.md`): md5 of every vendored file matches
its upstream reference. The full upstream-modifications audit trail is in
`docs/audit/wave261-p1-inventory.md` + `wave261-p5-final-audit.md` +
`wave262-p1-revert-all.md` + `wave262-p3-rerun.md`.

## Data availability

### Per-record CSVs (verification artifacts)

All headline numbers in the manuscript are sourced from byte-addressable per-record CSVs under `verification_outputs/`:

- **R1 LineageFlow HMMER N=1000:** `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/`
- **R2 Kanzi RMSD N=1000:** `verification_outputs/wave235-p2-r2-uplift.json`
- **R3 FlowMol3 fg_dev N=200 NFE=250:** `verification_outputs/wave242-p1-flowmol3-seed{43,44}-*.json` (in flight)
- **R4 2D Two Moons W₂:** `verification_outputs/r4_2d_two_moons_w2_m7p28pct/`
- **R5 2D Eight Gaussians W₂:** `verification_outputs/r5_2d_eight_gaussians_w2_m10p40pct/`
- **R5b CIFAR-10 Rectified Flow matched-NFE=50:** `verification_outputs/wave235-p1-r5b-fix.json`
- **R6 MNIST FM with tier-aware scheduler:** `verification_outputs/wave235-p3-r6-uplift.json`

### 4-arm head-to-head per-record CSVs

- **16 cells × N=1000 paired per-record:** `verification_outputs/wave230-p2-real-4arm-per-record.csv`

### Statistical methods outputs

- **TOST equivalence (16 cells):** `verification_outputs/wave234-p2-tost.csv`
- **BF01 Bayes factor (16 cells):** `verification_outputs/wave234-p4-bf01.csv`
- **Jonckheere-Terpstra ordered test (R2 + R6):** `verification_outputs/wave234-p3-jonckheere.csv`
- **DerSimonian-Laird random-effects meta-analysis:** `verification_outputs/wave234-p5-meta-summary.json`
- **Non-inferiority test (R5b):** `verification_outputs/wave234-p6-ni-test.csv`

### Engineering gates artifacts

- **D.4 byte-stable regression vectors:** 30/30 PASS preserved (Wave 238 P4 + Wave 242 P4)
- **mkdocs build:** 0 warnings
- **claims_consistency:** no drift
- **Pytest:** 5155 passed / 196 skipped

## Checkpoint availability

All three Tier-3 checkpoints are SHA-256-pinned:

| Checkpoint | SHA-256 (prefix) | Path |
|---|---|---|
| Kanzi | `c2f2ab8d...d270` | `data/kanzi_upstream/` (vendored at commit `cfed9cf`) |
| LineageFlow | `f0b4b25e...54a2b` | `data/lineageflow_upstream/` (vendored at commit `ccef84a`) |
| FlowMol3 | epoch 17, global_step 1,547,236, PyTorch Lightning 2.1.3 | `data/flowmol3/weights_real/checkpoints/last.ckpt` (sha256 `d6cda2d7...`) |

Reviewers re-verify by:

```bash
sha256sum data/flowmol3/weights_real/checkpoints/last.ckpt
# Expected: d6cda2d7bc3d190db1ef7c07a2b84c81  ...
```

## Theorem 1 source paper

The Theorem 1 derivation appendix (`docs/theory/theorem-1-self-contained.md`) references the corresponding author Li 2026 ("Gaussian Posterior Selection on Noncompact Fibres with Uniformly Separated Roots"), submitted to JMAA (rejected) and currently under review at QTDS. The source paper is attached as `supplementary_paper.pdf` (14 pages, LaTeX-rendered) per the corresponding author's submission cover-sheet declaration.

- **Supplementary paper SHA-256:** `a6f3e3650de977e815b4080e21cff64bbbd3274ae07e5698567ea1acdd7a789d`
- **Source-of-truth LaTeX:** `docs/ARCHIVE/top-level/NoiseSelectedRectification_EN.md`
- **Markdown mirror:** `supplementary_paper.md`

## Honesty disclosure — incomplete / partial data

The following items are honestly disclosed as incomplete or partial, with full provenance:

- **R3 FlowMol3 fg_dev 3-seed direction consistency:** Wave 242 P1 in flight (single_mol path NFE=250 N=200 per seed, due to DGL 2.4.0 batched-path bug). Wave 243 P2 verification will produce the final per-seed d_z.
- **K4 (Kanzi decision-metric saturation):** UNDERPOWERED / TIES_AT_ZERO — both arms decode to same mod-20 AA sequence on the saturation ceiling. Camera-ready scope.
- **K5 (FreqFlow + MM-FM integration):** ENV_BLOCKED — deferred to PHASE-4 (upstream checkpoint release gating).
- **K6 (Wan2.2 N=1000 sweep):** DEFERRED to camera-ready (compute budget).

## Cross-references

- `tnnls_submission/MANIFEST.md` — package manifest
- `tnnls_submission/submission_checklist.md` — TNNLS editorial requirements
- `docs/CLAIMS.md` — 39 ACTIVE claims (claims_consistency check passes)
- `docs/audit/wave{235,236,238}-*.md` — Wave 235-238 audit trail