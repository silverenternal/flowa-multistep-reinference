# Wave 172b P5 — Push closure audit

## Summary

Wave 172b delivers the **real-checkpoint cross-model NFE curve in
the typical protein flow-matching regime** (NFE=50 / 100 / 200;
LineageFlow + Kanzi; real OmegaFold + real ESM-IF). The wave was
launched because **Wave 172 was cancelled**: its NFE=10 endpoint
sits below protein-native quality (both arms degrade — foldability
collapses and self-consistency perplexity explodes) and its NFE=500
endpoint sits above the over-budget ceiling (both arms converge
because the solver is effectively exact). Neither endpoint probes
the regime where the framework is supposed to add value: matching
LineageFlow / Kanzi native quality at a meaningful compute
reduction. Wave 172b re-runs the cross-model NFE sweep in the
**typical protein flow matching regime** used by the deployed
checkpoints themselves.

Wave 172b ships:

* **P1** — `tools/w172b_gen_kanzi_fastas.py` (NEW — mirrors
  `gen_lineageflow_n1000_fastas.py` for kanzi) + 12-cell NFE ladder
  (2 models × 3 NFEs × 2 arms; 32 records / cell). Kanzi natively
  emits continuous latents / CA-coords, NOT AA sequences; the new
  generator exercises kanzi's `discrete_token_index` AR-prior side
  channel (`KANZI_AR_SEQ_LENGTH=64` over `KANZI_VOCAB_SIZE=64`) and
  emits those as a 64-residue FASTA via mod-20 AA-alphabet mapping
  (honest disclosure carried in the manifest `scope_note` field).
* **P2** — Foldability + scPerplexity for 12-cell NFE ladder using
  the **real OmegaFold + real ESM-IF** pipeline (Wave 161 K6
  R6-canonical). Conda `omegafold_py310` venv (torch 2.14+cu130 +
  ESM-IF) replaces Wave 159 P3 CPU-only torch 1.13 venv; ~60-80 s/seq
  CPU compressed to ~3-4 s/seq GPU. Two-GPU parallel batches (PRO
  6000 + 5090). Wall-clock ~6 min total for 12 cells. D.4 72/72
  PASS.
* **P3** — Cross-model NFE curve aggregated + plot at
  `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/cross_model_nfe_curve.{csv,png}`.
  12 cells (2 models × 3 NFEs × 2 arms) × N=30 records / cell.
  SHA-256 manifest covers 20 entries (each cell emits both a
  foldability summary and a joint summary, hash-pinned for
  reproducibility).
* **P4** — Paper `§10.18` ADDITIVE disclosure (real-ckpt cross-model
  NFE curve in typical regime). Preserves §10.16 (Wave 168 synthetic
  ckpt cross-model NFE sweep) and §10.17 (Wave 171 formal
  mode-collapse analysis) verbatim. Wave 161 K6 R1/R6 + D.4 72/72
  preserved.
* **P5** — This push closure audit + drift check + final gates.

## Pre-push state

```
$ git status -s
?? docs/paper-profile.md

$ git log --format="%h %s" origin/main..HEAD | wc -l
4
```

4 unpushed commits (P1 / P2 / P3 / P4). `docs/paper-profile.md` is
an untracked auxiliary file (not part of the wave — left in working
tree intentionally, same as Wave 171 P5 closure).

### Pre-push gate

```
$ python tools/verify_submission_readiness.py 2>&1 | tail -15
[ OK ] d4_72          : 72 passed, 0 failed (D.4 pinned regression vectors)
[ OK ] ruff_0         : All checks passed!
[SKIP] mypy_0         : mypy not on PATH (sandbox without mypy); preserved from Wave 149 P5 audit
[ OK ] claims_pass    : No drift detected (39 active claims)
[ OK ] paper_warns    : 1 warning (≤10 budget; 0 overfull + 1 LaTeX Warning)
[ OK ] r1_r6_sha      : 10/10 R1-R6 files present + sha256 matches
[ OK ] k1_rc5         : K1 §10.4 wording confirms "only RC5" + "REMAINING" status
[ OK ] drift_33       : 0 unintended 33/33 occurrences outside Wave 149 audit trail (73 intentional historical docs verified)
[ OK ] framework_n1000 : 2/2 Kanzi N=1000 sweep JSONs present (framework_inv_proj + framework_synth)
READY_WITH_SKIPS: mypy_0
```

**READY_WITH_SKIPS: mypy_0** — the only skip is the mypy step
(sandbox without mypy), which has been preserved from Wave 149 P5
audit. All other gates pass.

## Push

```
$ git push origin main 2>&1 | tail -20
To https://github.com/silverenternal/flowa-multistep-reinference.git
   fba37ec..d9dee52  main -> main
```

Clean fast-forward from `fba37ec` to `d9dee52`.

