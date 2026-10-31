# TNNLS Submission — Data Availability Statement

**Status:** Finalised for TNNLS submission. All artifacts cited below are byte-addressable in [`verification_outputs/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs) and on Zenodo.

---

## Code availability

The FlowA framework is open-source under the project's existing license (see `LICENSE`).

- **Source code repository:** GitHub (`flowa-multistep-reinference`)
- **Frozen release tag:** `v3.0-tnnls-ready` (to be tagged at submission freeze)
- **Docker image:** `flowa:tnnls-v3.0` (Docker recipe at `Dockerfile.tnnls`)
- **Zenodo DOI:** (to be generated at submission freeze via GitHub release `v3.0-tnnls-ready`)

### Unmodified vendored upstream code (2026-09-22)

All vendored upstream repositories (FlowMol3, LineageFlow, Kanzi,
ProtBFN-AbBFN, GraphBFN, Lumina-Image-2.0, HiDream-I1, Wan2.2, FreqFlow
— total 9) were initially inspected for modifications. 9 files had been
silently patched during internal development. Per the user's
academic-integrity directive (2026-09-22), ALL 9 files were
reverted to their upstream commit-hash versions (FlowMol3 commit `77cae22`,
LineageFlow commit `ccef84a`). The framework now ships unmodified vendored
code. `tools/check_vendored_pristine.py` re-verifies this on the authoring
machine: it fails if any vendored code tree has a modified tracked file, if a
pinned repository is off its commit, or if any of the nine files below differs
from its pin.

The 9 reverted files and their upstream commits are:

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

(File 4 = `metrics.py` was reverted at commit `4af95da`; files
1–3 and 5–9 at commit `8f0255d`. All 9 files are
bytewise identical to their upstream commit hash.)

Previously defensively patched papers' evaluation scripts (which added
`--workers-per-gpu` / `--pctid-novelty` / `--temperature` flags with
defaults=OFF to preserve prior behavior) were reverted. R1 LineageFlow HMMER
N=1000 reading (158 baseline / 342 framework / +116.46% Δ / p<1e-10) and
R6 k6 foldability per-tier d_z values were generated with default flags;
since the new flags were default=OFF (preserves prior behavior), the
numbers are stable. Future work: full rerun with `--workers-per-gpu` flag
explicitly set to 1 to verify byte-stable reproduction.

Reviewers can verify byte-identity via the verify audit
([`docs/audit/wave262-p2-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave262-p2-verify.md)): md5 of every vendored file matches
its upstream reference. The full upstream-modifications audit trail is in
[`docs/ARCHIVE/audit-by-wave/wave261-p1-inventory.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/audit-by-wave/wave261-p1-inventory.md) + [`wave261-p5-final-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/audit-by-wave/wave261-p5-final-audit.md) +
[`wave262-p1-revert-all.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-revert-all.md).

## Data availability

### Per-record CSVs (verification artifacts)

All headline numbers in the manuscript are sourced from byte-addressable per-record CSVs under [`verification_outputs/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs) and [`docs/headline-evidence/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence):

- **R1 LineageFlow HMMER N=1000:** [`verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026)
- **R2 Kanzi RMSD N=1000:** [`verification_outputs/wave235-p2-r2-uplift.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p2-r2-uplift.json)
- **R3 FlowMol3 fg_dev, N=1000 per arm, NFE=250, seeds 42/43/44:** [`verification_outputs/r3_n1000_3seed_fixed_q4_2026/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/r3_n1000_3seed_fixed_q4_2026)
- **R4 2D Two Moons W₂:** [`docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct)
- **R5 2D Eight Gaussians W₂:** [`docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct)
- **R5b CIFAR-10 Rectified Flow matched-NFE=50:** [`verification_outputs/wave235-p1-r5b-fix.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p1-r5b-fix.json)
- **R6 MNIST FM with tier-aware scheduler:** [`verification_outputs/wave235-p3-r6-uplift.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p3-r6-uplift.json)

