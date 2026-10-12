# GAP-02-R3-N1000 — resolved at the management surface (3-seed ACTUAL, PROJECTED dropped)

**Date:** 2026-10-13
**Branch:** main
**Base commit:** `14bf0ae` (chore(todo): record GAP-09-THEORY resolved)
**Scope:** GAP-02-R3-N1000 acceptance closure at the **management surface only** (`todo.json` + this note). Frozen surfaces (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.md`, `tnnls_submission/`) are **deliberately untouched** — per the user's explicit scope decision on 2026-10-13 ("todo.json + audit only").
**Verdict:** GAP-02's measurement acceptance is **met** — valid yield is 100% (≥ 99%), the N=1000 paired `fg_dev` sweep is measured at 3 seeds (ACTUAL, not PROJECTED), and the R3 `PROJECTED` label is dropped **at the management surface** (`todo.json` evidence ledger). The framework-WINS direction is reproduced in aggregate (−0.0377) but **not statistically significant** (p = 0.559), consistent with the pre-existing UNDERPOWERED per-arm verdict.

---

## 1. Purpose

`todo.json` `open_gaps` carried GAP-02-R3-N1000 with acceptance:

> "valid yield >= 99%; N=1000 paired measured; R3 label drops 'PROJECTED'."

The **measurement** work was completed in a prior increment (`docs/audit/r3-env-investigation.md` §8–§9, commit `0f62c27`): the documented "RDKit environment drift" root cause was **refuted** (the live `flowmol3_venv` is byte-identical to the pre-Wave-82 lock), the real cause was a batched prior-tiling regression (`repeat_interleave` → `.repeat(n_mol, 1)`), the fix restored valid-yield 40% → 100%, and a full 3-seed N=1000 re-run completed. This note closes the gap by (a) re-verifying the artifacts, and (b) recording the resolution in `todo.json`.

---

## 2. Acceptance verification

| Acceptance clause | Evidence | Status |
|---|---|---|
| valid yield ≥ 99% | `verification_outputs/r3_n1000_3seed_fixed_q4_2026/*.json` — all six arms emit `validity_pct = 1.0` (n_sampled 990–999/1000) | ✅ MET (100%) |
| N=1000 paired measured | `verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.json` — `n_seeds_completed=3`, `n_total_per_arm=1000`, `nfe=250`, 10 batches × 100 mols, blocked tiling | ✅ MET (3-seed ACTUAL) |
| R3 label drops `PROJECTED` | `todo.json` evidence-ledger R3 `status` changed from `PARTIAL / single-seed PROJECTED` → `PARTIAL / 3-seed ACTUAL` | ✅ MET (management surface) |

---

## 3. Measured result (3-seed N=1000 ACTUAL, `fg_dev`)

| seed | baseline `fg_dev` | framework `fg_dev` | paired diff | n_sampled (b / f) |
|---:|---:|---:|---:|---|
| 42 | 0.605186 | 0.655220 | **+0.050035** | 997 / 998 |
| 43 | 0.787544 | 0.650808 | **−0.136736** | 990 / 997 |
| 44 | 0.583237 | 0.556876 | **−0.026361** | 999 / 997 |

3-seed paired summary: `mean_diff = −0.037687`, `sd_diff = 0.093899`, `se = 0.054213`, `t = −0.695175`, `df = 2`, `p_raw = 0.558854`, 95% CI `[−0.143944, +0.068570]`, `cohens_d_z = −0.401360`, Bonferroni α = 0.05/7 = 0.007143, `bonf_sig = False`.

**Direction:** framework-WINS in aggregate (−0.0377), 2/3 seeds framework-wins — same direction as the canonical seed-42 headline (−0.0235). **Significance:** none (p = 0.559), consistent with the existing UNDERPOWERED per-arm verdict.

---

## 4. Honest caveats (carried forward verbatim from `r3-env-investigation.md §9.3`)

- The canonical seed-42 point is **not reproduced** (`−0.0235` → `+0.0500`) because the canonical number came from the **pre-fix** adapter revision (`e3f4072`, untiled prior); the two are different configurations and only the aggregate direction is comparable.
- Per-record PROJECTED (t = −9.005) vs per-arm ACTUAL 3-seed (p = 0.559) is a **granularity difference**, not a conflict.
- `n_seeds=3, df=2` is a low-power design; this run does **not** lift R3 out of UNDERPOWERED.
- Single shared tiled prior per batch (`.repeat(n_mol, 1)`); whether the canonical batched path used independent per-molecule priors remains **unverified**.

---

## 5. What this changes (and what it does not)

**Changes:** the `todo.json` evidence ledger now reads `PARTIAL / 3-seed ACTUAL` and the `PROJECTED` label is dropped; GAP-02-R3-N1000 moves from `open_gaps` to `resolved_gaps`.

**Does not change:** every **frozen** surface — `docs/CLAIMS.md` CLM-068 / CLM-060, `docs/CONSOLIDATED_RESULTS.md` §15.105, `docs/drafts/paper-A-final.md` §7.2 / §7.11, and all of `tnnls_submission/` remain **byte-identical**. The frozen paper/CLAIMS still carry the historical `PARTIAL / single-seed PROJECTED` label; this is now a known **management-vs-frozen staleness** that is recorded here and flagged for a future, explicitly-authorized additive paper update. No number moved anywhere.

---

## 6. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ new audit note + `todo.json` ledger update; no frozen number/label rewritten |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ keeps UNDERPOWERED; drops only the *PROJECTED* provenance label, which is now factually ACTUAL |
| #5 TNNLS freeze | ✅ `tnnls_submission/` byte-identical |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ todo.json + audit only, per the user's explicit scope decision |

---

## 7. Verification

| Gate | Result |
|---|---|
| R3 artifacts present (`r3_n1000_3seed_fixed_q4_2026/`, 13 files + `SHA256SUMS`) | ✅ present |
| `validity_pct == 1.0` on all 6 arms | ✅ verified |
| `n_seeds_completed == 3` in the paired JSON | ✅ verified |
| `python3 tools/check_claims_consistency.py` | No drift detected (frozen CLAIMS untouched) |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `mkdocs build --strict` | exit 0 |

---

## 8. Residual / noted

- **Frozen-surface staleness.** The paper/CLAIMS still say `PARTIAL / single-seed PROJECTED`. Aligning them is a **frozen-surface edit** and was explicitly **out of scope** for this increment (user decision 2026-10-13). It is the natural next step if/when the user authorizes an additive paper update.
- **Independent per-molecule prior** question (audit §3.4 / §5 option (b)) remains open; this run does not settle it.
