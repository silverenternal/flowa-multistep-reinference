# GAP-45 — R1 blend-off switch: code wiring + sensitivity pre-check

**Date:** 2026-10-18
**Branch:** main
**Scope:** make the R1 restart-blend isolate-able at the canonical
NFE=150 budget. This increment is **code only** — it adds an additive
`--beta-override` flag, pins the β semantics, and verifies that the
lever actually moves the decoded output in the canonical (real
classifier) regime. The 3-seed × 2-arm sweep is a separate increment.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`,
`docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.*`,
`tnnls_submission/**`, `verification_outputs/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| New flag | `--beta-override <float>` on `tools/gen_lineageflow_n1000_fastas.py` |
| Blend-off arm | `--beta-override 0.0` → β = 0 → m = 1 → **identity restart** |
| Blend-on arm | default (no flag) → β = 0.5 × 50/150 = **0.1667** at NFE=150 |
| Semantics correction | GAP-25 / `todo.json` said "blend-off (m = 0)"; that is a **sign error** — the adapter uses `m = 1 − β` |
| Sensitivity (real classifier, torch mode) | β=0 vs β=0.1667 changes **235–248 of 256** decoded positions per record (3/3 records) |
| Sensitivity (synthetic adapter) | **0** positions differ — argmax collapse; CPU tests must not assert FASTA bytes |
| Byte-stability | `beta_override=None` is byte-identical to omitting the kwarg; D.4 30/30 PASS |
| Sweep | **not run** in this increment |
| **Sweep result (§8, 2026-10-20)** | β = 0 is a **collapse mode**, not a control: 0/0/0 hits vs baseline 37/36/32, entropy 1.68 bits, top-3 fraction 0.98. β = 1 (fresh perturbation, no memory) is healthy and **ties** β = 1/6 in 3/3 seeds → the gain is the perturbation, not the memory |

---

## 1. What was changed

### 1.1 `tools/eval/framework.py`

1. `_make_framework_policy(..., beta_override: float | None = None)` —
   after the legacy / paper-quantity / tier-aware β branches and
   **before** the NFE-adaptive scaling:

   ```python
   if beta_override is not None:
       beta = min(1.0, max(0.0, float(beta_override)))
   ```

   Placement is load-bearing. Applying the override *before*
   `beta *= min(1, NFE_REF / nfe)` means:
   * `beta_override = 0.0` stays exactly `0.0` at every NFE (a true
     blend-off, not a scaled blend-off);
   * `beta_override = 0.5` reproduces the legacy default at any NFE
     (the override is a pre-scaling β, not a post-scaling one).
   The clamp keeps `beta_by_channel` inside the contract's `[0, 1]`.

2. `_solve_framework(..., beta_override=None)` — new keyword-only
   parameter, threaded verbatim into the policy builder. Default
   `None` leaves every existing call site byte-identical.

### 1.2 `tools/gen_lineageflow_n1000_fastas.py`

1. Module-level `BETA_OVERRIDE: float | None = None`, wired from
   `--beta-override` in `main()`.
2. `--beta-override` argparse entry (default `None`), documented as a
   *diagnostic* lever distinct from `--beta-base`.
3. `_framework_emit_sequence` passes `beta_override=BETA_OVERRIDE` to
   `_solve_framework`.
4. The Wave 186 P2 sensitivity wrapper (`_apply_sensitivity_patches`)
   now (a) accepts `beta_override` explicitly and forwards it, and
   (b) skips its `beta_base` re-substitution when an override is in
   force. Without (a) the wrapper's `**_extra_kwargs` would silently
   swallow the override — the flag would have been a no-op. Without
   (b) the wrapper would clobber the override back to
   `beta_base × scale`.
5. `manifest.json` gains `"beta_override": <float|null>` so every arm
   is self-describing.

**Why not reuse `--beta-base`?** `--beta-base` only substitutes the
legacy `0.5` constant and is deliberately skipped on the tier-aware
path (Wave 275 P4 guard). It also goes through a post-hoc
`dataclasses.replace` on the finished policy. `--beta-override` is the
first-class, last-word-on-β lever, which is what a *blend-off* control
needs: it must win regardless of which β branch the adapter would
otherwise take.

### 1.3 Tests

`tests/test_tools/eval/test_framework.py` (+4):

| test | asserts |
|---|---|
| `..._beta_override_zero_is_blend_off` | β = 0 at NFE ∈ {0, 10, 50, 150} |
| `..._beta_override_none_preserves_legacy` | `None` ≡ omitted (same `policy_hash`); β = 0.5 at NFE=0 and 0.5·50/150 at NFE=150 |
| `..._beta_override_is_clamped` | `2.5 → 1.0`, `−1.0 → 0.0` |
| `..._beta_override_wins_on_paper_quantity_path` | override beats the scheduler-derived β |

`tests/test_tools/test_gen_lineageflow_n1000_fastas.py` (+2):

| test | asserts |
|---|---|
| `test_beta_override_reaches_restart_policy` | spies on `apply_restart_distribution`; default arm β = 0.5·50/60, blend-off arm β = 0.0; baseline FASTA unchanged; manifest records the override |
| `test_beta_override_default_is_byte_stable` | omitting the flag ≡ `--beta-base 0.5` byte-for-byte |

---

## 2. β / m semantics (the correction)

`adaptive_reflow/adapters/lineageflow.py:2027` (and the shared
`memory_fraction_for` contract):

```
blended = m * prior_theta + (1 - m) * fresh_theta
m = 1 - beta
```

* `beta = 0` → `m = 1` → `blended == prior_theta` → the restart is the
  **identity**. This is "blend off".
* `beta = 1` → `m = 0` → `blended == fresh_theta` → a **full** fresh
  restart, the maximal perturbation.

GAP-25 §6 and the earlier `todo.json` wording said "`m` forced to 0"
for the blend-off arm. That would have been the maximal-perturbation
arm, the opposite of the intended control. Corrected additively in
`docs/audit/gap25-r1-blend-isolation.md` §6 and in `todo.json`
(`open_gaps[GAP-45].gap`, `metric_remediation[R1]`). The GAP-25
verdict itself is unaffected: it compares arms B (init-only) and C
(full framework), neither of which is a blend-off arm.

---

### 2.1 Related finding — GAP-25's "blend" arm had the gate closed

While pinning the semantics we re-read the GAP-25/D-004B-ATTRIBUTION
manifests. Both recorded framework manifests
(`verification_outputs/r1_3seed_d004b_q4_2026/seed4{2,3,4}/manifest.json`
and the D-004 arm) carry:

```json
{"nfe_per_record": 10, "n_rounds": 3, "restart_min_nfe": 20}
```

The driver's gate (`tools/gen_lineageflow_n1000_fastas.py`, present
since 2026-09-18 per `git log -S "effective_n_rounds = 1"`) is:

```python
effective_n_rounds = int(N_ROUNDS)
if int(NFE_PER_RECORD) < int(RESTART_MIN_NFE):
    effective_n_rounds = 1
```

So at NFE=10 < 20 the framework arm ran **one** `solve_ode` pass and
never entered `apply_restart_distribution` in a round that feeds the
next round. The manifest records the *requested* `n_rounds: 3`; the
`effective_n_rounds` disclosure field was only added later (GAP-40),
so the recorded artifact does not contradict this reading.

**Consequence for GAP-25.** Its arm C is described as "canonical init
+ 3 restart-blend rounds". Operationally it was a single pass. The
`B ≈ C` comparison is therefore not evidence that the blend adds
nothing — the blend was absent from C by construction. The
`B ≫ A` result (the per-record init carries the win) is unaffected,
because that comparison never depended on the blend. The honest
reading of GAP-25 is: *"at NFE=10 the framework arm is a single pass,
so the blend was not tested"*, not *"the blend was tested and is
zero"*.

This makes GAP-45 the first measurement of the blend at **any**
budget, not merely the first at the canonical budget. It also means
the "init-attributed" label on R1 rests on an untested blend; the
sweep in §4 is what decides it.

---

## 3. Sensitivity pre-check (observed)
**Question:** does β change the *decoded* sequence at the canonical
budget, or would the sweep be a structural null?

### 3.1 Synthetic adapter (CPU)

`LineageFlowAdapter(force_mode="synthetic")`, NFE=150, `n_rounds=3`,
8 records, β ∈ {default, 0.0, 1.0}, argmax decode:

| arm | differing positions vs default (per record) | total |
|---|---|---|
| β = 0.0 | `0,0,0,0,0,0,0,0` | **0** |
| β = 1.0 | `0,0,0,0,0,0,0,0` | **0** |

The state digest changes (e.g. `4ace62b9…` vs `6cc0b509…` at NFE=60)
but the argmax decode does not: the synthetic velocity field relaxes
both initial conditions into the same argmax basin. Same result with
`restart_from_endpoint=True`. **Consequence:** the CPU regression tests
assert the β carried by the policy, not the FASTA bytes — a
FASTA-bytes assertion would be vacuous.

### 3.2 Real classifier (canonical regime)

`LineageFlowAdapter(force_mode="auto")` in `.venvs/lineageflow_venv`,
`mode: torch`, `_is_lineageflow_classifier: True`, NFE=150,
`n_rounds=3`, 3 records, argmax decode:

| record | differing positions, β=0.0 vs default (of 256) |
|---|---|
| 0 | **238** |
| 1 | **235** |
| 2 | **248** |

So in the regime that produced the canonical R1 numbers, the blend is
strongly active and the sweep is informative.

**Disclosure:** the CPU/synthetic and GPU/real regimes differ
qualitatively on this lever. Any statement about "the blend does
nothing" must name the regime; the synthetic result is an
argmax-collapse artifact, not evidence about the mechanism.

### 3.3 N=20 driver smoke (confirms the wiring end-to-end)

Full driver, not a direct adapter probe: `--n 20 --nfe 150 --n-rounds 3
--restart-min-nfe 5 --seed 42`, blend-on (default) vs
`--beta-override 0.0`, `.venvs/lineageflow_venv`, `cuda:0`
(`verification_outputs/gap45-r1-blend-off-150/smoke/{on,off}/`).

| Artifact | Result |
|---|---|
| `baseline.fasta` SHA-256 | `9fab8535…` in both arms — **identical** |
| `framework.fasta` SHA-256 | `abbc2068…` (on) vs `6645e81c…` (off) |
| Per-record decoded sequences | **0 / 20 identical** |
| off manifest | `beta_override: 0.0`, `effective_n_rounds: 3`, `beta_base: 0.5` |
| on manifest | `beta_override: null`, `effective_n_rounds: 3`, `beta_base: 0.5` |

This reproduces §3.2 at the driver level (every record changes), rules
out a baseline-side effect, and confirms the gate-open configuration
(`effective_n_rounds == n_rounds == 3`) that the real sweep must use.
Wall clock: 5 m 03 s (on) / 10 m 24 s (off) for 20 records.

---

## 4. Prescribed sweep (not run here)

Match the GAP-41b canonical NFE=150 screen exactly except for β:

```bash
# blend-on (default) and blend-off arms, 3 seeds each
for seed in 42 43 44; do
  for arm in on off; do
    extra=""; [ "$arm" = off ] && extra="--beta-override 0.0"
    .venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
      --seed $seed --n 200 --start-index 0 \
      --upstream-eval-len-bias short \
      --nfe 150 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
      $extra --outdir verification_outputs/gap45-r1-blend-off-150/seed${seed}_${arm}
  done
done
```

Then HMMER both arms with the canonical counter
(`hmmscan --noali --cpu 32 --tblout <out> --acc Pfam-A.hmm <fasta>`),
pair per record, and report `Δ(blend_on − blend_off)` with a 95 % CI.
Decision rule (from `todo.json` GAP-45): CI excludes 0 positive → the
blend gets credit; includes 0 → R1 stays init-attributed. **The frozen
R1 headline is not changed either way.**

Runtime estimate: ~8–9 h CPU/GPU for 6 arms × 200 records + HMMER.

---

## 5. Verification (this increment)

| command | result |
|---|---|
| `pytest tests/test_tools/eval/test_framework.py tests/test_tools/test_gen_lineageflow_n1000_fastas.py -q` | 24 passed |
| `pytest tests/test_d4_regression_vectors.py -q` | see §6 |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | see §6 |
| `mkdocs build --strict` | see §6 |
| `python3 tools/check_claims_consistency.py` | see §6 |
| real-adapter sensitivity probe | 235–248/256 positions differ (3/3) |

---

## 6. Gate results

Recorded at commit time (see the commit message footer for the exact
HEAD). The D.4 vectors are the load-bearing check: `beta_override=None`
must leave all 30 byte-stable vectors unchanged.

| gate | result |
|---|---|
| D.4 regression vectors | **30/30 PASS** |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **0 findings** ("All checks passed!") |
| `mkdocs build --strict` | **exit 0** (26.8 s) |
| `check_claims_consistency.py` | **exit 0**, "No drift detected." |
| `pytest tests/test_tools/eval/test_framework.py tests/test_tools/test_gen_lineageflow_n1000_fastas.py -q` | **24 passed** |
| `pytest tests/ -q -p no:randomly` | 15 failed, 5167 passed, 177 skipped, 12 xfailed — **all 15 pre-existing** in modules untouched here (`test_cli` / `test_sweep` stub signatures predate the `classifier_aware_restart` kwarg; `test_paper_metrics` is env-bound) |
| `mypy adaptive_reflow/` (`.venv/bin/mypy`) | **3 pre-existing errors**, unchanged (CLM-024 state); `tools/` is not in the mypy scope |

The D.4 vectors are the load-bearing check: `beta_override=None` leaves
all 30 byte-stable vectors unchanged.

---

## 7. Unresolved / noted

> **ADDITIVE correction (2026-10-20, §8).** The first bullet below is now
> superseded: the sweep was run. It found that β = 0 is a collapse mode rather
> than a control, and that the memory term adds nothing measurable
> (β = 1/6 vs β = 1 is a tie in 3/3 seeds). The bullet is kept verbatim as the
> state of knowledge when it was written.

- **The sweep is not run.** GAP-45 stays `PLANNED` in `todo.json`
  until the 6-arm HMMER comparison lands.
- **The blend-on arm is already attenuated at NFE=150.** β =
  0.5 × 50/150 = 0.1667, i.e. one third of the NFE=50 anchor strength.
  A null at NFE=150 does not license "the blend does nothing at full
  strength"; it licenses "the blend does nothing *at the canonical
  budget's effective β*". This must travel with the verdict.
- **`--beta-base` has a pre-existing closure-capture quirk:** the
  Wave 186 P2 patch installs once per process and captures the first
  invocation's `beta_base`. It is not exercised by the canonical
  one-process-per-cell driver, so it is left untouched (additive rule);
  noted here for the next agent.
- **The real-classifier probe loaded the 10.5 GB ckpt on GPU 0** and
  ran 6 framework solves (~2m17s wall, including load). No artifacts
  were written; this was a diagnostic only.

---

## 8. The sweep, run — beta = 0 is a collapse mode, not a control (2026-10-20)

§4 prescribed a blend-on / blend-off contrast at NFE=150. It was run. The
result is not the one the decision rule was written for.

### 8.1 Protocol

| item | value |
|---|---|
| generator | `tools/gen_lineageflow_n1000_fastas.py` |
| seeds | 42 / 43 / 44 |
| N | 200 records per arm |
| NFE | 150, `--n-rounds 3 --restart-min-nfe 5 --temperature 1.0` |
| length bias | `short` |
| env | `.venvs/lineageflow_venv`, `cuda:0` (arms) / `cuda:1` (beta=1 control) |
| scorer | `tools/gap55_r1_score_fastas.py --metrics family_validity` |
| metric | `family_validity__hmmscan_total_hits` (canonical HMMER counter) |
| artifacts | `verification_outputs/gap45-r1-blend-off-150/` (β = 0 and β = 1/6), `verification_outputs/gap45-r1-beta1-150/` (β = 1) |
| aggregation | `tools/gap45_r1_blend_off_paired.py` → `attribution.json` |

With `blended = m * prior + (1 - m) * fresh` and `m = 1 - beta`
(`adaptive_reflow/adapters/lineageflow.py:2019`), the three arms are:

| arm | beta | m | restart state |
|---|---:|---:|---|
| baseline | — | — | no restart, 150 NFE single pass |
| **β = 1/6** (default at NFE=150) | 0.1667 | 0.833 | 83 % previous sample + 17 % fresh per-record simplex |
| **β = 0** (the prescribed "blend off") | 0.0 | 1.000 | previous sample only — **no fresh perturbation at all** |
| **β = 1** (added after the fact) | 1.0 | 0.000 | fresh per-record simplex only — **no memory** |

β = 1 was not in the pre-registration. It was added because the pre-registered
control turned out to be degenerate (§8.2) and the same axis has a second,
non-degenerate endpoint. It costs no new seeds.

### 8.2 Observed

**Totals (hits, N = 200 per arm):**

| seed | baseline | β = 0 | β = 1/6 | β = 1 |
|---:|---:|---:|---:|---:|
| 42 | 37 | **0** | 48 | 50 |
| 43 | 36 | **0** | 55 | 44 |
| 44 | 32 | **0** | 63 | 52 |
| mean | 35.0 | **0.0** | 55.3 | 48.7 |

**Sequence degeneracy** (median over 200 records):

| arm | unique | median Shannon entropy | median top-3 residue fraction |
|---|---:|---:|---:|
| baseline | 200/200 | 3.68 bits | 0.34 |
| **β = 0** | **95–99/200** | **1.68 bits** | **0.98** |
| β = 1/6 | 200/200 | 4.13 bits | 0.28 |
| β = 1 | 200/200 | 4.13 bits | 0.27 |

**Paired contrasts** (record level, paired by `qid`, 4000-replicate bootstrap,
seed 20261020):

| contrast | Δ hits/record by seed | 95 % CI excludes 0 | verdict |
|---|---|---:|---|
| β = 1/6 vs baseline | +0.055 / +0.095 / +0.155 | 2/3 | framework ahead |
| β = 1 vs baseline | +0.065 / +0.040 / +0.100 | 1/3 | framework ahead |
| **β = 1/6 vs β = 1** | **−0.010 / +0.055 / +0.055** | **0/3** | **tie in 3/3** |
| β = 1/6 vs β = 0 | +0.240 / +0.275 / +0.315 | 3/3 | β = 0 collapses |

**Controls.**

- *Baseline identity*: within each seed, `baseline.fasta` is byte-identical
  between the β = 0 and β = 1/6 run directories (200/200 records, 3/3 seeds).
  The baseline does not see β, and it does not.
- *Reproducibility*: `seed42` β = 1/6 reproduces the GAP-41b canonical prefix
  **200/200 records byte-identical**.
- *Nesting*: the N = 200 `seed42` β = 1/6 arm is byte-identical to the first
  200 records of the N = 1000 `gap55-r1-nfe150-n1000/seed42` arm (200/200), so
  the screen is a strict prefix of the powered run rather than an independent
  draw.

### 8.3 The prescribed decision rule fires, and its inference is not licensed

§4 says: "CI excludes 0 positive → the blend gets credit". The β = 1/6 vs β = 0
CI excludes 0 by a wide margin, so by the letter of the rule the blend "gets
credit". That reading is wrong, and the reason is visible in the arm itself:

- β = 0 removes the *fresh perturbation*, not the blend. `m = 1` means the
  restart state is the previous sample verbatim.
- The arm then re-integrates the flow from a data-like state, which drives it
  into a low-complexity attractor: entropy falls 3.68 → 1.68 bits, the top-3
  residue fraction rises 0.34 → 0.98, half the records become duplicates, and
  the arm scores **0 hits on all three seeds**.
- This is the same failure signature already documented for R1 in
  `docs/audit/r1-d004-remeasure.md` §6 ("a low-complexity poly-S/A/T string with
  no Pfam domain, hence 0 hits"), which identified the restart perturbation as
  the pipeline's only per-record seed carrier.

So the contrast is "perturbation vs no perturbation", not "blend vs no blend".
Comparing against a collapsed arm inflates any positive effect to look decisive.

### 8.4 What the β = 1 arm settles

β = 1 keeps the per-record perturbation and discards the memory, so it isolates
the memory term at fixed total NFE and fixed R:

- **β = 1 is not degenerate** (200/200 unique, 4.13 bits) — the perturbation
  alone is enough to keep the arm alive.
- **β = 1/6 vs β = 1 is a tie in 3/3 seeds** (Δ = −0.010 / +0.055 / +0.055
  hits per record; every CI spans 0). The 83 % memory term adds nothing
  measurable at NFE=150.
- Both endpoints sit above the baseline; the β = 1/6 arm clears the CI in 2/3
  seeds and the β = 1 arm in 1/3.

**Reading: R1's NFE=150 gain is carried by the per-record random restart
perturbation, not by the memory blend.** This is the D-004b conclusion
(`docs/audit/r1-d004b-attribution.md`), now measured with the blend actually
executing — which is exactly what GAP-25 could not do, because its arm C was
downgraded to one round by the `nfe < restart_min_nfe` gate (§2.1).

### 8.5 What this does and does not change

- **Does not change** the frozen R1 headline. The N = 1000 NFE = 150 result
  (+117 hits, +74.1 %, per-record CI [+0.073, +0.160]) stands; §8.2's N = 200
  numbers are a screen and are underpowered for that contrast (2/3 seeds).
- **Does change** the mechanism attribution available for the paper. The
  defensible statement is "the restart's per-record perturbation is the
  load-bearing mechanism; the memory fraction is not", not "the blend earns the
  win". The pre-existing wording in the manuscript already declines to claim
  the blend (`gap25-r1-blend-isolation.md` §0), so no overclaim needs
  correcting — but no new blend claim may be added either.
- **Does not license** "β = 0 is harmless". It is a collapse mode.

### 8.6 Unresolved / noted

- **N = 200 only for β = 1.** The powered comparison would be N = 1000 × 3
  seeds; the screen is enough to see a 3/3 tie, not enough to bound the memory
  term's effect size. Recorded as an open gap rather than a confirmation.
- **β = 1/6 vs baseline is 2/3 at N = 200 but 1/1 at N = 1000** (seed 42, CI
  [+0.073, +0.160]). The N = 200 screen is underpowered, not contradictory.
- **Novelty was not scored.** `run_lineageflow_upstream_eval` with the `novelty`
  metric invokes MMseqs2 through a *shared relative* temp directory
  (`results/mmseqs_tmp` inside the vendored tree); two concurrent evaluations
  collide and the metric returns `nonzero_exit`. Two arms were scored
  concurrently and both failed that way, so every arm was re-scored sequentially
  with `--metrics family_validity`. The R1 claim is about `hmmscan_total_hits`,
  which is unaffected. The collision is a real property of the upstream
  evaluator and is worth fixing before any future concurrent HMMER run.
- **The machine was shared.** Two unrelated jobs from another project were
  running throughout; per-arm wall time rose from ~55 min to ~70 min. No
  measurement depends on wall time.
