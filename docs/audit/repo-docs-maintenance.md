# Repository documentation maintenance — refresh

**Date:** 2026-10-12
**Scope:** Repo-wide documentation hygiene and project maintenance (beyond the manuscript-consistency sweeps): the new increment-free management surface, gate-claim honesty across the READMEs and doc map, an inventory of legacy drafts/artifacts, and the `docs/` map.
**Status:** COMPLETE — four workstreams executed. Management surface is now fully increment-free; gate claims reconciled with the readiness verifier; legacy artifacts annotated (not deleted). **No manuscript artifact, metric, or claim changed.**

---

## 1. Findings (observed facts)

| # | Finding | Evidence |
|---|---|---|
| F1 | **Increment identifier left in the new management surface.** `todo/WAVES.md` carried one numbered-work-increment reference ("the first push since the Wave 325 NO-PUSH policy"); `todo/README.md` carried four (a "post-Wave 384" heading, a "Wave 238 P3" supersession note, and a "Wave 238 P3" venue note). | `grep -cE "Wave [0-9]+\|wave[0-9]+" todo/*.md` before the fix: `WAVES.md` 1, `README.md` 4. |
| F2 | **Stale repository-state pins.** Both `todo/WAVES.md` and `todo/README.md` reported HEAD `fea137d` and "**0** commits ahead of `origin/main`"; actual HEAD is `8756f19` with **5** local-only commits ahead (`origin/main` = `fea137d`). | `git rev-list --count origin/main..HEAD` → `5`. |
| F3 | **Gate-claim scope mismatch.** `README.md` / `README.zh.md` / `docs/README.md` / `todo/WAVES.md` advertise a "9-gate ALL PASS" hard-requirement set, while `tools/verify_submission_readiness.py` reports **NOT_READY** overall because of two additional gates — `k1_rc5` and `drift_33`. These are the documented **camera-ready-scope doc-drift** items (the pytest side was closed with xfail markers; the doc side remains open), so they are a gate-*scope* difference, not a contradiction — but the surfaces did not say so. | Verifier output: `NOT_READY: k1_rc5, drift_33`; root-cause note `docs/audit/wave359-k1-rc5-drift33-fix.md` (cited in the manuscript's own K1 row). |
| F4 | **Environment-dependent mypy claim.** `README.md`, `README.zh.md`, and `todo/WAVES.md` state "mypy 0 errors". In the current sandbox (`mypy 2.3.1` via `.venvs/flowmol3_venv`, with missing third-party stubs) the same command reports **39 errors** in adapter files — pre-existing and environment-dependent (already recorded in `docs/audit/manuscript-defect-review-7.md`). | `.venvs/flowmol3_venv/bin/python -m mypy adaptive_reflow/` → `Found 39 errors in 13 files`. |
| F5 | **Legacy drafts/artifacts not labelled.** `docs/paper-draft.md` (the superseded EAAI-era draft, still read by the verifier's `r1_r6_sha` + `k1_rc5` gates) carried no legacy banner; three superseded compiled PDFs (`paper-eaai.pdf`, `paper-tnnls.pdf`, `paper-final-neurips.pdf`) were absent from the `docs/` map. `paper-eaai.pdf` and `paper-tnnls.pdf` are **byte-identical** (`940fe61d…`). | `sha256sum docs/paper-eaai.pdf docs/paper-tnnls.pdf` → identical digests. |
| F6 | **Doc-map date stale.** `docs/README.md` said "updated 2026-10-11". | line 3. |

**Non-findings (verified clean):**
- No stale ledger SHA pins outside the intentional historical records: the superseded `.md` / `.tex` / `.pdf` digests survive only in `docs/audit/` history and the `tnnls_submission/` additive blockquotes, where they are correct to preserve.
- Working tree was clean at the start; the manuscript artifacts (`paper-A-final.{md,tex,pdf}`) were untouched by this refresh.

## 2. Changes (additive; no deletions)

**Workstream 1 — management-surface consistency.**
- `todo/WAVES.md`: removed the residual increment reference; refreshed HEAD → `8756f19` (prior readings kept) and ahead-of-`origin/main` → **5**; added the readiness-verifier scope note and the mypy environment caveat to §1.2.
- `todo/README.md`: removed all four increment references ("post-Wave 384" → "Structure"; supersession/venue notes reworded to phase level); refreshed HEAD/ahead; updated the "latest audit" pointer; corrected the remaining user-gated-action list (push of the 5 local commits).
- Both files are now **fully increment-free** (`grep -cE "Wave [0-9]+|wave[0-9]+"` → 0 each).

**Workstream 2 — gate-claim honesty.**
- `README.md`: annotated the submission-status row and the mypy row; added a "Gate-scope note" after the gate table reconciling the 9-gate set with the readiness verifier's `k1_rc5` / `drift_33`.
- `README.zh.md`: mirrored the same three annotations.
- `docs/README.md`: annotated the acceptance-gates banner with the same scope note.
- `todo/WAVES.md` §1.2: added the readiness-verifier gate breakdown + the mypy environment caveat.

**Workstream 3 — legacy artifact inventory.**
- `docs/paper-draft.md`: added a top **LEGACY DRAFT (EAAI-era)** banner naming the live manuscript (`drafts/paper-A-final.md` / `.pdf`) and noting the file is still read by the verifier's `r1_r6_sha` + `k1_rc5` gates. No body content changed.
- Legacy compiled PDFs inventoried in the `docs/README.md` §6 archival list (see workstream 4). The tracked `.bak` archives (`docs/paper-draft-precut*.md.bak`, `docs/internal/todo/todo.json.bak`) were reviewed and **retained** (provenance).

**Workstream 4 — doc-map refresh.**
- `docs/README.md`: refreshed the "updated" date to 2026-10-12; clarified the `paper-draft.md` row as the legacy EAAI-era draft; added the three superseded compiled PDFs to §6.

## 3. Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| docs-against-code | `python tools/check_docs_against_code.py` | **PASS** — see §3.1 |
| claims consistency | `python tools/check_claims_consistency.py` | **PASS** — no drift |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** |
| D.4 regression | `pytest tests/test_d4_regression_vectors.py -q` | **PASS** — 30/30 |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0 |
| readiness verifier | `tools/verify_submission_readiness.py` | **NOT_READY** — the two documented camera-ready-scope gates only (see F3) |

### 3.1 Post-edit file digests

Recorded for provenance; the digests are the pre-commit working-tree values.

| File | SHA-256 | Bytes |
|---|---|---|
| `todo/WAVES.md` | `491fd4e8ed72cda7f10f8b7372a1c358c81fecd3028c8aaf1c56d55c438d9688` | 21872 |
| `todo/README.md` | `c832636f4d2543c7ed76ab1081fff5dc49224b14e83f8f1e5b341882dd40f379` | 3749 |
| `README.md` | `cf91fdc593ab991ca11111906efe0338231c0ee33fe25642318f02787d436f03` | 39491 |
| `README.zh.md` | `63de78ad246be366e855cc5500e2ed63a144bc0dcd11db2806fe740063900c59` | 42006 |
| `docs/README.md` | `d44ee543919070c530a56cccbad4d29693f4e3d3fea9f1806ddec494cf204878` | 15160 |
| `docs/paper-draft.md` | `ec3643e03a1b873f9566c9f21b76894f6bcb5d26a4afad07ba616a603e46a488` | 190884 |

## 4. Unresolved gaps / caveats

- **`k1_rc5` / `drift_33` remain red by design.** They are camera-ready-scope doc-drift gates tied to superseded artifacts (`docs/paper-draft.md` K1 wording; historical `33/33 PASS` strings under `docs/audit/engineering/`). Clearing them would require either editing historical records (against the provenance rule) or repointing the verifier at the current manuscript — a gate-semantics change left for an explicit decision.
- **Full `pytest tests/` sweep** is environment/ordering-dependent in this sandbox and did not terminate within ~27 min; the reproducible pytest gate is D.4 (30/30 single-file; 72/72 via the verifier).
- **Legacy `.bak` archives and superseded PDFs are retained** (not deleted) per the provenance rule.
- **Update (2026-10-12, follow-up pass).** The `k1_rc5` / `drift_33` "explicit decision" flagged above was made by the user: the verifier was repointed at the live manuscript and `drift_33`'s allowlist extended, so **both gates now pass** (`READY_WITH_SKIPS: mypy_0`, exit 0). See `docs/audit/readiness-verifier-repoint.md`. The prior readings in §1–§3 above are preserved verbatim as the state at the time of this refresh.
