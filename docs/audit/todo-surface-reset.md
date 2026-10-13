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

---

## 6. Addendum (2026-10-13) — todo.json narrowed to open work only

Per a later user directive ("这个文件现在太长了" → "只留待办"), the surface
described in §2 was split again:

- **`todo.json`** now holds only: `schema_version`, `purpose`, `updated_at`,
  `head`, `history`, `gate_chain`, `no_push`, `commit_footer`, `open_gaps`,
  `done_2026-10-13`. It answers one question — *what is left to do*.
- **`docs/audit/todo-history.md`** (new) holds everything that is state or
  history rather than open work: the binding policy rationale, the gate
  snapshot, the manuscript/venue metadata, the 11-cell `evidence_ledger`, the
  `lineageflow_real_forward` (D-004/D-004b) saga, the closed-gap list, the
  publication assessment, and `removed_surfaces`.

Consequence for §2/§4 above: the key names `evidence_ledger`,
`lineageflow_real_forward`, `resolved_gaps`, `recommended_attack_order` and
`removed_surfaces` are no longer top-level keys of `todo.json`; the
`removed_surfaces.known_dangling_references` pointer flagged in §4 now lives in
`docs/audit/todo-history.md` §8. No fact was dropped; nothing frozen was
touched.

---

## 7. Addendum (2026-10-13) — completed work removed; empirical-upgrade program opened

Per a later user directive ("todo.json 里那些已经完成的任务就从 todo.json 里去除，
这个文件不能长" + "你提到的这些卡点我们都要做好对应的修复"), `todo.json` was
rewritten again:

- **The `done_2026-10-13` array was deleted entirely.** Completed work is
  already recorded in `docs/audit/todo-history.md` §6 (closed-gap table) and in
  git history, so keeping it in the open-work surface was pure duplication.
  `todo.json` now carries **only** `open_gaps` (plus the fixed header keys).
- **A new empirical-upgrade program was opened** (the six agent-side gaps),
  derived from the publication assessment's gating risks
  (`docs/audit/todo-history.md` §7). The program's thesis: the Q1 gating risk is
  the **empirical axis**, not the framework, so the fixes target the evidence,
  not the infrastructure.

| new gap | gating risk it addresses | acceptance |
|---|---|---|
| GAP-24-BOUNDARY-LAW | §7 risk 3 (per-cell excuses → one law) | a criterion stated before backtesting predicts the 11-cell regime |
| GAP-25-R1-BLEND-ISOLATION | §7 risk 1 (R1 win is the random init) | blend-vs-init experiment; claim matches the finding |
| GAP-26-R5B-REGIME | §7 risk 2 (straw-man baseline) | surviving config, or a precise boundary the law reproduces |
| GAP-27-R3-POWER | §7 risk 1 (R3 underpowered) | R3 significant, or a clearly-bounded null |
| GAP-28-R6-LIVE-FAITHFUL | §7 risk 1 (R6 live below bar) | faithful easy-tier direction clears +0.2235, or a definitive null |
| GAP-29-MANUSCRIPT-DENSITY | §7 risk 4 (engineering-heavy / science-thin) | reduced meta-content density (needs user sign-off) |

`GAP-15-VENUE` is marked `PARKED` (user: "投到哪家先不管"); `GAP-20-COVERLETTER`
stays user-gated. No frozen surface was touched; the numbers in the evidence
ledger are unchanged.
