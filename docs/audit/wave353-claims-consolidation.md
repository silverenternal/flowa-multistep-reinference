# Wave 353 P8 — Wave 349-352 CLAIMS addenda consolidated status table

**Date:** 2026-09-25
**Author:** Wave 353 P8 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive consolidated status table for reviewer-facing visibility of Wave 349-352 CLM-level work. No claim number, no claim status, no asserted-by reference is changed.
**Trigger:** Wave 353 P8 task brief — consolidate Wave 349-352 ADDITIVE addenda into a single canonical status table at the top of `docs/CLAIMS.md` so reviewers can see all CLM-level addenda at a glance. Per Wave 268 strict-clean rule (status history additive, no removal).
**Scope:** `docs/CLAIMS.md` (new consolidated status table appended after the "How it works" intro, before `## CLM-001`); this audit doc. No edits to `docs/drafts/paper-A-final.md`, `tnnls_submission/`, `tools/`, `verification_outputs/`, or `docs/CONSOLIDATED_RESULTS.md`.
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); per Wave 268 strict-clean rule (status history additive, no removal); per Wave 325 NO-PUSH policy (commit local only); per `flowa-paper-evidence` skill (wording only, never numbers); per AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7).

---

## 1. Executive Summary

A consolidated status table is added at the top of `docs/CLAIMS.md` (lines 23-40, between the "How it works" intro and `## CLM-001`) summarising every Wave 349-352 ADDITIVE addendum that touched a `## CLM-NNN:` row. The full Wave 349-352 audit trail (17 docs under `docs/audit/wave349-*.md` ... `docs/audit/wave352-*.md`) covers much broader work — paper §6.6 Theorem 5 derivation + §6.6.1 numerical validation footnote + §10.9.3 partial close-out (Wave 350-352 P1-P6), §3.4-§3.7 framework code-anchor cross-references (Wave 352 P4), §A.3 Lipschitz-constant appendix (Wave 352 P3), §7.6 R5b 4-scheduler × 3-`n_rounds` figure (Wave 350 P4), cover-letter helper + interactive mode (Wave 351 P5 + Wave 352 P2), R3 vendor-fix status (Wave 351 P3), R6 live-GPU smoke test (Wave 350 P3) + status audit (Wave 352 P1), R1 3-seed materialization status (Wave 350 P2), R5a n=10 paired-t + meta-analysis (Wave 351 P2), LineageFlowAdapter cuda:0 dispatch (Wave 349 P4), final-pre-submission gap audit (Wave 349), and the implementation agent that closed 3 of 5 GAPs (Wave 349 impl) — but **only one of these added a `## CLM-NNN:` row to `docs/CLAIMS.md`**: the Wave 352 P5 addendum on CLM-060 (the R5a Wave 351 P2 n=10 paired-t confirmation addendum, TIE_PERSISTS).

| Metric | Value |
|---|---|
| Total active CLMs in `docs/CLAIMS.md` | **61** (unchanged) |
| Total deprecated CLMs | **2** (unchanged) |
| Total provisional CLMs | **0** (unchanged) |
| Wave 349-352 ADDITIVE addenda that touched a `## CLM-NNN:` row | **1** (CLM-060 / Wave 352 P5) |
| Wave 349-352 audit docs total | **17** (Wave 349: 3 docs, Wave 350: 4 docs, Wave 351: 4 docs, Wave 352: 6 docs) |
| Number of CLM IDs in the consolidated table | **1** (CLM-060) |
| Number of claim numbers changed | **0** |
| Number of status labels changed | **0** |
| Number of asserted-by references changed | **0** |

**Headline:** Wave 349-352's footprint in `docs/CLAIMS.md` is a single additive row (CLM-060 / Wave 352 P5). The consolidated status table is the reviewer-facing visibility surface for that single CLM-level touchpoint.

---

## 2. Investigation methodology

### 2.1 Source data inspected

| File | Role | Notes |
|---|---|---|
| `docs/CLAIMS.md` | ACTIVE claim ledger (this consolidation target) | 61 active + 2 deprecated + 0 provisional = 63 total CLM rows |
| `docs/audit/wave349-*.md` (3 docs) | Wave 349 audit trail | gap-audit, gpu-acceleration, impl — none touched a `## CLM-NNN:` row |
| `docs/audit/wave350-*.md` (4 docs) | Wave 350 audit trail | r1-materialize-status, r5b-figure, r6-live-attempt, thm5 — none touched a `## CLM-NNN:` row |
| `docs/audit/wave351-*.md` (4 docs) | Wave 351 audit trail | cover-letter-helper, r3-vendor-fix-status, r5a-n10, thm5-numerical — none touched a `## CLM-NNN:` row |
| `docs/audit/wave352-*.md` (6 docs) | Wave 352 audit trail | claims-r5a-update, cover-letter-interactive, framework-code-anchors, l-local-appendix, r6-status, sec10-9-close-out — **only `wave352-claims-r5a-update.md` added a `## CLM-NNN:` row (CLM-060)** |
| `tools/check_claims_consistency.py` | Claim consistency verifier | Confirms `## CLM-NNN:` rows parse cleanly and asserted-by references resolve |
| `tests/test_d4_regression_vectors.py` | D.4 byte-stable regression vectors | Must remain 30/30 PASS |