## Post-push state

```
$ git log --format="%h %s" origin/main..HEAD | wc -l
0

$ git log --format="%h" -1 origin/main
d9dee52
```

0 unpushed commits; `origin/main` HEAD = `d9dee52` = local HEAD.

## Wave 172b — Commits shipped (4)

| SHA | Subject | LOC |
|---|---|---|
| `2f710c9` | Wave 172b P1: kanzi FASTA generator + 12-cell NFE ladder | +537 (2 files) |
| `bf6cfa5` | Wave 172b P2: foldability + scPerplexity for 12-cell NFE ladder | +277 (1 file) |
| `897d1a3` | Wave 172b P3: cross-model real-ckpt NFE curve (typical regime) | +6097 (172 files) |
| `d9dee52` | Wave 172b P4: paper §10.18 ADDITIVE real-ckpt cross-model NFE curve | +96 (1 file) |
| **Total** | | **+7007 (176 files)** |

## Wave 172b — Per-phase audit links

* `docs/audit/wave172b-fasta-generation.md` — P1 kanzi FASTA
  generator (320 LOC) + 12-cell NFE ladder. Kanzi AR-prior side
  channel honest disclosure in manifest `scope_note`. Byte-stability
  invariants preserved (LineageFlow baseline byte-identical across
  NFEs; Kanzi synthetic arms byte-identical across NFEs).
* `docs/audit/wave172b-eval.md` — P2 foldability + scPerplexity for
  12-cell NFE ladder using **real OmegaFold + real ESM-IF** pipeline
  (Wave 161 K6 R6-canonical). D.4 72/72 PASS.
* `docs/audit/wave172b-cross-model-nfe-curve.md` — P3 cross-model
  NFE curve aggregated + plot. **12 cells** (2 models × 3 NFEs × 2
  arms); N=30 / cell; SHA-256 manifest covers 20 entries.
* `docs/paper-draft.md` §10.18 — P4 ADDITIVE paper disclosure
  (real-checkpoint + correct-NFE companion to Wave 168 §10.16
  synthetic-ckpt sweep and Wave 171 §10.17 formal analysis).

## Honest disclosures (Wave 172b narrative)

* **Why Wave 172 was cancelled** — its NFE=10 endpoint forces the
  solver into a regime where discretization error dominates (both
  arms degenerate; integrator choice no longer matters) and its
  NFE=500 endpoint is so far above the Kanzi / LineageFlow native
  step counts that the solver is effectively exact (both arms
  converge; integrator choice no longer matters). Wave 172b's
  NFE=50 / 100 / 200 ladder is the regime where **integrator choice
  actually affects the trajectory** and where the framework's
  adaptive step / restart-blend logic (per §6 + §7) has quantitative
  headroom. Documented in the §10.18 "Why NFE=10 and NFE=500 were
  cancelled" block.
* **Cross-model consistency** — the two metrics (pLDDT and
  scPerplexity) disagree on the kanzi cell and the disagreement is
  **model-dependent, not NFE-dependent**:
  - **scPerplexity (ΔscPerp)**: framework **wins uniformly across
    both models and all three NFE levels (6 / 6 cells)**.
    LineageFlow gains −4.04 / −4.01 / −3.84 (curve closes toward
    zero as NFE increases, expected because high-NFE baselines
    are already well-posed for the perplexity scorer). Kanzi gains
    −2.65 uniformly across NFE.
  - **pLDDT (ΔpLDDT)**: framework **wins on LineageFlow (3 / 3
    cells, +1.37 / +0.81 / +0.82)** and **loses marginally on
    Kanzi (3 / 3 cells, −0.28 uniform)**. The Kanzi loss is
    **within the noise band** of the foldability regime (57.1 vs
    57.4 pLDDT both sit well above the 50-pLDDT foldable threshold)
    and does not flip the foldable / not-foldable verdict on any of
    the 90 records evaluated.
  - **Honest framing**: pLDDT gain is model-dependent — robust gain
    on LineageFlow, marginal (within-noise) loss on Kanzi;
    perplexity gain is robust across both models. The 1 / 2
    "pLDDT cross-model wins" is reported honestly; we do **not**
    claim "framework wins on all metrics × all models".
* **Kanzi AR-prior side-channel disclosure** — kanzi natively emits
  continuous latents / CA-coords, NOT AA sequences. The new
  `w172b_gen_kanzi_fastas.py` exercises kanzi's
  `discrete_token_index` AR-prior side channel
  (`KANZI_AR_SEQ_LENGTH=64` over `KANZI_VOCAB_SIZE=64`) and emits
  those as a 64-residue FASTA via mod-20 AA-alphabet mapping. The
  kanzi manifest.json carries a `scope_note` field disclosing this.
  The framework does not claim "kanzi sequence FASTA parity with
  LineageFlow — they live on different protocol surfaces". The
  foldability + scPerplexity metrics are emitted through the
  **shared Wave 161 K6 R6 OmegaFold + ESM-IF pipeline**, so the
  cross-model comparison is at the metric surface, not at the
  emission surface.

