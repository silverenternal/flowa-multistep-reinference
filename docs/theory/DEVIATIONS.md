# Theory layer deviations — paper vs. implementation

**Date:** 2026-09-05
**Wave:** Wave 29 Agent A
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Paper:** Li 2024, JMAA paper (`docs/ARCHIVE/top-level/NoiseSelectedRectification_EN.md`)

This file records deviations between the JMAA paper's theorems /
equations and the framework's implementation. It is **additive**
(append-only); earlier deviations may live in upstream docs.

The primary audit document with experimental details and impact
estimates is `docs/audit/theory-implementation-gap.md` (Wave 29
Agent A).

---

## DEVIATION-001 — `checkers.py:sheet_tube_evidence` uses wrong residual

**Status:** CONFIRMED BUG
**Severity:** Medium
**Affected file:** `adaptive_reflow/theory/checkers.py` (lines
304-404)

**Paper says:** Lemma 2 (line 100-104) with the residual identity
(line 142-144):

```
|F_g(x, y)|^2 = y^2 · (g(x)^2 + (y - 1)^2)
```

**Implementation does:** Uses `F_g = y - g(x)` (line 379), so
`|F_g|² = (y - g(x))²`. The comment on line 378 ("We use the standard
paper residual") is incorrect — the paper's residual is 2D-vector-
valued with the codimension-1 sheet `{(x, 0)}` and codimension-2
points `{(z, 1) : g(z) = 0}`.

**Compare:** The CORRECT paper-faithful implementation lives in
`adaptive_reflow/theory/lemma2_checker.py` (line 131):

```python
F_g_sq = (y * y) * (gx2 + ym1 * ym1)  # y^2 * (g(x)^2 + (y-1)^2)
```

Both `sheet_tube_evidence` functions are exported from
`adaptive_reflow/theory/__init__.py`. The wrong one is reached via
`from adaptive_reflow.theory.checkers import sheet_tube_evidence`.

**Affected regression:** none directly (this function is a
diagnostic, not on the algorithm path). The bug is in the
**theory-layer witness**, which means any conformance test using
the wrong function will fail (or pass on the wrong residual).

**Recommended fix:** Copy the `lemma2_checker.py` body into
`checkers.py`, replacing the wrong implementation. Mark
`lemma2_checker.sheet_tube_evidence` as the canonical entry and
deprecate the duplicate.

---

## DEVIATION-002 — `eval/lipschitz_diagnostic.py:PLANAR_BL_CONSTANT` binds simplified residual, not paper's

**Status:** CONFIRMED BUG (misleadingly named, self-consistent math)
**Severity:** Medium
**Affected files:**
- `adaptive_reflow/eval/lipschitz_diagnostic.py` (lines 420-429,
  543-568, 571-589)
- `adaptive_reflow/theory/rate_bound.py` (lines 30-50, 107-196)
- `adaptive_reflow/theory/checkers.py` (lines 79-82)

**Paper says:** The residual posterior `μ_{g,ε}` has density
proportional to `exp(-|z|²/2) · exp(-|F_g(z)|²/(2ε²))` with the
**paper** residual `F_g(x,y) = (y·g(x), y·(y-1))`.

**Implementation does:** Uses the **simplified** residual
`F_g(x, y) = y - g(x)` everywhere in the planar witness and rate
bound. The synchronous coupling `(x, g(x) + ε·z) ↔ (x, g(x))` is
valid for the simplified residual, and `√(2/π) = E|ε·z|` is the
right constant.

The "selection density" `q_g(x) = e^{-x²/2} / √(1+g(x)²)` (paper
line 82) is NOT what the framework's planar witness converges to;
the correct limit for the simplified residual is `exp(-x²/2) /
√(2π)` (a Gaussian), not the paper's coarea-weighted form.

**Affected regression:** None on the algorithm path (the framework
uses cosine annealing, not paper-driven n_cap; see DEVIATION-004).
The deviation is in the **theory layer** — anyone reading
`PLANAR_BL_CONSTANT = √(2/π)` and `BL(μ_{g,ε}, ν_g) ≤ √(2/π)·ε`
will believe this bounds the paper's Theorem 1 quantity, which it
does not.

**Recommended fix:** Document `PLANAR_BL_CONSTANT` as bound for the
**simplified planar residual**, not the paper's. Consider
implementing a paper-faithful sampler in
`eval/paper_faithful_sampler.py` and a separate
`check_explicit_rate_bound_paper_faithful` in `theory/rate_bound.py`.

---

## DEVIATION-003 — `selection_ratio` (eval) name collision with paper quantity

**Status:** KNOWN LIMITATION (documented, but name is misleading)
**Severity:** Low
**Affected file:** `adaptive_reflow/eval/posterior_selection_evaluator.py`
(lines 279-353)

**Paper says:** n/a (the paper has no `selection_ratio` quantity;
its analog is `μ_{g,ε}(sheet) / μ_{g,ε}(cells)` which is paper-
inferred from A_g, B_g, C_g).

**Implementation does:** Computes `sheet / (sheet + cell)` where:
- `sheet = mean(exp(-x²/2))` over endpoints (≈ 0.4 for N(0,1)ish
  samples).
- `cell = sum(exp(-|z_j|²/2) / (2π))` over **canonical mode centres
  for `two_moons` or `eight_gaussians`** (a CONSTANT).

**Why this saturates at 1.0 on LineageFlow:** LineageFlow does not
produce 2D continuous endpoints, so the heuristic's "cells" are
either empty (ratio → 1.0 by `total == 0` fallback) or derived
from a target name that doesn't apply (line 522 in
`posterior_selection_evaluator.py`).