### 2.2 Detection methodology — which Wave 349-352 audit docs touched a CLM row

For each `docs/audit/wave35X-*.md` audit doc, the detection step is:
1. Read the audit doc's "Scope" section (typically the second paragraph after the title) which explicitly lists which files were modified.
2. If the scope includes `docs/CLAIMS.md` AND specifies a `## CLM-NNN:` row was appended/modified, that audit doc contributed to the consolidated table.
3. Otherwise, the audit doc's work lives in other files (paper, tools/, tnnls_submission/, verification_outputs/, CONSOLIDATED_RESULTS.md) and is not surfaced in this table.

This methodology was applied to all 17 Wave 349-352 audit docs. Only **one** matched the criteria: `docs/audit/wave352-claims-r5a-update.md` (which appended the Wave 352 P5 status addendum to CLM-060 between the Wave 326 addendum line and the Date line).

### 2.3 Reproduction

```bash
# Find which Wave 349-352 audit docs explicitly modify docs/CLAIMS.md
for f in docs/audit/wave349-*.md docs/audit/wave350-*.md docs/audit/wave351-*.md docs/audit/wave352-*.md; do
  if grep -qE "CLAIMS\.md" "$f" && grep -qE "CLM-[0-9]+" "$f"; then
    echo "$f -> CLM touched"
  else
    echo "$f -> no CLM"
  fi
done
```

Only `wave352-claims-r5a-update.md` reports a CLM modification (CLM-060 Wave 352 P5 addendum). All other 16 audit docs either don't modify `docs/CLAIMS.md` at all (most) or only reference CLM IDs as evidence anchors without appending addenda.

---

## 3. Findings (observed facts vs interpretation vs unresolved gaps)

### 3.1 Observed facts (byte-stable, verified)

1. **`docs/CLAIMS.md` has 61 active + 2 deprecated + 0 provisional CLM rows** at HEAD `04660bb` (Wave 353 P7) — verified via `python3 tools/check_claims_consistency.py` (output: "Active claims: 61; Provisional: 0; Deprecated: 2; No drift detected").
2. **Only one Wave 349-352 ADDITIVE addendum touches a `## CLM-NNN:` row** — CLM-060 / Wave 352 P5 (R5a Wave 351 P2 n=10 paired-t confirmation addendum, TIE_PERSISTS) — added in commit `cba15e3` or earlier per `git log -p docs/CLAIMS.md` for CLM-060 region.
3. **The consolidated table summarises 1 CLM row** with a one-line cross-reference to the Wave 351 P2 + Wave 352 P5 audit docs and the canonical Wave 216 P2 n=10 per-seed CSV.
4. **D.4 regression vectors:** `python3 -m pytest tests/test_d4_regression_vectors.py -q` reports **30/30 PASS** after the consolidated table insertion.
5. **Claims consistency:** `python3 tools/check_claims_consistency.py` reports **"No drift detected"** after the consolidated table insertion.
6. **No CLM number is changed**, **no CLM status label is changed**, **no asserted-by reference is changed** — verified by `git diff docs/CLAIMS.md` (which shows only an additive 18-line block at the top of the file, lines 23-40, between the existing "How it works" intro and `## CLM-001`).
7. **No edits to `docs/drafts/paper-A-final.md`, `tnnls_submission/`, `tools/`, `verification_outputs/`, or `docs/CONSOLIDATED_RESULTS.md`** — verified by `git status` (only `docs/CLAIMS.md` modified).
8. **No push** (per Wave 325 NO-PUSH policy; commit is local only).

### 3.2 Interpretation

The Wave 349-352 wave-arc was overwhelmingly a **paper-side + tools-side** wave-arc, not a CLM-side one. The single CLM-level touchpoint (CLM-060 / Wave 352 P5) is consistent with the Wave 351 P2 audit doc §3.4 "What was NOT done (deliberately)" section which explicitly said "No edit to `docs/CLAIMS.md` (CLM-060 row is preserved verbatim per Wave 268)" — and the Wave 352 P5 audit doc's purpose was to surface the n=10 paired-t confirmation as an additive CLM-060 status addendum without changing the row text or any number.

The other 60 active CLMs preserve their pre-Wave-349 status verbatim because Wave 349-352 did not add any new evidence that would change a verdict, status label, or asserted-by reference for those rows. The paper-side work (Theorem 5 derivation, §6.6.1 numerical footnote, §10.9.3 partial close-out, §3.4-§3.7 framework code-anchor cross-references, §A.3 Lipschitz-constant appendix, §7.6 R5b 4-scheduler figure) and tools-side work (cover-letter helper + interactive mode, LineageFlowAdapter cuda:0 dispatch) are correctly recorded in the wave audit docs and propagated to the paper surfaces they touch (`docs/drafts/paper-A-final.md`, `tools/render_cover_letter.py`, `adaptive_reflow/adapters/lineageflow.py`, etc.) — but they do not affect the CLM ledger.

