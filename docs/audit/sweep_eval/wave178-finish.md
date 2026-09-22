# Wave 178 — finish-line audit doc (companion to P7 paper §10.24 + §15.75 + §R.66)

**Date:** 2026-09-17
**Branch:** main (HEAD `3f1a551`, post-Wave 178 P2-P6)
**Scope:** Final audit doc for Wave 178 — paper finalization, gates
verify, and push to `origin/main`. This is the Wave 178 equivalent of
the Wave 175 P6 finish-line audit doc (`docs/audit/wave175-finish.md`)
and the Wave 177 audit doc (`docs/audit/wave177-shape-composite-fixes.md`).

---

## 1. Wave 178 commit chain (P1 → P6)

| # | Commit | Subject |
|---|--------|---------|
| P1 | `28ccc78` | Wave 178 P1: kanzi real arch redesign design audit (trajectory in `(L, 3)` coord space throughout) |
| P2 | `3675a89` | Wave 178 P2: `_real_state_shape` returns `(L_abstract, 3)` in real mode — trajectory in coord space; D.4 33/33 preserved |
| P3 | `de2d4bd` | Wave 178 P3: `build_initial_state` initializes `x0` as `(L, 3)` in real mode (synthetic mode unchanged for D.4 preservation) |
| P4 | `98594bc` | Wave 178 P4: `velocity_field` bridge + padding code paths now no-op for real mode (`state_shape = (L, 3)`); source unchanged if dead-code verification passes |
| P6 | `3f1a551` | Wave 178 P6: kanzi real ckpt end-to-end eval N=10 × 6 cells (NFE=50/100/200, baseline/framework) |

P5 (gates verify, no source change) is captured at commit `98594bc`
(gates re-verified post-P4).

## 2. Wave 178 P7 paper additions (this commit)

1. `docs/paper-draft.md` — new §10.24 "Kanzi real ckpt architecture
   redesign (Wave 178 — ADDITIVE on §10.20/§10.21/§10.22/§10.23;
   supersedes nothing)" between §10.23 and §11. Six subsections (a)-(g)
   covering: root cause, P2/P3/P4/P6 commits, honest verdict, and
   acceptance gates.
2. `docs/CONSOLIDATED_RESULTS.md` — new §15.75 "Wave 178 Kanzi real ckpt
   architecture redesign + N=10 × 6 cells e2e eval (2026-09-17)" with
   full per-cell pLDDT + scPerplexity numbers + verdict + acceptance
   gates + ADDITIVE-only disclosure.
3. `docs/baseline-audit-report.md` — new §R.66 "Wave 178 Kanzi real ckpt
   architecture redesign + N=10 × 6 cells e2e eval (2026-09-17)" with
   same disclosure as §15.75.
4. `docs/audit/wave178-finish.md` — this audit doc.

## 3. Gates (verified at P5 commit `98594bc`, all preserved at P6 + P7)

| # | Gate | Command | Result |
|---|------|---------|--------|
| 1 | D.4 byte-stable regression vectors | `python -m pytest tests/ -k "d4" -q` | **33 passed, 30 skipped, 5028 deselected** (D.4 33/33 PASS) |
| 2 | Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **All checks passed!** (ruff 0 across 4 dirs) |
| 3 | Claims consistency | `python tools/check_claims_consistency.py` | **No drift detected.** (39 active, 0 provisional, 2 deprecated) |
| 4 | mkdocs strict build | `mkdocs build --strict` | **PRE-EXISTING FAILURE** (28 un-included files; unrelated to Wave 178) |
| 5 | Wave 178 P6 e2e | 6 cells exit=0 in 222 s wall | **All 6 cells PASS** (per-cell mean 37.0 s, max 42 s, all <2 min) |

Gates 1, 2, 3, 5 are PASS. Gate 4 is a pre-existing failure
unrelated to Wave 178 (the `mkdocs.yml` `not_in_nav` allowlist does
not include 28 pre-existing files); out of scope for Wave 178.

## 4. Wave 178 verdict (one-line)

Kanzi real ckpt integration now **runs end-to-end at <2 min/cell**
(was 12+ min blocked), with framework wins on scPerp at all 3 NFEs
and wins on pLDDT at 2/3 NFEs. **R6 cross-model claim now spans real
ckpts** (was synthetic-only in §10.20-§10.23). The Wave 175 P5
escalation path option (3) "use the kanzi real ckpt instead of
synthetic mode" is now unblocked and load-bearing for any Wave 178+
escalation of the kanzi synthetic-mode pLDDT trade-off.

## 5. ADDITIVE-only disclosure (no prior §10/§15/§R rewritten)

Wave 178 P7 §10.24 + §15.75 + §R.66 are ADDITIVE on §10.20/§10.21/
§10.22/§10.23 + §15.63-§15.74 + §R.54-§R.65. The §10.20
model-asymmetric narrative + §10.21 per-adapter NFE_REF + §10.22
primary-metric saturation + §10.23 Wave 177 shape fix + lineageflow
synthetic composite cleanup are all preserved verbatim. The
honest-negative trail documenting the diagnostic progression
(kanzi regression root-cause → per-adapter NFE_REF fix →
mechanism-byte-stability-discovery → kanzi-N=30-eval →
lineageflow-regression-check → saturation-discovery →
shape-redesign-design → shape-redesign-impl →
shape-redesign-verify → kanzi-real-ckpt-e2e) is preserved.

## 6. Push plan

After the P7 commit lands:
- `git push origin main` — pushes all 6 Wave 178 commits
  (P1 `28ccc78` → P6 `3f1a551`) plus the P7 paper-finalization
  commit to `origin/main`.
- 0 unpushed commits after push.
- Verification: `git log --oneline origin/main..main` → empty.

## 7. Files modified by P7 (this commit)

- `docs/paper-draft.md` (+~176 lines: §10.24)
- `docs/CONSOLIDATED_RESULTS.md` (+~108 lines: §15.75)
- `docs/baseline-audit-report.md` (+~113 lines: §R.66)
- `docs/audit/wave178-finish.md` (new, this file)

## 8. References

* Wave 178 P1 audit: `docs/audit/wave178-p1-design.md`
* Wave 178 P2 audit: `docs/audit/wave178-p2-real-state-shape.md`
* Wave 178 P3 audit: `docs/audit/wave178-p3-build-initial-state.md`
* Wave 178 P4 audit: `docs/audit/wave178-p4-velocity-field-noop.md`
* Wave 178 P5 audit: `docs/audit/wave178-p5-gates.md`
* Wave 178 P6 audit: `docs/audit/wave178-p6-e2e-eval.md`
* Wave 175 finish-line audit: `docs/audit/wave175-finish.md`
* Wave 177 audit: `docs/audit/wave177-shape-composite-fixes.md`
* Paper §10.20-§10.23: ADDITIVE predecessors
* Paper §15.63-§15.74: ADDITIVE predecessors
* Baseline audit §R.54-§R.65: ADDITIVE predecessors
