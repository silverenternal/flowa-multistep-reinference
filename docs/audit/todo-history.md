# todo.json history — state, ledger, assessment (moved out 2026-10-13)

**Date:** 2026-10-13
**Why this file exists:** the user asked for `todo.json` to become a pure
open-work surface ("本文件只回答现在还要做什么"). Everything that is *state,
history, or assessment* rather than *open work* was moved here verbatim, so no
fact was lost. `todo.json` now points at this file.
**Frozen surfaces:** untouched by the move.

---

## 1. Binding policy (still in force)

- **No push.** Every commit carries the footer `(USER AUTHORIZED, NO PUSH)`.
- **Frozen surfaces** (change only via additive addenda backed by a new
  measurement; never by wording alone):
  `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
  `docs/drafts/paper-A-final.md`, `docs/drafts/paper-A-final.tex`,
  `docs/drafts/paper-A-final.pdf`, `tnnls_submission/**`.
- **Vendored upstream** `data/**` stays byte-identical.
- **Gate chain** (run before every commit):
  1. `python tools/verify_submission_readiness.py`
  2. `python tools/check_claims_consistency.py`
  3. `python tools/check_docs_against_code.py`
  4. `python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q`
  5. `ruff check adaptive_reflow/ tests/ scripts/ tools/`
  6. `mkdocs build --strict`

## 2. Gate snapshot (as of 2026-10-13)

| gate | result |
|---|---|
| D.4 byte-stable | 30/30 PASS |
| ruff | 0 findings in scope |
| mkdocs --strict | PASS (exit 0) |
| claims consistency | PASS, no drift |
| docs-vs-code | OK, 4143 claims verified |
| readiness verifier | READY_WITH_SKIPS: mypy_0 (mypy absent in sandbox), exit 0 |
| checkpoint SHA-256 | 4/4 PASS |
| import acyclic | PASS |
| vendored `data/` | byte-identical |
| pytest CI subset | 5055 passed / 171 skipped / 50 deselected / 12 xfailed / 0 failed (last full run 2026-10-12) |

## 3. Manuscript + venue

- Title: *FlowA: Geometry-Aware State-Intervention Reformulation for Frozen
  Flow-Matching Checkpoints*
- PDF: `docs/drafts/paper-A-final.pdf` (11 pages, IEEEtran-journal)
- Sources: `docs/drafts/paper-A-final.md`, `docs/drafts/paper-A-final.tex`
- Figure: `docs/figures/fig9_cell_evidence_comparison.png`
- Primary venue: IEEE TNNLS (CAS Tier-1 / JCR Q1). Backups in order: TIP,
  Pattern Recognition, Neural Networks, EAAI. Self-assessed acceptance
  probability: not recorded.

## 4. Evidence ledger — 11 headline cells

Verdicts and numbers verbatim from paper §7.2/§7.11; no number changed here.
Tuned-baseline / straw-man status is GAP-12's — see
`docs/audit/gap12-tuned-baseline.md`.

| cell | model | metric | status | value | caveat |
|---|---|---|---|---|---|
| R1 | LineageFlow | HMMER hits | PARTIAL | synthetic 158 → 342 (+116%); real-forward 3/3 WINS 158/159/174 → 275/272/259 (DL d_pooled=+0.156, z=8.49, I²=0) | effect small (per-seed d_z ≈ 0.13–0.17); the win is carried by the per-record random **INIT**, not the restart-blend |
| R2 | Kanzi | RMSD (Å) | STRONG framework-WINS | 0.9020 → 0.8798 (−0.022; d_z=−0.0990, Bonferroni-sig) | synthetic-input coordinate basis; small effect; "STRONG" = significance, not the effect-size bar; structurally compute-invariant (DAE encode has no NFE knob) |
| R3 | FlowMol3 | fg_dev | PARTIAL / not significant | 3-seed N=1000 −0.0377 (framework-WINS direction, p=0.559); the advantage holds at baseline NFE 500 (−0.0614, p=0.165) and 1000 (−0.0399, p=0.627) → straw-man refuted at 2× and 4× | — |
| R5a | 2D Two Moons | W₂ | TIE | \|Δ\| = 0.0091 < 0.01 floor; persists at n=7 and n=10 | — |
| R5b | CIFAR-10 RF | FID | CONDITIONAL | n_rounds=1 wins at matched NFE=50 (2/4 schedulers, −1.2 % to −2.1 %); dies under a tuned baseline (4/4 losses at baseline NFE=200); n_rounds ≥ 2 regresses +20 % to +31 % | — |
| R5c | MNIST FM | FID | STRONG (smoke ckpt) / REGIME-DEPENDENT | smoke −28.43 % (d_z=−13.18) and survives a step-tuned baseline (baseline is step-insensitive); production ckpt +10.37 % baseline-WINS | — |
| R6 | LineageFlow k6 | pLDDT / scPerp | STRONG on scPerp; counterfactual on pLDDT | scPerp cluster-robust d_z=−4.019; hard-tier counterfactual d_z=+1.189; beats vanilla + Fast-DLLM + AB-Cache + LeDiFlow (16-cell Table B, Bonferroni-sig) | the pLDDT live 3-seed sweep landed at pooled d_z=+0.1466 (< the +0.2235 bar, so not promoted), but its tier structure reproduces: hard d_z≈+1.10 and easy d_z≈−0.72 on 3/3 seeds — docs/audit/gap01-r6-live-wiring.md §3.1/§4 |
| K1 | FlowMol3 RDKit-validity | validity | NOT-SIGNIFICANT at K-level α | p_b=0.5676 vs α_K=0.0125; framework pb_validity exceeds the baseline at matched NFE and at 2×/4× baseline NFE (the baseline's pb_validity *degrades* with more steps) → straw-man refuted | — |
| K4 | LineageFlow HMMER length-bias | length-bias | SUPPORTED at K-level α | cluster-robust d_z=+0.84, p_b=0.009 | — |
| K5 | LineageFlow HMMER delta | delta hits | SUPPORTED / SUPPORTS-WITH-CAVEAT | cluster-robust d_z=+1.12, p_b=0.003 | n=3 re-aggregation caveat, pending n ≥ 7 |
| K7 | LineageFlow novelty | novel_pct_pfam_twilight | PARTIAL / direction INVERTED | baseline 46.6 % vs framework 3.7 % novel (framework 12.6× LESS novel); structural-correctness signal preserved | — |

**Verdict distribution:** 4 STRONG (R2, R5b-conditional, R5c-smoke, R6) +
1 TIE (R5a) + 6 PARTIAL/SUPP (R1, R3, K1, K4, K5, K7).

### 4.1 External-method head-to-head extension (GAP-32, 2026-10-14)

R6 was the only cell with a published-external-method comparison (§7.8). GAP-32
extends the same roster (`vanilla` + Fast-DLLM + AB-Cache + LeDiFlow +
framework, seed-matched, Bonferroni-corrected paired t-test, unit = seed) to
**two more cells**. Recorded here as an **observations-only** addendum (no
frozen claim surface moved); full detail in `docs/audit/gap32-headtohead.md`.

| cell | metric | vanilla | best external | framework | framework Δ% | p_bonf | verdict |
|---|---|---:|---:|---:|---:|---:|:---|
| R5c MNIST FM `w16e1_5k` | Fréchet-projection FID ↓ | 24.9115 | 24.6390 (AB-Cache) | **14.3815** | **−42.27** | 4.6 × 10⁻⁴ | framework WINS |
| R3 FlowMol3 | `fg_dev` ↓ | 0.4741 | 0.4154 (Fast-DLLM) | 0.5265 | +11.05 | 1.00 | framework loses (n.s.) |

- **MNIST:** decisive framework win; flowa beats every external arm by ≈ −42 %
  (all Bonferroni-significant, all 3 seeds). The external accelerators each move
  FID by ≤ 1 %.
- **FlowMol3 R3:** framework **does not win** (+11.05 %, n.s.); the external
  accelerators *reduce* `fg_dev` (Fast-DLLM −12.4 %, AB-Cache −5.8 %). This
  head-to-head tests the **coordinate channel** only (the vendored FlowMol3
  sampler is CTMC-based; only the x-channel is a continuous ODE); the framework
  arm is the restart-blend, not the canonical R3 σ = 0.05 prior perturbation.
  R3 N = 250/seed (canonical is 1000) — disclosed.
- **Dropped 3rd cell:** 2D eight-gaussians (framework arm diverges, W₂ +882 %).
- **Net:** the "beats SOTA" claim now stands on **R6 + MNIST**; R3 is an explicit
  counter-example (negative transfer on the molecule coordinate channel).

### 4.2 R3 paired-design fix (GAP-37, 2026-10-15)

GAP-37 asked to raise the power / effect size of the primary cells. Root cause
found: the R3 seed-level test was **not actually paired**. The driver keyed each
batch's prior on the arm name
(`batch_id = f"{arm_name}-seed{seed_base}-batch{batch_idx}"`), so the baseline
and framework arms built **independent** priors — the "paired" t-test was a
two-sample test in disguise, and its seed-to-seed variance was dominated by
nuisance prior noise. A `--shared-prior` flag (a few lines) drops `arm_name`
from the key so both arms build the **same** prior and share the solver seed.
Observations-only addendum; full detail in
`docs/audit/gap37-statistical-power.md`.

| R3 quantity (unit = seed, n = 3) | independent prior (canonical) | shared prior (fixed) |
|---|---:|---:|
| mean_diff fg_dev | −0.03769 | −0.02725 |
| sd_diff | 0.09390 | **0.02502** |
| `d_z` | −0.401 (small) | **−1.089 (large)** |
| seeds same sign | 2/3 | **3/3** |
| seeds @ 80 % power (α=0.05) | 49 | **7** |
| seeds @ 80 % power (Bonferroni α=0.05/7) | 78 | **11** |

- **Acceptance:** GAP-37 asks "medium+ effect size **OR** ≥ 80 % power" — met via
  the large-effect branch (`|d_z| = 1.089 ≥ 0.8`).
- **Honest limit:** at the canonical n = 3 the test is **still n.s.**
  (`p = 0.200`); the fix corrects the *design* (removes nuisance variance), it
  does not manufacture significance. A definitive R3 verdict now needs ~7–11
  seeds instead of ~49–78.
- **Cross-cell power audit** (`tools/gap37_power_audit.py`) makes the replication
  unit explicit: R1 record (n=3000) is adequate at d=0.156, while R3 seed (n=3)
  is not — "underpowered" is not "no effect".
- **Net:** the R3 label in the frozen surfaces is unchanged (PARTIAL / n.s.);
  this records the correct paired design and its large effect size.

### 4.3 Consolidated ablation matrix (GAP-36, 2026-10-15)

GAP-36 asked for **one** table crossing the three axes the generative headline
cells were swept along. Built by `tools/gap36_ablation_matrix.py` (CPU-only) from
two committed matched-NFE runs — **24 rows**:

- **R5b** (CIFAR-10 FM smoke, N=200, NFE=50): rounds {1,2,3} × 4 schedulers.
- **R5c** (MNIST FM, N=1000, NFE=50): 4 checkpoints × 3 schedulers.

Reading: the **sign** of the framework effect tracks the **training-budget axis**
(rounds for R5b, checkpoint for R5c), **not** the scheduler; within a fixed
setting the scheduler moves magnitude only. The decisive cell `w16e1_5k` is
framework-WINS on **all three** schedulers (−25.20 … −25.59 % FID, p_bonf ≤ 1e-6).
Honest caveat: the R5b smoke checkpoint has a degenerate baseline FID ≈ 452, so
its rows are reported for sign/robustness, not magnitude; the two d_z columns are
on different units (per-sample vs paired-chunk). Aggregation-only, no new
experiments — `docs/audit/gap36-ablation-matrix.md`.

### 4.4 Shared-prior fix applied to the remaining arm-keyed drivers (GAP-38, 2026-10-15)

GAP-37 found the arm-keyed-prior defect in **one** driver and fixed it. GAP-38
applies the same additive `--shared-prior` flag (default off = byte-stable) to
the **five** other drivers that still carried it: `tools/wave87_n1000_sweep.py`,
`tools/run_sota_flowmol3_v2_adapter_experiment.py`,
`tools/run_sota_graphbfn_experiment.py`, `tools/run_sota_cifar_experiment.py`,
`scripts/wave235_p4_flowmol3_3seed.py`. Bounded A/B on the canonical K1/R3
driver (`wave87`, N=100, NFE=250, `nfe_batch=100`, seeds 42/43/44):

| metric | mode | mean Δ | SD | d_z |
|---|---|---:|---:|---:|
| `fg_dev` | legacy | +0.0939 | 0.3591 | +0.261 |
| `fg_dev` | shared | −0.0132 | **0.1306** | −0.101 |
| `pb_validity_pct` | legacy | +0.273 | 0.202 | **+1.351** |
| `pb_validity_pct` | shared | +0.032 | **0.115** | +0.279 |

**Reading:** the shared prior is a real **design** correction (cross-seed SD
collapses 2.75× / 1.76×) but it does **not** flip the near-miss cells into
wins. For K1 `pb_validity` the apparent framework advantage **shrinks**
(`d_z +1.35 → +0.28`) — the legacy number was partly nuisance-prior noise.
Consistent with GAP-37's honest limit. GraphBFN was not testable (no usable
weights). Observations-only; no frozen surface moved —
`docs/audit/gap38-shared-prior-thorough.md`;
evidence `verification_outputs/gap38-shared-prior-thorough/`.

### 4.5 Real FlowMol3 restart-blend wired into the R3/K1 framework arm (GAP-39, 2026-10-15)

GAP-38's own recommendation pointed at the FlowMol3 restart-blend wiring gap.
The canonical R3/K1 driver's framework arm was **not** the framework's
restart-blend: it applied a coordinate-only single-shot Gaussian proxy
(`x += N(0, 0.05)`) and never called the adapter's real
`apply_restart_distribution` (all three channels). GAP-39 wires the real blend
(additive `--real-restart-blend`, default off = byte-stable) in
`scripts/wave338_p5_r3_n1000_paired.py`, and corrects the stale "size-mismatch
bug" comment in the SOTA harness (bug fixed at `flowmol3_v2_adapter.py:1299`;
harness gains `--restart-blend`). Canonical A/B, N=1000, NFE=250, seeds
42/43/44 (legacy reproduces the committed `r3_n1000_3seed_fixed_q4_2026`
bit-for-bit):

| metric | mode | mean Δ | SD | `d_z` | `p` | seeds fw-favourable |
|---|---|---:|---:|---:|---:|---:|
| `fg_dev` (R3) | legacy | −0.03769 | 0.09390 | −0.401 | 0.559 | 2/3 |
| `fg_dev` (R3) | real blend | −0.05476 | 0.15262 | **−0.359** | 0.598 | 2/3 |
| `pb_validity_pct` (K1) | legacy | +0.0852 | 0.13064 | +0.652 | 0.376 | 2/3 |
| `pb_validity_pct` (K1) | real blend | +0.1410 | 0.15313 | **+0.921** | 0.252 | **3/3** |

**Reading:** the faithful all-channel blend lifts **K1 `pb_validity` to a large
effect** (`d_z +0.65 → +0.92`, 3/3 seeds framework-favourable, legacy seed-43 tie
gone) but does **not** flip **R3 `fg_dev`** (mean improves, SD grows, `d_z` flat).
Neither cell is significant at n=3. The fix corrects the *mechanism*, it does not
manufacture significance. Observations-only; no frozen surface moved —
`docs/audit/gap39-flowmol3-real-restart-blend.md`;
evidence `verification_outputs/gap39-flowmol3-real-restart-blend/`.

### 4.6 LineageFlow classifier-aware restart wired + the R1 gate degeneracy (GAP-40, 2026-10-16)

The next dormant lever from the same menu. `LineageFlowClassifierAwareRestart`
(`adaptive_reflow/adapters/lineageflow.py:925`) replaces the scalar restart blend
with a per-position memory vector `m_vec[l] = clip(base_m + α·(c[l]−mean_c),0,1)`
derived from a per-position classifier-confidence vector. Before GAP-40 the
symbol appeared **only** inside the adapter module — no driver, tool, or factory
referenced it. GAP-40 wires it additively (`--classifier-aware-restart` /
`--classifier-alpha`, default off) through
`tools/gen_lineageflow_n1000_fastas.py` (R1/K4/K5) and
`default_lineageflow_adapter` → `tools/eval/framework.py` → `sweep.py` → `cli.py`.
(The formula was previously documented as the multiplicative form
`base_m·(1+α·(c−mean_c))`; GAP-40b corrected it to the additive form the code has
always used — see §4.7.)

**Load-bearing structural finding.** At the **canonical R1 config** the
restart-blend gate is **closed**: `tools/gen_lineageflow_n1000_fastas.py:545`
degenerates `n_rounds` to 1 when `nfe < restart_min_nfe`, and the canonical
command uses `--nfe 10` with the default `--restart-min-nfe 20`. The canonical R1
framework arm is therefore a **single `solve_ode` pass** — neither the scalar nor
the classifier-aware blend is ever invoked, so the +116% R1 headline is produced
entirely by the adapter's real ESM-2 forward (vs the bare-RNG baseline). This is
the mechanism-level explanation of the standing "R1 is init-attributed" note.
Empirically: at canonical config the legacy and classifier-aware framework arms
are byte-identical (`md5 027a0f01…`).

**Gate-open bounded A/B** (N=200, seed 42, `--restart-min-nfe 5`,
`force_mode="auto"`, zero fallback; canonical HMMER counter):

| arm | total hits | records ≥1 hit | hits/record |
|---|---:|---:|---:|
| baseline (bare RNG) | 37 | 30 | 0.1850 |
| framework — legacy scalar blend | 38 | 32 | 0.1900 |
| framework — classifier-aware | **44** | **42** | **0.2200** |

`car vs legacy` MWU `p=0.117` / Fisher `p=0.123`; `car vs baseline` `p=0.073`.
Directional win, **not significant** at N=200 single seed, and **family-dependent**
(wins PF00005.27 +5 and PF00183.19 +6; loses PF00072.24 −4 and PF02517.18 −1).

**Decisive test — canonical N=1000, 3 seeds, gate-open** (seeds 42/43/44,
`--nfe 10 --n-rounds 3 --restart-min-nfe 5`, `force_mode="auto"`, zero fallback;
canonical HMMER counter). Per-seed totals (baseline / legacy / car):

| seed | baseline | legacy (scalar blend) | car (classifier-aware) |
|---:|---:|---:|---:|
| 42 | 158 | 257 | **271** |
| 43 | 159 | 265 | **269** |
| 44 | 174 | 245 | **265** |

Seed-level pooled (n=3, df=2): `car vs legacy` mean **+12.67** hits,
`d_z=1.567`, **3/3 direction-consistent**, but `p_bonf_rlevel=1.0` → **NOT
STRONG** (the pre-registered bar needs `p_two<1.95e-4`, i.e. `d_z>17.7` at n=3 —
unreachable for any realistic effect). Per-record paired-t DL meta
`d_pooled=+0.024`, `z=1.33`, `p=0.184` → **NOT significant**. The lever roughly
doubles the framework-vs-baseline seed-level effect size (legacy `d_z=4.97` →
car `d_z=8.77`), and the framework-vs-baseline effect is highly significant
per-record (DL `d_pooled=+0.157`/`+0.139`), but the **incremental** lever effect
is not significant under either statistic.

**Reading:** the lever is real and load-bearing once the gate is open, but it does
**not** flip R1 — the canonical R1 number is untouched (the gate is closed there),
and the gate-open lift is consistent but non-significant at N=1000 (same category
as GAP-38 / GAP-39). Observations-only; no frozen surface moved —
`docs/audit/gap40-lineageflow-classifier-aware-restart.md`; evidence
`verification_outputs/gap40-lineageflow-classifier-aware-restart/`
(`n200_gate_open/`, `canonical_gate_closed/`, `n1000_gate_open/`).

### 4.7 Non-conserving bias modes — the "add/reduce memory one-sidedly" hypothesis (GAP-40b, 2026-10-16)

Follow-up to GAP-40. The GAP-40 policy is *mass-preserving*: `m_vec` is centred
on `base_m = 1 − β`, so the mean memory is unchanged and the classifier bias only
**redistributes** memory from uncertain to confident positions. GAP-40b adds a
`bias_mode` selector so the "add memory where confident without removing it
elsewhere" hypothesis can be tested directly:

```
centred[l] = c[l] − mean_c
m_vec[l]   = clip(base_m + alpha * bias(centred[l]), 0, 1)

bias(x) = x          # "centered" (default)  — mass-preserving
bias(x) = max(x, 0)  # "positive"           — one-sided boost
bias(x) = min(x, 0)  # "negative"           — one-sided reduction
```

`classifier_bias_mode` is threaded additively (default `centered`, byte-stable)
through `LineageFlowAdapter.__init__` → `default_lineageflow_adapter` →
`tools/gen_lineageflow_n1000_fastas.py` (`--classifier-bias-mode`, recorded in
`manifest.json`) → `tools/eval/framework.py::_resolve_adapter` → `sweep.py` →
`cli.py`; unknown modes raise `lineageflow_classifier_bias_mode_unknown`; 7 CPU
conformance tests added. The class docstring was also corrected (the additive
form `base_m + alpha*(c−mean_c)`, not the multiplicative form it had stated) —
doc-only, no behaviour change.

**Screen** (N=200, seed 42, gate-open):

| arm | total hits | records ≥1 | hits/record |
|---|---:|---:|---:|
| baseline | 37 | 30 | 0.1850 |
| legacy | 38 | 32 | 0.1900 |
| centered | 44 | 42 | 0.2200 |
| positive | 44 | 41 | 0.2200 |
| **negative** | **47** | 40 | 0.2350 |

`positive` is **byte-inert vs `centered`** (44 == 44) — the "add where confident"
hypothesis gains nothing. `negative` is nominally highest but
`negative vs centered` MWU `p=0.556` (noise at N=200 single seed). Advance
`negative` to the decisive N=1000 sweep.

**Decisive test — N=1000, 3 seeds, gate-open** (baseline/legacy/centered reused
from the archived GAP-40 arms; baseline md5 byte-verified equal):

| seed | baseline | legacy | centered | negative |
|---:|---:|---:|---:|---:|
| 42 | 158 | 257 | 271 | 277 |
| 43 | 159 | 265 | 269 | 272 |
| 44 | 174 | 245 | 265 | 260 |

Seed-level pooled (n=3, df=2): **`negative vs centered` diffs [6, 3, −5]**,
mean **+1.33** hits, `d_z=0.234`, only **2 of 3** seeds positive,
`p_two=0.724`. Per-record paired-t DL meta `d_pooled=+0.0022`, `z=0.12`,
`p=0.902` — a **wash**. `negative vs legacy` is nominally larger than
`centered vs legacy` (DL `d=+0.0437`, uncorrected `p=0.017` vs `+0.024`,
`p=0.184`) but still fails the family-wise bar (`p_bonf,k=7 = 0.118`).

**Reading:** non-conservation does **not** strengthen the lever. The
mass-preserving vs one-sided distinction is not the binding constraint — the
limiting factor is statistical power at n=3, not the memory-conservation choice.
Same category as GAP-38/39/40. Observations-only; no frozen surface moved —
`docs/audit/gap40-lineageflow-classifier-aware-restart.md` §4d; evidence
`verification_outputs/gap40b-lineageflow-bias-modes/` (`n200_screen/`,
`n1000_negative/`).

### 4.8 R1 init dose-response — the init is a load-bearing, model-mediated knob (GAP-34, 2026-10-16)

Closes GAP-34 via acceptance path (a): *"show the init is a legitimate,
load-bearing part of the mechanism with a supporting experiment."* D-004b had
shown the R1 win is the per-record random init, not the blend; GAP-34 asks
whether that init is a real mechanism component or a tool artifact.

`tools/sweep_gap34_init_dose.py` sweeps the AA-logit temperature `τ` of the
per-record init simplex `softmax(randn(L, AA_VOCAB)·τ)` — `τ=0` is the
near-uniform canonical init, `τ=1` is the D-004b convention — holding the
length/family RNG and solver seeds fixed; single-pass init-only arm, N=1000,
`--nfe 10`, canonical HMMER counter. Baseline (arm A) = 158/159/174.

| `τ` | seed 42 | seed 43 | seed 44 | mean | sd |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 0 | 0 | 0 | **0.0** | 0.0 |
| 0.25 | 261 | 266 | 273 | 266.7 | 6.0 |
| 0.5 | 290 | 276 | 241 | 269.0 | 25.2 |
| **1.0** | 298 | 274 | 290 | **287.3** | 12.2 |
| 2.0 | 62 | 247 | 314 | 207.7 | 130.5 |

**Findings.** (i) `τ=0` collapses to **0 hits on all 3 seeds** and `τ=1` gives
+287.3 hits (paired `t=40.73`, `p=6.0e-4`) — the init is **decisively
load-bearing and model-mediated** (a random init cannot raise family-consistent
HMMER hits without the model). (ii) The `τ=1.0` row reproduces the D-004b
init-only arm (298/274/290) **exactly** — anchored, not re-derived. (iii) The
dose-response is **non-monotone / inverted-U** (Spearman `ρ` per seed
0.40/0.30/0.90, mean 0.53), peaking at the canonical `τ=1.0`; `τ=2.0` falls to
72.3 % of peak. (iv) **Honest caveat:** the `τ=2.0` fall is seed-heterogeneous
(seed42 62, seed43 247, seed44 314; sd 130.5 vs 12.2 at `τ=1.0`), so the shape is
*"an interior optimum at the canonical `τ=1` with a high-variance high-`τ`
regime"*, not a clean dome.

**Reading:** the canonical init setting is the interior optimum of a
model-mediated mechanism knob. R1's win is therefore a legitimate mechanism win
(the restart step's required per-record diversity), not a tool artifact. R1
verdict unchanged (PARTIAL). Observations-only; no frozen surface moved —
`docs/audit/gap34-r1-init-dose.md`; evidence
`verification_outputs/gap34-r1-init-dose/`.

## 5. R1 real-forward saga (D-004 / D-004b)

- **D-004 defect:** the checkpoint-compat shim registered a bare core module
  with no `__path__`, shadowing the vendored upstream `core/`, so the adapter
  integrated an **all-zero velocity field**; every pre-fix "real-ckpt" run was
  zero-field. Fixed in `bf66aa4`. With the real field live the framework arm
  collapsed to 0 hits (`docs/audit/r1-d004-remeasure.md`).
- **D-004b fix:** `1264cec` — on the real-classifier path the restart fresh
  state is a per-record random simplex `softmax(randn(L, AA_VOCAB))`; the
  synthetic path is byte-unchanged (D.4 preserved).
- **Result:** 3/3 seeds framework-WINS 158/159/174 → 275/272/259 (per-record
  d_z=+0.169/+0.170/+0.129; DL d_pooled=+0.1559, z=8.49, I²=0, Bonferroni-sig
  at k=7).
- **Attribution (DONE 2026-10-13):** init-only 298/274/290 ≈ framework
  275/272/259 ≫ baseline 158/159/174 (B−A=+123.7, p=0.0043; B−C=+18.7,
  p=0.164 n.s.) ⇒ the win is the **per-record random INIT**, not the
  restart-blend. R1 stays PARTIAL. See `docs/audit/r1-d004b-attribution.md`.
- **Mechanism (DONE 2026-10-16, GAP-34):** the init dose-response shows the
  init is a **load-bearing, model-mediated** knob (τ=0 → 0 hits; τ=1 → +287.3,
  paired t=40.73, p=6.0e-4) with an interior optimum at the canonical τ=1 —
  so the attribution is a legitimate mechanism component, not a tool artifact.
  See §4.8 / `docs/audit/gap34-r1-init-dose.md`.
- **Caveat:** the D-004b restart init is a tool-convention surrogate, not the
  upstream intervention sampler.
- **Evidence:** `verification_outputs/r1_3seed_d004b_q4_2026/`;
  `verification_outputs/r1_d004b_attribution_q4_2026/`.

## 6. Closed gaps

| gap | closed | one-line outcome |
|---|---|---|
| GAP-02-R3-N1000 | 2026-10-13 | real 3-seed N=1000 R3 measurement, valid-yield 100 % — `docs/audit/gap02-r3-n1000-resolved.md` |
| GAP-03-R1-3SEED | 2026-10-13 | clean 3-seed real-forward basis via D-004b; its residual (attribution control) is now DONE |
| GAP-04-R5B-ROUNDS | 2026-10-13 | boundary CONFIRMED (n_rounds=1 win/tie 3/4; ≥2 regress 3/4 by +20–31 % FID); disclosure — the framework arm is seed-invariant, so the seeds probe the baseline axis only — `docs/audit/gap04-r5b-rounds.md` |
| GAP-05/06/07/08 | 2026-10-12 | framing / honesty items already in the live manuscript |
| GAP-09-THEORY | 2026-10-13 | q=mK<1 + the exact blend identity predict the R5b sign 4/4 — `docs/audit/gap09-reinference-diagnostic.md` |
| GAP-14 | 2026-10-13 | novelty-differentiation paragraph added |
| GAP-16 | 2026-10-13 | 31 deferred reviewer-facing gaps triaged |
| GAP-17-K2K6 | 2026-10-13 | honest disclosure retained (K2 closed; K6 env-blocked by LFS-pointer stubs; K5 un-pinnable) — `docs/audit/gap17-k2k6-disclosure.md` |
| GAP-18/19/21 | 2026-10-13 | dead links + Q1-odds + test-citation cluster fixed |
| GAP-22 | 2026-10-13 | R2/R1 rubric disclosure satisfied (no label change) |
| GAP-23 | 2026-10-13 | retracted — R2 significance is not a pairing artifact |
| D-004B-ATTRIBUTION | 2026-10-13 | init-only ≈ framework ≫ baseline, so the R1 win is the random INIT — `docs/audit/r1-d004b-attribution.md` |
| GAP-24-BOUNDARY-LAW | 2026-10-13 | one falsifiable regime law `blend improves iff q < sqrt((1+m)/(1-m))` (Theorem-5 Eq. 7 closed form); 45/45 off-boundary matches on the R5b field, 15/16 headline-cell directions — `docs/audit/gap24-boundary-law.md` |
| GAP-25-R1-BLEND-ISOLATION | 2026-10-13 | the R1 win is the per-record random INIT (B ≈ C, B ≫ A); blend marginal bounded ≤ +46 hits (≤ 28 % of baseline) — `docs/audit/gap25-r1-blend-isolation.md` |
| GAP-26-R5B-REGIME | 2026-10-13 | no tested R5b protocol survives a tuned baseline (0/4 at baseline NFE=200); the GAP-24 law reproduces the 2/4→1/4→0/4 flip — `docs/audit/gap26-r5b-regime.md` |
| GAP-27-R3-POWER | 2026-10-13 | R3 is bounded-marginal (~49 seeds for 80 % power; d_z=−0.40); fixed a seed-level CI defect (1.96 at df=2 → t=4.303; NFE=500 CI had falsely excluded 0) — `docs/audit/gap27-r3-power.md` |
| GAP-28-R6-LIVE-FAITHFUL | 2026-10-13 | the faithful easy-tier direction (β 0.75→0.25) is a DEFINITIVE NULL: pooled d_z +0.1104 < as-designed +0.1466 < bar +0.2235; the GAP-01 §4.3/§4.5 direction-mismatch hypothesis is refuted (easy-tier regression is monotone *increasing* in β_easy); tier isolation exact; secondary finding — the frozen reference tier is uncorrelated with the seed's own baseline on seeds 43/44 (Pearson +0.03/−0.01) — `docs/audit/gap28-r6-faithful.md` |
| GAP-30-R6-TIER-TARGETING | 2026-10-14 | fresh-tier (correctly targeted) 3-seed live re-run recorded: as-designed pooled d_z +0.1604 (↑ from frozen-tier +0.1466, still < bar +0.2235); faithful +0.1103 (null confirmed); under the wrapper's own quantile tier rule the easy tier is the only group that differs (hard/medium byte-identical) and the fresh-easy regression is −0.6562 (β 0.75) → −0.8811 (β 0.25), monotone in β_easy; tier isolation exact (330/330 per seed) — `docs/audit/gap30-r6-fresh-tier.md` |
| GAP-31-R6-LIVE-UPLIFT | 2026-10-14 | three live, non-counterfactual R6 measurements on the seed-matched arms (3 seeds × N=1000): **scPerplexity** (ESM-IF) pooled d_z −0.8393 (framework WINS on every tier: hard −0.7952 / medium −0.8634 / easy −0.8924); **hard-tier pLDDT** anchor d_z +1.1211 (≈ frozen hard-tier counterfactual +1.1889); **uniform arm** (factor 1.0, no tier manipulation) d_z +0.1466 (n=3000) — the framework beats the baseline live with no tier cut; as-designed +0.1604. Honest live ladder: uniform +0.1466 → as-designed +0.1604 → disclosed counterfactual +0.2235 (the tier-aware refinement adds only +0.0138 d_z) — `docs/audit/gap31-r6-live-uplift.md` |
| GAP-32-SOTA-HEADTOHEAD | 2026-10-14 | external-method head-to-head extended beyond R6 to **2 more cells** (seed-matched, Bonferroni-corrected paired statistics): **R5c MNIST `w16e1_5k`** framework-WINS −42.27 % FID (p_bonf 4.6e-4, beats every external arm); **R3 FlowMol3** framework does **not** win +11.05 % fg_dev (n.s.; coordinate-channel restart-blend; external Fast-DLLM/AB-Cache reduce fg_dev). Dropped 3rd candidate 2D eight-gaussians (framework arm diverges). Observations-only; no frozen surface moved — `docs/audit/gap32-headtohead.md` |
| GAP-37-STATISTICAL-POWER | 2026-10-15 | the R3 seed-level "paired" test was **not paired** (driver keyed the prior on `arm_name` → independent priors → two-sample in disguise). A `--shared-prior` flag makes both arms build the SAME prior: R3 `d_z` −0.401 (small) → **−1.089 (large)**, sd 3.75× tighter, 3/3 seeds same sign, seeds-for-80 %-power 49 → 7 (Bonferroni 78 → 11). Acceptance met via the medium+ effect-size branch; n=3 still n.s. (p=0.200). Observations-only; no frozen surface moved — `docs/audit/gap37-statistical-power.md` |
| GAP-36-ABLATION-MATRIX | 2026-10-15 | consolidated **rounds × schedulers × checkpoints** ablation matrix (24 rows, matched NFE=50) assembled from existing runs (R5b rounds × schedulers; R5c checkpoints × schedulers). Reading: the **sign** of the framework effect tracks the training-budget axis (rounds / checkpoint), **not** the scheduler; within a fixed setting the scheduler tunes magnitude only. Decisive cell **`w16e1_5k`** is framework-WINS on all 3 schedulers (−25.2…−25.6 % FID, p_bonf ≤ 1e-6). Aggregation-only; no new experiments; no frozen surface moved — `docs/audit/gap36-ablation-matrix.md` |
| GAP-34-R1-MECHANISM | 2026-10-16 | closed via acceptance path (a): the R1 init dose-response (τ sweep of the per-record init simplex, 3 seeds, N=1000) shows the init is a **legitimate, load-bearing, model-mediated** knob — τ=0 collapses to 0 hits, τ=1 (canonical) gives +287.3 (paired t=40.73, p=6.0e-4) and reproduces the D-004b arm exactly; the dose-response is a non-monotone inverted-U peaking at the canonical τ=1 (honest caveat: the τ=2 fall is seed-heterogeneous). R1 stays PARTIAL — `docs/audit/gap34-r1-init-dose.md` |

## 7. Publication assessment (2026-10-13)

**Question:** can this be published in a CAS Tier-1 / Q1 journal (TNNLS)?

**Verdict:** plausible, but sitting on the decision boundary. The contribution
type (portable training-free re-inference framework + typed contracts +
hash-chained ledger + byte-stable reproducibility + 2 conditional theorems +
mechanism-isolating evidence) is what TNNLS publishes, and the reproducibility
infrastructure is above the venue norm. The gating risk is the **empirical**
axis, not the framework.

**Strong axes**

1. Framework + reproducibility infrastructure (D.4 byte-stable, SHA-256 ledger,
   per-cell recipes, master verifier) — Tier-1 grade.
2. Large effects where the mechanism is load-bearing (R6 hard-tier
   d_z=+1.189; R6 scPerp d_z=−4.019; R5c smoke d_z=−13.18; K4/K5
   d_z=+0.84/+1.12).
3. Head-to-head: beats vanilla + Fast-DLLM + AB-Cache + LeDiFlow on R6, both
   metrics × both NFE.
4. Two theorems with proofs and honest scope.
5. The conditional/regression cells form a coherent "headroom" story, not noise.

**Gating risks**

1. R1's flagship win is now attributed to the random init rather than the
   restart-blend; R3 remains underpowered (n=3, p=0.559).
2. Baseline fairness (GAP-12) — the straw-man baseline is the classic
   framework-paper death, and R5b does not survive it.
3. The conditional/regression cluster still needs one boundary law rather than
   per-cell excuses.
4. Meta-content density: 11 pages carry a lot of audit/disclosure prose; a
   reviewer may read it as engineering-heavy / science-thin.

**Addendum (2026-10-14) — venue fit.** The venue target is a **general ML**
journal (user directive 2026-10-14: do not pigeonhole into an image/CV or
bio/medical venue — the cross-domain breadth, protein + molecule + toy + image,
and the genuine per-domain SOTA improvements are the asset). Candidates (CAS
Tier-1): **IEEE TNNLS** (current, IEEEtran 11pp, IF 10.2), **IEEE TPAMI**
(CCF-A, IF ≈ 20.8), **JMLR**, **Artificial Intelligence** (Elsevier), **IEEE
Transactions on Cybernetics**, **Information Sciences**. Pattern Recognition
(pattern/CV-centric) and the AI4Science venues (bio-specific) were considered
and dropped as leads because they would narrow the work to a single domain; the
manuscript should lead with cross-domain generality.

**Metric-state inventory + execution order (2026-10-14).** A per-cell audit
against the 11-cell ledger and GAP-12 found that several of the venue-driven
gaps were already largely satisfied, so `todo.json` was re-scoped to what is
genuinely new:

- **Already covered** — tuned-baseline survival: R5c *survives* a tuned baseline
  (GAP-12 §2.5, straw-man REFUTED) but only on the smoke checkpoint; R3/K1 hold
  directionally (n.s.); R5b dies (0/4); R1/R6/K4/K5/K7 and R2 are structurally
  compute-invariant. Ablations: paper §7.3 (five-arm, k=5), §7.7 (NFE boundary),
  §7.9 (regime curve) and `docs/ABLATION.md` (36 uplifts) already exist.
- **GAP-33-TUNED-BASELINE-SURVIVAL was absorbed into GAP-35** (its residual is
  the non-smoke half of the same requirement).
- **GAP-36 reframed** as an aggregation/writing task (consolidate existing
  ablations), not new experiments.

The re-ordered open set is: **Phase 0** GAP-15-VENUE; **Phase 1** (shared GPU
sweeps) GAP-35-CROSS-DOMAIN-COVERAGE → GAP-32-SOTA-HEADTOHEAD →
GAP-37-STATISTICAL-POWER; **Phase 2** GAP-34-R1-MECHANISM →
GAP-36-ABLATION-MATRIX; **Phase 3** GAP-29-MANUSCRIPT-DENSITY and
GAP-20-COVERLETTER (user). *(Phases 1–2 partly complete: GAP-35 resolved
2026-10-14, GAP-32 resolved 2026-10-14, GAP-37 resolved 2026-10-15, GAP-36
resolved 2026-10-15; GAP-34 in progress.)*

**GAP-35-CROSS-DOMAIN-COVERAGE — RESOLVED 2026-10-14.** The gap's residual was
a cross-domain cell that is *both* non-smoke *and* survives a tuned baseline.
The paper's §7.9 R5c regime curve confounded **width** (8 vs 16 channels) with
**training budget** (1 epoch / 6 K images vs 2-3 epochs / 60 K images); §10.8
named the missing control. The audit
[`docs/audit/gap35-cross-domain.md`](gap35-cross-domain.md) runs that control as
a factorial sweep (`tools/sweep_gap35_mnist_regime.py`, N = 200, seeds
42/43/44, the canonical `wave191` matched-NFE protocol):

- **Width is irrelevant to the sign.** At 60 K images the framework regresses at
  *both* widths: `w8e3_60k` (width 8) +3.11 %, `w16e1_60k` (width 16) +3.96 %.
- **The optimization budget is the governing variable.** The delta is monotone
  in optimizer steps: 78 steps → −25.4 %, 93 → −28.4 %, 156 → −15.2 %,
  937 → +3.96 %, 1 874 → +8.53 %, 2 811 → +3.11 / +10.37 %. The sign flips
  between 156 and 937 steps (equivalently, baseline FID 19 → 13).
- **A production-width (base16, 75 KB → non-smoke) checkpoint wins.**
  `w16e1_5k` (78 steps) is framework-WINS −25.39 % (per-seed −25.43 / −24.77 /
  −25.97 %), best-arm Bonferroni p = 7.4 × 10⁻⁶, and **survives a tuned
  baseline** (baseline step-insensitive: 27.2361 → 27.2327 → 27.2311 across
  50/100/200 steps). `w16e1_10k` (156 steps) corroborates: −15.18 %,
  Bonferroni-significant. → **GAP-35 acceptance met.**
- **Honest caveat:** the two winning cells are non-smoke by the canonical *width*
  flag but share the smoke recipe's *low training budget*; the load-bearing
  claim is width-independence, not that a production-*budget* model wins.

GAP-35 is removed from `todo.json`; the remaining Phase-1 items were
GAP-32-SOTA-HEADTOHEAD (resolved 2026-10-14) and GAP-37-STATISTICAL-POWER
(resolved 2026-10-15) — Phase 1 is now complete.

## 8. Removed surfaces

- **Removed 2026-10-13:** the legacy repo-root `todo.json` and the entire
  `todo/` directory (13 files), replaced by a single management surface per
  user directive.
- **Known dangling reference:** `docs/drafts/paper-A-final.md:842` still links
  `todo/RISK-REGISTER.md` R-019 (frozen manuscript; left untouched).
- **Repaired references:** `docs/README.md` and `docs/RELEASE-NOTES.md`
  pointers repointed at `todo.json`.
