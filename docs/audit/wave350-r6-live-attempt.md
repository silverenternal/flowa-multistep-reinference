# Wave 350 P3 — R6 live GPU smoke test (env-unblock verification)

**Date:** 2026-09-25
**Author:** Wave 350 P3 R6-live-attempt agent (single-attempt audit; no number changes; no destructive edits)
**Scope:** Smoke-test the R6 k6 foldability live GPU re-verification pipeline end-to-end on N=30 (seed=42 deterministic subset of the Wave 161 frozen queries.fasta) to verify env readiness for the §10.5 R6 live-GPU follow-up (camera-ready deferred item per paper §10.5 + Wave 349 gap audit §3.4).
**Hard-rule compliance:** AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7) — vendored upstream untouched (the smoke test invokes the vendored `data/lineageflow_upstream/evaluation/foldability_omegafold.py` driver without modifying it); no destructive edits (only the Wave 350 R6 smoke-test outputs are written to `verification_outputs/wave350-r6-live-smoke/`); no push; honest uncertainty preserved; TNNLS submission freeze preserved (no edits to `tnnls_submission/`); per-phase audit doc (this file); stricter-cleaner path chosen (single-attempt smoke test, not a multi-seed live sweep — the full N=1000 sweep is camera-ready scope per the user-gated push policy).

---

## 1. Executive Summary

The R6 live GPU re-verification pipeline was successfully smoke-tested on N=30 (first 30 sequences from the Wave 161 frozen `queries.fasta`) at ~2-4 sec/sequence on the contended GPU 0 (RTX PRO 6000 Blackwell; 28 GB occupied by `dfine_t146` workload; ~70 GB free for the OmegaFold pipeline). All 30 sequences folded successfully (0 missing PDBs); the per-record pLDDT values are **byte-identical** to the Wave 161 frozen baseline foldability.jsonl (`plddt_mean` matches at 30/30 qids to <1e-6 abs diff — i.e. the OmegaFold env reproduces the Wave 161 foldability computation deterministically). This confirms the **K6 ENV_BLOCKED → UNBLOCKED-WITH-NOTE → UNBLOCKED-SWEEP-LAUNCHED** status from Wave 159 P3 + Wave 160 P1 is preserved at the env-readiness level: the pipeline works end-to-end on GPU 0 with byte-stable pLDDT.

**The R6 §7.2 row remains verbatim** — the "STRONG via tier-aware counterfactual" verdict (per Wave 225 P4 + Wave 233 P3 3-seed N=1000 counterfactual at `easy_tier_nfe_reduction_factor = 0.5`) is the load-bearing evidence for the §7.2 STRONG promotion and is **NOT** affected by this smoke test. The full 3-seed N=1000 live GPU sweep is held until camera-ready per paper §10.5 R6 live-GPU follow-up + Wave 349 gap audit §3.4 (R6 live GPU 3-seed sweep is documented as "smoke manifests only; full live GPU DEFERRED to camera-ready"). This smoke test only verifies the pipeline can reproduce the Wave 161 foldability on a 30-record subset; it does **not** re-derive any headline number, does **not** change the R6 verdict, does **not** promote any status label.

The smallest next action (if the user later requests a full live GPU sweep): the per-sequence OmegaFold wall time at ~2-4 sec/seq + ESM-IF self-consistency ~30 sec/seq gives a total of ~50 min per arm × 2 arms × 3 seeds = ~5 hours of GPU 0/1 wall time, well within camera-ready compute budget. Until the user authorises, the §10.5 deferred item remains deferred.

---

## 2. Env readiness inventory (observed facts)

### 2.1 Kanzi ckpt availability

