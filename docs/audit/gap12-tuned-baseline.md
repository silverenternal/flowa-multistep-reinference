# GAP-12-BASELINE — tuned-baseline fairness audit (all 11 headline cells)

**Date:** 2026-10-13
**Author:** GAP-12 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` GAP-12-BASELINE — "Baseline fairness: matched-NFE + at
least one tuned baseline per headline cell (straw-man exposure)."
**Acceptance:** "tuned-baseline comparison exists per headline cell."
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

The classic framework-paper failure is a **straw-man baseline** — the framework
wins only because the baseline was denied compute. The direct test on a
solver-based cell is to **give the baseline more compute** (more NFE / steps)
and check whether the framework's *matched-protocol* win survives.

The paper has **11 headline cells** (§7/§10.10): R1, R2, R3, R5a, R5b, R5c, R6,
K1, K4, K5, K7. This audit covers all 11. **9 of 11 are resolved**; 2 (R3, K1 —
the same FlowMol3 model) remain residual.

- **2 NEW baseline-compute sweeps**: R5b (straw-man **REAL**), R5c (straw-man
  **REFUTED**).
- **1 NEW well-averaged protocol run**: R5a — the canonical 4.6× win **does not
  survive** a well-averaged baseline (straw-man **REAL**; §4.3).
- **6 structurally compute-invariant**: R1, R6, K4, K5, K7 (LineageFlow bare-RNG
  baseline — no solver) and R2 (Kanzi — DAE encode, no NFE knob; §4.1).
- **2 residual**: R3, K1 (FlowMol3 fg_dev / RDKit validity — needs the heavy
  real-FlowMol3 pipeline; §4.2).

| cell | model | headline metric | tuned-baseline status | source |
|---|---|---|---|---|
| **R5b** | CIFAR-10 RF | FID | **NEW sweep** — win does NOT survive (framework loses 4/4 at baseline NFE=200) | `gap12-tuned-baseline-cifar.json` + Wave 225 P9 |
| **R5c** | MNIST FM | FID | **NEW sweep** — win SURVIVES (baseline step-insensitive) | `gap12-mnist-tuned-baseline.json` |
| **R5a** | 2D Two Moons | W2 | **NEW well-averaged run** — win does NOT survive (1/4 schedulers beat baseline, +5.6 %) | `gap12-2d-sota-wellaveraged/` |
| R1 | LineageFlow | hmmscan hits | **structurally invariant** (bare-RNG baseline) | this doc §3 + `wave183-p4` |
| R6 | LineageFlow k6 | pLDDT / scPerp | **structurally invariant** | this doc §3 |
| K4 | LineageFlow | hmmscan hits | **structurally invariant** | this doc §3 |
| K5 | LineageFlow | hits delta | **structurally invariant** | this doc §3 |
| K7 | LineageFlow | novelty | **structurally invariant** | this doc §3 |
| R2 | Kanzi | RMSD (Å) | **structurally invariant** — DAE encode, no NFE knob; composite NFE-invariant {10..2000} | §4.1 |
| R3 | FlowMol3 | fg_dev | **residual** — scan degenerate TIE | §4.2 |
| K1 | FlowMol3 | RDKit validity | **residual** — scan degenerate TIE | §4.2 |

---

## 1. Method

For a solver-based cell the "tuned baseline" is the baseline arm run at its own
**best compute budget** (its best NFE / step count), compared against the
framework arm at the **matched** protocol. If the framework still does not lose,
its matched-protocol verdict is not a compute artifact.

For a cell whose baseline has **no solver** (the LineageFlow bare-RNG sampler),
there is no compute knob to tune: matched-NFE = best-NFE by construction, and
the straw-man concern is structurally impossible.

---

## 2. R5b — CIFAR-10 RF (NEW sweep) — **straw-man concern is REAL**

Driver: `scripts/gap12_tuned_baseline.py`. Baseline NFE ∈ {50, 100, 200} with
the framework held at the matched NFE=50, n_rounds=1, N=200, seed 42 (matched
NFE protocol, `--match-nfe budget`). Evidence:
`verification_outputs/gap12-tuned-baseline-cifar.json`.

| baseline NFE | baseline FID | framework wins / 4 | framework ΔFID% (Cos / Codim / Evid / Free) |
|---:|---:|:---:|---|
| 50  | 447.8943 | **2 / 4** | −0.17 / −1.12 / +1.34 / +0.78 |
| 100 | 443.7458 | **1 / 4** | +0.76 / −0.19 / +2.28 / +1.73 |
| 200 | 439.2525 | **0 / 4** | +1.79 / +0.83 / +3.33 / +2.77 |

**Verdict:** the R5b `n_rounds=1` matched-NFE win **does NOT survive baseline
NFE tuning**. At the baseline's *best* NFE=200 (FID 439.25), the framework
(held at NFE=50) **loses on all four schedulers** (+0.83 % to +3.33 %). The
matched-NFE=50 "win" is therefore (at this seed/config) **a compute artifact**:
giving the baseline 4× the NFE closes and reverses the margin.

*Caveat (honest):* at NFE=50 this run records only **2/4** framework wins
(−0.17 / −1.12 / +1.34 / +0.78), whereas the canonical Wave 235 P1 R5b
`n_rounds=1` reading is 4/4 WINS (−1.60 / −2.53 / −0.12 / −0.66). The baseline
FID reproduces closely (447.89 vs canonical 454.39), so the discrepancy is on
the **framework** arm (runner seed/config drift), not the FID method. The
*internal* tuned-baseline comparison (framework@50 vs baseline@{50,100,200})
is valid regardless and is the load-bearing result here.

Prior evidence (reused, no new GPU sweep): Wave 225 P9
(`verification_outputs/wave225-p9-r5b-matched-eff-nfe.json`) matched the
framework's *effective* NFE to the baseline's (framework nominal NFE=100,
n_rounds=2 → effective 50 vs baseline NFE=50) and found the framework
**ΔFID = +20.89 % WORSE** — the matched-effective-NFE hypothesis is falsified;
the R5b regression is not a compute artifact.

---

## 2.5 R5c — MNIST FM (NEW sweep) — **straw-man concern REFUTED**

Driver: `scripts/gap12_mnist_tuned_baseline.py`. Baseline solver steps ∈
{50, 100, 200} with the framework held at its matched NFE (4 rounds × 12 ≈ 48),
N=1000, seed 42, smoke ckpt. Evidence:
`verification_outputs/gap12-mnist-tuned-baseline.json`.

| baseline steps | baseline FID | framework@matched FID | verdict |
|---:|---:|---:|---|
| 50  | 29.4925 | 23.3879 | framework BEATS |
| 100 | 29.4902 | 23.3879 | framework BEATS |
| 200 | 29.4890 | 23.3879 | framework BEATS |

**Verdict:** the R5c smoke-ckpt win **survives** baseline tuning. The baseline
FID is **step-insensitive** (29.4925 → 29.4890 across 4× steps — the smoke
ckpt's ODE converges by 50 steps), so the framework's −28.43 % matched-NFE
margin cannot be a compute artifact. (Baseline steps=50 reproduces the
canonical 29.4925 **exactly**, validating the driver.)

---

## 3. LineageFlow cells (R1, R6, K4, K5, K7) — structurally compute-invariant

The LineageFlow **baseline arm is a bare RNG sampler** over each Pfam family's
amino-acid bias — it does not run an ODE solver and consumes no NFE:

- `tools/gen_lineageflow_n1000_fastas.py:598` `_write_baseline_arm(...)` calls
  `_generate_sequence(rng, ...)` (line 165) → `_biased_aa(rng, ...)` (line 205)
  → `rng.choices(aas, weights=weights, k=n)` (line 205). The only inputs are the
  per-arm RNG sub-stream and the Pfam AA-bias profile.
- The `--nfe` flag is plumbed only into the **framework** arm
  (`NFE_PER_RECORD`, read by `_write_framework_arm`); it never touches the
  baseline.

Therefore the baseline's output is **byte-identical for every NFE budget** —
there is no compute knob to tune, and the matched-NFE protocol *is* the
best-baseline protocol. This is corroborated by the canonical NFE ladder
(`verification_outputs/wave183-p4-aggregation.csv`, NFE ∈ {10, 25, 50, 75, 100,
150, 200, 300, 500}), where the LineageFlow baseline pLDDT is **byte-constant
(41.1798)** at every NFE.

**Consequence for the straw-man concern:** on R1/R6/K4/K5/K7 the framework
cannot be winning by denying the baseline compute, because the baseline uses
none. The concern is structurally impossible for these five cells.

---

## 4. R2, R3/K1, R5a — structural / residual / well-averaged

### 4.1 R2 — Kanzi RMSD — **structurally compute-invariant**

- The headline is a paired per-record **RMSD** comparison at N=1000
  (`verification_outputs/wave218-p3-kanzi-framework-wins.json`: framework
  mean Å 0.8838 vs baseline 0.9028, d_z = −0.0990, p = 0.0018).
- The RMSD is produced by a **direct DAE encode/decode** (`kanzi.DAE.encode +
  decode + kabsch_rmsd`) — there is **no flow rollout and no NFE knob**. The
  R2 baseline artifact states this explicitly:
  `paper-data/R2_kanzi_rmsd/kanzi_n1000_paper_metrics.json` →
  `"nfe_budget": "n/a (DAE encode is direct; not a flow rollout)"`. So the
  baseline RMSD cannot be improved by giving the baseline more compute: the
  matched protocol *is* the best-baseline protocol.
- The framework's swept axes are also invariant: the canonical NFE scan
  (`verification_outputs/kanzi_nfe_scan_q4_2026.json`, NFE ∈ {10, 50, 200, 500,
  1000, 2000}, seeds 42/43/44) reports the **validity rate saturated at 1.0**
  and the **internal composite byte-identical across all six NFE budgets** at
  each seed (0.18566 / 0.17017 / 0.15253 — 18/18 cells `TIE_AT_SATURATION`).
- **Verdict:** R2 is structurally compute-invariant on both its headline (RMSD)
  and swept (validity/composite) axes — the straw-man concern is impossible.
  (Earlier this cell was mis-documented as "residual, needs elevated-NFE
  re-run"; that framing was wrong because the DAE encode has no NFE.)

### 4.2 R3 / K1 — FlowMol3 (fg_dev / RDKit validity) — **residual**

- The existing NFE scan (`verification_outputs/flowmol3_fine_nfe_q4_2026.json`,
  NFE ∈ {5, 10, 25, 50, 100, 200}) reports a **degenerate TIE**: baseline ==
  framework == 0.073404 at every NFE (the `reduction_value` metric). It carries
  no headline signal.
- A fresh attempt was made — `tools/run_real_ckpt_eval.py --model flowmol3`
  (and `flowmol3_v2`, `--n-molecules 4`) at NFE ∈ {50, 100, 200} with
  `--force-mode real --metric-mode real --paper-metrics`
  (`verification_outputs/gap12-flowmol3-tuned-nfe.json`,
  `gap12-flowmol3v2-tuned-nfe.json`) — but the harness's FlowMol3 metric stays a
  degenerate TIE (`0.073404`) and `--paper-metrics` degrades to `none`
  (`no _PAPER_QUANTITY_PROFILES entry`), so it does not surface fg_dev.
- The v2 SOTA runner (`tools/run_sota_flowmol3_v2_adapter_experiment.py`) has the
  right `--baseline-nfe` plumbing but its own docstring states it runs the
  **synthetic NumPy velocity field** (backend `numpy`) — "validity numbers will
  sit near zero on both arms until real FlowMol3 weights land". So it is not a
  real-fg_dev tuned-baseline either.
- **Residual:** a tuned-baseline comparison on the fg_dev / RDKit-validity axis
  requires the **real FlowMol3 production checkpoint pipeline** at elevated NFE
  (not reproducible from the harnesses available here). R3 and K1 share this one
  blocker (same model).

### 4.3 R5a — 2D Two Moons — **straw-man REAL (magnitude not robust)**

- The canonical headline (`verification_outputs/g1_deep_dive_q3_2026.json`, row
  `twodim_fm_2d_ablation`: baseline W2 2.85 → framework W2 0.62, 4.6×) is
  produced by `tools/run_ablation.py`. Reproduced fresh (seed 42):
  `single_pass` final_w2 = **2.6691** (1 round), `multi_round_no_restart`
  final_w2 = **0.3482** (20 rounds). The canonical protocol is reproduced.
- **Sample-count confound:** `ReInferenceResult.endpoints` is `(n_rounds, 2)`
  (`adaptive_reflow/algorithm/runner/runner.py:240`), so the ablation's W2 is
  computed over **1 point** (`single_pass`) vs **20 points**
  (`multi_round_no_restart`). `multi_round_no_restart` uses `beta=1.0`
  (memory_fraction = 0 → full fresh noise each round), i.e. the 20 endpoints are
  **20 independent draws**. The 4.6× "win" therefore confounds sample count with
  the framework effect.
- **Well-averaged protocol** (`tools/run_sota_2d_experiment.py`, 1000
  samples/round × 20 rounds, seed 0; same adapter/weights/evaluator for both
  arms): baseline W2 = **0.0790**; framework per scheduler — CosineAnneal
  0.0866 (−9.7 %), **CodimensionSheet 0.0746 (+5.6 %), the only win**,
  EvidenceDriven 0.0834 (−5.6 %), FreeTraj 0.0822 (−4.0 %). Only **1 of 4**
  schedulers beats the baseline, and only by **+5.6 %** — not 4.6×. Evidence:
  `verification_outputs/gap12-2d-sota-wellaveraged/` (comparison.md + per-arm
  CSVs + summary.json).
- **Verdict:** the R5a headline magnitude is **not robust to the baseline's
  sample count**. The canonical ablation's small-sample baseline makes the
  framework look 4.6× better; under a well-averaged baseline the framework is at
  near-parity (1/4 schedulers win, +5.6 %). Caveat: the two protocols differ in
  sample count and scoring path, so this is a **magnitude** exposure, not a
  claim that the canonical run is wrong.
- The earlier attempt `scripts/gap12_2d_tuned_baseline.py` (retained) swept the
  adapter `num_steps` ∈ {100, 200} but gave identical W2 (0.08284) at both —
  because the runner hardcodes `delta_spec={"num_steps": 100}`
  (`adaptive_reflow/algorithm/runner/runner.py:336`), so the sweep was a no-op.
  It is kept as a protocol note only.

---

## 5. Files

- `scripts/gap12_tuned_baseline.py` (R5b baseline-NFE sweep)
- `scripts/gap12_mnist_tuned_baseline.py` (R5c baseline-steps sweep)
- `scripts/gap12_2d_tuned_baseline.py` (R5a attempt; retained as protocol note)
- `verification_outputs/gap12-tuned-baseline-cifar.{json,csv}`
- `verification_outputs/gap12-mnist-tuned-baseline.{json,csv}`
- `verification_outputs/gap12-2d-tuned-baseline.{json,csv}`
- `verification_outputs/gap12-2d-sota-wellaveraged/` (R5a well-averaged run:
  `summary.json`, `two_moons_comparison.md`, per-arm CSVs)
- `verification_outputs/gap12-flowmol3-tuned-nfe.json` +
  `gap12-flowmol3v2-tuned-nfe.json` (R3/K1 residual attempts)
- this audit doc
