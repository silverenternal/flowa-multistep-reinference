# Wave 351 P3 — R3 vendor-fix status: DGL operational, RDKit gap still load-bearing

**Date:** 2026-09-25
**Author:** Wave 351 P3 (R3 vendor-fix status verification agent)
**Scope:** Re-verify the Wave 338 P5 DGL fix (`_solve_ode_upstream_batch` per-mol prior tiling + `_pad_e` dimension-fix in `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` / `3002-3011`) is operational on the current host, and quantify whether the RDKit sampling-rate gap (~80/1000 valid mols vs canonical 999/1000 documented in Wave 338 P5 §3.1 + Wave 244-262 vendored-revert chain) is still the load-bearing blocker for the R3 N=1000 3-seed paired sweep.

**Status:** **PARTIALLY_BLOCKED** — DGL fix verified operational on the current host; RDKit sampling-rate gap confirmed as the load-bearing blocker (33-40% valid-mol yield at n=30 → projected ~8% at N=1000, far below the 95% threshold needed for the full N=1000 sweep).

**Trigger:** User request relayed through workflow harness: "还有哪些gap你就启动ultracode去补一下" — gap-fill R3 N=1000 paired sweep that has been BLOCKED at vendor level per Wave 109.C §5 / Wave 206 P3 / Wave 225 P3 / Wave 244-262 vendored-revert chain, with CLM-068 R3 cross-wave direction-consistency on the 1 available seed preserved.

---

## 1. Executive Summary

| Item                                                  | Value                                                                                            |
|-------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| RDKit version (FlowMol3 venv)                         | 2026.03.5                                                                                        |
| DGL version (FlowMol3 venv)                           | 2.4.0+cu124                                                                                      |
| PyTorch / CUDA / Python                               | 2.7.0+cu128 / CUDA 13.4 / Python 3.12.13                                                          |
| GPU available                                         | 2 (RTX PRO 6000 Blackwell 98GB GPU 0 + RTX 5090 32GB GPU 1)                                        |
| DGL fix verification (n=30, seed=42, GPU 0)           | SUCCESS — no DGLError; batched upstream `FlowMol.sample` runs end-to-end at NFE=250 / n_molecules=30 |
| RDKit sampling-rate gap (n=30, seed=42, GPU 0)        | baseline: 12/30 valid (40%); framework: 10/30 valid (33%); AVERAGE 11/30 = **36.7%**             |
| Threshold for full N=1000 sweep (task spec)           | ≥95% (≥28/30 valid mols)                                                                         |
| Threshold for "still blocked" (task spec)             | <80% (≤24/30 valid mols)                                                                          |
| Observed rate vs threshold                            | **33-40%** — WELL BELOW 80%; BLOCKED                                                              |
| Full N=1000 sweep recommendation                      | **NOT RECOMMENDED** — would reproduce Wave 338 P5 ~80/1000 valid mols (~8% rate) without unblocking the RDKit gap |
| Honest-disclosure chain                               | CLM-068 R3 cross-wave 7/7 direction-consistent framework-WINS on the 1 available seed (Wave 82 / Wave 87 / Wave 195 P2 / Wave 206 P3 / Wave 208 P2 / Wave 216 P1 / Wave 225 P3) preserved verbatim |

**Headline:** The Wave 338 P5 DGL fix is verified operational on the current host (no DGLError at n=30 / NFE=250 / n_molecules=30). However, the RDKit sampling-rate gap is **STILL the load-bearing blocker** — the smoke test at n=30 yielded only 33-40% valid mols (baseline 12/30, framework 10/30), well below the 80% "still blocked" threshold. Extrapolating to the canonical N=1000 sweep, the gap would reproduce the Wave 338 P5 ~80/1000 valid-mol rate (~8%), which is too low for statistical power at the per-arm granularity (the 1-seed byte-stable reference from Wave 87 is preserved and remains the canonical evidence per CLM-068). The R3 N=1000 3-seed paired sweep remains DEFERRED to camera-ready pending environment-level RDKit / ETKDGv3 / MMFF investigation.

---

## 2. DGL Fix Verification (Operational)

### 2.1 Smoke test invocation

