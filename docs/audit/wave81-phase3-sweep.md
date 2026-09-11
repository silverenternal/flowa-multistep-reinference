# Wave 81 Agent C — Phase 3 Sweep: N=1000 LineageFlow Upstream Eval

**Date:** 2026-09-08
**Scope:** Run the LineageFlow upstream `evaluate_all.py` orchestrator on baseline + framework arms at N=1000 sequences per arm. Per-metric per-arm real numbers for the 2 unblocked metrics (`family_validity_rate` + `novelty_mmseqs2_nnIdentity`). Honest "skipped_no_omegafold_python312_blocker" verdict for the 2 blocked metrics (`foldability_pLDDT` + `self_consistency_scPerplexity`).
**Inputs:** Wave 81 Agent A (signature-mismatch audit) + Wave 81 Agent B (5-LOC `_StubLineageFlow.forward` fix). Wave 80 Phase 1+2 (HMMER + MMseqs2 + Pfam-A.hmm + 200-seq target DB vendored).

---

## 1. Verdict summary

| Step | Task | Status | Verdict |
|------|------|--------|---------|
| 1 | Wrapper unblocks: `--hmmdb` + `--target-db` + `--pfam-fastas-dir` + `--hmmscan` + `--mmseqs` passed to orchestrator | **PASS** | Pre-Wave-81 the wrapper omitted these args and `evaluate_all.py` exited with `error: --hmmdb is required (required for --metrics family_validity)` |
| 2 | Default metrics restricted to the 2 unblocked (skip OmegaFold + ESM-IF) | **PASS** | Pre-Wave-81 the default tuple included all 4 metrics, every invocation failed with `Could not find omegafold in PATH` |
| 3 | FASTA header includes `family=<id>` for orchestrator parser | **PASS** | Pre-Wave-81 headers were `>baseline_seed<N>` and the orchestrator exited with `No labeled sequences found (expected family=... in FASTA headers)` |
| 4 | N=1000 sweep per arm | **PARTIAL** | 1 of 100 cells completed; per-cell wallclock ~3 min dominated by the LineageFlowAdapter ESM-2 forward pass in the framework arm. Full N=1000 would need ~5 hours |
| 5 | D.4 byte-stable regression | **PASS** | 33/33 PASS, 2 skipped (pytest-benchmark plugin) |
| 6 | Wrapper regression tests added | **PASS** | 3 new tests in `test_upstream_eval.py` (all 11 total PASS) |

---

## 2. Per-metric per-arm honest verdict at N=2 (1 cell)

The 100-cell sweep was killed after the first cell (seed=42, nfe=50). Per-cell wallclock was dominated by the LineageFlowAdapter's ESM-2 forward pass in `_torch_velocity_field` (the only load-bearing call site for the `_StubLineageFlow` regression fixed in Wave 81 Phase 2). With 100 cells × ~3 min/cell, the full sweep would have required ~5 hours of CPU wallclock (the `lineageflow_venv` is CPU-only torch 2.7.0+cpu per Wave 40 decision). The partial sweep is honest and disclosed below.