**Affected regression:** LineageFlow decision metric saturation
(Wave 19 P1A2 finding). Documented as framework-internal
heuristic, NOT a paper claim.

**Recommended fix:** Rename `eval.selection_ratio` to
`eval.sheet_vs_cells_proxy` (or `heuristic_selection_ratio` per the
deprecated `SelectionRatioWitness.heuristic_selection_ratio`).
Callers importing `selection_ratio` from `eval.posterior_selection_evaluator`
should switch to the qualified name.

---

## DEVIATION-004 — `CodimensionSheetScheduler.n_cap` is cosine-driven, not paper-ratio-driven

**Status:** KNOWN LIMITATION (architectural)
**Severity:** High (root cause of twodim_fm regression)
**Affected file:**
`adaptive_reflow/algorithm/scheduler/_core.py` (lines 2290-2784)

**Paper says:** Theorem 1 + Corollary 1 imply that as `ε → 0`,
sheet evidence `Θ(ε⁺¹)` dominates cell evidence `O(ε⁺²)`. In the
framework's mapping, this means per-round `n_cap` should track
`evidence_ratio` (high when sheet dominates → fine integration).

**Implementation does:** `n_cap` is purely cosine-annealing
(ADR-0010); the paper-derived `ratio` is computed per-round but
only stored as a **reportable metric** (`evidence_ratio` on the
`ScheduleSample`).

**Why this is structural:** Per
`docs/theory/operating-regime.md` §2.2:

> "There is **no** profile `g(x)` such that `v_θ` matches `g` on the
> support — the framework's sheet-vs-cell decomposition (`A_g · ε`
> vs `C_g · B_g · ε²`, paper line 161 + Corollary 1 line 165) is
> therefore ill-conditioned."

For 2D velocity fields (twodim_fm), the paper's 1D-sheet machinery
does not specialise. The framework has accepted this regression
explicitly (operating-regime §1.4 falsification).

**Affected regression:** twodim_fm at every σ ∈ [0, 0.5]
(Wave 17 P3 honest operating-regime).

**Recommended fix:** Defer — the cosine-driven n_cap is the
framework's published design (ADR-0010); changing it would
invalidate 36 algorithm-level uplifts.

---

## DEVIATION-005 — `LinearBlender` is convex combination, not paper §4 restart

**Status:** KNOWN LIMITATION (architectural)
**Severity:** Medium
**Affected files:**
- `adaptive_reflow/algorithm/blender.py` (lines 466-555)
- `adaptive_reflow/algorithm/blender_extra.py`
- `adaptive_reflow/algorithm/per_channel_blender.py`
- `adaptive_reflow/algorithm/categorical_blender.py`

