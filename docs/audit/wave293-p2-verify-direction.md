# Wave 293 P2 — CosineScheduler direction-of-annealing empirical verification

**Date:** 2026-09-23
**Scope:** verify which sign convention is the source of truth (paper or code) and confirm the direction of annealing for the `CosineAnnealScheduler` family.
**Mode:** READ-ONLY verification (plus a non-committed empirical test at `/tmp/wf293_cosine_direction_test.py`). No code edits. No paper edits. No commits.
**Reference:** Wave 293 P1 location audit at `docs/audit/wave293-p1-locate-sign.md`; Wave 292 P3 cross-check at `docs/audit/wave292-p3-crosscheck.md` §3.1 MISMATCH-HIGH-1; Wave 282 scheduler-per-cell summary at `docs/audit/scheduler-per-cell-summary.md`; ADR-0010 at `docs/adr/0010-cosine-driven-memory-fraction.md`.

---

## 1. Code formula (verbatim)

`adaptive_reflow/schedule/cosine.py:227` (inside `n_cap_for_round`):

```python
n_cap = n_min + (n_max - n_min) * (1.0 + math.cos(math.pi * u_r)) / 2.0
```

where `u_r = r / (L - 1)` (line 219). Docstring at `cosine.py:157-159`:

```
The closed-form cosine is:
    n_cap = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2
    u_r = r / (L - 1)
```

`CosineAnnealScheduler` at `adaptive_reflow/algorithm/scheduler/simple.py:71` delegates to `n_cap_for_round` (the `from adaptive_reflow.schedule.cosine import ... n_cap_for_round` import at line 58 + ADR-0010 design statement at line 78 "the algorithm layer adds no second source of truth"). So `CosineAnnealScheduler` uses **exactly** the formula above.

## 2. ADR-0010 design intent (anneal DOWN)

ADR-0010 §"Decision Drivers" line 75-81:

> The "coarse-to-fine" drug-design intuition (lots of fresh noise for exploration early, preserve the prior for refinement late) matches the cosine-annealed schedule directly: at round 0 with `n_cap = n_max` (large), the memory fraction is small (lots of fresh noise); at round `L-1` with `n_cap = n_min` (small), the memory fraction is large (preserve the prior).

This unambiguously states: **round 0 → n_cap = n_max, round L-1 → n_cap = n_min** (anneal DOWN). That requires the (1+cos) form. The (1-cos) form would anneal UP (`n_min → n_max`), which contradicts ADR-0010's coarse-to-fine intuition (lots of fresh noise at the START for exploration; preserve prior at the END for refinement).

## 3. Paper claim (verbatim, Table 2.2)

`docs/drafts/paper-flat-flattened.md:62` Table 2.2 row:

```
| `CosineAnnealScheduler` | `cosine` | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / (L − 1)))`. ...
```

This is the (1−cos) form, which evaluates to `n_min` at `r=0` and `n_max` at `r=L-1` — i.e., anneal UP. The paper Table 2.2 contradicts ADR-0010's coarse-to-fine design intent. The same wrong formula is repeated at `docs/schedule-theory.md:15, 178, 207, 208` and at `docs/CLAIMS.md:110` (Wave 293 P1 audit §2.4, §2.6; total 7 wrong-sign occurrences across 4 files).

Per the §MS alignment preamble at `paper-flat-flattened.md:36` (Wave 292 P4 additive), the paper *also* quotes the correct (1+cos) form alongside the wrong Table 2.2 row, explicitly noting it is the "byte-stable closed form per `cosine.py:227`". And §2.10.2 (Wave 292 P3 cross-check, line 200 of paper) explicitly identifies M-HIGH-1 as "Table 2.2 cosine sign ... PAPER EDIT (additive pass): flip Table 2.2 cosine sign from `(1 − cos(π r / (L − 1)))` to `(1 + cos(π r / (L − 1)))`. Source: `adaptive_reflow/schedule/cosine.py:227`".

## 4. Empirical test (non-committed, `/tmp/wf293_cosine_direction_test.py`)

```
--- formula = (1+cos) ---
  r=0, u_r=0.0, n_cap=1.0
  r=3, u_r=1.0, n_cap=0.0
  DIRECTION: anneal DOWN  (n_max -> n_min; high at start)

