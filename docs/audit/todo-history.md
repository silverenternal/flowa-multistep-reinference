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

### 4.9 R1 tier-aware n_cap — the last dormant lever, a wash at N=1000 (GAP-41, 2026-10-16)

The dormant-lever survey's final candidate: the **R6 tier-aware `n_cap`**
scheduler path (trim restart NFE for records whose *baseline* pLDDT is already
high), transplanted onto the R1 (HMMER-hit) metric via the already-wired flags
`--tier-aware-n-cap 0.5` + `--tier-aware-baseline-metrics-jsonl <foldability.jsonl>`.

**Screen (N=200, seed 42, gate-open).** `legacy` 38 → **`tier_a` 50** hits
(**+12**, +31.6 %), per-record MWU `p=0.120` — the strongest signal in the whole
survey. `tier_a ≡ tier_b` (framework md5 `3ecc3048…`) ⇒ `--scheduler
tier_aware_codimension` is a **no-op**; the effect is entirely the `n_cap` +
baseline JSONL.

**Decisive (N=1000, seeds 42/43/44).** Controls reused byte-for-byte from the
archived GAP-40 `n1000_gate_open` run (baseline md5 verified equal at gen time):

| seed | baseline | legacy | centered | **tier** |
|---:|---:|---:|---:|---:|
| 42 | 158 | 257 | 271 | **252** |
| 43 | 159 | 265 | 269 | **279** |
| 44 | 174 | 245 | 265 | **262** |

`tier vs legacy`: per-seed diffs **[−5, +14, +17]**, mean **+8.67**, `d_z=0.726`,
**2/3 seeds positive**, `p_bonf_rlevel=1.0` → **NOT STRONG** (fails both the
`d_z>0.8` bar and the 3/3 direction criterion); per-record DL `d_pooled=+0.0196`,
`z=1.07`, `p=0.284`. `tier vs centered` is a wash (`d_z=−0.28`). The `centered vs
legacy` control row reproduces GAP-40 §4b.2/§4b.3 exactly (`d_z=1.567`; DL
`+0.0243`, `p=0.184`) — same pipeline.

**Reading:** the R6 tier-aware mechanism is **real and wired** (framework FASTAs
byte-distinct from every control arm; manifests record `tier_aware_n_cap=0.5`) but
**inert on R1** — the N=200 `+12` did not replicate, exactly as GAP-40b's N=200
`negative` screen did not. This is the **sixth consecutive dormant lever**
(GAP-38/39/40/40b/34/41) that is wired and active yet fails the n=3 STRONG bar.
The R1 near-miss is **power-limited, not code-limited**. Observations-only; no
frozen surface moved — `docs/audit/gap41-r1-tier-aware-ncap.md`; evidence
`verification_outputs/gap41-r1-tier-aware-ncap/`.

### 4.10 NFE fidelity — the budget is a load-bearing axis (GAP-41b, 2026-10-16)

Every dormant-lever rejection above (GAP-38/39/40/40b/34/41) was measured at
the canonical `--nfe 10`, but the upstream LineageFlow released config
(`data/lineageflow_upstream/config/generation.json`) uses `steps_base=100` +
`steps_final=50` ≈ **150 NFE** — a ~15× budget gap. The user's hypothesis: the
rejections may be a low-budget artifact rather than evidence the levers are
inert. **Premise test** (`/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/run_premise.sh`): N=200,
seed 42, gate-open (`--restart-min-nfe 5`, `effective_n_rounds=3`), arms
`{legacy, tier}` × NFE ∈ {10, 150}.

| NFE | baseline | legacy fw | tier fw | fw − baseline | tier − legacy |
|---:|---:|---:|---:|---:|---:|
| 10  | 37 | 38 | 50 | **+1** (p≈0.91) | **+12** (p=0.089) |
| 150 | 37 | 48 | 46 | **+11** (p≈0.22) | **−2** (p=0.70) |

**The baseline is NFE-invariant** — `nfe10`/`nfe150` baseline FASTAs are
byte-identical (md5 `ff5a6de6609c72f86cae3a3c8279d50a`, 37 hits = 37), so the
movement is entirely in the framework arm. Two readings: (a) the
framework-vs-baseline **headline grows with budget** (+1 → +11) — NFE=10 was too
*harsh*; (b) the **tier lever flips sign** (+12 → −2) — NFE=10 was too
*generous*. Either way, **NFE is load-bearing and the six prior rejections are
conditional on `--nfe 10`, not budget-invariant.**

**Caveats:** premise only — N=200, single seed; no NFE=150 comparison reaches
p<0.05 at N=200; the canonical driver's β-scale (`NFE_REF=50`) means the NFE=150
blend is 1/3, so steps and blend-strength move together. The canonical R1 STRONG
bar remains n=3. A decisive n=3 N=1000 run at NFE=150 costs ≈ 21 h (legacy
headline) to ≈ 41 h (legacy + tier), measured 24.7 s/record — user-gated. Observations-only; no frozen surface moved —
`docs/audit/gap41b-r1-nfe-fidelity.md`.

**Follow-up — n=3 N=200 NFE=150 legacy screen.** Before committing to N=1000,
seeds 43/44 were generated at N=200, NFE=150, legacy arm (seed 42 reused):

| seed | baseline | framework | framework − baseline |
|---:|---:|---:|---:|
| 42 | 37 | 48 | **+11** |
| 43 | 36 | 55 | **+19** |
| 44 | 32 | 63 | **+31** |

mean **+20.33**, **3+/0−**, one-sample t=3.50, p=0.073 → **direction-consistent
3/3**. This is an *entry ticket* for a decisive N=1000 run, not a result (p=0.073
at n=3; still the N=200 screen, where GAP-40b and GAP-41 were both false
positives). Caveat flagged: the diffs are monotone (+11/+19/+31) while the
baseline drifts down (37/36/32) — a seed-level trend, not independent noise;
watch it at N=1000. Evidence:
`verification_outputs/gap41b-r1-nfe-fidelity/nfe150_screen/`.

### 4.11 Scheduler NFE budget leak — the math schedulers were silently given 2.1× compute (GAP-42, 2026-10-16)

The user pointed at the framework's core scheduler: the default is cosine
annealing, but there is a paper-grounded family (`codimension_sheet`,
`paper_ratio_adaptive`, `tier_aware_codimension`, …) that consumes the paper's
sheet-vs-cell quantities. A check of `tools/eval/framework.py::_solve_framework`
found a **budget leak** in the non-cosine branch: `n_cap` is a per-round
*fraction* (`n_cap(r) = n_min + (n_max-n_min)*ratio(r)`), not a partition, but
the driver multiplied it straight by `nfe`. At `nfe=10`, `n_rounds=3`:

| `--scheduler` | per-round NFE | sum |
|---|---:|---:|
| `cosine` | `[3,3,4]` | 10 |
| `codimension_sheet` | `[10,10,1]` | **21** |
| `tier_aware_codimension` | `[10,10,1]` | **21** |
| `linear` | `[10,5,1]` | 16 |
| `nfe_aware_memory` | `[5,5,1]` | 11 |

So every prior cosine-vs-math-scheduler comparison was a **compute** comparison,
and would have been confounded with the GAP-41b NFE axis. Fixed with
`_allocate_nfe_budget` (normalise weights → largest-remainder apportionment,
floor 1 per round); the `cosine` path stays byte-identical (pinned by a test).

Post-fix all schedulers sum to 10. But the fix also exposes the deeper issue:
on R1 `codimension_sheet`'s `n_cap` is `[1.0, 0.9997, 1.0]` — a ~3e-4 spread —
because the LineageFlow adapter exposes no `profile_residual_fn`, so the
paper-quantity path never activates and the ratio saturates at ≈1. Its split
`[4,3,3]` therefore differs from cosine `[3,3,4]` only in **where the rounding
remainder lands**. The A/B is near-null by construction; the real lever is
wiring a residual profile `g(x)` into the adapter. Observations-only —
`docs/audit/gap42-scheduler-budget-conservation.md`.