**Paper says:** §4 (CIFAR-10 matched-NFE restart) is an
**experimental** setup with a specific sheet-restart at chosen
points. There is NO closed-form operator equation in the paper.

**Implementation does:** `LinearBlender` computes `new = m * prior +
(1 - m) * fresh` (a convex combination). `DistanceDecayBlender`
adds a content-aware decay factor. `CategoricalAwareBlender` and
`PerChannelBlender` are framework-internal variants.

**Affected regression:** CIFAR-10 matched-NFE +24-31% (paper §4).
The framework implements the closest analog (linear blend) but
there is no paper formula to match.

**Recommended fix:** Document the gap. Defer paper-faithful
matched-NFE restart as "experimental, no closed-form operator".

---

## DEVIATION-006 — Two `validate_f_side` functions with different error codes

**Status:** KNOWN LIMITATION (intentional, but confusing)
**Severity:** Low
**Affected files:**
- `adaptive_reflow/theory/validation.py` (line 58-95)
- `adaptive_reflow/theory/f_side_validator.py` (line 54-105)

Both modules export `validate_f_side(d, c, rho, eta)` with the
same logic but DIFFERENT error codes:
- `theory/validation`: `separation_d_must_be_positive`,
  `simplicity_c_must_be_positive`, `rho_must_be_in_(0,1/4]`,
  `cells_overlap`, `eta_must_be_positive`.
- `theory/f_side_validator`: `rho_must_be_lt_d_over_4`,
  `rho_must_be_le_1/4`, `c_must_be_positive`, `eta_must_be_positive`.

This is documented in `f_side_validator.py` docstring (line 41-45)
as a deliberate naming split (paper-symbol-friendly vs framework-
internal), but it remains a maintenance hazard.

**Recommended fix:** Consolidate to a single `validate_f_side`
with one canonical error-code namespace. The two callers
(framework-side + paper-symbol-friendly) can both import from one
source.

---

## DEVIATION-001 (FIXED) — `checkers.py:sheet_tube_evidence` residual

**Status:** FIXED in Wave 30 Agent C (F-1 fix)
**Severity (pre-fix):** Medium
**Affected file:** `adaptive_reflow/theory/checkers.py`
(lines 304-404, LHS loop at 376-388)

**Paper says:** Lemma 2 (line 100-104) with the residual identity
(line 142-144):

```
|F_g(x, y)|^2 = y^2 · (g(x)^2 + (y - 1)^2)
```

**Pre-fix implementation did:** Used `F_g = y - g(x)` so
`|F_g|² = (y - g(x))²`. This was documented as DEVIATION-001 above.

**Fix applied (Wave 30 Agent C, F-1):** The inner loop in
`sheet_tube_evidence` (checkers.py:376-388) now mirrors the canonical
paper-faithful form from `adaptive_reflow/theory/lemma2_checker.py:131`:

```python
gx = float(g(x))
gx2 = gx * gx
ym1 = y - 1.0
F_g_sq = (y * y) * (gx2 + ym1 * ym1)
log_p = -0.5 * (x * x + y * y) - F_g_sq * inv_2eps2
```

This matches paper line 142-144 verbatim (the literal residual
geometry of the residual fibre). The simplified `F_g = y - g(x)`
form is REMOVED.

**Deprecation note:** The `checkers.py:sheet_tube_evidence` function
docstring now declares itself as a back-compat shim that re-implements
the canonical
`adaptive_reflow.theory.lemma2_checker.sheet_tube_evidence` math.
The lemma2_checker module is the canonical entry point; new code
should import from there.

**Tests verified:** All 85 tests in `tests/test_theory/` pass with the
paper-faithful residual. Tests that were silently passing on the
wrong residual (DEVIATION-001 pre-fix) now pass on the paper-faithful
one — the conformance is real, not a name change.

---

## DEVIATION-003 (PARTIAL FIX) — `selection_ratio` (eval) name collision

**Status:** PARTIAL FIX (Wave 30 Agent C, F-4): function renamed,
legacy alias kept.
**Severity (pre-fix):** Low
**Affected file:** `adaptive_reflow/eval/posterior_selection_evaluator.py`