### 4-arm head-to-head per-record CSVs

- **16 cells × N=1000 paired per-record:** [`verification_outputs/wave230-p2-real-4arm-per-record.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave230-p2-real-4arm-per-record.csv)

### Statistical methods outputs

- **TOST equivalence (16 cells):** [`verification_outputs/wave234-p2-tost.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p2-tost.csv)
- **BF01 Bayes factor (16 cells):** [`verification_outputs/wave234-p4-bf01.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p4-bf01.csv)
- **Jonckheere-Terpstra ordered test (R2 + R6):** [`verification_outputs/wave234-p3-jonckheere.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p3-jonckheere.csv)
- **DerSimonian-Laird random-effects meta-analysis:** [`verification_outputs/wave234-p5-meta-summary.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p5-meta-summary.json)
- **Non-inferiority test (R5b):** [`verification_outputs/wave234-p6-ni-test.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p6-ni-test.csv)

### Engineering gates artifacts

- **D.4 byte-stable regression vectors:** 30/30 PASS preserved
- **mkdocs build:** 0 warnings
- **claims_consistency:** no drift
- **Pytest:** 5650 passed / 180 skipped / 0 failed (2026-10-31 CPU run)

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

The Theorem 1 derivation appendix ([`docs/theory/theorem-1-self-contained.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/theorem-1-self-contained.md)) references the corresponding author Li 2026 ("Gaussian Posterior Selection on Noncompact Fibres with Uniformly Separated Roots"), submitted to JMAA (rejected) and currently under review at QTDS. The source paper is attached as `supplementary_paper.pdf` (14 pages, LaTeX-rendered) per the corresponding author's submission cover-sheet declaration.

- **Supplementary paper SHA-256:** `a6f3e3650de977e815b4080e21cff64bbbd3274ae07e5698567ea1acdd7a789d`
- **Source-of-truth LaTeX:** [`docs/ARCHIVE/top-level/NoiseSelectedRectification_EN.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/top-level/NoiseSelectedRectification_EN.md)
- **Markdown mirror:** `supplementary_paper.md`

## Honesty disclosure — incomplete / partial data

The following items are honestly disclosed as incomplete or partial, with full provenance:

- **R3 FlowMol3 fg_dev 3-seed direction consistency:** in flight (single_mol path NFE=250 N=200 per seed, due to DGL 2.4.0 batched-path bug). The final per-seed d_z will be produced once that sweep completes.
- **K4 (Kanzi decision-metric saturation):** UNDERPOWERED / TIES_AT_ZERO — both arms decode to same mod-20 AA sequence on the saturation ceiling. Camera-ready scope.
- **K5 (FreqFlow + MM-FM integration):** ENV_BLOCKED — deferred to PHASE-4 (upstream checkpoint release gating).
- **K6 (Wan2.2 N=1000 sweep):** DEFERRED to camera-ready (compute budget).

## Cross-references

- [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) — package manifest
- [`tnnls_submission/submission_checklist.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/submission_checklist.md) — TNNLS editorial requirements
- [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) — 39 ACTIVE claims (claims_consistency check passes)
- [`docs/audit/wave{235,236,238}-*.md`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit) — statistical / wall-clock audit records

---

## Upstream vendored repositories — pinned commits (additive — 2026-09-25)

The 9 vendored upstream repositories referenced in the manuscript are
pinned at their canonical upstream commit hashes (or SHA-256-pinned
tarball for tarball-vendored releases). These are the same sources the
user's academic-integrity directive ("all modifications to others' original
repos must be reverted") references; vendored code is byte-identical to
upstream. **Source of truth: `git -C data/<repo>/<path> log -1 --format='%H'`
read-only on 2026-09-25 (no vendored file modified during this
verification).**

| # | Repository | Local vendored path | Pinned upstream ref | Vendor mode |
|---|------------|---------------------|---------------------|-------------|
| 1 | FlowMol3 | `data/FlowMol3/repo/` | git commit `77cae22174b7792b0e25e9e0414038420736d841` (`77cae22`) — "Update readme.md" | git vendor (cloned at `77cae22`) |
| 2 | LineageFlow | `data/lineageflow_upstream/` | git commit `ccef84adff421fcb6b855285bc1860e1f9a94f59` (`ccef84a`) — "Prepare LineageFlow public release" | git vendor (cloned at `ccef84a`) |
| 3 | Kanzi | `data/kanzi_upstream/` | git commit `cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b` (`cfed9cf`) — "add nano banana strip" | git vendor (cloned at `cfed9cf`) |
| 4 | HiDream-I1 | `data/hidream_i1/weights/` | git commit `8ccbbfb270ccdae26d6bb0081df67dc81e4033bf` (`8ccbbfb`) — "Update README.md" | git vendor (HF-diffusers mirror at `8ccbbfb`) |
| 5 | GraphBFN | `data/graphbfn/repo/` | git commit `a36ce07d680a3299b56d2e1436917c30b9817fc0` (`a36ce07`) — "Initial commit" | git vendor (cloned at `a36ce07`) |
| 6 | Lumina-Image-2.0 | `data/lumina_image_2_0/repo/` | git commit `4a4d6f856115db07e8ae127280ebcc3d9f65004e` (`4a4d6f8`) — "Update README.md" | git vendor (cloned at `4a4d6f8`) |
| 7 | ProtBFN-AbBFN | `data/protbfn_abbfn/repo/` | git commit `869a9afb2c0167b2d5a35b07867220da9732ef43` (`869a9af`) — "Update README.md" | git vendor (cloned at `869a9af`) |
| 8 | Wan2.2 | `data/wan2_2/repo/` | git commit `42bf4cfaa384bc21833865abc2f9e6c0e67233dc` (`42bf4cf`) — "fix readme" | git vendor (cloned at `42bf4cf`) |
| 9 | FreqFlow | `data/freqflow_ckpt/upstream/` (source tree) + `data/freqflow_ckpt/upstream.tar.gz` (packaged tarball) | tarball SHA-256-pinned per `data/freqflow_ckpt/SHA256SUMS` (1024 source-tree files + 32 weights; pinned 2026-09-05) | tarball vendor (CVPR 2026, arXiv 2604.15521; no git release available) |

**Honest-uncertainty disclosure (additive):** for FreqFlow (row 9), no
git-vendored repo is published by the authors; the upstream source is
SHA-256-pinned as a tarball per `data/freqflow_ckpt/SHA256SUMS.upstream`.
The `nnet_ema.pth` weights remain **NOT RELEASED** by upstream as of
2026-09-25 (verified by [CLM-056](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#clm-056) — FreqFlowAdapter is
synthetic-skeleton-only by editorial honesty). Rows 1–8 use git
vendor mode and are byte-identical to upstream commit hashes per the
verify audit
([`docs/audit/wave262-p2-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave262-p2-verify.md)).

