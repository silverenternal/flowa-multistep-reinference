# GAP-01-R6-LIVE — R6 tier-aware live-sweep wiring (dead code, direction, clobber)

**Date:** 2026-10-13
**Author:** GAP-01 R6-live agent (USER AUTHORIZED, NO PUSH)
**Scope:** Wire the Wave 275 P4 R6 tier-aware restart-blend into the
LineageFlow constant-β path, launch the 3-seed × N=1000 live GPU sweep on
cuda:0, and record the outcome honestly.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

The R6 "STRONG via tier-aware counterfactual" label rests on the Wave 225 P4 /
Wave 233 P3 **mathematical proxy** (halve the easy-tier per-record pLDDT diff),
never on a live in-loop run. GAP-01 asked for the live sweep. Preparing it
surfaced **three material defects** in the previously-"wired" path:

1. **The tier-aware wrapper was dead code for LineageFlow.** It was built only
   inside `if paper_quantities is not None`, but LineageFlow exposes no
   `profile_residual_fn`, so the constant-β branch always ran. Verified: with
   `tier_aware_n_cap=0.5` + a populated baseline-pLDDT mapping, β = 0.5000 for
   hard, medium **and** easy records alike.
2. **The wrapper's `n_cap`-reduction direction is inverted** relative to the
   counterfactual it is meant to materialize. `_make_framework_policy` maps
   `β = 1 − n_cap`, so reducing the easy-tier `n_cap` (0.5 → 0.25) raises the
   easy-tier β to 0.75 = **more** fresh-noise perturbation. The Wave 225 P4
   counterfactual halves the framework's easy-tier deviation from baseline =
   **less** perturbation. The faithful materialization would need β 0.5 → 0.25
   (factor 1.5 on `n_cap`), not 0.75.
3. **The gen-script's `--beta-base` sensitivity patch would clobber the
   tier-aware β** back to a flat `beta_base` whenever `paper_quantities is None`
   (`tools/gen_lineageflow_n1000_fastas.py:362`), silently degenerating the R6
   live arm to the uniform arm.

Additionally, the frozen Wave 161 **framework** arm is **not reproducible**
today (it was generated pre-D-004 with the all-zero velocity field), so the
"live sweep" is a **new experiment**, not a re-verification of Wave 161.

**User decision (2026-10-13, AskUserQuestion):** materialize **as-designed**
(`easy_tier_nfe_reduction_factor = 0.5`; easy-tier β → 0.75) and run the sweep,
reporting the honest live `d_z` whatever its sign.

---

## 1. Observed facts (verified, not inferred)

### 1.1 The wrapper is inert on the constant-β path

```
$ python -c "<build _make_framework_policy with tier_aware_n_cap=0.5, mapping q0/q1/q2>"
q0 (hard):   beta=0.5000
q1 (medium): beta=0.5000
q2 (easy):   beta=0.5000     # <- wrapper never built
```

`_make_framework_policy` (`tools/eval/framework.py`) built
`TierAwareCodimensionSheetScheduler` only inside the `paper_quantities is not
None` branch (Wave 275 P4). `_compute_paper_quantities` returns `None` for
LineageFlow (no `profile_residual_fn`), so the `else` branch (`beta = 0.5`)
ran for every record.

### 1.2 Direction of the reduction

- Adapter (`adaptive_reflow/adapters/lineageflow.py:1975,2043,2075`):
  `memory_fraction = 1 − β`; `blended = m·prior + (1−m)·fresh` ⇒ β is the
  **fresh-noise fraction**.
- Framework (`tools/eval/framework.py`): `β = 1 − sample.n_cap`.
- Wrapper (`adaptive_reflow/algorithm/scheduler/tier_aware.py:496`): easy tier
  `n_cap ← n_cap · factor` (factor 0.5).
- ⇒ easy-tier β: 0.5 → 0.75 (more fresh noise).

The Wave 225 P4 counterfactual (`scripts/wave225_p4_k6_tier_aware.py:164-187`)
scales the easy-tier per-record diff by 0.5 — i.e. **less** framework effect,
hence **less** perturbation. The two are opposite.

### 1.3 The patch clobber

`tools/gen_lineageflow_n1000_fastas.py:362` (Wave 186 P2) replaced the policy's
per-channel β with `beta_base · scale` whenever `paper_quantities is None`.
With the canonical `--beta-base 0.5` this would reset every record (easy
included) to β = 0.5.

### 1.4 Frozen framework arm not reproducible

