# 2026-10-27 — No-experiment manuscript and submission refresh

**Increment:** `paper-refresh-2026-10-27`
**Scope:** documentation only. No sweep was launched, no model was sampled,
and **no measured number was changed**. The refresh moves three cells from
projected or conditional evidence to evidence that already existed on disk
but was not in the manuscript, and propagates that through every surface that
quotes them.

---

## 1. Why this was done

The manuscript frozen at `v3.1` (2026-10-18) quoted the weakest version of
three cells while the stronger measured evidence sat unused:

| cell | what the frozen manuscript said | what the artifacts already contained |
|---|---|---|
| R5c | smoke checkpoint `d_z = −13.18`, arms **not NFE-matched** (25/48/25 vs a 50-step baseline); production "regresses +10.37%" | four checkpoints × seven NFE rungs at N=1000 and 3 seeds (`verification_outputs/gap84-cap-frontier/`): a frontier WIN on `w16e1_5k`, TIEs elsewhere |
| R3 | `PARTIAL / single-seed PROJECTED`, derived from an N=200 REOS proxy | a three-seed test at N=1000 per arm (`verification_outputs/r3_n1000_3seed_fixed_q4_2026/`) |
| R6 | `STRONG via tier-aware counterfactual` | a live tier-aware run (`verification_outputs/gap31-r6-live-uplift/`) |

Submitting the frozen text would have led with a budget-confounded point
estimate and a projection, while leaving the strongest measured result out of
the paper. The user authorised a documentation refresh without new
experiments ("先做无实验刷新再投").

---

## 2. Observed facts (what changed, and from which artifact)

### 2.1 R5c — checkpoint-conditional NFE frontier

Protocol as executed: N=1000 per arm, seeds 42/43/44, rungs
{4, 5, 10, 25, 50, 100, 200}, `evidence_driven` arm, at least two integration
steps per round, plateau = mean of the last two rungs, dual dominance rule
(1-FID floor and 1% relative margin).

| checkpoint | baseline plateau | framework plateau | Δ FID | Δ rel | strict rungs | verdict |
|---|---:|---:|---:|---:|---:|:---|
| `w16e1_5k` | 24.4839 | 21.3632 | −3.1206 | −12.75% | 7/7 | WIN |
| `w16e1_10k` | 16.9537 | 15.9501 | −1.0036 | −5.92% | 0/7 | TIE |
| `w16e1_60k` | 11.3795 | 11.3945 | +0.0150 | +0.13% | 0/7 | TIE |
| `production` | 9.9938 | 9.9603 | −0.0335 | −0.34% | 0/7 | TIE |

Source: `verification_outputs/gap84-cap-frontier/frontier_{w16e1_5k,w16e1_10k,w16e1_60k,production}.json`;
audit `docs/audit/gap84-inference-frontier.md`. Values re-derived in this
session from the JSON (`baseline_plateau.value`, mean of the NFE 100 and 200
`framework` entries) and matched the manuscript table to four decimals.

**Consequence for the old reading.** The single-budget series ran the
framework arm at 25–48 steps against a 50-step baseline. Its positive Δ FID at
`w16e1_10k`/`w16e1_60k`/`production` therefore mixed a budget penalty with a
checkpoint effect. At matched rungs those checkpoints are neutral, not worse.
The manuscript now says this explicitly instead of calling them regressions.

### 2.2 R3 — three-seed test

`verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.json`:
N=1000 per arm, NFE=250, seeds 42/43/44, ten batches of 100 molecules per arm.

mean −0.03769, sd 0.09390, se 0.05421, t=−0.695, df=2, p=0.5589,
d_z=−0.4014, 95% CI [−0.27095, +0.19557], α=0.007143, `bonf_sig=false`.

The single-seed seed-42 reading (−0.061, p=0.043) does not survive. The
`real_restart_blend` arm gives −0.05476 (sd 0.15262, d_z=−0.3588, p=0.5977)
per `verification_outputs/gap39-flowmol3-real-restart-blend/summary.json`.
The N=200 REOS flag-count proxy (`d_z=−0.285`) is retained only as a retired
proxy.

### 2.3 R6 — live tier-aware run

`verification_outputs/gap31-r6-live-uplift/gap31_summary.json`: three seeds at
N=1000 per seed, n=3000 pooled. scPerplexity pooled d_z=−0.8393
(diff −3.6823), sign-consistent on 3/3 seeds and all three tiers; hard-tier
pLDDT d_z=+1.1211 (n=990); pooled pLDDT d_z=+0.1466 (diff +2.6386), below the
+0.2235 bar. The counterfactual (+0.2235) and grid-search (+0.6467) are
retained as design validation.

---

## 3. Surfaces updated