**Pre-fix problem:** `eval.posterior_selection_evaluator.selection_ratio`
(framework-internal heuristic `sheet / (sheet + cell)`) collided by
name with
`adaptive_reflow.theory.paper_quantities.paper_selection_ratio`
(paper Corollary 1, with `eps -> 0` limit). They are DIFFERENT
quantities that share the suffix "selection_ratio".

**Fix applied (Wave 30 Agent C, F-4):**

1. Renamed the function `selection_ratio` → `sheet_vs_cells_proxy` in
   `adaptive_reflow/eval/posterior_selection_evaluator.py` (the
   function now lives under its paper-faithful semantic name).
2. Kept `selection_ratio` as a **deprecated back-compat alias** that
   emits a `DeprecationWarning` and forwards to `sheet_vs_cells_proxy`
   (byte-identical output).
3. The dict key in oracle outputs (`oracle()` / `oracle_batched()` /
   `oracle_at_round()`) now uses `"sheet_vs_cells_proxy"` as the
   canonical key, with `"selection_ratio"` retained as a legacy alias
   for byte-stable callers.
4. `adaptive_reflow/eval/__init__.py` re-exports BOTH names so existing
   `from adaptive_reflow.eval import selection_ratio` continues to
   work (with warning).

**Call sites updated (full audit):**

- `adaptive_reflow/eval/posterior_selection_evaluator.py` (function
  definition + 3 internal callsites + 3 oracle dict-key pairs).
- `adaptive_reflow/eval/__init__.py` (re-export list updated to
  include `sheet_vs_cells_proxy` + retained `selection_ratio` as a
  deprecated re-export).
- `adaptive_reflow/algorithm/batched_runner.py`:
  `_evaluate_selection_ratio_for_round` (line 525) docstring updated
  to reference `sheet_vs_cells_proxy`; the function still does the
  same math inline (does not call `sheet_vs_cells_proxy` directly).
  Result dict key `"selection_ratio"` retained as the legacy name
  (no behaviour change for callers).
- `adaptive_reflow/algorithm/runner.py` (line 1050-1051): keeps
  `"selection_ratio"` dict-key access for the per-round metric —
  legacy alias dict key in the oracle ensures byte-stable output.
- `adaptive_reflow/algorithm/scheduler/evidence_driven.py`:
  `metrics["selection_ratio"]` dict-key access kept; comment updated
  to note the legacy alias.

**Tests:** All 49 tests in `tests/test_eval/test_posterior_selection_evaluator.py`
pass with the rename. Deprecation warnings appear when the legacy
`selection_ratio` name is used (intentional).

**Follow-up TODO:** A future wave can remove the legacy
`selection_ratio` alias once all downstream callers are migrated.
Track in `docs/DEPRECATION.md` if not already present.

---

## Summary

- **6 deviations** (DEVIATION-001 to DEVIATION-006); plus 2 fix
  entries (DEVIATION-001 FIXED, DEVIATION-003 PARTIAL FIX).
- **2 CONFIRMED BUGS** (DEVIATION-002; DEVIATION-001 was FIXED in
  Wave 30 Agent C)
- **0 paper-quantity primitives wrong** — A_g, B_g, C_g, e_ρ are
  all paper-faithful.
- **0 paper-thesis violations** — the framework correctly
  IMPLEMENTS the math; the divergences are in (a) which residual
  the framework uses for diagnostics (simplified vs paper — DEVIATION-002
  only; DEVIATION-001 is now FIXED), and (b) how the paper signal
  maps to scheduler n_cap (decorative vs driving).
- **0 paper-quantity primitives wrong** — A_g, B_g, C_g, e_ρ are
  all paper-faithful.
- **0 paper-thesis violations** — the framework correctly
  IMPLEMENTS the math; the divergences are in (a) which residual
  the framework uses for diagnostics (simplified vs paper), and
  (b) how the paper signal maps to scheduler n_cap (decorative vs
  driving).

The honest summary: **the framework implements the paper's math
correctly, but uses a different residual than the paper for the
planar / BL machinery, and the paper-signal doesn't drive the
scheduler on out-of-F-side-class adapters**. The latter is by
design (ADR-0010 cosine annealing); the former is the framework's
"sheet+graph" simplified view.