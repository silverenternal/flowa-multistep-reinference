# Table 1 — Paper quantity → framework function mapping

**Source paper**: Li 2026, *Gaussian Posterior Selection on Noncompact Fibres with Uniformly Separated Roots* (`NoiseSelectedRectification_EN.md`).
**Framework module**: `adaptive_reflow.contracts.paper_quantities` (`paper_quantities`).
**Grounding claims**: `docs/CLAIMS.md` CLM-001 / CLM-002 / CLM-007 / CLM-011.

| Paper quantity | Paper line | Framework function | Used by |
|---|---|---|---|
| `A_g` — sheet evidence (Proposition 3 / line 161): `(2π)^{-1/2} ∫_ℝ exp(−s²/2) / sqrt(1 + g(s)²) ds` | `NoiseSelectedRectification_EN.md:116-117`, `:161` | `sheet_evidence_A(g, *, K=8.0, h=0.01) -> float` (`adaptive_reflow/contracts/paper_quantities.py:71`) | `CodimensionSheetScheduler._paper_evidence_balance` (closed-form per-round `evidence_ratio`); `AdaptivePolicyDriver` per-cell scaling; `ReInferenceRunner` (consumes via `paper_quantities_provider`) |
| `B_g` — root-cell packing (Lemma 5 / line 159): `Σ_{z ∈ Z_g} exp(−z²/4) < ∞` | `NoiseSelectedRectification_EN.md:132`, `:159` | `root_cell_packing_B(g, *, separation_d=1.0, K=8.0, h=0.01) -> float` (`adaptive_reflow/contracts/paper_quantities.py:142`) | `CodimensionSheetScheduler._paper_evidence_balance` (denominator of the closed-form ratio); `AdaptivePolicyDriver` `paper_quantities_provider` |
| `C_g` — per-cell coefficient (Lemma 3 / line 191): `C_g = exp(ρ²/2) / a` where `a = (1−ρ)² · min{c², 1}` | `NoiseSelectedRectification_EN.md:107`, `:188`, `:191` | `per_cell_coefficient_C(*, rho=0.1, c=1.0) -> float` (`adaptive_reflow/contracts/paper_quantities.py:239`) | `CodimensionSheetScheduler` (per-cell evidence term in the closed form); `AdaptivePolicyDriver` (per-cell coefficient); `ReInferenceRunner` (β-saturation lookup) |
| `e_ρ` — exterior gap (Lemma 5 / line 128 / Lemma 4 / line 110-113): `e_ρ = min{ρ⁴, (1−ρ)² η²}` | `NoiseSelectedRectification_EN.md:110-113`, `:128` | `exterior_gap_e_rho(*, rho=0.1, eta=0.1) -> float` (`adaptive_reflow/contracts/paper_quantities.py:284`) | `BoundedMergeOperator` `floor` derivation (Lemma 4 exponential suppression); `CosineAnnealScheduler` `n_min > 0` (bounded-noise floor); `CodimensionSheetScheduler` `_paper_evidence_balance` `physical_complement` term |

## Per-quantity rich-result dataclasses (uplifts)

| Quantity | Rich dataclass | Extra fields | Used by |
|---|---|---|---|
| `A_g` | `SheetEvidenceResult` (`paper_quantities.py:331`) | `discretization_error`, `K`, `h`, `n_steps` | `EvidenceScaleGapMetric` calibration reports |
| `B_g` | `RootCellPackingResult` (`paper_quantities.py:350`) | `tail_bound`, `separation_d`, `K`, `h`, `n_steps` | `CodimensionSheetScheduler` tail-bound audit |
| `C_g` | `PerCellCoefficientResult` (`paper_quantities.py:369`) | `drift_robustness`, `rho`, `c` | `AdaptivePolicyDriver` perturbation-aware ceiling |

## Notes

* All four quantities are exposed as **first-class algorithm-layer inputs** via `adaptive_reflow.contracts.paper_quantities` (CLM-011).
* The plain float-returning functions (`sheet_evidence_A` etc.) are **byte-stable**: two calls with identical inputs return bit-identical floats (CLM-018 byte-stability guarantee, regression-pinned by `tests/test_contracts/test_paper_quantities.py`).
* The rich-result dataclasses are A17 / B13 / B14 uplifts; their `.value` field is bit-identical to the plain function return value.