**Follow-up (equal-NFE N=20 smoke, seed 42).** `cosine` and
`codimension_sheet` produce **byte-identical** framework FASTAs
(`md5 ad2205a3…`, hits 3 = 3) despite different splits `[3,3,4]` vs `[4,3,3]`.
Root cause is bigger than the scheduler: **the R1 framework does not chain
rounds at all.** `_solve_framework` defaults `restart_from_endpoint=False` and
the R1 driver never overrides it; even with the flag on,
`_stash_endpoint_as_x0` writes `dst["x0"]` while `LineageFlowAdapter` reads
`prior_entry["theta"]` (`lineageflow.py:2400`, `:2049`). So every round blends
the **initial** theta with fresh noise and the endpoint never carries forward.

| configuration | cosine digest | sigmoid digest | sensitive? |
|---|---|---|---|
| stock | `27036f32…` | `27036f32…` | no |
| `restart_from_endpoint=True` (writes `x0`) | `27036f32…` | `27036f32…` | no |
| flag on + theta-aware stash | `85d2eb8e…` | `aeb2a98f…` | **yes** |

This is the **likely root cause of the six dormant-lever nulls**: nothing can
compound across rounds on R1. Enabling the chain is a protocol change
(user-gated) requiring (1) a theta-aware stash, (2) a default-off
`--restart-from-endpoint` on the R1 driver, (3) a fresh N=1000 3-seed run.
Evidence: `verification_outputs/gap42-scheduler-budget/`.

**Wiring landed (GAP-42b, default off).** `_stash_endpoint_as_x0` now also
writes `dst["theta"]` when the native entry carries it, and the R1 driver gains
`--restart-from-endpoint` (`store_true`, default off; recorded in the
manifest). N=20 seed-42 smoke: `chain_off` framework is **byte-identical** to
the archived GAP-42 cosine arm (default stays byte-stable); `chain_on`
**differs** (chain is live). Hits: baseline 4, off 3, on 5 — noise at N=20;
this establishes liveness, not an effect size. Next: N=200 3-seed screen of
`chain_on` vs `chain_off`.

### 4.12 Endpoint chain — the first dormant lever that moves the metric, but not yet 3/3 (GAP-42c, 2026-10-17)

`run_chain_screen.sh`: seeds 42/43/44, N=200 per seed, NFE=10, 3 rounds,
cosine, temperature 1.0, GPU 0, 47 min wall clock. Each seed runs the default
arm (`chain_off`) and the Eq. 2 arm (`chain_on`); the baseline FASTA is
byte-identical across the two arms (verified per seed), so the baseline is
shared.

| seed | baseline | fw_off | fw_on | off−base | on−base | on−off |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 37 | 38 | 47 | +1 | +10 | +9 |
| 43 | 36 | 49 | 47 | +13 | +11 | −2 |
| 44 | 32 | 41 | 52 | +9 | +20 | +11 |
| **mean** | | | | **+7.67** | **+13.67** | **+6.00** |
| direction | | | | 3+/0− | 3+/0− | 2+/1− |
| seed-level t / p | | | | 2.17 / 0.162 | 4.30 / 0.050 | 1.49 / 0.276 |

Turning the chain on roughly **doubles** the mean framework−baseline gap, and
both contrasts are 3/3 in direction — the first time any of the seven dormant
levers has moved the R1 metric in a consistent direction. But the NFE-matched
causal contrast (`on − off`) is **2+/1−** (seed 43 goes the other way), so the
screen does not establish the chain effect. Status **UNDERPOWERED**; the
decisive test is the canonical N=1000 3-seed run with
`--restart-from-endpoint`.

Methodological fact established along the way: the baseline FASTA is
**byte-identical at NFE=10 and NFE=150** (seed 42 `md5 ff5a6de6…`, seed 43
`md5 1624b10e…`). `--nfe` moves only the framework arm, so `fw − baseline` is
NFE-unmatched by construction (the GAP-41b axis) while `on − off` is
NFE-matched — which is why the null-ish marginal, not the +13.67, is the
number that matters. Observations-only —
`docs/audit/gap42-scheduler-budget-conservation.md` §7.2.

### 4.13 The endpoint chain is real but is not a lever — decisive N=1000 (GAP-42d, 2026-10-17)

Canonical configuration (seeds 42/43/44, N=1000, NFE=10, 3 rounds, cosine,
`restart_min_nfe=20`), chain ON, 1 h 44 min on GPU 0. `chain_off` was not
re-run: it is byte-stable and the canonical numbers 275/272/259 *are* that arm.

**Identity check passed:** the regenerated baseline hits are exactly the
canonical 158 / 159 / 174, so the comparison is apples-to-apples.

| seed | baseline | canonical fw (off) | fw (on) | chain − off |
|---:|---:|---:|---:|---:|
| 42 | 158 | 275 | 280 | +5 |
| 43 | 159 | 272 | 281 | +9 |
| 44 | 174 | 259 | 259 | **0** |
| mean | | 268.67 | 273.33 | +4.67 |

| quantity | off (canonical) | on |
|---|---:|---:|
| per-seed `d_z` | +0.169 / +0.170 / +0.129 | +0.1773 / +0.1762 / +0.1296 |
| `d_pooled` (DL) | +0.1559 | **+0.1609** |
| z | 8.49 | 8.76 |
| 95 % CI | [0.120, 0.192] | [0.125, 0.197] |

**Decisive null.** The chain moves `d_pooled` by +0.005 (+3 %), each per-seed
`d_z` by ≤ 0.008, and the new CI sits almost entirely inside the canonical CI.
On hits, one seed is an exact tie and the others move +5/+9 out of ~270
(2+/1−, the same shape as the N=200 screen). R1 stays **PARTIAL** — 0.161 ≪ the
0.8 STRONG bar, unchanged in class.

**Hypothesis update.** §4.11/§4.12 called the missing chain the likely root
cause of the six dormant-lever nulls. That is **refuted as stated**: a live
chain does not move the metric, so "nothing compounds across rounds" is not
what suppressed those levers. The narrower claim (other levers becoming
load-bearing *given* a live chain) is untested and would need a tier-aware
`n_cap` A/B with `--restart-from-endpoint`. Observations-only —
`docs/audit/gap42-scheduler-budget-conservation.md` §7.3.

### 4.14 The two surviving levers are substitutes, not complements (GAP-42e, 2026-10-17)

2x2 screen at N=200 / seeds 42/43/44 / NFE=10 / gate-open: {legacy, tier-aware
`n_cap` 0.5} x {chain off, chain on}. The legacy row is the GAP-42c screen, so
the full 2x2 cost only 6 generations (43 min). `seed42_tier_off` reproduces the
GAP-41 archived `tier_a` arm **byte-for-byte** (`md5 3ecc3048…`).

| seed | baseline | A legacy/off | B legacy/on | C tier/off | D tier/on |
|---:|---:|---:|---:|---:|---:|
| 42 | 37 | 38 | 47 | 50 | 53 |
| 43 | 36 | 49 | 47 | 51 | 44 |
| 44 | 32 | 41 | 52 | 46 | 45 |

| contrast | mean | direction | t | p |
|---|---:|---|---:|---:|
| tier effect, chain OFF | +6.33 | 3+/0− | 2.14 | 0.166 |
| tier effect, chain ON | −1.33 | 1+/2− | −0.35 | 0.762 |
| chain effect, tier OFF | +6.00 | 2+/1− | 1.49 | 0.276 |
| chain effect, tier ON | −1.67 | 1+/2− | −0.57 | 0.624 |
| **interaction** | **−7.67** | **0+/3−** | −3.51 | 0.073 |

Each lever alone is worth ~+6 hits over legacy; together only +4.67, and the
interaction is negative on **all three seeds**. They are **substitutes**: both
consume the same per-round memory/budget axis, so the gain saturates. The
strongest single cell is tier-only (+14.0 vs baseline, 3/3) — exactly the arm
GAP-41 took to N=1000 and found a wash.

So "turn the chain on and the other dormant levers will wake up" is **not
supported** — the chain cancels the tier lever's apparent gain rather than
unlocking it. Screen only (n=3, N=200, p=0.073); it does not overturn GAP-41's
N=1000 null. Observations-only —
`docs/audit/gap42-scheduler-budget-conservation.md` §7.4.

### 4.15 NFE=150 decisive run — profiling first, then seed-level concurrency (GAP-42f, 2026-10-17)

