# Paper v3.2 — data refresh checklist

**Date:** 2026-10-24
**Author:** paper-refresh agent (USER AUTHORIZED, NO PUSH)
**Status:** prepared while GAP-69 seeds 43/44 are still generating (ETA 2026-10-25 ~04:30 local). **No number in this file is a result**; it is the map from each published number to the artifact that will regenerate it.
**Frozen surfaces:** `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.*`, `tnnls_submission/**` are **not** touched by this file. They are touched only in §6, after the refresh, under the user's 2026-10-24 "完整刷新所有数据记录" instruction.

---

## 0. Ground rules

1. **Refresh = regenerate, never hand-edit.** Every number in the manuscript must be copied from an artifact that is produced by a committed tool. If a table cannot be regenerated, it is not refreshed — it is flagged (§8).
2. **One artifact per number.** If two artifacts disagree, the disagreement is written down and a basis is chosen explicitly (§4.3). Numbers from different bases are never averaged, pooled, or silently substituted.
3. **Labels move only by rule.** `STRONG` / `TIE` / `PARTIAL` / `UNDERPOWERED` / `REGRESSES` change only if the pre-registered acceptance rule fires. A refresh that changes a label must cite the rule and the artifact in the same paragraph.
4. **No seed top-ups.** The 3 seeds are 42/43/44 because the escalation was pre-registered at 3 seeds. No fourth seed is added to move a verdict.
5. **The frozen v3.0/v3.1 tags stay.** v3.2 is a new tag cut after §7 passes; the old tag is never moved.

---

## 1. What triggers the refresh

| trigger | state | effect on the paper |
|---|---|---|
| GAP-69 seeds 43/44 (R1 init-profile, 3 seeds) | **RUNNING**, ETA 2026-10-25 ~04:30 | R1 paragraph + status row + (only if it passes) a new mechanism subsection |
| GAP-76 mean-preserve (MNIST, 4 ckpts × 3 seeds) | landed 2026-10-23 | R5c row: the `+10.37%` REGRESSES reading is superseded for the production ckpt |
| GAP-78 β=0.3 three-seed R5c verdict | landed 2026-10-24 | §7.2 R5c paragraph, §7.9 table, §7.11 index, CLM-059 |
| GAP-84 frontier protocol | protocol only, **0 complete grids** | **no table change.** No frontier number exists, so no frontier claim is written (§8.3) |
| GAP-78 rho/κ selector screens | falsified, no paper number | nothing; the mechanism section gains one sentence at most |

---

## 2. New artifacts (everything created after the 2026-10-18 freeze)

| artifact | what it measures | N / seeds | report file | state |
|---|---|---|---|---|
| `verification_outputs/gap69-lineageflow-profile/seed{42,43,44}/` | R1 arm C, `init_profile=conservation`, `hmmscan_total_hits` + per-record jsonl | 1000 / seed | `report_seed42.json` (43/44 **missing**) | 42 done, 43 done, 44 running |
| `…/seed{43,44}_init_only/` | R1 arm B, same config, no profile | 1000 / seed | — | 43 done, 44 running |
| `…/armD_hmm_draw/` | R1 arm D, no model (ceiling reference) | 1000 / seed 42 | — | done |
| `verification_outputs/gap76-mean-preserving/report.json` | MNIST projection-FID, mean-preserving blend, 4 ckpts × 3 seeds × 3 arms | 36 cells | `report.json` | done |
| `verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json` | R5c β=0.3 verdict, 4 ckpts × 3 arms × 3 seeds | 12 cells | `r5c_report.json` (`schema gap78_r5c_report_v2`) | done |
| `verification_outputs/gap78-observable-screen/` | ρ / κ selector screen | 4 ckpts | screen json | done, both falsified |

Generator commands (exact):

```bash
# R5c three-seed verdict (both rules are written into the artifact; neither may be quoted alone)
python3 tools/gap78_r5c_report.py --root verification_outputs/gap78-kappa-dose-n1000-3seed \
    --floor-units 1.0 --out verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json

# R1 per-seed paired report (run once per seed after 43/44 land)
python3 tools/gap69_report.py \
    --profile-run verification_outputs/gap69-lineageflow-profile/seed43 \
    --init-only-run verification_outputs/gap69-lineageflow-profile/seed43_init_only \
    --out verification_outputs/gap69-lineageflow-profile/report_seed43.json
```