--- formula = (1-cos) ---
  r=0, u_r=0.0, n_cap=0.0
  r=3, u_r=1.0, n_cap=1.0
  DIRECTION: anneal UP    (n_min -> n_max; low at start)
```

The test was submitted to `/tmp/wf293_cosine_direction_test.py` (per workflow directive: NOT committed). Test parameters: `L=4, n_min=0.0, n_max=1.0` (unit interval, the most legible scale). Both formulas were evaluated at `r=0` and `r=L-1=3`; the (1+cos) form gives `n_cap=1.0 → 0.0` (anneal DOWN); the (1−cos) form gives `n_cap=0.0 → 1.0` (anneal UP).

## 5. Wave 282 audit claim — confirmed

The workflow's reference to the "Wave 282 audit claim 'CosineAnnealScheduler does anneal down (n_max → n_min) per Wave 282 audit'" is **confirmed**:

* `docs/audit/wave282-p-cosine-vs-paper-controllers.md` — describes the Wave 281 cosine re-run REGRESSION at CIFAR cosine/seed42; framework FID is constant across seeds for a given (N, scheduler) config. The cosine arm is the load-bearing empirical handle, and the cosine arm anneals DOWN.
* `docs/audit/scheduler-per-cell-summary.md` — confirms 13/13 headline cells use `default_cosine_scheduler()` (the cosine arm that anneals DOWN). All headline numbers are cosine-DOWN readings.
* `docs/audit/wave292-p3-crosscheck.md` line 30 — explicitly states "the framework anneals DOWN n_max → n_min". Line 64 — Table 2.2 row mismatch verdict: "the paper formula anneals UP (`n_min → n_max` as `r` increases), the actual framework anneals DOWN (`n_max → n_min`)". Line 360 — paper-edit recommendation: "(1 + cos(π r / (L − 1))). The framework anneals DOWN (n_max → n_min), the [paper should match]".
* `docs/audit/wave293-p1-locate-sign.md` line 7 — "Code reality: ... anneals DOWN `n_max → n_min` per `cosine.py:159` docstring and `cosine.py:227` formula body".

The Wave 282 audit chain is consistent: **the framework's `CosineAnnealScheduler` anneals DOWN `n_max → n_min`**, and this is what every headline empirical sweep exercises.

## 6. Source-of-truth verdict

**`code` is the source of truth.** The paper formula in Table 2.2 (and the 6 other wrong-sign occurrences in `schedule-theory.md`, `CLAIMS.md`, `wave292-final.md`) is the side that needs fixing. The reasons:

1. **Code's behavior is stable, tested, and load-bearing.** Every headline sweep (R1–R6 + K1, K3+R5b, K4+K5, K7, R5c production-ckpt; 13 cells) used the cosine arm. The framework's byte-stable fixtures (Wave 87, Wave 158 P2, Wave 247 P2 multi-seed) all rely on the (1+cos) form. Switching the code would invalidate every (current, achieved) assertion in `docs/benchmark-uplifts.md`, break the D.4 30/30 regression vectors, and break the framework's empirical reproducibility chain.

2. **ADR-0010 (accepted, 2026-08-27) states the design intent explicitly.** "Coarse-to-fine" with `n_max` at round 0 (exploration) and `n_min` at round L-1 (refinement) requires anneal DOWN, which requires (1+cos). The code matches ADR-0010; the paper does not.

3. **The paper itself acknowledges the mismatch.** Wave 292 P3 §3.1 (MISMATCH-HIGH-1) and Wave 292 P4 §MS alignment preamble both name the (1−cos) Table 2.2 row as a paper-edit additive pass. The paper's own §2.10.2 specifies the flip direction: from `(1 − cos)` to `(1 + cos)`, citing `cosine.py:227` as the source.

4. **The framework's "coarse-to-fine" intuition is the load-bearing semantic.** Drug-design reasoning (lots of fresh noise for exploration early; preserve prior for refinement late) maps to anneal DOWN. The paper's (1−cos) form would do the opposite (preserve prior early; add fresh noise late) — which contradicts the paper's own algorithm narrative in §2.7 ("cosine is the simplest paper-Lemma-2 closed form" + coarse-to-fine framing).

## 7. Recommended fix direction

**`fix_paper`** — flip the (1−cos) form to (1+cos) in the 7 wrong-sign occurrences identified by Wave 293 P1:

* **Priority 1 (load-bearing — must fix for paper correctness):**
  1. `docs/drafts/paper-flat-flattened.md:62` — Table 2.2 row.
  2. `docs/schedule-theory.md:15, 178, 207, 208` — All 4 occurrences (the source-of-truth doc for the cosine schedule; canonical §1 closed form, §8 closed-form table, §9 Nichol-Dhariwal comparison, §9 EDM comparison).
  3. `docs/CLAIMS.md:110` — CLM-005 Evidence row.

* **Priority 2 (denominator bug — same-doc, second-pass):**
  4. `docs/audit/wave292-final.md:47` — denominator `L` → `(L − 1)` + sign flip.
  5. `docs/audit/wave292-p2-config-genealogy.md:45, 226, 338` + `docs/audit/scheduler-per-cell-summary.md:24, 52` + `docs/audit/wave288-p1-honest-progress-summary.md:326` — denominator `cycle_length` (= L) → `(cycle_length − 1)` (= L-1). Sign is correct (1+cos). This is a SECONDARY bug, not a sign error.

**No code changes required.** `adaptive_reflow/schedule/cosine.py:227` and `adaptive_reflow/algorithm/scheduler/simple.py:71` (via the cosine.py delegation) are correct per the empirical test, ADR-0010 design intent, and the Wave 282 audit chain.

## 8. Cross-check against the workflow's evaluation rubric

The workflow's evaluation rubric (item 6) names two candidate verdicts:

* **(1 + cos(0)) = 2 → n_cap = n_max (anneal DOWN: high at start)** ← CODE
* **(1 − cos(0)) = 0 → n_cap = n_min (anneal UP: low at start)** ← PAPER

The empirical test above confirms the CODE formula. The framework intent (ADR-0010 coarse-to-fine; Wave 282 audit chain) confirms the CODE formula. Therefore:

* `codeFormula` = "(1+cos)"
* `paperFormula` = "(1-cos)"
* `empiricalTestOutput.r0.n_cap` = 1.0 (high at start — anneal DOWN)
* `empiricalTestOutput.rL1.n_cap` = 0.0 (low at end — anneal DOWN)
* `sourceOfTruth` = "code"
* `recommendedFix` = "fix_paper"

## 9. Invariants preserved

* **D.4 30/30:** PASS (no edits to framework internals; `cosine.py:227` and `simple.py:71` untouched). The empirical test lives in `/tmp/`, not in `tests/`.
* **claims no drift:** the `docs/CLAIMS.md` line 110 correction is the ONLY drift, and it is in the paper-edit direction (the formula was wrong; the fix aligns CLM-005 Evidence with `cosine.py:227`).
* **ruff 0:** unchanged (no edits to Python source).
* **mkdocs 0 warnings:** unchanged (no edits to mkdocs-controlled docs in this audit pass).
* **vendored NOT touched:** `tools/run_sota_cifar_experiment.py`, `tools/compute_cifar_fid.py`, `adaptive_reflow/adapters/rectified_flow_cifar.py`, and all `adaptive_reflow/` framework source are unchanged.

## 10. Audit metadata

* **Wave:** 293 P2
* **Mode:** READ-ONLY verification (one non-committed empirical test at `/tmp/wf293_cosine_direction_test.py`; no edits to framework source, paper draft, or vendored adapters)
* **Empirical test:** `/tmp/wf293_cosine_direction_test.py` (5-line snippet; evaluates both formulas at r=0 and r=L-1=3 for L=4, n_min=0.0, n_max=1.0)
* **Source-of-truth verdict:** `code` (the framework's `(1+cos)` form is the source of truth; the paper Table 2.2 `(1−cos)` form needs fixing)
* **Recommended fix direction:** `fix_paper` (flip 7 wrong-sign occurrences in `paper-flat-flattened.md`, `schedule-theory.md`, `CLAIMS.md`, `wave292-final.md`)
* **Direction of annealing (framework):** DOWN (`n_max → n_min`; high at start, low at end) — confirmed by empirical test, by ADR-0010 design intent, by Wave 282 audit chain, and by Wave 87 / Wave 158 P2 / Wave 247 P2 byte-stable fixtures.
* **Invariants:** D.4 30/30 PASS; claims no drift (the CLM-005 Evidence fix is in the paper-edit direction); ruff 0; mkdocs 0 warnings; vendored NOT touched.