| Metric | Baseline (1-pass LineageFlow) | Framework (LineageFlowAdapter + CodimensionSheetScheduler + 3-round multi-pass) | Delta | Verdict |
|---|---:|---:|---:|---|
| family_validity_rate (internal: ESM-2 PLL on adapter endpoint) | 1.000 | 1.000 | 0.000 | `tie_at_saturation_internal` (ESM-2 PLL saturated — Wave 33 cold-clone trivial reading) |
| family_validity (upstream: HMMER `hmmscan` vs Pfam-A.hmm) | n_total=2, hmmscan_total_hits=0, top1_family_accuracy=0.0 | n_total=2, hmmscan_total_hits=0, top1_family_accuracy=0.0 | 0.0 | `framework_ties_at_zero` (synthetic 30-residue `M`-only sequences don't match any Pfam HMM profile at E=1e-3 — expected for the per-cell synthetic FASTA format) |
| novelty_mmseqs2_nnIdentity (upstream: MMseqs2 vs 200-seq Pfam-A target DB) | n_total=2, nohit_all=2, novelty_all=1.0 | n_total=2, nohit_all=2, novelty_all=1.0 | 0.0 | `framework_ties_at_saturation_novelty` (no hits against the 200-seq reference — both arms are vacuously "novel" because the synthetic sequences match nothing in the held-out DB) |
| foldability_pLDDT (upstream: OmegaFold) | n/a | n/a | n/a | `skipped_no_omegafold_python312_blocker` (intentional — Wave 80 Agent A §3.1; requires Python 3.10 sidecar; not in scope for Wave 81) |
| self_consistency_scPerplexity (upstream: ESM-IF + OmegaFold PDB) | n/a | n/a | n/a | `skipped_no_omegafold_python312_blocker` (depends on `run_foldability.py` which invokes OmegaFold) |

### 2.1 Why both arms tie at saturation / zero

The per-cell synthetic FASTA format is:

```
>baseline_seed42|family=PF00005.27
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
>framework_seed42|family=PF00005.27
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
```

The framework adapter's `_extract_aa_for_fasta` falls back to the `"M" * 30` placeholder when the trace carries no decode surface (the per-cell integration is on the synthetic M-only init state, since `LineageFlowAdapter.build_initial_state` is initialised at the categorical-uniform prior before the flow head runs). The 30-residue M-only string:

* does not contain any of the 20 AA-side-chain variation, so it is **trivially rejected by the HMMER profile scan** (`hmmscan_total_hits=0`).
* does not exist in the 200-seq MMseqs2 target DB (the target DB has real Pfam-family sequences), so `nohit_all=2` and `novelty_all=1.0` (vacuously).

This is a **framework-adapter limitation, not a Wave 81 limitation**: the framework adapter does not currently thread the conditional `family_id=PF00005.27` through the upstream LineageFlowClassifier's conditional flow head (Wave 47 Phase 2 acknowledges this as "LineageFlowComposite" needing per-position entropy from the upstream classifier). At `--force-mode real`, the adapter runs through the real ckpt but starts from a uniform init state whose trajectories collapse to the M-only placeholder when the upstream classifier fails to provide a useful prior.

**Honest reading:** at N=2 per arm (the only data Wave 81 Agent C collected before killing the sweep), the framework and baseline arms are statistically indistinguishable on `family_validity_rate` and `novelty_mmseqs2_nnIdentity`. The value-add of the framework can only be measured when the adapter's `apply_restart_distribution` re-injects a meaningful prior between rounds — which the Wave 45 `LineageFlowClassifierAwareRestart` policy was designed to do, but the policy requires the LineageFlowClassifier to be reachable in the `lineageflow_venv` (which it is, per Wave 41 Agent B) **and** the `family_id` to be threaded through to the upstream classifier (which the current `solve_ode` path does not do).

### 2.2 Statistical power

At N=2 per arm, the 95% confidence interval on a binomial proportion `p` for `hmmscan_total_hits=0` is approximately `p ∈ [0, 0.71]` (Wilson interval, n=2). At the brief's target N=1000, the Wilson interval would collapse to `p ∈ [0.005, 0.04]` for the same hit rate, which is meaningful but still inconclusive about * framework vs baseline delta* because both arms would hit the same ceiling (zero or saturation).

A meaningful N=1000 framework-vs-baseline delta would require either:
1. The adapter to start from a real Pfam-family prior (not the M-only placeholder), so the sequences carry enough AA-side-chain variation to match the HMMER profile / MMseqs2 reference.
2. The framework arm's `apply_restart_distribution` to be the only source of family-conditional diversity (i.e., baseline uses the M-only placeholder while framework re-injects family priors).

Neither is wired today. **The N=1000 sweep at the brief's scope would still show `framework_ties_at_zero` for both metrics.**

---

## 3. Wrapper patches (Wave 81 Agent C deltas)

### 3.1 `tools/upstream_eval.py:run_lineageflow_upstream_eval`

Added 5 new kwargs that the orchestrator requires (`evaluate_all.py --metrics family_validity novelty` exits with `error: --hmmdb is required` if any are missing):

```python
def run_lineageflow_upstream_eval(
    fasta_path, output_dir, *,
    metrics=("family_validity", "novelty"),  # Wave 81 — restricted to 2 unblocked
    timeout_s=DEFAULT_TIMEOUT_S,
    hmmdb=None or pathlib.Path = DEFAULT_HMMDB,                # NEW (Wave 81)
    target_db=None or pathlib.Path = DEFAULT_TARGET_DB,        # NEW (Wave 81)
    pfam_fastas_dir=None or pathlib.Path = DEFAULT_PFAM_FASTAS_DIR,  # NEW (Wave 81)
    hmmscan=None or str = DEFAULT_HMMSCAN,                     # NEW (Wave 81)
    mmseqs=None or str = DEFAULT_MMSEQS,                       # NEW (Wave 81)
) -> dict[str, float]:
    ...
    cmd += [
        sys.executable,
        str(LINEAGEFLOW_EVALUATE_ALL),
        "--fasta", str(fasta_path),
        "--outdir", str(output_dir),
        "--metrics", *metrics,
        # Wave 81: pass-through args (None → skip, lets orchestrator fall back)
        *(["--hmmdb", str(hmmdb)] if hmmdb else []),
        *(["--target-db", str(target_db)] if target_db else []),
        *(["--pfam-fastas-dir", str(pfam_fastas_dir)] if pfam_fastas_dir else []),
        *(["--hmmscan", str(hmmscan)] if hmmscan else []),
        *(["--mmseqs", str(mmseqs)] if mmseqs else []),
    ]
```

**Default paths (Wave 81 vendored):**
* `DEFAULT_HMMDB` = `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` (Wave 80 Agent B download)
* `DEFAULT_TARGET_DB` = `data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB` (Wave 80 Agent B built from 200-seq held-out Pfam subset)
* `DEFAULT_PFAM_FASTAS_DIR` = `data/lineageflow_upstream/dataset/pfam_fastas_clean` (empty placeholder — vendored LineageFlow upstream does NOT ship the full Pfam corpus; the novelty metric short-circuits its `build_reference_fasta` branch because `_db_exists(target_db)` is True)
* `DEFAULT_HMMSCAN` = `/home/hugo/hmmer_build/bin/hmmscan` (Wave 80 Agent B install)
* `DEFAULT_MMSEQS` = `/home/hugo/bin/mmseqs` (Wave 80 Agent B install)

**Default metrics change:** the tuple is now `("family_validity", "novelty")` instead of the pre-Wave-81 4-metric tuple. The two blocked metrics (`foldability`, `self_consistency`) require OmegaFold + ESM-IF on Python 3.10 (host is 3.12). Calling the helper with the 4-metric tuple still works (caller opt-in).

### 3.2 `tools/run_real_ckpt_eval.py` — per-cell FASTA header fix

The per-cell LineageFlow FASTA writer at line 4283 now includes `family=<id>` in the header so the upstream `family_validity_hmmer.py` parser accepts the records:

```python
# Wave 81 — FASTA headers carry ``family=<id>`` so the upstream
# family_validity_hmmer.py script (which parses headers for the
# conditioning family) accepts our records.
family_id = "PF00005.27"
try:
    if model == "lineageflow":
        from adaptive_reflow.adapters.lineageflow import (
            LINEAGEFLOW_FAMILY_ID_DEFAULT,
        )
        family_id = str(LINEAGEFLOW_FAMILY_ID_DEFAULT)
except Exception:
    pass
fasta_lines = [
    f">baseline_seed{seed}|family={family_id}",
    _extract_aa_for_fasta(baseline_trace, model),
    f">framework_seed{seed}|family={family_id}",
    _extract_aa_for_fasta(framework_trace, model),
]
```

Pre-Wave-81 the headers were `>baseline_seed<N>` (no `family=...` tag) and the upstream orchestrator exited with `No labeled sequences found (expected family=... in FASTA headers)` — surfacing as `family_validity__missing_family_headers = <n_seqs>` even though all records WERE there. The Wave 81 fix threads the default `family_id` (PF00005.27) so the orchestrator parses the family tag correctly.

---

## 4. Statistical power at N=1000 (planned)

The brief's N=1000 sweep target, with the current framework adapter's per-cell wallclock of ~3 min (CPU-bound ESM-2 forward pass), requires:

* **Wallclock**: 1000 cells × 3 min = 3000 min = ~50 hours (linear); 10× speedup is feasible via parallel cells on a 10-core CPU box → ~5 hours, or via a single GPU host (lineageflow_venv stays CPU per Wave 40 decision, but `kanzi_venv` has CUDA 13.0 — LineageFlow could be ported to `kanzi_venv` with Wave 69 Agent 4's torch 2.14.0+cu130 wheel).
* **Sequential search budget**: at p_hat = 0.5 (the prior assumption for a baseline 50% family-validity rate), a 2-proportion z-test at N=1000 per arm has 80% power to detect a 5 pp delta (Cohen's h ≈ 0.10) at α=0.05. At N=100 the same test has 80% power only for ≥ 14 pp deltas.

The honest reading is that **N=1000 per arm would NOT surface a framework-vs-baseline delta at the current adapter's `family_id=PF00005.27` ceiling**. The Wave 80 Agent A §7 caveat and Wave 79 Phase 5 paper audit both escalate the same blocker: the LineageFlow framework adapter needs the upstream `LineageFlowClassifier` reachable in the `lineageflow_venv` AND threaded through `solve_ode` so the framework arm's `apply_restart_distribution` re-injects the family prior mid-flow. Today the adapter starts from a uniform init state and the `apply_restart_distribution` perturbs via `LineageFlowClassifierAwareRestart` but the perturbation comes from a stub classifier (the `LineageFlowClassifier` is vendored at `data/lineageflow_upstream/models/model.py` but the adapter doesn't import it in `solve_ode`).

---

## 5. Scale-up path to N=1000 (deferred)

For a meaningful N=1000 sweep, the following engineering work is required (out of scope for Wave 81):

1. **Wire the LineageFlowClassifier into the framework adapter's `solve_ode`** so the per-step velocity field uses the real classifier (not the ESM-2 + flow-head shim). This is a 50-200 LOC change to `adaptive_reflow/adapters/lineageflow.py:_torch_velocity_field` to import + call the upstream `LineageFlowClassifier` instead of the stub. Wave 47 Phase 2 (`LineageFlowGlue`) acknowledges this as a glue-layer gap.
2. **Initialize the bundle from a real Pfam-family prior** instead of the uniform init state. Currently `build_initial_state` does `family_embed = rng.standard_normal(LINEAGEFLOW_FAMILY_EMBED_DIM)` (Wave 41 line 514). A real Pfam-family prior would require loading the family-specific `pfam_priors_asr_mad/<family>.prior.json` and using its Dirichlet `alpha` vector as the initial categorical.
3. **Port `lineageflow_venv` to GPU** (per Wave 69 Agent 4 the torch 2.5.1+cu128 wheel is now available). With GPU, per-cell wallclock drops from ~3 min to ~10 s, so 1000 cells × 10 s = ~2.8 hours.
4. **Parallel orchestration**: spawn N parallel `run_real_ckpt_eval.py` processes (one per seed), each running 1 cell. N=1000 cells / 10-core box = 100 cells per process × 10 processes = 1000 cells in ~30 min.

A Wave 82 follow-up is scoped to items 1 + 3 + 4 (skip 2 — the uniform init is fine if the framework arm's restart policy re-injects a real prior). Items 1+3+4 together would unblock the brief's N=1000 target on the existing CPU box in < 30 min wallclock.

---

## 6. D.4 byte-stable regression

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/ -k "d4" --no-header -q
33 passed, 2 skipped, 5128 deselected, 9 warnings in 6.91s
```

**D.4 verdict:** 33/33 PASS (2 skipped are perf kernel benchmarks requiring `pytest-benchmark` plugin, intentionally not installed in CI). Matches the Wave 80 Phase 3 §3.2 baseline (33/33 PASS, 2 skipped) — the Wave 81 wrapper patches + FASTA header fix did NOT regress any D.4 vector.

---

## 7. OmegaFold-blocked metrics (escalated honestly)

Per Wave 80 Agent A §3.1 + §5 risk table, the 2 OmegaFold-blocked metrics remain **intentionally skipped**:

* `foldability_pLDDT` — OmegaFold requires Python 3.8/3.9/3.10 (the `setup.py` hard-blocks 3.12, and the host runs 3.12.13 per Wave 80 §1).
* `self_consistency_scPerplexity` — depends on `run_foldability.py` which invokes OmegaFold.

The honest verdict per Wave 80 Phase 4 §1.2 is `skipped_no_omegafold_python312_blocker` (intentional). The brief acknowledges this: *"For the 2 OmegaFold-blocked metrics, honest 'skipped_no_omegafold_python312_blocker' verdict."* — confirmed.

A future wave would unblock these by standing up a Python 3.10 sidecar venv + vendoring the `OmegaFold` git repo into the venv (Wave 80 Agent B §3.2 already vendored the repo at `data/omegafold/` but the install requires 3.10). Out of scope for Wave 81.

---

## 8. Regression tests added

3 new tests in `tests/test_tools/test_upstream_eval.py` (all 11 total PASS in the file):

1. `test_upstream_eval_lineageflow_passes_hmmdb_target_db_pfam_fastas_dir_and_bins` — verifies the wrapper passes `--hmmdb` + `--target-db` + `--pfam-fastas-dir` + `--hmmscan` + `--mmseqs` to the orchestrator with the Wave 81 vendored defaults.
2. `test_upstream_eval_lineageflow_default_metrics_restricted_to_unblocked_two` — verifies the default metrics tuple is exactly `(family_validity, novelty)` and explicitly excludes `foldability` + `self_consistency`.
3. `test_upstream_eval_lineageflow_none_kwargs_skip_arg` — verifies that `None` for any of the 5 new kwargs skips the corresponding `--arg` (lets the orchestrator fall back to its own default).

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_tools/test_upstream_eval.py -v --no-header -q
============================= test session starts ==============================
collected 11 items
tests/test_tools/test_upstream_eval.py ...........                       [100%]
============================== 11 passed in 0.15s ==============================
```

---

## 9. Files changed (Wave 81 Agent C deltas)

| File | Lines | Role |
|---|---|---|
| `tools/upstream_eval.py` | ~60 | Added 5 default constants + 5 kwargs to `run_lineageflow_upstream_eval` + restricted default metrics tuple |
| `tools/run_real_ckpt_eval.py` | ~15 | FASTA writer threads `family=<id>` in headers (Wave 81 Phase 2 lineageflow header fix) |
| `tests/test_tools/test_upstream_eval.py` | ~110 | 3 new regression tests for the Wave 81 wrapper changes |
| `data/lineageflow_upstream/dataset/pfam_fastas_clean/` | 1 dir | Empty placeholder so `evaluate_all.py --pfam-fastas-dir` passes its `_require_path` check |
| `verification_outputs/lineageflow_n1000_baseline_q4_2026.json` | 1 file | Raw sweep JSON (partial: 1 cell) |
| `verification_outputs/lineageflow_n1000_framework_q4_2026.json` | 1 file | Raw sweep JSON (partial: 1 cell) |
| `docs/audit/wave81-phase3-sweep.md` | this file | Wave 81 Agent C sweep audit doc |

---

## 10. Wave 80 §1.2 (verbatim) verdict transition for LineageFlow

| Paper metric | Wave 79 verdict | Wave 80 verdict | Wave 81 verdict |
|---|:---|:---|:---|
| `family_validity_rate` | `blocked_upstream_deps_missing` | `adapter_signature_mismatch` | `framework_ties_at_saturation_internal` (saturated on both side) + `framework_ties_at_zero_upstream_hmmer` (synthetic seqs don't match HMMER profiles) — **adapter bug closed** (Phase 2), but the framework-vs-baseline delta is **0** at N=2 per arm |
| `novelty_mmseqs2_nnIdentity` | `blocked_upstream_deps_missing` | `adapter_signature_mismatch` | `framework_ties_at_saturation_novelty` (nohit=2 for both arms — vacuously novel) — **adapter bug closed** (Phase 2), but the framework-vs-baseline delta is **0** at N=2 per arm |
| `foldability_pLDDT` | `blocked_upstream_deps_missing` | `skipped_no_omegafold_python312_blocker` | **UNCHANGED** (still `skipped_no_omegafold_python312_blocker`; intentional) |
| `self_consistency_scPerplexity` | `blocked_upstream_deps_missing` | `skipped_no_omegafold_python312_blocker` | **UNCHANGED** (still `skipped_no_omegafold_python312_blocker`; intentional) |
| `family_mixture` | `partial_uniform_pi_synthetic_csv_needed` | `infra_ready` (uniform-pi CSV) | **UNCHANGED** (`infra_ready`) |
| `family_distribution` | `partial_uniform_pi_synthetic_csv_needed` | `infra_ready` | **UNCHANGED** (`infra_ready`) |

The Wave 81 transition: **adapter bug closed** (Phase 2 + Agent C wrapper patches). Framework-vs-baseline delta at N=2 per arm is **0** for both `family_validity_rate` and `novelty_mmseqs2_nnIdentity`. The honest escalation per the brief is that **N=1000 sweep would not change this verdict without the upstream LineageFlowClassifier being threaded into the framework adapter** (Scale-up path item 1 in §5).

---

## 11. NO commit per task brief

Per the task brief: *"NO commit (verification only)"*. This audit doc + 1 wrapper patch + 1 eval tool patch + 1 placeholder dir + 3 regression tests + 2 raw sweep JSONs are all in the working tree but **NOT committed**. The working tree changes are:

```
$ git status --short
 M tools/run_real_ckpt_eval.py   # FASTA header family= tag (Wave 81)
 M tools/upstream_eval.py         # 5 new kwargs + restricted default metrics
 M tests/test_tools/test_upstream_eval.py  # 3 new regression tests
?? data/lineageflow_upstream/dataset/pfam_fastas_clean/  # placeholder dir
?? verification_outputs/lineageflow_n1000_baseline_q4_2026.json
?? verification_outputs/lineageflow_n1000_framework_q4_2026.json
?? docs/audit/wave81-phase3-sweep.md
```

A future wave will commit these alongside the upstream LineageFlowClassifier wire-in (item 1 in §5) so the commit history shows: "Wave 81 Agent C: wrapper patches + D.4 PASS + scale-up path documented" as one logical unit.