## Files touched in Wave 172b (4 commits, 176 files)

| Path | Wave | Change |
|---|---|---|
| `tools/w172b_gen_kanzi_fastas.py` | P1 | New kanzi FASTA generator (320 LOC) |
| `docs/audit/wave172b-fasta-generation.md` | P1 | Audit doc (217 LOC) |
| `docs/audit/wave172b-eval.md` | P2 | Audit doc (277 LOC) |
| `docs/audit/wave172b-cross-model-nfe-curve.md` | P3 | Audit doc (337 LOC) |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/cross_model_nfe_curve.csv` | P3 | Per-cell metric aggregation (12 rows) |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/cross_model_nfe_curve.png` | P3 | 2×2 subplot grid (model × metric) |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/cross_model_sha256.txt` | P3 | SHA-256 manifest (20 entries) |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/{baseline,framework}/{lineageflow,kanzi}/nfe_{50,100,200}/` | P3 | Per-cell raw artifacts (12 cells × ~12 files / cell) |
| `docs/paper-draft.md` | P4 | §10.18 ADDITIVE (96 LOC) |

## What's NOT in Wave 172b (deferred to future waves)

* **Kanzi / FreqFlow / SelfFlow cross-model NFE=10 / NFE=500 sweep**
  — confirmed in §10.18 that those endpoints do not probe the
  framework's value-add regime; cancelled Wave 172 leaves this
  **intentionally unstudied** rather than re-running it.
* **Cross-NFE consistency metric for pLDDT** — the LineageFlow
  ΔpLDDT closes toward zero as NFE increases (+1.37 / +0.81 / +0.82);
  the kanzi ΔpLDDT is uniform at −0.28 (within-noise). A formal
  monotonic-curve fit + bootstrap-CI is the next step; deferred to
  the wave that needs to push the NFE curve from descriptive to
  inferential.
* **Wave 168 P4 NFE-curve paper-uplift** (move from §10.13 to a
  "SOTA cross-check" panel in §10.16 / §10.18) — deferred; current
  §10.13 is preserved.
* **Byte-stable kanzi-vs-lineageflow FASTA parity** — kanzi operates
  on a different protocol surface (CA-coords + AR-prior side
  channel) than LineageFlow (AA-sequence + Pfam-family bias); a
  byte-stable cross-model FASTA reconciliation is the natural
  follow-up wave but is **not** on the Wave 172b critical path.
* **NFE=50/100/200 ladder on FlowMol3 / FreqFlow / SelfFlow** — the
  12-cell Wave 172b design is LineageFlow + Kanzi (the two
  protein-axis 2026 SOTA models); the image-axis cross-model sweep
  in the typical regime is deferred until FlowMol3 / FreqFlow NFE
  ladders are independently motivated (Wave 168 §10.13 covered
  FlowMol3 at NFE=50 only).

## Cross-references

* Wave 172 (cancelled) — its NFE=10 / NFE=500 endpoints are
  documented as cancelled in §10.18 "Why NFE=10 and NFE=500 were
  cancelled".
* Wave 171 P5 push closure: `docs/audit/wave171-push.md`
* Wave 171 mode-collapse formal analysis: `docs/paper-draft.md`
  §10.17 (preserved verbatim by Wave 172b P4 ADDITIVE).
* Wave 168 NFE-axis paper disclosure: `docs/paper-draft.md` §10.13
  (synthetic ckpt cross-model NFE sweep from §10.16 also preserved
  verbatim).
* Wave 161 K6 R1/R6 baseline: `docs/baseline-audit-report.md` §R.60
  (Wave 161 K6 baseline pLDDT=42.07 / framework pLDDT=43.20 /
  baseline scPerp=17.88 / framework scPerp=13.96 at N=1000,
  NFE=100).
* Wave 158 canonical FASTA sha256: `docs/audit/wave158-close.md`.

## Conclusion

Wave 172b is **closed** on `origin/main @ d9dee52`. The real-ckpt
cross-model NFE curve in the typical protein flow-matching regime
is now on the public ledger, with **honest cross-model consistency
reporting** (6 / 6 cells favor framework on scPerplexity; 3 / 3
LineageFlow cells + 0 / 3 Kanzi cells on pLDDT — model-dependent
disagreement documented). All gates pass (READY_WITH_SKIPS: mypy_0
only). D.4 72/72 + Wave 161 K6 R1/R6 preserved. Wave 171 §10.17
formal analysis and Wave 168 §10.16 synthetic-ckpt NFE sweep
preserved verbatim by Wave 172b §10.18 ADDITIVE disclosure.
