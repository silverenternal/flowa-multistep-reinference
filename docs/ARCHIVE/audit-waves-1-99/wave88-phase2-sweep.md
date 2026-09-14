# Wave 88 Agent B — Kanzi N=1000 framework-vs-baseline sweep

**Date:** 2026-09-09
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Scope:** Run the Kanzi N=1000 framework-vs-baseline paper-metric sweep with a
**REAL** framework arm (`KanziAdapter.solve_ode` + `apply_restart_distribution`),
per-metric per-arm numbers, statistical power, FSQ noise-band analysis.
**Status:** COMPLETE — with a **negative structural result** on the framework arm.
**Commits:** NONE (verification only; Wave 88 Agent C owns the paper update + commit).

---

## 0. TL;DR

Three things came out of this wave, and only the first is what the brief expected:

1. **Baseline arm N=1000 closed.** All 6 Kanzi paper metrics now have real
   N=1000 numbers on the published ckpt (§4). This supersedes Wave 83's N=200.

2. **The framework arm cannot be scored on the Kanzi paper metric — by
   construction, not by budget.** The framework arm *does* run (100/100 samples
   diverge from baseline at both the digest and the latent level, §3 F-1), but
   its state is a `(64, 64)` synthetic `protein_latent`, whereas the DAE's
   continuous latent is `(L, 256)`. `dae.quantize` rejects dim 64 outright.
   There is **no latent → Cα-coordinate bridge**, so
   `reconstruction_kabsch_rmsd_A` and the 5 codebook metrics are unreachable
   from framework output (§3 F-3, §5). The honest verdict is
   **`NOT_MEASURABLE`**, not `framework_ties`.

3. **The Wave 79 n=2 framework-arm proxy (`baseline 1.40 Å vs framework
   1.67 Å, Δ=+0.27 Å`) is an artifact and should be retracted.** Both arms were
   scored on the *same* 30-zero placeholder string, because
   `_extract_ca_coords_for_kanzi(trace)` can never read a real endpoint
   (§3 F-2). Re-running the identical placeholder input gives 1.40 / 1.67 /
   2.23 Å across three runs — a spread of 0.83 Å, 3× the Δ that was reported as
   a finding (§3 F-5). That number is cited in at least 6 committed docs.

A fourth finding lands outside the brief but affects every Kanzi number in the
repo: **`DAE.decode` is stochastic and nothing seeds it** (§3 F-4). Per-record
`reconstruction_kabsch_rmsd_A` has a run-to-run σ of **0.0947 Å** — about half
the total variance previously attributed to the data. The `"deterministic":
true` field the sweep script writes into its own output JSON is false.

---

## 1. The brief's CLI does not exist — what was run instead

The brief specifies:

```
tools/extract_ca_coords_for_kanzi.py --arm baseline   --n 1000
tools/extract_ca_coords_for_kanzi.py --arm framework  --n 1000
```

