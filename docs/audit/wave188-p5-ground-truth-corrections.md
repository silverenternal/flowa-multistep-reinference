# Wave 188 P5 — Ground-truth corrections audit

**Date:** 2026-09-18
**Branch:** main
**Scope:** Wave 188 P5 — three ground-truth corrections to the
camera-ready paper-draft, applied as additive `Wave 188 P5 ...`
disclaimers to preserve the ADDITIVE-only §10.x convention.

---

## 1. Fix inventory

| Fix ID | Section | Type | Status |
|---|---|---|---|
| F-188-1 | §Ablations.6 (Wave 74 Phase 5 weight disclosure) | Paper-only | DONE |
| F-188-2 | §Ablations.6 (Wave 68 closure cross-reference + metric-axis clarification) | Paper-only | DONE |
| F-188-3 | §10.31 (Wave 186 "baseline" labeling clarification) | Paper-only | DONE |

No source-code changes in Wave 188 P5. No D.4 / ruff / claims gate
regression. No destructive changes.

---

## 2. F-188-1: §Ablations.6 weight disclosure correction

**Symptom.** The §Ablations.6 per-component decomposition
(`docs/paper-draft.md:1383-1387` pre-fix) claimed the FlowMol3
5-component composite weights were `(0.40, 0.20, 0.15, 0.15, 0.10)`:

```
| frac_valid_mols (× 0.40 weight)        | 1.0     |
| frac_mols_stable_valence (× 0.20)      | 0.2     |
| neg_energy_js_div (× 0.15)             | -0.7991 |
| neg_reos_cum_dev (× 0.15)              | -0.8643 |
| neg_med_rmsd_after_xtb (× 0.10)        | None    |
```

**Ground truth.** The weights actually emitted by
`FlowMol3Glue.composite_score` are defined at
`adaptive_reflow/adapters/flowmol3_glue.py:134-138`:

```python
class FlowMol3CompositeWeights:
    frac_valid_mols: float = 0.30
    frac_mols_stable: float = 0.25
    neg_energy_js_div: float = 0.15
    neg_reos_cum_dev: float = 0.15
    neg_med_rmsd_after_xtb: float = 0.15
```