**Prerequisite that does not exist yet:** the per-family decomposition (§7.2 needs it, GAP-69's acceptance rule needs it). `tools/gap69_report.py` groups by nothing — it reads `intended_family_canon` but never aggregates on it. Seed 42's four-family table was computed ad hoc. **`tools/gap69_per_family.py` must be written before the R1 refresh**, taking `--runs <profile> <init-only>` and emitting per-family `n / hits_B / hits_C / ratio / delta_per_record / t / ci95` plus the PF00005-excluded aggregate.

---

## 3. Manuscript table map — 10 tables

Line numbers are as of `paper-A-final.md` 216 736 B (2026-10-18). Anchors are section + caption, which survive edits.

| # | § | table | action | source after refresh |
|---|---|---|---|---|
| 1 | 3.4.2 | capability-token SHA-256 example | **VERIFY-ONLY** | `verification_outputs/wave355-capability-token-example/` |
| 2 | 3.5.1 | ledger SHA-256 chain (3 files) | **VERIFY-ONLY** | `verification_outputs/wave349-r1-3seed-gpu/` |
| 3 | 3.10 | causal mechanism chain | **VERIFY-ONLY** | `docs/audit/mechanism-core-driver.md` |
| 4 | 5.3 | five adapter implementations | **VERIFY-ONLY** | `adaptive_reflow/adapters/*.py` |
| 5 | 6.1 | mechanism-to-metric transfer | **VERIFY-ONLY** | unchanged |
| 6 | 7.2 | per-cell power-disclosure index (7 rows) | **REWRITE 2 rows** | R1 row ← GAP-69; R5c row ← GAP-78 |
| 7 | 7.7 | NFE-matched boundary (R5b, 4 rows) | **VERIFY-ONLY** | `wave235-p1`, `wave247-p3`, `wave225-p7`, `wave206-p6` |
| 8 | 7.9 | R5c regime curve (3 rows) | **REWRITE** | `gap78-kappa-dose-n1000-3seed/r5c_report.json` + `wave191-r5-n1000/` |
| 9 | 7.11 | 11-cell status index (11 rows) | **REWRITE 2 rows** | R1, R5c |
| 10 | 8.10 | per-cell recipe manifest (11 rows) | **REHASH + ADD** | `paper-data/*/…RECIPE.md` SHA-256 |

Rules for each action:

* **VERIFY-ONLY** — re-read the artifact, confirm the printed digits match byte-for-byte, change nothing. If a digit differs, stop and open a reconciliation note; do not "fix" the table.
* **REWRITE** — regenerate from the artifact, then restate the verdict using §0.3.
* **REHASH** — every recipe whose source numbers moved gets a new SHA-256; recipes whose cells did not move keep their old hash.

---

## 4. The three reconciliations that must be decided before any edit

### 4.1 R1: GAP-69 is not the headline R1 number

The headline R1 in `tnnls_submission/tables.md` Table 1 is `158 → 342` (`+116.46%`, synthetic-velocity basis, `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/`). GAP-69 measures a **different intervention** — the fresh-restart state is seeded from the family HMM (`init_profile=conservation`) against an init-only control, 284 → 2329 at seed 42. These are not interchangeable.

Decision required: GAP-69 becomes **§7.6.x "profile-aware restart init"** (a mechanism study, own table), and the headline R1 row is left alone. Replacing the headline would silently change what the paper's R1 cell means.

### 4.2 R1: the acceptance rule is per-family, and the paper must say which rule it uses

`todo.json` GAP-69 acceptance: WIN requires the 3-seed aggregate CI to exclude 0 **and every one of the four families to be at or above baseline**. Seed 42 satisfies only the first (PF00005 27.81×, other three 0.908, n.s.). The refresh computes the same two numbers at 3 seeds and writes **both**. A verdict that quotes only the aggregate is not admissible under the pre-registration.

### 4.3 R5c: two different baseline bases exist — do not merge them

| basis | production baseline FID | where | what it is |
|---|---:|---|---|
| paper §7.9 (`wave191-r5-n1000`) | 11.99 | current manuscript | single-pass headline FID over the full population; `n_seeds=3` |
| GAP-78 (`gap78-kappa-dose-n1000-3seed`) | 9.967 | new artifact | projection-FID at N=1000, shared prior, β=0.3 arm |

The two cannot be placed in one column, and `+10.37%` (paper) vs `−0.50%…−0.19%` (GAP-78) are **not** a contradiction — they are different metrics on a different blend parameter. The refresh must either (a) keep §7.9 on the old basis and add the β=0.3 result as a **separate labelled table**, or (b) restate §7.9 entirely on the GAP-78 basis with the old rows kept as historical. Option (a) is the additive choice and is the default unless the user says otherwise.

---

## 5. `tnnls_submission/` surfaces

| file | action |
|---|---|
| `tables.md` Table 1 (R-level headline) | VERIFY-ONLY; R1 headline unchanged (§4.1) |
| `tables.md` Tables 2–5 | VERIFY-ONLY |
| `tables.md` Table of Tables | re-point T4/T5 source rows if §7.2 / §7.9 move |
| `highlights.md` | rewrite the R5c bullet only; no new bullet unless GAP-69 passes §4.2 |
| `cover_letter.md` | same; plus the SHA-256 table at the end |
| `MANIFEST.md` | rehash every changed file (`sha256sum -- *.md`) |
| `submission_checklist.md` / `SUBMISSION_READINESS.md` | status lines only |
| `data_availability.md` | add `verification_outputs/gap69-lineageflow-profile/` and `gap78-kappa-dose-n1000-3seed/` if they are cited |

---

## 6. Claim ledger rows

| claim | current | refresh action |
|---|---|---|
| CLM-059 (R5c MNIST, **PROVISIONAL**) | smoke ckpt WINS −28.43%, production REGRESSES +10.37% | append GAP-78 addendum: β=0.3, 3 seeds, 12/12 weak dominance on the ledger floor, 3 strict floor-gains on `w16e1_5k`; keep both rule verdicts (`LOSS` under 1% relative, `WIN` under floor) and state which one is claimed |
| CLM-060 (R-level power, R1/R5a rows) | R1 PARTIAL single-seed; R5a TIE | R1 row gains the GAP-69 3-seed result; R5a untouched |
| CLM-070 (R5b) | conditional single-round | untouched |
| CLM-068 (R3) | PARTIAL / PROJECTED | untouched |
| new row (GAP-69) | — | only if §4.2 fires; otherwise the GAP-69 numbers live in the audit + §7.6.x and no new CLM is opened |

---

## 7. Prose surfaces

| surface | change |
|---|---|
| abstract (`docs/drafts/abstract-final.md`, paper §Abstract) | the cell-count sentence and the R5c clause; no new sentences beyond what the numbers support |
| §7.2 R5c paragraph | full rewrite on the new basis (§4.3) |
| §7.2 R1 paragraph | add the 3-seed profile result; keep `PARTIAL` unless §4.2 fires |
| §7.9 | see §4.3 |
| §7.10 summary | one clause per changed cell |
| §7.11 | the `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` line, recomputed |
| §8.10 | recipe hashes |
| `README.md` / `README.zh.md` | only if they quote a changed number |

---

## 8. Rehash and gates (run in this order)

```bash
# 1. D.4 byte-stable regression — must be 30/30
python3 -m pytest tests/test_d4_regression_vectors.py -q

# 2. claims consistency — must exit 0
python3 tools/check_claims_consistency.py

# 3. lint + docs
ruff check adaptive_reflow/ tests/ scripts/ tools/
mkdocs build --strict

# 4. submission package hashes — MANIFEST must match
cd tnnls_submission && sha256sum -- *.md

# 5. full suite (subset green; env/ordering-dependent)
python3 -m pytest tests/ -q
```

`mypy` is expected to report SKIP in this environment (`docs/CLAIMS.md` CLM-024); run it with system `python3`, not an activated `.venv` (a venv mypy turns a SKIP into FAIL on 3 pre-existing errors).

---

## 9. Blockers and open decisions

1. **GAP-69 not finished** — R1 refresh cannot start. Everything else can.
2. **`tools/gap69_per_family.py` does not exist** — required by §4.2 and by GAP-69's own acceptance rule.
3. **No frontier numbers exist.** GAP-84's inventory found 0 complete NFE grids, so the paper keeps the current matched-NFE framing. Writing a frontier section requires new GPU grids and is out of scope for this refresh.
4. **No committed TeX/PDF build path.** `paper-A-final.tex` / `.pdf` were produced outside the repo; a repo-wide grep finds no script that regenerates them from `paper-A-final.md`. Either the build is scripted in this refresh (`reproduce/build_paper.sh`) or the .tex/.pdf are declared stale — silently shipping a PDF that disagrees with the .md is the one failure mode this checklist cannot tolerate.
5. **§4.3 basis choice** — needs a decision before §7.9 is touched.

---

## 10. Do not touch

* `data/` (9 vendored upstream repos)
* the frozen regression vectors
* `v3.0-tnnls-ready` / `v3.1-*` tags
* any number in a VERIFY-ONLY table
* `docs/audit/` historical records (additive sections only)