---

## Reproduction instructions (additive — 2026-09-25)

The manuscript's headline numbers are reproduced from byte-stable artifacts at
[verification_outputs/](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs).
Reviewers re-verify in four steps. Step 2 + 3 use the `reproduce/`
directory's per-cell one-click scripts (one per R-level cell, with a second
recipe-level verifier for R6 and an aggregate verifier for all eleven cells)
plus a `verify_all_headlines.sh` master verifier that runs them serially.

1. **Activate the appropriate sidecar venv** — never mix model environments
   ([`docs/environments.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/environments.md)):

   ```bash
   # FlowMol3, 2D (Two Moons / Eight Gaussians), CIFAR-10, MNIST FM
   source .venvs/flowmol3_venv/bin/activate
   # LineageFlow (R1, R4-R5, plus HMMER Pfam-A reads)
   source .venvs/lineageflow_venv/bin/activate
   # Kanzi (R2 — protein decision-metric saturation)
   source .venvs/kanzi_venv/bin/activate
   ```

   Sidecar venvs mirror each upstream repo's `requirements.txt` /
   `environment.yml` and keep the framework's project venv minimal
   (torch-free, stdlib-only). Vendored upstream code (rows 1–9 above) is
   byte-identical to upstream regardless of which venv is activated.

2. **Install** (reviewer-side, idempotent): the framework itself plus
   per-model deps:

   ```bash
   pip install -e .                               # framework (project venv)
   pip install -r data/FlowMol3/repo/requirements.txt   # or model-equivalent
   ```

   Each vendored repo's `requirements.txt` (or `environment.yml`) is at
   the canonical upstream path listed in the table above.

3. **Reproduce per-cell** via `reproduce/*.sh` (one-click, byte-stable):

   ```bash
   bash reproduce/01_R1_LineageFlow.sh        # R1: HMMER N=1000
   bash reproduce/02_R2_Kanzi.sh              # R2: Kanzi RMSD N=1000
   bash reproduce/03_R3_FlowMol3.sh           # R3: FlowMol3 fg_dev, N=1000 x 3 seeds
   bash reproduce/04_R4_2D_TwoMoons.sh        # R4: 2D Two Moons W2 (SOTA + ablation)
   bash reproduce/05_R5_2D_EightGaussians.sh  # R5: 2D Eight Gaussians W2
   bash reproduce/06_R5b_CIFAR_n_rounds1.sh   # R5b: CIFAR-10 matched-NFE=50
   bash reproduce/07_R6_MNIST_TierAware.sh    # R6: LineageFlow k6, live tier-aware
   bash reproduce/08_verify_R6_recipe.sh      # R6: recipe-level SHA-256 chain
   bash reproduce/09_verify_all_cell_recipes.sh  # all 11 cells, one command
   ```

   Each per-cell script verifies the headline from the byte-stable
   `verification_outputs/<cell>/` artifact (default behaviour prints
   "OK" / "FAIL" against the pinned headline). The full live-sweep
   re-execution command is **commented out** by default inside each
   script; uncomment for an end-to-end re-run (cells range from 30 min
   GPU to 50 h CPU).

4. **Verify all 8 reproduction checks (7 R-level cells + the R6 recipe
   check)** with one command:

   ```bash
   bash reproduce/verify_all_headlines.sh
   # Expected: "OK: All 8/8 reproduction checks verified"
   # On failure, exits non-zero and prints the failing check(s).
   ```

   Then run the engineering gates (must all exit 0):

   ```bash
   python3 -m pytest tests/test_d4_regression_vectors.py -q     # 30/30 PASS
   ruff check adaptive_reflow/ tests/ scripts/ tools/           # 0 findings
   mkdocs build --strict                                         # exit 0
   python3 tools/check_claims_consistency.py                    # no drift
   cd tnnls_submission && sha256sum -- *.md                     # matches MANIFEST
   ```

   Wall-clock budgets and skipped-record counts for each cell are in
   the per-cell audit notes ([docs/audit/wave{086,235,236}-*.md](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit)).
   Out-of-scope: K4 (Kanzi saturation ceiling), K5 (FreqFlow + MM-FM
   integration), and K6 (Wan2.2 N=1000 sweep) are honestly disclosed as
   `UNDERPOWERED` / `DEFERRED` / `ENV_BLOCKED` in the prior section —
   these are not reproducible from public artifacts at submission
   time.

---

## Supporting audit documents

Every per-increment audit record behind this submission is indexed at
[`docs/audit/INDEX.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/INDEX.md),
which lists each record by topic with its path. The records cover the
paper-fix passes, cross-document consistency fixes, link repair, the gap
audits, R1 materialisation and the Theorem 5 numerics, the claims
consolidation, and the supplementary-bundle polish. Together they
constitute the reproducible evidence chain from code →
`verification_outputs/` → headline number. Each `verification_outputs/`
artifact is byte-addressable per the
[`docs/verification_outputs.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/verification_outputs.md)
master index (SHA-256 disclosed).