| surface | change |
|---|---|
| `docs/drafts/paper-A-final.md` | abstract, intro, contribution (v), §7.1 (three passages + figure caption), §7.2 (R5c, R6, R1, R3, aggregate distribution, power-index rows), §7.3, §7.5, §7.6.1, §7.9 (rewritten as the frontier, old curve kept as history), §7.10, §7.11 (intro + three rows), §8.3, §8.7, §10.2, §10.3, §10.5(d), §10.8, §11.1 |
| `docs/drafts/paper-A-final.tex` | same set (abstract, §I contribution (iv), §VII-A scope, Table III rows, Figure 3 caption, §VII-B R5c/R6/R3/aggregate, §VII-C, §VII-E, §VII-F, §VIII-C seed coverage, §IX synthesis, §X limitations) |
| `docs/drafts/abstract-final.md` | banner: historical working abstract, paper file is authoritative |
| `tools/render_cell_evidence_figure.py` | PANEL_A → R3 −0.401, R6 −0.8393 / +1.1211, R5c removed (frontier carries no single standardised effect); PANEL_B → 3/1/1/2/4 |
| `docs/figures/fig9_cell_evidence_comparison.png` | re-rendered, byte-stable across two invocations, sha256 `54c37142…`, 149598 bytes |
| `docs/CLAIMS.md` | additive status-flag sentences in CLM-059, CLM-060, CLM-068, CLM-073. **No existing wording, number or status field was edited.** Claim counts unchanged (61 active / 0 provisional / 2 deprecated) |
| `docs/CONSOLIDATED_RESULTS.md` | new `§15.106` + one `§15.INDEX` row + index counts |
| `docs/paper-evidence.json` / `docs/PAPER-EVIDENCE.md` | added `paper_label` per cell and `summary.paper_labels`; register now carries both taxonomies explicitly |
| `tools/paper_evidence.py` | validates `paper_label`, cross-checks `summary.paper_labels`, renders the paper-label column and distribution |
| `tnnls_submission/{MANIFEST,cover_letter,highlights,tables,submission_checklist,SUBMISSION_READINESS,README,figures}.md` | new-artifact banner, verdict distribution, R3/R6 closure, page count 12, current SHA-256s |
| `todo.json` | `updated_at` 2026-10-27; execution-order items 7 and 8 rewritten |

---

## 4. Interpretation

- **The paper's headline changed, not its data.** The R5c frontier and the R3
  and R6 runs were already on disk. The refresh makes the manuscript quote
  them.
- **R5c is now the strongest cell in the paper** and the only one that
  satisfies both halves of the standing win rule. That is a fact about
  coverage, not about effect size: the other six R-level cells still have no
  usable frontier grid.
- **R3 got weaker, honestly.** The three-seed test replaces a projection and
  returns not-significant. The paper says so in the R3 row, the aggregate
  distribution and §11.1.
- **R6 got stronger on the axis that was measured** (scPerplexity, live) and
  unchanged on the axis that was not (pooled pLDDT stays below the bar).

---

## 5. Gates

| gate | command | result |
|---|---|---|
| claims consistency | `python3 tools/check_claims_consistency.py` | exit 0, no drift |
| register integrity | `python3 tools/paper_evidence.py --check` | exit 0, 11 cells, all paths and quotes verified |
| register tests | `python3 -m pytest tests/test_paper_evidence.py -q` | 7 passed |
| figure byte-stability | render twice, compare sha256 | identical (`54c37142…`) |
| PDF build | `pdflatex` ×2, `-halt-on-error` | exit 0, 12 pages, 0 overfull hboxes, 0 undefined references |
| D.4 regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30/30 PASS |
| ruff | `ruff check` on touched Python | 0 findings |
| mkdocs | `mkdocs build --strict` | exit 0 |

**Not run:** full `pytest tests/` (ordering-dependent; 2 pre-existing failures
in `tools/eval/sweep.py` unrelated to this change) and `mypy` (module absent
from the system interpreter, CLM-024).

---

## 6. Unresolved

1. **Frontier coverage.** Six of seven R-level cells have no complete
   (quality, NFE) grid. The paper's win rule cannot be satisfied for them by
   any amount of writing.
2. **R5c mechanism.** The crossover is measured but not explained: the four
   checkpoints differ in architecture and training-set size as well as in
   training time, so "under-trained" is not yet isolated as the cause.
3. **R3 power.** The three-seed test is underpowered for the observed effect
   (d_z=−0.401 at n_seeds=3). A larger seed count would be a power fix, not a
   mechanism fix, and is not proposed here.
4. **Submission metadata.** `MANIFEST.md` carries a long chain of dated
   addenda whose page counts disagree (8, 10, 11, 12). The new top banner
   states the current build; the historical lines were left in place rather
   than rewritten.

---

## 7. Artifacts

- `docs/drafts/paper-A-final.pdf` — 461403 bytes, 12 pages,
  sha256 `a0a0d97f07a078cdcc0695003c7258f487d10c04a6e12f21511740eb0709aec9`
- `docs/drafts/paper-A-final.tex` — 70688 bytes,
  sha256 `a6fcee684c1afbc27fc1911a59713db0a8c5e291b4a3e200515abd1dba0f1f1d`
- `docs/drafts/paper-A-final.md` — 222100 bytes,
  sha256 `85c90e5d619bc349384eccaa545723b7f09064ab4df0f5b96a93cc966ed7c482`
- `docs/figures/fig9_cell_evidence_comparison.png` — 149598 bytes,
  sha256 `54c37142033cac364c41a6b88ce5997b5a4ecd11b4573033544d35995dee9861`
- `docs/PAPER-EVIDENCE.md` — regenerated