Neither flag exists. `tools/extract_ca_coords_for_kanzi.py` (263 LOC, Wave 80
Agent B) is a **pure data-prep tool** with flags `--reference-pdbs --output
--n-per-pdb --seed --noise-sigma --manifest-output`. It parses Cα atoms out of
the 4 vendored demo PDBs and writes deterministic Gaussian variants. It has no
arm concept, imports neither `torch` nor `kanzi`, and never touches the
adapter. Wave 88 Agent A's audit says so explicitly
(`wave88-phase1-audit.md:31-36`: *"the extractor is a **pure data-prep** tool —
it does NOT call `KanziAdapter.solve_ode`"*).

The framework arm lives in `tools/run_real_ckpt_eval.py`:

| Arm | Entry point | What it does |
|---|---|---|
| baseline | `_solve_baseline(adapter, nfe, seed)` (line 1030) | one `solve_ode` call |
| framework | `_solve_framework(adapter, nfe, seed, n_rounds)` (line 1289) | `n_rounds` × (`solve_ode` → `export_endpoint` → `apply_restart_distribution`), then a final full-NFE `solve_ode` |

Both were driven **unmodified** for this wave, in-process with the real DAE.
That is possible because `.venvs/kanzi_venv` can import *both* the framework and
the upstream package:

```
$ .venvs/kanzi_venv/bin/python -c "from adaptive_reflow.adapters.kanzi import default_kanzi_adapter; import kanzi, torch"
# OK — adapter + kanzi + torch 2.14.0+cu130 all import
```

The adapter must be built with `force_mode="torch"`, not `"real"` — the CLI
token `real` is translated by
`run_real_ckpt_eval.py:_ADAPTER_FORCE_MODE_ALIAS["kanzi"] = {"real": "torch"}`;
passing `"real"` straight to the factory raises
`ValueError: unknown_force_mode:real`.

---

## 2. Step 1 — the N=10 smoke, and what it actually showed

The brief's step 1 was "verify framework coords != baseline coords at N=10".
Result:

```
SMOKE RESULT: 0/10 samples have framework coords != baseline coords
mean L2(framework - baseline) = 0.000000
  sample 0 seed=1000: differ=False  len_b=30 len_f=30  L2=0.000000
  ... (all 10 identical)
```

The smoke **failed** — but not because the framework arm is a no-op. `len=30`
is the tell: `_extract_ca_coords_for_kanzi` returns `",".join(["0.0"] * 30)`,
its hard-coded fallback, for **both** arms. See §3 F-1/F-2: the framework arm
diverges from baseline in every sample; it is the *coordinate extraction* that
is broken, and it has been broken for every Kanzi arm ever run through this path.

---

## 3. Findings

### F-1 — The framework arm is live (not a no-op)

`_solve_baseline` vs `_solve_framework`, N=100 paired samples (same seed both
arms), NFE=50, `n_rounds=3`, real ckpt, adapter mode `torch`. Latents recovered
from the adapter's own cache
(`adapter._native_states[trace.native_state_digest]["trajectory"][-1]`, a
`(64,64)` float64 array):

| Quantity | Value |
|---|---:|
| samples with differing `native_state_digest` | **100 / 100** |
| samples with differing latent endpoint | **100 / 100** |
| `‖framework − baseline‖₂` (mean) | **67.44** |
| `‖framework − baseline‖₂` (min / max) | 66.43 / 68.73 |
| **relative** `‖f−b‖₂ / ‖b‖₂` (mean) | **1.0423** |
| framework / baseline wallclock ratio | 1.28× |

The relative divergence ≈ 1.04 means the framework endpoint is about as far from
the baseline endpoint as the baseline endpoint is from the origin — consistent
with 3 rounds of β=0.5 blending against fresh noise. `apply_restart_distribution`
is genuinely executing and genuinely moving the state.

### F-2 — `_extract_ca_coords_for_kanzi(trace)` can never succeed

`ODEIntegratorTrace` (`adaptive_reflow/universal/state.py:216-234`) has exactly
four fields:

```
steps, accept_rate, native_state_digest, integrator_config_hash
```

`_extract_ca_coords_for_kanzi` (`run_real_ckpt_eval.py:4119-4144`) does:

```python
endpoint = getattr(trace, "endpoint", None) or getattr(trace, "states", None)
if endpoint is None:
    return ",".join(["0.0"] * 30)
```

Neither attribute exists, on any trace, ever ⇒ the fallback fires 100 % of the
time. Both `coords_lines` entries written at
`run_real_ckpt_eval.py:4654-4657` are therefore the same 30-zero string, for
both arms, in every cell.

This is not fixable by reaching for a different accessor. The protocol is
*designed* to hide arrays: `StateBundle.channels` maps to `TensorRef`, and a
`TensorRef` is an **opaque string handle** — verified empirically, its attribute
list is `str`'s. Even the correct API, `observe_endpoint(trace, state)`, returns
a `StateBundle` whose channels are opaque strings. Numeric arrays exist only in
the adapter's private `_native_states` cache. No public protocol surface yields
coordinates.

Introduced in `4f2f05d Wave 79 Agent 2: Wire upstream eval into pipeline`;
never modified since.

### F-3 — No latent → coordinate bridge exists (the load-bearing blocker)

| Space | Shape | Source |
|---|---|---|
| Kanzi adapter `protein_latent` | **`(64, 64)`** = `(L_z=64, d=64)` | `KANZI_STATE_SHAPE`, `kanzi.py:220` |
| DAE continuous latent | **`(1, L, 256)`** | `dae.encode(x)[0]`, measured for L=39 |
| DAE FSQ input dim | **256** | `dae.quantize.dim` |
| DAE decode input | FSQ indices `(1, L)` int32 | `dae.decode(idx)` |

```
>>> dae.quantize(torch.randn(1, 64, 64))
AssertionError: expected dimension of 256 but found dimension of 64
```

Two independent mismatches: **dim** (64 vs 256) and **length** (fixed 64 vs the
actual residue count — 39/100/49/155 for the 4 demo PDBs). The adapter's
`_velocity_field` does call the real ckpt (`model(x_t, t_t, family=...)` on a
`(1,64,64)` tensor, `kanzi.py:900-944`), so the framework arm is not synthetic —
but it operates on a latent geometry that is not the trained DAE latent
geometry, and there is no inverse map back to backbone coordinates.

**Consequence:** `reconstruction_kabsch_rmsd_A` and all 5 codebook metrics are
computed from `dae.encode(coords)`. Framework output cannot enter that pipeline.
The framework arm is unmeasurable on the Kanzi paper-metric axis until an
adapter change puts the framework's state in the DAE's `(L, 256)` latent (or in
coordinate space).

### F-4 — `DAE.decode` is stochastic, and nothing seeds it

| Probe | Result |
|---|---|
| `encode()` FSQ indices, 5 unseeded repeats, same input | **identical** (deterministic) |
| `decode()` given a **fixed** `idx`, 4 repeats | **differs** (stochastic) |
| `torch.manual_seed(1234)` before each call, 5 repeats | spread **0.000e+00** → torch-RNG driven, pinnable |

Run-to-run σ of `reconstruction_kabsch_rmsd_A`, 8 real records × 8 repeats each:

| Record | mean (Å) | sd (Å) | min | max |
|---|---:|---:|---:|---:|
| 0 | 0.7682 | 0.0535 | 0.6958 | 0.8841 |
| 1 | 0.8135 | 0.1112 | 0.6626 | 1.0133 |
| 2 | 0.9448 | 0.1194 | 0.8362 | 1.1164 |
| 3 | 0.9709 | 0.1155 | 0.8246 | 1.1860 |
| 4 | 0.7334 | 0.0722 | 0.6703 | 0.8939 |
| 5 | 0.9437 | 0.1326 | 0.7922 | 1.1156 |
| 6 | 0.7323 | 0.0638 | 0.6545 | 0.8306 |
| 7 | 0.7862 | 0.0896 | 0.6539 | 0.9659 |
| **mean** | — | **0.0947** | — | — |

So a **single-draw** per-record RMSD carries ±0.186 Å at 95 %. Neither
`tools/sweep_kanzi_n1000_paper_metrics.py` nor the `_KANZI_DRIVER` in
`tools/upstream_eval.py` calls `torch.manual_seed`. The
`"deterministic": true` field the sweep script writes
(`sweep_kanzi_n1000_paper_metrics.py:239`) is **incorrect**, as is Wave 83's
"result is deterministic + byte-stable" risk-mitigation claim
(`wave83-phase4-final.md:306`).

### F-5 — The Wave 79 framework-arm proxy is noise

Feeding the driver **two byte-identical 30-zero lines** (exactly what F-2
produces):

```
n_seqs = 2.0   mean = 2.2254   min = 2.1869   max = 2.2639
```

Identical inputs, different RMSDs. Across the three runs of that same degenerate
input now on record:

| Run | mean RMSD | Provenance |
|---|---:|---|
| Wave 79 "baseline arm" | 1.3995 | `kanzi_upstream_baseline_q4_2026.json` |
| Wave 79 "framework arm" | 1.6711 | `kanzi_upstream_framework_q4_2026.json` |
| Wave 88 replication | 2.2254 | this wave |

Spread **0.826 Å** — 3.1× the Δ=+0.27 Å that Wave 79 reported as its
framework-vs-baseline reading, and the two Wave 79 files were scoring the *same*
placeholder. A 6-repeat probe on that input gave 1.451 / 1.119 / 2.408 / 2.492 /
2.410 / 2.800 Å (spread 1.68 Å).

The Δ=+0.27 Å is cited in `wave79-phase3-sweep.md`, `wave79-phase4-verdict.md`,
`wave79-phase5-paper.md`, `wave79-phase6-final.md`, `wave83-phase4-final.md`,
`wave88-phase1-audit.md`, and via `verdict.framework_arm_source` in the
committed `kanzi_n1000_paper_metrics.json`. **Recommend retraction** (§8).

### F-6 — `seed` does not produce independent samples in the baseline arm

`solve_ode` applies the seed as a deliberately tiny perturbation
(`kanzi.py:1814-1815`: `x0 + 1e-6 * rng.standard_normal(...)`). Measured over 8
distinct seeds:

| Arm | `‖e_i − e_0‖₂ / ‖e_0‖₂` (min–max) | Independent? |
|---|---|---|
| baseline | **1.38e-06 – 1.43e-06** | **NO** — seed is a 1e-6 perturbation |
| framework | 1.362 – 1.384 | yes (restart noise is `policy_hash`-seeded) |

`‖baseline endpoint‖₂ = 64.707077` for every seed. Meanwhile
`build_initial_state(batch_id, sample_id)` *does* give independent states
(`‖x₀ᵢ − x₀₀‖₂ ≈ 88–91` vs `‖x₀₀‖ ≈ 64`), but
`_build_initial_state_and_condition` hard-codes `batch_id="eval",
sample_id="s0"` (`run_real_ckpt_eval.py:1007`). So **every Kanzi cell in every
sweep from Wave 36 onward starts from the same initial state**, and an
N-by-varying-seed baseline arm has `n_eff = 1`. Independent samples require
varying `(batch_id, sample_id)`, which no current caller does.

### F-7 — The Wave 86 paper-quantity β is inert for Kanzi (confirms Agent A)

```
profile_residual_fn on caps    = ABSENT
profile_residual_fn on adapter = ABSENT
_compute_paper_quantities(...) -> None
policy.beta_by_channel = {'discrete_token_index': 0.5,
                          'pfam_family_cond': 0.5,
                          'protein_latent': 0.5}
```

Confirmed at runtime on the real ckpt. β = 0.5 constant on every channel and
every round; the Wave 31 `PaperRatioAdaptiveScheduler` path never fires. Wave 88
Agent A's §1.4 finding reproduces exactly. Note this is a *second-order* issue
here: even with paper-quantity-driven β, F-3 still blocks measurement.

---

## 4. Baseline arm — N=1000, all 6 paper metrics

<!--NUMBERS-->

---

## 9. D.4 byte-stable regression

```
$ python3 -m pytest tests/ -k "d4" --ignore=tests/test_property_based \
      --ignore=tests/test_expecttest_smoke.py --ignore=tests/perf -q
33 passed, 6 skipped, 4810 deselected, 9 warnings in 2.43s
```

**33/33 PASS** — matches the Wave 83 / 86 / 87 baseline. No framework, adapter,
or tool file was modified in this wave, so byte-stability is unchanged by
construction.

---

## 10. Reproduction

All probes are verification-only scratch scripts under `/tmp/wave88/`; the only
repo artifact written is the N=1000 baseline JSON under a **fresh** directory
(`verification_outputs/wave88_kanzi_n1000_baseline/`) so the committed Wave 83
N=200 file at `verification_outputs/kanzi_n1000_paper_metrics/` is left
untouched.

```bash
# Baseline arm N=1000 (6 paper metrics) — the committed Wave 83 script, unmodified.
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir verification_outputs/wave88_kanzi_n1000_baseline \
    --limit 1000

# F-1  framework-arm liveness, N=100 paired
.venvs/kanzi_venv/bin/python /tmp/wave88/probe_framework_liveness.py
# F-2  trace surface / 30-zero fallback
.venvs/kanzi_venv/bin/python /tmp/wave88/probe_trace.py
# F-4  decode stochasticity + run-to-run sigma
.venvs/kanzi_venv/bin/python /tmp/wave88/probe_stochasticity.py
.venvs/kanzi_venv/bin/python /tmp/wave88/probe_determinism.py
# F-7 + step-1 smoke
.venvs/kanzi_venv/bin/python /tmp/wave88/smoke_arm_divergence.py
```

| Artifact | Path |
|---|---|
| N=1000 baseline metrics | `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` (NEW, uncommitted) |
| framework liveness N=100 | `/tmp/wave88/framework_liveness_n100.json` |
| input coords (N=1000, unchanged) | `verification_outputs/kanzi_n1000_coords.txt` |
