# Wave 293 P1 — CosineScheduler sign-error location audit

**Date:** 2026-09-23
**Scope:** locate ALL occurrences of the `CosineAnnealScheduler` closed-form formula in the paper draft and related docs to determine the full extent of the `(1 − cos)` vs `(1 + cos)` sign error.
**Mode:** READ-ONLY audit. No code edits. No paper edits. No commits.
**Reference:** `docs/audit/wave292-p3-crosscheck.md` §3.1 MISMATCH-HIGH-1 (the paper Table 2.2 row reads `(1 − cos(π r / (L − 1)))` but the code at `adaptive_reflow/schedule/cosine.py:227` uses `(1 + cos(π r / (L − 1)))`).
**Code reality:** `n_cap = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2` where `u_r = r / (L - 1)` — anneals DOWN `n_max → n_min` per `cosine.py:159` docstring and `cosine.py:227` formula body.

---

## 1. Scope boundary

This audit covers the `CosineAnnealScheduler` family closed-form
`n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 ± cos(π r / (L − 1)))`.
The `HandoffSequentialScheduler` blending factor
`α = 0.5 · (1 − cos(π · progress))` is a DIFFERENT mathematical formula
(a blending weight that runs 0 → 1 across slot boundaries; semantically
correct for that purpose) and is listed separately in §6 below for
completeness but is NOT counted as part of the `CosineAnnealScheduler`
sign-error inventory.

---

## 2. Per-file occurrence table

### 2.1 `docs/drafts/paper-flat-flattened.md` (primary target)