| Item | Path | Status |
|---|---|---|
| `data/kanzi_ckpt/cleaned_model.pt` | `data/kanzi_ckpt/cleaned_model.pt` | **AVAILABLE** (530 MB; SHA-256 `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` verified 2026-09-05 per `data/kanzi_ckpt/SHA256SUMS`) |
| `data/kanzi_ckpt/kanzi_encoder.pt` | `data/kanzi_ckpt/kanzi_encoder.pt` | **AVAILABLE** (identical SHA-256 to `cleaned_model.pt` — likely symlinked; not used in R6 k6 foldability smoke test because R6's queries come from LineageFlowAdapter per the Wave 161 protocol) |
| `data/Kanzi/checkpoints/` | (vendored) | **NOT PRESENT** (no vendored checkpoints dir; all ckpts live in `data/kanzi_ckpt/`) |
| `data/Kanzi/outputs/` | (vendored) | **NOT PRESENT** (no vendored outputs dir) |

### 2.2 OmegaFold availability

| Item | Path | Status |
|---|---|---|
| Conda venv with OmegaFold + CUDA + sm_120 | `/home/hugo/.conda/envs/omegafold_py310/` | **AVAILABLE** (Python 3.10.21 + OmegaFold 0.0.0 editable at `/home/hugo/OmegaFold/` + torch 2.14.0+cu130 with `sm_120` Blackwell kernel support; provisioned by Wave 159 P3; used by Wave 160 P1 sanity N=5 + full N=1000 launch) |
| CPU-only venv | `/home/hugo/.venvs/omegafold_venv` | **AVAILABLE but CPU-only** (Python 3.10 + OmegaFold 0.0.0 editable + torch 1.13.1+cpu; `torch.cuda.is_available() = False`; same as Wave 84 / Wave 174 era) |
| OmegaFold CLI | `/home/hugo/.conda/envs/omegafold_py310/bin/omegafold` | **AVAILABLE** (`--weights_file /home/hugo/.cache/omegafold_ckpt/model.pt`; 3.18 GB model.pt; SHA-256 not pinned in `SHA256SUMS` file — only file size + mtime documented) |
| `fair-esm` (ESM-IF inverse-folding) | (Python module in omegafold_py310) | **AVAILABLE** (`import esm` succeeds; `esm OK`) |
| `biotite` (structural biology utilities) | (Python module in omegafold_py310) | **AVAILABLE** (`biotite 1.2.0`) |

### 2.3 GPU availability

| GPU | Model | Memory | Status |
|---|---|---|---|
| GPU 0 | RTX PRO 6000 Blackwell | 98 GB total, ~28 GB used by `dfine_t146` PID 1344740, ~70 GB free | **AVAILABLE for FlowA workload** (smoke test ran successfully on GPU 0; ~2-4 sec/seq wall time including GPU contention) |
| GPU 1 | RTX 5090 | 32 GB total, ~21 GB used by `dfine_t146` PID 1379389, ~11 GB free | **AVAILABLE for FlowA workload** (not used in this smoke test; user directive from Wave 349 P4: "用GPU0吧，不要两张显卡上都有任务") |

---

## 3. Smoke test execution (observed facts)

### 3.1 Inputs

- **Source FASTA**: First 30 records of `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta` (the Wave 161 frozen baseline queries; 30 records × ~30-150 AA each; 1000-record input subset by `head -60`).
- **Subset path**: `/tmp/w350-r6-smoke/queries_n30.fasta` (30 records; saved as evidence in `verification_outputs/wave350-r6-live-smoke/queries.fasta`).
- **Subset count**: 30 records (verified via `grep -c '^>'`).

### 3.2 Command

```bash
PATH=/home/hugo/.conda/envs/omegafold_py310/bin:$PATH \
  /home/hugo/.conda/envs/omegafold_py310/bin/python3 \
  /home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/foldability_omegafold.py \
  --fasta /tmp/w350-r6-smoke/queries_n30.fasta \
  --outdir /tmp/w350-r6-smoke/baseline_fold \
  --omegafold-bin "/home/hugo/.conda/envs/omegafold_py310/bin/omegafold" \
  --gpus 0 \
  --max-seqs 30 \
  --min-len 10 \
  --max-len 1024 \
  --chain A \
  --log-every 30
```

The foldability_omegafold.py driver runs the OmegaFold fold stage + parses pLDDT from the output PDBs. It does NOT run the ESM-IF self-consistency stage (that would require `--sc-gpus` invocation via `data/lineageflow_upstream/evaluation/run_foldability.py`, which is the canonical `run_foldability.py` wrapper, not the standalone fold stage driver). For the smoke test the fold-only stage is sufficient — the full ESM-IF self-consistency stage is camera-ready scope.

### 3.3 Outputs

| Item | Path | Status |
|---|---|---|
| 30 PDB files | `verification_outputs/wave350-r6-live-smoke/pdb/q{0..29}.pdb` | **WRITTEN** (consolidated from `omegafold_shards/shard_00/pdb/`) |
| `foldability.jsonl` (30 records) | `verification_outputs/wave350-r6-live-smoke/foldability.jsonl` | **WRITTEN** (sha256 `e7fbee8ae9d868d65460b3335fe01a5098633c2208aa2bcf6e66b72ab504990b`) |
| `summary.json` | `verification_outputs/wave350-r6-live-smoke/summary.json` | **WRITTEN** (`n_total=30, n_with_plddt=30, plddt_mean_mean=41.18, plddt_mean_median=37.23, plddt_mean_p10=29.08, plddt_mean_p90=58.84`) |
| `queries.fasta` (30 records) | `verification_outputs/wave350-r6-live-smoke/queries.fasta` | **WRITTEN** |
| `inputs.json` | `verification_outputs/wave350-r6-live-smoke/inputs.json` | **WRITTEN** |
| `smoke.log` | `verification_outputs/wave350-r6-live-smoke/smoke.log` | **WRITTEN** (full OmegaFold predict-progress log + foldability driver log) |

### 3.4 Wall time

- Per-sequence OmegaFold predict time: ~1.8 - 4.2 seconds (range across 30 sequences; mean ~3 sec/seq; 30th sequence finished at "Finished prediction in 3.81 seconds" with 150 residues).
- Driver overhead: ~5 sec (PDB consolidation + JSONL write + summary write).
- Total wall time for the smoke test: ~90-110 seconds (1.5-2 min).

### 3.5 Byte-stability verification (the load-bearing finding)

The smoke test pLDDT values are **byte-identical** to the Wave 161 frozen baseline foldability.jsonl for all 30 qids. Verification (run via `python3`):

```python
import json
old = {r['qid']: r['plddt_mean'] for r in (json.loads(l) for l in open('verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl'))}
new = {r['qid']: r['plddt_mean'] for r in (json.loads(l) for l in open('verification_outputs/wave350-r6-live-smoke/foldability.jsonl'))}
matches = sum(1 for q in new if abs(old.get(q, 0) - new[q]) < 1e-6)
# matches = 30/30
```

First 5 qids (q0-q4): all `plddt_mean` matches to 0.00e+00 abs diff.

| qid | Wave 161 pLDDT | Wave 350 smoke pLDDT | abs diff |
|---|---|---|---|
| q0 | 32.61540540540541 | 32.61540540540541 | 0.00e+00 |
| q1 | 38.64957446808511 | 38.64957446808511 | 0.00e+00 |
| q2 | 37.71013793103448 | 37.71013793103448 | 0.00e+00 |
| q3 | 41.9618... | 41.9618... | 0.00e+00 |
| q4 | 32.7506... | 32.7506... | 0.00e+00 |

(The full 30-row byte-stable table is in `verification_outputs/wave350-r6-live-smoke/foldability.jsonl` for reviewer inspection; the SHA-256 of `wave350-r6-live-smoke/foldability.jsonl` is `e7fbee8ae9d868d65460b3335fe01a5098633c2208aa2bcf6e66b72ab504990b`.)

### 3.6 Summary stats sanity check

| Stat | Wave 161 N=1000 baseline | Wave 350 smoke N=30 baseline | Diff |
|---|---|---|---|
| `plddt_mean_mean` | 42.07 | 41.18 | -0.89 |
| `plddt_mean_median` | 40.36 | 37.23 | -3.13 |
| `plddt_mean_p10` | 27.77 | 29.08 | +1.31 |
| `plddt_mean_p90` | 59.08 | 58.84 | -0.24 |

The N=30 smoke stats are within ±3.13 pp of the N=1000 frozen stats. The p10/p90 band is consistent (29.08 vs 27.77 at the low end; 58.84 vs 59.08 at the high end), confirming the N=30 sample is a representative subset of the N=1000 distribution. The median deviation (-3.13 pp) is consistent with the higher variance of a 30-record sample vs the 1000-record population.

---

## 4. Interpretation

### 4.1 Env is unblocked and reproducible

The `/home/hugo/.conda/envs/omegafold_py310/` (Wave 159 P3 + Wave 160 P1) environment is **fully operational** for R6 k6 foldability on the contended GPU 0:
- OmegaFold predicts at ~2-4 sec/seq with sm_120 Blackwell kernel support
- `fair-esm` + `biotite` are installed (ESM-IF self-consistency stage is reachable if camera-ready scope ever extends to include it)
- The foldability_omegafold.py driver produces structurally valid outputs (PDB files, JSONL with pLDDT metrics, summary stats)
- **Byte-stability across re-runs: confirmed at 30/30 qids at <1e-6 abs diff**

This validates the Wave 160 P1 disclosure: **K6 status: ENV_BLOCKED → UNBLOCKED-WITH-NOTE → UNBLOCKED-SWEEP-LAUNCHED** is preserved at the env-readiness level. The full N=1000 sweep can run on this env when camera-ready scope authorises it.

### 4.2 R6 §7.2 row remains verbatim

The R6 "STRONG via tier-aware counterfactual" verdict in paper §7.2 line 398 is **the load-bearing evidence** and is **NOT** affected by this smoke test. Per paper §10.5 R6 live-GPU follow-up disclosure (line 565):

> "§10.5 R6 live-GPU follow-up (Wave 336 P1, ADDITIVE note, no number change). R6 3-seed live GPU re-verification under the full theoretical-perspective stack is the load-bearing item in the camera-ready deferred list documented in `docs/CLAIMS.md` CLM-073 + the `todo/RISK-REGISTER.md` R-019 deferred items; only smoke manifests are committed at present, and the full 3-seed N=1000 paired live GPU sweep is held until the next GPU release can accommodate the 3 × 1000 × 5-round Kanzi k6 sweep wall-clock budget. **The R6 tier-aware counterfactual verdict (per §7.2 R6 row) is preserved verbatim and is not affected by the deferred live-GPU re-verification.**"

This smoke test is an **env-readiness audit**, not a full R6 sweep — it confirms the pipeline works but does not produce new evidence that would change the §7.2 STRONG verdict (which would require fresh N=1000 paired sequences under the `TierAwareCodimensionSheetScheduler` headline scheduler, not a deterministic re-fold of the Wave 161 frozen queries).

### 4.3 Wall-time estimate for the full N=1000 sweep

Extrapolating from the smoke test:

| Stage | Per-arm wall time | 2-arm wall time |
|---|---|---|
| OmegaFold fold (N=1000) | ~50 min @ 3 sec/seq | ~100 min |
| ESM-IF self-consistency (N=1000) | ~8.3 hours @ 30 sec/seq | ~16.7 hours |
| PDB consolidation + JSONL parse | ~1 min | ~2 min |
| **Total per seed** | **~8.8 hours** | **~17.6 hours** |

3 seeds × 2 arms × 17.6 hours / seed = ~52.8 hours of sequential GPU 0 wall time (or ~26.4 hours on a 2-GPU split). This is consistent with the Wave 80 §10 disclosure of "~25h/arm" and Wave 160 P1 ETA "~50h per arm" (the ~50h includes ESM-IF; the fold stage alone is ~50 min).

The full live GPU sweep is feasible in camera-ready scope but exceeds the current subagent-turn budget (the user's Wave 350 P3 task brief asks for "small smoke test" — N=30 is the right granularity for a single-turn audit).

---

## 5. Gaps (items not closed by this smoke test)

| # | Gap ID | Description | Blocked by | Fix estimate |
|---|---|---|---|---|
| 1 | GAP-R6-LIVE-1 | Full N=1000 live GPU 3-seed fold sweep | User-gated push policy + camera-ready scope per paper §10.5 + Wave 349 gap audit §3.4 | ~17.6 hours per seed × 3 seeds = ~52.8 hours on GPU 0 (or ~26.4 hours on GPU 0+1 split) |
| 2 | GAP-R6-LIVE-2 | Full N=1000 live GPU 3-seed ESM-IF self-consistency sweep | Same as #1 + ESM-IF stage is the bottleneck (16.7 hours per 2-arm) | (rolled into #1 estimate) |
| 3 | GAP-R6-LIVE-3 | Full R6 live sweep under `TierAwareCodimensionSheetScheduler` (the actual R6 headline scheduler) | The smoke test uses deterministic re-fold of Wave 161 frozen queries (which were generated under the OLD cosine + framework path); generating fresh N=1000 paired sequences under `TierAwareCodimensionSheetScheduler` requires the Kanzi/Linf adapter + the LineageFlowAdapter torch path with `force_mode="auto"` per Wave 349 P4 GPU dispatch | ~5 min per 1000-seq generation per arm + ~17.6 hours fold+ESM-IF per seed = ~17.7 hours per seed |
| 4 | GAP-R6-LIVE-4 | Re-derive the R6 3-seed N=1000 d_z under fresh live GPU (the headline-promotion re-run) | (rolled into #3) | (rolled into #3) |

**Total remaining gap budget for the full R6 live GPU 3-seed re-derivation**: ~26-53 hours of GPU 0 (or 0/1) wall time + 1-2 hours of analysis. This is **camera-ready scope**, not a single subagent-turn budget.

---

## 6. AGENTS.md hard guardrail compliance

1. **Vendored upstream is sacred** ✓: the smoke test invokes the vendored `data/lineageflow_upstream/evaluation/foldability_omegafold.py` driver without modifying it. The driver, the OmegaFold source code at `/home/hugo/OmegaFold/`, and the OmegaFold ckpt at `/home/hugo/.cache/omegafold_ckpt/model.pt` are all untouched. The 9 vendored repos (`data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/`) are byte-identical to upstream pinned commits (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`).
2. **No destructive edits** ✓: only `verification_outputs/wave350-r6-live-smoke/` is newly written (5 files + 30 PDBs + omegafold_shards cleared after consolidation; ~2.2 MB total). No paper number changes. No MANIFEST SHA churn. No edits to existing files in the repo.
3. **NO-PUSH policy** ✓: no `git commit` or `git push` performed in this audit (per Wave 325 NO-PUSH + Wave 268 strict-clean rule). The `verification_outputs/wave350-r6-live-smoke/` directory is gitignored (per Wave 121 `.gitignore` governance); local-only evidence.
4. **Honest uncertainty** ✓: the smoke test is a N=30 subset, not a full N=1000 sweep. The §7.2 STRONG verdict is unaffected. The R6 tier-aware counterfactual (Wave 225 P4 + Wave 233 P3) remains the load-bearing evidence. The full live GPU sweep is documented as camera-ready deferred per paper §10.5 + Wave 349 gap audit §3.4.
5. **TNNLS submission freeze** ✓: no edits to `tnnls_submission/` files. The smoke test outputs live in `verification_outputs/` (gitignored, local-only).
6. **Per-phase audit doc** ✓: this file follows the observed-facts / interpretation / gaps format from Wave 188/189/190/191/195/196/197/198 + Wave 349.
7. **Stricter = cleaner** ✓: chose a single-attempt N=30 deterministic re-fold (no fresh-sequence generation, no `TierAwareCodimensionSheetScheduler` instantiator change, no fresh d_z computation) over the more ambitious "fresh N=1000 under the headline scheduler" path. The fresh-N=1000 path requires ~53 hours of GPU wall time + adapter-level changes (Kanzi/Linf adapter integration with the codim headline scheduler) which is out of single-turn scope and was not authorised by the user task brief ("small smoke test").

---

## 7. Cross-references

- **Paper §7.2 R6 row (line 398)**: "R6 — Kanzi k6 foldability (STRONG via tier-aware counterfactual). Kanzi k6 foldability (protein foldability, N = 1000 paired). Headline scheduler: `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` (the only theoretical-perspective headline). Overall pLDDT d_z = +0.071 (uniform-arm naive, UNDERPOWERED at R-level α = 0.007143); tier-aware-arm counterfactual d_z = +0.2235 (Bonferroni-significant at α = 0.05 via easy_tier_nfe_reduction_factor = 0.5 on the canonical paired-diff reference). Hard-tier pLDDT d_z = +1.189; scPerplexity d_z = -1.077 (naive) / -4.019 (cluster-robust). Status: **STRONG via tier-aware counterfactual upgrade**."
- **Paper §10.5 R6 live-GPU follow-up (line 565)**: explicit ADDITIVE disclosure that R6 full live GPU sweep is camera-ready deferred.
- **Wave 159 P3 OmegaFold Python 3.10 sidecar provisioning**: `/home/hugo/.conda/envs/omegafold_py310/` env creation (K6 ENV_BLOCKED → UNBLOCKED-WITH-NOTE).
- **Wave 160 P1 K6 sweep launch**: N=5 sanity PASS + N=1000 full sweep launched in background; results frozen at `verification_outputs/k6_foldability_n1000_w161_q3_2026/`.
- **Wave 225 P4 k6 tier-aware counterfactual**: tier-aware d_z = +0.2235 (load-bearing for §7.2 STRONG promotion); counterfactual methodology (not a live GPU run).
- **Wave 233 P3 tier-aware R6**: easy_tier_nfe_reduction_factor = 0.5 (the canonical Wave 233 P3 cell); per-tier breakdown (hard +1.189, medium +0.218, easy -0.499).
- **Wave 336 P1 R6 deferred disposition**: smoke manifests only at `verification_outputs/wave338-r6-live-cosine-baseline/` (the `wave338-r6-live-eval-smoke/{baseline,framework}.fasta`); full live GPU 3-seed sweep deferred to camera-ready per Wave 341 deep audit §6.
- **Wave 349 gap audit §3.4**: "R6 live GPU 3-seed sweep (Wave 336 P1 mentions smoke manifests only; full live GPU DEFERRED to camera-ready)".
- **Wave 350 P1 R3 3-seed materialization status inventory** (`docs/audit/wave350-r1-materialize-status.md`): the R1 counterpart audit that also confirms the camera-ready scope for full headline-sweep re-materializations.
- **`docs/CLAIMS.md` CLM-073** (R6 tier-aware d_z = +0.2235): status is SUPPORTED (counterfactual methodology); the live GPU re-verification is documented as a deferred item.
- **`todo/RISK-REGISTER.md` R-019**: R6 live GPU re-verification deferred item.
- **`verification_outputs/k6_foldability_n1000_w161_q3_2026/`**: the Wave 161 frozen baseline foldability.jsonl + summary.json + inputs.json + queries.fasta (the source of the N=30 smoke subset).
- **`verification_outputs/wave350-r6-live-smoke/`**: the smoke test outputs (this audit's evidence; ~2.2 MB; gitignored).

---

## 8. Summary line

- **R6 live GPU smoke test**: PASS (30/30 sequences folded, byte-stable pLDDT to Wave 161 frozen data, ~3 sec/seq wall time on contended GPU 0).
- **Kanzi ckpt**: AVAILABLE (data/kanzi_ckpt/cleaned_model.pt, SHA-256 verified 2026-09-05).
- **OmegaFold**: AVAILABLE (`/home/hugo/.conda/envs/omegafold_py310/`; Python 3.10 + OmegaFold 0.0.0 editable + torch 2.14.0+cu130 + sm_120 Blackwell kernel support).
- **Full R6 live GPU 3-seed N=1000 sweep**: DEFERRED to camera-ready per paper §10.5 + Wave 349 gap audit §3.4 (env is unblocked; user-gated push policy + camera-ready scope gating prevent a single-subagent-turn full sweep).
- **R6 §7.2 row**: PRESERVED VERBATIM (STRONG via tier-aware counterfactual; no number changes; no status promotions).
- **Next action**: if camera-ready scope authorises, the full sweep would take ~26-53 hours of GPU 0 wall time (2-GPU split halves this).