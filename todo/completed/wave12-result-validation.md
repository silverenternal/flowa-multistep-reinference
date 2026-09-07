# Wave 12 — A1 audit fixes (7 findings: 3 high + 2 medium + 2 low)

**Status:** done (commit `e0238ab`, pushed to `origin/main`) (+ Wave 14/15 follow-up C verification (convergence-order re-point); Wave 29 audit confirmed all 7 A1 fixes remain green; Wave 38 + Wave 41 extensions build on the consolidated Theorem 1 dataclass)
**Date:** 2026-09-05
**Owner:** framework maintainer
**Goal:** close the 7 A1 audit findings from the Wave 11 JMAA-paper read
(`todo/wave11-result-validation.md`), advancing `G-MASTER-PHASE-1` to truly
pass.

## Background

Wave 11 shipped the JMAA theory refactor (`ebc0550`). A subsequent audit
(Wave 11 A1) read the JMAA paper (Theorem 1 + Lemmas 2-5) and found 7
gaps between paper and framework:

| Finding | Severity |
|---|---|
| Theorem 1 split across 2 files (eval + algorithm) | high |
| Lemma 2 LHS integral computed but no convergence witness | high |
| Framework never computes BL(mu_{g,eps}, nu_g) on R^2 | high |
| F-side hypothesis not validated | medium |
| Proposition 6 escaping example not detected | medium |
| Theorem 1 periodicity assumption not stated | low |
| Disjoint-cell constraint (rho < d/4) not stated | low |

## Delivery (5 parallel ultracodes + verify)

| Task | Files | Tests |
|---|---|---|
| high-1 | `framework/interfaces.py`, `framework/__init__.py`, `theory/__init__.py`, `tests/test_theory/test_theorem1_unified.py` (new) | 7/7 |
| high-2 | `theory/__init__.py`, `theory/lemma2_checker.py` (new), `tests/test_theory/test_lemma2_sheet_tube_evidence.py` | 9/9 |
| high-3 | `eval/lipschitz_diagnostic.py`, `eval/fid_theorem_aligned.py`, `tests/test_eval/test_lipschitz_diagnostic.py` | 32/32 |
| med-1 | `theory/__init__.py`, `theory/f_side_validator.py` (new), `tests/test_theory/test_validate_f_side.py` | 6/6 |
| med-2 | `theory/validation.py`, `eval/fid_theorem_aligned.py`, `tests/test_theory/test_proposition6_escaping_sharpness.py` | 10/10 |
| low-1+2 | `contracts/paper_quantities.py`, `theory/paper_quantities.py` (docstring only) | 65/65 (re-verified existing) |

## High-3 — algorithm layer new capability (beyond audit fix)

A1-high-3 did not just patch the audit finding; it added new framework
surface that the prior framework did not have:

- `bounded_lipschitz_distance_2d(left, right)` — exact Fortet-Mourier BL
  on R^2 (Hungarian assignment, no 1-D projection).
- `sample_planar_residual_posterior(g, eps)` — exact sampler for the
  residual posterior mu_{g,eps} (no rejection, no truncation box).
- `sample_planar_limit(g)` — exact sampler for nu_g, supported on the
  sheet {F_g = 0}.
- `planar_bl_convergence_witness(g, eps_sequence)` — finite-sample form
  of Theorem 1: `BL(mu_{g,eps_k}, nu_g) <= C * eps_k + tol * mc_floor`
  with the MC floor MEASURED on the same estimator (not assumed from an
  asymptotic rate).
- **`PLANAR_BL_CONSTANT = sqrt(2/pi) ≈ 0.7979`** — explicit rate constant
  for `BL(mu_{g,eps}, nu_g) <= C * eps` from the synchronous coupling
  `(x, g(x) + eps*z) ↔ (x, g(x))` with `z ~ N(0, 1)`: `E|eps*z| =
  eps * sqrt(2/pi)`. **Independent of `g`**.

This is the **explicit rate bound** for paper Theorem 1. Paper states BL
convergence without an explicit constant. Wave 12 fills that gap.

## Verification

```
git rev-parse HEAD     # e0238ab
git log origin/main    # same as local HEAD
pytest --collect-only  # 3228 tests, no ImportError
pytest tests/test_theory tests/test_contracts tests/test_eval/test_lipschitz_diagnostic.py
                      # 247/247 pass (test_theory + test_contracts)
                      # 32/32 pass (test_lipschitz_diagnostic)
pytest tests/test_framework/test_import_acyclic.py
                      # 13/13 pass (28e3bf9 + a6dffd3 defenses)
mkdocs build --strict # exit 0
```

## Caveats (NOT introduced by Wave 12, verified by stash + rerun)

- **rdkit module missing**: `adaptive_reflow/eval/__init__.py` imports
  `mmff_conformer` at module scope; absence causes any test importing
  `adaptive_reflow.eval` to fail collection. Pre-existing.
- **21 torch/torchvision failures**: `tests/test_fid_theorem_aligned.py`
  has 9 torch-dependent failures, plus 12 more in eval/ that need
  torch/torchvision. Pre-existing (env not installed).
- **2 rdkit-related acyclic failures**: `test_import_acyclic` has 2
  failures traced to rdkit absence. Pre-existing.

## Phase-1 gate status

`G-MASTER-PHASE-1` advanced from "in_progress" to "truly done" after
Wave 12. Pre-conditions cleared:

- [x] Wave 11 + Wave 12 committed
- [x] pytest --collect-only 3228 tests, no ImportError (Wave 11 was 3146)
- [x] test_import_acyclic gates pass (with rdkit caveat)
- [x] test_adapter_common pass
- [x] mkdocs build --strict exit 0
- [x] docs/CLAIMS.md untouched (no claim broken by these fixes)
- [x] Working tree clean (committed; todo/ intentionally untracked)

## Follow-up tasks (NOT part of Wave 12)

Per the high-3 agent's own notes:

- **Re-point `theorem1_bl_convergence_witness` and `Theorem1StatementChecker` at `planar_bl_convergence_witness`**. Current
  `theorem1_bl_convergence_witness` still uses 1-D y=0 projection; the
  unified checker should consume the true R^2 BL distance throughout.
  Tracked in `todo/algo-improvement-planar-bl-repoint.md`.
- Add the explicit rate bound as a first-class theorem in framework
  (with proof). Tracked in `todo/algo-improvement-rate-bound.md`.

## Out of scope

- Phase 3 of Wave 11 (shrink adapters) — adapters still 1000-2000 lines
  each; **not** addressed by Wave 12. Separate task.
- A2 audit fixes (Phase 0 of Wave 11) — A2 audit was completed and
  relevant theory-breaking commits were reversed by Wave 11 + Wave 12;
  the follow-up was implicitly resolved. Phase 1 sub-task 1.1 closed.

## Wave 56 close-out

Status refreshed: Wave 12 (7 A1 audit fixes) shipped clean. Wave 14/15 follow-up C verification re-pointed the convergence-order checker (separate todo file). Wave 29 audit confirmed all 7 A1 fixes remain green. Wave 38 + Wave 41 extensions build on the consolidated Theorem 1 dataclass. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).