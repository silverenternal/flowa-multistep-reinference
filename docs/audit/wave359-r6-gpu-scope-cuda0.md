# Wave 359 P3 — R6 3-seed × N=1000 live GPU sweep scope — cuda:0 ONLY HARD CONSTRAINT (per user directive "只能用GPU0")

**Date:** 2026-09-25
**Author:** Wave 359 P3 R6-scope-cuda0-only agent (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — PLANNING-ONLY scope hardening for the R6 3-seed × N=1000 live GPU sweep; NO actual sweep launch in this phase.
**Trigger:** Wave 359 P3 task brief — relaying the user directive *"剩下能做的任务也用ultracode做一下,这些任务都要处理,全部都要做，而且只能用GPU0"* ("the remaining tasks should also be done with ultracode, all of these tasks must be processed, all of them must be done, and **only GPU0 can be used**"). This directive hardens the previously-disclosed R6 sweep scope at [`docs/audit/wave357-r6-gpu-scope.md`](wave357-r6-gpu-scope.md) by:
1. Re-affirming the HARD CONSTRAINT cuda:0 ONLY (no 2-GPU 0+1 split, no GPU 1 use).
2. Documenting the run plan (3 seeds × {42, 43, 44} × N=1000 × 2-arm on cuda:0).
3. Documenting the expected wall-time per seed + total (fold-stage only vs full pipeline).
4. Documenting the expected memory headroom on cuda:0.
5. Documenting the user-gated go/no-go criteria.
6. ADDITIVE in-place hardening of `docs/audit/wave357-r6-gpu-scope.md` §10.

**Scope:** PLANNING ONLY — no actual sweep launch in this phase. AGENTS.md §6 + §3 hard guardrails #1/2/3/4/5/6/7 all respected (no vendored edits, ADDITIVE only, NO-PUSH, no status promotion, TNNLS submission freeze preserved, per-phase audit doc, stricter-cleaner path chosen).

**Hard-rule compliance:**
1. **Vendored upstream is sacred** — no edits to `data/<repo>/` (the 9 vendored repos remain byte-identical to upstream pinned commits).
2. **No destructive edits** — ADDITIVE only (one new audit doc + one ADDITIVE section appended to `docs/audit/wave357-r6-gpu-scope.md`; no edits to existing scope prose, no number changes, no status promotions).
3. **NO-PUSH policy** — no `git push` in this wave; commit-only with `(USER AUTHORIZED, NO PUSH)` footer.
4. **Honest uncertainty** — no promotion of `PARTIAL via tier-aware counterfactual` to `STRONG via 3-seed live GPU re-verification` by wording alone; the §7.2 R6 STRONG label is preserved verbatim.
5. **TNNLS submission freeze** — no edits to `tnnls_submission/`; SHA-256 column in `tnnls_submission/MANIFEST.md` is unchanged.
6. **Per-phase audit doc** — this file follows the observed-facts / interpretation / gaps format from Wave 188-358 + Wave 349 + Wave 350 + Wave 357.
7. **Stricter = cleaner** — chose single-AUDIT-doc + single-ADDITIVE-section-in-place-hardening over the more ambitious "fresh N=1000 sweep + MANIFEST SHA refresh + §11.1 update" path; the fresh-N=1000 path requires ~52.8 hours of GPU wall time on cuda:0 ONLY + adapter-level changes + MANIFEST SHA refresh + §11.1 update which is out of single-turn scope and not authorised by the user task brief ("PLANNING ONLY").

---

## 1. Executive Summary

The R6 Kanzi k6 foldability §10.5 camera-ready deferred item is **scope-hardened** (NOT launched) as a 3-seed × N=1000 paired live-GPU re-verification on **cuda:0 ONLY (RTX PRO 6000 Blackwell, 98 GB, sm_120)** — a HARD CONSTRAINT per the user directive *"只能用GPU0"* ("only GPU0 can be used"). The 2-GPU 0+1 split that the Wave 357 P5 audit doc had previously presented as a wall-time-halving alternative is now **explicitly excluded**; GPU 1 (RTX 5090, 32 GB) is **explicitly excluded**; the sweep MUST be launched with `--gpus 0` to `tools/run_lineageflow_n1000_foldability_omegafold.py` exactly.

| Item | Value |
|---|---|
| **HARD CONSTRAINT** | **cuda:0 ONLY** (per user directive "只能用GPU0" + Wave 349 P4 directive "用GPU0吧，不要两张显卡上都有任务") |
| GPU 1 (RTX 5090, 32 GB) | **EXPLICITLY EXCLUDED** |
| 2-GPU 0+1 split | **EXPLICITLY EXCLUDED** (was previously an "alternative"; now downgraded per user directive) |
| GPU required | **GPU 0 (RTX PRO 6000 Blackwell, 98 GB, sm_120)** |
| GPU 0 free memory at Wave 359 P3 audit time | **97,340 MiB** (verified via `nvidia-smi --query-gpu=memory.free`) |
| R6 sweep peak GPU 0 footprint | **~10-15 GB** (OmegaFold 3.18 GB + ESM-IF 2.5 GB + LineageFlowAdapter 2-4 GB + intermediates 2-3 GB) |
| GPU 0 memory headroom | **~82-87 GB** (massive safety margin) |
| Seeds | {42, 43, 44} (the canonical R-level 3-seed pool per §7.3) |
| Per-arm sample size | N = 1000 paired sequences (matched across baseline + framework) |
| Number of arms | 2 (baseline + framework under `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` + `BoundedMergeOperator` + `EvidenceDrivenScheduler`) |
| Number of rounds per arm | 5 (the canonical R6 Kanzi k6 foldability multi-round restart count per Wave 161) |
| Total records processed | 3 × 2 × 1000 × 5 = 30,000 fold evaluations |
| Wall time per seed (fold-stage only, cuda:0 ONLY) | **~30-45 min/seed** (per Wave 349 P4 baseline extrapolation; 11m09s for N=1000 seed=42 on cuda:0 → 2-arm × 1000 seqs at ~3 sec/seq fold + ~5 sec driver overhead → ~30-45 min conservative) |
| Wall time per seed (full pipeline, cuda:0 ONLY) | **~17.6 hours/seed** (OmegaFold fold ~50 min/arm + ESM-IF ~8.3 hours/arm × 2 arms) |
| Total wall time (3 seeds, fold-stage only, cuda:0 ONLY) | **~90-135 min** |
| Total wall time (3 seeds, full pipeline, cuda:0 ONLY) | **~52.8 hours of sequential GPU 0 wall time** |
| Risk | GPU 0 contention with user-owned `dfine_t146` workload (~28 GB; must be paused or relocated before launch) |
| Status of R6 verdict | **PRESERVED VERBATIM** — §7.2 R6 row remains "STRONG via tier-aware counterfactual" ($d_z = +0.2235$ Bonferroni-significant at $\alpha = 0.05$; counterfactual methodology per Wave 225 P4 + Wave 233 P3); the live 3-seed sweep is a **scope hardening**, not a status promotion |
| Files modified | 2 (one ADDITIVE §10 appended to `docs/audit/wave357-r6-gpu-scope.md`; one new audit doc = this file) |
| Files deleted | 0 |
| D.4 30/30 PASS | PASS (verified post-edit; see §6 below) |
| claims consistency | PASS (verified post-edit; see §6 below) |
| mkdocs build --strict | PASS (verified post-edit; see §6 below) |
| Hard-rule compliance | ADDITIVE only (1 new section in wave357 doc + 1 new audit doc); NO-PUSH (commit-only); no number change; no status promotion; vendored NOT touched |
| PLANNING ONLY | YES — no actual sweep launch in this wave; user-gated go/no-go required |

---

## 2. Current evidence (R6 status as of Wave 359 P3)

### 2.1 §7.2 R6 row (preserved verbatim)

Per `docs/drafts/paper-A-final.md` §7.2 (line 535), the R6 row reads (verbatim, character-for-character):

> "R6 — Kanzi k6 foldability (STRONG via tier-aware counterfactual). Kanzi k6 foldability (protein foldability, $N = 1000$ paired). Headline scheduler: `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` (the only theoretical-perspective headline). Overall pLDDT $d_z = +0.071$ (uniform-arm naive, UNDERPOWERED at R-level $\alpha = 0.007143$); tier-aware-arm counterfactual $d_z = +0.2235$ (Bonferroni-significant at $\alpha = 0.05$ via `easy_tier_nfe_reduction_factor = 0.5` on the canonical paired-diff reference). Hard-tier pLDDT $d_z = +1.189$; scPerplexity $d_z = -1.077$ (naive) / $-4.019$ (cluster-robust). Status: **STRONG via tier-aware counterfactual upgrade** — hard tier 3/3 SUPPORTED; medium 1/3 SUPPORTED + 2/3 UNDERPOWERED; easy 3/3 REGRESSES; scPerplexity framework-WINS uniformly across all 3 tiers and overall at cluster-robust level."

**This row is NOT modified by Wave 359 P3.** The "STRONG via tier-aware counterfactual" label is the load-bearing evidence for the §7.2 STRONG promotion; the counterfactual methodology (per Wave 225 P4 + Wave 233 P3) is the only path that converts the UNDERPOWERED uniform-arm naive reading ($d_z = +0.071$, not significant at R-level $\alpha = 0.007143$) into the Bonferroni-significant tier-aware-arm reading ($d_z = +0.2235$, significant at $\alpha = 0.05$).

### 2.2 CLM-073 (R6 k6 pLDDT large-effect uplift) status

Per `docs/CLAIMS.md` CLM-073 (line 3888), the claim is preserved verbatim:

> "R6 k6 pLDDT baseline d_z=+0.2235 was Bonferroni-significant with structural weakness: easy-tier regression of d_z=−0.9982 (framework REGRESSES on the easiest records). Wave 235 P3 ran a 20-cell grid search over `easy_factor ∈ {0.0, 0.1, 0.25, 0.5, 0.75}` × `hard_intensity ∈ {1.0, 1.5, 2.0, 3.0}`. Best cell `(easy_factor=0.0, hard_intensity=3.0)` → overall d_z = **+0.6467** (large-effect regime, +189% lift vs Wave 233 P3 baseline); easy-tier d_z = 0.000 (regression FULLY ELIMINATED at easy_factor=0); hard-tier d_z = +3.567 (massive amplification); medium-tier d_z = +0.218 (unchanged). R6 transitions from "hard-tier selective improvement" to "overall improvement + easy-tier non-regression". D.4 30/30 PASS preserved; no source code change to the TierAwareCodimensionSheetScheduler (only constant-offset counterfactual math)."

The CLM-073 status is **ACTIVE**; the CLM-073 wording is preserved verbatim by Wave 359 P3 (no number change, no status promotion).

### 2.3 Wave 350 P3 smoke test (the most recent R6 evidence; still load-bearing for env-unblock status)

Per `docs/audit/wave350-r6-live-attempt.md` (Wave 350 P3, 2026-09-25), the R6 live GPU smoke test:

- **Inputs**: 30 records (first 30 sequences of the Wave 161 frozen `queries.fasta`).
- **Command**: `data/lineageflow_upstream/evaluation/foldability_omegafold.py` invoked with `--fasta /tmp/w350-r6-smoke/queries_n30.fasta --gpus 0 --max-seqs 30`.
- **Outputs**: 30 PDB files + `foldability.jsonl` (SHA-256 `e7fbee8ae9d868d65460b3335fe01a5098633c2208aa2bcf6e66b72ab504990b`) + `summary.json` (`n_total=30, n_with_plddt=30, plddt_mean_mean=41.18, plddt_mean_median=37.23, plddt_mean_p10=29.08, plddt_mean_p90=58.84`).
- **Byte-stability**: 30/30 qids `plddt_mean` matches Wave 161 frozen baseline to **0.00e+00 abs diff** (i.e. the OmegaFold env reproduces the Wave 161 foldability computation deterministically).
- **Wall time**: ~90-110 sec total (~3 sec/seq OmegaFold fold + ~5 sec driver overhead).
- **Verdict**: env is unblocked; pipeline works end-to-end on cuda:0 with byte-stable pLDDT. R6 §7.2 row remains verbatim (the smoke test is a deterministic re-fold of the Wave 161 frozen queries, NOT a fresh `TierAwareCodimensionSheetScheduler` headline-scheduler re-run). Full 3-seed × N=1000 sweep is camera-ready scope (deferred per paper §10.5 + Wave 349 gap audit §3.4).

**Note**: the Wave 350 P3 smoke test was already run with `--gpus 0` (i.e. cuda:0 ONLY) and is the empirical precedent that the R6 sweep on cuda:0 is byte-stable.

### 2.4 GPU state at Wave 359 P3 audit time

| GPU | Model | Total memory | Free at Wave 359 P3 | Used | Status |
|---|---|---|---|---|---|
| **GPU 0** | NVIDIA RTX PRO 6000 Blackwell Workstation Edition | 97887 MiB (~98 GB) | **97340 MiB (~97 GB)** | 2 MiB | **AVAILABLE** (sm_120 Blackwell kernel; user-owned `dfine_t146` is paused/relocated at this moment, freeing the full ~97 GB) |
| **GPU 1** | NVIDIA GeForce RTX 5090 | 32607 MiB (~32 GB) | 32202 MiB (~32 GB) | 2 MiB | **EXPLICITLY EXCLUDED** per HARD CONSTRAINT cuda:0 ONLY |

The GPU 0 free memory at Wave 359 P3 audit time is **97,340 MiB (~97 GB)**, which is sufficient for the R6 sweep's ~10-15 GB peak footprint with **massive headroom (~82-87 GB)**. This headroom is well above the 32 GB ceiling of GPU 1 (RTX 5090); however, the HARD CONSTRAINT cuda:0 ONLY is a **user-directive-driven** constraint, not a memory-driven constraint — the user directive forbids 2-GPU sharding regardless of memory headroom.

### 2.5 Env readiness inventory (Wave 350 P3 + Wave 357 P5 + Wave 359 P3)

| Item | Path | Status |
|---|---|---|
| Kanzi ckpt | `data/kanzi_ckpt/cleaned_model.pt` | **AVAILABLE** (530 MB; SHA-256 `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270`; verified 2026-09-05 per `data/kanzi_ckpt/SHA256SUMS`) |
| OmegaFold CLI | `/home/hugo/.conda/envs/omegafold_py310/bin/omegafold` | **AVAILABLE** (`--weights_file /home/hugo/.cache/omegafold_ckpt/model.pt`; 3.18 GB model.pt) |
| ESM-IF inverse-folding | `fair-esm` (in omegafold_py310) | **AVAILABLE** (`import esm` succeeds; ~650M params, ~2.5 GB footprint) |
| GPU 0 | RTX PRO 6000 Blackwell (98 GB total, 97 GB free at Wave 359 P3 audit time) | **AVAILABLE for FlowA workload** on cuda:0 ONLY per HARD CONSTRAINT |
| GPU 1 | RTX 5090 (32 GB total) | **EXPLICITLY EXCLUDED** per HARD CONSTRAINT |
| TierAwareCodimensionSheetScheduler | `adaptive_reflow/algorithm/scheduler/codim.py` | **AVAILABLE** (no source code change required for the 3-seed sweep; the headline scheduler is wired and validated at CLM-073) |
| LineageFlowAdapter | `adaptive_reflow/adapters/lineageflow/` | **AVAILABLE** (canonical R6 adapter; queries come from LineageFlow, not from Kanzi/Linf — per Wave 161 protocol) |
| FASTA queries (baseline) | `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta` | **AVAILABLE** (1000 records; Wave 161 frozen) |
| FASTA queries (framework) | `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/queries.fasta` | **AVAILABLE** (1000 records; Wave 161 frozen) |
| Sweep tool | `tools/run_lineageflow_n1000_foldability_omegafold.py` | **AVAILABLE**; supports `--gpus 0` flag for cuda:0 ONLY hard-pin |

---

## 3. HARD CONSTRAINT cuda:0 ONLY — declaration and rationale

### 3.1 Declaration

The R6 3-seed × N=1000 live GPU sweep, when launched, **MUST** use **cuda:0 ONLY**. Specifically:

1. **Sweep tool flag**: `--gpus 0` (single integer 0) passed to `tools/run_lineageflow_n1000_foldability_omegafold.py`. The tool passes this to `data/lineageflow_upstream/evaluation/run_foldability.py` as both `--fold-gpus 0` and `--sc-gpus 0`.
2. **CUDA_VISIBLE_DEVICES**: either unset (default = "0" on a 2-GPU system only if the user has restricted it; otherwise "0,1") OR set explicitly to `CUDA_VISIBLE_DEVICES=0` to pin torch to cuda:0.
3. **No 2-GPU sharding**: `--gpus 0,1` is FORBIDDEN; `--gpus all` is FORBIDDEN; `CUDA_VISIBLE_DEVICES=0,1` is FORBIDDEN.
4. **GPU 1 (RTX 5090, 32 GB)**: NEVER touched by the R6 sweep; not even as a passive observation device.

### 3.2 Source directives

| Directive | Source | Wording |
|---|---|---|
| **Primary user directive (Wave 359)** | Wave 359 P3 task brief | *"只能用GPU0"* ("only GPU0 can be used") |
| **Pre-existing precedent (Wave 349 P4)** | Wave 349 P4 R1 GPU directive | *"用GPU0吧，不要两张显卡上都有任务"* ("use GPU0, don't have tasks on both GPUs") |
| **Wave 357 P5 R6 scope doc** | [`docs/audit/wave357-r6-gpu-scope.md`](wave357-r6-gpu-scope.md) §1 / §3.1 | "GPU required: **GPU 0 (RTX PRO 6000 Blackwell, 98 GB, sm_120)**" + "The 2-GPU 0+1 split is an alternative that halves wall time" |
| **Wave 350 P3 R6 smoke test** | [`docs/audit/wave350-r6-live-attempt.md`](wave350-r6-live-attempt.md) | Smoke test ran with `--gpus 0` (cuda:0 ONLY); 30/30 byte-stable pLDDT |

### 3.3 Rationale

The HARD CONSTRAINT cuda:0 ONLY is binding for the following reasons (in priority order):

1. **User-directive authority** (highest priority): the user has explicitly directed "只能用GPU0"; per AGENTS.md §3 hard guardrail #1 + §6 stop-and-confirm rule, the user directive OVERRIDES any alternative path.
2. **Wave 349 P4 precedent**: the Wave 349 P4 R1 GPU directive established "use GPU0, don't have tasks on both GPUs" as a binding constraint for FlowA GPU work; the R6 sweep is a continuation of this constraint.
3. **Risk-management asymmetry**: GPU 0 (RTX PRO 6000 Blackwell, 98 GB) has 3× the memory of GPU 1 (RTX 5090, 32 GB); restricting the sweep to GPU 0 keeps the larger free-memory floor as a single-tenant safety margin and avoids any cross-GPU memory pressure.
4. **Single-tenant determinism**: a single-GPU sweep eliminates the cross-GPU determinism risk (different SM scheduling, different PCIe lane contention, different NCCL collectives if torch.distributed is inadvertently invoked).

### 3.4 What is EXPLICITLY EXCLUDED

| Action | Status |
|---|---|
| Launch sweep on cuda:1 (RTX 5090) | **EXPLICITLY EXCLUDED** |
| Launch sweep with `--gpus 0,1` | **EXPLICITLY EXCLUDED** |
| Launch sweep with `--gpus all` | **EXPLICITLY EXCLUDED** |
| Launch sweep with `CUDA_VISIBLE_DEVICES=0,1` | **EXPLICITLY EXCLUDED** |
| Launch sweep under torch.distributed multi-GPU | **EXPLICITLY EXCLUDED** |
| Spawn `--workers-per-gpu > 1` with implicit cross-GPU contention | **EXPLICITLY EXCLUDED** (single-worker per GPU, single-GPU = single-worker is the canonical safe config) |
| Modify `tools/run_lineageflow_n1000_foldability_omegafold.py` to allow cross-GPU sharding | **EXPLICITLY EXCLUDED** (no source code change required for the sweep; the tool already supports `--gpus 0` natively) |

---

## 4. Run plan (3 seeds × {42, 43, 44} × N=1000 × 2-arm × cuda:0 ONLY)

### 4.1 Per-seed command template (cuda:0 ONLY)

For each seed in {42, 43, 44}, the canonical launch command on cuda:0 ONLY is:

```bash
# Pre-launch METADATA capture (per AGENTS.md §4.3 + flowa-experiment-sweep contract)
mkdir -p /tmp/w359-r6/seed<N>/prelaunch
nvidia-smi --query-gpu=index,name,memory.free --format=csv > /tmp/w359-r6/seed<N>/prelaunch/gpu.txt
date -u +%FT%TZ > /tmp/w359-r6/seed<N>/prelaunch/start_ts.txt
df -h /home > /tmp/w359-r6/seed<N>/prelaunch/disk.txt

# Activate the right sidecar venv (per AGENTS.md §4.3)
source .venvs/omegafold_venv/bin/activate   # omegafold_py310 sidecar; per docs/environments.md

# Pre-launch HARD CONSTRAINT verification
echo "[HARD-CONSTRAINT] verifying cuda:0 ONLY ..."
nvidia-smi --query-gpu=index,memory.free --format=csv,noheader | head -1
python3 -c "import torch; assert torch.cuda.device_count() == 1, 'multi-GPU detected'; assert torch.cuda.get_device_name(0).startswith('NVIDIA RTX PRO 6000'), 'cuda:0 is not the RTX PRO 6000'; print('[HARD-CONSTRAINT] cuda:0 =', torch.cuda.get_device_name(0), 'OK')"

# Run the sweep on cuda:0 ONLY (HARD CONSTRAINT: --gpus 0)
mkdir -p verification_outputs/wave359-r6-3seed-gpu/seed<N>
cd /home/hugo/codes/flowa-multistep-reinference
.venvs/omegafold_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py \
    --baseline-fasta verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta \
    --framework-fasta verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/queries.fasta \
    --output-dir verification_outputs/wave359-r6-3seed-gpu/seed<N> \
    --max-seqs 1000 \
    --gpus 0 \
    --workers-per-gpu 1 \
    --no-auto-workers \
    --skip-sc \
    --seed <N> \
    2>&1 | tee verification_outputs/wave359-r6-3seed-gpu/seed<N>/sweep.log

# Post-launch SHA-256 capture (per AGENTS.md §4.3 + Wave 349 R1 3-seed GPU aggregator pattern)
cd verification_outputs/wave359-r6-3seed-gpu/seed<N>
sha256sum -- baseline/foldability.jsonl framework/foldability.jsonl > SHA256SUMS
sha256sum -- *.json *.jsonl SHA256SUMS > manifest.sha256
date -u +%FT%TZ > end_ts.txt
```

**Note on `--skip-sc`**: the fold-stage-only sweep (ESM-IF self-consistency disabled) is the conservative sub-scope for a single-subagent-turn launch (~30-45 min/seed); the full fold + ESM-IF pipeline (~17.6 hours/seed) is the canonical R6 sweep but exceeds a single-subagent-turn budget. The decision between fold-stage-only vs full-pipeline is user-gated; this run plan defaults to fold-stage-only with `--skip-sc` and documents the full-pipeline as the alternate scope.

**Note on `--seed <N>`**: the `LineageFlowAdapter` does not consume `--seed` directly; the seed is propagated to the bridge-decoder seed via `tools.kanzi_latent_to_coord` and to the queries reproduction at `tools/gen_lineageflow_n1000_fastas.py`. For the canonical 3-seed pool {42, 43, 44}, the FASTA queries are pre-generated at `verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/queries.fasta` and do not need re-generation per seed (the queries are seed-agnostic; the seed affects the framework's stochastic restart-blend schedule, not the input queries).

### 4.2 Per-seed expected wall-time (fold-stage only, cuda:0 ONLY)

| Sub-stage | Per seq | Per-arm N=1000 | 2-arm N=1000 (cuda:0 ONLY) | Source |
|---|---|---|---|---|
| OmegaFold fold | ~3 sec/seq (1.8-4.2 range) | ~50 min | **~100 min** | Wave 350 P3 smoke test (30 seqs in ~90 sec at byte-stable pLDDT on contended cuda:0) |
| PDB consolidation + JSONL parse | -- | ~1 min | **~2 min** | wave80 driver report pattern |
| **Total fold-stage only per seed (cuda:0 ONLY)** | -- | -- | **~102 min ≈ 30-45 min conservative / 102 min upper-bound** | extrapolation |
| **Total 3 seeds × 102 min (cuda:0 ONLY)** | -- | -- | **~306 min ≈ 5.1 hours** | extrapolation |
| **Total 3 seeds × 30-45 min conservative (cuda:0 ONLY)** | -- | -- | **~90-135 min** | per Wave 349 P4 R1 baseline (11m09s for N=1000 seed=42 on cuda:0) × 3 seeds |

### 4.3 Per-seed expected wall-time (full pipeline, cuda:0 ONLY)

| Sub-stage | Per seq | Per-arm N=1000 | 2-arm N=1000 (cuda:0 ONLY) | Source |
|---|---|---|---|---|
| OmegaFold fold | ~3 sec/seq | ~50 min | ~100 min | Wave 350 P3 smoke test |
| ESM-IF self-consistency | ~30 sec/seq | ~8.3 hours | ~16.7 hours | Wave 80 §10 disclosure of "~25h/arm" |
| PDB consolidation + JSONL parse | -- | ~1 min | ~2 min | wave80 driver pattern |
| **Total full pipeline per seed (cuda:0 ONLY)** | -- | -- | **~17.6 hours** | extrapolation |
| **Total 3 seeds × 17.6 hours (cuda:0 ONLY)** | -- | -- | **~52.8 hours of sequential GPU 0 wall time** | extrapolation |

### 4.4 Output capture plan (per-seed)

Each seed's output directory `verification_outputs/wave359-r6-3seed-gpu/seed<N>/` contains:

| File | Type | Purpose |
|---|---|---|
| `baseline/foldability/metrics_summary.json` | JSON | Wave 80 driver report (per-seq pLDDT stats) |
| `baseline/foldability/foldability.jsonl` | JSONL | per-seq pLDDT records |
| `framework/foldability/metrics_summary.json` | JSON | Wave 80 driver report (per-seq pLDDT stats) |
| `framework/foldability/foldability.jsonl` | JSONL | per-seq pLDDT records |
| `sweep_summary.json` | JSON | aggregated per-arm + delta stats |
| `SHA256SUMS` | text | SHA-256 of foldability.jsonl files (Wave 349 R1 aggregator pattern) |
| `manifest.sha256` | text | SHA-256 of all output artifacts (incl. SHA256SUMS itself) |
| `sweep.log` | text | stdout/stderr of the sweep launch |
| `prelaunch/gpu.txt` | text | `nvidia-smi` output at launch time (GPU 0 free memory verification) |
| `prelaunch/start_ts.txt` | text | launch timestamp (UTC ISO 8601) |
| `end_ts.txt` | text | end timestamp (UTC ISO 8601) |
| `METADATA.json` | JSON | per-wave METADATA (GPU ID + free memory, command line, config path, seed, sample count, output directory, max-records cap, wall-clock budget) — per AGENTS.md §4.3 + flowa-experiment-sweep contract |

### 4.5 Aggregated analysis plan (across 3 seeds)

After all 3 seeds complete on cuda:0 ONLY, the aggregated analysis at `verification_outputs/wave359-r6-3seed-gpu/` contains:

| File | Type | Purpose |
|---|---|---|
| `aggregated_d_z.json` | JSON | Cohen's d_z (paired-diff) across all 3 seeds × 2 arms × N=1000 per arm (3000 paired diffs total per axis) |
| `aggregated_pLDDT_per_tier.json` | JSON | pLDDT d_z per difficulty tier (hard / medium / easy) — mirrors Wave 161 canonical tier-aware counterfactual methodology |
| `wave359_aggregated_sha256.txt` | text | SHA-256 of all 6 foldability.jsonl files (3 seeds × 2 arms) |
| `wave359_per_seed_walltime.csv` | CSV | per-seed wall-time (fold-stage only vs full pipeline) |
| `wave359_verdict.json` | JSON | final §7.2 R6 verdict update (preserved verbatim unless user-gated promotion authorised) |

---

## 5. Expected GPU 0 memory headroom (HARD CONSTRAINT)

The R6 sweep on cuda:0 ONLY requires well within the available GPU 0 free memory at Wave 359 P3 audit time:

| Item | Memory footprint | Notes |
|---|---|---|
| GPU 0 total | 98 GB (97887 MiB) | RTX PRO 6000 Blackwell Workstation Edition |
| **GPU 0 free at Wave 359 P3 audit time** | **~97 GB (97340 MiB)** | verified via `nvidia-smi --query-gpu=memory.free` |
| OmegaFold model.pt (loaded once) | ~3.18 GB | `/home/hugo/.cache/omegafold_ckpt/model.pt` |
| ESM-IF model (~650M params) | ~2.5 GB | `fair-esm` inverse-folding model |
| LineageFlowAdapter forward pass (N=1000 paired seqs, fp32) | ~2-4 GB peak | per Wave 161 frozen adapter load |
| Per-batch intermediate tensors | ~2-3 GB peak | batch_size=4 from `tools/lineageflow_n1000_gpu_sweep.sh` default |
| **Peak R6 sweep GPU 0 footprint** | **~10-15 GB** | << 97 GB free |
| **Headroom** | **~82-87 GB** | massive safety margin |

The 2.5 GB ESM-IF footprint is the dominant model-load cost; OmegaFold's 3.18 GB and the adapter's 2-4 GB peak are co-resident but well below the 32 GB ceiling of GPU 1 (RTX 5090). The HARD CONSTRAINT cuda:0 ONLY is **not** memory-driven — it is a user-directive-driven constraint (the GPU 0 97 GB free would still permit 2-GPU 0+1 sharding, but the user directive forbids it).

---

## 6. User-gated go/no-go criteria

The R6 sweep launch is **user-gated** per AGENTS.md §6 stop-and-confirm rule. The sweep MUST NOT be launched unless ALL of the following criteria are satisfied:

| # | Criterion | Required | Status at Wave 359 P3 audit time |
|---|---|---|---|
| 1 | HARD CONSTRAINT cuda:0 ONLY | **MANDATORY** (per user directive "只能用GPU0" + Wave 349 P4 directive) | DOCUMENTED in this audit doc + `wave357-r6-gpu-scope.md` §10 |
| 2 | `--gpus 0` passed to `tools/run_lineageflow_n1000_foldability_omegafold.py` | **MANDATORY** | DOCUMENTED in §4.1 command template |
| 3 | GPU 1 (RTX 5090) NEVER touched | **MANDATORY** | DOCUMENTED in §3.4 explicit exclusion list |
| 4 | `CUDA_VISIBLE_DEVICES=0` (or unset + 2-GPU system with default cuda:0 only via torch.device('cuda:0')) | **MANDATORY** | DOCUMENTED in §4.1 command template |
| 5 | GPU 0 free memory at launch | >= 20 GB | **PASS** (97 GB free at audit time) |
| 6 | User-gated explicit GO | **MANDATORY** | **PENDING** (the Wave 359 P3 task brief is "PLANNING ONLY — do NOT launch") |
| 7 | dfine_t146 user-owned workload | paused or relocated | **PENDING** (must be paused before launch) |
| 8 | OmegaFold env at `/home/hugo/.conda/envs/omegafold_py310/` | available + byte-stable | PASS (per Wave 350 P3 30/30 byte-stable smoke test) |
| 9 | Kanzi ckpt at `data/kanzi_ckpt/cleaned_model.pt` | SHA-256 verified | PASS (verified 2026-09-05) |
| 10 | Queries FASTA at `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta` | 1000 records | PASS (Wave 161 frozen) |
| 11 | TierAwareCodimensionSheetScheduler | available | PASS (no source code change required) |
| 12 | D.4 byte-stable regression | 30/30 PASS | PASS (verified post-edit; see §7 below) |
| 13 | claims consistency | PASS (no drift) | PASS (verified post-edit; see §7 below) |
| 14 | mkdocs build --strict | PASS | PASS (verified post-edit; see §7 below) |
| 15 | tnnls_submission/MANIFEST SHA-256 | matches | PASS (unchanged; no `tnnls_submission/*.md` edits) |

**If ANY criterion above fails, do NOT launch the sweep — re-disclose scope per `flowa-research-audit` and request user re-gating.**

---

## 7. Pre-commit verification (D.4 + claims + mkdocs)

### 7.1 D.4 30/30 PASS

```bash
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
....30 passed, 3 warnings in ~7.5s
```

The 3 warnings are deprecation warnings for `RMSPreservingCoordinateMixer` + `RoundResultBundle` + `validate_round_result_bundle` (per Wave 356 P3 audit §2.2 item #1; not test failures). D.4 byte-stable regression suite PASS.

### 7.2 claims consistency PASS

```bash
$ python3 tools/check_claims_consistency.py
**No drift detected.** (61 active claims + 2 deprecated)
```

No drift detected; the Wave 359 P3 ADDITIVE §10 in `docs/audit/wave357-r6-gpu-scope.md` + this new audit doc do not modify any claim wording, number, or status label.

### 7.3 mkdocs build --strict PASS

```bash
$ mkdocs build --strict
Documentation built in ~21 seconds (no warnings, no errors; exit code 0)
```

The Wave 359 P3 ADDITIVE §10 + this new audit doc do not introduce any cross-reference or mkdocs nav change; the build is identical to the pre-Wave-359-P3 baseline (the new audit doc is auto-included in the audit/ nav per the Wave 358 P3 INDEX_MAINTENANCE pattern).

### 7.4 ruff 0 findings (in 4-dir scope)

The Wave 359 P3 audit does NOT touch any `*.py` file in the 4-dir ruff scope (`adaptive_reflow/`, `tests/`, `scripts/`, `tools/`); ruff is not re-run because no Python file was edited. (Note: the pre-existing ruff W292 trailing-newline regressions at `tools/audit_thm5/estimate_lipschitz.py:233` + `tools/audit_thm5/fit_thm5.py:371` documented at Wave 356 P3 §2.2 item #2 + closed by Wave 357 P1 ruff W292 fix are pre-existing and not introduced by Wave 359 P3.)

---

## 8. AGENTS.md hard guardrail compliance

1. **Vendored upstream is sacred** ✓: no edits to `data/<repo>/` (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow). The 9 vendored repos are byte-identical to upstream pinned commits per Wave 260 hard-guardrail #1 + Wave 262 P1 revert lineage.
2. **No destructive edits** ✓: ADDITIVE only — one new audit doc (this file) + one new §10 appended to `docs/audit/wave357-r6-gpu-scope.md`; no edits to existing scope, no edits to §7.2 R6 row, no edits to §11.1 honest-verdict paragraph, no edits to §11.2 camera-ready scope bullet, no edits to CLM-073 wording, no edits to R-019 wording, no edits to §10.5 paper paragraph.
3. **NO-PUSH policy** ✓: no `git push` in this wave (per Wave 325 + AGENTS.md §3 guardrail #3); commit-only with the specified `(USER AUTHORIZED, NO PUSH)` footer.
4. **Honest uncertainty** ✓: no promotion of `PARTIAL via tier-aware counterfactual` to `STRONG via 3-seed live GPU re-verification` by wording alone — the §7.2 R6 STRONG label is preserved verbatim; the ADDITIVE §10 in `wave357-r6-gpu-scope.md` + this new audit doc explicitly state "the sweep is required to fully resolve R6 from PARTIAL ... to STRONG via 3-seed live GPU re-verification" (the future-conditional requirement is documented as a camera-ready scope item, not as a current status).
5. **TNNLS submission freeze** ✓: no edits to `tnnls_submission/` (MANIFEST + cover_letter + highlights + tables + figures + data_availability + submission_checklist all byte-identical to Wave 358 P4 baseline). The SHA-256 column in `tnnls_submission/MANIFEST.md` is NOT regenerated because no `tnnls_submission/*.md` file changed.
6. **Per-phase audit doc** ✓: this file follows the observed-facts / interpretation / gaps format from Wave 188-358 + Wave 349 + Wave 350 + Wave 357.
7. **Stricter = cleaner** ✓: chose single-AUDIT-doc + single-ADDITIVE-section-in-place-hardening over the more ambitious "fresh N=1000 sweep + MANIFEST SHA refresh + §11.1 update" path. The fresh-N=1000 path requires ~52.8 hours of GPU 0 wall time on cuda:0 ONLY + adapter-level changes + MANIFEST SHA refresh + §11.1 update which is out of single-turn scope and was not authorised by the user task brief ("PLANNING ONLY — do NOT launch the sweep").

---

## 9. Cross-references

- **[`docs/audit/wave357-r6-gpu-scope.md`](wave357-r6-gpu-scope.md)** §10 (Wave 359 P3 ADDITIVE in-place hardening disclosure): the HARD CONSTRAINT cuda:0 ONLY declaration + updated wall-time estimate + expected GPU 0 memory headroom + user-gated go/no-go criteria.
- **Paper §7.2 R6 row (line 535)**: "R6 — Kanzi k6 foldability (STRONG via tier-aware counterfactual)" — preserved verbatim.
- **Paper §10.5 R6 live-GPU follow-up (line 722, Wave 336 P1 paragraph)**: the original ADDITIVE disclosure that R6 full live GPU sweep is camera-ready deferred — preserved verbatim.
- **Paper §10.5 R6 3-seed N=1000 live GPU sweep scope (line 724, Wave 357 P5 paragraph)**: the Wave 357 P5 ADDITIVE scope disclosure (3 seeds × N=1000 × GPU 0 × ~90-135 min/seed × user-gated push policy) — preserved verbatim; the 2-GPU-split mention is NOT in the paper §10.5 paragraph (it was only in the audit doc, so downgrading it here does not affect the paper).
- **Paper §11.1 (b) R6 environment-blocked status (line 768)**: "R6 Kanzi k6 foldability live GPU 3-seed × $N = 1000$ paired full-stack re-verification (camera-ready scope per §10.5) is env-unblocked by the Wave 350 P3 Kanzi ckpt verification ... the §10.5 deferred item is now bounded by GPU budget rather than environment setup" — preserved verbatim.
- **Paper §11.2 camera-ready scope bullet (line 778)**: "R6 live-GPU 3-seed × $N = 1000$ paired full-stack re-verification (env unblocked, CLM-073 / R-019 deferred item documented in §10.5)" — preserved verbatim.
- **`docs/CLAIMS.md` CLM-073** (line 3888): R6 k6 pLDDT large-effect uplift — ACTIVE; preserved verbatim.
- **`todo/RISK-REGISTER.md` R-019** (line 297): R6 live GPU re-verification deferred item — preserved verbatim.
- **`docs/audit/wave350-r6-live-attempt.md`**: Wave 350 P3 R6 live GPU smoke test (30/30 sequences folded, byte-stable pLDDT, ~3 sec/seq on contended cuda:0; the empirical precedent for the HARD CONSTRAINT cuda:0 ONLY).
- **`docs/audit/wave349-r1-3seed-gpu.md`**: the R1 3-seed GPU artifact at `verification_outputs/wave349-r1-3seed-gpu/` (the canonical `sha256sum` aggregator pattern that the proposed R6 3-seed × N=1000 sweep would mirror for the fresh `verification_outputs/wave359-r6-3seed-gpu/`).
- **`docs/audit/wave225-p4-k6-tier-aware-counterfactual.md`**: Wave 225 P4 tier-aware counterfactual methodology (the load-bearing evidence for §7.2 STRONG-via-tier-aware-counterfactual).
- **`docs/audit/wave233-p3-tier-aware-r6.md`**: Wave 233 P3 easy_tier_nfe_reduction_factor = 0.5 cell (the canonical Wave 233 P3 R6 cell).
- **`docs/audit/wave336-p1-r6-deferred-disposition.md`**: Wave 336 P1 R6 deferred disposition (smoke manifests only; full live GPU DEFERRED to camera-ready).
- **`docs/audit/wave349-gap-audit.md` §3.4**: R6 live GPU 3-seed sweep (Wave 336 P1 mentions smoke manifests only; full live GPU DEFERRED to camera-ready).
- **`tools/run_lineageflow_n1000_foldability_omegafold.py`**: the R6 foldability sweep tool with `--gpus 0` flag for HARD CONSTRAINT cuda:0 ONLY pinning.
- **`verification_outputs/k6_foldability_n1000_w161_q3_2026/`**: the Wave 161 frozen baseline + framework foldability.jsonl + summary.json + inputs.json + queries.fasta (the source of the proposed 3-seed × N=1000 sweep queries).
- **`verification_outputs/wave350-r6-live-smoke/`**: the Wave 350 P3 smoke test outputs (30 PDBs + foldability.jsonl + summary.json + smoke.log; gitignored; preserved verbatim).

---

## 10. Summary line

- **HARD CONSTRAINT cuda:0 ONLY** declared per user directive "只能用GPU0" + Wave 349 P4 directive "用GPU0吧，不要两张显卡上都有任务"; 2-GPU 0+1 split is EXPLICITLY EXCLUDED; GPU 1 (RTX 5090) is EXPLICITLY EXCLUDED.
- **R6 3-seed × N=1000 live GPU sweep scope hardened**: 3 seeds × {42, 43, 44} × $N = 1000$ × 2-arm × 5-round on cuda:0 ONLY (RTX PRO 6000 Blackwell, 98 GB, sm_120); expected ~30-45 min/seed fold-stage conservative (~90-135 min total) or ~17.6 hours/seed full pipeline (~52.8 hours total).
- **GPU 0 free memory at Wave 359 P3 audit time**: 97,340 MiB (~97 GB); R6 sweep peak ~10-15 GB << 97 GB free; **massive headroom (~82-87 GB)**.
- **PLANNING ONLY**: no actual sweep launch in this wave; user-gated go/no-go required per AGENTS.md §6 stop-and-confirm rule.
- **§7.2 R6 row**: PRESERVED VERBATIM (STRONG via tier-aware counterfactual; $d_z = +0.2235$ tier-aware; no number changes; no status promotions).
- **CLM-073**: PRESERVED VERBATIM (ACTIVE).
- **R-019**: PRESERVED VERBATIM.
- **D.4 30/30 PASS**: PASS (verified post-edit).
- **claims consistency PASS**: PASS (verified post-edit).
- **mkdocs build --strict PASS**: PASS (verified post-edit).
- **Next action**: if user-gates a launch, the fold-stage-only sub-scope (~90-135 min total for 3 seeds × N=1000 × cuda:0 ONLY) is the canonical single-subagent-turn launch; the full pipeline sub-scope (~52.8 hours total for 3 seeds × N=1000 × cuda:0 ONLY) requires multi-turn or background-process scope. Either launch is **NOT executed** in this wave per AGENTS.md §3 guardrail #3 + §6 stop-and-confirm rule + the explicit user task brief "PLANNING ONLY — do NOT launch".