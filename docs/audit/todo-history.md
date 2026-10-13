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

## 8. Removed surfaces

- **Removed 2026-10-13:** the legacy repo-root `todo.json` and the entire
  `todo/` directory (13 files), replaced by a single management surface per
  user directive.
- **Known dangling reference:** `docs/drafts/paper-A-final.md:842` still links
  `todo/RISK-REGISTER.md` R-019 (frozen manuscript; left untouched).
- **Repaired references:** `docs/README.md` and `docs/RELEASE-NOTES.md`
  pointers repointed at `todo.json`.