| # | Line | Exact formula | Sign convention | Verdict |
|---:|---:|---|---|---|
| 1 | 36 | `n_cap(r) = n_min + (n_max − n_min) · 0.5 · (1 + cos(π r / (L − 1)))` | (1+cos) ✓ | MATCH — §MS alignment preamble correctly transcribes the code |
| 2 | 62 | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / (L − 1)))` | (1−cos) ✗ | **WRONG** — Table 2.2 row `CosineAnnealScheduler` |
| 3 | 151 | `n_cap = n_min + (n_max − n_min) · 0.5 · (1 + cos(π r / (L − 1)))` | (1+cos) ✓ | MATCH — §2.8 "site 1 reading" |
| 4 | 176 | `n_cap = n_min + (n_max − n_min) · 0.5 · (1 + cos(π r / (L − 1)))` | (1+cos) ✓ | MATCH — §2.9 "Common pattern (12/13 cells)" |
| 5 | 200 | `n_cap = n_min + (n_max - n_min) · (1 + cos(π · u_r)) / 2` (describes code actual) | (1+cos) ✓ | MATCH — Table 2.10.2 M-HIGH-1 mismatch description correctly quotes the code |

### 2.2 `README.md`

| # | Line | Exact formula | Verdict |
|---:|---:|---|---|
| — | — | No `(1 ± cos(π r / (L − 1)))` closed-form found in README.md (lines 13, 24, 109, 208 mention `CosineAnnealScheduler` by name but no formula transcribed) | N/A |

### 2.3 `README.zh.md`

| # | Line | Exact formula | Verdict |
|---:|---:|---|---|
| — | — | No `(1 ± cos(π r / (L − 1)))` closed-form found in README.zh.md (lines 13, 15, 98, 197 mention `CosineAnnealScheduler` by name but no formula transcribed) | N/A |

### 2.4 `docs/CLAIMS.md`

| # | Line | Exact formula | Sign convention | Verdict |
|---:|---:|---|---|---|
| 1 | 110 | ``n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))`` | (1−cos) ✗ | **WRONG** — CLM-005 Evidence row transcribes the WRONG closed form (inconsistent with code at `adaptive_reflow/algorithm/scheduler/_core.py:347` which actually uses the (1+cos) form per Wave 87 byte-stable fixtures; the citation points at the right line but the formula on line 110 has the wrong sign) |

### 2.5 `docs/METRIC_LEDGER.md`

| # | Line | Exact formula | Verdict |
|---:|---:|---|---|
| — | — | No `(1 ± cos(π r / (L − 1)))` closed-form found in METRIC_LEDGER.md (lines 41, 54, 89–102, 121, 140, 154, 185, 192, 194, 196, 197 mention `CosineAnnealScheduler` by name but no formula transcribed) | N/A |

### 2.6 Other docs found with the `CosineAnnealScheduler` formula (related-source docs)

| # | File | Line | Exact formula | Sign convention | Verdict |
|---:|---|---:|---|---|---|
| 1 | `docs/schedule-theory.md` | 15 | ``n_cap(r) = n_min + (n_max − n_min) · (1 − cos(π · r / (L − 1))) / 2`` | (1−cos) ✗ | **WRONG** — primary source-of-truth doc for the cosine schedule (the canonical closed-form §1); the source-of-truth doc carries the wrong sign, which means EVERY downstream cross-reference (Nichol-Dhariwal comparison §2, EDM comparison §3, the 9-family closed-form table §8) propagates the wrong sign |
| 2 | `docs/schedule-theory.md` | 178 | ``n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))`` | (1−cos) ✗ | **WRONG** — §8 closed-form table row |
| 3 | `docs/schedule-theory.md` | 207 | ``n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))`` | (1−cos) ✗ | **WRONG** — §9 Nichol-Dhariwal comparison (same formula as the framework's "identical" analog) |
| 4 | `docs/schedule-theory.md` | 208 | ``n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))`` | (1−cos) ✗ | **WRONG** — §9 EDM comparison |
| 5 | `docs/audit/wave292-final.md` | 47 | ``n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / L))`` | (1−cos) ✗ | **WRONG** — also has a SECONDARY bug: denominator is `L` instead of `(L − 1)` (the cosine.py code uses `(L − 1)` for `u_r = r / (L - 1)`) |
| 6 | `docs/audit/wave292-final.md` | 54 | ``n_cap(r) = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH — same doc, correct form |
| 7 | `docs/audit/EPSILON_DIRECTION.md` | 113 | ``n_cap(r) = n_min + (n_max - n_min) * (1 + cos(pi * r / (L - 1))) / 2`` | (1+cos) ✓ | MATCH |
| 8 | `docs/audit/wave292-p1-pipeline-inventory.md` | 57 | ``n_cap(r) = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2`` | (1+cos) ✓ | MATCH |
| 9 | `docs/audit/wave275-p4-cifar10-proposal.md` | 112 | ``n_cap(r) = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / (n_rounds - 1)))`` | (1+cos) ✓ | MATCH |
| 10 | `docs/audit/wave275-p4-cifar10-proposal.md` | 336 | ``n_cap_for_round(r) = 0.5 + 0.5 * 0.5 * (1 + cos(pi * r / (cycle_length - 1)))`` | (1+cos) ✓ | MATCH |
| 11 | `docs/audit/wave292-p2-config-genealogy.md` | 45 | ``n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH (note: denominator is `cycle_length`, not `(cycle_length − 1)` — this is a SECONDARY bug: code uses `r / (L - 1)` but the doc says `r / cycle_length`; per cycle_length = L they coincide only when L=1; at L=2 the doc says r/2 = 0.5 at the midpoint, but code says r/(L-1) = r/1 = 0 at r=0 and 1 at r=L-1) |
| 12 | `docs/audit/wave292-p2-config-genealogy.md` | 226 | ``n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH (same `r / cycle_length` denominator caveat as line 45) |
| 13 | `docs/audit/wave292-p2-config-genealogy.md` | 338 | ``n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH (same denominator caveat) |
| 14 | `docs/audit/scheduler-per-cell-summary.md` | 24 | ``n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH (denominator caveat) |
| 15 | `docs/audit/scheduler-per-cell-summary.md` | 52 | ``n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH (denominator caveat) |
| 16 | `docs/audit/wave288-p1-honest-progress-summary.md` | 326 | ``n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH (denominator caveat) |
| 17 | `docs/audit/wave292-p3-crosscheck.md` | 64 | ``n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / (L − 1)))`` | (1−cos) ✗ (paper claim) | **NOT A BUG** — correctly quotes the paper's WRONG claim; correctly identifies the sign as a MISMATCH in the adjacent verdict column |
| 18 | `docs/audit/wave292-p3-crosscheck.md` | 81 | n/a — `HandoffSequentialScheduler` formula (see §6 below) | N/A | N/A |
| 19 | `docs/audit/wave292-p3-crosscheck.md` | 131 | ``n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / (L − 1)))`` | (1−cos) ✗ (paper claim) | **NOT A BUG** — paper claim quoted inside §3.1 MISMATCH-HIGH-1 box |
| 20 | `docs/audit/wave292-p3-crosscheck.md` | 134 | ``n_cap = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2`` | (1+cos) ✓ | MATCH — code actual quoted |
| 21 | `docs/audit/wave292-p3-crosscheck.md` | 155 | ``(1 − cos(π r / (L − 1)))`` → ``(1 + cos(π r / (L − 1)))`` | (1−cos → 1+cos) | **NOT A BUG** — paper-edit recommendation correctly identifies the flip direction |
| 22 | `docs/audit/wave292-p3-crosscheck.md` | 180 | ``n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`` | (1+cos) ✓ | MATCH (denominator caveat) |
| 23 | `docs/audit/wave292-p3-crosscheck.md` | 360 | ``(1 + cos(π r / (L − 1)))`` | (1+cos) ✓ | MATCH — code-edit recommendation correctly identifies the flip direction |

---

## 3. Aggregate count

| Bucket | Count |
|---|---:|
| Total `CosineAnnealScheduler` closed-form occurrences (excluding `HandoffSequentialScheduler` blending factor) | **28** |
| Wrong sign (1−cos) — total occurrences of the (1−cos) form | **9** |
| └─ Of which: bugs that need fixing (paper Table 2.2 + downstream propagations) | **7** |
| └─ Of which: audit-narrative quotes in `wave292-p3-crosscheck.md` that intentionally quote the wrong paper claim (lines 64, 131) | **2** |
| Correct sign (1+cos) | **19** |
| `HandoffSequentialScheduler` blending factor (separate formula; not part of the sign error) | 1 (correct for its purpose, listed in §6 below) |
| Files searched with no occurrences | 3 (`README.md`, `README.zh.md`, `docs/METRIC_LEDGER.md`) |

---

## 4. Per-file breakdown (sign-error count)

| File | Total occurrences | Wrong sign (1−cos) | Correct sign (1+cos) | Notes |
|---|---:|---:|---:|---|
| `docs/drafts/paper-flat-flattened.md` | 5 | 1 (line 62) | 4 (lines 36, 151, 176, 200) | The single WRONG line is Table 2.2 — the load-bearing "official" closed form. The other 4 lines correctly use (1+cos). |
| `README.md` | 0 | 0 | 0 | No formula transcribed |
| `README.zh.md` | 0 | 0 | 0 | No formula transcribed |
| `docs/CLAIMS.md` | 1 | 1 (line 110) | 0 | The CLM-005 Evidence row transcribes the wrong formula in line with the Table 2.2 error; this is the same Wave 286 P / Wave 87 era mistake propagated forward |
| `docs/METRIC_LEDGER.md` | 0 | 0 | 0 | No formula transcribed |
| `docs/schedule-theory.md` | 4 | 4 (lines 15, 178, 207, 208) | 0 | **ENTIRELY WRONG** — the source-of-truth doc for the cosine schedule carries the wrong sign on all 4 occurrences (the canonical §1 closed form, the §8 closed-form table row, the §9 Nichol-Dhariwal comparison, and the §9 EDM comparison). This is the most load-bearing document to fix because every downstream cross-reference propagates from here. |
| `docs/audit/wave292-final.md` | 2 | 1 (line 47) | 1 (line 54) | Line 47 also has a SECONDARY bug: denominator is `L` instead of `(L − 1)` |
| `docs/audit/EPSILON_DIRECTION.md` | 1 | 0 | 1 | Correct |
| `docs/audit/wave292-p1-pipeline-inventory.md` | 1 | 0 | 1 | Correct |
| `docs/audit/wave275-p4-cifar10-proposal.md` | 2 | 0 | 2 | Correct |
| `docs/audit/wave292-p2-config-genealogy.md` | 3 | 0 | 3 | All (1+cos); SECONDARY bug: denominator is `cycle_length` (= L), not `(cycle_length − 1)` (= L-1). At cycle_length=2 the code uses `r / (L-1) = r / 1 ∈ {0, 1}` but the doc says `r / cycle_length = r / 2 ∈ {0, 0.5}`. This is a separate Wave 293 P2 secondary bug. |
| `docs/audit/scheduler-per-cell-summary.md` | 2 | 0 | 2 | Correct (with denominator caveat) |
| `docs/audit/wave288-p1-honest-progress-summary.md` | 1 | 0 | 1 | Correct (with denominator caveat) |
| `docs/audit/wave292-p3-crosscheck.md` | 6 | 2 (lines 64, 131) | 4 (lines 134, 155, 180, 360) | Lines 64 and 131 are paper-claim quotes inside the MISMATCH-HIGH-1 box — they are CORRECTLY QUOTED (as the WRONG paper claim); lines 134, 155, 180, 360 correctly use (1+cos). (Plus line 81 is the `HandoffSequentialScheduler` N/A blending factor, counted in §6 below.) |
| **TOTAL** | **28** | **9** | **19** | (7 WRONG occurrences need fixing; of these 7, 4 are in `docs/schedule-theory.md` and 1 each in `paper-flat-flattened.md`, `CLAIMS.md`, `wave292-final.md`; the remaining 2 (1−cos) occurrences are in `wave292-p3-crosscheck.md` lines 64, 131 which are audit-narrative quotes of the wrong paper claim.) |

### Per-file occurrence map (for the structured-output's `byFile` field)

| Bucket | Count |
|---|---:|
| paper (`docs/drafts/paper-flat-flattened.md`) | 5 |
| readme (`README.md` + `README.zh.md`) | 0 |
| claims (`docs/CLAIMS.md`) | 1 |
| ledger (`docs/METRIC_LEDGER.md`) | 0 |
| other (audit docs + `schedule-theory.md`) | 22 |
| **TOTAL** | **28** |

---

## 5. Recommendation — which files to fix

### Priority 1 (load-bearing — must fix for paper correctness)

1. **`docs/drafts/paper-flat-flattened.md:62`** — Table 2.2 row. Flip `(1 − cos(π r / (L − 1)))` → `(1 + cos(π r / (L − 1)))`. This is the paper's official closed-form claim. (Per Wave 292 P3 §3.1 recommendation, already on the Wave 293+ additive pass.)

2. **`docs/schedule-theory.md:15, 178, 207, 208`** — All 4 occurrences are (1−cos). This is the **single most load-bearing document** to fix because:
   - It is the source-of-truth doc for the cosine schedule family
   - The §1 closed form is the canonical reference
   - The §9 "Nichol-Dhariwal cosine" comparison says the framework formula is **identical** to Nichol-Dhariwal's at the functional level — but Nichol-Dhariwal's noise-rate `β_diff(t) = 1 − ᾱ(t)/ᾱ(t−1)` with `ᾱ(t) = cos²((t/T + s)/(1+s) · π/2)` MONOTONE-DECREASES (anneals DOWN), matching the (1+cos) form. So the §9 "Yes (functional form: half-cosine scaled into [0,1]; offset s = 0)" claim is also wrong when the doc transcribes the framework's (1−cos) form as "identical to Nichol-Dhariwal" — Nichol-Dhariwal's framework and the framework's actual code both anneal DOWN, but the doc's stated form anneals UP.
   - All 4 lines must flip to (1+cos).

3. **`docs/CLAIMS.md:110`** — CLM-005 Evidence row. Flip (1−cos) → (1+cos). The citation points at `adaptive_reflow/algorithm/scheduler/_core.py:347` (a class declaration line, not a formula line), and the actual code uses (1+cos) per `cosine.py:159` docstring + `cosine.py:227` formula body + Wave 87 byte-stable test fixtures. The transcribed formula on line 110 contradicts all three.

### Priority 2 (denominator bug — same-doc, second-pass)

4. **`docs/audit/wave292-final.md:47`** — Denominator is `L`, should be `(L − 1)` (matches `u_r = r / (L − 1)` per `cosine.py:219`). Also flip (1−cos) → (1+cos).

5. **`docs/audit/wave292-p2-config-genealogy.md:45, 226, 338`** and **`docs/audit/scheduler-per-cell-summary.md:24, 52`** and **`docs/audit/wave288-p1-honest-progress-summary.md:326`** — Denominator is `cycle_length` (= L), should be `(cycle_length − 1)` (= L-1). Sign is correct (1+cos). This is a SECONDARY bug, not a sign error. Flag for a separate Wave 293 P2 pass.

### Priority 3 (no action — already correct or correctly quoted as wrong)

- `docs/audit/wave292-p3-crosscheck.md:64, 131, 134, 155, 180, 360` — All correctly quote either the paper's WRONG claim (inside the MISMATCH-HIGH-1 box) or the code's CORRECT closed form. No changes required.

### N/A (no formula transcribed)

- `README.md`, `README.zh.md`, `docs/METRIC_LEDGER.md` — no `n_cap(r) = ...` closed-form found; only `CosineAnnealScheduler` by-name references. No changes required.

---

## 6. Separate formula — `HandoffSequentialScheduler` blending factor (NOT a sign error)

For completeness, the paper's Table 2.3 also transcribes the `HandoffSequentialScheduler` blending factor
`α = 0.5 · (1 − cos(π · progress))` (paper line 80) where `progress ∈ [0, 1]` over `handoff_window` rounds.

This formula uses (1−cos) **deliberately** and the (1−cos) form is CORRECT for the blending-factor semantics:
- `progress = 0` → `α = 0` → `n_cap = n_cap_a` (stay at outgoing slot)
- `progress = 1` → `α = 1` → `n_cap = n_cap_b` (go to incoming slot)
- The blending weight ramps UP from 0 to 1 across the handoff window

The `HandoffSequentialScheduler` formula is therefore NOT the same cosine scheduler formula as the
`CosineAnnealScheduler` noise-capacity formula; they are different mathematical objects with different
sign conventions serving different purposes. **The Wave 293 paper-edit pass should NOT touch the
`HandoffSequentialScheduler` blending factor.**

| # | File | Line | Formula | Verdict |
|---:|---|---:|---|---|
| 1 | `docs/drafts/paper-flat-flattened.md` | 80 | `α = 0.5 · (1 − cos(π · progress))` | CORRECT — blending factor semantics |
| 2 | `docs/audit/wave292-p3-crosscheck.md` | 81 | `α = 0.5 · (1 − cos(π · progress))` | CORRECT (paper claim) |
| 3 | `docs/audit/wave292-p3-crosscheck.md` | 81 | `alpha = 0.5 * (1.0 - math.cos(math.pi * progress))` | CORRECT (code actual) |

---

## 7. Reading the inventory

The cosine sign error is **structurally larger than just Table 2.2** — it spans **7 occurrences that need fixing across 4 files** (`paper-flat-flattened.md`, `CLAIMS.md`, `schedule-theory.md`, `wave292-final.md`) and the **most load-bearing source** is `docs/schedule-theory.md` (4 of the 7 wrong-sign occurrences; the source-of-truth doc for the cosine schedule family).

The sign error is also **NOT a Wave 292 P3 finding in isolation** — it was already present in
`docs/schedule-theory.md` (the doc §1 line 15 carries the wrong sign, and this doc is the framework's
canonical schedule-theory reference; the Wave 282 scheduler-per-cell-summary and the Wave 286 P / Wave 87
byte-stable tests all use the correct (1+cos) form). The wrong sign in `docs/schedule-theory.md` is the
**upstream propagation source** that Table 2.2 and the CLM-005 evidence row copied from.

The (1+cos) form (correct) is everywhere in the empirical-side audit docs (Wave 275 P4, Wave 286 P,
Wave 288 P1, Wave 291 P5, Wave 292 P1 + P2, EPSILON_DIRECTION, scheduler-per-cell-summary). The empirical
community has the correct formula; the paper-side and the source-of-truth docs (`schedule-theory.md`,
Table 2.2, CLM-005 evidence) have the wrong formula.

The fix list is **7 line edits across 4 files** for the sign error alone, plus a secondary 6-line denominator
fix across 4 files for the `r / cycle_length` vs `r / (cycle_length − 1)` distinction (separate Wave 293
P2 secondary-bug pass recommended).

---

## 8. Audit metadata

- **Wave:** 293 P1
- **Mode:** READ-ONLY audit (no code edits, no paper edits, no commits)
- **Files audited:** `docs/drafts/paper-flat-flattened.md`, `README.md`, `README.zh.md`, `docs/CLAIMS.md`,
  `docs/METRIC_LEDGER.md`, plus 9 related-source docs (`docs/schedule-theory.md`,
  `docs/audit/wave292-p3-crosscheck.md`, `docs/audit/wave292-p2-config-genealogy.md`,
  `docs/audit/wave292-p1-pipeline-inventory.md`, `docs/audit/wave292-final.md`,
  `docs/audit/wave275-p4-cifar10-proposal.md`, `docs/audit/wave288-p1-honest-progress-summary.md`,
  `docs/audit/scheduler-per-cell-summary.md`, `docs/audit/EPSILON_DIRECTION.md`)
- **Code citation:** `adaptive_reflow/schedule/cosine.py:159` (docstring), `:227` (formula body), `:219` (`u_r = r / (L - 1)`)
- **Reference:** `docs/audit/wave292-p3-crosscheck.md` §3.1 MISMATCH-HIGH-1 (the original Wave 292 P3 cross-check that identified the Table 2.2 sign mismatch)
- **Invariants:** vendored NOT touched (no edits to vendored adapters or any framework source); claims no drift (no edits to CLAIMS.md or METRIC_LEDGER.md in this audit pass); ruff 0 / mkdocs 0 unchanged.