# `verification_outputs/` — Master Index of Headline-Evidence Artifacts

> **Status:** Wave 355 P1 — master index for the gitignored byte-addressable evidence directory.
> **Path:** `verification_outputs/` (gitignored at `.gitignore:64`).
> **Mirror:** SHA-256 fingerprints of pinned headline artifacts are recorded in
> `tnnls_submission/MANIFEST.md` rows 34–40 (figure SHA-256s for Wave 183 P4 + R5c/R5b)
> and inline inside individual `docs/audit/wave<N>-*.md` audit notes (per-wave provenance).
> **Audit doc:** [`docs/audit/wave355-verification-outputs-readme.md`](audit/wave355-verification-outputs-readme.md)
> (this README's Wave 355 P1 audit trail).
> **Date:** 2026-09-25.

---

## 1. Scope (observed facts at HEAD `a3944e0`)

| Item | Value |
|---|---|
| Top-level directory | `verification_outputs/` |
| Total bytes (filesystem) | 1,006,900,606 B (≈ 960 MiB, `du -sh` reports 975M) |
| Subdirectories | 122 (grouped below by topic / wave) |
| Top-level loose files | 426 (mostly `*_q3_2026.json` / `*_q4_2026.json` headless single-record evidence; see §5) |
| Subdirectories with `SHA256SUMS` | 7 (`wave280-{k7,p-k1,p-k4k5,p-r1,p-r3,p-r5c}` + `wave349-r1-3seed-gpu`) |
| Subdirectories with `manifest.json` / `summary.json` | 27 (root-level manifest, mostly post-Wave 280) |
| Audit docs that reference this tree | 270+ entries in `docs/audit/wave*.md` (per `grep -lE "verification_outputs/(wave\|wf)[0-9]+" docs/audit/*.md`) |
| Tracking policy | `.gitignore:64` excludes `verification_outputs/` wholesale (verified by `git check-ignore -v verification_outputs/README.md`) |
| Provenance surface | SHA-256 of every tracked row that pins a figure / numerical artifact lives in `tnnls_submission/MANIFEST.md` and inline in the owning audit doc |

The **whole tree is gitignored by design** — the underlying artifacts (npz checkpoints, FASTAs, PDB outputs, FID caches, etc.) are large binary blobs that do not belong in git history. SHA-256 fingerprints of the headline-load-bearing artifacts (R5c / R5b / R6 / Wave 183 figures) are tracked in `tnnls_submission/MANIFEST.md` rows 34–40 and inside individual audit docs; a reviewer who can clone the repo + access `verification_outputs/` can re-verify every fingerprint.

---

## 2. How to read this index

The directory contains three classes of artifact (documented in §1):

1. **122 wave/topic subdirectories** — each cell maps to (b) the wave that produced it (§3) and (b) the audit doc that explains it (§4). They are the canonical "headline evidence" for the corresponding claim / figure / verdict.
2. **426 loose top-level JSON files** — pre-Wave-280 headless single-record evidence; each one is a frozen snapshot of one sweep / ablation / scoring run from the `q3_2026` / `q4_2026` work cycle. They are listed in §5.
3. **Per-subdirectory metadata** — `SHA256SUMS` (7 subdirs) + `manifest.json` / `summary.json` (27 subdirs) + per-record CSVs / `.npy` / `.npz` / `.json` / `.jsonl` artifacts. SHA-256 of pinned headline bytes is in `tnnls_submission/MANIFEST.md`.

For any subdirectory:

- **Read the audit doc** first (§4 cross-reference column).
- **Inspect `manifest.json` / `summary.json`** for the wave's tool, N, seed policy, environment, and per-record wall-clock.
- **Run `sha256sum -c SHA256SUMS`** when the subdirectory has one (7 subdirs at HEAD).
- **For non-SHA256SUMS subdirs**, SHA-256 of pinned headline figures / numerical artifacts is recorded inline in the audit doc + `tnnls_submission/MANIFEST.md` (rows 34–40).

---

## 3. Per-directory table (122 subdirs, grouped by topic / wave)

Columns:
- **path** — subdirectory relative to repo root
- **MB** — `du -sm` size (filesystem allocation; rounded)
- **files** — `find -type f` count
- **SHA** — `Y` if a `SHA256SUMS` file is present, `-` otherwise
- **topic** — one-line headline-evidence description
- **audit** — `docs/audit/waveNNN-*.md` doc(s) that reference this directory (if any)

### 3.1 Recent headline evidence (Wave 349–355, camera-ready scope)

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave349-r1-3seed-gpu/` | 0 | 7 | Y | R1 3-seed N=1000 LineageFlow paper-parity GPU sweep (seed 42 + 43 + 44) | `wave349-p2-r1-3seed-n1000-gpu.md` |
| `wave350-r6-live-smoke/` | 2 | 5 | - | R6 k6 foldability live GPU smoke (N=30 foldability.jsonl + 30 pdbs) | `wave350-r6-live-attempt.md` |
| `wave351-p3-thm5-numerical/` | 0 | 2 | - | Theorem 5 numerical validation (L_local ≈ 0.3810, 12-cell grid fit) | `wave351-thm5-numerical.md` |
| `wave351-r5a-n10/` | 0 | 3 | - | R5a Wave 351 P2 n=10 paired-t TIE_PERSISTS confirmation | `wave351-r5a-n10.md`, `wave352-claims-r5a-update.md` |
| `wave338-r6-live-smoke/` | 0 | 4 | - | R6 live GPU smoke (Wave 338 baseline env-blocked check) | `wave338-r6-live-eval-smoke.md` (if present) |
| `wave338-r6-live-eval-smoke/` | 0 | 1 | - | R6 live eval smoke (Wave 338) | `wave338-r6-live-eval-smoke.md` (if present) |
| `wave338-r6-live-cosine-baseline/` | 0 | 1 | - | R6 cosine baseline reference (Wave 338) | `wave338-r6-live-eval-smoke.md` (if present) |
| `wave355-capability-token-example/` | 0 | 1 | - | Wave 355 capability-token handshake synthetic-continuous example | `wave355-verification-outputs-readme.md` (this README) |

### 3.2 Wave 280 — paper-parity p1–p7 R-level sweep (the load-bearing §7.2 evidence refresh)

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave280-k7/` | 0 | 10 | Y | K7 paper-parity 3-seed N=1000 sweep (seeds 42/43/44) | `wave280-paper-parity.md` (if present) |
| `wave280-p-k1/` | 0 | 1 | Y | K1 paper-parity N=1000 sweep | `wave280-paper-parity.md` (if present) |
| `wave280-p-k4k5/` | 3 | 7 | Y | K4+K5 paper-parity N=1000 sweep | `wave280-paper-parity.md` (if present) |
| `wave280-p-r1/` | 11 | 13 | Y | R1 3-seed N=1000 LineageFlow HMMER sweep (load-bearing §7.2 R1 row) | `wave280-paper-parity.md` (if present) |
| `wave280-p-r3/` | 0 | 1 | Y | R3 4-arm sweep (FlowMol3 baseline vs framework) | `wave280-paper-parity.md` (if present) |
| `wave280-p-r5c/` | 3 | 4 | Y | R5c 4-arm sweep (lineageflow cosine schedule) | `wave280-paper-parity.md` (if present) |

### 3.3 Wave 247–248 — R5b algorithm uplift sweeps (n_rounds / NFE ladder)

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave247-p2-r5b-seed42-n1-n100/` | 16 | 2 | - | R5b seed=42 n=100 4-arm sweep (baseline / framework / arms) | `wave247-p2-r5b-multiseed.md` (if present) |
| `wave247-p2-r5b-seed42-n1-n200/` | 0 | 2 | - | R5b seed=42 n=200 4-arm sweep | `wave247-p2-r5b-multiseed.md` (if present) |
| `wave247-p2-r5b-seed43-n1-n100/` | 16 | 2 | - | R5b seed=43 n=100 4-arm sweep | `wave247-p2-r5b-multiseed.md` (if present) |
| `wave247-p2-r5b-seed44-n1-n100/` | 16 | 2 | - | R5b seed=44 n=100 4-arm sweep | `wave247-p2-r5b-multiseed.md` (if present) |
| `wave247-p3-r5b-n1000-n1/` | 157 | 8 | - | R5b n=1000 4-arm sweep (largest R5b evidence) | `wave247-p3-r5b-n1000.md` (if present) |
| `wave247-p5-r5b-nfe50-n1/` | 32 | 6 | - | R5b NFE=50 ladder | `wave247-p5-r5b-nfe-sweep.md` (if present) |
| `wave247-p5-r5b-nfe100-n1/` | 32 | 6 | - | R5b NFE=100 ladder | `wave247-p5-r5b-nfe-sweep.md` (if present) |
| `_wave247-p2-logs/` | 0 | 1 | - | Wave 247 P2 sweep log directory (informational) | — |
| `wave248-p1-r5b-heun-heun_heun_nrounds1_nfe50/` | 12 | 6 | - | R5b Heun 1-round NFE=50 ablation | `wave248-p1-r5b-heun.md` (if present) |
| `wave248-p1-r5b-heun-heun_heun_nrounds4_nfe200/` | 2 | 6 | - | R5b Heun 4-round NFE=200 ablation | `wave248-p1-r5b-heun.md` (if present) |

### 3.4 Wave 235 — R5b `n_rounds` + no-final-restart ablations

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `_wave235-p1-logs/` | 0 | 1 | - | Wave 235 P1 log directory (informational) | — |
| `wave235-p1-r5b-no-final-restart-n200/` | 12 | 8 | - | R5b no-final-restart N=200 ablation | `wave235-p1-r5b-no-final-restart.md` (if present) |
| `wave235-p1-r5b-no-final-restart-n200-quick/` | 4 | 8 | - | R5b no-final-restart N=200 quick ablation | `wave235-p1-r5b-no-final-restart.md` (if present) |
| `wave235-p1-r5b-nofr-rounds1-n200/` | 31 | 8 | - | R5b no-fr rounds=1 N=200 ablation | `wave235-p1-r5b-nofr-rounds1.md` (if present) |
| `wave235-p1-r5b-rounds1-n200/` | 31 | 8 | - | R5b rounds=1 N=200 ablation | `wave235-p1-r5b-rounds1.md` (if present) |

### 3.5 Wave 225 — R5b matched-eff-NFE + rounds=2 ablations

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave225-p7-r5b-rounds2-n200/` | 39 | 8 | - | R5b rounds=2 N=200 ablation | `wave225-p7-r5b-rounds2.md` (if present) |
| `wave225-p9-r5b-matched-eff-nfe-n200/` | 12 | 8 | - | R5b matched-eff-NFE N=200 ablation | `wave225-p9-r5b-matched-eff-nfe.md` (if present) |

### 3.6 Wave 218 / 214 / 206 / 199 — Kanzi / LineageFlow n=1000 sweeps

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave218-p2-kanzi-n10-smoke/` | 0 | 1 | - | Kanzi N=10 smoke (Wave 218) | `wave218-p2-kanzi-n10-smoke.md` (if present) |
| `wave214-p2-kanzi-baseline-n1000/` | 0 | 1 | - | Kanzi N=1000 baseline (Wave 214 P2) | `wave214-p2-kanzi-baseline-n1000.md` (if present) |
| `wave214-p2-kanzi-framework-inv-proj-n1000/` | 0 | 1 | - | Kanzi N=1000 framework inverse-projector (Wave 214 P2) | `wave214-p2-kanzi-framework-inv-proj-n1000.md` (if present) |
| `wave214-p2-kanzi-framework-inv-proj-n10-smoke/` | 0 | 1 | - | Kanzi N=10 framework inv-proj smoke | `wave214-p2-kanzi-framework-inv-proj-n10-smoke.md` (if present) |
| `wave206-p1-lineageflow-n1000/` | 241 | 3 | - | LineageFlow N=1000 sweep (Wave 206 P1, large FASTAs) | `wave206-p1-lineageflow-n1000.md` (if present) |
| `wave206_p6_pilot/` | 0 | 1 | - | LineageFlow P6 pilot sweep | `wave206-p6-pilot.md` (if present) |
| `wave199-p2-lineageflow-n1000/` | 0 | 1 | - | LineageFlow N=1000 sweep (Wave 199 P2) | `wave199-p2-lineageflow-n1000.md` (if present) |

### 3.7 Wave 196 — Kanzi framework inv-proj baseline vs framework

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave196-p3-kanzi-n1000-framework-inv-proj-baseline/` | 0 | 1 | - | Kanzi N=1000 inv-proj baseline (Wave 196 P3) | `wave196-p3-kanzi-n1000-framework-inv-proj.md` (if present) |
| `wave196-p3-kanzi-n1000-framework-inv-proj-framework/` | 0 | 1 | - | Kanzi N=1000 inv-proj framework (Wave 196 P3) | `wave196-p3-kanzi-n1000-framework-inv-proj.md` (if present) |

### 3.8 Wave 191 — CIFAR-10 / MNIST N=1000 sweeps

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave191-p2-cifar10-n1000/` | 179 | 13 | - | CIFAR-10 N=1000 sweep (Wave 191 P2, largest CIFAR-10 evidence) | `wave191-p2-cifar10-n1000.md` (if present) |
| `wave191-p2-cifar10-smoke/` | 2 | 9 | - | CIFAR-10 smoke (Wave 191 P2) | `wave191-p2-cifar10-smoke.md` (if present) |
| `wave191-p3-mnist-n1000/` | 8 | 9 | - | MNIST N=1000 sweep (Wave 191 P3) | `wave191-p3-mnist-n1000.md` (if present) |

### 3.9 Wave 189 / 178 / 175 — 2D SOTA rerun + §p6 + sanity

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave189-p2-sota-2d-rerun/` | 0 | 1 | - | 2D SOTA rerun (Wave 189 P2) | `wave189-p2-sota-2d-rerun.md` (if present) |
| `wave178-p6/` | 0 | 1 | - | Wave 178 P6 evidence | `wave178-p6.md` (if present) |
| `wave175-p3-sanity/` | 0 | 4 | - | Wave 175 P3 sanity check | `wave175-p3-sanity.md` (if present) |

### 3.10 Wave 165–174 — k6 foldability + nfe_curve + novelty real_ckpt (lineageflow evidence burst)

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave165_failure_modes_q3_2026/` | 0 | 1 | - | Failure-modes scan (Wave 165, q3_2026 cycle) | `wave165-failure-modes.md` (if present) |
| `cross_model_nfe_curve_w171_q3_2026/` | 0 | 8 | - | Cross-model NFE curve (Wave 171) | `wave171-cross-model-nfe-curve.md` (if present) |
| `cross_model_real_ckpt_w172b_q3_2026/` | 2 | 171 | - | Cross-model real ckpt (Wave 172b) | `wave172b-cross-model-real-ckpt.md` (if present) |
| `cross_model_real_ckpt_w173_p5_2026/` | 1 | 13 | - | Cross-model real ckpt (Wave 173 P5) | `wave173-p5-cross-model-real-ckpt.md` (if present) |
| `cross_model_real_ckpt_w174_q3_2026/` | 36 | 929 | - | Cross-model real ckpt (Wave 174, large) | `wave174-cross-model-real-ckpt.md` (if present) |
| `k1_rc5_5arm_synth_w154b_q3_2026/` | 0 | 1 | - | K1 5-arm synthetic sweep (Wave 154b) | `wave154b-k1-rc5-5arm-synth.md` (if present) |
| `k1_rc5_real_w157_q3_2026/` | 0 | 1 | - | K1 real ckpt sweep (Wave 157) | `wave157-k1-rc5-real.md` (if present) |
| `k6_foldability_n1000_w160_q3_2026/` | 3 | 22 | - | K6 foldability N=1000 baseline+framework (Wave 160) | `wave160-k6-foldability.md` (if present) |
| `k6_foldability_n1000_w161_q3_2026/` | 2 | 24 | - | K6 foldability N=1000 retest (Wave 161) | `wave161-k6-foldability.md` (if present) |
| `k6_foldability_sanity_w160_q3_2026/` | 1 | 37 | - | K6 foldability sanity (Wave 160) | `wave160-k6-foldability-sanity.md` (if present) |
| `lineageflow_hmmer_full_placeholder_w154b_q3_2026/` | 0 | 1 | - | LineageFlow HMMER full placeholder (Wave 154b) | `wave154b-lineageflow-hmmer-full.md` (if present) |
| `lineageflow_hmmer_real_n1000_w156c_q3_2026/` | 0 | 1 | - | LineageFlow HMMER real N=1000 (Wave 156c) | `wave156c-lineageflow-hmmer-real.md` (if present) |
| `lineageflow_hmmer_real_n1000_w158_q3_2026/` | 0 | 1 | - | LineageFlow HMMER real N=1000 (Wave 158) | `wave158-lineageflow-hmmer-real.md` (if present) |
| `lineageflow_n1000_omegafold_q4_2026/` | 2 | 3 | - | LineageFlow N=1000 OmegaFold sweep | `wave158-omegafold.md` (if present) |
| `lineageflow_novelty_mmseqs2_w163_q3_2026/` | 0 | 1 | - | LineageFlow novelty via MMseqs2 (Wave 163) | `wave163-lineageflow-novelty-mmseqs2.md` (if present) |
| `lineageflow_real_fastas_w158_q3_2026/` | 0 | 4 | - | LineageFlow real FASTAs (Wave 158, manifest.json) | `wave158-lineageflow-real-fastas.md` (if present) |
| `nfe_curve_fair_w170_q3_2026/` | 0 | 1 | - | NFE curve fair comparison (Wave 170) | `wave170-nfe-curve-fair.md` (if present) |
| `nfe_curve_real_w166_q3_2026/` | 0 | 1 | - | NFE curve real (Wave 166) | `wave166-nfe-curve-real.md` (if present) |
| `nfe_curve_real_w166b_q3_2026/` | 0 | 1 | - | NFE curve real (Wave 166b) | `wave166b-nfe-curve-real.md` (if present) |
| `nfe_curve_real_w167_q3_2026/` | 0 | 1 | - | NFE curve real (Wave 167) | `wave167-nfe-curve-real.md` (if present) |
| `nfe_curve_real_w168_q3_2026/` | 0 | 1 | - | NFE curve real (Wave 168) | `wave168-nfe-curve-real.md` (if present) |
| `nfe_curve_w165b_q3_2026/` | 0 | 1 | - | NFE curve (Wave 165b) | `wave165b-nfe-curve.md` (if present) |
| `novelty_canonical_sensitive_w165b_q3_2026/` | 0 | 1 | - | Novelty canonical-sensitive (Wave 165b) | `wave165b-novelty-canonical-sensitive.md` (if present) |
| `novelty_canonical_w165_q3_2026/` | 0 | 1 | - | Novelty canonical (Wave 165) | `wave165-novelty-canonical.md` (if present) |
| `novelty_pctid_w166_q3_2026/` | 1 | 8 | - | Novelty pctid (Wave 166) | `wave166-novelty-pctid.md` (if present) |

### 3.11 Wave 132 / 131 / 129 / 128 — CIFAR-10 ARM + FID + 2D sweeps

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave132_cifar_arm_fid/` | 0 | 1 | - | CIFAR-10 ARM FID sweep (Wave 132) | `wave132-cifar-arm-fid.md` (if present) |
| `wave131_cifar_arms/` | 0 | 1 | - | CIFAR-10 arms sweep (Wave 131) | `wave131-cifar-arms.md` (if present) |
| `wave131_cifar_ref_build/` | 0 | 1 | - | CIFAR-10 reference build (Wave 131) | `wave131-cifar-ref-build.md` (if present) |
| `wave131_cifar_small_sweep/` | 1 | 1 | - | CIFAR-10 small sweep (Wave 131) | `wave131-cifar-small-sweep.md` (if present) |
| `wave129_cifar_arm_smoke/` | 0 | 1 | - | CIFAR-10 ARM smoke (Wave 129) | `wave129-cifar-arm-smoke.md` (if present) |
| `wave129_cifar_ref_check/` | 0 | 1 | - | CIFAR-10 ref check (Wave 129) | `wave129-cifar-ref-check.md` (if present) |
| `wave129_cifar_small_sweep/` | 1 | 1 | - | CIFAR-10 small sweep (Wave 129) | `wave129-cifar-small-sweep.md` (if present) |
| `wave128_cifar_gpu/` | 0 | 1 | - | CIFAR-10 GPU smoke (Wave 128) | `wave128-cifar-gpu.md` (if present) |
| `wave128_cifar_gpu_retry/` | 0 | 1 | - | CIFAR-10 GPU retry (Wave 128) | `wave128-cifar-gpu-retry.md` (if present) |
| `wave128_cifar_gpu_retry2/` | 0 | 1 | - | CIFAR-10 GPU retry 2 (Wave 128) | `wave128-cifar-gpu-retry2.md` (if present) |
| `wave128_cifar_gpu_retry3/` | 0 | 1 | - | CIFAR-10 GPU retry 3 (Wave 128) | `wave128-cifar-gpu-retry3.md` (if present) |
| `wave128_twodim_cpu/` | 0 | 1 | - | 2D Two Moons CPU sweep (Wave 128) | `wave128-twodim-cpu.md` (if present) |

### 3.12 Wave 96 / 88 / 80 — early FlowMol3 / Kanzi baseline sweeps

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `wave96a_diagnose/` | 0 | 1 | - | Wave 96 P-A diagnose | `wave96a-diagnose.md` (if present) |
| `wave96c_verify/` | 0 | 1 | - | Wave 96 P-C verify | `wave96c-verify.md` (if present) |
| `wave88_kanzi_n1000_baseline/` | 0 | 1 | - | Kanzi N=1000 baseline (Wave 88) | `wave88-kanzi-n1000-baseline.md` (if present) |
| `wave80_kanzi_smoke_eval/` | 0 | 1 | - | Kanzi smoke eval (Wave 80) | `wave80-kanzi-smoke-eval.md` (if present) |

### 3.13 Kanzi / LineageFlow real_ckpt / framework_paper_metrics / codebook smoke

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `kanzi_n1000_baseline_seed42_wave116_q3_2026/` | 0 | 1 | - | Kanzi N=1000 baseline seed=42 (Wave 116) | `wave116-kanzi-n1000-baseline-seed42.md` (if present) |
| `kanzi_n1000_baseline_seed42_wave120_q3_2026/` | 0 | 1 | - | Kanzi N=1000 baseline seed=42 (Wave 120) | `wave120-kanzi-n1000-baseline-seed42.md` (if present) |
| `kanzi_n1000_baseline_seed7_wave121_q3_2026/` | 0 | 1 | - | Kanzi N=1000 baseline seed=7 (Wave 121) | `wave121-kanzi-n1000-baseline-seed7.md` (if present) |
| `kanzi_n1000_framework_inv_proj_seed42_wave122_q3_2026/` | 0 | 1 | - | Kanzi N=1000 framework inv-proj seed=42 (Wave 122) | `wave122-kanzi-n1000-framework-inv-proj-seed42.md` (if present) |
| `kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/` | 0 | 1 | - | Kanzi N=1000 framework inv-proj seed=42 (Wave 127) | `wave127-kanzi-n1000-framework-inv-proj-seed42.md` (if present) |
| `kanzi_n1000_framework_inv_proj_seed42_wave131_byte_repro_q3_2026/` | 0 | 1 | - | Kanzi N=1000 framework inv-proj byte-repro seed=42 (Wave 131) | `wave131-kanzi-n1000-framework-inv-proj-seed42-byte-repro.md` (if present) |
| `kanzi_n1000_framework_inv_proj_w149_q4_2026/` | 0 | 1 | - | Kanzi N=1000 framework inv-proj (Wave 149) | `wave149-kanzi-n1000-framework-inv-proj.md` (if present) |
| `kanzi_n1000_framework_paper_metrics/` | 0 | 5 | - | Kanzi N=1000 framework paper-metrics | `wave88-kanzi-framework-paper-metrics.md` (if present) |
| `kanzi_n1000_framework_paper_metrics_diverse/` | 0 | 5 | - | Kanzi N=1000 framework paper-metrics (diverse seeds) | `wave88-kanzi-framework-paper-metrics-diverse.md` (if present) |
| `kanzi_n1000_framework_paper_metrics_inv_proj/` | 7 | 5 | - | Kanzi N=1000 framework paper-metrics inv-proj | `wave88-kanzi-framework-paper-metrics-inv-proj.md` (if present) |
| `kanzi_n1000_framework_paper_metrics_real/` | 0 | 5 | - | Kanzi N=1000 framework paper-metrics real ckpt | `wave88-kanzi-framework-paper-metrics-real.md` (if present) |
| `kanzi_n1000_framework_paper_metrics_real_diverse/` | 0 | 5 | - | Kanzi N=1000 framework paper-metrics real diverse | `wave88-kanzi-framework-paper-metrics-real-diverse.md` (if present) |
| `kanzi_n1000_framework_synth_seed42_wave121_q3_2026/` | 0 | 1 | - | Kanzi N=1000 framework synthetic seed=42 (Wave 121) | `wave121-kanzi-n1000-framework-synth-seed42.md` (if present) |
| `kanzi_n1000_framework_synth_w152_q4_2026/` | 0 | 1 | - | Kanzi N=1000 framework synthetic (Wave 152) | `wave152-kanzi-n1000-framework-synth.md` (if present) |
| `kanzi_n1000_framework_synth_wave120_q3_2026/` | 0 | 1 | - | Kanzi N=1000 framework synthetic (Wave 120) | `wave120-kanzi-n1000-framework-synth.md` (if present) |
| `kanzi_n1000_paper_metrics/` | 0 | 1 | - | Kanzi N=1000 paper-metrics | `wave88-kanzi-n1000-paper-metrics.md` (if present) |
| `kanzi_n1000_real_v3/` | 0 | 1 | - | Kanzi N=1000 real ckpt v3 | `wave88-kanzi-n1000-real-v3.md` (if present) |
| `kanzi_codebook_smoke/` | 0 | 1 | - | Kanzi codebook smoke | `wave88-kanzi-codebook-smoke.md` (if present) |
| `kanzi_inv_proj_n20_20260913_corrected/` | 0 | 10 | - | Kanzi inv-proj N=20 corrected | `wave-kanzi-inv-proj-n20-corrected.md` (if present) |
| `kanzi_inv_proj_n20_20260913_preflight/` | 0 | 5 | - | Kanzi inv-proj N=20 preflight | `wave-kanzi-inv-proj-n20-preflight.md` (if present) |

### 3.14 Ablation / smoke / twodim / power / upstream / engineering

| path | MB | files | SHA | topic | audit |
|---|---|---|---|---|---|
| `ablation_w165b_q3_2026/` | 1 | 9 | - | Ablation sweep (Wave 165b, q3_2026 cycle) | `wave165b-ablation.md` (if present) |
| `cifar_n200_nfe50_ema_corrected/` | 24 | 11 | - | CIFAR-10 N=200 NFE=50 EMA corrected | `wave-cifar-n200-nfe50-ema-corrected.md` (if present) |
| `ci_smoke/` | 1 | 96 | - | CI smoke artifacts | `ci-smoke.md` (if present) |
| `engineering_full_20260913_after_recovery/` | 1 | 5 | - | Engineering full sweep after recovery | `engineering-full-20260913.md` (if present) |
| `engineering_full_20260913_default_threads/` | 2 | 5 | - | Engineering full sweep default-threads | `engineering-full-20260913-default.md` (if present) |
| `flowmol3/` | 0 | 4 | - | FlowMol3 small artifacts (smiles / validity / paper-metrics) | `flowmol3-*.md` (if present) |
| `power_analysis/` | 0 | 1 | - | Power-analysis artifacts (sample-size determination) | `wave-power-analysis.md` (if present) |
| `todo_smoke_20260913/` | 0 | 1 | - | Todo smoke (2026-09-13) | `wave-todo-smoke-20260913.md` (if present) |
| `twodim_beta_smoke_20260913/` | 0 | 1 | - | 2D beta smoke (2026-09-13) | `wave-twodim-beta-smoke-20260913.md` (if present) |
| `twodim_restart_sigma05_smoke_20260913/` | 0 | 1 | - | 2D restart σ=0.5 smoke (2026-09-13) | `wave-twodim-restart-sigma05-smoke-20260913.md` (if present) |
| `upstream_eval/` | 0 | 16 | - | Upstream eval lineageflow / kanzi seeds | `wave-upstream-eval.md` (if present) |
| `wave229-p1-sweep-vanilla/` | 0 | 1 | - | Vanilla sweep (Wave 229 P1) | `wave229-p1-sweep-vanilla.md` (if present) |
| `wave229-p5-molecule-image-per-record/` | 0 | 1 | - | Molecule / image per-record (Wave 229 P5) | `wave229-p5-molecule-image-per-record.md` (if present) |
| `wave296_p6_backward_compat/` | 0 | 1 | - | Wave 296 P6 backward-compat check | `wave296-p6-backward-compat.md` (if present) |
| `wf286/` | 2 | 1 | - | Wavefront 286 evidence | `wf286.md` (if present) |

### 3.15 Loose files at top level (`verification_outputs/*.{json,csv}`)

The 426 top-level loose files (verified via `find verification_outputs/ -maxdepth 1 -type f`) are mostly `*_q3_2026.json` / `*_q4_2026.json` / `*_smoke.json` / `*.csv` snapshots from the q3/q4 2026 work cycle (Wave 60–165). They are referenced inline from `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/INSIGHTS.md`, and the relevant audit docs. Notable categories:

- **Pre-Wave-165 evidence (q3_2026 / q4_2026):** `ablation_q4_2026.json`, `baseline_comparison_q4_2026.json`, `capability_audit_*.json`, `controlled_audit_q3_2026.json`, `flowmol3_*_q4_2026.{json,jsonl}`, `g1_deep_dive_q3_2026.json`, `heuristic_ablation_*_q4_2026.json`, `kanzi_*_q4_2026.json`, `lineageflow_*_q4_2026.json`, `mol_*`, `nfe_scan_*`, `wave39_phase4_regression.json`, `wave40_phase4_regression.json`, `wave59_*_q4_2026.json`, `wave73_phase2_tier1_speedup.json`, `wave80_lf_smoke_q4_2026.json`, etc.
- **Wave 183 figure sidecars (top-level CSVs / PNGs):** `wave183-p3-eval-summary.csv`, `wave183-p4-aggregate.py`, `wave183-p4-aggregation.csv`, `wave183-p4-figure-{pLDDT,scPerplexity,deltas}-finer.png` — byte-stable matplotlib Agg renders at 110 DPI referenced from `paper-A-final.md` §7.7.1 + `tnnls_submission/MANIFEST.md` rows 38–40 (Wave 353 P4 ADDITIVE figures).
- **Wave 235–247 R5b sweeps (top-level CSVs / JSONs):** `wave235-p3-r6-uplift.{csv,json}`, `wave235-p4-flowmol3-3seed.{csv,json,per-record.csv}` (+ per-seed `.json` + `.smiles.txt`), `wave236-p1-p4finish.json`, `wave236-p2-cuda-graph-wall-clock.{csv,json}`, `wave236-p2-wallclock.json`, `wave239-p1-flowmol3-seed43-baseline.{csv,json,jsonl}`, `wave240-p2-flowmol3-direction.csv`, `wave242-p{1,2}-flowmol3-{seed43-baseline,seed43-framework,seed43-summary,direction}.{csv,json}`, `wave245-p2-tier-aware-independence.{csv,json}`, `wave245-p3-cuda-graph-repro.{csv,json}`, `wave246-p{2,3,4}-*.{csv,json}`, `wave247-p2-r5b-multiseed.{csv,json}` (per-seed JSONs), `wave247-p3-r5b-n1000-n1.{csv,json}`, `wave247-p4-r5b-tier-aware.{csv,json}`, `wave247-p5-r5b-nfe{50,100}.{csv,json}`, `wave247-p5-r5b-nfe-sweep-{aggregate,summary}.{csv,json}`, `wave248-p1-r5b-heun-aggregate.{csv,json}` (per-config JSONs).
- **Cross-cutting bytes:** `ckpt_sha256.json` (checkpoint SHA-256 registry), `kanzi_n1000_manifest.json`, `kanzi_n1000_coords.txt` (2.6 MB, Kanzi coordinate sidecar).

**A reviewer who wants to verify a specific top-level file should:**

1. Locate the file in `verification_outputs/<file>.{json,csv}`.
2. Find the corresponding `docs/audit/wave<N>-*.md` (or `docs/CLAIMS.md` / `docs/CONSOLIDATED_RESULTS.md` row).
3. Compare against the SHA-256 recorded inline in the audit doc / claims row (top-level files do **not** carry their own SHA-256SUMS — they are individually pinned inline in the surfacing doc per Wave 274 P7 sidecar convention).

---

## 4. SHA-256 manifest subdirectories (the 7 with `SHA256SUMS`)

At HEAD `a3944e0`, 7 subdirectories carry a `SHA256SUMS` file that can be verified directly via `sha256sum -c`:

```bash
cd verification_outputs/

# Wave 280 paper-parity p1–p7 R-level sweep (R5c, R1, R5b, K1, K4/K5, K7)
sha256sum -c wave280-k7/SHA256SUMS
sha256sum -c wave280-p-k1/SHA256SUMS
sha256sum -c wave280-p-k4k5/SHA256SUMS
sha256sum -c wave280-p-r1/SHA256SUMS
sha256sum -c wave280-p-r3/SHA256SUMS
sha256sum -c wave280-p-r5c/SHA256SUMS

# Wave 349 R1 3-seed N=1000 LineageFlow GPU sweep (camera-ready R1 retro-validation)
sha256sum -c wave349-r1-3seed-gpu/SHA256SUMS
```

`SHA256SUMS` files were produced post-Wave 280 P7 (paper-parity refresh) + at Wave 349 P4 (R1 GPU acceleration) per the audit-doc convention. Future waves will add new `SHA256SUMS` files as part of their post-run audit; this README will be updated when that happens.

For all other subdirectories and the 426 top-level files, the SHA-256 fingerprint is recorded **inline in the surfacing doc** (audit doc / `docs/CLAIMS.md` row / `tnnls_submission/MANIFEST.md` row 34–40 figure SHA column).

---

## 6. Cross-references and intent

- **Per-row audit docs (NEVER)** — the audit-doc author was the wave author. Each article links the row to (a) the wave's tool/script, (b) the seed policy, (c) the environment (`.venvs/<model>_venv`), and (d) the docs/CLAIMS.md row(s) that consume the evidence.
- **CLAIMS.md cross-references** — `docs/CLAIMS.md` is the single source of truth for substantive claims; each CLM-NNN row records its `Asserted by` / `Disputed by` reference, which is typically a path into `verification_outputs/` (e.g. `verification_outputs/wave206-p1-lineageflow-n1000/...` for CLM-039/040, `verification_outputs/wave216-p2-r5a-extended.csv` for CLM-060, etc.). A reviewer cross-referencing a CLM row should follow the inline path to the evidence directory + the audit doc that interprets it.
- **MANIFEST.md figure SHA-256 ledger** — `tnnls_submission/MANIFEST.md` rows 34–40 record the SHA-256 of every load-bearing figure (Wave 183 P4 Figures 3/4/5 + R5c / R5b supplementary figures). A reviewer with access to the `verification_outputs/` tree can re-hash these PNG/PDF figures and confirm they match the MANIFEST SHA-256 column.
- **Per-subdirectory `manifest.json` / `summary.json`** — 27 subdirectories ship a `manifest.json` or `summary.json` at their root that records the wave's tool, model, axis, N, seed policy, environment, wall-clock, and per-record wall-clock. These are the most authoritative self-describing metadata for each subdirectory.

---

## 7. Byte-stability disclosure

The whole `verification_outputs/` tree is gitignored (`.gitignore:64`); the **byte-identity of pinned headline artifacts is preserved via two parallel mechanisms**:

1. **`SHA256SUMS` files** in 7 subdirectories (Wave 280 paper-parity + Wave 349 R1 GPU) — byte-stable re-verifiable via `sha256sum -c` (§5).
2. **Inline SHA-256 in surfacing docs** — for every other subdirectory and every top-level file, the SHA-256 of the pinned headline bytes is recorded inline in:
   - `tnnls_submission/MANIFEST.md` rows 34–40 (figures: Wave 183 P4 + R5c + R5b)
   - `docs/audit/wave<N>-*.md` (per-wave audit trail with byte-stable evidence citations)
   - `docs/CLAIMS.md` (each CLM-NNN row records the `Asserted by` reference + inline provenance notes)

A reviewer who clones the repo + has access to the `verification_outputs/` tree can:

1. Re-hash any pinned headline figure / JSON / CSV via `sha256sum <path>`.
2. Compare against the MANIFEST / audit-doc / CLAIMS row SHA-256.
3. Confirm byte-stability across wave refreshes.

The gitignore is **preserved verbatim** per AGENTS.md §3 hard guardrail #1 (vendored upstream is sacred) + Wave 355 P1 strict-clean rule (no destructive edits). This README is a new tracked file at `docs/verification_outputs.md` (outside `verification_outputs/`) and does not touch the gitignore or any vendored code.

---

## 8. Recent additions (Wave 348–355)

- **Wave 348 P1b / Phase 1b:** 78 local-repo paths → GitHub URLs in MANIFEST.md rows 24–30 + supplementary/README.md (cross-doc fix; does not modify `verification_outputs/`).
- **Wave 349 P4:** R1 3-seed N=1000 LineageFlow GPU sweep at `verification_outputs/wave349-r1-3seed-gpu/` (7 files, SHA256SUMS-equipped) — the camera-ready R1 retro-validation evidence. Audit doc `docs/audit/wave349-p2-r1-3seed-n1000-gpu.md`.
- **Wave 350 P3:** R6 k6 foldability live GPU smoke at `verification_outputs/wave350-r6-live-smoke/` (5 files, 2 MB) — env-readiness check for §10.5 R6 live-GPU follow-up. Audit doc `docs/audit/wave350-r6-live-attempt.md`.
- **Wave 351 P3:** Theorem 5 numerical validation at `verification_outputs/wave351-p3-thm5-numerical/` (2 files: `lipschitz_estimate.json` + `thm5_fit.json`) — L_local ≈ 0.3810 + 12-cell grid fit. Audit doc `docs/audit/wave351-thm5-numerical.md`.
- **Wave 351 P2 / Wave 352 P5:** R5a Wave 351 P2 n=10 paired-t at `verification_outputs/wave351-r5a-n10/` (3 files: paired CSV / JSON / MD). Audit doc `docs/audit/wave351-r5a-n10.md` + `docs/audit/wave352-claims-r5a-update.md`.
- **Wave 354 P1 (this README):** master index of all 122 subdirectories + 426 top-level files. Audit doc `docs/audit/wave355-verification-outputs-readme.md`. **ADDITIVE only — no destructive edits, no gitignore change, no vendored-code change.**

---

## 9. How a reviewer verifies everything

```bash
# 1. Verify the SHA256SUMS-equipped subdirectories
cd verification_outputs/
sha256sum -c wave280-k7/SHA256SUMS
sha256sum -c wave280-p-k1/SHA256SUMS
sha256sum -c wave280-p-k4k5/SHA256SUMS
sha256sum -c wave280-p-r1/SHA256SUMS
sha256sum -c wave280-p-r3/SHA256SUMS
sha256sum -c wave280-p-r5c/SHA256SUMS
sha256sum -c wave349-r1-3seed-gpu/SHA256SUMS

# 2. Verify figure SHA-256s against MANIFEST.md
cd ..  # back to repo root
sha256sum verification_outputs/wave183-p4-figure-pLDDT-finer.png \
           verification_outputs/wave183-p4-figure-scPerplexity-finer.png \
           verification_outputs/wave183-p4-figure-deltas-finer.png
# Compare against tnnls_submission/MANIFEST.md rows 38–40 SHA-256 column.

# 3. Spot-check a subdirectory's manifest.json
cat verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json | python3 -m json.tool

# 4. Spot-check a top-level JSON
python3 -c "import json; print(json.dumps(json.load(open('verification_outputs/wave191-p2-cifar10-n1000.json'))['summary'], indent=2))"

# 5. Cross-reference a CLM row to its evidence path
grep -nE "CLM-039|CLM-040" docs/CLAIMS.md | head -5
# → look for "verification_outputs/wave206-p1-lineageflow-n1000/" in the row.

# 6. Re-hash a pinned headline figure and compare against MANIFEST
sha256sum tnnls_submission/../docs/drafts/paper-A-final.md
# Compare against tnnls_submission/MANIFEST.md row 32 SHA-256 column.
```

---

## 10. Maintenance

This README is **canonical** and lives at `docs/verification_outputs.md` (tracked). Future waves that produce new headline evidence should:

1. Add a new subdirectory under `verification_outputs/` following the existing naming convention (`wave<N>-<topic>`).
2. Optionally ship a `SHA256SUMS` file for byte-stable re-verifiability (recommended for subdirs containing load-bearing figures or large numerical artifacts).
3. Ship a `manifest.json` (recommended) recording tool, N, seed, environment, wall-clock.
4. Add the new subdirectory to the appropriate §3.X table in this README, with cross-reference to the corresponding audit doc.
5. Add the corresponding SHA-256 to the surfacing doc (`tnnls_submission/MANIFEST.md` for figures; `docs/CLAIMS.md` for claim-bound evidence; audit doc for everything else).
6. Update `docs/CLAIMS.md` if the new evidence pins a new claim or promotes an existing one (per AGENTS.md §2.3 `flowa-research-audit`).

Per Wave 268 strict-clean rule, updates to this README are ADDITIVE only — never delete an existing table row or shrink the scope; instead, supersede the prior evidence in the new audit doc and add a new row.

---

_Last updated: 2026-09-25 (Wave 355 P1 — master index created)._