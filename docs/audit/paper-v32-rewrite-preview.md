# Paper v3.2 — REWRITE rows 6, 8, 9 (preview, nothing applied)

**Date:** 2026-10-25
**Author:** paper-refresh agent (USER AUTHORIZED, NO PUSH)
**Status:** preview only. **No frozen surface was edited.** `paper-A-final.md`,
`CLAIMS.md`, `CONSOLIDATED_RESULTS.md` and `tnnls_submission/**` are unchanged;
this file holds the exact additive text so applying it is mechanical once the
user says go.

Rows 6, 8, 9 of `paper-v32-data-refresh.md` §3 are **not** blocked on GAP-84 —
their sources (GAP-69, GAP-78) are closed. Row 10 is still blocked (it hashes
recipes whose cells move only after 6/8/9 land).

---

## 0. Sources, read from the artifacts (not from prose)

| quantity | value | artifact |
|---|---|---|
| GAP-69 seed 42 / 43 / 44 aggregate C/B | 8.20× / 8.06× / 8.46× | `gap69-lineageflow-profile/per_family_3seed.json` |
| GAP-69 families at or above B, all 3 seeds | PF00005 3/3 (27.8–40.9×, CI excludes 0), PF00072 0/3 (0.79×), PF00183 0/3 (0.80×), PF02517 3/3 (1.07–1.42×, every seed's CI includes 0) | same |
| GAP-69 verdict label | `HEADLINE_GAIN_NO_FAMILY_IDENTITY` | same, `verdict.label` |
| GAP-78 cells / weak dominance / strict gain (1 % relative) | 12 / 11 / 7 → `verdict_relative = LOSS` | `gap78-kappa-dose-n1000-3seed/r5c_report.json` |
| GAP-78 cells / weak dominance / strict gain (1 FID floor) | 12 / 12 / 3 → `verdict_floor = WIN` | same |
| GAP-78 worst cell | +0.098 FID units | `docs/audit/gap78-*.md` (§7.2 of that record) |

Both GAP-78 verdicts are in the artifact and, per the report's own `caveat`
field, **neither may be quoted alone**.

---

## 1. Row 6 — §7.2 per-cell power-disclosure index (2 of 7 rows)

### 1.1 R1 row — append to the `per-cell power disclosure in this paper` cell

```
+ ; §7.6.x profile-aware restart init (GAP-69, three seeds): the aggregate is
8.06–8.46× with a paired CI that excludes 0 at every seed, and the per-family
decomposition puts PF00072 and PF00183 below the init-only arm at all three
seeds. The headline R1 cell above is a different intervention and is unchanged
(§4.1 of the refresh checklist).
```

Rationale: the index row is a **navigation** surface. GAP-69 is a mechanism
study with its own subsection; linking it here is additive and does not touch
the R1 number or the `PARTIAL` label.

### 1.2 R5c row — append to the same cell

```
+ ; §7.9b β = 0.3 three-seed table (GAP-78): 12/12 cells weakly dominate the
baseline on the ledger floor with 3 strict floor-gains on w16e1_5k, worst cell
+0.098 FID units. Under the 1 % relative rule the same 12 cells give 11/12 and
7/12, so the two rules are printed together and neither is quoted alone.
```

---

## 2. Row 8 — §7.9 R5c regime curve

`§4.3` default is option (a): **keep** the existing 3-point table on its own
basis (baseline FID 11.99 / 9.967 are different metrics, `§4.3`) and **add** the
β = 0.3 result as a separate labelled table. No existing row changes.

### 2.1 Proposed additive block (new §7.9b, inserted after the §7.9 figure note)

```markdown
#### 7.9b R5c at β = 0.3, three seeds, N = 1000 (separate basis)

The §7.9 table is a *regime* curve: one blend parameter, three checkpoints, and
a baseline FID read as a single pass over the full population. The table below
is a different object — a **fixed** blend parameter (β = 0.3) across four
checkpoints × three seeds, scored as projection-FID at N = 1000 on a shared
prior. Its production baseline is 9.967, not 11.99; the two bases are not
comparable and are never pooled (`docs/audit/paper-v32-data-refresh.md` §4.3).

| rule | weak dominance | strict gain | verdict |
|---|---:|---:|---|
| 1 % relative ΔFID | 11 / 12 | 7 / 12 | `LOSS` |
| 1 FID-unit floor (CLM-060) | 12 / 12 | 3 / 12 | `WIN` |

Worst cell: +0.098 FID units. The two rows are both printed because the ledger
floor is the cell's own margin and the relative rule is scale-free; a verdict
that quotes one without the other is not admissible
(`verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json`,
`verdict_relative` / `verdict_floor` / `caveat`).

This does not move the §7.9 regime reading and does not promote CLM-059: the
smoke-ckpt STRONG row and the production REGRESSES row stand as written.
```

---

## 3. Row 9 — §7.11 11-cell status index (2 of 11 rows)

### 3.1 R1 row — append to `current_status`, and set `wave_last_updated`

```
+ [GAP-69 addendum, additive: a three-seed profile-aware restart init reaches
8.06–8.46× over its own init-only control with a CI excluding 0 at every seed,
but only PF00005 clears the per-family condition (2/4 families); verdict
HEADLINE_GAIN_NO_FAMILY_IDENTITY. Different intervention from the R1 cell —
no change to the status above.]
```

`wave_last_updated`: `Wave 308 P1 …` → `GAP-69 (2026-10-25, profile-init
mechanism study, additive)`.

### 3.2 R5c row — append to `current_status`

```
+ [GAP-78 addendum, additive: at β = 0.3, 3 seeds × 4 checkpoints, 12/12 cells
weakly dominate on the 1 FID-unit floor (3 strict floor-gains, worst cell
+0.098) and 11/12 under the 1 % relative rule (7 strict); both verdicts printed,
neither quoted alone. Status above unchanged.]
```

`wave_last_updated`: `Wave 349 … + Wave 334 …` → `+ GAP-78 (2026-10-25,
β = 0.3 three-seed table)`.

---

## 4. Row 10 — still blocked

`§8.10` recipe hashes move only for recipes whose source numbers moved. Rows
6/8/9 above are **additive** — no existing number changes — so on the current
plan **no recipe hash changes** and row 10 reduces to a re-verification pass.
If the F2 fix from `paper-v32-verify-only-pass.md` is applied in the same edit,
only §3.10's row is touched and no recipe cites it.

---

## 5. Apply order (when authorised)

1. §7.9b block (§2.1) — new subsection, no existing line edited.
2. §7.2 index rows (§1.1, §1.2) — two cell appends.
3. §7.11 rows (§3.1, §3.2) — two cell appends + two provenance cells.
4. Re-run `python3 tools/check_claims_consistency.py` (must exit 0) and
   `mkdocs build --strict`.
5. `cd tnnls_submission && sha256sum -- *.md` and update `MANIFEST.md` only if
   a submission file was touched (it is not, on this plan).
6. Full suite + D.4 30/30, then commit.

Nothing in this plan changes a number, a label, or a `tnnls_submission/` file.