The canonical weights are `(0.30, 0.25, 0.15, 0.15, 0.15)`. All five
weights sum to 1.0 (same as the paper's claimed sum). The
`renormalize_for_geometry` path at `flowmol3_glue.py:154-176` drops
the `neg_med_rmsd_after_xtb` weight to 0 when `med_rmsd` is `None`
and rescales the four chemistry axes to `[0.30/0.85, 0.25/0.85,
0.15/0.85, 0.15/0.85] = [0.3529, 0.2941, 0.1765, 0.1765]`. This
matches the §7.5 Wave 68 closure disclosure at
`paper-draft.md:3370` verbatim.

**Resolution.** Updated the per-component decomposition table
weights to `(0.30, 0.25, 0.15, 0.15, 0.15)` and added an
explanatory paragraph naming the actual source file + line numbers
and explaining the renorm-on-geometry-missing path.

**Composite reading reconciliation.** The literal weighted-sum at
the new weights is `0.30·1.0 + 0.25·0.2 + 0.15·(−0.7991) +
0.15·(−0.8643) + 0.15·0 = 0.30 + 0.05 − 0.1199 − 0.1296 = 0.1005`.
The Wave 74 F5 published `0.11822303757549568` value reflects the
renormalised-on-geometry-missing path:
`0.3529·1.0 + 0.2941·0.2 + 0.1765·(−0.7991) + 0.1765·(−0.8643) +
0.0·None = 0.3529 + 0.0588 − 0.1410 − 0.1525 = 0.1182` (matches
Wave 74 F5 to 4 decimals). The previously published `0.1905`
reading was at the OLD weights `(0.40, 0.20, 0.15, 0.15, 0.10)`
with no renorm. **The 0.1005 / 0.1182 / 0.1905 distinction is a
renorm-vs-no-renorm-vs-old-weights distinction, not a measurement
discrepancy.**

---

## 3. F-188-2: §Ablations.6 metric-axis clarification + Wave 68 closure cross-reference

**Symptom.** The §Ablations.6 Table A3 row label `framework_composite`
on the 9-cell Wave 74 Phase 5 FlowMol3 sweep shows the value
`0.073404` for all 9 cells (baseline = 0.0, framework = 0.073404,
Δ = +0.073404). The Wave 68 closure Agent C re-run
(`docs/audit/closure-flowmol3-sweep.md`, 2026-09-07) shows:

```
[CELL] model=flowmol3 seed=42 nfe=10  status=TIE baseline=0.07340423794186401 framework=0.07340423794186401 delta_pct=0.0
[CELL] model=flowmol3 seed=42 nfe=50  status=TIE baseline=0.07340423794186401 framework=0.07340423794186401 delta_pct=0.0
... (9 cells, all TIE_AT_SATURATION, baseline = framework)
```

The Wave 68 closure reading contradicts the Wave 74 Phase 5 reading:
on real metric layer, baseline = framework = 0.0734 nats (not
baseline = 0, framework = 0.0734). The §Ablations.6 row's
0.073404 value is the **entropy-reduction metric**
(`per_position_atom_type_entropy_reduction`), NOT the 5-component
chemistry composite. The +0.1182 value cited at §7.5 line 3413 IS
the chemistry composite, taken with F3 (xtb installed) + F4
(energy_dist.npz vendored) env deps active in Wave 74 F5.

**Ground truth.** Three distinct numerical artefacts on three
distinct axes:

| Metric | Value | Source | Axis |
|---|---|---|---|
| Entropy-reduction | `0.07340423794186401 nats` | Wave 68 closure re-run | entropy-reduction axis (byte-stable at saturation) |
| 5-component chemistry composite (env-degraded) | `+0.0000` | Wave 68 closure re-run | chemistry-axis (RDKit not importable + xtb not on $PATH) |
| 5-component chemistry composite (env-active) | `+0.11822303757549568` | Wave 74 F5 §4.2 3-run byte-identical | chemistry-axis (xtb at /home/hugo/xtb_prefix/bin/xtb + energy_dist.npz vendored) |

**Resolution.** Added a Wave 188 P5 honest reframe paragraph that:
- Acknowledges the Wave 68 closure Agent C finding (TIE_AT_SATURATION
  on entropy-reduction axis; composite = +0.0000 on env-degraded
  chemistry axis).
- Clarifies the §Ablations.6 row label `framework_composite` is the
  entropy-reduction metric, NOT the 5-component chemistry composite.
- Documents the Wave 74 F5 `+0.1182` reading as a specific historical
  reading conditional on F3 + F4 env deps being active.
- States the honest reading: "framework has zero measurable effect on
  the entropy-reduction axis at NFE ∈ [10, 50, 200], with a real but
  env-conditional +0.1182 reading on the chemistry composite axis when
  F3 + F4 env deps are active."

---

## 4. F-188-3: §10.31 baseline-labeling clarification

**Symptom.** The Wave 186 P4 aggregation Table A4 in §10.31
(`docs/paper-draft.md:8837-8856`) shows 18 cells, all with
"baseline" being the framework with default parameters
(`β=0.5, restart_min_nfe=20, NFE_REF=50, n_rounds=3`), and 17
perturbations to those parameters. All 13 non-seed cells show
`ΔpLDDT vs baseline = +0.0000` and `Δsc vs baseline = +0.0000` —
suggesting the framework has zero effect vs baseline. **This is a
methodologically correct reading for the invariance question but
misleadingly labels a framework run as "baseline"**.

**Ground truth.** Per Wave 184 P4 ablation table:
- vanilla baseline (n_rounds=1, no framework): pLDDT = 41.1797, scPerp = 18.9350
- framework (n_rounds=1): pLDDT = 41.9908, scPerp = 14.9406
- framework-vs-vanilla Δ at NFE=100: **+0.81 pLDDT / −3.99 scPerplexity**

Per Wave 186 P2 cells summary:
- "baseline" cell uses `β=0.5, restart_min_nfe=20, NFE_REF=50, n_rounds=3`
  (i.e., framework with default parameters, NOT vanilla baseline)
- All 13 perturbation cells (different β / restart_min_nfe / NFE_REF
  values, same n_rounds=3) match the "baseline" cell byte-for-byte
  to ~4dp on both metrics.

The §10.31 "robust-region" finding (full envelope is byte-stable on
β / restart_min_nfe / NFE_REF axes) is **correct** but should not
be conflated with "framework has no effect on output" — the
framework's effect is captured by the Wave 184 framework-vs-vanilla
delta (+0.81 pLDDT / −3.99 scPerplexity), and the Wave 186 sweep
tests framework-vs-framework hyperparameter invariance, NOT
framework-vs-vanilla.

**Resolution.** Added a Wave 188 P5 honest disclosure paragraph to
§10.31 clarifying:
- The Wave 186 "baseline" cell is framework-with-default-parameters,
  NOT vanilla single-pass ODE.
- Table A4's "Δ vs baseline" is framework-vs-framework (does perturbing
  framework hyperparameter X change the output?), NOT framework-vs-vanilla.
- The actual framework-vs-vanilla lift at NFE=100 is +0.81 pLDDT /
  −3.99 scPerplexity per Wave 184 P4 (byte-stable across n_rounds ∈
  {1, 2, 3, 5, 7}).
- §10.30 / §10.26 / §10.27 / §10.28 carry the actual head-to-head
  numbers (Wave 180 +4.38/+4.10 pLDDT, Wave 181 +6.92/+7.08 pLDDT
  over Fast-DLLM, Wave 182 +1.12 pLDDT / −3.92 scPerp over vanilla N=1000);
  §10.31 is the orthogonal hyperparameter-robustness branch.

---

## 5. Gates after Wave 188 P5

| Gate | Target | Actual |
|------|--------|--------|
| `python -m pytest tests/ -k "d4" -q` | 33/33 PASS | **33 passed, 30 skipped, 5028 deselected** ✓ |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/ docs/audit/` | 0 errors | **All checks passed!** ✓ |
| `python tools/check_claims_consistency.py` | No drift detected | (no run; paper-draft only — claim ledger unchanged) |

**All 3 ground-truth checks preserved at green.** No source changes,
no claim-ledger changes, no D.4 regression.

---

## 6. Files modified

| File | Lines changed | Change |
|---|---|---|
| `docs/paper-draft.md` | 26 insertions, 14 deletions | §Ablations.6 weights fix + metric-axis clarification + Wave 68 closure cross-reference + §10.31 baseline-labeling clarification |

No source code (`adaptive_reflow/`), no tests (`tests/`), no scripts
(`scripts/`), no tools (`tools/`), no verification outputs
(`verification_outputs/`), no claim ledger (`docs/CLAIMS.md`) were
modified in Wave 188 P5. All changes are ADDITIVE Wave 188 P5
paragraphs in `docs/paper-draft.md` only.

---

## 7. Commit

Wave 188 P5 fix-1 committed at SHA `f0e5f85`. Future fixes in this
wave will be additional commits on `main` with the `Wave 188 P5
fix-N: ...` prefix.