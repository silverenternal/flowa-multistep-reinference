# Framework-internal metrics — baseline audit report

**Date:** 2026-09-05
**Purpose:** baseline measurements for framework-internal-metrics.md rev 2 §6
**Method:** 9 parallel audit sub-agents (each owns one metric); aggregated below

## Summary

(see per-section details below)

---

## A.0 — Paper-statement inventory

**Audit command:**

```bash
grep -RnE 'Theorem|Lemma|Proposition|Remark|Thm\.|Lem\.|Prop\.|Corollary|paper line|paper section' \
  /home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/theory/ \
  /home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/framework/
```

**Raw output:** 141 paper-reference hits across the inspected tree (paper_quantities.py=51, checkers.py=19, validation.py=11, f_side_validator.py=11, lemma2_checker.py=8, framework/interfaces.py=18, theory/__init__.py=23).

The table below enumerates every paper theorem / lemma / proposition / corollary / remark the codebase implements, plus paper statements that are referenced in docstrings/comments but lack a dedicated implementation module (gaps).

### A.0.1 — Paper statements implemented in code

| # | Statement | Paper section/line | Code module / class | Test file | Reference docstring/comment |
|---|-----------|-------------------|---------------------|-----------|------------------------------|
| 1 | Theorem 1 (3-claim unified statement) | line 87-92 | `adaptive_reflow.theory.checkers.Theorem1Statement` + `Theorem1StatementChecker`; re-exported via `adaptive_reflow.framework.interfaces.emit_theorem1_statement` | `tests/test_theory/test_theorem1_unified.py`, `tests/test_theory/test_theorem1_bl_convergence.py` | "Paper Theorem 1 (line 87-92) is a SINGLE statement that combines: (a) BL convergence... (b) root-cell mass... (c) bounded-Lipschitz equivalence display" |
| 2 | Theorem 1 claim (a) — BL convergence witness | line 87-89 | `adaptive_reflow.theory.checkers.theorem1_bl_convergence_witness`, `LipschitzConvergenceReport` | `tests/test_theory/test_theorem1_bl_convergence.py::test_theorem1_bl_convergence_witness_smoke` | "Compute ``BL(mu_{g,eps_k}, nu_g)`` for each ``eps_k``" — paper line 87-89 |
| 3 | Theorem 1 claim (b) — root-cell mass `O(eps)` | line 90 | `adaptive_reflow.theory.paper_quantities.paper_selection_ratio` (sheet_A*eps / (sheet_A*eps + cell_C*packing_B*eps^2)) | `tests/test_theory/test_paper_selection_ratio_eps_zero.py`, `tests/test_theory/test_theorem1_unified.py::test_emit_theorem1_statement_root_cell_mass_is_paper_formula` | "per-round sheet-dominance mass from Corollary 1, line 165" |
| 4 | Theorem 1 claim (c) — bounded-Lipschitz equivalence | line 91-92 | `adaptive_reflow.theory.checkers.theorem1_bl_convergence_witness` + `adaptive_reflow.framework.interfaces.PosteriorEvaluator.bl_distance_planar` (Protocol) | (covered transitively by Theorem 1 unified tests) | "the bounded-Lipschitz equivalence (line 91-92, the equivalent display for ``phi in BL``)" |
| 5 | Lemma 2 — sheet-tube rescaling | line 100-104 | `adaptive_reflow.theory.checkers.sheet_tube_evidence` (returns `SheetTubeEvidence` dataclass) AND `adaptive_reflow.theory.lemma2_checker.sheet_tube_evidence` (returns `float` LHS/RHS ratio) | `tests/test_theory/test_lemma2_sheet_tube_evidence.py` | "Paper Lemma 2 (line 100-104): ``eps^{-1} int_T phi p_eps -> (2*pi)^{-1/2} int_R phi(s,0) e^{-s^2/2} / sqrt(1+g(s)^2) ds``" |
| 6 | Lemma 4 — physical-complement suppression | line 110-113 | `adaptive_reflow.theory.paper_quantities.PhysicalComplement` + `PhysicalComplement.lemma4_floor_value()` | `tests/test_theory/test_physical_complement_lemma4_floor.py` | "Per Lemma 4 (line 110-113), the exterior posterior mass is bounded by ``exp(-e_rho / (2 eps^2)) = o(eps)``" |
| 7 | Lemma 3 — root-cell coefficient `C_g = e^{rho^2/2}/a` | Lemma 3 proof, line 188-191 | `adaptive_reflow.theory.paper_quantities.per_cell_coefficient_C` (rho, c -> `e^{rho^2/2} / ((1-rho)^2 * min(c^2, 1))`) | `tests/test_contracts/test_paper_quantities.py` (legacy) | "Lemma 3 states that ``int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2``" |
| 8 | Lemma 5 — uniform cells, Gaussian packing | line 132, line 135-138 | `adaptive_reflow.theory.paper_quantities.root_cell_packing_B` (line 159 quantity B_g) | `tests/test_contracts/test_paper_quantities.py` (legacy) | "Lemma 5 (line 132) derives the finiteness of ``B_g`` from uniform separation (``d``) and Gaussian decay" |
| 9 | Lemma 5 — exterior-gap bound `e_rho` | line 128 | `adaptive_reflow.theory.paper_quantities.exterior_gap_e_rho` (rho, eta -> `min(rho^4, (1-rho)^2 * eta^2)`) | `tests/test_contracts/test_paper_quantities.py` (legacy) | "``e_rho = min{rho^4, (1-rho)^2 eta^2} > 0``" |
| 10 | Lemma 5 — disjoint-cell constraint `rho < d/4` | line 135-138 | `adaptive_reflow.theory.validation.validate_f_side` (codes `rho_must_be_lt_d_over_4`, `cells_overlap`); ALSO `adaptive_reflow.theory.f_side_validator.validate_f_side` (sibling, paper-symbol-friendly codes) | `tests/test_theory/test_proposition6_escaping_sharpness.py`, `tests/test_theory/test_validate_f_side.py` | "Lemma 5 disjoint-cell constraint. When ``d <= 0`` the inequality ``d/4 <= 0`` forces ``rho < non-positive``" |
| 11 | Lemma 5 setup — cell-radius upper bound `rho <= 1/4` | Lemma 5 setup | `adaptive_reflow.theory.f_side_validator.validate_f_side` (code `rho_must_be_le_1_over_4`) | `tests/test_theory/test_validate_f_side.py::test_validate_f_side_fail_rho_gt_1_over_4` | "``rho <= 1/4`` is the cell-radius upper bound" |
| 12 | F-side hypothesis set — `(d, c, rho, eta)` | line 22-26 | `adaptive_reflow.theory.validation.validate_f_side`, `validate_g_admissible`, `NotInFsideClassError`; re-exported via `adaptive_reflow.theory.f_side_validator.validate_f_side` | `tests/test_theory/test_proposition6_escaping_sharpness.py`, `tests/test_theory/test_validate_f_side.py` | "The paper's Theorem 1 (line 87-92) is conditional on the F-side hypotheses (line 22-26)" |
| 13 | Proposition 2 — non-periodic family `g_a(x) = a(x) sin(x)` | line 62-64 | Used as canonical witness inside `tests/test_theory/test_lemma2_sheet_tube_evidence.py::_g_a`, `tests/test_theory/test_proposition6_escaping_sharpness.py::test_validate_g_admissible_accepts_canonical_nonperiodic_profile` | same | "``g_a(x) = (1 + 0.25*tanh(x)) * sin(x)`` with ``a(x) = 1 + 0.25*tanh(x)`` ... admissible (no periodicity)" |
| 14 | Proposition 3 — posterior assembly / `A_g` selection-mechanism display | line 116-117, 161 | `adaptive_reflow.theory.paper_quantities.sheet_evidence_A` (line 161 quantity A_g) | `tests/test_contracts/test_paper_quantities.py` (legacy) | "Return ``A_g`` from Proposition 3 / line 161" |
| 15 | Proposition 6 — escaping-sharpness counterexample | line 294-300 | `adaptive_reflow.theory.validation.validate_g_admissible` + `adaptive_reflow.theory.validation.NotInFsideClassError` (fail-closed); ALSO `adaptive_reflow.eval.fid_theorem_aligned.PaperQuantitiesSnapshot.for_profile(validate=True)` | `tests/test_theory/test_proposition6_escaping_sharpness.py::test_for_profile_rejects_proposition_6_sharpness_example` | "Paper Proposition 6 (line 294-300) presents H(x) = e^{-x^2/2} * sin(pi*x) as a sharpness example" |
| 16 | Corollary 1 — quantitative allocation `Z_{g,eps} >= C_1 eps` | line 165 | `adaptive_reflow.theory.paper_quantities.paper_selection_ratio` | `tests/test_theory/test_paper_selection_ratio_eps_zero.py::test_paper_selection_ratio_zero_eps_returns_one` | "Paper Corollary 1 (line 165) divides ``Z_{g,eps}`` ... deduces the per-round selection ratio at finite ``L``" |
| 17 | Remark 1 — periodicity-free Theorem 1 | line 54-56 | Documentation only; encoded as module docstring in `adaptive_reflow/theory/__init__.py`, `adaptive_reflow/theory/paper_quantities.py` | (no dedicated test) | "The main theorem does NOT require periodicity of ``g``; Lemma 1 is only a verification convenience" |
| 18 | `nu_g` reference density (paper formula line 82-83) | line 82-83 | `adaptive_reflow.framework.interfaces.PosteriorEvaluator.nu_g_density` (Protocol); also encoded inline in `adaptive_reflow.theory.checkers.theorem1_bl_convergence_witness` | (covered transitively by BL convergence tests) | "Return ``nu_g`` density at ``(s, t)`` (paper formula line 82-83)" |
| 19 | Selection-mechanism display (per Proposition 3) | line 161 (sheet scheduling) | `adaptive_reflow.framework.interfaces.SheetSchedulerProtocol.sheet_density`, `.inject_noise`; `adaptive_reflow.framework.interfaces.NoiseInjectionProtocol` | `tests/test_algorithm/test_scheduler.py::test_codimension_sheet_scheduler_with_profile_uses_paper_quantities`, `tests/test_algorithm/test_scheduler_algorithm_on_2d_oracle.py` | "Sheet sampling and noise injection scheduling per Proposition 3" |
| 20 | Selection-ratio witness `sheet_A*eps/(sheet_A*eps + cell_C*packing_B*eps^2)` | (derived in Corollary 1) | `adaptive_reflow.framework.interfaces.SelectionRatioWitness.paper_selection_ratio` (Protocol) | `tests/test_theory/test_paper_selection_ratio_eps_zero.py` | "Paper-grounded selection ratio witness" |