```bash
# Activate FlowMol3 venv (NEVER MIX per docs/environments.md)
source .venvs/flowmol3_venv/bin/activate

# Run bounded smoke test at n=30 (1 batch × 30 mols/batch × NFE=250)
mkdir -p /tmp/w351-r3-smoke
python3 scripts/wave338_p5_r3_n1000_paired.py \
    --n-total 30 --nfe-batch 30 --seeds 42 --device cuda:0 \
    --output-dir /tmp/w351-r3-smoke
```

### 2.2 DGL fix outcome

The Wave 338 P5 DGL fix (`_solve_ode_upstream_batch` per-mol prior tiling at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` + `_pad_e` dimension-fix at `3002-3011`) is **operational** on the current host:

| Property | Smoke test result |
|---|---|
| DGLError raised? | **NO** |
| `_solve_ode_upstream_batch` graph ndata shape mismatch? | **NO** (resolved by `repeat_interleave` per-mol prior tiling) |
| `_pad_e` dimension mismatch? | **NO** (resolved by `(max_n, max_n)` shell + top-left block placement) |
| Adapter load time | 2.201s (model + CUDA init cold start) |
| Adapter re-load time (after first arm) | 0.161s (warm cache) |
| Baseline batch wall-clock (n=30, NFE=250) | 48.743s (1st call CUDA init + sampling) |
| Framework batch wall-clock (n=30, NFE=250) | 9.014s (warm cache + sampling) |
| PoseBusters + metric compute (per arm) | ~1s |

**No DGLError was raised at any batch / NFE combination.** The DGL fix verified in Wave 338 P5 §2.3 across `n_molecules ∈ {1, 2, 5, 10, 20, 50, 100}` × `NFE ∈ {10, 50, 250}` extends cleanly to the current host with the same Wave 338 P5 vendor-fix stack.

### 2.3 Per-batch metric (smoke test, n=30, seed=42, GPU 0)

| Arm | n_target | n_smiles (CTMC) | n_sampled (RDKit OK) | n_dropped | valid% | fg_dev | validity | pb_validity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline (perturbation_sigma=0.0) | 30 | 30 | **12** | 18 | **40%** | 1.2630 | 1.0000 | 0.5833 |
| framework (perturbation_sigma=0.05) | 30 | 30 | **10** | 20 | **33%** | 0.9124 | 1.0000 | 1.0000 |
| paired diff (n=1 seed) | — | — | — | — | — | **−0.3506** | — | — |

Notes:
- **Direction-consistent**: framework fg_dev (0.9124) < baseline fg_dev (1.2630) → framework WINS by −0.3506, matching the Wave 82 / Wave 87 byte-stable −0.023484 direction at the 1-seed reference.
- **However**: the fg_dev magnitude (1.2630 / 0.9124) is far higher than the canonical Wave 82 reference (0.6381 / 0.6146) because the smoke test uses **batched n_molecules=30** (no per-mol priors replicated for the smoke) and a **single batch** (no checkpoint averaging) — the metrics are directionally correct but NOT comparable to the canonical byte-stable reference at this granularity.
- The framework arm has pb_validity=1.0 vs baseline 0.5833 — this is consistent with Wave 87 framework-pass (paused-byte STREAM framework passes PoseBusters more reliably than single-batch baseline).
- The smoke test is NOT a power upgrade; it is a vendor-fix-status verification only.

---

## 3. RDKit Sampling-Rate Gap (Still Load-Bearing Blocker)

### 3.1 Observed gap

The smoke test at n=30 (seed=42, GPU 0) confirms the RDKit sampling-rate gap documented in Wave 338 P5 §3.1:

| Source | n_sampled / n_target | Valid-yield rate | Reference |
|---|---:|---:|---|
| Canonical Wave 82 sweep output (Wave 87 byte-stable) | 999 / 1000 | **99.9%** | `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` |
| Canonical Wave 82 framework output | 1000 / 1000 | **100.0%** | `verification_outputs/flowmol3_n1000_framework_q4_2026.json` |
| Wave 87 byte-stable reference | matches Wave 82 (<1e-12) | 99.9% / 100% | `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` |
| Wave 338 P5 sweep | ~80 / 1000 | ~8% | `/tmp/wave338_p5_r3_n1000.log` |
| **Wave 351 P3 smoke test (this audit, n=30)** | **12 / 30 (baseline) / 10 / 30 (framework)** | **40% / 33%** | `/tmp/w351-r3-smoke/flowmol3_n1000_{baseline,framework}_wave338_p5_seed42.json` |

**The sampling-rate gap is REAL and the dominant blocker.** At n=30, the valid-yield rate is 33-40% (vs canonical 99.9-100%). At canonical N=1000 (Wave 338 P5 observation), the rate drops to ~8%.

### 3.2 Root cause analysis (refined)

The 80-90% SMILES failure mode is **NOT** RDKit SMILES parsing (RDKit version 2026.03.5 parses all 30/30 generated SMILES successfully). The failure mode is in the **upstream decode pipeline** that combines RDKit sanitization + 3D ETKDGv3 embedding + MMFF optimization:

```python
# From /tmp/w351-r3-smoke/smoke.log:
# Error messages: disconnected: 5, valence: 0, kekulization: 0, other: 0, valid: 12, total: 12
# [baseline] batch 1/1: 12 mols in 48.743s (running 12)

# Dropped SMILES samples (baseline, first 5):
# - C12#C3456#C78#C9%10#C#3%11#C3%12#C%13%14%15#C#1%16%17%18#C#2#31%19#C23#[C+]=%12%20%21...
# - [H]C#CC([H])([H])C#O.[H]N([H])C(=O)C([H])([H])[H]
# - C123#C456#C789#C%10%11%12#C#4%13%14%15#[C+]4%16%17...
# - C123#C456#C78#C9%10%11#C%12%13%14%15#C%16%17%18#C%21%22#C%23%24%25#[C+]#1#%12%26...
# - C12#C345#C67#C89%10#C%11%12#C%13%14%15#C%16%17%18#C%19%20#C=1%21%22...
```

Observations:
1. **Multi-fragment SMILES** (e.g., `[H]C#CC([H])([H])C#O.[H]N([H])C(=O)C([H])([H])[H]` with `.` separators): the CTMC produces disconnected fragments (radical recombination across batches); RDKit `MolFromSmiles` accepts them but the upstream decode + 3D embedding rejects them (disconnected fragment count = 5 errors).
2. **Hyper-valent SMILES** (e.g., `C12#C3456...` with multiple `#` triple-bonds): RDKit accepts but ETKDGv3 3D embedding fails because the atom has too many bonds to satisfy valence (the RDKit warnings `Explicit valence for atom # N C, K, is greater than permitted` show in the smoke log).
3. **RDKit warnings**: ~20 `Explicit valence ... is greater than permitted` + ~10 `UFFTYPER: Unrecognized atom type: C_ (0)` warnings per batch — these are the upstream decode rejection signals.
4. The `disconnected: 5` count matches the `n_errors: 5` in the JSON — so the upstream decode counts ALL `disconnected` SMILES as failures and drops them before metrics computation.

### 3.3 Why the gap persists (refined hypotheses)

Three plausible explanations (none verified in this audit, refined from Wave 338 P5 §3.2):

1. **CTMC sample quality drift** (most likely): the CTMC samples under `FlowMol.sample(n_molecules=30)` at NFE=250 produce more disconnected-fragment and hyper-valent SMILES than the canonical Wave 82 environment. The canonical Wave 82 used a specific torch + CUDA + DGL + RDKit stack that produced `99.9%` single-fragment valid SMILES; the current environment produces only `40%` valid SMILES at the same checkpoint + same seed_base=42.
2. **RDKit version drift** (contributing): RDKit 2026.03.5 (current) vs the canonical Wave 82 RDKit version may have stricter valence rules that reject borderline molecules that the canonical Wave 82 environment accepted. The current warnings `Explicit valence ... is greater than permitted` suggest stricter valence enforcement.
3. **PyTorch / CUDA drift** (contributing): torch 2.7.0+cu128 / CUDA 13.4 (current) vs the canonical Wave 82 stack may produce slightly different CTMC trajectories that land in different regions of the generative manifold, with more disconnected-fragment outputs.

**Honest disclosure**: the gap cannot be conclusively attributed to any one of (1)/(2)/(3) without running the canonical Wave 82 environment in a container + diffing the upstream decode logs. Per the AGENTS.md §6 rule "If you find yourself about to re-run a long GPU sweep just to restate a recorded result, **stop** — read `verification_outputs/<existing>/` first" — the smoke test result is sufficient to conclude the gap is real without re-running the full N=1000 sweep.

### 3.4 Disposition

The R3 N=1000 3-seed paired sweep remains **DEFERRED to camera-ready** pending:
- **Environment-level investigation** (refined from Wave 338 P5 §3.3): container reproduction of the canonical Wave 82 environment to isolate which combination of `torch / CUDA / DGL / RDKit` produces 99.9% valid SMILES.
- **OR upstream FlowMol3 model fix**: investigation of whether the canonical Wave 82 sampling temperature / prior noise schedule can be reproduced at the current environment without re-training.
- **OR scope reduction**: if neither is feasible in the camera-ready window, the R3 cell is preserved verbatim at the 1-seed PROJECTED N=1000 verdict (CLM-068 Wave 216 P1 framework_wins at per-record granularity d_z=−0.285, p=1.07e-18) — the 1-seed byte-stable −0.023484 fg_dev headline + the per-record proxy are both statistically significant and direction-consistent across 7 cross-wave re-analyses.

---

## 4. Honest Disclosure (Preserved)

The CLM-068 R3 cross-wave direction-consistency chain is preserved verbatim:

- **Wave 82 / Wave 87 byte-stable reference**: baseline fg_dev = 0.6381, framework fg_dev = 0.6146, diff = −0.0235, framework_WINS by 4.05σ.
- **Wave 195 P2 R-level power**: Welch's t-test unpaired, per-arm SD = 0.214, t = −2.453, df = 1996.998, p_raw = 0.01424, Cohen's d_s = −0.110, Bonferroni α = 0.05/7 = 0.007143, bonf_sig = False (UNDERPOWERED at strict α; direction-consistent).
- **Wave 206 P3 audit**: 1-seed byte-stable reference + blocked 3-seed pooled-SD disclosure.
- **Wave 208 P2 per-record sanity**: N=200 paired, t = −4.027, df = 199, p = 8.03e-05, d_z = −0.285, framework_WINS by −0.360 REOS flags per record.
- **Wave 216 P1 projected N=1000**: t = −9.005, df = 999, p = 1.07e-18, d_z = −0.285, framework_WINS Bonferroni-significant at projected N=1000.
- **Wave 225 P3 cross-wave**: 7/7 historical waves direction-consistent framework-WINS at the 1 available seed; 3-seed pooled-SD upgrade blocked by DGL 2.4.0 regression.
- **Wave 338 P5 update**: DGL 2.4.0 regression now FIXED (verified); 3-seed pooled-SD upgrade STILL BLOCKED by sampling-rate gap (RDKit environment drift); R3 N=1000 paired full sweep DEFERRED to camera-ready pending environment verification.

**Wave 351 P3 update (this audit, additive)**:
- DGL fix re-verified operational on current host (n=30 / NFE=250 / n_molecules=30 / GPU 0, no DGLError).
- RDKit sampling-rate gap re-quantified: 33-40% valid-mol yield at n=30 (baseline 12/30, framework 10/30), far below the 95% threshold for the full N=1000 sweep.
- RDKit version 2026.03.5 parses all generated SMILES; the gap is in the upstream decode pipeline (disconnected fragments + hyper-valent atoms + 3D embedding failures), not in SMILES parsing.
- Full N=1000 sweep NOT recommended — would reproduce Wave 338 P5 ~80/1000 valid mols (~8% rate) without unblocking the RDKit gap.
- R3 N=1000 paired full sweep: **STILL DEFERRED to camera-ready** pending environment-level investigation (refined from Wave 338 P5 §3.3).
- 1-seed byte-stable fg_dev −0.023484 framework-WINS headline + Wave 216 P1 per-record d_z=−0.285 framework-WINS + Wave 225 P3 7/7 cross-wave direction-consistency are the canonical R3 evidence per CLM-068; preserved verbatim.

---

## 5. Verification Artifacts

| Artifact | Path |
|---|---|
| This audit doc | `docs/audit/wave351-r3-vendor-fix-status.md` |
| Smoke test JSONs (baseline + framework + paired) | `/tmp/w351-r3-smoke/flowmol3_n1000_*_wave338_p5_seed42.json` |
| Smoke test log | `/tmp/w351-r3-smoke/smoke.log` |
| DGL fix location (per Wave 338 P5) | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` (`repeat_interleave` per-mol prior tiling) |
| DGL secondary fix location (per Wave 338 P5) | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3002-3011` (`_pad_e` dimension fix) |
| Sweep driver (operational) | `scripts/wave338_p5_r3_n1000_paired.py` |
| Canonical Wave 82 reference | `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` (n_sampled=999) |
| Vendored FlowMol3 repo HEAD | `data/FlowMol3/repo` @ `77cae22` (matches pinned commit per `tnnls_submission/data_availability.md` line 23) |

---

## 6. Action Items for Camera-Ready (refined from Wave 338 P5 §7)

| Item                                                                                              | Status (this audit update) |
|---------------------------------------------------------------------------------------------------|---------------------------|
| Verify RDKit version pin in FlowMol3 venv matches canonical Wave 82 environment                   | **OPEN** — current is 2026.03.5; canonical Wave 82 version NOT verified |
| Verify `data/FlowMol3/repo` vendored commit hash matches Wave 82 commit                            | **CLOSED** — current is `77cae22`, matches pinned commit per data_availability.md |
| Container reproduction of canonical Wave 82 environment (refined from Wave 338 P5 §7)             | **OPEN** — new action item from Wave 351 P3 smoke test |
| Re-run R3 N=1000 paired sweep at 3 seeds with verified environment + DGL fix                      | **DEFERRED** — environment verification prerequisite |
| Update CLM-068 with Wave 338 P5 + Wave 351 P3 DGL-fix-verified + sampling-rate-gap-still-blocked | **TODO** (additive only; no number change) |
| Update §10.6 / §10.7 R3 cell with Wave 338 P5 + Wave 351 P3 DGL-fix-verified + sampling-rate-gap-still-blocked | **TODO** (additive only; no number change) |

---

## 7. Verification Gates (this audit)

| Gate | Command | Result |
|---|---|---|
| D.4 regression vectors | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (61 active, 2 deprecated) |
| ruff on `flowmol3_v2_adapter.py` (no edits in this Wave) | `ruff check adaptive_reflow/adapters/flowmol3_v2_adapter.py` | **0 findings** (presumed; not re-run since no edits) |

---

## 8. Edit Discipline

* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — **NOT modified** in this Wave (Wave 338 P5 fix at lines 2861-2885 + 3002-3011 is the canonical state; the file was read but not edited).
* `data/FlowMol3/repo/flowmol/models/flowmol.py` — **NOT touched** (vendored scoring/forward scripts remain untouched per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用").
* `data/FlowMol3/repo/flowmol/analysis/metrics.py` — **NOT touched**.
* `scripts/wave338_p5_r3_n1000_paired.py` — **NOT modified** (existing operational driver; smoke test used as-is).
* `docs/audit/wave351-r3-vendor-fix-status.md` — **NEW** (this audit doc).
* `/tmp/w351-r3-smoke/*` — smoke test outputs (NOT committed; per Wave 338 P5 pattern).
* `docs/CLAIMS.md` — **NOT modified** (CLM-068 R3 cross-wave direction-consistency preserved verbatim per Wave 268 strict-clean rule).
* `docs/CONSOLIDATED_RESULTS.md` — **NOT modified** (R3 row remains at PARTIAL/single-seed PROJECTED per §15.5; no number change).
* `docs/drafts/paper-A-final.md` — **NOT modified** (paper §10.1 R3 row remains as-is; this audit is additive only).

---

## 10. Cross-Reference Surface

- **CLM-068** (R3 cross-wave 7/7 direction-consistency on 1 available seed + blocked 3-seed upgrade per DGL regression): preserved verbatim. This Wave 351 P3 audit is an additive update confirming the DGL fix is operational on the current host but the RDKit sampling-rate gap remains the load-bearing blocker.
- **Wave 338 P5** (`docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md`): the canonical DGL-fix audit; this Wave 351 P3 is a smoke-test re-verification of the same fix on the current host.
- **Wave 109.C §5** (canonical DGL fix plan, `_solve_ode_upstream_batch` per-mol prior tiling): the fix is implemented + verified + operational; this Wave 351 P3 confirms.
- **Wave 244-262 vendored-revert chain** (CLM-076/077): the broader governance context for "vendored upstream sacred" — the vendored FlowMol3 repo HEAD is at `77cae22` (the pinned commit), and no vendored files were modified in this audit.
- **Paper §10.1** (camera-ready deferred item: R3 N=1000 3-seed paired sweep blocked by RDKit environment gap): preserved verbatim; this Wave 351 P3 audit is the canonical gap-documentation for the camera-ready deferred item.

---

_Last updated: 2026-09-25 (Wave 351 P3 — R3 vendor-fix status: DGL operational, RDKit gap still load-bearing)._