The user authorised the 21 h NFE=150 decisive rerun but asked for an engineering
pass first (raise GPU utilisation, move the CPU hot path to the GPU, cut I/O
waits). Profiling at NFE=150 (gate open → 3x50 chained rounds + a 150-step
re-anchor = 300 velocity calls/record):

| stage | share of per-record wall |
|---|---:|
| `compute_family_vector_field` (vendored `_betacf` loop) | **69 %** |
| ESM-2-650M forward | **29 %** |
| everything else (bundle, blend, decode, FASTA write) | < 0.3 % |

The `_betacf` loop runs ~144 iterations per call, each ~20 elementwise ops on a
`(1,256,20)` tensor **plus one `torch.all` device sync** — it is already on the
GPU, but launch- and sync-bound. H2D/D2H is < 0.5 % and there is no I/O wait, so
the user's "I/O" hypothesis does not hold. Every fast rewrite of the loop was
rejected on numeric drift (TorchScript 5.8e-11, check-every-8 1.2e-10,
fixed-iteration 1.7e-3) and the upstream tree is frozen byte-identical.

Adopted fix: one process per seed, three concurrent on cuda:0. Measured
22.1 s/record solo vs 30.0 s/record at 3-way = **2.2x aggregate**, GPU 98-100 %,
34.9 GB VRAM. `N=20` serial-vs-parallel FASTAs are **byte-identical**
(framework `md5 87be1c7b…`, baseline `6e7445d4…`), so the concurrency is
arithmetically free. Projected wall clock 18.4 h → **8.3 h**.

