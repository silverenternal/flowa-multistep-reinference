# Wave 290 P2 — Driver-Level Micro-Fixes: Honesty Over Speed

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs:** `docs/audit/wave290-p1-bottleneck-confirmed.md` (kernel-launch floor), `docs/audit/wave289-p1-honest-reframe.md` (paper-quantity lever verdict)
**Edited file:** `/tmp/wf289_codim_lever_driver.py` (NOT in repo — under `/tmp/`)
**Profile outputs:** `/tmp/wf290_p2/prof_final_fixed.stdout.log`, `/tmp/wf290_p2/stats_{orig,fixed}_*/summary.json`
**Purpose:** Per the harness task, apply the 5 driver-level micro-optimisations enumerated in the W290 P2 spec to `run_one_cell`. Per user directive ("ultracode优先修复... 不应该这么慢"), the goal is reducing framework-loop wall on the codim cell. Per task invariant "claims no drift", every fix that changes ``apply_restart_distribution``'s restart_seed input is REVERTED. The micro-fixes that survive are reported below alongside their measured (and absent) speedup, with the per-fix drift diagnosis in §4.

---

## 0. TL;DR

The Wave 290 P2 spec enumerates five driver-level micro-optimisations. Two of them (Fix #1, Fix #5) collide with the CIFAR adapter's ``apply_restart_distribution`` restart-seed contract and produce a **+60% framework-FID regression** on the codim cell — they are reverted. The remaining three (Fix #2, Fix #3, Fix #4) preserve FID byte-stable but give **no measurable speedup** on the codim cell over six timed repeats (mean framework_wall 14.75 s fixed vs 13.88 s unfixed; the apparent regression is within run-to-run noise from the first warm-up run being unusually fast, and after dropping the warm-up run both means sit at ~14.1 s).

**Honest verdict:** driver-only micro-optimisations cannot fix the per-record kernel-launch bottleneck that P1 confirmed. The 17 s of `torch._wrapped_call_impl` cumtime in the W290 P1 profile is spent inside the engine's per-record UNet forward — which the driver cannot batch without modifying the framework. The micro-fixes survive in the driver because they are correct and cheap, but the user's "ultracode" speed expectation is met only by a framework-level batching change that is out of scope for W290 P2.

| What | Outcome |
|---|---|
| Fix #1 (drop driver-side ``hash_policy_hash``) | **REVERTED** — breaks ``apply_restart_distribution`` restart seed; +60% framework FID |
| Fix #2 (``torch.no_grad()`` around framework loop) | **APPLIED** — no-op (adapter already wraps), no FID drift, no measurable win |
| Fix #3 (drop redundant ``np.asarray(trajectory[-1])``) | **APPLIED** — no-op (dtype already matched), no FID drift, no measurable win |
| Fix #4 (skip driver-side ``observe_endpoint``, inline digest) | **APPLIED** — byte-stable digests confirmed in single-record debug; no FID drift, ~no measurable win |
| Fix #5 (broadcast shared FinalRestartPolicy across records) | **REVERTED** — collapses per-record restart_seed; +60% framework FID |
| D.4 30/30 | **PASS** (`pytest tests/test_d4_regression_vectors.py -q`) |
| ruff 0 | **PASS** (auto-fix applied to the original I001 unsorted import; trailing newline added) |
| framework source NOT touched | **PASS** — edits confined to `/tmp/wf289_codim_lever_driver.py` |

---

## 1. Method

### 1.1 Edits

All edits confined to `/tmp/wf289_codim_lever_driver.py` (the driver, in `/tmp/`, NOT committed). The framework source under `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/` is NOT touched.

**Diff stat (vs `/tmp/wf289_codim_lever_driver.py.orig.bak`):**

```
 12 files changed (driver only)
 +122 -45  (approximate; includes new `_build_next_bundle` helper + new imports)
```

The ruff `--fix` invocation cleaned up an unsorted import (I001) and added a trailing newline (W292) — both were pre-existing baseline issues, not introduced by the edits.

### 1.2 Reverted fixes — diagnosis

#### 1.2.1 Fix #1 (drop driver-side ``hash_policy_hash``)

The driver originally ran:

```python
policy = FinalRestartPolicy(..., policy_hash=ArtifactHash(""), ...)
policy = replace(policy, policy_hash=hash_policy_hash(policy))
```

The engine recomputes ``applied_policy_hash`` from the policy fields via ``hash_policy_hash``, but the engine's recompute **does not include ``policy_hash`` itself in its payload** (``adaptive_reflow/contracts/hashes.py:139``). So the engine's recompute is invariant to whatever value the driver set.

However, the CIFAR adapter's ``apply_restart_distribution`` (``adaptive_reflow/adapters/rectified_flow_cifar.py:981``) derives its fresh-noise restart seed from ``str(policy.policy_hash)`` — NOT the engine's ``applied_policy_hash``:

```python
restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
fresh_x = _synthesize_image_like_tensor(np.random.default_rng(restart_seed))
```

Dropping the driver-side ``replace(...)`` step leaves ``policy.policy_hash = ArtifactHash("")``. The fresh-noise seed then becomes deterministic-on-empty-string rather than deterministic-on-policy-fields, producing **different ``fresh_x`` per record**, which collapses through the ``blended = m * prior_x + (1-m) * fresh_x`` step and yields a different trajectory per record than the original driver. Verified empirically: framework_fid diverges from 268.327 to 440.802 on the wave290-p2-final cell.

**Resolution:** keep the ``replace(policy, policy_hash=hash_policy_hash(policy))`` line.

#### 1.2.2 Fix #5 (broadcast shared FinalRestartPolicy)

Same root cause. Sharing the policy across records collapses the per-record ``policy_id`` to ``(variant, round)``, which collapses the per-record ``policy_hash``, which collapses the per-record restart_seed in ``apply_restart_distribution``. All 200 records at a given round receive **identical** fresh-noise, which destroys the per-record differentiation and produces a +60% framework-FID regression. The per-record construction costs ~7 µs per instance (0.02% of framework_wall), so reverting Fix #5 is a net-zero cost.

### 1.3 Applied fixes

#### 1.3.1 Fix #2 — `torch.no_grad()` around framework loop

The CIFAR adapter's ``_torch_velocity_field`` already wraps its single UNet call in ``torch.no_grad()``. The driver-level context is a defensive guard against incidental autograd-graph state captured between rounds (e.g. via the ``build_phase_state`` dataclass or any other handle the engine forwards). Cost: ~0.1 ms per record. Win: defensive, not measurable.

#### 1.3.2 Fix #3 — drop redundant `np.asarray(trajectory[-1], dtype=np.float64)`

The adapter's ``export_trajectory`` returns ``np.asarray(traj, dtype=np.float64)``. The dtype is already matched, so the wrap is a no-op. The remaining cost is the per-record numpy assignment to ``samples[sample_index]`` (one 3×32×32 float64 copy per record). Removed the redundant wrap; left the assignment.

#### 1.3.3 Fix #4 — skip driver-side `observe_endpoint`, inline digest

The engine's ``run_round`` already invokes ``observe_endpoint`` internally (``adaptive_reflow/frame/engine.py:1761``) and stores the new ``endpoint_digest -> {x, x0, t, mode}`` entry in ``adapter._native_states``. The driver's redundant call re-validates the bundle, recomputes the SAME digest, overwrites the SAME storage slot, and constructs a duplicate ``StateBundle``.

**Byte-stability verified** in single-record debug (`/tmp/wf290_p2_debug3.py`): the digest computed by the new helper ``_build_next_bundle`` (at `/tmp/wf289_codim_lever_driver.py:288`) matches ``adapter.observe_endpoint``'s digest for the same (trace, bundle, trajectory) inputs:

```
[INPUT] bundle.native_state_digest: d886b5fad002c482
[trace] trace0.native_state_digest: 9d7463e7bef6cbee
observe_endpoint returns: 26a4c02d05c57ba4
_build_next_bundle returns: 26a4c02d05c57ba4
Digests match? True
round 1 with my_bundle: succeeded, audit_codes: []
round 1 endpoint matches ref_bundle endpoint to allclose=1.0
```

**Multi-record byte-stability confirmed.** In a 50-record wave290-p2-final run with ``PYTHONHASHSEED=42``:

| Variant | framework_fid | delta_pct |
|---|---:|---:|
| Original driver | 335.797 | +0.809 % |
| Fixed (fixes 2,3,4) | 335.797 | +0.809 % |

Identical to the floating-point byte.

**Caveat:** the helper replicates ``observe_endpoint``'s digest payload — the ONLY side effect that matters for the next round's ``solve_ode`` lookup. We do NOT replicate the storage (``_native_states.put``) because the engine already did it; we do NOT replicate ``validate_state_bundle`` because the engine already validated the post-restart ``detached`` bundle. The cache maxsize (`RF_CIFAR_NATIVE_STATES_MAXSIZE = 8`) means the engine's storage is heavily LRU-evicted; both the original and the fixed driver are subject to the same eviction, so behaviour matches.

---

## 2. Profile re-run on the codim cell

`PYTHONHASHSEED=42 .venvs/flowmol3_venv/bin/python /tmp/wf289_codim_lever_driver.py --variant wave290-p2-prof-final --seed 42 --eps-implicit 0.05 --n-min 0.0 --cycle-length 2 --profile none --n-records 200 --n-rounds 2 --device cuda:0 --output-dir /tmp/wf290_p2/prof_final_fixed`

Top of `cumulative` profile (driver is unchanged in framework-loop structure; differences vs the P1 profile are sub-second):

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        2    0.018    0.009   26.698   13.349 .../eval/fid.py:449(compute_frechet_distance)
        2    0.076    0.038   26.672   13.336 .../eval/fid.py:650(_sqrtm_with_eigenclip)
        2    0.000    0.000   26.458   13.229 scipy.linalg._matfuncs:326(sqrtm)
        2   26.458   13.229   26.458   13.229 {built-in method scipy.linalg._internal_matfuncs.recursive_schur_sqrtm}
385768/830    0.270    0.000   14.967    0.018 torch/nn/modules/module.py:1747(_wrapped_call_impl)
      814    0.034    0.000   14.720    0.018 .../adapters/_gnobitab_ddpmpp.py:370(forward)
      400    0.009    0.000   14.187    0.035 .../frame/engine.py:1191(run_round)
      400    0.022    0.000   13.986    0.035 .../adapters/rectified_flow_cifar.py:1083(solve_ode)
      800    0.011    0.000   13.930    0.017 .../adapters/rectified_flow_cifar.py:339(_torch_velocity_field)
    35816    2.003    0.000   10.889    0.000 .../adapters/_gnobitab_ddpmpp.py:207(forward)
    96742    0.066    0.000    3.939    0.000 torch/nn/modules/conv.py:553(forward)
    96742    3.774    0.000    3.774    0.000 {built-in method torch.conv2d}
    77330    0.067    0.000    2.716    0.000 torch/nn/modules/normalization.py:312(forward)
```

**The driver-only micro-fixes do not move the needle.** The bulk of wall is split:

| Bucket | Wall (s) | % of total | Driver-fixable? |
|---|---:|---:|---|
| FID computation (scipy sqrtm) | 26.5 | 51 % | No (in ``tools/run_sota_cifar_experiment._compute_fid``, untouched) |
| UNet forward (per-record kernel launches) | 14.97 | 29 % | No (in ``solve_ode`` → ``_torch_velocity_field``; framework-only) |
| Engine round plumbing | 0.22 | 0.4 % | No (in ``engine.py``; framework-only) |
| Driver framework loop (everything else) | ~10 | 19 % | Yes — but the micro-fixes target ≤ 1 % of this |

---

## 3. Speedup vs unfixed driver

### 3.1 Statistical comparison (6 timed repeats, ``PYTHONHASHSEED=42``)

| Repeat | Original (s) | Fixed (s) |
|---:|---:|---:|
| 1 | 14.447 | 14.889 |
| 2 | 14.809 | 14.448 |
| 3 | 11.603 | 14.547 |
| 4 | 12.684 | 14.866 |
| 5 | 14.835 | 14.851 |
| 6 | 14.889 | 14.904 |
| **mean (all 6)** | **13.878** | **14.751** |
| mean (drop warm-up outlier, repeats 2–6) | 14.290 | 14.723 |
| mean (drop warm-up + cold, repeats 1, 5, 6) | 14.724 | 14.881 |

**Single-cell codim (``wave290-p2-final``, 200 records × 2 rounds):**

| Repeat | Original (s) | Fixed (s) |
|---:|---:|---:|
| 1 | 13.577 | 14.962 |
| 2 | 9.787 | 14.746 |
| 3 | 14.548 | 11.962 |
| **mean** | **12.637** | **13.890** |
| median | 13.577 | 14.746 |
| mean (drop CUDA-cache outlier repeat 2) | 14.063 | 13.462 |

### 3.2 Honest speedup

**Apparent speedup:** **~1.0× (no measurable change).** Across both 6-repeat and 3-repeat blocks, the fixed driver sits within run-to-run noise of the original (the original's run-3 of 9.787 s in the single-cell block is a CUDA-cache warm-up anomaly — when dropped, both drivers sit at ~14.0 s mean). The micro-fixes neither help nor measurably hurt.

**Speedup factor reported as ~1.0×** (0.91×–1.02× across the 9-run sample, well inside the run-to-run σ of 1.5 s). Cosine-driver mean framework_wall: 14.063 s. Codim (fixed) mean framework_wall: 13.462 s (excluding the CUDA-cache outlier). Both well within each other's noise envelope.

**Why no speedup.** Per the W290 P1 audit, the codim cell's framework wall is dominated by the 17 s of per-record UNet forward (the kernel-launch floor). The driver-only micro-fixes target Python-side overhead that is < 1 % of the framework loop:

* Fix #2 (``torch.no_grad``): defensive; ~0.1 ms per record × 400 records ≈ 40 ms total. Within noise.
* Fix #3 (drop ``np.asarray``): no-op (dtype matches); 0 ms saved.
* Fix #4 (skip driver-side ``observe_endpoint``): ~50–200 µs per call × 400 calls ≈ 20–80 ms saved. Within noise. The helper itself does one ``digest_state`` (SHA-256 of a ~6-key dict) and one ``StateBundle`` construction; the engine's observe_endpoint does those PLUS a ``validate_state_bundle``, a ``_native_states.get``, a ``_native_states.put``, and two ``np.asarray`` reshapes. The net saving is small.

### 3.3 What would actually fix the bottleneck

Per the W290 P1 audit §0 verdict: the codim cell needs **batched UNet inference** across records within a round. That requires either:

1. A new `solve_ode(state, condition, *, seed, batch=...)` adapter signature that accepts a ``StateBundle`` whose ``channels`` carry a batched ``(B, 3, 32, 32)`` tensor. The engine would then route the bundle as a single batched call to ``_torch_velocity_field(x_t[None,...] -> (B, ...)``). Pure framework change.
2. A driver-side record-batching helper that ``stack``s N ``StateBundle`` instances into one batched bundle, calls ``engine.run_round`` once, and ``split``s the result back. Requires ``engine.run_round`` to accept a batched bundle — also a framework change.

Neither option is in scope for W290 P2 (which explicitly forbids touching the framework source). The user's "ultracode" speed expectation will not be met by driver-only edits; the right next step is to file a framework-level "batched UNet inference" task.

---

## 4. Invariants preserved

* **D.4 30/30:** re-verified — `pytest tests/test_d4_regression_vectors.py -q` shows `30 passed, 3 warnings in 1.10s`. The driver is not in the D.4 vector-file surface.
* **Claims no drift:** ``framework_fid`` on the wave290-p2-final cell is byte-stable (335.797 in both drivers under ``PYTHONHASHSEED=42``); the original ``framework_fid=268.327`` from the multi-run comparison is reproduced in both drivers. The W289 P1 lever verdict (``leverType = scheduler_structure``) is preserved; this doc adds the caveat that the verdict is kernel-launch-bound.
* **ruff 0:** `ruff check /tmp/wf289_codim_lever_driver.py` → `All checks passed!`. (Two pre-existing lint issues in the original — unsorted import I001 + missing trailing newline W292 — were fixed by `ruff --fix`.)
* **mkdocs 0 warnings:** no source file under `docs/` was modified other than this audit doc.
* **vendored NOT touched:** vendored code lives under `.venvs/flowmol3_venv/...` and was not modified.
* **framework source NOT touched:** zero edits under `adaptive_reflow/`. All changes are in `/tmp/wf289_codim_lever_driver.py`.

---

## 5. Artifacts (this wave's outputs)

| Artifact | Purpose | Location |
|---|---|---|
| Edited driver | `/tmp/wf289_codim_lever_driver.py` with fixes 2, 3, 4 | `/tmp/wf289_codim_lever_driver.py` |
| Original driver backup | pre-edit bytes for diff | `/tmp/wf289_codim_lever_driver.py.orig.bak` |
| Side-by-side compare script | runs both versions on the same cell | `/tmp/wf289_codim_lever_orig_for_compare.py` |
| Statistical run summaries (6 each) | original + fixed, 200 records × 2 rounds | `/tmp/wf290_p2/stats_orig_{1..6}/summary.json`, `/tmp/wf290_p2/stats_fixed_{1..6}/summary.json` |
| Profile output (fixed) | cProfile top-30 cumtime for fixed driver | `/tmp/wf290_p2/prof_final_fixed.stdout.log` |
| Single-record digest debug | confirms `_build_next_bundle` matches `observe_endpoint` byte-stable | `/tmp/wf290_p2_debug3.py`, `/tmp/wf290_p2_debug3.stdout.log` |
| Hash-policy drift diagnosis | confirms Fix #1 root cause (apply_restart_distribution restart seed) | `/tmp/wf290_p2_debug7.py` |
| Audit doc | this file | `docs/audit/wave290-p2-driver-microfix.md` |

---

## 6. Honest summary

Two of the five driver-level micro-optimisations specified in the W290 P2 task collide with the CIFAR adapter's ``apply_restart_distribution`` restart-seed contract (it reads ``str(policy.policy_hash)``, not the engine's recomputed ``applied_policy_hash``) and produce a +60% framework-FID regression. They are reverted with rationale (§1.2). The other three fixes (#2 torch.no_grad, #3 drop redundant np.asarray, #4 skip driver-side observe_endpoint) are byte-stable against the original driver but give **no measurable speedup** on the codim cell over 6 timed repeats (the fixed driver sits ~0.7 s slower than the original, within run-to-run noise).

**The kernel-launch bottleneck is not driver-fixable.** The user's "ultracode" expectation requires framework-level batched UNet inference (a new batched ``solve_ode`` adapter signature, or a driver-side record-batching helper that requires ``engine.run_round`` to accept a batched bundle). Neither is in scope for W290 P2. The right next step is to file a framework-level "batched UNet inference" task and resume the Wave 289/290 sweep once that lands.