### A.0.2 — Gaps (paper statements referenced but NOT implemented as a dedicated module/class)

| # | Statement | Paper section | Where referenced | Why not implemented / gap |
|---|-----------|---------------|------------------|---------------------------|
| G1 | Lemma 1 (periodicity verification lemma) | line 54-56 (referenced) | `theory/__init__.py`, `theory/paper_quantities.py` | Mentioned only as a "verification convenience" in the Remark 1 docstring; no dedicated evaluator exists because Lemma 1 is a structural sanity result rather than a quantitative bound. |
| G2 | Lemma 4 explicit `exp(-e_rho/(2 eps^2))` posterior integral bound | line 110-113 | `theory/paper_quantities.py::exterior_gap_e_rho` docstring cites the formula but no function returns the integral value at finite eps | The bound is `o(eps)`; the codebase exposes `PhysicalComplement.lemma4_floor_value()` (the floor constant) but does NOT expose a numeric evaluator of the upper-bound integral. |
| G3 | Lemma 3 explicit integral `int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2` | Lemma 3 statement | `theory/paper_quantities.py::per_cell_coefficient_C` docstring describes the inequality but no function returns the LHS integral value at finite eps | Same reason as G2 — the bound is stated for documentation only. |
| G4 | Theorem 1 explicit rate constant `BL(mu_{g,eps}, nu_g) = O(some explicit eps power)` | line 87-92 (implicit) | `adaptive_reflow.framework.interfaces.emit_theorem1_statement` returns a numeric BL witness but no explicit `rate_constant` field | Tracked as pending Task #360: "Document explicit rate bound for Theorem 1 (algorithm layer)". |
| G5 | Proposition 1 (paper section before Prop 2; not explicitly numbered in codebase) | (line ~54-60 area) | Referenced only via Proposition 2 docstring cross-references | No dedicated module; not surfaced as an explicit statement. |
| G6 | Proposition 4 / Proposition 5 (intermediate sharpness results) | (paper body, between Prop 3 and Prop 6) | Not mentioned in any theory file | No implementation; appear unnecessary for the framework's quantitative needs (A_g, B_g, C_g, e_rho + selection ratio + disjoint-cell constraint are sufficient). |
| G7 | Proposition 6 — positive direction (Proposition 6 also presents a positive-direction admissible profile alongside H(x)) | line 294-300 | Only the fail-closed direction (H(x) rejection) is implemented | The positive direction is implicitly tested via `test_for_profile_accepts_canonical_nonperiodic_profile_when_validate` (Prop 2 family) but no Proposition-6-specific positive example is named. |

### A.0.3 — Cross-reference (test → implementation) coverage

Every paper statement listed in A.0.1 has at least one test:

- **Theorem 1** (statements 1-4, 18): `tests/test_theory/test_theorem1_unified.py` (6 tests) + `tests/test_theory/test_theorem1_bl_convergence.py` (7 tests).
- **Lemma 2** (statement 5): `tests/test_theory/test_lemma2_sheet_tube_evidence.py` (8 tests, both `checkers.sheet_tube_evidence` dataclass variant and `lemma2_checker.sheet_tube_evidence` float variant).
- **Lemma 4** (statement 6): `tests/test_theory/test_physical_complement_lemma4_floor.py` (8 tests).
- **Lemma 3, Lemma 5 quantities** (statements 7-9): legacy coverage via `tests/test_contracts/test_paper_quantities.py::test_no_torch` and Wave 11 protocol-conformance tests; no dedicated `tests/test_theory/test_paper_quantities.py` file, but the quantities are exercised in every higher-level test.
- **F-side hypotheses + Lemma 5 disjoint-cell** (statements 10-12): `tests/test_theory/test_proposition6_escaping_sharpness.py` (8 tests) + `tests/test_theory/test_validate_f_side.py` (6 tests).
- **Proposition 2 / Proposition 3** (statements 13-14): Proposition 2 via `test_lemma2_sheet_tube_evidence.py::_g_a` + `test_proposition6_escaping_sharpness.py::test_validate_g_admissible_accepts_canonical_nonperiodic_profile`; Proposition 3 (`A_g`) via legacy `tests/test_contracts/test_paper_quantities.py`.
- **Proposition 6** (statement 15): `tests/test_theory/test_proposition6_escaping_sharpness.py::test_for_profile_rejects_proposition_6_sharpness_example`.
- **Corollary 1** (statement 16): `tests/test_theory/test_paper_selection_ratio_eps_zero.py` (7 tests) + `tests/test_theory/test_theorem1_bl_convergence.py::test_paper_selection_ratio_canonical_formula`.
- **Remark 1** (statement 17): no dedicated test — pure documentation in three module docstrings.
- **Selection-mechanism display** (statement 19): `tests/test_algorithm/test_scheduler.py::test_codimension_sheet_scheduler_with_profile_uses_paper_quantities` + `tests/test_algorithm/test_scheduler_algorithm_on_2d_oracle.py::test_codimension_scheduler_caches_paper_quantities`.
- **Selection-ratio witness** (statement 20): covered under Corollary 1 tests.

### A.0.4 — Interpretation

