# R3 FlowMol3 — environment investigation: the valid-yield gap is a code artifact of the batched prior-tiling, **not** RDKit environment drift

**Date:** 2026-10-12
**Author:** R3 environment-investigation pass (light-GPU, parallel to the user's GPU-0 job)
**Scope:** Diagnose the R3 FlowMol3 `fg_dev` N=1000 "valid-yield gap" — canonical Wave 82 produced **999/1000 (99.9%)** valid molecules, while the current host produces only **33–40% valid** at n=30 (`docs/audit/wave351-r3-vendor-fix-status.md`) and **~8%** at N=1000 (`docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md`). The blocker is documented across Wave 338 P5 / Wave 351 P3 / Wave 357 P3 / `docs/CONSOLIDATED_RESULTS.md` §15.105 / paper §7.2 R3 footnote as an **"RDKit 2026.03.5 environment drift"**.

**Status:** **DIAGNOSIS COMPLETE — the documented root cause is REFUTED.** The diagnosis itself changed no source code, no vendored upstream, no `tnnls_submission/`, no `docs/CLAIMS.md`, and no R3 number/verdict. The R3 verdict label `PARTIAL / single-seed PROJECTED` is preserved verbatim. **Follow-up (2026-10-12, user-gated):** the blocked-tiling fix + a CPU regression test were applied and a full 3-seed N=1000 re-run launched — see §8.

**Trigger:** User chose the **"R3 环境调查"** track after the R1 3-seed materialization closed — to diagnose / reproduce the canonical Wave 82 `RDKit / torch / CUDA / DGL` combination that unblocks the R3 3-seed N=1000 P0 gap.

---

## 1. Executive summary

| Item | Value |
|---|---|
| Documented root cause (Wave 351 P3 / §15.105) | "RDKit 2026.03.5 environment drift" (stricter valence rules than the canonical Wave 82 stack) |
| **Verdict on that hypothesis** | **REFUTED** — the live `.venvs/flowmol3_venv` is byte-identical to the pins in `requirements-lock.txt` (committed **2026-09-05**, three days *before* the canonical Wave 82 sweep on **2026-09-08**) |
| Actual root cause | The batched-path DGL "fix" — `torch.repeat_interleave(n_mol, dim=0)` prior tiling, added **2026-09-22** (Wave 277 / commit `1efe5ce`) — **interleaves** the per-molecule prior across the DGL batch instead of **blocking** it, corrupting the CTMC prior |
| Fix (verified, not committed) | blocked tiling `.repeat(n_mol, 1)` → **valid-yield 40% → 100%** and baseline `fg_dev` returns to the canonical scale |
| Vendored upstream | `data/FlowMol3/repo` at `77cae22`, `flowmol/models/flowmol.py` **unmodified** (byte-identical to the pin) |
| Canonical path (per `wave240-p2-flowmol3-direction.csv`) | seed 42 = **"batched DGL (n_molecules=100)"**, NFE=250, N=1000 |
| Honest caveat | The blocked tiling restores the valid-yield but does **not** reproduce the canonical framework-arm direction at n≤100 single-batch — the full 10-batch N=1000 re-run is required to settle that (see §5). |
| R3 verdict / numbers / CLM-068 | **PRESERVED VERBATIM** |

---

## 2. Observed facts

### 2.1 The live venv matches the pre-Wave-82 lock — no environment drift

`requirements-lock.txt` was committed **2026-09-05** (commit `43b862d`, "Wave 15 Phase 1: F.5 env_hash infrastructure"), i.e. **three days before** the canonical Wave 82 sweep (artifact timestamp `2026-09-08T20:54:32+0800`). Every pin relevant to the FlowMol3 decode pipeline matches the live venv exactly:

| Package | `requirements-lock.txt` (2026-09-05) | live `.venvs/flowmol3_venv` | match |
|---|---|---|---|
| Python | 3.12.13 | 3.12.13 | ✅ |
| torch | `torch==2.7.0+cu128` | 2.7.0+cu128 (CUDA 12.8) | ✅ |
| dgl | `dgl==2.4.0+cu124` | 2.4.0+cu124 | ✅ |
| numpy | `numpy==2.4.6` | 2.4.6 | ✅ |
| rdkit | `rdkit==2026.3.5` | 2026.03.5 | ✅ |
| scipy | `scipy==1.18.1` | 1.18.1 | ✅ |
| pytorch-lightning | `pytorch-lightning==2.1.3` | 2.1.3 | ✅ |

`env_hash_R3.txt` (the R3 venv fingerprint) records `python_version=Python 3.12.13` / `torch_version=torch:2.7.0+cu128+cuda12.8` — the same stack.

**Conclusion:** there was no `torch` / `CUDA` / `DGL` / `RDKit` upgrade between the canonical Wave 82 sweep and the current host. The "RDKit 2026.03.5 environment drift" hypothesis cannot explain the 99.9% → 40% gap, because RDKit was already 2026.03.5 when the 99.9% run was produced.

> Note: `docs/environments.md` still describes `flowmol3_venv` as `torch 2.2.0+cu121` — that row is **stale** (it predates the cu128 upgrade that was required to run on the sm_120 Blackwell GPUs). The lock file + `env_hash_R3.txt` are authoritative for the R3 stack.

### 2.2 The canonical Wave 82 artifacts are genuinely clean

`verification_outputs/flowmol3_n1000_{baseline,framework}_q4_2026.json`:

| field | baseline | framework |
|---|---|---|
| `n_target` | 1000 | 1000 |
| `n_sampled` | **999** | **1000** |
| `n_smiles` | 1000 | 1000 |
| `n_errors` | 0 | 0 |
| `errors_sample` | `[]` | `[]` |
| `nfe_batch` | 100 | 100 |
| `seed_base` | 42 | 42 |
| `device` | `cuda:0` | `cuda:0` |

The cached `smiles_list` (200 capped) contains **0% disconnected fragments and 0 hyper-valent (`#`×4) strings** — the canonical run produced legitimate drug-like molecules. So the 999/1000 is a real valid-yield, **not** a metric-definition artifact.

### 2.3 The canonical path is the batched DGL path

`verification_outputs/wave240-p2-flowmol3-direction.csv` records the canonical seed-42 row as:

```
seed_42, 250, 1000, "batched DGL (n_molecules=100)", ... agg_fg_dev_baseline=0.6381122391671532, agg_fg_dev_framework=0.614627774616795
```

and seeds 43/44 (Wave 235 P4) as `"single_mol"` with NFE=100 / N=500 (framework-WORSE: 0.658→0.677 and 0.661→0.674). So the canonical R3 seed-42 evidence — the one that carries the framework-WINS headline — was produced by the **batched DGL path with `n_molecules=100`**, the exact path that is broken today.

### 2.4 The adapter changed after Wave 82 — `repeat_interleave` introduced 2026-09-22

`adaptive_reflow/adapters/flowmol3_v2_adapter.py` `_solve_ode_upstream_batch`:

- On the Wave 82 date (2026-09-08) the adapter revision was **`e3f4072`**, which built `prior_dict["x_0"]` as the **untiled** `(n, 3)` single-molecule prior and passed `n_atoms=[n]*n_mol` to `FlowMol.sample`.
- `torch.repeat_interleave(int(n_mol), dim=0)` first appears in **`1efe5ce` (2026-09-22, Wave 277)** — 14 days after the canonical run.
- The `_pad_e` dimension fix landed in `d9d3da7` (2026-09-23, Wave 336).

The vendored upstream `data/FlowMol3/repo/flowmol/models/flowmol.py` at line 530 does `g = dgl.batch(g)` (a **blocked** node layout: molecule 0's nodes, then molecule 1's, …) and line 535 assigns `g.ndata['x_0'] = prior['x_0']` with **no broadcasting** (DGL 2.4.0 is strict-shape — verified: assigning a `(4,3)` feature to a 12-node graph raises `DGLError: Expect number of features to match number of nodes`). Therefore the prior handed to upstream **must** be in blocked order: `prior.repeat(n_mol, 1)`.

`torch.repeat_interleave(n_mol, dim=0)` produces the **interleaved** order `[p0,p0,…,p0, p1,p1,…,p1, …]`, not the blocked order. It is a shape-compatible but **semantically wrong** replication: the per-atom prior rows no longer line up with their molecule, scrambling coordinates, atom types, charges, and — most damagingly — the bond tensor `e_0` relative to the atom indices.

### 2.5 Empirical smokes (light GPU, cuda:0, seed 42)

Driver `scripts/wave338_p5_r3_n1000_paired.py`; canonical protocol NFE=250.

| Config | n | nfe_batch | baseline valid | framework valid | baseline `fg_dev` | framework `fg_dev` |
|---|---|---:|---:|---:|---:|---:|
| **HEAD** (`repeat_interleave`) | 30 | 30 | **12/30 (40%)** | **10/30 (33%)** | 1.2630 | 0.9124 |
| HEAD (`repeat_interleave`) | 100 | 100 | (matches Wave 338 P5 table 6–9/100) | — | — | — |
| **`.repeat(n_mol,1)`** | 30 | 30 | **30/30 (100%)** | **30/30 (100%)** | 0.6451 | 1.1731 |
| **`.repeat(n_mol,1)`** | 100 | 100 | **100/100 (100%)** | **100/100 (100%)** | 0.4373 | 0.8020 |
| Canonical Wave 82 | 1000 | 100 | 999/1000 (99.9%) | 1000/1000 (100%) | 0.6381 | 0.6146 |

The HEAD n=30 run reproduces the Wave 351 P3 numbers **exactly** (paired_diff `fg_dev` = −0.350647 vs Wave 351's −0.3506; `n_errors=5`; dropped SMILES identical: hyper-valent `C12#C3456#C78#…` and disconnected `[H]C#CC([H])([H])C#O.[H]N([H])C(=O)…`). The blocked-`repeat` runs restore **100% valid yield** and put the baseline `fg_dev` back at the canonical scale.

Wave 338 P5's own verification table (`docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md` §2.3) corroborates: with `repeat_interleave`, `export_sampled_molecules` yields **1/1 at `n_molecules=1`** but only **6–9/100 at `n_molecules ≥ 20`** — i.e. the single-molecule path (where `repeat_interleave(1, dim=0)` is a no-op) is clean, and the batched path is the broken one.

---

## 3. Interpretation

1. **The environment is not the blocker.** The `torch / CUDA / DGL / RDKit` stack on the current host is identical to the stack that produced the canonical 99.9% run. Any "container reproduction of the canonical Wave 82 environment" would reproduce the *same* broken batched tiling and the *same* 40% valid-yield — because the defect lives in the framework adapter, not the environment.

2. **The blocker is a framework-side regression in the batched prior tiling.** `repeat_interleave` was introduced on 2026-09-22 (Wave 277) to satisfy DGL 2.4.0's strict shape check. It satisfies the *shape* but violates the *layout*: the DGL batch is blocked, `repeat_interleave` is interleaved. The scrambled prior is what produces the disconnected-fragment and hyper-valent SMILES that RDKit then rejects — which is exactly why the Wave 351 P3 root-cause analysis found the failure "in the upstream decode pipeline … NOT RDKit SMILES parsing". That observation was correct; the *attribution* to RDKit version drift was not.

3. **The `_pad_e` fix (Wave 336) is orthogonal and correct** — it is a genuine dimension-alignment fix, not the cause.

4. **Why the Wave-82 run worked at all.** The canonical 2026-09-08 adapter passed an **untiled** `(n, 3)` prior, which under strict DGL 2.4.0 should trip the same `DGLError`. The most parsimonious explanation consistent with all evidence is that the vendored `flowmol.py` (or the adapter) broadcast the single-molecule prior across the batch *at that time* — a behaviour removed in the Wave 244-262 vendored-revert chain, after which `repeat_interleave` was added to compensate. This specific mechanism is **not verified** (the vendored repo is grafted at `77cae22` with no usable local history); what *is* verified is the empirical contrast in §2.5. This is recorded as an **unresolved gap**, not a claim.

---

## 4. What this does NOT change

- R3 verdict label `PARTIAL / single-seed PROJECTED` — preserved verbatim.
- R3 numbers (per-arm aggregate UNPAIRED; per-record paired ACTUAL n=200 `d_z=−0.285`; PROJECTED N=1000 `t=−9.005`) — preserved verbatim.
- `docs/CLAIMS.md` CLM-068, `docs/CONSOLIDATED_RESULTS.md` §15.105, the paper §7.2 R3 footnote, and every `tnnls_submission/` file — **not modified**.
- The Wave 338 P5 DGL-fix and Wave 351 P3 smoke results — preserved verbatim as historical records (this audit *supersedes their root-cause attribution*, not their observations).
- No source code, no vendored upstream, no adapter — the *diagnosis* commit made no code change. (The follow-up fix + regression test are recorded in §8.) The `.repeat(n_mol,1)` experiment was applied to a working copy and reverted for the diagnosis commit; the adapter was byte-identical to HEAD at that point.

---

## 5. Honest caveat and next action

The blocked tiling restores the **valid-yield** (40% → 100%) and the **baseline** `fg_dev` scale, but at n≤100 single-batch it does **not** reproduce the canonical framework-arm direction (canonical: framework 0.6146 < baseline 0.6381; blocked-`repeat`: framework 1.1731/0.8020 > baseline 0.6451/0.4373). Two possibilities remain open:

- **(a)** the single-batch n≤100 comparison is simply too noisy / too correlated (with `repeat`, all `n_mol` molecules share one prior, so a single batch is one perturbed-prior group); the full 10-batch N=1000 re-run would settle it; or
- **(b)** the canonical batched path built **independent per-molecule priors**, and the correct repair is a per-molecule prior (not a shared tiled prior). Note the canonical `single_mol` seeds 43/44 also showed framework-WORSE, so the framework-WINS headline is currently only attested at seed 42.

**Smallest next action (gated on the user):** apply the one-line blocked-tiling fix and re-run the **full 10-batch N=1000 paired sweep on `cuda:0`** (the adapter seeds via `_seed_everything(seed, str(device))`, so `cuda:1` would not reproduce the canonical stream). This is the same re-run the R3 recipe already lists as the camera-ready GPU path — but with the environment correctly identified as **already canonical**, so no container reproduction is needed.

---

## 6. Verification (this pass)

| Gate | Command | Result |
|---|---|---|
| Adapter restored to HEAD | `git status --porcelain adaptive_reflow/adapters/flowmol3_v2_adapter.py` | clean |
| `repeat_interleave` present (4×) after restore | `grep -c "repeat_interleave(int(n_mol), dim=0)" …` | 4 |
| Vendored upstream unmodified | `cd data/FlowMol3/repo && git status --porcelain flowmol/models/flowmol.py` | empty (== `77cae22`) |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30/30 PASS |
| Claims consistency | `python3 tools/check_claims_consistency.py` | no drift |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings |
| mkdocs strict | `mkdocs build --strict` | exit 0 |

---

## 7. Evidence inventory

| Artifact | Path |
|---|---|
| HEAD smoke (40%/33% valid) | `/tmp/r3-investigation/head/flowmol3_n1000_{baseline,framework}_wave338_p5_seed42.json` |
| blocked-`repeat` smoke n=30 (100%/100%) | `/tmp/r3-investigation/repeat/…` |
| blocked-`repeat` smoke n=100 (100%/100%) | `/tmp/r3-investigation/repeat_n100/…` |
| Canonical artifacts | `verification_outputs/flowmol3_n1000_{baseline,framework,sweep}_q4_2026.json` |
| Canonical path label | `verification_outputs/wave240-p2-flowmol3-direction.csv` (seed_42 row) |
| Environment lock | `requirements-lock.txt` (commit `43b862d`, 2026-09-05) + `env_hash_R3.txt` |
| Adapter history | `git log -S repeat_interleave -- adaptive_reflow/adapters/flowmol3_v2_adapter.py` → `1efe5ce` (2026-09-22) |
| Vendored assignment site | `data/FlowMol3/repo/flowmol/models/flowmol.py:530` (`dgl.batch`) + `:535` (`g.ndata['x_0'] = prior['x_0']`) |
| Superseded attributions | `docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md`, `docs/audit/wave351-r3-vendor-fix-status.md`, `docs/audit/wave357-r3-rdkit-blocker-doc.md` |

---

## 8. Follow-up (2026-10-12) — fix applied, regression test added, full sweep launched

User-gated after the diagnosis ("改 tiling + 跑全量 N=1000"):

1. **Adapter fix** — `adaptive_reflow/adapters/flowmol3_v2_adapter.py` `_solve_ode_upstream_batch`: the four prior channels now use `.repeat(int(n_mol), 1)` (blocked) instead of `.repeat_interleave(int(n_mol), dim=0)` (interleaved). The comment block was rewritten to document the blocked-layout requirement and explicitly warn against `repeat_interleave`. Byte-stability for `n_mol == 1` is preserved (`repeat(1, 1)` is a no-op).

2. **CPU regression test** — `tests/test_adapters/test_flowmol3_v2_adapter_conformance.py::TestFlowMol3V2NMoleculesBatch::test_v2_upstream_batched_prior_is_block_tiled`. Uses the stub-upstream harness (no checkpoint needed) to capture the `prior` dict reaching `sample()` and asserts every per-molecule block is identical (blocked layout). **Validated**: it PASSES with the fix and FAILS with `repeat_interleave` (re-verified by temporarily reverting the tiling).

3. **Driver crash fix** — `scripts/wave338_p5_r3_n1000_paired.py` built its CSV `fieldnames` from the per-seed row only, so the summary row's extra `paired_*` columns raised `ValueError: dict contains fields not in fieldnames` **before** the paired JSON was written — which is why `verification_outputs/wave338-p5-r3-n1000-paired.json` never existed. Header now unions the summary-row keys.

4. **Full 3-seed N=1000 re-run** — `scripts/wave338_p5_r3_n1000_paired.py --n-total 1000 --nfe-batch 100 --seeds 42 43 44 --device cuda:0`, output in `verification_outputs/r3_n1000_3seed_fixed_q4_2026/` (per-arm JSON + per-seed sweep JSON + `wave338-p5-r3-n1000-paired.{csv,json}` + `METADATA.txt`). `cuda:0` is mandatory because the adapter seeds via `_seed_everything(seed, str(device))`.

---

## 9. Results (2026-10-12) — the 3-seed N=1000 re-run completed

**Run:** `scripts/wave338_p5_r3_n1000_paired.py --n-total 1000 --nfe-batch 100 --seeds 42 43 44 --device cuda:0`, output in `verification_outputs/r3_n1000_3seed_fixed_q4_2026/` (13 artifacts + `SHA256SUMS`). Wall-clock **2 h 13 m 49 s** on `cuda:0` (RTX PRO 6000 Blackwell). NFE=250, 10 batches × 100 mols per arm, blocked tiling (`.repeat(n_mol, 1)`).

### 9.1 Per-seed and paired results

| seed | baseline `fg_dev` | framework `fg_dev` | paired diff | baseline n_sampled | framework n_sampled | verdict |
|---|---|---:|---:|---:|---:|---|
| 42 | 0.605186 | 0.655220 | **+0.050035** | 997 | 998 | baseline_wins |
| 43 | 0.787544 | 0.650808 | **−0.136736** | 990 | 997 | framework_wins |
| 44 | 0.583237 | 0.556876 | **−0.026361** | 999 | 997 | framework_wins |

**3-seed paired summary:** `n_seeds=3`, `mean_diff=−0.037687`, `sd_diff=0.093899`, `se_diff=0.054213`, `t=−0.695175`, `df=2`, `p_raw=0.558854`, 95% CI `[−0.143944, +0.068570]`, `cohens_d_z=−0.401360`, Bonferroni α=0.05/7=0.007143, `bonf_sig=False`.

*2026-10-13 ADDITIVE correction (GAP-27; no point estimate / verdict change).* The 95% CI quoted above used a **normal 1.96** multiplier at `df = 2`; the correct t multiplier is `t_{0.975,2} = 4.3027`. The corrected CI is **`[−0.270946, +0.195571]`**. The point estimate, `t`, `p` and the not-significant verdict are unchanged. See `docs/audit/gap27-r3-power.md`.

All six arms emit `validity_pct=1.0000` (of the n_sampled molecules, 100% are RDKit-valid; the small shortfall from 1000 is decode-drop, not invalidity).

### 9.2 Interpretation

1. **The blocked-tiling fix restores the valid-yield.** Every arm emits `validity=1.0000` with n_sampled 990–999/1000. This is the fix's direct, unambiguous effect (40% → 100% valid-yield vs the HEAD `repeat_interleave` path, §2.5).
2. **The framework-WINS direction is reproduced in aggregate.** The 3-seed mean paired diff is `−0.0377` (framework `fg_dev` lower) — the same direction as the canonical Wave 82 seed-42 headline (`−0.0235`). 2 of 3 seeds are `framework_wins`.
3. **But it is not statistically significant.** `p=0.559` ≫ 0.05 (and ≫ Bonferroni α=0.007143); the 95% CI `[−0.144, +0.069]` straddles zero. This is fully consistent with the pre-existing **UNDERPOWERED** per-arm verdict (CLM-060 / Wave 195 P2): a directional improvement the per-arm aggregate cannot resolve at n=3 seeds.
4. **This converts R3 from 1-seed + PROJECTED to ACTUAL 3-seed.** The 3-seed pooled SD is now measurable (`sd_diff=0.0939`), replacing the previously NaN pooled SD (Wave 206 P3).

### 9.3 Honest caveats

- **The canonical seed-42 point is not reproduced** (canonical `−0.0235` → fixed-adapter `+0.0500`). This is expected and is **not** a contradiction: the canonical number was produced by the **pre-fix** adapter revision (`e3f4072`, untiled prior), whereas this run uses the **post-fix** blocked-tiling adapter. Different prior layout → different trajectory → different per-seed value. The two are **not** the same configuration, so the seed-42 point is not comparable across them; only the aggregate direction is.
- **Per-record PROJECTED (t=−9.005, significant) vs per-arm ACTUAL 3-seed (p=0.559, not significant) is a granularity difference, not a conflict.** The per-record proxy (Wave 216 P1, REOS flag count) operates at the record granularity where the framework value-add is detectable; the per-arm aggregate has one paired observation per arm. Both readings are honest (unchanged from the existing R3 disclosure).
- **`n_seeds=3`, `df=2`** is a low-power design; the CI is correspondingly wide. This run does not by itself lift R3 out of UNDERPOWERED.
- **Single shared tiled prior per batch.** With `.repeat(n_mol, 1)` all 100 molecules in a batch share one prior; the framework's σ=0.05 perturbation is applied to that shared prior. Whether the canonical batched path instead used **independent per-molecule priors** (audit §3.4 / §5 option (b)) remains **unverified**; this run does not settle it.

### 9.4 What this does NOT change

- R3 verdict label, the canonical 1-seed numbers, CLM-068, CLM-060, `docs/CONSOLIDATED_RESULTS.md` §15.105, the paper, and every `tnnls_submission/` file — **all preserved verbatim**. This section is **additive observation only**.
- No source code, no vendored upstream, no adapter change in this recording increment.
- The `repeat_interleave` → `.repeat(n_mol, 1)` adapter fix + CPU regression test were already committed in `0f62c27`; this increment only records the completed re-run.

### 9.5 Artifacts

| Artifact | Path |
|---|---|
| 3-seed sweep dir (13 files + `SHA256SUMS`) | `verification_outputs/r3_n1000_3seed_fixed_q4_2026/` |
| Paired summary | `verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.{csv,json}` |
| Driver | `scripts/wave338_p5_r3_n1000_paired.py` |

---

_Last updated: 2026-10-12 (R3 environment investigation — RDKit-drift root cause REFUTED; actual cause is the `repeat_interleave` batched prior-tiling regression; fix + regression test committed in `0f62c27`; **full 3-seed N=1000 re-run completed — valid-yield restored to 100%, framework-WINS direction reproduced in aggregate (−0.0377) but not significant (p=0.559), consistent with the existing UNDERPOWERED verdict; canonical seed-42 point not reproduced because it came from the pre-fix adapter configuration**)._
