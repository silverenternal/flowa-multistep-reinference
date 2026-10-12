# Governance-surface reset — retire `todo/`, single-source `todo.json`

**Date:** 2026-10-13
**Branch:** main
**Base commit:** `1264cec`
**Scope:** replace the legacy governance surface (repo-root `todo.json` + the entire `todo/` directory) with one current-state `todo.json`; record the D-004b R1 result in the same change.
**Directive:** user — "写一份新的 todo.json（老的 todo.json 包括 todo 目录都删掉好了，没关系的）".

---

## 1. Observed facts

**Removed** (user-authorized, 13 files):

- repo-root `todo.json` (old schema `wave11_audit_fixes_v1`, 20 legacy tasks + wave summaries)
- `todo/`: `decisions.md`, `GATES.md`, `INDEX.md`, `lessons-learned.md`, `LOOP.md`, `PUSH-READY.md`, `README.md`, `RISK-REGISTER.md`, `STATUS.md`, `SUBMISSION-GAP-CHECKLIST.md`, `TIMELINE.md`, `TPAMI-6-WEEK-PLAN.md`, `WAVES.md`

**Created** — a single machine-readable management surface, `todo.json` (schema `flowa-state-v2`):

| Section | Content |
|---|---|
| `policy` | NO-PUSH, frozen surfaces, additive rule, the binding gate chain |
| `gates` | current gate readings (D.4 30/30, ruff 0, mkdocs strict 0, claims no drift, readiness `READY_WITH_SKIPS: mypy_0`) |
| `manuscript` / `venue` | title, artifacts, TNNLS target + backups |
| `evidence_ledger` | the 11 R/K cells with their current verdicts (verbatim from paper §7.2/§7.11) |
| `lineageflow_real_forward` | the D-004 / D-004b saga (defect → fix → re-measure → caveat) |
| `open_gaps` / `resolved_gaps` | the P0/P1/P2 Tier-1 gaps, updated |
| `assessment` | the honest one-screen Tier-1 assessment (strong axes, gating risks, decision variables) |
| `recommended_attack_order` | ordered next steps |
| `removed_surfaces` | what was deleted and the known dangling references |

**Repaired references** (live surfaces, not frozen):

- `docs/README.md` — 5 pointers to `../todo/WAVES.md` / `../todo/` repointed to `../todo.json`.
- `docs/RELEASE-NOTES.md` — gate-state pointer repointed to `todo.json`.

**Recorded in the same change** — the D-004b R1 3-seed re-measure (see §3).

---

## 2. Known dangling references (left, deliberately)

- `docs/drafts/paper-A-final.md:842` links `todo/RISK-REGISTER.md` R-019 (a GitHub blob URL). The manuscript is a **frozen surface** (AGENTS.md §3 guardrail #5); it is **not** edited here. The link will 404 once the deletion is pushed. Flagged in `todo.json` → `removed_surfaces.known_dangling_references`.

No other live surface references the deleted tree. Historical audit docs under `docs/audit/` mention `todo/` paths in prose; they are historical records, are not part of the mkdocs nav, and are not gate-checked.

---

## 3. D-004b result recorded here

The background R1-REMEASURE-D004b run completed: 3 seeds × N=1000 × 2 arms on the genuine real-forward basis with the D-004b per-record stochastic restart init.

| seed | baseline | framework | Δ |
|---:|---:|---:|---:|
| 42 | 158 | 275 | +117 |
| 43 | 159 | 272 | +113 |
| 44 | 174 | 259 | +85 |

3/3 direction-consistent framework-WINS; seed-level $d_z = +6.02$; DL meta $d_\text{pooled} = +0.1559$, $z = 8.49$, $I^2 = 0$, Bonferroni-significant at $k=7$. This **reverses** the D-004 zero-collapse ($d_\text{pooled} = -0.4013$). Full write-up: [`r1-d004b-remeasure.md`](r1-d004b-remeasure.md); evidence: `verification_outputs/r1_3seed_d004b_q4_2026/`.

**Caveat carried:** the D-004b restart init is a tool-convention surrogate, not the upstream intervention sampler; the init-only vs full-framework attribution control is not yet run (`D-004B-ATTRIBUTION` in `todo.json`).

---

## 4. Verification

| Gate | Result |
|---|---|
| `python tools/check_claims_consistency.py` | No drift detected |
| `python tools/check_docs_against_code.py` | 4143/4144 OK — the 1 miss (`CLAIMS.md:3038` `R2_kanzi_rmsd`) is **pre-existing** (reproduces at HEAD with `todo/` intact); a checker false-positive, not caused by this change |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed |
| `pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `mkdocs build --strict` | exit 0, no warnings |
| `python tools/verify_submission_readiness.py` | `READY_WITH_SKIPS: mypy_0`, exit 0 |
| `sha256sum --check` (D-004b evidence dir) | 11/11 OK |
| `json.load(todo.json)` | valid |

---

## 5. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ no frozen number/label rewritten; `todo.json` is the single new surface |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ the D-004b caveat + the pre-existing checker failure are disclosed |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved; the frozen manuscript link is flagged, not edited |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ one management surface replaces fourteen legacy files |
