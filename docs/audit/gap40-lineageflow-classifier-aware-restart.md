# GAP-40 — wiring the LineageFlow classifier-aware restart into the R1/K4/K5 framework arm

**Date:** 2026-10-16
**Author:** GAP-40 agent (USER AUTHORIZED, NO PUSH)
**Base commit:** `b65406b1` (GAP-39 FlowMol3 real restart-blend)
**Scope:** the user directive — *"要扭转这些差一点点 的指标只需要改几处关键代码"*, and
the user's explicit selection of the **LineageFlow `classifier_aware_restart`**
lever from the dormant-lever menu.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Result |
|---|---|
| Defect class | the LineageFlow adapter ships a real per-position classifier-aware restart policy (`LineageFlowClassifierAwareRestart`, `adaptive_reflow/adapters/lineageflow.py:925`) but **no headline driver enables it** — the symbol appeared only inside the adapter module |
| Fix (additive, default off) | `--classifier-aware-restart` / `--classifier-alpha` on `tools/gen_lineageflow_n1000_fastas.py` (R1/K4/K5 driver) + `classifier_aware_restart`/`classifier_alpha` threaded through `default_lineageflow_adapter` → `tools/eval/framework.py::_resolve_adapter` → `tools/eval/sweep.py` → `tools/eval/cli.py` |
| **Load-bearing structural finding** | at the **canonical R1 config** (`--nfe 10`, default `--restart-min-nfe 20`) the restart-blend gate degenerates `n_rounds` to **1** (`tools/gen_lineageflow_n1000_fastas.py:546`). The framework arm is a **single `solve_ode` pass** — neither the scalar nor the classifier-aware blend fires. The lever is therefore **byte-identical** to legacy at canonical config |
| Gate-open A/B (N=200, seed 42, `--restart-min-nfe 5`) | baseline 37 → legacy 38 → **classifier-aware 44** hits; `car vs legacy` MWU `p=0.117`, Fisher `p=0.123`; `car vs baseline` `p=0.073`. Directional win, **not significant** at N=200 single seed; **family-dependent** (wins 2 of 4 families) |
| **Decisive test — canonical N=1000, 3 seeds, gate-open** | seed-level totals (baseline / legacy / car): 42 = 158/257/**271**, 43 = 159/265/**269**, 44 = 174/245/**265**. `car vs legacy` mean **+12.67** hits, `d_z=1.567`, **3/3 direction-consistent**, but `p_bonf_rlevel=1.0` → **NOT STRONG**. Per-record paired-t DL meta `d_pooled=+0.024`, `p=0.184` → **NOT significant**. The lever roughly doubles the framework-vs-baseline seed-level effect size (legacy `d_z=4.97` → car `d_z=8.77`) but neither clears the pre-registered bar |
| Net | The lever is wired, additive, default-off, and **load-bearing once the gate is open**. It does **not** flip R1: the canonical config never runs the blend, and even with the gate open the incremental effect is consistent but not significant. No frozen surface moved. |

---

## 1. The dormant lever

`LineageFlowAdapter.__init__` accepts `classifier_aware_restart: bool = False`
(`lineageflow.py:1627`). When set, `apply_restart_distribution` replaces the
scalar `m = 1 - beta` restart blend with a **per-position memory vector**
`m_vec[l]` derived from a per-position classifier-confidence vector
(`lineageflow.py:2052-2073`):

```
m_vec[l] = clip(base_m * (1 + alpha * (c[l] - mean_c)), 0, 1)
```

Confidence `c[l]` comes from the upstream 657M `LineageFlowClassifier` when
reachable, else from the adapter-internal max-probability proxy
(`_lineageflow_classifier_confidence_proxy`). The bias is centred on the mean
confidence, so it is mass-preserving: when all positions share the same
confidence the policy **reduces exactly to the scalar blend** (documented at
`lineageflow.py:978-979`).

Before GAP-40 the symbol `classifier_aware_restart` appeared **only** inside
`adaptive_reflow/adapters/lineageflow.py` — no driver, tool, or reproduce script
referenced it. The canonical factory `default_lineageflow_adapter`
(`lineageflow.py:3006`) did not expose it either.

## 2. The fix (additive, default off)

### 2.1 Canonical R1/K4/K5 driver — `tools/gen_lineageflow_n1000_fastas.py`

* `_build_lineageflow_adapter(..., classifier_aware_restart=False, classifier_alpha=1.0)`
  forwards both kwargs to the `LineageFlowAdapter` constructor.
* `_write_framework_arm(..., classifier_aware_restart=False, classifier_alpha=1.0)`
  threads them to the adapter factory.
* New CLI flags `--classifier-aware-restart` (store_true) and `--classifier-alpha`
  (float, default 1.0); both recorded in `manifest.json`.
* New manifest key `effective_n_rounds` — the honest disclosure of the
  restart-blend gate outcome (see §3).

### 2.2 Factory + generic driver

* `default_lineageflow_adapter` (`lineageflow.py:3006`) gains
  `classifier_aware_restart` / `classifier_alpha` kwargs (default off).
* `tools/eval/framework.py::_resolve_adapter` gains the two params and forwards
  them **only when the factory signature accepts them** (mirroring the existing
  `restart_min_nfe` / `nfe_budget` / `weights_path` gating).
* `tools/eval/sweep.py::_run_cell` / `_run_cell_impl` and `tools/eval/cli.py`
  thread the flags end-to-end (`--classifier-aware-restart` / `--classifier-alpha`).

Every default is the pre-GAP-40 no-op, so the D.4 regression vectors and all
existing call shapes are byte-stable.

## 3. The load-bearing structural finding

`tools/gen_lineageflow_n1000_fastas.py:545-547`:

```python
effective_n_rounds = int(N_ROUNDS)
if int(NFE_PER_RECORD) < int(RESTART_MIN_NFE):
    effective_n_rounds = 1
```

The canonical R1 command (per `docs/audit/wave280-p-r1-sweep-result.md` §2.2) is

```
tools/gen_lineageflow_n1000_fastas.py --seed <N> --n 1000 \
  --upstream-eval-len-bias short --nfe 10 --n-rounds 3 --temperature 1.0
```

with `--restart-min-nfe` at its default **20**. Since `10 < 20`, the gate fires
and `effective_n_rounds = 1`: the framework arm runs a **single `solve_ode`
pass with no `apply_restart_distribution` chain at all**.

**Consequence:** the canonical R1 +116% framework-vs-baseline headline is
produced entirely by the adapter's real ESM-2 forward pass (vs the bare-RNG
baseline arm). The namesake restart-blend contributes **nothing** to the
canonical R1 number — neither the scalar blend nor the classifier-aware blend is
ever invoked. This is the mechanism-level explanation of the standing note that
*"R1 is init-attributed"*.

Empirical confirmation: at canonical config (N=200, seed 42) the legacy and
classifier-aware framework arms are **byte-identical**
(`md5 027a0f013658f4e725987f0a8c53a5ca`), while with the gate open
(`--restart-min-nfe 5`) they differ.

## 4. Gate-open A/B (N=200, seed 42, `--restart-min-nfe 5`)

Config: `--nfe 10 --n-rounds 3 --restart-min-nfe 5 --upstream-eval-len-bias short
--temperature 1.0`, N=200 per arm, real-forward (`force_mode="auto"`,
`framework_fallback_per_family_count == {}`), GPU 0. Hit counter identical to the
canonical R1 protocol:
`hmmscan --noali --cpu 32 --tblout <out> --acc Pfam-A.hmm <fasta>`, hits =
non-comment tblout lines.

### 4.1 Totals

| arm | total hits | records with ≥1 hit | hits / record |
|---|---:|---:|---:|
| baseline (bare RNG) | 37 | 30 | 0.1850 |
| framework — legacy scalar blend | 38 | 32 | 0.1900 |
| framework — **classifier-aware** | **44** | **42** | **0.2200** |

### 4.2 Per-record statistics

| comparison | Mann-Whitney `p` (greater) | Fisher exact `p` on ≥1 hit |
|---|---:|---:|
| classifier-aware vs legacy | 0.1174 | 0.1232 |
| classifier-aware vs baseline | 0.0726 | 0.0760 |
| legacy vs baseline | 0.3957 | 0.4451 |

### 4.3 Per-family breakdown (total hits)

| family | baseline | legacy | classifier-aware |
|---|---:|---:|---:|
| PF00005.27 | 6 | 8 | **13** |
| PF00072.24 | 11 | **13** | 9 |
| PF00183.19 | 5 | 7 | **13** |
| PF02517.18 | **15** | 10 | 9 |

## 4b. Decisive test — canonical N=1000, 3 seeds, gate-open

Config: `--n 1000 --nfe 10 --n-rounds 3 --restart-min-nfe 5
--upstream-eval-len-bias short --temperature 1.0`, seeds `{42, 43, 44}`, arms
`{legacy, car}`, `force_mode="auto"` (real-ckpt), GPU 0,
`framework_fallback_per_family_count == {}` (zero fallback on every arm).
Same hmmscan hit counter as the canonical R1 protocol. The baseline arm is
byte-stable across the two arms (same seed → identical `baseline.fasta`), and
the legacy-vs-car `framework.fasta` md5s differ on all 3 seeds (the lever is
active). Evidence: `verification_outputs/gap40-lineageflow-classifier-aware-restart/n1000_gate_open/`.

### 4b.1 Per-seed totals

| seed | baseline (bare RNG) | legacy (scalar blend) | car (classifier-aware) |
|---:|---:|---:|---:|
| 42 | 158 | 257 | **271** |
| 43 | 159 | 265 | **269** |
| 44 | 174 | 245 | **265** |

### 4b.2 Seed-level pooled statistics (n=3, df=2) — canonical R1 protocol

| comparison | per-seed diffs | mean diff | `d_z` | `t` | `p_two` | `p_bonf_rlevel` | 3/3 dir | STRONG? |
|---|---|---:|---:|---:|---:|---:|:--:|:--:|
| **car vs legacy** | [14, 4, 20] | +12.67 | **1.567** | 2.714 | 0.1132 | **1.0** | ✓ | **no** |
| car vs baseline | [113, 110, 91] | +104.67 | 8.773 | 15.196 | 0.0043 | 0.0688 | ✓ | no |
| legacy vs baseline | [99, 106, 71] | +92.00 | 4.968 | 8.604 | 0.0132 | 0.2118 | ✓ | no |

The pre-registered STRONG bar (`d_z > 0.8` ∧ `p_bonf_rlevel < 0.003125` ∧ 3/3
direction-consistent) is **not met** by any comparison: `d_z` and direction pass
for all three, but the strict R-level Bonferroni threshold is unreachable at
n=3 (it requires `p_two < 1.95e-4`, i.e. `t > 30.6` / `d_z > 17.7`).

### 4b.3 Per-record paired t (df=999) + DerSimonian–Laird meta

| comparison | per-seed `d_z` | per-seed `p` | DL `d_pooled` | DL `z` | DL `p_two` | `p_bonf,k=7` |
|---|---|---:|---:|---:|---:|---:|
| **car vs legacy** | +0.025 / +0.008 / +0.040 | 0.43 / 0.80 / 0.21 | **+0.024** | 1.33 | **0.184** | 1.0 |
| car vs baseline | +0.171 / +0.164 / +0.136 | 8.0e-8 / 2.8e-7 / 1.9e-5 | +0.157 | 8.53 | 1.4e-17 | 1.0e-16 |
| legacy vs baseline | +0.154 / +0.155 / +0.109 | 1.4e-6 / 1.1e-6 / 5.9e-4 | +0.139 | 7.58 | 3.3e-14 | 2.3e-13 |

The framework-vs-baseline effect (both arms) is highly significant per-record,
but the **incremental** lever effect (car vs legacy) is not significant under
either the seed-level or the per-record statistic.

### 4b.4 Relation to the canonical R1 headline

The canonical Wave 158 R1 `framework = 342` headline is a **synthetic-velocity-field**
number; the real-ckpt basis (this run's `force_mode="auto"`) gives framework
`= 271` on seed 42 (already disclosed in `docs/CLAIMS.md` — the "real-ckpt
materialization addendum"). This run is therefore the real-ckpt family. The
restart-blend blend is not required for the R1 headline; the framework-vs-baseline
gap is driven by the adapter forward pass, consistent with §3 ("R1 is
init-attributed"). Opening the gate neither breaks nor strengthens the headline.

## 5. Interpretation

1. **The lever works mechanically.** With the gate open, the real
   (`force_mode="auto"`) path produces a non-trivial per-position memory vector
   (instrumented `c.std` 0.027–0.033, `m_vec` range 0.457–0.665 around
   `base_m = 0.5`), and the framework FASTA changes.
2. **Directionally positive, not significant.** At N=200 single seed the
   classifier-aware arm gains +6 hits over the legacy scalar blend (+15.8%
   hits/record; +10 records crossing the ≥1-hit threshold) and +7 over baseline
   (+18.9%). `p ≈ 0.07–0.12` — a trend, not a result. The N=1000 3-seed sweep
   (§4b) confirms the direction (3/3 seeds, seed-level `d_z=1.567`) but the
   effect remains **non-significant** (seed-level `p_bonf_rlevel=1.0`;
   per-record DL `p=0.184`).
3. **Family-dependent.** The gain is concentrated in PF00005.27 (+5) and
   PF00183.19 (+6); the classifier-aware arm *loses* ground on PF00072.24 (−4)
   and PF02517.18 (−1) relative to the legacy blend. The net +6 is therefore not
   a uniform mechanism uplift.
4. **The canonical R1 headline is untouched.** Because the canonical config
   closes the restart-blend gate, GAP-40 changes **no** committed R1 number. To
   make the lever measurable at all, the gate must be opened
   (`--restart-min-nfe 5`), which is a *different* configuration from the
   canonical one.

## 6. Honest scope / what is NOT claimed

* The canonical-scale (N=1000) 3-seed gate-open sweep **has now been run**
  (§4b). It is the decisive test: the lever's incremental effect is consistent
  (3/3 seeds, seed-level `d_z=1.567`) but **not significant** under either the
  canonical seed-level protocol or the per-record DL meta. It does **not** flip R1.
* No promotion of any R1/K4/K5/K7 verdict. The cell statuses are unchanged.
* No claim that opening the gate is "the fix" for R1 — the N=1000 data confirm a
  consistent-but-non-significant trend; the N=200 family split (wins 2 of 4
  families) is not resolved at N=1000 either.

## 7. Acceptance gates

* `tools/verify_submission_readiness.py` — `READY_WITH_SKIPS:mypy_0` (known/accepted)
* `tools/check_claims_consistency.py` — no drift
* `tools/check_docs_against_code.py` — OK
* `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` — 72 passed
* `ruff check` — clean
* `mkdocs build --strict` — exit 0

## 8. References

* `adaptive_reflow/adapters/lineageflow.py:925` — `LineageFlowClassifierAwareRestart`
* `adaptive_reflow/adapters/lineageflow.py:1627` — `classifier_aware_restart` ctor arg
* `adaptive_reflow/adapters/lineageflow.py:2052` — opt-in branch in `apply_restart_distribution`
* `adaptive_reflow/adapters/lineageflow.py:3006` — `default_lineageflow_adapter`
* `tools/gen_lineageflow_n1000_fastas.py:545` — restart-blend gate
* `docs/audit/wave280-p-r1-sweep-result.md` §2.2 — canonical R1 command
* `docs/audit/gap39-flowmol3-real-restart-blend.md` — sibling dormant-lever fix