Wave 161's `framework/foldability/queries.fasta` was produced by the
pre-D-004 adapter (all-zero velocity field; see
`docs/audit/r1-d004-remeasure.md`). Regenerating today yields a different
framework arm. The **baseline** arm is bare-RNG and *is* byte-reproducible
(verified: first 20 regenerated baseline sequences byte-identical to the
frozen Wave 161 baseline).

---

## 2. Changes made

| File | Change |
|---|---|
| `tools/eval/framework.py` `_make_framework_policy` | Build the tier-aware wrapper on the **constant-β** path too: wrap `ConstantScheduler(cycle_length=20, n_cap=0.5)` in `TierAwareCodimensionSheetScheduler`, `set_baseline_metrics(...)`, `set_current_record(current_record_id)`, then `β = 1 − sample.n_cap`. Gated behind the same `(0,1)` factor + non-empty mapping guard; legacy default byte-stable. |
| `tools/gen_lineageflow_n1000_fastas.py` `_apply_sensitivity_patches` | Skip the Wave 186 P2 β override whenever the tier-aware flags are active (do not clobber the per-record β). |
| `tests/test_algorithm/test_scheduler/test_r6_tier_aware_wiring.py` | +2 tests: policy-level β on the constant path (easy 0.75 / hard+medium 0.5 / legacy 0.5); the sensitivity patch preserves the tier-aware β. |
| `tools/sweep_r6_tier_aware_live.py` | NEW 3-seed × N=1000 live driver (generate → fold framework on cuda:0 → paired `d_z`). |

### 2.1 Pilot verification (N=20, cuda:0)

- Baseline arm byte-identical legacy vs tier-aware (bare RNG unaffected). ✓
- Framework arm: **all 5 easy records changed** (q5, q8, q9, q10, q19);
  **all 15 hard/medium records unchanged**. ✓ The wiring is live and
  tier-selective, exactly as designed.

---

## 3. Live sweep (3 seeds × N=1000, cuda:0 ONLY)

- Driver: `tools/sweep_r6_tier_aware_live.py`
  `--seeds 42,43,44 --n 1000 --tier-aware-n-cap 0.5 --gpu 0`.
- Generation: `gen_lineageflow_n1000_fastas.py --upstream-eval-len-bias short
  --nfe 10 --n-rounds 3 --temperature 1.0 --tier-aware-n-cap 0.5`.
- Fold: `run_foldability.py --fold-gpus 0 --skip-sc` (pLDDT only; ESM-IF
  self-consistency deferred — see §5).
- Pairing: fresh framework `plddt_mean` vs **frozen Wave 161 baseline**
  `plddt_mean`, by `qid` (positional; the fold pipeline assigns `q{i}` =
  record `i`).
- Output: `verification_outputs/gap01-r6-tier-aware-live/` (`METADATA.json`,
  `METADATA.gpu`, per-seed `sweep.log`, `sweep_summary.json`).

**Hard constraint:** cuda:0 ONLY (user directive "只能用GPU0"); GPU 1 never
touched.

### 3.1 Result

> **[FILLED IN §4 after the sweep completes]**

---

## 4. Interpretation

> **[FILLED IN after the sweep completes]**

---

## 5. Unresolved gaps / caveats

1. **Direction mismatch (§1.2) is real.** The as-designed run tests a
   *different* intervention from the counterfactual. A live `d_z` that fails to
   reproduce `+0.2235` refutes the counterfactual's *materialization*, and is
   recorded as such — it does not by itself refute the proxy arithmetic.
2. **ESM-IF self-consistency (scPerplexity) not measured** in this sweep
   (`--skip-sc`); the R6 scPerp axis (cluster-robust `d_z = −4.019`) is
   untouched.
3. **Baseline reuse.** The frozen Wave 161 baseline folds are reused (validated
   byte-reproducible at the sequence level); only the framework arm is
   re-folded.
4. **Frozen framework arm non-reproducibility (§1.4)** means the live sweep is
   a new experiment; the Wave 161 framework arm cannot be regenerated.

---

## 6. Files

- `tools/eval/framework.py` (constant-β tier-aware wiring)
- `tools/gen_lineageflow_n1000_fastas.py` (β-clobber bypass)
- `tools/sweep_r6_tier_aware_live.py` (driver)
- `tests/test_algorithm/test_scheduler/test_r6_tier_aware_wiring.py` (+2 tests)
- `verification_outputs/gap01-r6-tier-aware-live/` (evidence)
- this audit doc