The run completed 23:27:52Z (9 h 56 min wall; generation 9 h 21–9 h 29 min,
+13–14 % over projection because a co-tenant GPU-0 job shared the device, still
1.85x faster than the serial projection). The baseline arm is byte-identical to
GAP-42d (hits 158/159/174). Framework hits fell from 280/281/259 at NFE=10 to
**247/251/245**, so `d_pooled` fell from +0.1609 to **+0.1178 (−27 %)** and every
per-seed `d_z` fell. Direction remains 3/3 framework-favourable and the DL pooled
effect survives Bonferroni k16 (p=2.06e-9), so this is not a framework-not-win —
but NFE fidelity **attenuates** the R1 contrast rather than rescuing it. R1 stays
PARTIAL. NFE and live-round count co-vary by construction, so the claim is about
the canonical NFE=150 cell, not a single factor. Observations-only —
`docs/audit/gap42-scheduler-budget-conservation.md` §9.4.

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
| GAP-41-R1-TIER-AWARE | 2026-10-16 | the last dormant lever: the R6 tier-aware `n_cap` mechanism (`--tier-aware-n-cap 0.5` + baseline pLDDT jsonl) on the R1 metric. N=200 screen `tier_a` 50 vs `legacy` 38 (**+12**, MWU p=0.120); decisive N=1000 3-seed sweep is a **wash** — per-seed diffs [−5,+14,+17], mean +8.67, `d_z=0.726`, **2/3**, `p_bonf=1.0`, per-record DL `d=+0.020 p=0.284`. Sixth consecutive wired-but-inert dormant lever; the R1 near-miss is power-limited, not code-limited. R1 stays PARTIAL — `docs/audit/gap41-r1-tier-aware-ncap.md` |
| GAP-41b-R1-NFE-FIDELITY | 2026-10-16 | the budget behind every prior rejection is a **load-bearing axis**. All six dormant-lever rejections ran at `--nfe 10`; upstream uses ~150 NFE. N=200 seed-42 premise (arms `{legacy,tier}` × NFE {10,150}, gate-open): baseline byte-identical across budgets (37 = 37, md5 `ff5a6de6…`), framework-vs-baseline **+1 → +11**, tier-vs-legacy **+12 → −2** (sign flip). So the six rejections are **conditional on `--nfe 10`**, not budget-invariant. Premise only (N=200, single seed; β-scale `NFE_REF=50` confound); n=3 N=1000 at NFE=150 ≈ 21–41 h = user-gated. Follow-up n=3 N=200 NFE=150 legacy screen: diffs +11/+19
| GAP-42e-LEVER-INTERACTION | 2026-10-17 | 2x2 tier-aware `n_cap` x chain screen (N=200, 3 seeds): tier-only +6.33 (3+/0−), chain-only +6.00 (2+/1−), both +4.67; **interaction −7.67, 0+/3−** (t=−3.51, p=0.073). The two levers are **substitutes**, not complements — a live chain does not unlock the tier lever, it cancels its apparent gain. Screen only; does not overturn GAP-41's N=1000 null — `docs/audit/gap42-scheduler-budget-conservation.md` §7.4 |/+31, mean +20.33, **3/3** positive, t=3.50 p=0.073 (entry ticket only). Observations-only — `docs/audit/gap41b-r1-nfe-fidelity.md` |
| GAP-42-SCHEDULER-BUDGET | 2026-10-16 | fixed a per-round NFE leak in `_solve_framework`: non-cosine schedulers multiplied the per-ro
| GAP-42d-CHAIN-N1000 | 2026-10-17 | decisive canonical run with the chain ON: baseline reproduced exactly (158/159/174), chain-on framework 280/281/259 vs canonical chain-off 275/272/259 → +5/+9/**0**; `d_pooled` +0.1559 → **+0.1609** (+3 %), per-seed `d_z` moves ≤ 0.008. **Decisive null**: the chain is live but not a lever on R1; R1 stays PARTIAL. Also refutes the 'missing chain explains the dormant levers' hypothesis as stated — `docs/audit/gap42-scheduler-budget-conservation.md` §7.3 |und `n_cap` *fraction* straight by `nfe`, so `codimension_sheet` ran `[10,10,1]`=21 steps at `nfe=10` (2.1× cosine). Any prior cosine-vs-math-scheduler A/B was a compute comparison. Fix: `_allocate_nfe_budget` (normalise + largest-remainder); cosine path byte-identical. Post-fix all sum to 10. Also found `codimension_sheet` is degenerate on R1 (`n_cap`≈`[1,1,1]` — no `profile_residual_fn`), so the A/B is near-null by construction. Equal-NFE N=20 smoke: cosine and codimension FASTAs **byte-identical** (`md5 ad2205a3…`). **Root cause: the R1 framework does not chain rounds** — `restart_from_endpoint=False` (driver never overrides) and `_stash_endpoint_as_x0` writes `x0` while LineageFlow reads `theta`. Likely root cause of the six dormant-lever nulls; enabling it is a protocol change = user-gated — `docs/audit/gap42-scheduler-budget-conservation.md` |
| GAP-42b-ENDPOINT-CHAIN | 2026-10-16 | wiring for the root cause, **default off**: `_stash_endpoint_as_x0` also writes the adapter's native key (`theta` for LineageFlow), and the R1 driver gains `--restart-from-endpoint`. N=20 smoke: `chain_off` **byte-identical** to the archived arm (default stable); `chain_on` **differs** (live); hits 4 / 3 / 5 (liveness only) — `docs/audit/gap42-scheduler-budget-conservation.md` §7.1 |
| GAP-42c-CHAIN-SCREEN | 2026-10-17 | N=200 3-seed screen of the now-live chain. Per-seed `on − off` = +9 / −2 / +11 → mean +6.00, **2+/1−**, t=1.49 p=0.276; `fw_on − baseline` = +13.67 (3+/0−, p=0.050) vs `fw_off − baseline` +7.67 (3+/0−, p=0.162). Suggestive, **UNDERPOWERED** — the NFE-matched contrast is not 3/3. Also pinned: baseline FASTA is byte-identical at NFE=10 vs 150, so `--nfe` moves only the framework arm — `docs/audit/gap42-scheduler-budget-conservation.md` §7.2 |

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

---

## 9. Addendum (2026-10-21) — `todo.json` reset to open work only

**Directive:** user — *"基于现状你把 todo.json 再整理一下，这个文件有点冗长了，
我们要维护他只用于做未完成的项的详细规划，已经做完的任务从 todo.json 中删除"*.

Same operation as §6/§7, applied again after GAP-45/54/56/57/58/60/64/65 closed
in one week. `todo.json` (schema `flowa-state-v6`) now carries **only** the
fixed header keys, the gate chain, `q1_gate` (one sentence: what still blocks
Q1), `execution_order`, and `open_gaps` with the full acceptance test per item.

Moved here verbatim, no fact dropped:

| was a `todo.json` key | now |
|---|---|
| `completed_index` (14 entries) | §10 below |
| `evidence_state` | §11 below |
| `metric_remediation` (12 rows) | §12 below |
| `q1_assessment` (incl. `mechanism_update_2026_10_21`) | §13 below |
| `venue` | §13.2 below (supersedes §3's backup list) |
| `config_inventory` | pointer now in GAP-44's `evidence` |

Two open items were **merged** rather than carried: GAP-63-R5B-N1000 required
N=1000 x 3 on R5b, and GAP-66-R5B-EQUAL-BUDGET required a matched-NFE re-run of
the same four arms. One run satisfies both, so GAP-63 is absorbed into GAP-66
(recorded in that entry's `absorbs` field) instead of consuming a second GPU
slot. GAP-44 is compressed to its only remaining item (P2-1, the
`profile_residual_fn` wiring); its closed sub-items are in §10 and in
`docs/audit/project-state-inventory.md`.

## 10. Closed-gap index (carried from `todo.json`, 2026-10-21)

**GAP-55-EVIDENCE-GRADE-REPAIR** — R5c equal-NFE -> REGRESSES +9.2..+14.6% (3/3 arms, production ckpt); R3 N=1000 measured dfg=-0.061 CI[-0.117,-0.001] p=0.043 (1 seed, not Bonf); R1 gate-open wiring live (effective_n_rounds=3, 200/200 seqs differ); R6 live scPerp d_z=-0.84 is the headline.

**GAP-43-BLEND-POSITIVE** — R3 50-seed blend: fg_dev INCONCLUSIVE (d=-0.0192, p=0.130; tuned gate fails); pb_validity +0.212, 50/50 seeds (exploratory).

**GAP-46-R5B-MEMORY-SWEEP** — R5b memory sweep: 0/16 cells survive the tuned baseline; the boundary is confirmed.

**GAP-48-K7-TWO-ARM** — K7 two-arm: framework 12.6x LESS novel (direction inverted, confirmed).

**GAP-49-COMPUTE-ACCOUNTING** — Compute accounting: NFE ledger complete; the framework pays no hidden NFE.

**GAP-52-CHANNEL-FAITHFUL-BLEND** — Charge-categorical + per-channel m: dev-screen null (no arm beats C0); confirm not run.

**GAP-53-INITIAL-CONDITION-CONTRACTION** — R=2 multi-round: null on both metrics (2/4 seeds, not significant); CTMC class flips break the Lipschitz premise; R=1 stays canonical.

**GAP-56-RESTART-T0** — solve_ode ignored t0/t1, so a restart whose blend is the path state at t=m was re-integrated over the full [0,1] (beta=0 drifted 24.9%); second defect: the prior was keyed only on (batch_id, sample_id) and solve_ode discarded its seed, so the Wave 280 '3-seed' R5c runs are three byte-identical copies. Fixed; regression halved (+15.9/+20.9/+10.8% -> +6.7/+9.7/+9.6%, 3 genuine draws, 18/18 positive).

**GAP-57-EQUAL-NFE-REGIME-LADDER** — GAP-35 ladder re-measured at equal total NFE=50, N=1000, 3 draws: w16e1_5k -9.37% (3/3, CI excludes 0), w16e1_10k +2.81%, w16e1_60k +15.59%, production +9.52%; slope -1.177 %/FID, R2 0.855, zero crossing FID 22.5. Also found FID is O(1)-biased at small n (true 0 reads 23.98 at n=200, 4.73 at n=1000), so every N=200 effect size was inflated 40-65% and one sign flipped. -28.43% retired (smoke ckpt).

**GAP-54-CLASS-PRESERVING-CONTRACTION** — sampler_stochasticity=0 fixes the CTMC class (dim_changes=0, 128 direction-runs) and the map STILL expands: per-round ratio 11.91/3.80/1.49/1.23, K_eff=11.64, verdict NO CONTRACTION. Theorem 4 cannot be exercised on FlowMol3 at any m that still counts as a restart; FlowMol3 cells keep R=1.

**GAP-45-R1-BLEND-OFF-150** — beta=0 is a collapse mode, not a control (m=1 removes the fresh perturbation; 0/0/0 hits, entropy 1.68 bits, top-3 fraction 0.98). Added beta=1 (no memory): beta=1/6 vs beta=1 ties in 3/3 seeds, both above baseline. R1's NFE=150 gain is the per-record restart perturbation, not the memory blend.

**GAP-64-R5C-OPERATING-REGIME** — R5c closed at the mechanism level. (a) The framework's own NFE allocator (nfe_steps_for_evidence, previously used only by tools/run_controlled_audit.py) was wired into the MNIST driver as --nfe-allocation evidence: NFE=16 codi +10.09% vs +9.05% (scheduler), NFE=50 +8.70% vs +8.55%. No sign flip; the allocator is not the missing lever. (b) Baseline-only NFE ladder with a byte-identical prior: production 11.1035 (NFE=3) -> 11.0675 (NFE=100), 0.33%; w16e1_5k 26.9258 -> 26.7300, 0.73%. The RK4 sampler is converged at three steps, so R5c has no integration headroom and its delta measures only the cost of the restart. (c) Mechanism identified: the blend m*x1+(1-m)*x0 is a variance-shrinkage operator. rho = tr(S_g)/tr(S_ref) in the FID projection: production 0.782, w16e1_10k 0.752, w16e1_60k 0.704 (all shrink -> FID up), w16e1_5k 1.006 (shrink -> FID down, -9.65%). Sign rule rho_base >= 1 predicts the measured sign 4/4. This reconciles K7 (novelty -42.9 pp) and R1/R6 (coverage metrics up) as one mechanism.

**GAP-65-DISPERSION-SELECTOR** — Out-of-family test of the rho sign rule. CONSISTENT but UNTESTED in the positive direction: sign(rho_base-1) matches the measured FID sign in 5/5 computable cells (R5c production 0.782/+8.91, w16e1_10k 0.752/+2.47, w16e1_60k 0.704/+15.42, w16e1_5k 1.006/-9.65; R5b CIFAR 0.972/+1.48). The pre-registered 6-of-7 threshold is not met because R1/R3 have no FID-style feature space, so the rule is not computable there - an applicability failure, disclosed as a defect in the pre-registration (applicability was not specified). Across 16 R5b cells corr(rho_arm, dFID) = -0.93, but that is driven by three arms the sweep under-budgeted (75-79 NFE vs 150) and which collapse to rho_arm ~ 0.10; within the non-collapsed arm the ordering is noisy. Net: rho is a monitoring statistic, not a selector contribution, and the framework cannot claim a fidelity win or a measured 'never worse'.

**GAP-60-VALIDITY-NOVELTY-TRADEOFF** — No trade-off on the within-generation axis. Scored family_validity + novelty on the SAME nine GAP-45 FASTA pairs (3 seeds x beta in {0,1/6,1}, N=200, NFE=150). beta=0 collapses to 5-6 clusters out of 200 (singleton frac 0.00, 0 hits) - the detector is not blind. beta=1/6 and beta=1 both keep 200/200 clusters at 90% identity (singleton frac 1.00, identical to baseline) while hits rise 37->48/55/63 and 37->50/44/52. So R1's +74% is NOT bought by population collapse. beta=1 reproduces the gain, so it belongs to the perturbation channel, not the memory blend (second independent confirmation of GAP-45 s8). Novelty against the default pfam_holdout DB is degenerate (0 hits -> 1.0 everywhere) and is NOT quoted; K7's 3.7% vs 46.6% used the 63.8M pfam_canonical build on different samples and must be cited separately. The R1/K7 pair was a measurement error on our side, not a contradiction.

**GAP-58-R1-BETA1-POWERED** — single-seed N=1000 bound, closed by user decision before the third seed. β=1 (m=0, no memory term at all) gives 284 hits vs baseline 158 (**+126, +79.7%**, per-record d=+0.126, CI [+0.084,+0.168], 207 up/109 down, sign p=3.8e-08). The canonical β=1/6 arm gives 275. The β=1 − β=1/6 contrast is **+0.009 hits/record, CI [−0.041,+0.057], 192/189, sign p=0.918** — so the memory term is bounded at ≤ +0.057 hits/record (≤ 36% of the perturbation effect), not merely unmeasured. Control: baseline 158 reproduces GAP-55's 158 exactly; framework md5 differs. Consequence recorded for GAP-67: m=0 is a legitimate operating point on R1 and belongs in the image-cell design space. `docs/audit/gap58-r1-beta1-powered.md`.

## 11. Evidence state snapshot (2026-10-21)

**strong_unconditional**

- R6 scPerplexity: 3 seeds, N=3000, d_z=-0.8393, all tiers, beats vanilla + Fast-DLLM + AB-Cache + LeDiFlow

**strong_conditional**

- R5c boundary (w16e1_5k): N=1000 x 3 draws, cosine -9.37%, CI excludes 0 in 3/3; model-conditional (baseline FID 24.5)
- R6 pLDDT hard tier: 3 seeds, d_z=+1.1211 (tier-conditional; pooled is NOT_SIGNIFICANT)
- R1 (NFE=150): N=1000 x 1 seed, +117 hits (+74.1%), per-record CI [+0.073,+0.160]; mechanism = per-record restart perturbation, not the blend
- R2 Kanzi RMSD: N=1000 x 1 seed, d_z=-0.0990, Bonferroni-significant but small

**tie**

- R5a: |delta W2| = 0.0091 < 0.01 floor

**regresses**

- R5c production: N=1000 x 3 draws, +9.52% / +12.87% / +10.34% (cosine/codim/evidence), 9/9 cells
- R5b CIFAR FID: +52.33% at N=200 x 3 (magnitude not quotable; N=1000 pending, GAP-63)
- K7 novelty: 12.6x LESS novel (3.7% vs 46.6%), McNemar p=1e-102, 1 seed

**not_significant**

- R3 fg_dev: -0.061, CI [-0.117,-0.001], p=0.043 > 0.00714 floor, 1 seed (GAP-62)
- K1 pb_validity: d=+0.92, p=0.252 (metric saturated; GAP-47 user-gated)
- R6 pLDDT pooled: d_z=+0.1466

**null_mechanism**

- The memory term (m = 1 - beta) has no measured positive contribution on any cell. R1 at N=1000: beta=1 (m=0) keeps the full +79.7% gain and the beta=1 - beta=1/6 contrast is +0.009 hits/record, CI [-0.041,+0.057], sign p=0.918 (GAP-58, single seed) - so the term is bounded at <= 36% of the perturbation effect, not just unmeasured. R5c boundary untested (deferred to GAP-67). beta=0 is a collapse mode, not a control.

**measurement_hygiene**

- FID at n=200 inflates a paired delta by 40-65% (true 11.52 reads 18.99); only N>=1000 FID numbers may be quoted
- Chunk-level FID tests are arm-dependently biased; use record-level paired bootstrap with a bias-corrected interval
- The MNIST FM seed axis was vacuous until --seed-keyed-prior; any pre-2026-10-20 '3-seed' MNIST claim is one draw

**last_decisive_result** — GAP-45 (2026-10-20): beta=0 collapses R1 to 0 hits on 3/3 seeds (entropy 1.68 bits, top-3 fraction 0.98) and beta=1/6 vs beta=1 ties in 3/3, so the NFE=150 gain is the per-record restart perturbation, not the blend.

## 12. Metric remediation ledger (2026-10-21)

Superseded as a work surface by `open_gaps`: the rows whose status
is `* PENDING`/`SCHEDULED` point at the gap that now owns them. The
resolved rows are kept here because the reasoning is the record.

**R1** (`hmmscan_total_hits`, priority P0, status 3-SEED PENDING (GAP-59))

- POWERED at N=1000 but ONE seed: +117 hits (+74.1%), per-record CI [+0.073,+0.160]. 3-seed N=200 screen 48/55/63 vs 37/36/32 (3/3 positive, 2/3 CI). Mechanism = per-record restart perturbation, NOT the blend (GAP-45 s8). GAP-59 adds seeds 43/44 at N=1000. DIVERSITY CONTROL (GAP-60): on the same FASTA files the framework keeps 200/200 within-generation clusters at 90% identity (all singletons, identical to baseline) while hits rise; beta=0 collapses to 5-6 clusters. The gain is not bought by collapse.

**R2** (`reconstruction_kabsch_rmsd_Angstrom`, priority P2, status SINGLE-SEED)

- d=-0.0990 at N=1000, Bonferroni-significant but small; ONE seed. Report as a small honest effect and disclose the seed count; a 3-seed repeat is not currently scheduled.

**R5a** (`W2 (two moons)`, priority -, status TERMINAL)

- TIE: |delta W2| = 0.0091 < 0.01 floor.

**R5b** (`FID (CIFAR-10 RF, n_rounds=1)`, priority P1, status N=200 ONLY (GAP-63))

- +52.33% regression measured at N=200 x 3. FID at n=200 inflates a paired delta by 40-65% (GAP-57 calibration), so the SIGN stands and the MAGNITUDE does not. GAP-63 re-measures at N=1000 before any headline quote.

**R5c** (`projection FID (MNIST FM)`, priority P2, status RESOLVED (GAP-57) + MECHANISM (GAP-64))

- Matched NFE=50, N=1000, 3 draws: production +9.52/+12.87/+10.34% (REGRESSES, 9/9 cells); w16e1_5k -9.37% (SUPPORTED, 3/3 draws). GAP-64 retires this cell as a headline: the baseline is converged at NFE=3 (11.1035) vs NFE=100 (11.0675), 0.33% headroom, so there is no integration error to recover and the delta is pure perturbation cost. Sign is predicted 4/4 by rho_base = tr(S_gen)/tr(S_ref) >= 1 (w16e1_5k 1.006 is the only cell above 1). Do NOT quote the +9.5% as 'the framework degrades a good model'.

**R3** (`fg_dev (FlowMol3)`, priority P1, status SINGLE-SEED (GAP-62))

- N=1000 fg_dev -0.061, CI [-0.117,-0.001], p=0.043 > 0.00714 floor, ONE seed. The 50-seed GAP-43 blend was inconclusive. GAP-62 adds seeds 43/44 at N=1000.

**K1** (`rdkit_validity_pct`, priority P2, status SCHEDULED)

- NOT-SIGNIFICANT at K-level alpha: p_b=0.5676; pb_validity is the candidate metric (GAP-47).

**K5** (`hmmscan framework-vs-baseline delta`, priority P3, status NOT SCHEDULED)

- SUPPORTED with caveat: cluster-robust d=+1.12, p_b=0.003 at n=3; n>=7 re-sweep needed.

**K7** (`novel_pct_pfam_twilight`, priority P0, status RECONCILED (GAP-60); canonical re-run pending)

- 12.6x LESS novel (3.7% vs 46.6%, McNemar p=1e-102), 1 seed, measured against the 63.8M pfam_canonical build. GAP-60 showed this is NOT a diversity collapse: within-generation clustering is unchanged (200/200 singletons). K7 measures proximity to KNOWN Pfam families, which is expected to rise when validity rises - it is not the opposite of R1. Re-run against pfam_canonical on the GAP-45 sets before quoting the pair together.

**R1/K7 joint** (`hits x novelty (two-axis)`, priority P0, status RESOLVED (GAP-60))

- Not contradictory. R1's validity gain leaves within-generation diversity unchanged (200/200 clusters, all singletons); K7's novelty drop measures distance to known Pfam families and moves the expected direction when validity rises.

**R5c boundary** (`projection FID (MNIST FM, w16e1_5k)`, priority P0, status SCHEDULED (GAP-61))

- -9.37% at matched NFE, 3/3 draws - the only N=1000 cell the framework wins. Memory attribution untested.

**R5c mechanism** (`rho_base = tr(S_gen)/tr(S_ref)`, priority P0, status 4/4 IN-FAMILY (GAP-65 for out-of-family))

- Variance-shrinkage operator. Baseline rho: production 0.782, w16e1_10k 0.752, w16e1_60k 0.704, w16e1_5k 1.006. Framework always shrinks (to 0.74/0.51/0.60/0.55). Measured FID sign matches sign(rho_base - 1) in 4/4 checkpoints. Unifies K7 (novelty down), R1/R6 (coverage metrics up) and the R5c split as one mechanism.

## 13. Q1 assessment (2026-10-21)

**verdict** — ONE_3-SEED-POSITIVE-SHORT

**as_of** — 2026-10-21

**gating_risk** — empirical axis, not infrastructure (infrastructure and theory are already Tier-1 grade)

**why** — After GAP-45/54/56/57 the picture is sharper and harsher. (a) The namesake mechanism is null: on R1 at NFE=150 the memory term ties a no-memory restart in 3/3 seeds, and beta=0 collapses the arm outright, so no current result can be attributed to the blend. (b) R5c's historical -28.43% was the smoke checkpoint; at matched NFE the production cell regresses +9.52% on 3 draws, and only the under-trained w16e1_5k wins (-9.37%, 3/3 draws) - a model-conditional cell. (c) The positive cells are now R6 (3 seeds, N=3000, scPerplexity d_z=-0.84), R5c-boundary (3 draws, N=1000, model-conditional) and R1 (N=1000 but ONE seed). (d) K7 shows the framework is 12.6x less novel and that has never been measured on the same samples as R1's +74% validity, so the two headline results currently read as contradictory.

**decisive_missing_piece** — One 3-seed positive at N=1000 on a canonical checkpoint (GAP-59: R1 seeds 43/44), plus one measurement that puts validity and novelty on the same axis (GAP-60) so R1 and K7 are one trade-off rather than two stories, plus a yes/no on whether the memory term earns anything anywhere (GAP-61).

**if_met** — Q1-defensible: theory + byte-stable infrastructure + a 3-seed N=1000 positive cell + an explicit validity/novelty trade-off + honest negatives (R5c production, R5b, K7) + a compute ledger. The mechanism claim must be restated either way: the perturbation channel is what the evidence supports.

**if_not_met** — Still submittable as a framework / operating-regime paper at TNNLS/TCyb/Information Fusion, but 'steady accept' is not supportable; fall back to KBS/EAAI rather than forcing a SOTA framing.

**framework_assets**

- theory: composite map G + conditional contraction + fixed point (Thm 4) + exact squared-error identity (Thm 5)
- falsifiable law: q < sqrt((1+m)/(1-m)); 45/45 off-boundary matches on R5b, 15/16 headline-cell directions, identity residual 2.7e-12
- system: typed four-port surface, 13 schedulers, zero-line integration into 5 frozen checkpoints, hash-chained ledger + 3 lemmas, byte-stable 2356-test infrastructure
- cross-domain: protein / molecule / 2D / CIFAR / MNIST under one inference interface
- measurement hygiene (new): FID small-n bias calibrated and corrected; chunk-level tests retired in favour of record-level paired bootstrap; seed axis verified non-vacuous

**blocking_point** — evidence homogeneity: one 3-seed N=1000 positive, and a mechanism that the evidence supports

- R1 (the strongest cross-domain positive) is single-seed at N=1000; R3 is single-seed and below the Bonferroni floor; R2 is single-seed with d=-0.099; R5b's effect size is an N=200 FID number that the project's own calibration says is inflated 40-65%; K7's novelty inversion has never been put on the same axis as R1's validity gain; and the memory blend - the paper's namesake - is null wherever it has been tested.

- `GAP-59-R1-THREE-SEED-N1000`: R1 seeds 43/44 at N=1000 -> the one 3-seed positive on a canonical checkpoint (~10 h GPU)

- `GAP-60-VALIDITY-NOVELTY-TRADEOFF`: score hits and novelty on the same 9 existing FASTA sets -> one trade-off curve instead of two contradictory headlines (~2 h, no new sampling)

- `GAP-61-MEMORY-ATTRIBUTION-WINNING-CELL`: beta in {0,1/6,1} on the only N=1000 cell the framework wins -> does the memory term ever earn anything (~2.5 h GPU)

### 13.1 Mechanism update (2026-10-21)

**finding** — The restart blend m*x1+(1-m)*x0 is a variance-shrinkage operator, not a sampler-accuracy operator. It contracts the sample cloud toward the model's conditional mean.

**evidence** — rho_base = tr(S_gen)/tr(S_ref) in the FID projection space predicts the sign of the measured FID delta in 4/4 MNIST-FM checkpoints (production 0.782 / w16e1_10k 0.752 / w16e1_60k 0.704 -> FID up; w16e1_5k 1.006 -> FID down -9.65%). docs/audit/gap64-r5c-operating-regime.md

**what_it_unifies** — K7 novelty -42.9 pp (shrinkage removes tail samples), R1 +74% hmmscan hits and R6 scPerplexity d_z=-0.84 (both reward a smoother, higher-likelihood population), and the R5c split (helps only the one checkpoint whose base dispersion is at or above the data).

**what_it_forbids** — 'For any FM model the framework improves inference quality' is FALSE on fidelity metrics and cannot be made true by better wiring: the operator is one-directional. The framework's own NFE allocator was wired in and measured (GAP-64): no sign flip.

**what_replaces_it** — Two claims that survive the mechanism audit: (a) on coverage/functional metrics the framework raises validity at unchanged within-generation diversity (R1: +30..97% hits, 200/200 singletons, 3/3 seeds; beta=1 reproduces it, so the channel is the perturbation, not the blend); (b) on fidelity metrics the blend is a one-directional variance shrinker that pays only when the base model is at or above the data's dispersion (GAP-64/65). The 'improves ANY FM model' framing is dead on (b) and is replaced by (a)+(b) as an explicit operator-characterisation.

**gap60_resolution** — R1 SURVIVES the collapse test. On the same nine FASTA pairs: beta=0 collapses to 5-6 clusters out of 200 (positive control); beta=1/6 and beta=1 both keep 200/200 singletons at 90% identity, identical to baseline, while hits rise 37->48/55/63 and 37->50/44/52. So the validity gain is not bought by diversity collapse, and K7 (distance to KNOWN Pfam families) is a different axis that moves as expected when validity rises. The R1/K7 'contradiction' was a measurement error on our side.

### 13.2 Venue (supersedes §3)

**scope** — general ML (user directive 2026-10-14: do not pigeonhole into image/CV or bio-specific venues)

**positioning** — Inference framework, NOT a model contribution (user directive 2026-10-18). The unit of contribution is the inference layer over a frozen checkpoint: no retraining, no new architecture. Judge fit by framework/system criteria (generality, plug-in cost, compute accounting, mechanism isolation), not by SOTA tables.

**primary** — IEEE TNNLS

**strategy** — Two-paper split (user-approved 2026-10-18): Paper A = framework + empirics + operating-regime law; Paper B = theory (composite-map contraction, fixed point, exact blend-error identity, boundary law).

**paper_a_targets**

- journal: IEEE TNNLS; cas: 1区 Top; fit: learning/adaptive systems; framework-level contribution is in scope; narrative: lead with the frozen-checkpoint inference layer + boundary law, not FID wins

- journal: IEEE Transactions on Cybernetics; cas: 1区; fit: controlled composite dynamical system + convergence condition + operating-regime law; narrative: recast as a controllable inference system; no SOTA table required

- journal: Information Fusion; cas: 1区 Top; fit: B_m is an inference-time fusion operator with an exact squared-error identity; narrative: define endpoint and fresh prior as the two sources; the identity is the fusion-theoretic result

**paper_b_targets**

- journal: JMLR; cas: verify current-year partition; fit: theory-only: Thm 4/5, fixed point, 45/45 backtest

- journal: Neural Networks; cas: 1区; fit: theory + method; boundary law as the core

**fallbacks** — Knowledge-Based Systems (1区); Engineering Applications of AI (1区)

**dropped_as_leads** — Pattern Recognition (model/CV-centric); IEEE TIP (model/CV-centric); AI4Science venues (bio-specific)

**note_on_partitions** — CAS partitions change yearly; verify the current-year table before submission.

---

## 14. Evidence-artifact index (2026-10-21)

The reference-graph scan behind `docs/ARCHIVE/audit-orphans/` found four recent
audit records that carried load-bearing results but were cited from nowhere.
They are listed here so the chain from a closed gap to its record is explicit.

| record | gap it closes | what it holds |
|---|---|---|
| [`gap46-r5b-memory-fraction.md`](gap46-r5b-memory-fraction.md) | GAP-46-R5B-MEMORY-SWEEP | the 0/16 R5b memory-fraction sweep; the +18..+23% arms whose budget defect GAP-66 now retracts |
| [`gap49-compute-accounting.md`](gap49-compute-accounting.md) | GAP-49-COMPUTE-ACCOUNTING | the NFE ledger showing the framework pays no hidden NFE |
| [`gap56-restart-t0-defect.md`](gap56-restart-t0-defect.md) | GAP-56-RESTART-T0 | `solve_ode` ignored `t0`/`t1`, so restarts re-integrated over the full `[0,1]`; also the vacuous-seed defect |
| [`gap60-validity-novelty-tradeoff.md`](gap60-validity-novelty-tradeoff.md) | GAP-60-VALIDITY-NOVELTY-TRADEOFF | same-FASTA validity x within-generation-diversity; the positive control (beta=0 collapses to 5-6 clusters) |

Two further records are cited from `docs/audit/INDEX.md` and from the open-gap
entries rather than from here: `gap15-venue-fit.md` (venue ranking, now in
section 13.2) and `gap16-deferred-triage.md` (the 31 deferred reviewer items).

---

## 15. Addendum (2026-10-21) — decision rule: measure less, design more

**Directive:** user — *"如果再补跑实验不能提升论文里指标的强度的话就不跑，而是转向那个
实验相关的代码设计（对应的adapter，需要结合相应领域具体的逻辑和知识进行调研做对应的
加强设计）"*.

### 15.1 The rule now in force

`todo.json` (schema `flowa-state-v7`) gained a `decision_rule` key:

> An experiment runs only if it can change a claim's STATUS or a metric's MAGNITUDE.
> More seeds, more draws or a larger N on an already-measured effect do not qualify:
> they buy confidence, not strength, and the paper's weakness is not confidence.

and a five-step `research_protocol` that every adapter gap must follow: read the
upstream implementation of the state space, read the metric's *definition* and scorer,
write the design hypothesis down before coding, change one mechanism at a time, then
make one confirmatory measurement at the cell's canonical N/NFE/seeds with no seed
top-ups afterwards.

### 15.2 What this retired, and what it started

| item | before | now |
|---|---|---|
| GAP-58 (beta=1 @ N=1000 x 3) | running 3 seeds, ~14-18 h | **stopped after seed 42** (user call). `reproduce/gap58_r1_beta1_n1000.sh` pinned to `for seed in 42`; result reported as a SINGLE-SEED bound |
| GAP-59 (R1 seeds 43/44) | P0, ~10 h | **deferred**; re-enters only as GAP-69's confirmatory run |
| GAP-62 (R3 seeds 43/44) | P1, ~8 h | **deferred**; re-enters only as GAP-68's confirmatory run |
| GAP-61 (memory attribution) | P0, ~2.5 h | **deferred**; re-asked on the NEW operator after GAP-67/68 |
| GAP-66 / GAP-63 (R5b matched budget, N=1000) | two separate runs | folded into **GAP-71 step (1)** as the before-arm |
| GAP-44 (config inventory) | bookkeeping | re-scoped to **GAP-44-PROFILE-RESIDUAL-WIRING**, a prerequisite for the theory sites |

Five new adapter gaps opened, all sharing one thesis derived from GAP-64's measurement
that the blend is a variance-shrinking operator:

| gap | state space | domain knowledge it must absorb |
|---|---|---|
| **GAP-67-BLEND-COVARIANCE-PRESERVATION** (P0) | the operator itself, all domains | second-moment matching; Thm 5's identity under a post-map |
| **GAP-68-ADAPTER-FLOWMOL3-CHANNELS** (P0) | coordinate / charge / 5-class bond CTMC | valence + kekulisation; which channel fg_dev actually rewards |
| **GAP-69-ADAPTER-LINAGEFLOW-PROTEIN** (P0) | ESM-2 embedding, family-conditioned | per-position conservation from the Pfam HMM; what hmmscan rewards |
| **GAP-71-ADAPTER-IMAGE-SPECTRAL** (P1) | pixel or latent, DCT/wavelet bands | whether Inception features are low-frequency dominated |
| **GAP-70-ADAPTER-KANZI-LATENT** (P1) | 64x64 latent + AR decoder prior | inverse-projection bridge; whether latent directions encode identity |

The ordering is deliberate: GAP-67 first, because it is the only change that can turn a
fidelity regression into a gain, and every adapter gap below it is measured against the
operator GAP-67 leaves behind.

### 15.3 Why this is the right move on the evidence

Three of the paper's negative cells (R5c production +9.5%, R5b CIFAR +52.33% at N=200,
K7 novelty 12.6x down) were traced by GAP-64/GAP-60 to one property of the map rather
than to three unrelated weaknesses. Every remaining power-only experiment would have
measured that same property more precisely without changing it. The honest options were
to state the boundary, or to change the operator. This addendum chooses the second and
keeps the first as the fallback if GAP-67's pre-registered reading fails.

## 16. Addendum (2026-10-21) — GAP-67 closed: the dispersion explanation is falsified

### 16.1 What was tested

`todo.json` §15 bet the plan on one change: replace the scalar convex restart blend with a
second-moment-preserving one, on the theory that `m*x1_hat + (1-m)*x0` contracts the sample
cloud and that restoring the blend's variance would restore `rho` and remove the R5c fidelity
cost. The design was pre-registered in `docs/audit/gap67-covariance-preservation.md` §0 before
any code was touched, including the prediction that R2 would fail if the FID gap turned out to
be mean-driven (§2.1) and that the chunk statistic would respond to dispersion rather than
quality (§2.2).

Implementation: `MnistFmAdapter(restart_noise_scale=c)` (default `1.0`, byte-identical — the
control reproduced `rho=0.7449`, `FID=10.8551`, `+0.63%` exactly), one `cosine` arm per
checkpoint, N=1000, NFE=50, seed 42, baselines reused from the frozen `gap57` run.

### 16.2 What happened

The correction is a null with the wrong sign on 4/4 checkpoints. Causal sensitivity
`d(rho ratio)/d(c^2)` measured −0.033, −0.051, −0.067, −0.056 against a predicted +5.6.
Raising the injected noise scale by 1–12 % moved the output dispersion by 0.03–0.7 %, in the
wrong direction, and made the chunk ΔFID uniformly slightly worse. R1, R2 and R3 all failed.

### 16.3 Why the cross-section lied

§2 of the audit had derived a 4.6–6.1× "amplification" by regressing the output deficit on the
input deficit **across four checkpoints**. That looked like a causal gain and was not: both
deficits are monotone in model quality, so the cross-section correlated two consequences of the
same latent variable. The dose-response (same checkpoint, one knob, two points) gives ≈ −0.05×.
**The intervention is the only valid instrument; a tight cross-section is not.** This is the
second time in this project that a cross-sectional regularity survived four checkpoints and then
failed under an intervention (the first was the GAP-64 sign rule, which GAP-67 also retires).

### 16.4 What replaced it

Two things, both recorded rather than assumed:

1. **The R5c cost is a mean shift.** Fréchet decomposition at N=1000: the mean term carries
   +0.760 of production's +0.888 gap and +1.480 of `w16e1_60k`'s +1.758, while the covariance
   term moves in both directions across the four checkpoints. The dispersion question was the
   wrong question; the mean is the mechanism.
2. **The contraction is a conditioning effect.** The restart injects independent noise at `t=m`
   and integrates to `t=1`, so the endpoint is approximately `E[x1|x_m]`, and conditional means
   are under-dispersed by the law of total variance. No rescale of the injected noise can undo
   it because the velocity field is scale-normalizing. This is *argued, not measured* — it is
   the one surviving candidate, not a result.

### 16.5 What this costs the plan

The plan's premise — "the weakness is the operator, and the operator is fixable" — is half
wrong. The operator is not fixable through its second moment; it may be fixable through its
mean, which nobody has looked at. The three gaps opened below split the question accordingly:
GAP-73 (is the R5c statistic even valid?), GAP-72 (what is the mean shift?), GAP-74 (is the
conditioning explanation true?). GAP-73 goes first because it is free and because it decides
whether the R5c numbers the paper quotes mean anything at all.

The adapter gaps (GAP-68/69/71/70) are untouched by this and keep their places. GAP-67 was
never a prerequisite for them — it was a prerequisite for the *claim* that the operator could
be repaired, and that claim is now withdrawn.

### 16.6 The lesson to carry

`todo.json` §15's decision rule said: run an experiment only if it can change a claim's status
or a metric's magnitude. GAP-67 passed that test and produced a *negative* result in 30 minutes
of GPU instead of the budgeted 3 hours, because the screen was designed to be falsifiable at one
seed and two dose points. The pre-registered confirmation ladder was never run and did not need
to be. That is the protocol working, and it is the reason the screen came before the ladder.

## 17. Addendum (2026-10-21) — GAP-73 closed: the R5c statistic reverses the sign

### 17.1 What was measured

The paired chunk test splits both arms into 10 chunks of 100 and scores each chunk against a
100-sample reference slice. `tools/gap73_r5c_nscan.py` reproduced it exactly and compared it to
`Delta(N)` — the same comparison at N ∈ {100, 200, 500, 1000} with a matched-N reference, 30
paired draws each — and to the N=1000 headline against the full 10K reference.

The chunk test reproduces `Delta(100)` to within 0.6 pp on all four checkpoints. It is not an
estimator of the headline; it *is* the headline at n=100.

### 17.2 What it costs

| ckpt | published chunk Δ (cosine) | N=1000 headline | ratio |
|---|---:|---:|---:|
| `production` | +0.6 % | **+8.9 %** | 14× |
| `w16e1_10k` | −11.4 % | **+2.5 %** | sign flip |
| `w16e1_60k` | +1.5 % | **+15.4 %** | 10× |
| `w16e1_5k` | −19.6 % | **−9.7 %** | 2× |

Across all three arms and four checkpoints, the chunk test reports 6 wins and 6 losses; the
N=1000 headline reports 10 losses and 2 wins. Two cells the chunk test called −12.7 % and
−12.9 % wins are, at N=1000, +0.1 % and −0.1 %. All three `w16e1_10k` arms flip sign.

The bias scales with the arm's dispersion, which is why it is largest exactly where the
framework was thought to be strongest: the two most-contracted checkpoints lose the most.

### 17.3 What it retires

* **CLM-059's R5c "WINS −28.43 %"** is a chunk statistic. Flagged, not edited.
* **GAP-64's sign rule** was fitted on the chunk statistic, so it was fitted on the bias. It
  remains true as a statement about the chunk statistic and is retired as a statement about
  fidelity.
* **The GAP-67 falsification now has a second reading**: the intervention on `rho` did not move
  FID because FID, properly measured, does not track `rho`. Both gaps point at the same defect.

### 17.4 What replaces it

GAP-75 opens next and costs nothing: the `gap57` ladder already holds 3 seeds × 4 checkpoints ×
3 arms at N=1000, so the corrected table is a re-read, not a re-run. The decision rule is not
violated — no new sampling, no new seeds, just the right statistic on samples that already
exist.

This is the third time in two days that a "confident" number turned out to be an estimator
artifact rather than a measurement (FID at N=200, the chunk test, and the GAP-67 cross-section).
The common shape is the same: a statistic whose bias is correlated with the treatment. Worth
carrying forward as a review rule — **before trusting any cell, check that the statistic's bias
is orthogonal to the arm it is comparing.**

## 18. Addendum (2026-10-21) — GAP-75 closed: R5c is a REGRESSES cell

### 18.1 The corrected table

The `gap57` ladder already held 3 seeds × 4 checkpoints × 3 arms at N=1000, so the corrected
R5c table cost no sampling. Verdicts (strict, 3-seed CI excludes 0): **9 REGRESSES, 2 TIE,
1 SUPPORTS**. Under the paper's 1-FID-unit effect floor: 7 REGRESSES, 3 TIE, 1 SUPPORTS,
1 UNDERPOWERED.

The only win is `w16e1_5k`/cosine at −9.4 % — the least-trained checkpoint in the ladder, and
the one where the baseline FID is worst (24.50). The largest regression is
`w16e1_60k`/`codimension_sheet` at +19.4 %.

### 18.2 Why the seeds are so tight

The per-seed spread is ~0.1 FID (e.g. +1.8/+1.8/+1.8 for `w16e1_60k`/cosine). At N=1000 the
sampling noise is already small, and the three seeds differ only in the prior draw. So these
cells are not underpowered — they are clear. The CI is a seed-to-seed interval and does not
include the estimator bias GAP-73 measured (~0.7 pp); the table is quoted with that caveat.

### 18.3 What this does to the R-level tally

`CLM-060` counts R5c as one of the 5-of-7 R-level WINS. On this table it is a REGRESSES cell.
The tally is flagged, not edited. Combined with R5b (already REGRESSES), the honest R-level
picture becomes **4 WINS (R1, R2, R3, R6) / 1 TIE (R5a) / 2 REGRESSES (R5b, R5c)**, pending the
paper owner's decision.

### 18.4 What is left of R5c

One question, and it is GAP-72's: why does the restart move the mean? The FID decomposition at
N=1000 says the mean term carries 86 % of production's gap and 84 % of `w16e1_60k`'s. If that
shift is a global DC offset it is correctable by a scalar; if it is structured, the cell is a
structural negative and the paper should say so.

Two days of work have now moved R5c from "the framework's flagship MNIST win" to "a REGRESSES
cell with one narrow exception, whose cause is an unexamined mean shift". That is the correct
direction for the paper even though it is the uncomfortable one.

## 19. Addendum (2026-10-21) — GAP-72 closed: the R5c cost is a location error

### 19.1 The decomposition

`delta_mu = mean(arm) - mean(baseline)` in pixel space, split into the all-ones direction (DC),
the reference mean image (ink), and the residual: DC 3–15 %, ink 0–2 %, residual 83–96 % on all
12 cells. The pre-registered rule (DC ≥ 0.5 → a scalar fixes it; DC < 0.2 → structured) resolves
as **structured**. The shift is also arm-specific (cross-arm cosine −0.015 to +0.234) and not a
border artifact (outer 2-px ring holds 8–23 % of the energy in 27 % of the area).

### 19.2 But a location correction removes the whole gap

Translating each arm so its mean equals the *baseline's* mean recovers 81–91 % of the loss on the
three regression checkpoints and takes `w16e1_10k` and `w16e1_5k` *below* baseline. So the cost
is a translation, not a quality loss.

Calibrating **both** arms to the training mean — deployable, one vector subtraction per sample,
target is a training-set statistic — gives:

| ckpt | raw Δ (cosine) | calibrated Δ (cosine) |
|---|---:|---:|
| `production` | +9.5 % | **+2.5 %** |
| `w16e1_10k` | +2.8 % | **−9.3 %** |
| `w16e1_60k` | +15.6 % | **+4.8 %** |
| `w16e1_5k` | −9.4 % | **−28.5 %** |

Mean over the 12 cells: **−7.3 %**, from +6.3 % raw. R5c becomes 6 wins / 6 small regressions
instead of 9 regressions.

### 19.3 The operator, stated properly

The restart has two separable effects:

* **location** — always harmful, +8 to +19 % on the converged checkpoints, and ~19 pp on
  `w16e1_5k` where it masks most of the shape gain;
* **shape** — helpful on the under-trained checkpoints (−8 %, −28 %), mildly harmful on the
  converged ones (+2 %, +6 %).

The convergence boundary is exactly the baseline-FID ordering: the two best models (5.12, 5.77
calibrated) lose on shape, the two worst (8.25, 11.33) gain. This is the same ordering as GAP-64's
"no NFE headroom" and it now has a mechanism instead of a correlation.

### 19.4 Why this matters for the plan

GAP-67 intervened on dispersion and found nothing. GAP-72 intervened on location and found the
whole effect. That is the correct way to settle a mechanism: one knob, one measurement. The
remaining question is why the restart biases the mean at all — GAP-76.

It also means the two days spent on R5c were not spent on a dead cell. The cell's story changed
from "the framework wins MNIST" (artifact) to "the framework is a shape operator whose gains are
hidden by a location error it also introduces" (measured, and actionable).