### 3.3 Unresolved gaps

None for this Wave 353 P8 consolidation. The consolidated table surfaces the single CLM-level touchpoint (CLM-060) and the 60 other active CLMs preserve their pre-Wave-349 status. The full Wave 349-352 audit trail is available via the 17 `docs/audit/wave35X-*.md` audit docs.

### 3.4 What was NOT done (deliberately)

- **No CLM number was changed.** The 61 active CLM IDs and 2 deprecated CLM IDs are preserved verbatim.
- **No CLM status label was changed.** No row was promoted from `UNDERPOWERED` to `SUPPORTED`, from `REGRESSES` to `SUPPORTED`, from `DEFERRED` to `SUPPORTED`, or from `NOT_SIGNIFICANT` to `SUPPORTED`. Per AGENTS.md hard guardrail #4 (Honest uncertainty), only the consolidated table wording was added.
- **No asserted-by reference was changed.** The file:line pointers in each `## CLM-NNN:` row's `Asserted by:` block are preserved verbatim.
- **No edits to other doc files** — the consolidated table is added to `docs/CLAIMS.md` only.
- **No re-run of any GPU sweep.** Per `flowa-research-audit` skill: prefer existing artifacts; the Wave 216 P2 n=10 per-seed CSV (referenced by the CLM-060 row in the table) is byte-stable and serves as the canonical evidence for the n=10 paired-t extension.
- **No push.** Per Wave 325 NO-PUSH policy; commit is local only.

---

## 4. Verification gates

| Gate | Command | Result |
|---|---|---|
| Claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — "No drift detected" (61 active, 2 deprecated, 0 provisional) |
| D.4 regression vectors | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** |
| No CLM number changed | `git diff docs/CLAIMS.md` | **PASS** — additive 18-line block only; no CLM IDs added/removed/renumbered |
| No CLM status changed | `git diff docs/CLAIMS.md` | **PASS** — no `Status: ` lines changed |
| No asserted-by changed | `git diff docs/CLAIMS.md` | **PASS** — no `Asserted by:` lines changed |
| No edits outside docs/CLAIMS.md | `git status` | **PASS** — only `docs/CLAIMS.md` modified + new `docs/audit/wave353-claims-consolidation.md` (this doc) |
| No push | `git log --oneline -1` (no remote) | **PASS** — local commit only |

---

## 5. Files written / modified

| File | Role | Lines changed |
|---|---|---|
| `docs/CLAIMS.md` | ACTIVE claim ledger | **+18 lines** (lines 23-40: new consolidated status table appended after "How it works" intro, before `## CLM-001`) — purely additive, no claim number / status / asserted-by changed |
| `docs/audit/wave353-claims-consolidation.md` | This audit doc | **new file** |

No existing files modified outside the additions above. No vendored upstream touched. No source code touched.

---

## 6. Cross-reference surface

- **Wave 351 P2 audit doc** [`docs/audit/wave351-r5a-n10.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-r5a-n10.md) — primary evidence anchor for the CLM-060 / Wave 352 P5 addendum. Paired-t + Hedges g + DL meta-analysis on the Wave 216 P2 n=10 per-seed CSV.
- **Wave 352 P5 audit doc** [`docs/audit/wave352-claims-r5a-update.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave352-claims-r5a-update.md) — propagation step that added the Wave 352 P5 status addendum to CLM-060.
- **Wave 216 P2 n=10 per-seed CSV** `verification_outputs/wave216-p2-r5a-extended.csv` — canonical evidence: N=1000 records/seed × canonical 10 seeds `[0, 1, 2, 3, 4, 5, 6, 43, 44, 45]`.
- **CLM-060 R-level row in `docs/CLAIMS.md` (lines 3009-3120)** — the row that received the Wave 352 P5 addendum; verdict distribution (0 SUPPORTED / 1 REGRESSES / 1 TIE / 6 UNDERPOWERED) is preserved verbatim.
- **§15.104 new section in `docs/CONSOLIDATED_RESULTS.md`** — Wave 352 P5 propagation partner; records the same n=10 paired-t confirmation in the §15 ledger.
- **Wave 326 cross-doc-snapshot 11-cell verdict distribution** — preserved verbatim (4 STRONG + 1 TIE + 6 PARTIAL/SUPP = 11 headline cells).
- **Wave 195 P2 verdict distribution** — preserved verbatim (0 SUPPORTED / 1 REGRESSES / 1 TIE / 6 UNDERPOWERED / 0 NOT_SIGNIFICANT over 8 rows / 7 R1-R6 sub-cells).

---

_Last updated: 2026-09-25 (Wave 353 P8 — Wave 349-352 CLAIMS addenda consolidated status table)._