- **Implementation coverage:** 16 distinct paper statements are explicitly implemented in code (statements 1-16, plus the supporting 17-20); 7 gaps identified, of which 4 (G1, G3, G5, G6) are paper lemmas/propositions the framework intentionally does not need to evaluate numerically, 2 (G2, G4) are quantitative rate constants with docstring references but no dedicated evaluator (one already tracked as Task #360), and 1 (G7) is the under-tested positive direction of Proposition 6.
- **Test parity:** Every implemented statement has at least one direct test except Remark 1 (pure docstring) and the `nu_g` density Protocol surface (transitively covered by BL-convergence tests).
- **Re-export surface:** The `framework/interfaces.py` Protocol surfaces (`SelectionRatioWitness`, `SheetSchedulerProtocol`, `NoiseInjectionProtocol`, `MergeOperatorProtocol`, `PosteriorEvaluator`, `Theorem1StatementChecker`) all carry paper-anchored docstrings; concrete implementations live in `algorithm/dynamic_noise_bias.py` and adapter modules (out of scope for this audit).

---

## A.4 — Per-equation citation density

**Audit commands:**

```bash
# Count docstrings containing explicit equation/section references
grep -RE 'Eq\.\s*\([0-9]+|Lemma\s+[0-9]+|Theorem\s+[0-9]+|Prop\.\s*[0-9]+|Section\s+[0-9]+|paper line' /home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/theory/ | wc -l

# Total public functions (heuristic: lines starting with 'def ')
grep -RE '^def [a-zA-Z_]+\(' /home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/theory/*.py | wc -l
```

**Raw counts:**

- Functions with paper reference (Eq./Lemma/Theorem/Prop./Section/paper line): **14**
- Total public functions (`^def [a-zA-Z_]+\(` over `adaptive_reflow/theory/*.py`): **82**
- Ratio: **14 / 82 ≈ 0.171 (17.07%)**

**Interpretation:**

Citation density in `adaptive_reflow/theory/` sits at roughly **17%** of public functions carrying an explicit paper reference (Eq./Lemma/Theorem/Prop./Section or a `paper line` note in the docstring). That is well short of the rev 2 target of **≥ 0.90 by Wave 14** — the gap is ~73 percentage points.

Inspection of the matches shows that paper references today are concentrated in two clusters:

1. `f_side_validator.py` / `lemma2_checker.py` / `checkers.py` — every witness function here names `Theorem 1`, `Lemma 2`, `Lemma 3`, or `Lemma 5` with the paper line range (e.g. `Theorem 1 (line 87-92)`, `Lemma 2 (line 100-104)`).
2. `paper_quantities.py` — quantity names (`A`, `B`, `C`, `e_rho`) implicitly correspond to paper sections but the docstrings do not currently cite `Section N` or `Eq. N` anchors; only one entry (`paper_selection_ratio`) makes the link explicit.

The remaining 68 functions in `validation.py`, `paper_quantities.py`, `__init__.py`, and helper modules (`_detect_zeros`, `sheet_evidence_with_result`, `root_cell_packing_with_result`, `per_cell_coefficient_with_result`, `validate_g_admissible`, etc.) have no in-docstring paper anchor — even when the function name mirrors a paper quantity. A small class of "with_result" wrappers is the easiest low-risk batch to annotate in Wave 14, because the underlying quantity is already named and the reference is one `Eq. N` away.

**Target gap:**

- Current: 0.171
- Rev 2 target: ≥ 0.900 (by Wave 14)
- Gap: **−0.729** (need ~+60 more annotated functions to reach the target assuming denominator stays ~82, or ~+72 if denominator grows to ~85).

**Concrete next actions to close the gap (Wave 14 plan):**

1. Annotate `paper_quantities.py` `_with_result` wrappers with the same `Eq. N`/`Section N` anchors used by their underlying quantity functions (4 functions, low risk).
2. Add paper anchors to `validation.py` helpers (`validate_g_admissible`, `_detect_zeros`) — the conditions they check correspond to specific Theorem/Lemma statements; cite them.
3. In `__init__.py`, lift the `Theorem 1 (line 87-92)` anchor from the module docstring into each public re-export docstring so the citation travels with the function.
4. Sweep `checkers.py` for any helper that emits a Theorem/Lemma check but currently lacks the paper-line reference in its docstring.
5. Re-run this audit after Wave 14 and confirm ratio ≥ 0.90; if denominator grows (new witnesses added), recompute on the new counts.

**Rev 2 target status:** NOT MET. 0.171 vs target 0.90 — far below; needs sustained citation-density work across the remaining waves.

---

## A.7 — Hypothesis-violation (must-fail) coverage

- **Metric ID:** A.7
- **Metric title:** Hypothesis-violation (must-fail) fixture coverage — paired fail-closed fixtures for paper statements
- **Audit command:**
  ```bash
  # (1) Does tests/test_theory/negative/ exist?
  ls /home/hugo/codes/flowa-multistep-reinference/tests/test_theory/negative/ 2>/dev/null | wc -l

  # (2) Fallback grep for must-fail test functions across the test_theory/ tree
  grep -RnE 'def test_[a-zA-Z_]*(violates|invalid|not_admissible|fails_|negation|reject)' \
    /home/hugo/codes/flowa-multistep-reinference/tests/test_theory/ 2>/dev/null | wc -l

  # (3) Same grep, repo-wide, to surface out-of-tree must-fail fixtures
  grep -RnE 'def test_[a-zA-Z_]*(violates|invalid|not_admissible|fails_|negation|reject)' \
    /home/hugo/codes/flowa-multistep-reinference/tests/ 2>/dev/null | wc -l

  # (4) Enumerate per-statement must-fail coverage
  grep -RnE 'def test_[a-zA-Z_]*(violates|invalid|not_admissible|fails_|negation|reject)' \
    /home/hugo/codes/flowa-multistep-reinference/tests/ 2>/dev/null
  ```
- **Raw output:**
  - (1) `tests/test_theory/negative/` → `0` files (directory **MISSING**: `ls: cannot access … No such file or directory`). The Wave 11 conformance suite uses 7 hand-authored files directly under `tests/test_theory/` rather than a `negative/` subdirectory.
  - (2) Must-fail test functions inside `tests/test_theory/` → **13** (count)
  - (3) Must-fail test functions repo-wide (`tests/`) → **27** (count). The extra 14 live under `tests/test_contracts/test_paper_quantities.py` (1 parametrised `test_paper_quantities_reject_invalid_params` covering 11 paper-quantity rejections: `sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C`, `exterior_gap_e_rho` × invalid params), `tests/test_algorithm/test_policy_driver.py` (`test_adaptive_policy_driver_rejects_invalid_per_cell_coefficient_C`, `test_protocol_surface.py:383` `AdaptivePolicyDriver(per_cell_coefficient_C=-1.0)`), plus framework fail-closed tests under `tests/test_adapters/`, `tests/test_round2_external_uplifts.py`, and `tests/property/test_fail_closed_invariants.py`.
  - (4) Per-file `tests/test_theory/` must-fail inventory (13 fixtures, the canonical paired-with-paper-statement set):
    ```
    tests/test_theory/test_paper_selection_ratio_eps_zero.py:66:def test_paper_selection_ratio_rejects_negative()
    tests/test_theory/test_paper_selection_ratio_eps_zero.py:73:def test_paper_selection_ratio_rejects_nan_inf()
    tests/test_theory/test_proposition6_escaping_sharpness.py:37:def test_validate_f_side_fails_for_cells_overlap()
    tests/test_theory/test_proposition6_escaping_sharpness.py:44:def test_validate_f_side_fails_for_negative_constants()
    tests/test_theory/test_proposition6_escaping_sharpness.py:58:def test_validate_f_side_fails_for_rho_out_of_range()
    tests/test_theory/test_proposition6_escaping_sharpness.py:73:def test_validate_g_admissible_rejects_proposition_6_sharpness_example()
    tests/test_theory/test_proposition6_escaping_sharpness.py:95:def test_validate_g_admissible_rejects_profile_with_no_zeros()
    tests/test_theory/test_proposition6_escaping_sharpness.py:114:def test_for_profile_rejects_proposition_6_sharpness_example()
    tests/test_theory/test_proposition6_escaping_sharpness.py:136:def test_for_profile_rejects_empty_zero_set_when_validate()
    tests/test_theory/test_theorem1_bl_convergence.py:94:def test_paper_selection_ratio_rejects_invalid_inputs()
    tests/test_theory/test_lemma2_sheet_tube_evidence.py:54:def test_sheet_tube_evidence_rejects_zero_eps()
    tests/test_theory/test_lemma2_sheet_tube_evidence.py:94:def test_ratio_witness_rejects_non_positive_eps()
    tests/test_theory/test_physical_complement_lemma4_floor.py:66:def test_physical_complement_rejects_invalid_inputs()
    ```
- **Locally-derived A.0 paper-statement inventory (sibling A.0 agent ran in parallel; cross-reference rebuilt from `grep -RnE 'Theorem|Lemma|Proposition|Remark|Corollary' adaptive_reflow/theory/`):**

  | # | Statement | Paper line | Code module / entry | Constructive? | Must-fail fixture (test_theory/) | Paired? |
  |---|---|---|---|---|---|---|
  | 1 | Theorem 1 | 87-92 | `theory/checkers.py:Theorem1Statement` / `theorem1_bl_convergence_witness`; `paper_quantities.py:paper_selection_ratio` | YES (dataclass + ratio) | `test_paper_selection_ratio_rejects_invalid_inputs` (theorem1_bl_convergence.py:94), `test_paper_selection_ratio_rejects_negative`, `test_paper_selection_ratio_rejects_nan_inf` | YES |
  | 2 | Lemma 1 (periodicity removed) | n/a (referenced via Remark 1) | `theory/__init__.py:8-10` (docstring only) | NO (qualitative note, no witness) | — | N/A (non-constructive) |
  | 3 | Lemma 2 | 100-104 | `theory/lemma2_checker.py` (Wave 12 A1-high-2) + `checkers.py:sheet_tube_evidence` | YES (LHS/RHS ratio witness) | `test_sheet_tube_evidence_rejects_zero_eps` (lemma2_sheet_tube_evidence.py:54), `test_ratio_witness_rejects_non_positive_eps` (lemma2_sheet_tube_evidence.py:94) | YES |
  | 4 | Lemma 3 | 107 (per-cell coefficient `C_g`) | `theory/paper_quantities.py:per_cell_coefficient_C` (line 226), wired into `AdaptivePolicyDriver.per_cell_coefficient_C` | YES (returns `C_g`) | NONE in `tests/test_theory/`; covered repo-wide by `tests/test_contracts/test_paper_quantities.py:293-317` parametrised `test_paper_quantities_reject_invalid_params` for `(rho=0.0, rho=1.0, c=0.0)` and by `test_algorithm/test_policy_driver.py:528 test_adaptive_policy_driver_rejects_invalid_per_cell_coefficient_C` | PARTIAL (test_theory-only gap; repo-wide covered) |
  | 5 | Lemma 4 | 117-122 (exterior gap `e_rho` floor) | `theory/paper_quantities.py:PhysicalComplement.lemma4_floor_value` | YES (floor pass-through) | `test_physical_complement_rejects_invalid_inputs` (physical_complement_lemma4_floor.py:66), `test_physical_complement_validates_f_side_invariants` (theorem1_bl_convergence.py:120) | YES |
  | 6 | Lemma 5 | 135-138 (disjoint-cell constraint `rho < d/4`) | `theory/validation.py:validate_f_side`, `theory/f_side_validator.py` | YES (returns `(False, "cells_overlap", …)`) | `test_validate_f_side_fails_for_cells_overlap`, `test_validate_f_side_fails_for_negative_constants`, `test_validate_f_side_fails_for_rho_out_of_range` (all in proposition6_escaping_sharpness.py:37/44/58) | YES |
  | 7 | Corollary 1 | 165 (quantitative allocation `Z_{g,eps} >= C_1 * eps`) | `theory/paper_quantities.py:paper_selection_ratio` (lines 36, 88, 113, 186, 288, 341, 647) | YES (ratio formula) | Same fixtures as Theorem 1 (`test_paper_selection_ratio_rejects_*`) | YES (shared with Thm 1) |
  | 8 | Proposition 2 | 62-64 (`g_a(x) = a(x) * sin(x)` admissible family) | `theory/__init__.py:13`, `theory/paper_quantities.py:10` (canonical witness only — used as positive fixture) | YES (witness construction; NOT a hypothesis to violate) | NONE — by design Prop 2 is the *admissible* witness; its must-fail counterpart is Prop 6 (sharpness, which IS paired). Per the constructive/non-qualitative reading, Prop 2 has only positive tests (`test_validate_g_admissible_accepts_canonical_nonperiodic_profile`, `test_for_profile_accepts_canonical_nonperiodic_profile_when_validate`, `test_ratio_witness_converges_to_one_for_proposition_two_profile`). | PARTIAL (covered-by-symmetry via Prop 6) |
  | 9 | Proposition 6 | 294-300 (`H(x) = e^{-x^2/2} sin(pi*x)` sharpness) | `theory/validation.py:validate_g_admissible`, `eval.fid_theorem_aligned.PaperQuantitiesSnapshot.for_profile` | YES (validator raises `NotInFsideClassError`) | 4 fixtures: `test_validate_g_admissible_rejects_proposition_6_sharpness_example` (proposition6_escaping_sharpness.py:73), `test_validate_g_admissible_rejects_profile_with_no_zeros` (:95), `test_for_profile_rejects_proposition_6_sharpness_example` (:114), `test_for_profile_rejects_empty_zero_set_when_validate` (:136) | YES (best-covered of all constructive entries) |
  | 10 | Remark 1 | 54-56 (periodicity not required) | `theory/__init__.py:8` (docstring) | NO (qualitative meta-statement) | — | N/A (non-constructive) |

- **Constructive entries:** 8 (rows 1, 3, 4, 5, 6, 7, 8, 9 above).
- **Current value (strict, `tests/test_theory/` only):** **6 / 8 = 75.0 %** of constructive entries have at least one paired must-fail fixture (Theorem 1, Lemma 2, Lemma 4, Lemma 5, Corollary 1, Proposition 6). The two gaps under the strict reading are:
  - **Lemma 3** (`per_cell_coefficient_C`): no must-fail test inside `tests/test_theory/`. The function IS exercised repo-wide via `tests/test_contracts/test_paper_quantities.py:293-317` parametrised `test_paper_quantities_reject_invalid_params` and `tests/test_algorithm/test_policy_driver.py:528 test_adaptive_policy_driver_rejects_invalid_per_cell_coefficient_C`, but neither lives under `tests/test_theory/` (which is the Wave 11 conformance suite root and where the audit task explicitly searches).
  - **Proposition 2**: by design has no must-fail — Prop 2 is the positive admissible witness family, and its fail-closed counterpart (Prop 6 sharpness) is fully covered with 4 paired must-fail fixtures. If the audit definition treats Prop 2's `validate_g_admissible` acceptance as the symmetric counterpart to Prop 6's rejection, then Prop 2 is covered-by-symmetry; if the definition requires an explicit reject path, Prop 2 has none.
- **Current value (broad, all of `tests/`):** **7 / 8 = 87.5 %** of constructive entries have at least one paired must-fail fixture. Only Proposition 2 remains uncovered under the strict "must-fail" reading.
- **Rev 2 target:** 100 % of A.0 *constructive* entries by Wave 16. Constructive = non-existence, non-qualitative theorems.
- **Interpretation:** The Wave 11 + Wave 12 conformance suite ships 13 hypothesis-violation fixtures under `tests/test_theory/`, all concentrated in 4 of the 7 test files (`test_paper_selection_ratio_eps_zero.py`, `test_proposition6_escaping_sharpness.py`, `test_theorem1_bl_convergence.py`, `test_lemma2_sheet_tube_evidence.py`, `test_physical_complement_lemma4_floor.py`). The heaviest coverage is on Proposition 6 (4 fixtures, covering the `validate_g_admissible`, `for_profile`, `Z_g` empty-set, and the explicit sharpness example paths). Lemma 5 is also well-covered (3 fixtures across `validate_f_side`'s three failure modes: `cells_overlap`, `negative_constants`, `rho_out_of_range`). Lemma 4 / `PhysicalComplement` is covered by 2 fixtures. Theorem 1 + Corollary 1 share 3 fixtures (`test_paper_selection_ratio_rejects_*`). Lemma 2 is covered by 2 fixtures (one per checker entry-point — `checkers.sheet_tube_evidence` and `lemma2_checker.sheet_tube_evidence`). The two gaps: (a) Lemma 3's `per_cell_coefficient_C` is the only constructive entry whose must-fail lives OUTSIDE `tests/test_theory/` — moving/copying the existing `test_paper_quantities_reject_invalid_params` parametrisation into `tests/test_theory/test_lemma3_per_cell_coefficient.py` (or adding a sibling) closes this gap with zero new test logic; (b) Proposition 2 is the positive admissible family and arguably does not require a must-fail by construction (its falsifier is Prop 6, fully paired). The Wave 11 / Wave 12 convention also omits `tests/test_theory/negative/` as a dedicated subdirectory — instead, must-fail fixtures live alongside positive fixtures in the same file, e.g. `test_proposition6_escaping_sharpness.py` contains both the positive `test_validate_g_admissible_accepts_canonical_nonperiodic_profile` and the must-fail `test_validate_g_admissible_rejects_proposition_6_sharpness_example`. This convention is documented in `docs/adr/0005-fail-closed-audit-code-policy.md` ("fail-closed by design").
- **Target gap (strict reading, tests/test_theory/):** Δ = 100 % - 75 % = **25 percentage points**. Need **+2 constructive entries with paired must-fail fixtures**: (1) Lemma 3 (closeable by promoting 1 existing parametrised test into `tests/test_theory/`, ~10 LOC), (2) Proposition 2 if the audit insists on a must-fail (closeable by adding e.g. `test_g_a_with_negative_a_function_fails_admissibility_check` since `a(x) < 0` violates the boundedness-from-below hypothesis — or accept Prop 2 as covered-by-symmetry via Prop 6).
- **Target gap (broad reading, all of tests/):** Δ = 100 % - 87.5 % = **12.5 percentage points**. Need **+1 entry**, namely Proposition 2 (or accept it as covered-by-symmetry).
- **Concrete next actions (in priority order):**
  1. **Promote Lemma 3 must-fail into `tests/test_theory/`.** Add `tests/test_theory/test_lemma3_per_cell_coefficient.py` containing a port of the `test_paper_quantities_reject_invalid_params` parametrisation restricted to `per_cell_coefficient_C` (cases: `rho=0.0`, `rho=1.0`, `c=0.0`). Estimated effort: ~10 LOC + 1 import. Closes 1 of 2 strict-reading gaps with no new test logic.
  2. **Optionally author a Prop 2 must-fail (or formally document the Prop-2 / Prop-6 symmetry).** Two routes: (a) add `test_g_a_with_unbounded_a_fails_admissibility` to `test_proposition6_escaping_sharpness.py` — takes the canonical `g_a(x) = (1 + 0.25 * tanh(x)) * sin(x)` family and perturbs `a(x)` so it violates the bounded-from-below hypothesis (e.g. `a(x) = -1 + 0.5 * sin(x)` which crosses zero); expects `NotInFsideClassError`. (b) Document in `docs/baseline-audit-report.md` (or `docs/adr/0005-fail-closed-audit-code-policy.md`) that Prop 2's paired must-fail IS Prop 6's sharpness rejection, i.e. the two propositions are by-design paired (admissible witness vs sharpness example), so Prop 2 does not require a separate must-fail.
  3. **(Optional) Create `tests/test_theory/negative/` as the canonical must-fail directory.** The current Wave 11/12 convention co-locates positive and must-fail tests in the same file, which works but does not match the directory structure implied by the audit task. A future cleanup could split the 13 must-fail fixtures into `tests/test_theory/negative/` (e.g. `test_proposition6_negative.py`, `test_selection_ratio_negative.py`, `test_lemma2_negative.py`, `test_lemma4_negative.py`, `test_lemma5_negative.py`) — cosmetic but would make the A.7 audit's `ls … /wc -l` first command non-zero and ease future scans. Estimated effort: 5 file moves + import-path updates in `conftest.py`.
  4. **No regression risk** on any of the above — every fixture is being *added* or *moved*, none replaced. All 13 existing must-fail fixtures continue to pass (verified by the Wave 12 A1-phase1-acceptance step).

---

## B.4 — Doctest execution

**Audit date:** 2026-09-05
**Command:** `.venvs/flowmol3_venv/bin/python -m pytest --doctest-modules adaptive_reflow/theory/ -q`

| Metric | Value |
| --- | --- |
| Exit code | **5** (`EXIT_NOTESTSCOLLECTED`) |
| Doctests collected | **0** |
| Failures | **0** |
| Collection errors | 0 |
| Wall clock | 0.03 s |

Raw output (complete):

```
no tests ran in 0.03s
```

There are no failure messages to report: nothing was collected, so nothing could fail.

### Why exit 5, not a failure

Exit 5 is pytest's "no tests were collected" code, not an error code. It is **not** caused by
import breakage — every module in the package imports cleanly under the same interpreter:

```
OK adaptive_reflow.theory.checkers
OK adaptive_reflow.theory.f_side_validator
OK adaptive_reflow.theory.lemma2_checker
OK adaptive_reflow.theory.paper_quantities
OK adaptive_reflow.theory.validation
OK adaptive_reflow.theory
```

The cause is simply that the package contains no doctest examples. `grep -c '>>>'` over every
module in `adaptive_reflow/theory/`:

| Module | `>>>` occurrences |
| --- | --- |
| `__init__.py` | 0 |
| `checkers.py` | 0 |
| `f_side_validator.py` | 0 |
| `lemma2_checker.py` | 0 |
| `paper_quantities.py` | 0 |
| `validation.py` | 0 |

### Repo-wide context

- Only **two** files in the entire `adaptive_reflow/` tree carry doctests:
  `adaptive_reflow/framework/interfaces.py` and `adaptive_reflow/writer/authority.py`.
  Running `--doctest-modules` against those two yields `2 passed`, exit code 0. So the doctest
  machinery itself is healthy — the theory package has simply never had examples written.
- **Doctests are not executed in CI at all.** `grep -rn 'doctest' .github/` returns 0 hits
  across all 10 workflows (`ci.yml`, `cpu-tests.yml`, `gpu-tests.yml`, `docs-validate.yml`,
  `bench-regression.yml`, `mutation-nightly.yml`, `experiments-nightly.yml`,
  `smoke-twodim.yml`, `docs-deploy.yml`, `gpu-experiment.yml`). `pyproject.toml`'s
  `[tool.pytest.ini_options] addopts` is `["-ra", "--strict-markers"]` — no `--doctest-modules`.
  Even the two passing doctests above are therefore only exercised when someone opts in manually.
- Docstring coverage in `adaptive_reflow/theory/` is high — **26 of 27** public
  functions/classes already have a docstring — so adding doctests is a matter of inserting
  worked examples into prose that already exists, not writing documentation from scratch.

| Module | public defs | with docstring |
| --- | --- | --- |
| `checkers.py` | 9 | 8 |
| `paper_quantities.py` | 13 | 13 |
| `validation.py` | 3 | 3 |
| `f_side_validator.py` | 1 | 1 |
| `lemma2_checker.py` | 1 | 1 |
| **Total** | **27** | **26** |

### Verdict against the rev 2 target

Rev 2 target is *0 doctest failures by Wave 13*. Measured failures are 0, so the target is met
**vacuously**: the count is zero because the denominator is zero, not because executable examples
were validated. As a signal of theory-layer documentation health this metric currently carries no
information.

### Gap to a meaningful pass

1. Add doctests to the highest-value public entry points in `adaptive_reflow/theory/` — start with
   `paper_quantities.py` (13/13 documented) and `checkers.py` (8/9 documented), which are the
   paper-facing surfaces most likely to drift from their prose.
2. Add `--doctest-modules adaptive_reflow/theory/` as an explicit step in `.github/workflows/cpu-tests.yml`
   (or add `--doctest-modules` to `addopts` in `pyproject.toml` and scope with `testpaths`), so that a
   collected count of 0 fails loudly instead of exiting 5 silently.
3. Treat exit code 5 as a failure in the CI step until doctests exist — otherwise a regression that
   deletes all examples looks identical to a green run.

---

## D.3 — Adapter conformance pass rate

- **Metric ID:** D.3
- **Metric title:** Adapter conformance pass rate — per-adapter `(passed) / (passed + failed + errored)` aggregated across `tests/test_adapters/`. Adapter = any of the 14 entries in `ADAPTER_REGISTRY` (14 = `flowmol3`, `flowmol3_v2`, `graphbfn`, `hidream_i1`, `lineageflow`, `lumina_image_2_0`, `mnist_fm`, `protbfn_abbfn`, `rectified_flow_cifar`, `self_flow`, `toy_gaussian`, `toy_linear`, `twodim_fm`, `wan2_2_video`). The rev 2 target `18/18` references the to-be-built D.5 auto-battery (currently MISSING; see D.5 section above); today's baseline measures hand-written per-adapter tests only (13 adapter-specific test files; 2 registered adapters (`flowmol3`, `toy_gaussian`) have no dedicated test file in `tests/test_adapters/` — see Target gap below).
- **Audit command:**
  ```bash
  cd /home/hugo/codes/flowa-multistep-reinference
  .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/ -v --tb=no 2>&1 | tail -100
  ```
- **Raw output (per-adapter test files, pass/fail/error counts; SKIP and XFAIL tracked separately):**

  | Adapter test file | Passed | Failed | Errored | Skipped | XFailed | Pass rate |
  |---|---|---|---|---|---|---|
  | `test_flowmol3_v2_adapter.py` | 13 | 0 | 0 | 0 | 0 | 13/13 = 100.0% |
  | `test_graphbfn.py` | 15 | 0 | 0 | 0 | 0 | 15/15 = 100.0% |
  | `test_hidream_i1.py` | 22 | 0 | 0 | 0 | 0 | 22/22 = 100.0% |
  | `test_lineageflow.py` | 22 | 0 | 0 | 0 | 0 | 22/22 = 100.0% |
  | `test_lumina_image_2_0.py` | 18 | 0 | 0 | 0 | 0 | 18/18 = 100.0% |
  | `test_mnist_fm.py` | 20 | 0 | 0 | 0 | 0 | 20/20 = 100.0% |
  | `test_mnist_fm_train.py` | 3 | 0 | 0 | 0 | 0 | 3/3 = 100.0% |
  | `test_protbfn_abbfn_adapter.py` | 15 | 0 | 0 | 0 | 0 | 15/15 = 100.0% |
  | `test_rectified_flow_cifar.py` | 26 | 0 | 0 | 0 | 0 | 26/26 = 100.0% |
  | `test_self_flow.py` | 22 | 0 | 0 | 0 | 0 | 22/22 = 100.0% |
  | `test_toy_linear.py` | 15 | 0 | 0 | 0 | 0 | 15/15 = 100.0% |
  | `test_twodim_fm.py` | 17 | 0 | 0 | 0 | 0 | 17/17 = 100.0% |
  | `test_wan2_2_video.py` | 18 | 0 | 0 | 0 | 0 | 18/18 = 100.0% |
  | **Per-adapter subtotal (13 files, 226 tests)** | **226** | **0** | **0** | **0** | **0** | **226/226 = 100.0%** |

  Cross-cutting test files (informational; not counted toward per-adapter pass rate):
  | Cross-cutting file | Passed | Failed | Errored | Skipped | XFailed |
  |---|---|---|---|---|---|
  | `test_adapter_common.py` | 9 | 0 | 0 | 0 | 0 |
  | `test_adapter_registry.py` | 5 | 0 | 0 | 0 | 0 |
  | `test_external_uplifts.py` | 45 | 0 | 0 | 0 | 0 |
  | `test_inject_forward_noise.py` | 12 | 0 | 0 | 2 | 0 |
  | `test_exp2_stochastic_fm_repro.py` | 3 | 0 | 0 | 0 | 1 |
  | **Cross-cutting subtotal** | **74** | **0** | **0** | **2** | **1** |

  Overall pytest summary: `300 passed, 2 skipped, 1 xfailed, 3 warnings in 87.39s (0:01:27)`. Wall-clock is for the full `tests/test_adapters/` directory; the per-adapter subtotal above covers only adapter-specific files (226/226 = 100%).

- **Current value:** **226/226 = 100.0%** pass rate across 13 adapter-specific test files (the 13 are all adapter-named test files in `tests/test_adapters/`). Zero FAIL and zero ERROR in any adapter test file. Cross-cutting tests: 74 passed, 2 skipped (capability-guard rejects; intentional skips for `SyntheticUnsupportedAdapter` and `StochasticFMAdapter` inject_forward_noise paths — they are NOT failures, they are documented skip conditions in the test source), 1 xfailed (the EXP-2 stochastic-FM W2 ratio reproduction test, deliberately `@pytest.mark.xfail(reason="...claim REFUTED on current setup...")`).

- **Adapters with FAIL or ERROR:** None. Zero FAIL or ERROR detected in this audit run — including the pre-existing 21 torch failures + 2 rdkit failures that were called out in the wave12 result validation are absent from the current pytest output. This means either (a) those environmental failures are now resolved/fixed in the current branch, or (b) the previously-failing tests live outside `tests/test_adapters/` (the audit scope is restricted to `tests/test_adapters/` only). The current `tests/test_adapters/` collection has zero FAIL/ERROR on this commit.

- **Rev 2 target:** 18/18 against D.5 auto-battery by Wave 14. D.5 auto-battery (`tests/test_adapters/conformance_battery.py`) does NOT exist yet (baseline 0% — see D.5 section above). Today's per-adapter pass rate against hand-written tests is 13/13 = 100% (13 adapter-named test files vs 14 registered adapters; see Target gap).

- **Interpretation:** Today every per-adapter test file in `tests/test_adapters/` runs to a green pass. The 13 per-adapter test files collectively cover 226 distinct conformance assertions (capabilities handshake, protocol satisfaction, build_initial_state, solve_ode, endpoint round-trip, determinism, restart-blend memory fraction, inject_forward_noise hook, etc.). No FAIL/ERROR is produced by any of these tests on the current commit. The 2 SKIPPED tests in `test_inject_forward_noise.py` and the 1 XFAIL test in `test_exp2_stochastic_fm_repro.py` are documented capability-guard-rejection / claim-refutation outcomes, not regressions: they are stable known-states of the test suite and do not indicate a defect in adapter conformance.

- **Target gap:** 13/13 today (hand-written) vs. 18/18 target (D.5 auto-battery). Concrete next actions toward rev 2 target: (1) add hand-written tests for the 2 registered adapters currently lacking one — `flowmol3` (registry key) and `toy_gaussian` (registry key) — bringing the hand-written coverage to 15/15; (2) author `tests/test_adapters/conformance_battery.py` (D.5) — a single auto-generated/spec-derived battery file that exercises the cross-adapter contract for all 14 (or 18, including future adapters) registered adapters; (3) ensure D.5 collects 18 distinct conformance assertions (one per registered adapter + 4 cross-cutting contract checks); (4) gate CI on `pytest tests/test_adapters/conformance_battery.py` returning 100% pass. Until D.5 exists, this section's pass rate is reported against the hand-written 13-adapter baseline, which is already at 100%.

---

## D.5 — Conformance battery existence

- **Metric ID:** D.5
- **Metric title:** Conformance battery existence
- **Audit command:**
  ```bash
  test -f /home/hugo/codes/flowa-multistep-reinference/tests/test_adapters/conformance_battery.py \
    && echo "EXISTS" || echo "MISSING"
  ls /home/hugo/codes/flowa-multistep-reinference/tests/test_adapters/ | head -50
  ```
- **Raw output:**
  - File existence check: `MISSING`
  - `tests/test_adapters/` directory contents (top 50):
    ```
    conftest.py
    __pycache__
    test_adapter_common.py
    test_adapter_registry.py
    test_exp2_stochastic_fm_repro.py
    test_external_uplifts.py
    test_flowmol3_v2_adapter.py
    test_graphbfn.py
    test_hidream_i1.py
    test_inject_forward_noise.py
    test_lineageflow.py
    test_lumina_image_2_0.py
    test_mnist_fm.py
    test_mnist_fm_train.py
    test_protbfn_abbfn_adapter.py
    test_rectified_flow_cifar.py
    test_self_flow.py
    test_toy_linear.py
    test_twodim_fm.py
    test_wan2_2_video.py
    ```
- **Current value:** MISSING — `tests/test_adapters/conformance_battery.py` is not present on disk.
- **Rev 2 target:** D.5 battery live by Wave 14.
- **Interpretation:** The auto-generated conformance battery (D.5) has not been authored yet. The `tests/test_adapters/` directory contains 20 hand-written adapter/unit tests covering individual adapters (`test_flowmol3_v2_adapter.py`, `test_lineageflow.py`, `test_self_flow.py`, `test_protbfn_abbfn_adapter.py`, `test_graphbfn.py`, `test_hidream_i1.py`, `test_lumina_image_2_0.py`, `test_wan2_2_video.py`), cross-cutting behavior (`test_adapter_common.py`, `test_adapter_registry.py`, `test_inject_forward_noise.py`, `test_external_uplifts.py`, `test_mnist_fm.py`, `test_mnist_fm_train.py`, `test_rectified_flow_cifar.py`, `test_twodim_fm.py`, `test_toy_linear.py`), and one repro (`test_exp2_stochastic_fm_repro.py`), plus `conftest.py` — but no single `conformance_battery.py` aggregating cross-adapter contract checks. The absence is consistent with "MISSING" as the expected pre-Wave-14 baseline state.
- **Target gap:** 1 file missing. Next action: author `tests/test_adapters/conformance_battery.py` as the auto-generated (or generated-from-spec) battery that exercises the adapter contract end-to-end against the registered adapters, and wire it into pytest collection (it will be picked up automatically once present, since `tests/test_adapters/` is a collected test root).

---

## E.2 — Documentation cross-reference rate

- **Audit command:**
  ```bash
  grep -lE 'Theorem\s+[0-9]+|Lemma\s+[0-9]+|Proposition\s+[0-9]+|paper line|paper section' \
    /home/hugo/codes/flowa-multistep-reinference/docs/*.md 2>/dev/null | wc -l
  find /home/hugo/codes/flowa-multistep-reinference/docs/ -maxdepth 1 -name '*.md' | wc -l
  ```
- **Raw output:**
  - Docs with paper theorem/lemma/proposition refs (count): `16`
  - Total top-level docs/*.md files (count): `28`
  - Ratio: `16 / 28 = 0.5714` (≈ 57.1%)
- **Current value:** 0.571 (16 / 28)
- **Rev 2 target:** ≥ 0.9 by Wave 14
- **Interpretation:** Cross-reference rate is currently 57.1%, well below the 0.9 target. Of 28 top-level docs, 16 mention at least one of `Theorem N`, `Lemma N`, `Proposition N`, `paper line`, or `paper section`; 12 do not. Non-referencing files include operational/policy docs (e.g. `RELEASING.md`, `TESTING_STRATEGY.md`, `PERFORMANCE_BUDGETS.md`, `DEPRECATION.md`, `ABLATION_METRIC_PROBE.md`, `distinguishing-from-reflow.md`, `lean_issue_re_inference_provenance.md`, `sequential-protocol.md`, `STRATEGY_FRAMEWORK_SCOPE.md`, `reproducibility_record.md`, `CONSOLIDATED_RESULTS.md`, `environments.md`) — most of which are process/log documents without theorem-bearing content, so a strict 0.9 across all 28 may be unobtainable without broadening the cross-reference definition (e.g. accepting equation references, figure references, or table references).
- **Target gap:** Δ = 0.9 - 0.571 = **0.329** (need +9 to +10 additional files referencing a paper theorem/lemma/proposition or `paper section` line, depending on whether borderline operational docs are in scope). Next action: (a) add at least one `Theorem N` / `Lemma N` / `Proposition N` or `paper section X.Y` anchor to each of the remaining 12 top-level docs where it is semantically relevant, and (b) re-evaluate with a broadened regex that also matches equation refs if 0.9 cannot be reached with the current strict pattern.

---

## F.2 — Wave 6 head experiments (3-way classification)

- **Metric ID:** F.2
- **Metric title:** Wave 6 head-experiments 3-way classification (REPRODUCED / PARTIAL / NOT_REPRODUCED)
- **Audit basis:** `docs/reproducibility_record.md` (commit `27dcb9cb`, 2026-09-04T15:02:53Z, GPU 0 = RTX PRO 6000 / 97887 MiB, GPU 1 = RTX 5090 / 32607 MiB *unused* per user directive; torch 2.7.0+cu128 / cuda 12.8 / cudnn 90701 / Python 3.12.13; **no env_hash captured in the run-record** — env_hash field below is left as `null`).
- **Headline experiments (8):** R1 algorithm uplifts, R2 2D ablation, R3 2D RF SOTA, R4 FlowMol3 paper-parity, R5 FlowMol3 framework-vs-baseline, R6 CIFAR-10 v4 matched-NFE, R7 byte-stability, R8 acyclic test-gate. Each was executed end-to-end on commit `27dcb9cb` with logs under `/tmp/repro_wave6/<task_id>/log.txt`.

| # | Experiment | Status | Last measured value | Where run | env_hash |
|---|---|---|---|---|---|
| R1 | algorithm-uplifts (`tools/benchmark_uplifts.py`) | **REPRODUCED** | 36 uplifts measured; 35 achieved target; 1 did not (A11 `AdaptivePolicyDriver.beta_saturation_count`, current=0 / achieved=no vs prior current=20 / achieved=yes); 0 regressions; 1 neutral; 23 ablation rows. Qualitative claim "35/36 yes, no regressions" reproduces; only 1 of 27 originally-recorded rows diverged. | CPU (0 GiB GPU) | null |
| R2 | 2D ablation (`tools/run_ablation.py`) | **PARTIAL** | 23/23 cells, exit 0; determinism CONFIRMED (3 independent invocations byte-identical). two_moons final W2: cosine 0.7272 < sigmoid 0.7535 < polynomial 0.8191 < convergence-adaptive 1.1093; eight_gaussians: convergence-adaptive 1.1488 < polynomial 1.2707 < cosine 1.2708 < sigmoid 1.3652; CLM-022 (A16) no-schedule 0.8343 → eps_schedule 0.9912 (+0.1569 abs, direction matches, magnitude diverges from prior claim). Runs reproduce byte-identical, but all 8 numeric figures in `docs/ABLATION.md` diverged from current HEAD output (qualitative ordering "no schedule family dominates both targets" survives). | CPU (0.002 GiB) | null |
| R3 | 2D RF SOTA (`tools/run_sota_2d_experiment.py --n-seeds 3`) | **NOT_REPRODUCED** | 14/30 runs completed (1800 s cap). two_moons baseline W2 = 0.0709±0.0070 (3-seed mean); framework best = 0.0800 (FreeTraj, 2 seeds) or 0.0805 (EvidenceDriven, 3 seeds); expected baseline=0.5029, expected framework best=0.4663. **Framework WORSE than baseline (0.08 vs 0.07)**, opposite to the claimed ~7% improvement direction. eight_gaussians NOT attempted. | CPU (0 GiB GPU) | null |
| R4 | FlowMol3 paper-parity (`/tmp/baseline_paper_flowmol3_nfe250.py`) | **REPRODUCED** | Phase B N=1000: frac_valid_mols=1.000, reos_cum_dev=0.42620895805461156 (matches recorded 0.4262 bit-exactly), fix_a_fg_reos_cum_dev=1.033875175315568 (matches 1.0339 bit-exactly), upstream_flag_rate=0.569, upstream_ood_rate=0.026, upstream_avg_num_components=8.92. Phase B wall-clock 480 s vs recorded 553 s (within sampling noise). | GPU 0 (8.18 GiB / 97887 MiB) | null |
| R5 | FlowMol3 framework-vs-baseline (`tools/run_sota_flowmol3_v2_adapter_experiment.py --n-mols 64 --n-rounds 3`) | **NOT_REPRODUCED** | framework_improved_on_sota = FALSE. n_valid=0/64 in both arms → baseline validity=0.0, framework validity=0.0, paired_delta validity=+0.0; qed/sa/logp/fcd/frac_atoms_stable/frac_mols_stable_valence/frac_connected/avg_num_components/pb_validity/fg_deviation/fg_deviation_eq4 all NaN in both arms. 0/5 paper-anchored metrics improved. Control at exact §1.1.d config (n=16, n_rounds=2, seed=0, device=cpu) also returned n_valid=0/16 vs documented baseline=0.1250 / framework=0.1875 — the §1.1.d table itself does not survive re-running on the native venv (the doc was produced via the Python 3.11 sidecar at `/home/hugo/.venv-flowmol311`, dgl 2.1.0 + torch 2.2.1+cpu, which is not installed in this sandbox). | GPU 0 (5.70 GiB / 97887 MiB) | null |
| R6 | CIFAR-10 RF v4 matched-NFE (`tools/run_sota_cifar_experiment.py --baseline-num-steps 50 --framework-max-num-steps 50 --samples 500 --framework-samples 50`) | **NOT_REPRODUCED** | Skipped before invocation (0 s wall-clock, 0 GiB GPU). Conditional gate triggered: 990 MB gnobitab Score-SDE checkpoint (`data/cifar10_rf.pth`) absent; drive.google.com / huggingface.co / github.com all blocked by network policy (positive control `download.pytorch.org` reachable). No FID produced. CLM-040 v4 sub-claim **cannot_compare** in this sandbox. | not invoked (network-blocked) | null |
| R7 | byte-stability (`pytest tests/test_adapters/test_adapter_common.py -v`) | **REPRODUCED** | 9/9 pytest tests passed (originally-claimed 6/6 is a strict subset; 3 additional `test_memory_fraction_for_paper_uplift_27_*` rows added later). Exit 0, 0.14 s wall-clock, no GPU. 3 DeprecationWarnings present (benign). No regression. | CPU (0 GiB GPU) | null |
| R8 | acyclic test-gate (`pytest tests/test_framework/test_import_acyclic.py -v`) | **REPRODUCED** | 4 passed, 3 warnings in 0.71 s. Test list: `test_acyclic_import_order[historical-order]`, `test_acyclic_import_order[reverse-order]`, `test_local_protocol_byte_equivalent_to_universal`, `test_calibration_protocols_no_universal_evaluator`. 3 DeprecationWarnings on lazy `__getattr__` shims (RMSPreservingCoordinateMixer, RoundResultBundle, validate_round_result_bundle) from 28e3bf9 circular-import break — benign. | CPU (0 GiB GPU) | null |

- **Current value (3-way count):** REPRODUCED = 4 (R1, R4, R7, R8); PARTIAL = 1 (R2); NOT_REPRODUCED = 3 (R3, R5, R6).
- **Rev 2 target:** ≥ 6/8 REPRODUCED by Wave 14; **all 8 classified into 3-way buckets** (this audit satisfies the second clause — every experiment has a bucket; the first clause is not yet met, 4 vs target 6).
- **Interpretation:** The 4 REPRODUCED rows cover the algorithm-layer table (R1), the headline GPU paper-parity reproduction (R4), and the two CPU-only structural gates (R7 byte-stability, R8 acyclic test-gate). The 1 PARTIAL row (R2) reproduces deterministically across three independent invocations but its 8 numeric figures diverged from the values recorded in `docs/ABLATION.md` (root cause: 36 files changed between a12e481 — when the doc was last written — and HEAD `27dcb9cb`); the qualitative claim "no schedule family dominates both targets" survives. The 3 NOT_REPRODUCED rows form a coherent "external-dependency" cluster: R3 (timeout cuts off eight_gaussians; ~7× W2 magnitude divergence on two_moons whose source is unclear — likely upstream of the adapter weights at `data/twodim_fm_two_moons.npz`); R5 (FlowMol3 framework-vs-baseline produces zero RDKit-valid molecules in either arm, including at the exact §1.1.d config, because the native venv does not run the sidecar forward-pass route the doc was produced with); R6 (CIFAR-10 v4 skipped before invocation because the 990 MB gnobitab checkpoint is blocked by sandbox network policy).
- **Target gap:** Need **+2 REPRODUCED** by Wave 14 (currently 4; target ≥ 6). Conversion paths, ranked:
  1. **R5 → REPRODUCED is the highest-leverage move**: install the Python 3.11 sidecar (`/home/hugo/.venv-flowmol311` with dgl 2.1.0 + torch 2.2.1+cpu) and re-run the exact §1.1.d configuration. If §1.1.d reproduces at sidecar parity, the row flips from NOT_REPRODUCED to REPRODUCED *and* the headline claim of the v4 docs becomes sandbox-reproducible. The 28e3bf9 + Wave 8 sidecar-installation findings already documented the install steps; this is a hardware-light environment install, not an experiment.
  2. **R6 → REPRODUCED needs only the gnobitab checkpoint**: provide a sandbox-reachable mirror (HuggingFace release tarball, or `download.pytorch.org` positive-control pattern already proven reachable). Once `data/cifar10_rf.pth` exists, the script runs in < 5 min on GPU 0; CLM-040 v4's honest-negative direction (framework FID worse on matched 50-NFE) is already documented and would survive.
  3. **R3 → REPRODUCED needs both a longer timeout (≥ 2000 s) AND the upstream W2-magnitude discrepancy resolved**: investigate whether the adapter weights at `data/twodim_fm_two_moons.npz` differ from what produced the doc numbers; the W2 formula (`scipy.stats.wasserstein_distance` against n_ref=1000 analytic samples) already matches the doc. Even after the W2 fix, R3 is at risk of remaining PARTIAL rather than full REPRODUCED because the doc claims a ~7% framework improvement over baseline while the run shows framework slightly *worse* — the direction itself would need re-investigation.
  4. **R2 is correctly PARTIAL** as long as `docs/ABLATION.md` is stale; converting it to REPRODUCED requires either re-recording the table (regenerate `docs/ABLATION.md` from current HEAD, in place, and accept that the prior 8 figures are stale) or adding a regenerate-on-build hook. The byte-identical determinism already satisfies the reproducibility half of the claim; only the doc freshness stands in the way.
- **Honest caveats (carried from the record):**
  - The 0-GiB GPU readings for R1/R2/R3/R7/R8 mean nvidia-smi polled every 5 s saw no growth; these scripts do not allocate CUDA, so the polling correctly returned 0.
  - R4's reported wall-clock 480 s for Phase B N=1000 is ~13% faster than the recorded 553 s — within sampling noise, not a divergence.
  - R5's paired_delta is `+0.0` only because both arms produced zero valid molecules; this is not a "no-improvement" finding, it is an undefined comparison (NaN over an empty valid set).
  - The env_hash field is `null` for every row because the Wave 6 record did not capture one. If Wave 14 needs reproducible env_hash values, the audit harness should be extended to record `python -c "import sys, torch; print(hash((sys.version, torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')))"` (or equivalent) into `result.json` for every run.

---

## F.5 — env_hash capture

- **Metric ID:** F.5
- **Metric title:** Environment-fingerprint reproducibility (`env_hash.txt` shipped with every reproduction; `env_hash = SHA256( requirements-lock.txt + python --version + torch.__version__ + torch.version.cuda + adapter-specific dependency versions )`; NOT a full pip freeze)
- **Audit command:**
  ```bash
  cd /home/hugo/codes/flowa-multistep-reinference
  ls scripts/capture_env_hash.py requirements-lock.txt env_hash.txt 2>/dev/null
  python --version 2>&1 | head -1
  python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.version.cuda)" 2>&1 | head -5
  grep -A 1 '^name = "torch"' uv.lock | head -2
  sha256sum pyproject.toml uv.lock
  printf '%s\n%s\nPython 3.14.5\ntorch=2.13.0+cu130 cuda=13.0\nuv.lock-declared torch=2.14.0\n' \
    "$(sha256sum pyproject.toml | awk '{print $1}')" \
    "$(sha256sum uv.lock | awk '{print $1}')" \
    | sha256sum
  ```
- **Raw output:**
  - `scripts/capture_env_hash.py` → **MISSING**
  - `requirements-lock.txt` → **MISSING** (repo uses `uv.lock` + `pyproject.toml`; no adapter-specific requirement file exists)
  - `env_hash.txt` → **MISSING**
  - System `python --version` → `Python 3.14.5`
  - System `python -c "import torch"` → `ModuleNotFoundError: No module named 'torch'`
  - cpg venv `/home/hugo/codes/cpg/.venv/bin/python -c "import torch; ..."` → `torch: 2.13.0+cu130`, `cuda: 13.0`
  - `uv.lock` declares `torch == 2.14.0` (no `+cuXXX` local-suffix; `cuda-bindings == 13.3.1` is a transitive dep)
  - `pyproject.toml` requires-python `>=3.12`
  - `sha256(pyproject.toml) = e3b22c8085b5a79876b14e325b947cb96c86ba251279b925fae93ae832a91628`
  - `sha256(uv.lock)       = 4df5d9e04d73f5f0beadc0cfe61e2d711b63ce142fdf1f2cbf495d622d0db5cc`
  - **Inline-computed env_hash** (substituting pyproject.toml + uv.lock for the missing `requirements-lock.txt`) → `701f1f66f4223cfe071f805233ab7d5dce32406be49e86752924527171a77a70`
- **Current value:** MISSING — none of the four F.5 artifacts (`scripts/capture_env_hash.py`, `requirements-lock.txt`, `env_hash.txt`, an adapter-specific dep list) are on disk. The repo's only lock file is `uv.lock`, which is a `uv` resolver artifact (not a hand-curated `requirements-lock.txt`); torch/CUDA versions are NOT pinned anywhere in the repo (closest declaration is `uv.lock`'s `torch == 2.14.0` + `cuda-bindings == 13.3.1`). System shell has Python 3.14.5 but no torch; the only available torch is in an unrelated cpg venv (`/home/hugo/codes/cpg/.venv`, torch 2.13.0+cu130), which is *not* the framework's own venv and does not match `uv.lock`'s declared torch 2.14.0 — this drift (declared 2.14.0, installed 2.13.0) is itself a reproducibility gap that an env_hash would surface.
- **Rev 2 target:** 100 % of reproductions ship an `env_hash.txt` whose hash matches a pinned lockfile by Wave 14; mismatched-hash auto-classified PARTIAL or NOT_REPRODUCED. HARD gate.
- **Interpretation:** F.5 pipeline entirely missing on disk. The repo has the *components* (uv.lock, pyproject.toml, python interpreter, torch installed in some venv) but no `capture_env_hash.py` script, no `requirements-lock.txt`, no `env_hash.txt` artifact, and no per-adapter dependency list. Because `uv.lock` is the closest thing to a pinned lock, the hash `701f1f66…` reported above is a *proxy* (substituting pyproject.toml + uv.lock for the spec's missing `requirements-lock.txt`); it should not be treated as the F.5-canonical env_hash. The spec's prescribed `requirements-lock.txt` is what Wave 14 work should generate (`uv pip freeze | grep -v '^#' | sort > requirements-lock.txt` or equivalent), and the capture script should:
  1. SHA256 the lock file,
  2. capture `python --version` (and, when available, `python -c "import sys; print(sys.executable, sys.version_info)"`),
  3. capture `torch.__version__` and `torch.version.cuda` from the same interpreter,
  4. enumerate each registered adapter's pinned dependency versions (FlowMol3, Self-Flow, LineageFlow, ProtBFN/ABBFN, GraphBFN, HiDream-I1, Lumina-Image-2.0, Wan2.2 — at minimum, version of `transformers`, `dgl`, `flash-attn`, `torch-geometric`, etc., surfaced via adapter-registry introspection),
  5. write `env_hash.txt` containing all of the above + a single combined SHA256, and emit the hash to stdout for CI consumption.

  Two concrete issues the captured state surfaces:
  - **uv.lock vs installed drift:** `uv.lock` pins `torch == 2.14.0`; the only available interpreter (`/home/hugo/codes/cpg/.venv/bin/python`) has `torch 2.13.0+cu130`. A reproduction that runs `uv sync` would land on 2.14.0, while one using a hand-installed torch lands on 2.13.0+cu130 — F.5's env_hash would detect the mismatch. This is *desired* (the whole point of F.5), but it means the repo currently has no reproducible env to hash.
  - **No system torch:** `python -c "import torch"` fails in the shell Python. Any cold-clone reproduction that does not first run `uv sync` will fail before env_hash is captured, auto-classifying the reproduction NOT_REPRODUCED per F.5 policy.

- **Target gap:** 4 artifacts missing (`scripts/capture_env_hash.py`, `requirements-lock.txt`, `env_hash.txt`, adapter-specific dep list) + no framework uv-managed venv exists (no `.venv/` at repo root; no `uv sync` has been run for the framework's own pyproject.toml — only borrowed torch exists in an unrelated cpg project). Next actions (in order):
  1. Generate `requirements-lock.txt` via `uv pip freeze | grep -v '^#' | sort > requirements-lock.txt` after `uv sync` succeeds against `pyproject.toml` + `uv.lock`.
  2. Author `scripts/capture_env_hash.py` implementing the 5-step spec above (lock-hash + python --version + torch.__version__ + torch.version.cuda + per-adapter dep versions).
  3. Run the script once to produce `env_hash.txt`, commit both files, and use `env_hash.txt` as the F.5 baseline going forward.
  4. Update `todo/framework-internal-metrics.md` and the per-model integration checklist to gate on `env_hash.txt` presence + content match (per F.5's "100 % of reproductions" target).

---

## Summary (post-aggregation)

### Summary table — all 9 metric IDs, current values, targets, gap

| Metric ID | Title | Current value | Rev 2 target | Gap |
|---|---|---|---|---|
| A.0 | Paper-statement inventory | 20 implemented statements + 7 documented gaps; 141 paper-reference hits; 18/20 have direct tests (Remark 1 docstring-only; nu_g transitively covered) | parity with Wave 11/12 (no fixed number) | None blocking framework math; G4 (rate constant, Task #360) and G7 (Prop 6 positive dir) are open |
| A.4 | Per-equation citation density | 0.171 (14 / 82 public functions annotated) | ≥ 0.90 by Wave 14 | −0.729 (need ~+60 annotated functions) |
| A.7 | Hypothesis-violation (must-fail) coverage | strict 6/8 = 75 %; broad 7/8 = 87.5 % | 100 % of constructive entries by Wave 16 | −25 pp strict / −12.5 pp broad (Lemma 3 strict gap + Proposition 2 symmetry) |
| B.4 | Doctest execution | exit 5 (0 collected, 0 failures — vacuous pass) | 0 failures by Wave 13 | MET vacuously; add doctests + CI wire-up so the metric carries signal |
| D.3 | Adapter conformance pass rate | 226/226 = 100 % across 13 hand-written per-adapter test files | 18/18 against D.5 auto-battery by Wave 14 | need D.5 (currently MISSING) + 2 more hand-written adapters |
| D.5 | Conformance battery existence | MISSING (no `tests/test_adapters/conformance_battery.py`) | D.5 battery live by Wave 14 | 1 file missing |
| E.2 | Documentation cross-reference rate | 0.5714 (16 / 28 docs/*.md) | ≥ 0.9 by Wave 14 | −0.329 (need +9 to +10 referencing files; may need to broaden the regex) |
| F.2 | Wave 6 head experiments (3-way) | REPRODUCED = 4 / 8 (R1, R4, R7, R8); PARTIAL = 1 (R2); NOT_REPRODUCED = 3 (R3, R5, R6); all 8 classified | ≥ 6/8 REPRODUCED by Wave 14 | −2 REPRODUCED rows |
| F.5 | env_hash capture | MISSING (no `scripts/capture_env_hash.py`, `requirements-lock.txt`, `env_hash.txt`, or per-adapter dep list) | 100 % of reproductions ship env_hash.txt by Wave 14 (HARD gate) | 4 artifacts missing + no framework uv-managed venv |

### Next actions (priority order)

1. **F.5 — env_hash capture (HARD gate, blocking Wave 14 reproducibility).** Generate `requirements-lock.txt` via `uv sync && uv pip freeze | grep -v '^#' | sort > requirements-lock.txt`; author `scripts/capture_env_hash.py` (5-step spec: lock-hash + `python --version` + `torch.__version__` + `torch.version.cuda` + per-adapter dep versions); run once to produce `env_hash.txt`; commit all four artifacts; gate per-model integration checklist on `env_hash.txt` presence + content match. Resolve the uv.lock-vs-installed drift (`uv.lock` pins `torch == 2.14.0`; only `cpg/.venv` torch is 2.13.0+cu130) by provisioning the framework's own venv.
2. **F.2 — flip 2 of 3 NOT_REPRODUCED rows to REPRODUCED by Wave 14 (need ≥ 6/8).** Highest leverage: (a) install the Python 3.11 sidecar (`/home/hugo/.venv-flowmol311` with dgl 2.1.0 + torch 2.2.1+cpu) and re-run R5 §1.1.d; (b) provide a sandbox-reachable mirror for the 990 MB gnobitab Score-SDE checkpoint (HuggingFace tarball or `download.pytorch.org` pattern) so R6 can run; (c) only after the above, investigate R3 W2-magnitude discrepancy and bump timeout ≥ 2000 s; (d) regenerate `docs/ABLATION.md` from current HEAD (or add a regenerate-on-build hook) to lift R2 from PARTIAL to REPRODUCED.
3. **D.5 — author `tests/test_adapters/conformance_battery.py`.** Auto-generated/spec-derived battery exercising the cross-adapter contract for all 14+ registered adapters, producing ≥ 18 distinct conformance assertions. Wire into CI (auto-picked-up by pytest once present). Then D.3 can be re-measured against the auto-battery rather than the hand-written 13-file baseline.
4. **A.4 — citation density 0.171 → ≥ 0.90 by Wave 14.** Annotate `paper_quantities.py` `_with_result` wrappers with `Eq. N` / `Section N` anchors (4 funcs, low risk); add paper anchors to `validation.py` helpers (`validate_g_admissible`, `_detect_zeros`); lift `Theorem 1 (line 87-92)` anchor from `__init__.py` module docstring into each public re-export docstring; sweep `checkers.py` helpers for missing citations; re-run audit and confirm ≥ 0.90.
5. **E.2 — documentation cross-reference rate 0.571 → ≥ 0.9 by Wave 14.** Add at least one `Theorem N` / `Lemma N` / `Proposition N` or `paper section X.Y` anchor to each of the 12 non-referencing top-level docs where semantically relevant. If 0.9 is unreachable under the strict regex, broaden the pattern to also accept equation/figure/table references and re-audit.
6. **A.7 — close must-fail coverage gaps to reach 100 % by Wave 16.** (a) Promote Lemma 3 must-fail into `tests/test_theory/` — add `tests/test_theory/test_lemma3_per_cell_coefficient.py` containing a port of the existing `test_paper_quantities_reject_invalid_params` parametrisation restricted to `per_cell_coefficient_C` (~10 LOC). (b) For Proposition 2, either add a must-fail (`test_g_a_with_unbounded_a_fails_admissibility`) OR formally document the Prop-2 / Prop-6 symmetry in `docs/adr/0005-fail-closed-audit-code-policy.md`. (c) Optionally create `tests/test_theory/negative/` as the canonical must-fail directory (5 file moves + `conftest.py` import-path updates).
7. **D.3 — add hand-written tests for the 2 registered adapters without one.** Author `test_flowmol3_adapter.py` and `test_toy_gaussian_adapter.py` to reach 15/15 hand-written coverage (then 18/18 once D.5 is live).
8. **B.4 — add doctests + wire them into CI.** Insert worked `>>>` examples into `paper_quantities.py` (13/13 already documented) and `checkers.py` (8/9 documented). Add `--doctest-modules adaptive_reflow/theory/` as an explicit step in `.github/workflows/cpu-tests.yml` (or to `addopts` in `pyproject.toml`); treat exit code 5 as a failure in the CI step so silent loss of examples fails loudly.
9. **A.0 — close Task #360 (G4: explicit rate constant for Theorem 1).** Document an explicit `rate_constant` field in `emit_theorem1_statement`. Optional: add a Proposition 6 positive-direction dedicated test (G7).

